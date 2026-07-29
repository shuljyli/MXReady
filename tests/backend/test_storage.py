from datetime import UTC, datetime, timedelta
from uuid import uuid4

from mxready.models import (
    ScanStatus,
    VerificationRun,
)
from mxready.storage import SQLiteStore


def test_scan_job_survives_store_reopen(tmp_path):
    database = tmp_path / "mxready.db"
    first = SQLiteStore(database)
    first.initialize()
    created = first.create_job("https://github.com/pytorch/extension-cpp", None)
    first.update_job(
        created.id,
        status=ScanStatus.CLONING,
        stage_message="Cloning repository",
    )

    reopened = SQLiteStore(database)
    reopened.initialize()
    loaded = reopened.get_job(created.id)

    assert loaded is not None
    assert loaded.status is ScanStatus.CLONING
    assert loaded.repo_url == "https://github.com/pytorch/extension-cpp"


def test_initialize_marks_interrupted_jobs_failed(tmp_path):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://gitee.com/example/project", None)

    store.mark_interrupted_jobs_failed()

    loaded = store.get_job(job.id)
    assert loaded is not None
    assert loaded.failure_code == "SCAN_INTERRUPTED"
    assert loaded.status is ScanStatus.FAILED
    assert "restarted" in loaded.failure_message.lower()


def test_report_round_trips_as_versioned_json(tmp_path, report_factory):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://github.com/example/project", "main")
    report = report_factory(scan_id=job.id)

    store.save_report(report)

    assert store.get_report(job.id) == report


def test_verification_round_trips_without_global_connection(tmp_path):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://github.com/example/project", None)
    started = datetime.now(UTC)
    run = VerificationRun(
        scan_id=job.id,
        repository_commit="a" * 40,
        runner_version="0.1.0",
        environment_fingerprint=f"sha256:{'f' * 64}",
        checks=[],
        commands=[],
        started_at=started,
        finished_at=started + timedelta(seconds=1),
        overall_status="passed",
    )

    store.save_verification(job.id, run)

    reopened = SQLiteStore(tmp_path / "mxready.db")
    assert reopened.get_verification(job.id) == run
    assert reopened.get_job(uuid4()) is None
