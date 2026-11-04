import json
import subprocess

import pytest

from mxready_runner.execute import run_manifest
from mxready_runner.schema import ManifestError


@pytest.fixture
def repository(tmp_path, manifest_path):
    root = tmp_path / "checkout"
    root.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    git("init", "-q")
    (root / "source.py").write_text("pass\n")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "initial")
    payload = json.loads(manifest_path.read_text())
    payload["repository_commit"] = git("rev-parse", "HEAD")
    manifest_path.write_text(json.dumps(payload))
    return root


def test_runner_requires_matching_clean_checkout(repository, manifest_path, recording_runner):
    result = run_manifest(
        manifest_path,
        repository_dir=repository,
        approve=lambda _: True,
        command_runner=recording_runner,
    )
    assert result.repository_state["working_directory"] == str(repository.resolve())
    assert result.repository_state["dirty"] is False
    (repository / "source.py").write_text("changed\n")
    recording_runner.calls.clear()
    with pytest.raises(ManifestError, match="dirty"):
        run_manifest(
            manifest_path,
            repository_dir=repository,
            approve=lambda _: True,
            command_runner=recording_runner,
        )
    assert not recording_runner.calls


def test_runner_rejects_wrong_commit_and_non_repository(repository, manifest_path, tmp_path):
    document = json.loads(manifest_path.read_text())
    document["repository_commit"] = "b" * 40
    manifest_path.write_text(json.dumps(document))
    with pytest.raises(ManifestError, match="commit"):
        run_manifest(manifest_path, repository_dir=repository, approve=lambda _: True)
    with pytest.raises(ManifestError):
        run_manifest(manifest_path, repository_dir=tmp_path, approve=lambda _: True)


def test_runner_rechecks_after_commands(repository, manifest_path):
    def mutate(command, *, timeout, cwd):
        assert cwd == repository.resolve()
        (repository / "source.py").write_text("changed\n")
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(ManifestError, match="dirty"):
        run_manifest(
            manifest_path, repository_dir=repository, approve=lambda _: True, command_runner=mutate
        )
