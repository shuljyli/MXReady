import hashlib
import shutil
import subprocess
from pathlib import Path
from runpy import run_path
from unittest.mock import Mock

import pytest


def installer(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    script = tmp_path / "install.py"
    shutil.copy2(root / "packaging" / "install.py", script)
    wheel = tmp_path / "packages" / "mxready-0.1.0-py3-none-any.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"test wheel")
    (tmp_path / "WHEEL.sha256").write_text(hashlib.sha256(wheel.read_bytes()).hexdigest())
    monkeypatch.setattr(shutil, "which", lambda name: "git")
    return run_path(str(script))["main"], wheel


def test_installer_checks_checksum_before_creating_environment(tmp_path, monkeypatch):
    main, wheel = installer(tmp_path, monkeypatch)
    wheel.write_bytes(b"corrupt")
    with pytest.raises(SystemExit):
        main([])
    assert not (tmp_path / ".venv").exists()


def test_offline_install_uses_local_wheels_without_shell(tmp_path, monkeypatch):
    main, wheel = installer(tmp_path, monkeypatch)
    import sys

    python = (
        tmp_path / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    python.parent.mkdir(parents=True)
    python.touch()
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    assert main(["--offline"]) == 0
    command = run.call_args.args[0]
    assert command[-1] == str(wheel)
    assert "--no-index" in command
    assert command[command.index("--find-links") + 1] == str(wheel.parent)
    assert run.call_args.kwargs == {"check": True, "timeout": 600}
