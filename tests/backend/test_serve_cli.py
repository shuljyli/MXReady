from pathlib import Path
from unittest.mock import Mock

import pytest

from mxready.cli import serve


def test_serve_uses_loopback_and_user_data_outside_working_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(serve.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(serve, "default_data_directory", lambda: tmp_path / "user-data")
    application = Mock()
    create = Mock(return_value=application)
    run = Mock()
    monkeypatch.setattr(serve, "create_app", create)
    monkeypatch.setattr(serve.uvicorn, "run", run)
    for name in ("MXREADY_DATA_DIR", "MXREADY_TEMP_DIR"):
        monkeypatch.delenv(name, raising=False)

    assert serve.main([]) == 0
    settings = create.call_args.args[0]
    assert settings.data_dir == tmp_path / "user-data"
    assert settings.temp_dir == tmp_path / "user-data" / "tmp"
    run.assert_called_once_with(application, host="127.0.0.1", port=8000)


def test_serve_respects_explicit_and_environment_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(serve.shutil, "which", lambda name: "git")
    monkeypatch.setenv("MXREADY_DATA_DIR", str(tmp_path / "environment"))
    monkeypatch.setenv("MXREADY_TEMP_DIR", str(tmp_path / "scratch"))
    create = Mock()
    monkeypatch.setattr(serve, "create_app", create)
    monkeypatch.setattr(serve.uvicorn, "run", Mock())

    assert serve.main(["--data-dir", str(tmp_path / "chosen"), "--port", "8123"]) == 0
    assert create.call_args.args[0].data_dir == tmp_path / "chosen"
    assert create.call_args.args[0].temp_dir == tmp_path / "scratch"


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_serve_rejects_invalid_port(port):
    with pytest.raises(SystemExit):
        serve.main(["--port", port])


def test_serve_reports_missing_git(monkeypatch, capsys):
    monkeypatch.setattr(serve.shutil, "which", lambda name: None)
    assert serve.main([]) == 1
    assert "Git" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("win32", "AppData/Local/MXReady"),
        ("darwin", "Library/Application Support/MXReady"),
        ("linux", ".local/share/mxready"),
    ],
)
def test_platform_data_directories(monkeypatch, tmp_path, platform, expected):
    monkeypatch.setattr(serve.sys, "platform", platform)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert serve.default_data_directory() == tmp_path / expected


def test_platform_data_directory_overrides(monkeypatch, tmp_path):
    monkeypatch.setattr(serve.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert serve.default_data_directory() == tmp_path / "mxready"
    monkeypatch.setattr(serve.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert serve.default_data_directory() == tmp_path / "MXReady"
