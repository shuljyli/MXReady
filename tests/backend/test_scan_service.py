from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import ScanStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog
from mxready.services.scans import ScanService
from mxready.storage import SQLiteStore

FIXTURE = Path("tests/fixtures/repositories/cuda_extension")


class FixtureGitClient:
    def clone(self, identity, requested_ref, destination):
        shutil.copytree(FIXTURE, destination)
        return "e" * 40


class FailingGitClient:
    def clone(self, identity, requested_ref, destination):
        raise MxReadyError("CLONE_TIMEOUT", "The clone timed out.")


def test_scan_service_persists_exact_successful_state_sequence(tmp_path: Path) -> None:
    service, store, settings = _build_service(tmp_path, FixtureGitClient())
    statuses: list[ScanStatus] = []
    update_job = store.update_job

    def recording_update(*args, **kwargs):
        statuses.append(kwargs["status"])
        return update_job(*args, **kwargs)

    store.update_job = recording_update
    job = service.create_scan(
        "https://github.com/example/cuda-extension",
        None,
    )

    service.run_scan(job.id)

    completed = store.get_job(job.id)
    assert completed is not None
    assert completed.status is ScanStatus.COMPLETED
    assert completed.resolved_commit == "e" * 40
    assert store.get_report(job.id) is not None
    assert statuses == [
        ScanStatus.CLONING,
        ScanStatus.INDEXING,
        ScanStatus.ANALYZING,
        ScanStatus.COMPLETED,
    ]
    assert list(settings.temp_dir.iterdir()) == []


def test_scan_service_maps_known_failures_to_failed_job(tmp_path: Path) -> None:
    service, store, _ = _build_service(tmp_path, FailingGitClient())
    job = service.create_scan("https://gitee.com/example/project", "main")

    service.run_scan(job.id)

    failed = store.get_job(job.id)
    assert failed is not None
    assert failed.status is ScanStatus.FAILED
    assert failed.failure_code == "CLONE_TIMEOUT"
    assert failed.failure_message == "The clone timed out."


def test_scan_service_limits_concurrent_active_jobs(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        rules_dir=Path("rules/v1"),
        temp_dir=tmp_path / "tmp",
        max_concurrent_scans=1,
    )
    settings.temp_dir.mkdir(parents=True)
    store = SQLiteStore(settings.data_dir / "mxready.db")
    store.initialize()
    service = ScanService(
        store,
        FixtureGitClient(),
        ScanAnalyzer(load_rule_catalog(settings.rules_dir)),
        settings,
    )
    service.create_scan("https://github.com/example/first", None)

    with pytest.raises(MxReadyError) as error:
        service.create_scan("https://github.com/example/second", None)

    assert error.value.code == "SCAN_LIMIT_REACHED"


def test_scan_service_ignores_limit_when_disabled(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        rules_dir=Path("rules/v1"),
        temp_dir=tmp_path / "tmp",
        max_concurrent_scans=0,
    )
    settings.temp_dir.mkdir(parents=True)
    store = SQLiteStore(settings.data_dir / "mxready.db")
    store.initialize()
    service = ScanService(
        store,
        FixtureGitClient(),
        ScanAnalyzer(load_rule_catalog(settings.rules_dir)),
        settings,
    )
    for _ in range(3):
        service.create_scan("https://github.com/example/project", None)

    assert store.count_active_jobs() == 3


def _build_service(tmp_path: Path, git_client):
    settings = Settings(
        data_dir=tmp_path / "data",
        rules_dir=Path("rules/v1"),
        temp_dir=tmp_path / "tmp",
    )
    settings.temp_dir.mkdir(parents=True)
    store = SQLiteStore(settings.data_dir / "mxready.db")
    store.initialize()
    analyzer = ScanAnalyzer(load_rule_catalog(settings.rules_dir))
    return ScanService(store, git_client, analyzer, settings), store, settings
