import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock

import pytest
from fastapi.testclient import TestClient

from mxready.app import create_app
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import ScanStatus
from mxready.persistence.sqlite import SQLiteStore
from mxready.services.worker import ScanWorker


def test_scan_can_be_claimed_by_only_one_consumer(tmp_path):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://github.com/example/project", None)
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(
            pool.map(
                lambda token: store.claim_job(job.id, str(token), lease_seconds=120),
                range(8),
            )
        )
    assert sum(claims) == 1


def test_http_submission_is_consumed_by_the_application_worker(tmp_path, monkeypatch):
    class FixtureGit:
        def clone(self, identity, ref, destination):
            shutil.copytree("tests/fixtures/repositories/cuda_extension", destination)
            return "b" * 40

    monkeypatch.setattr("mxready.app.GitClient", FixtureGit)
    settings = Settings(data_dir=tmp_path / "data", temp_dir=tmp_path / "tmp")
    with TestClient(create_app(settings)) as client:
        submitted = client.post(
            "/api/scans",
            json={
                "repo_url": "https://github.com/example/project",
                "ref": None,
            },
        )
        assert submitted.status_code == 202
        scan_id = submitted.json()["id"]
        deadline = time.monotonic() + 5
        while client.get(f"/api/scans/{scan_id}").json()["status"] != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        report = client.get(f"/api/scans/{scan_id}/report").json()
        assert report["repository"]["commit"] == "b" * 40
        assert report["ruleset_digest"].startswith("sha256:")


def test_finished_scan_revokes_its_execution_token(tmp_path):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://github.com/example/project", None)
    assert store.claim_job(job.id, "owner", lease_seconds=120)
    store.update_job(
        job.id, status=ScanStatus.COMPLETED, stage_message="Done", worker_token="owner"
    )
    with pytest.raises(MxReadyError, match="lease"):
        store.update_job(
            job.id, status=ScanStatus.ANALYZING, stage_message="Late", worker_token="owner"
        )


def test_recovery_preserves_queued_jobs_and_fences_expired_executors(tmp_path, report_factory):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    queued = store.create_job("https://github.com/example/queued", None)
    live = store.create_job("https://github.com/example/live", None)
    assert store.claim_job(live.id, "owner", lease_seconds=120)
    assert not store.renew_lease(live.id, "wrong-owner", lease_seconds=120)
    assert store.renew_lease(live.id, "owner", lease_seconds=120)
    store.recover_expired_jobs()
    assert store.get_job(live.id).status is ScanStatus.CLONING
    store.recover_expired_jobs(now=datetime.now(UTC) + timedelta(seconds=121))
    assert store.get_job(live.id).failure_code == "SCAN_INTERRUPTED"
    assert store.get_job(queued.id).status is ScanStatus.QUEUED
    assert not store.renew_lease(live.id, "owner", lease_seconds=120)
    with pytest.raises(MxReadyError, match="lease"):
        store.update_job(
            live.id, status=ScanStatus.COMPLETED, stage_message="Late", worker_token="owner"
        )
    with pytest.raises(MxReadyError, match="lease"):
        store.save_report(report_factory(scan_id=live.id), worker_token="owner")


def test_two_workers_resume_a_persisted_queue_and_execute_each_scan_once(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", temp_dir=tmp_path / "tmp")
    store = SQLiteStore(settings.data_dir / "mxready.db")
    store.initialize()
    job = store.create_job("https://github.com/example/project", None)
    started, release = Event(), Event()
    calls = []
    lock = Lock()

    class FixtureGit:
        def clone(self, identity, ref, destination):
            with lock:
                calls.append(destination)
            started.set()
            assert release.wait(5)
            shutil.copytree(Path("tests/fixtures/repositories/cuda_extension"), destination)
            return "a" * 40

    with (
        TestClient(create_app(settings, start_worker=False)) as a,
        TestClient(create_app(settings, start_worker=False)) as b,
    ):
        workers = []
        for client in (a, b):
            client.app.state.scan_service.git_client = FixtureGit()
            worker = ScanWorker(client.app.state.scan_service)
            workers.append(worker)
            worker.start()
        try:
            assert started.wait(5)
            assert store.get_job(job.id).status is ScanStatus.CLONING
            release.set()
            deadline = time.monotonic() + 5
            while store.get_job(job.id).status is not ScanStatus.COMPLETED:
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert len(calls) == 1
            assert a.get(f"/api/scans/{job.id}/report").status_code == 200
        finally:
            release.set()
            for worker in workers:
                worker.stop()
