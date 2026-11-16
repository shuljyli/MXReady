import io
import sys
from unittest.mock import Mock

import pytest

from mxready.cli import terminal


def test_launcher_requires_terminal(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    assert terminal.main([]) == 1
    assert "mxready-scan" in capsys.readouterr().err


def test_launcher_passes_project_and_output(monkeypatch, tmp_path):
    from mxready.tui import app

    launch = Mock()
    monkeypatch.setattr(app, "MXReadyApp", launch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("MXREADY_DATA_DIR", str(tmp_path / "data"))
    assert terminal.main([str(tmp_path), "--output-dir", str(tmp_path / "results")]) == 0
    launch.assert_called_once_with(
        project_dir=tmp_path,
        output_dir=tmp_path / "results",
        default_output_dir=tmp_path / "data" / "reports",
        state_path=tmp_path / "data" / "tui" / "state.db",
    )
    launch.return_value.run.assert_called_once_with()


def test_launcher_explains_missing_optional_dependency(monkeypatch, tmp_path, capsys):
    import builtins

    real_import = builtins.__import__

    def without_textual(name, *args, **kwargs):
        if name == "mxready.tui.app":
            raise ModuleNotFoundError("No module named textual", name="textual")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_textual)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert terminal.main([str(tmp_path)]) == 1
    assert "mxready[tui]" in capsys.readouterr().err


def test_launcher_rejects_missing_project(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert terminal.main([str(tmp_path / "missing")]) == 1
    assert "directory" in capsys.readouterr().err


def test_help_works_without_terminal(capsys):
    with pytest.raises(SystemExit) as result:
        terminal.main(["--help"])
    assert result.value.code == 0
    assert "--output-dir" in capsys.readouterr().out


def test_no_state_does_not_create_user_data(monkeypatch, tmp_path):
    from mxready.tui import app

    launch = Mock()
    monkeypatch.setattr(app, "MXReadyApp", launch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("MXREADY_DATA_DIR", str(tmp_path / "private"))
    assert terminal.main([str(tmp_path), "--no-state"]) == 0
    assert launch.call_args.kwargs["state_path"] is None
    assert not (tmp_path / "private").exists()
