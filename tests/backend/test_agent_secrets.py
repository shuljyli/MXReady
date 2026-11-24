import os

import pytest

from mxready.agent.secrets import (
    EncryptedVaultStore,
    KeyringStore,
    SecretError,
    SecretManager,
    VaultError,
    VaultPasswordRequired,
    session_api_key,
)


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.fail = False

    def get_password(self, service: str, key: str) -> str | None:
        if self.fail:
            raise RuntimeError("backend locked")
        return self.values.get(key)

    def set_password(self, service: str, key: str, value: str) -> None:
        if self.fail:
            raise RuntimeError("backend locked")
        self.values[key] = value

    def delete_password(self, service: str, key: str) -> None:
        self.values.pop(key, None)


def _use_keyring(monkeypatch, backend: FakeKeyring | None) -> None:
    monkeypatch.setattr(KeyringStore, "_keyring", lambda self: backend)


def test_keyring_is_preferred_and_failure_falls_back_to_vault(monkeypatch, tmp_path):
    backend = FakeKeyring()
    _use_keyring(monkeypatch, backend)
    manager = SecretManager(tmp_path / "agent")
    assert manager.set("provider:work", "sk-keyring", password="master") == "keyring"
    assert backend.values["provider:work"] == "sk-keyring"
    assert manager.get("provider:work") == "sk-keyring"
    assert not (tmp_path / "agent" / "secrets.vault").exists()
    manager.delete("provider:work")
    assert manager.get("provider:work") is None

    backend.fail = True
    assert manager.set("provider:work", "sk-fallback", password="master") == "vault"
    assert manager.get("provider:work") == "sk-fallback"


def test_vault_requires_password_and_never_stores_plaintext(monkeypatch, tmp_path):
    _use_keyring(monkeypatch, None)
    agent_dir = tmp_path / "agent"
    manager = SecretManager(agent_dir)
    with pytest.raises(VaultPasswordRequired):
        manager.set("provider:work", "sk-plain-secret")
    assert manager.set("provider:work", "sk-plain-secret", password="correct horse") == "vault"
    vault = agent_dir / "secrets.vault"
    payload = vault.read_bytes()
    assert b"sk-plain-secret" not in payload
    assert b"correct horse" not in payload
    assert manager.get("provider:work") == "sk-plain-secret"
    with pytest.raises(VaultPasswordRequired):
        SecretManager(agent_dir).get("provider:work")
    with pytest.raises(VaultError):
        SecretManager(agent_dir, password="wrong password").get("provider:work")


def test_vault_store_roundtrip_delete_and_corruption(tmp_path):
    path = tmp_path / "secrets.vault"
    store = EncryptedVaultStore(path, "master")
    store.set("provider:a", "one")
    store.set("provider:b", "two")
    assert store.get("provider:a") == "one"
    store.delete("provider:a")
    assert store.get("provider:a") is None
    assert EncryptedVaultStore(path, "master").get("provider:b") == "two"
    store.delete("provider:b")
    assert not path.exists()

    path.write_text('{"version": 1}', encoding="utf-8")
    with pytest.raises(VaultError):
        EncryptedVaultStore(path, "master").get("provider:b")
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(VaultError):
        EncryptedVaultStore(path, "master").get("provider:b")


def test_environment_key_overrides_stored_secret_without_writing(monkeypatch, tmp_path):
    monkeypatch.setenv("MXREADY_AGENT_API_KEY", " sk-session ")
    assert session_api_key() == "sk-session"
    manager = SecretManager(tmp_path / "agent")
    assert manager.get("provider:work") == "sk-session"
    assert not (tmp_path / "agent").exists()


def test_secret_validation_rejects_empty_control_characters_and_oversize(monkeypatch, tmp_path):
    _use_keyring(monkeypatch, None)
    manager = SecretManager(tmp_path / "agent", password="master")
    for value in ("", "   ", "sk\x00key", "x" * 8193):
        with pytest.raises(SecretError):
            manager.set("provider:work", value)
    with pytest.raises(SecretError):
        EncryptedVaultStore(tmp_path / "vault", "master").set("provider:work", "")
    assert os.path.exists(tmp_path / "agent") is False
