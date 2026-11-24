"""API key storage: OS keyring first, encrypted local vault as a fallback."""

from __future__ import annotations

import base64
import contextlib
import json
import os
import tempfile
from pathlib import Path

SERVICE_NAME = "mxready-agent"
ENVIRONMENT_KEY = "MXREADY_AGENT_API_KEY"
VAULT_VERSION = 1
MAX_SECRET_BYTES = 8192
MAX_SECRETS = 64
MAX_VAULT_BYTES = 1024 * 1024


class SecretError(RuntimeError):
    """A secret backend could not be used."""


class VaultPasswordRequired(SecretError):
    """The encrypted vault exists but no master password is available."""


class VaultError(SecretError):
    """The encrypted vault is invalid or could not be decrypted."""


def session_api_key() -> str | None:
    value = os.getenv(ENVIRONMENT_KEY)
    if value is None or not value.strip():
        return None
    return value.strip()


def _validate_secret(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise SecretError("The API key must not be empty")
    if len(cleaned) > MAX_SECRET_BYTES:
        raise SecretError("The API key is too long")
    if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise SecretError("The API key contains control characters")
    return cleaned


class KeyringStore:
    """Thin wrapper that treats a missing or fail backend as unavailable."""

    def __init__(self, service: str = SERVICE_NAME) -> None:
        self.service = service
        self._module: object | None = None
        self._checked = False
        self._usable = False

    def _keyring(self) -> object | None:
        if self._checked:
            return self._module
        self._checked = True
        try:
            import keyring

            backend = keyring.get_keyring()
        except Exception:
            return None
        module = type(backend).__module__
        if module.startswith("keyring.backends.fail"):
            return None
        self._module = keyring
        self._usable = True
        return keyring

    def available(self) -> bool:
        return self._keyring() is not None

    def _call(self, name: str, *args: str) -> object:
        module = self._keyring()
        if module is None:
            raise SecretError("No keyring backend is available")
        try:
            return getattr(module, name)(self.service, *args)
        except Exception as error:
            raise SecretError(f"Keyring operation failed: {error}") from error

    def get(self, key_ref: str) -> str | None:
        value = self._call("get_password", key_ref)
        if value is None:
            return None
        return str(value)

    def set(self, key_ref: str, value: str) -> None:
        self._call("set_password", key_ref, value)
        if self.get(key_ref) != value:
            raise SecretError("Keyring did not retain the API key")

    def delete(self, key_ref: str) -> None:
        self._call("delete_password", key_ref)


class EncryptedVaultStore:
    """scrypt + AES-GCM vault; the master password only lives in memory."""

    def __init__(self, path: Path, password: str) -> None:
        if not password:
            raise VaultPasswordRequired("The vault master password is required")
        self.path = path
        self._password = password
        self._derived: tuple[bytes, bytes] | None = None

    def _derive(self, salt: bytes) -> bytes:
        if self._derived is not None and self._derived[0] == salt:
            return self._derived[1]
        try:
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        except ModuleNotFoundError as error:
            raise SecretError(
                'Encrypted key storage requires cryptography: pip install "mxready[agent]"'
            ) from error
        key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
            self._password.encode("utf-8")
        )
        self._derived = (salt, key)
        return key

    def _read(self) -> dict[str, str]:
        if not self.path.is_file():
            return {}
        try:
            if self.path.stat().st_size > MAX_VAULT_BYTES:
                raise VaultError("The encrypted vault exceeds 1 MiB")
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError as error:
            raise VaultError(f"Cannot read the encrypted vault: {error}") from error
        except json.JSONDecodeError as error:
            raise VaultError("The encrypted vault is not valid JSON") from error
        if not isinstance(payload, dict) or payload.get("version") != VAULT_VERSION:
            raise VaultError("Unsupported encrypted vault format")
        try:
            salt = base64.b64decode(str(payload["salt"]), validate=True)
            nonce = base64.b64decode(str(payload["nonce"]), validate=True)
            ciphertext = base64.b64decode(str(payload["ciphertext"]), validate=True)
        except (KeyError, ValueError) as error:
            raise VaultError("The encrypted vault is malformed") from error
        if len(salt) != 16 or len(nonce) != 12:
            raise VaultError("The encrypted vault has invalid parameters")
        try:
            from cryptography.exceptions import InvalidTag
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ModuleNotFoundError as error:
            raise SecretError(
                'Encrypted key storage requires cryptography: pip install "mxready[agent]"'
            ) from error
        try:
            cleartext = AESGCM(self._derive(salt)).decrypt(nonce, ciphertext, None)
        except InvalidTag as error:
            raise VaultError("The vault master password is incorrect") from error
        try:
            values = json.loads(cleartext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VaultError("The decrypted vault payload is invalid") from error
        if not isinstance(values, dict) or len(values) > MAX_SECRETS:
            raise VaultError("The decrypted vault payload is invalid")
        result: dict[str, str] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise VaultError("The decrypted vault payload is invalid")
            result[key] = value
        return result

    def _write(self, values: dict[str, str]) -> None:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ModuleNotFoundError as error:
            raise SecretError(
                'Encrypted key storage requires cryptography: pip install "mxready[agent]"'
            ) from error
        salt = os.urandom(16)
        nonce = os.urandom(12)
        cleartext = json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if len(cleartext) > MAX_VAULT_BYTES:
            raise VaultError("The decrypted vault payload is too large")
        ciphertext = AESGCM(self._derive(salt)).encrypt(nonce, cleartext, None)
        payload = json.dumps(
            {
                "version": VAULT_VERSION,
                "kdf": "scrypt",
                "salt": base64.b64encode(salt).decode("ascii"),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            },
            indent=2,
            sort_keys=True,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            dir=self.path.parent, prefix=".vault-", suffix=".tmp"
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            with contextlib.suppress(OSError):
                os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(temporary)

    def get(self, key_ref: str) -> str | None:
        return self._read().get(key_ref)

    def set(self, key_ref: str, value: str) -> None:
        values = self._read()
        if key_ref not in values and len(values) >= MAX_SECRETS:
            raise VaultError("The vault holds too many secrets")
        values[key_ref] = _validate_secret(value)
        self._write(values)

    def delete(self, key_ref: str) -> None:
        values = self._read()
        if values.pop(key_ref, None) is None:
            return
        if values:
            self._write(values)
            return
        with contextlib.suppress(FileNotFoundError):
            self.path.unlink()


class SecretManager:
    """Resolve and store API keys without ever writing them to agent config."""

    def __init__(self, agent_dir: Path, *, password: str | None = None) -> None:
        self.agent_dir = agent_dir
        self.vault_path = agent_dir / "secrets.vault"
        self.password = password
        self.keyring = KeyringStore()

    def keyring_available(self) -> bool:
        return self.keyring.available()

    def vault_exists(self) -> bool:
        return self.vault_path.is_file()

    def get(self, key_ref: str) -> str | None:
        override = session_api_key()
        if override is not None:
            return override
        if self.keyring_available():
            try:
                value = self.keyring.get(key_ref)
                if value:
                    return value
            except SecretError:
                pass
        if not self.vault_path.is_file():
            return None
        if not self.password:
            raise VaultPasswordRequired(
                "The encrypted vault needs its master password for this session"
            )
        return EncryptedVaultStore(self.vault_path, self.password).get(key_ref)

    def set(self, key_ref: str, value: str, *, password: str | None = None) -> str:
        cleaned = _validate_secret(value)
        password = password or self.password
        if self.keyring_available():
            try:
                self.keyring.set(key_ref, cleaned)
                return "keyring"
            except SecretError:
                if not password:
                    raise VaultPasswordRequired(
                        "The keyring failed; enter a vault master password to continue"
                    ) from None
        if not password:
            raise VaultPasswordRequired("A vault master password is required")
        EncryptedVaultStore(self.vault_path, password).set(key_ref, cleaned)
        self.password = password
        return "vault"

    def delete(self, key_ref: str, *, password: str | None = None) -> None:
        password = password or self.password
        if self.vault_path.is_file() and not password:
            raise VaultPasswordRequired("The vault master password is required to remove the key")
        if self.keyring_available():
            with contextlib.suppress(SecretError):
                self.keyring.delete(key_ref)
        if self.vault_path.is_file():
            EncryptedVaultStore(self.vault_path, str(password)).delete(key_ref)
