from pathlib import Path

import pytest

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


def test_prefilter_defaults_to_auto() -> None:
    assert Settings().prefilter_mode == "auto"
    assert Settings().prefilter_enabled is True


def test_prefilter_mode_env_switch(monkeypatch) -> None:
    """应急止血开关：off 关闭预过滤，大小写与空白都容忍。"""
    monkeypatch.setenv("MXREADY_PREFILTER_MODE", " OFF ")
    settings = Settings.from_env()
    assert settings.prefilter_mode == "off"
    assert settings.prefilter_enabled is False


def test_prefilter_mode_env_falls_back_on_typo(monkeypatch) -> None:
    """拼错时回退默认值：既不阻止启动，也不静默关掉优化。"""
    monkeypatch.setenv("MXREADY_PREFILTER_MODE", "disable")
    assert Settings.from_env().prefilter_mode == "auto"


def test_prefilter_mode_rejects_unknown_construction() -> None:
    """直接构造是编程错误，必须立刻失败而不是悄悄降级。"""
    with pytest.raises(ValueError):
        Settings(prefilter_mode="auto ")
