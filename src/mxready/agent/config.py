"""Non-secret provider configuration with atomic, private writes."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit

from mxready.i18n import DEFAULT_LANGUAGE, tr

CONFIG_VERSION = 1
MAX_CONFIG_BYTES = 256 * 1024
MAX_PROVIDERS = 32
PROTOCOLS = ("openai", "anthropic")
_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_KEY_REF = re.compile(r"^[a-z0-9][a-z0-9:._-]{0,79}$")
_FINGERPRINT = re.compile(r"^(?:[0-9a-f]{12})?$")
_MODEL_CONTROL = re.compile(r"[\x00-\x20\x7f]")


class ConfigError(ValueError):
    """A configuration file could not be read or validated."""


def validate_provider_name(value: str, language: str = DEFAULT_LANGUAGE) -> str:
    cleaned = value.strip().casefold()
    if not _NAME.fullmatch(cleaned):
        raise ValueError(
            tr(
                language,
                "服务名称只能包含小写字母、数字、下划线或连字符（最多 32 字符）。",
                "Provider names use lowercase letters, digits, underscores, or hyphens "
                "(maximum 32 characters).",
            )
        )
    return cleaned


def validate_model_name(value: str, language: str = DEFAULT_LANGUAGE) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 200 or _MODEL_CONTROL.search(cleaned):
        raise ValueError(
            tr(
                language,
                "模型名称必须是 1-200 个不含空白或控制字符的字符。",
                "Model names must be 1-200 characters without whitespace or control characters.",
            )
        )
    return cleaned


def validate_base_url(value: str, language: str = DEFAULT_LANGUAGE) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 2048:
        raise ValueError(
            tr(language, "base URL 长度无效。", "The base URL length is invalid.")
        )
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(
            tr(
                language,
                "base URL 不能包含空白或控制字符。",
                "The base URL must not contain whitespace or control characters.",
            )
        )
    if "\\" in cleaned:
        raise ValueError(
            tr(
                language,
                "base URL 不能包含反斜杠。",
                "The base URL cannot contain backslashes.",
            )
        )
    parts = urlsplit(cleaned)
    scheme = parts.scheme.casefold()
    if scheme not in {"https", "http"}:
        raise ValueError(
            tr(
                language,
                "base URL 必须使用 https；仅本机 localhost 允许 http。",
                "The base URL must use https; http is allowed only for localhost.",
            )
        )
    if not parts.hostname:
        raise ValueError(tr(language, "base URL 缺少主机名。", "The base URL has no host."))
    if parts.username is not None or parts.password is not None:
        raise ValueError(
            tr(
                language,
                "base URL 不能包含用户名或密码。",
                "The base URL must not contain a username or password.",
            )
        )
    if parts.query or parts.fragment:
        raise ValueError(
            tr(
                language,
                "base URL 不能包含查询参数或 fragment。",
                "The base URL must not contain a query or fragment.",
            )
        )
    if scheme == "http" and parts.hostname.casefold() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(
            tr(
                language,
                "仅 localhost / 127.0.0.1 / ::1 允许使用 http。",
                "Only localhost / 127.0.0.1 / ::1 may use http.",
            )
        )
    return cleaned.rstrip("/")


def key_reference(name: str) -> str:
    return f"provider:{name}"


def fingerprint_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def endpoint_url(base_url: str, protocol: str) -> str:
    """Append the protocol path unless the user supplied the full endpoint."""
    if protocol == "openai":
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"
    if base_url.endswith("/messages"):
        return base_url
    return f"{base_url}/messages"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    protocol: str
    base_url: str
    model: str
    key_ref: str
    fingerprint: str = ""
    max_tokens: int = 2048
    temperature: float = 0.2

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_provider_name(self.name))
        if self.protocol not in PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
        object.__setattr__(self, "base_url", validate_base_url(self.base_url))
        object.__setattr__(self, "model", validate_model_name(self.model))
        if not _KEY_REF.fullmatch(self.key_ref):
            raise ValueError("Invalid key reference")
        if not _FINGERPRINT.fullmatch(self.fingerprint):
            raise ValueError("Invalid key fingerprint")
        if not 1 <= self.max_tokens <= 32768:
            raise ValueError("max_tokens must be between 1 and 32768")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2")

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "base_url": self.base_url,
            "model": self.model,
            "key_ref": self.key_ref,
            "fingerprint": self.fingerprint,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

    @classmethod
    def from_dict(cls, name: str, value: object) -> ProviderConfig:
        if not isinstance(value, dict):
            raise ConfigError(f"Provider {name!r} is not an object")
        try:
            return cls(
                name=name,
                protocol=str(value.get("protocol", "")),
                base_url=str(value.get("base_url", "")),
                model=str(value.get("model", "")),
                key_ref=str(value.get("key_ref", key_reference(name))),
                fingerprint=str(value.get("fingerprint", "")),
                max_tokens=int(value.get("max_tokens", 2048)),
                temperature=float(value.get("temperature", 0.2)),
            )
        except (TypeError, ValueError) as error:
            raise ConfigError(f"Invalid provider {name!r}: {error}") from error


@dataclass(frozen=True)
class AgentConfig:
    version: int = CONFIG_VERSION
    active: str | None = None
    providers: dict[str, ProviderConfig] = field(default_factory=dict)

    def provider(self, name: str | None = None) -> ProviderConfig | None:
        key = name or self.active
        return self.providers.get(key) if key else None

    def with_provider(self, provider: ProviderConfig, *, activate: bool = True) -> AgentConfig:
        providers = dict(self.providers)
        providers[provider.name] = provider
        if len(providers) > MAX_PROVIDERS:
            raise ValueError(f"At most {MAX_PROVIDERS} providers are supported")
        return replace(self, providers=providers, active=provider.name if activate else self.active)

    def without(self, name: str) -> AgentConfig:
        providers = {key: value for key, value in self.providers.items() if key != name}
        active = None if self.active == name else self.active
        return replace(self, providers=providers, active=active)

    def with_active(self, name: str) -> AgentConfig:
        if name not in self.providers:
            raise ValueError(f"Unknown provider: {name}")
        return replace(self, active=name)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": CONFIG_VERSION,
            "active": self.active,
            "providers": {
                name: provider.to_dict() for name, provider in sorted(self.providers.items())
            },
        }

    @classmethod
    def from_dict(cls, value: object) -> AgentConfig:
        if not isinstance(value, dict):
            raise ConfigError("Agent configuration must be an object")
        version = value.get("version", CONFIG_VERSION)
        if version != CONFIG_VERSION:
            raise ConfigError(f"Unsupported agent configuration version: {version}")
        raw_providers = value.get("providers", {})
        if not isinstance(raw_providers, dict) or len(raw_providers) > MAX_PROVIDERS:
            raise ConfigError("Agent providers must be a bounded object")
        providers = {
            validate_provider_name(name): ProviderConfig.from_dict(name, item)
            for name, item in raw_providers.items()
        }
        active = value.get("active")
        if active is not None:
            active = validate_provider_name(str(active))
            if active not in providers:
                active = None
        return cls(version=CONFIG_VERSION, active=active, providers=providers)


class ConfigStore:
    def __init__(self, agent_dir: Path) -> None:
        self.agent_dir = agent_dir
        self.path = agent_dir / "config.json"

    def load(self) -> AgentConfig:
        try:
            if not self.path.is_file():
                return AgentConfig()
            if self.path.stat().st_size > MAX_CONFIG_BYTES:
                raise ConfigError("Agent configuration exceeds 256 KiB")
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except OSError as error:
            raise ConfigError(f"Cannot read agent configuration: {error}") from error
        except json.JSONDecodeError as error:
            raise ConfigError(f"Invalid agent configuration JSON: {error.msg}") from error
        return AgentConfig.from_dict(payload)

    def save(self, config: AgentConfig) -> None:
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self.agent_dir, 0o700)
        payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        descriptor, temporary = tempfile.mkstemp(
            dir=self.agent_dir, prefix=".config-", suffix=".tmp"
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
