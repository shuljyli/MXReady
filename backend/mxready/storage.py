import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from mxready.errors import MxReadyError
from mxready.models import (
    ScanJob,
    ScanReport,
    ScanStatus,
    VerificationRun,
)


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_jobs (
                    id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    requested_ref TEXT,
                    resolved_commit TEXT,
                    status TEXT NOT NULL,
                    stage_message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    failure_code TEXT,
                    failure_message TEXT,
                    report_json TEXT,
                    verification_json TEXT
                )
                """
            )

    def create_job(self, repo_url: str, requested_ref: str | None) -> ScanJob:
        now = datetime.now(UTC)
        job = ScanJob(
            id=uuid4(),
            repo_url=repo_url,
            requested_ref=requested_ref,
            status=ScanStatus.QUEUED,
            stage_message="Waiting to start",
            created_at=now,
            updated_at=now,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scan_jobs (
                    id, repo_url, requested_ref, resolved_commit, status,
                    stage_message, created_at, updated_at, failure_code,
                    failure_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.id),
                    job.repo_url,
                    job.requested_ref,
                    job.resolved_commit,
                    job.status.value,
                    job.stage_message,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.failure_code,
                    job.failure_message,
                ),
            )
        return job

    def get_job(self, scan_id: UUID) -> ScanJob | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, repo_url, requested_ref, resolved_commit, status,
                       stage_message, created_at, updated_at, failure_code,
                       failure_message
                FROM scan_jobs
                WHERE id = ?
                """,
                (str(scan_id),),
            ).fetchone()
        if row is None:
            return None
        return self._job_from_row(row)

    def update_job(
        self,
        scan_id: UUID,
        *,
        status: ScanStatus,
        stage_message: str,
        resolved_commit: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> ScanJob:
        current = self.get_job(scan_id)
        if current is None:
            raise MxReadyError(
                "SCAN_NOT_FOUND",
                "The requested scan does not exist.",
                {"scan_id": str(scan_id)},
            )
        updated = current.model_copy(
            update={
                "status": status,
                "stage_message": stage_message,
                "resolved_commit": resolved_commit or current.resolved_commit,
                "failure_code": failure_code,
                "failure_message": failure_message,
                "updated_at": datetime.now(UTC),
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE scan_jobs
                SET resolved_commit = ?, status = ?, stage_message = ?,
                    updated_at = ?, failure_code = ?, failure_message = ?
                WHERE id = ?
                """,
                (
                    updated.resolved_commit,
                    updated.status.value,
                    updated.stage_message,
                    updated.updated_at.isoformat(),
                    updated.failure_code,
                    updated.failure_message,
                    str(scan_id),
                ),
            )
        return updated

    def mark_interrupted_jobs_failed(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE scan_jobs
                SET status = ?, stage_message = ?, updated_at = ?,
                    failure_code = ?, failure_message = ?
                WHERE status IN (?, ?, ?, ?)
                """,
                (
                    ScanStatus.FAILED.value,
                    "Scan interrupted",
                    datetime.now(UTC).isoformat(),
                    "SCAN_INTERRUPTED",
                    (
                        "The MXReady service restarted before this scan completed. "
                        "Start a new scan."
                    ),
                    ScanStatus.QUEUED.value,
                    ScanStatus.CLONING.value,
                    ScanStatus.INDEXING.value,
                    ScanStatus.ANALYZING.value,
                ),
            )

    def save_report(self, report: ScanReport) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE scan_jobs SET report_json = ?, updated_at = ? WHERE id = ?",
                (
                    report.model_dump_json(),
                    datetime.now(UTC).isoformat(),
                    str(report.scan_id),
                ),
            )
        self._ensure_updated(cursor.rowcount, report.scan_id)

    def get_report(self, scan_id: UUID) -> ScanReport | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM scan_jobs WHERE id = ?",
                (str(scan_id),),
            ).fetchone()
        if row is None or row["report_json"] is None:
            return None
        return ScanReport.model_validate_json(row["report_json"])

    def save_verification(self, scan_id: UUID, run: VerificationRun) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE scan_jobs SET verification_json = ?, updated_at = ? WHERE id = ?",
                (
                    run.model_dump_json(),
                    datetime.now(UTC).isoformat(),
                    str(scan_id),
                ),
            )
        self._ensure_updated(cursor.rowcount, scan_id)

    def get_verification(self, scan_id: UUID) -> VerificationRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT verification_json FROM scan_jobs WHERE id = ?",
                (str(scan_id),),
            ).fetchone()
        if row is None or row["verification_json"] is None:
            return None
        return VerificationRun.model_validate_json(row["verification_json"])

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> ScanJob:
        return ScanJob(
            id=UUID(row["id"]),
            repo_url=row["repo_url"],
            requested_ref=row["requested_ref"],
            resolved_commit=row["resolved_commit"],
            status=ScanStatus(row["status"]),
            stage_message=row["stage_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            failure_code=row["failure_code"],
            failure_message=row["failure_message"],
        )

    @staticmethod
    def _ensure_updated(row_count: int, scan_id: UUID) -> None:
        if row_count == 0:
            raise MxReadyError(
                "SCAN_NOT_FOUND",
                "The requested scan does not exist.",
                {"scan_id": str(scan_id)},
            )
