from pathlib import Path

from mxready.config import Settings


def test_defaults_match_construction() -> None:
    """未设置环境变量时，from_env() 与默认构造等价。"""
    assert Settings.from_env() == Settings()


def test_env_overrides_paths(monkeypatch) -> None:
    """MXREADY_* 环境变量覆盖对应路径配置。"""
    monkeypatch.setenv("MXREADY_DATA_DIR", "/srv/mxready/data")
    monkeypatch.setenv("MXREADY_RULES_DIR", "/srv/mxready/rules/custom")
    monkeypatch.setenv("MXREADY_TEMP_DIR", "/srv/mxready/tmp")
    monkeypatch.setenv("MXREADY_FRONTEND_DIR", "/srv/mxready/static")

    settings = Settings.from_env()

    assert settings.data_dir == Path("/srv/mxready/data")
    assert settings.rules_dir == Path("/srv/mxready/rules/custom")
    assert settings.temp_dir == Path("/srv/mxready/tmp")
    assert settings.frontend_dist == Path("/srv/mxready/static")


def test_env_overrides_log_level(monkeypatch) -> None:
    monkeypatch.setenv("MXREADY_LOG_LEVEL", "DEBUG")
    assert Settings.from_env().log_level == "DEBUG"


def test_unrelated_env_ignored(monkeypatch) -> None:
    """不相关的环境变量不影响配置。"""
    monkeypatch.setenv("MXREADY_UNKNOWN", "boom")
    assert Settings.from_env() == Settings()
