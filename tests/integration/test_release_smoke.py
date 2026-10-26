import hashlib
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def smoke():
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_release.py"
    spec = importlib.util.spec_from_file_location("release_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rejects_corrupt_installer_before_execution(smoke, tmp_path):
    archive = tmp_path / "mxready-0.1.0-macos.zip"
    archive.write_bytes(b"original")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (tmp_path / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n")
    assert smoke.select_archive(tmp_path, "macos") == archive
    archive.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        smoke.select_archive(tmp_path, "macos")


def test_profile_uses_os_defaults_without_touching_real_user_data(smoke, tmp_path, monkeypatch):
    monkeypatch.setenv("MXREADY_DATA_DIR", "/real/data")
    monkeypatch.setenv("MXREADY_TEMP_DIR", "/real/tmp")
    monkeypatch.setenv("PYTHONPATH", "/source/checkout")
    monkeypatch.setenv("PYTHONHOME", "/development/python")
    monkeypatch.setenv("XDG_DATA_HOME", "/real/xdg")
    env, data = smoke.profile_environment(tmp_path, "macos")
    assert data == tmp_path / "home/Library/Application Support/MXReady"
    assert env["HOME"] == str(tmp_path / "home")
    assert not any(name.startswith("MXREADY_") for name in env)
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env
    assert "XDG_DATA_HOME" not in env
    env, data = smoke.profile_environment(tmp_path, "windows")
    assert data == tmp_path / "home/AppData/Local/MXReady"
    assert env["LOCALAPPDATA"] == str(tmp_path / "home/AppData/Local")
    _, data = smoke.profile_environment(tmp_path, "linux")
    assert data == tmp_path / "home/.local/share/mxready"


def test_command_failure_keeps_exit_code_and_log(smoke, tmp_path):
    import subprocess
    import sys

    evidence = smoke.Evidence(tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        evidence.run(
            "failure",
            [sys.executable, "-c", "print('diagnostic');exit(7)"],
            cwd=tmp_path,
            env={},
            timeout=10,
        )
    assert evidence.commands[0]["returncode"] == 7
    assert "diagnostic" in (tmp_path / "failure.log").read_text()


def test_failed_checksum_writes_failed_evidence(smoke, tmp_path):
    import json

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "mxready-0.1.0-macos.zip").write_bytes(b"corrupt")
    (dist / "SHA256SUMS.txt").write_text("0" * 64 + "  mxready-0.1.0-macos.zip\n")
    evidence = tmp_path / "evidence"
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(smoke.sys, "platform", "darwin")
        with pytest.raises(ValueError, match="checksum"):
            smoke.main(["--dist", str(dist), "--evidence-dir", str(evidence)])
    result = json.loads((evidence / "result.json").read_text())
    assert result["status"] == "failed"
    assert result["commands"] == []
    assert "checksum" in result["error"]
    with pytest.raises(SystemExit):
        smoke.main(["--dist", str(dist), "--evidence-dir", str(evidence)])
