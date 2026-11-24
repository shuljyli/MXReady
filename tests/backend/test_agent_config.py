import json
import subprocess
import sys

import pytest

from mxready.agent.config import (
    AgentConfig,
    ConfigError,
    ConfigStore,
    ProviderConfig,
    endpoint_url,
    fingerprint_secret,
    key_reference,
    validate_base_url,
    validate_model_name,
    validate_provider_name,
)


def _provider(**overrides):
    values = {
        "name": "work",
        "protocol": "openai",
        "base_url": "https://api.example.com/v1",
        "model": "gpt-x",
        "key_ref": key_reference("work"),
        "fingerprint": fingerprint_secret("secret-key"),
    }
    values.update(overrides)
    return ProviderConfig(**values)


def test_provider_validation_rejects_unsafe_urls_and_names():
    assert validate_provider_name(" Work_1 ") == "work_1"
    for name in ("", "Upper Space", "-bad", "x" * 33, "bad/name"):
        with pytest.raises(ValueError):
            validate_provider_name(name)
    assert validate_base_url("https://api.example.com/v1/") == "https://api.example.com/v1"
    assert validate_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"
    assert validate_base_url("http://[::1]:8080") == "http://[::1]:8080"
    for url in (
        "http://example.com",
        "ftp://example.com",
        "https://user:pass@example.com",
        "https://example.com/v1?x=1",
        "https://example.com/#x",
        "https://example.com\\v1",
        "not a url",
    ):
        with pytest.raises(ValueError):
            validate_base_url(url)
    assert validate_model_name(" vendor/model-2 ") == "vendor/model-2"
    with pytest.raises(ValueError):
        validate_model_name("bad\nmodel")
    with pytest.raises(ValueError):
        validate_model_name("two words")


def test_endpoint_url_respects_full_paths():
    assert (
        endpoint_url("https://api.example.com/v1", "openai")
        == "https://api.example.com/v1/chat/completions"
    )
    assert (
        endpoint_url("https://api.example.com/v1/chat/completions", "openai")
        == "https://api.example.com/v1/chat/completions"
    )
    assert endpoint_url("https://api.example.com/v1", "anthropic") == "https://api.example.com/v1/messages"
    assert (
        endpoint_url("https://api.example.com/v1/messages", "anthropic")
        == "https://api.example.com/v1/messages"
    )


def test_config_roundtrip_never_contains_secret_material(tmp_path):
    store = ConfigStore(tmp_path / "agent")
    first = _provider()
    second = _provider(name="local", protocol="anthropic", base_url="http://127.0.0.1:8080")
    config = AgentConfig().with_provider(first).with_provider(second, activate=False)
    store.save(config)
    raw = (tmp_path / "agent" / "config.json").read_text(encoding="utf-8")
    assert "secret-key" not in raw
    assert fingerprint_secret("secret-key") in raw
    loaded = store.load()
    assert loaded.active == "work"
    assert loaded.provider("local") == second
    assert loaded.provider().key_ref == "provider:work"


def test_config_rejects_unknown_versions_oversized_files_and_bad_active(tmp_path):
    store = ConfigStore(tmp_path / "agent")
    assert store.load() == AgentConfig()
    store.path.parent.mkdir(parents=True)
    store.path.write_text('{"version": 9, "providers": {}}', encoding="utf-8")
    with pytest.raises(ConfigError):
        store.load()
    store.path.write_text(" " * (256 * 1024 + 1), encoding="utf-8")
    with pytest.raises(ConfigError):
        store.load()
    config = AgentConfig.from_dict(
        {
            "version": 1,
            "active": "missing",
            "providers": {"work": _provider().to_dict()},
        }
    )
    assert config.active is None
    assert config.provider("work") is not None


def test_provider_dict_does_not_accept_a_plain_string_secret(tmp_path):
    payload = _provider().to_dict()
    payload["api_key"] = "sk-should-not-be-stored"
    payload.pop("fingerprint")
    serialized = json.dumps({"version": 1, "providers": {"work": payload}})
    parsed = AgentConfig.from_dict(json.loads(serialized))
    assert "api_key" not in json.dumps(parsed.to_dict())


def test_with_active_and_without_keep_configuration_consistent():
    config = AgentConfig().with_provider(_provider())
    with pytest.raises(ValueError):
        config.with_active("missing")
    config = config.with_active("work")
    removed = config.without("work")
    assert removed.active is None
    assert removed.providers == {}


def test_web_entrypoints_do_not_import_the_agent_package():
    code = (
        "import sys; import mxready.app; import mxready.cli.serve; "
        "import mxready.api.scans; import mxready.services.scans; "
        "assert 'mxready.agent' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=60)
