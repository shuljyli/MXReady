import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from mxready.errors import MxReadyError
from mxready.models import (
    FindingReview,
    FindingReviewInput,
    FindingReviewPage,
    ScanJob,
    ScanPage,
    ScanReport,
    ScanStatus,
    VerificationRun,
)

# 顺序迁移列表：索引 i 对应 user_version = i + 1。新增表结构变更时在末尾追加，
# initialize() 会从当前版本顺序执行到最新版本。
_MIGRATIONS: list[str] = [
    # v1：初始表
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
    """,
    "ALTER TABLE scan_jobs ADD COLUMN worker_token TEXT",
    "ALTER TABLE scan_jobs ADD COLUMN lease_expires_at TEXT",
    "CREATE INDEX IF NOT EXISTS scan_jobs_status_created ON scan_jobs(status, created_at)",
    "CREATE INDEX IF NOT EXISTS scan_jobs_updated ON scan_jobs(updated_at)",
    """CREATE TABLE verification_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id TEXT NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
        uploaded_at TEXT,
        verification_json TEXT NOT NULL
    )""",
    "CREATE INDEX verification_runs_scan ON verification_runs(scan_id, id DESC)",
    """INSERT INTO verification_runs(scan_id, uploaded_at, verification_json)
        SELECT id, NULL, verification_json FROM scan_jobs
        WHERE verification_json IS NOT NULL""",
    """CREATE TABLE checklist_progress (
        scan_id TEXT NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
        rule_id TEXT NOT NULL,
        completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
        PRIMARY KEY (scan_id, rule_id)
    )""",
    """CREATE TABLE finding_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id TEXT NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
        rule_id TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('confirmed', 'false-positive', 'deferred')),
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX finding_reviews_lookup "
    "ON finding_reviews(scan_id, rule_id, relative_path, id DESC)",
]


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
            connection.execute("BEGIN IMMEDIATE")
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            for version in range(current, len(_MIGRATIONS)):
                connection.execute(_MIGRATIONS[version])
                connection.execute(f"PRAGMA user_version = {version + 1}")

    def create_job(
        self,
        repo_url: str,
        requested_ref: str | None,
        *,
        max_active: int = 0,
    ) -> ScanJob:
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
            if max_active > 0:
                connection.execute("BEGIN IMMEDIATE")
                active = self._count_active_jobs(connection)
                if active >= max_active:
                    raise MxReadyError(
                        "SCAN_LIMIT_REACHED",
                        "并发扫描数量已达上限，请稍后再试。",
                        {"active": str(active), "limit": str(max_active)},
                    )
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

    def list_jobs(
        self,
        *,
        query: str = "",
        status: ScanStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ScanPage:
        # instr treats %, _ and quote characters literally; all values are bound.
        where = "instr(lower(repo_url), lower(?)) > 0 AND (? IS NULL OR status = ?)"
        parameters = (query, status, status)
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute(
                f"SELECT COUNT(*) FROM scan_jobs WHERE {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT id, repo_url, requested_ref, resolved_commit, status, stage_message, "
                "created_at, updated_at, failure_code, failure_message FROM scan_jobs "
                f"WHERE {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        return ScanPage(
            items=[self._job_from_row(row) for row in rows], total=total, limit=limit, offset=offset
        )

    def update_job(
        self,
        scan_id: UUID,
        *,
        status: ScanStatus,
        stage_message: str,
        resolved_commit: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        worker_token: str | None = None,
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
                WHERE id = ? AND (? IS NULL OR
                    (worker_token = ? AND lease_expires_at > ?))
                """,
                (
                    updated.resolved_commit,
                    updated.status.value,
                    updated.stage_message,
                    updated.updated_at.isoformat(),
                    updated.failure_code,
                    updated.failure_message,
                    str(scan_id),
                    worker_token,
                    worker_token,
                    datetime.now(UTC).isoformat(),
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise MxReadyError("SCAN_LEASE_LOST", "The scan execution lease has expired.")
            if status in {ScanStatus.COMPLETED, ScanStatus.FAILED}:
                connection.execute(
                    "UPDATE scan_jobs SET worker_token = NULL, lease_expires_at = NULL "
                    "WHERE id = ?",
                    (str(scan_id),),
                )
        return updated

    def recover_expired_jobs(self, *, now: datetime | None = None) -> None:
        """Fail abandoned executions only; queued and live leased jobs survive startup."""
        timestamp = (now or datetime.now(UTC)).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE scan_jobs
                SET status = ?, stage_message = ?, updated_at = ?,
                    failure_code = ?, failure_message = ?,
                    worker_token = NULL, lease_expires_at = NULL
                WHERE status IN (?, ?, ?) AND
                    (lease_expires_at IS NULL OR lease_expires_at <= ?)
                """,
                (
                    ScanStatus.FAILED.value,
                    "Scan interrupted",
                    timestamp,
                    "SCAN_INTERRUPTED",
                    ("The MXReady service restarted before this scan completed. Start a new scan."),
                    ScanStatus.CLONING.value,
                    ScanStatus.INDEXING.value,
                    ScanStatus.ANALYZING.value,
                    timestamp,
                ),
            )

    def queued_job_ids(self, limit: int = 1) -> list[UUID]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM scan_jobs WHERE status = ? ORDER BY created_at, id LIMIT ?",
                (ScanStatus.QUEUED.value, limit),
            ).fetchall()
        return [UUID(row["id"]) for row in rows]

    def claim_job(self, scan_id: UUID, token: str, *, lease_seconds: int) -> bool:
        now = datetime.now(UTC)
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE scan_jobs SET worker_token = ?, lease_expires_at = ?,
                   status = ?, stage_message = ?, updated_at = ?
                   WHERE id = ? AND status = ?""",
                (
                    token,
                    (now + timedelta(seconds=lease_seconds)).isoformat(),
                    ScanStatus.CLONING.value,
                    "正在安全获取仓库",
                    now.isoformat(),
                    str(scan_id),
                    ScanStatus.QUEUED.value,
                ),
            )
        return cursor.rowcount == 1

    def renew_lease(self, scan_id: UUID, token: str, *, lease_seconds: int) -> bool:
        now = datetime.now(UTC)
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE scan_jobs SET lease_expires_at = ?
                   WHERE id = ? AND worker_token = ? AND lease_expires_at > ?
                   AND status IN (?, ?, ?)""",
                (
                    (now + timedelta(seconds=lease_seconds)).isoformat(),
                    str(scan_id),
                    token,
                    now.isoformat(),
                    ScanStatus.CLONING.value,
                    ScanStatus.INDEXING.value,
                    ScanStatus.ANALYZING.value,
                ),
            )
        return cursor.rowcount == 1

    def count_active_jobs(self) -> int:
        """统计排队与执行中的扫描任务数。"""
        with self._connect() as connection:
            return self._count_active_jobs(connection)

    @staticmethod
    def _count_active_jobs(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            """
            SELECT COUNT(*) FROM scan_jobs
            WHERE status IN (?, ?, ?, ?)
            """,
            (
                ScanStatus.QUEUED.value,
                ScanStatus.CLONING.value,
                ScanStatus.INDEXING.value,
                ScanStatus.ANALYZING.value,
            ),
        ).fetchone()
        return int(row[0])

    def prune_old_scans(self, days: int) -> int:
        """删除超过 `days` 天未更新的扫描记录，返回删除条数。"""
        if days <= 0:
            return 0
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM scan_jobs WHERE updated_at < ? AND status IN (?, ?)",
                (cutoff, ScanStatus.COMPLETED.value, ScanStatus.FAILED.value),
            )
        return cursor.rowcount

    def backup(self, destination: Path) -> None:
        """使用 SQLite 在线备份 API 将数据库备份到 `destination`。"""
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path, timeout=5)
        target = sqlite3.connect(destination)
        try:
            with target:
                source.backup(target)
        finally:
            target.close()
            source.close()

    def save_report(self, report: ScanReport, *, worker_token: str | None = None) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE scan_jobs SET report_json = ?, updated_at = ? WHERE id = ?
                   AND (? IS NULL OR (worker_token = ? AND lease_expires_at > ?))""",
                (
                    report.model_dump_json(),
                    datetime.now(UTC).isoformat(),
                    str(report.scan_id),
                    worker_token,
                    worker_token,
                    datetime.now(UTC).isoformat(),
                ),
            )
        if cursor.rowcount == 0 and worker_token is not None:
            raise MxReadyError("SCAN_LEASE_LOST", "The scan execution lease has expired.")
        self._ensure_updated(cursor.rowcount, report.scan_id)

    def get_report(self, scan_id: UUID) -> ScanReport | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM scan_jobs WHERE id = ?",
                (str(scan_id),),
            ).fetchone()
            progress = connection.execute(
                "SELECT rule_id, completed FROM checklist_progress WHERE scan_id = ?",
                (str(scan_id),),
            ).fetchall()
        if row is None or row["report_json"] is None:
            return None
        report = ScanReport.model_validate_json(row["report_json"])
        saved = {item["rule_id"]: bool(item["completed"]) for item in progress}
        return report.model_copy(
            update={
                "migration_checklist": [
                    item.model_copy(update={"completed": saved.get(item.rule_id, item.completed)})
                    for item in report.migration_checklist
                ]
            }
        )

    def append_review(self, scan_id: UUID, payload: FindingReviewInput) -> FindingReview:
        now = datetime.now(UTC)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO finding_reviews(scan_id, rule_id, relative_path, "
                "status, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(scan_id),
                    payload.rule_id,
                    payload.relative_path,
                    payload.status,
                    payload.reason,
                    now.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return FindingReview(**payload.model_dump(), id=cursor.lastrowid, created_at=now)

    def review_history(
        self, scan_id: UUID, rule_id: str, relative_path: str, *, limit: int, offset: int
    ) -> FindingReviewPage:
        args = (str(scan_id), rule_id, relative_path)
        where = " WHERE scan_id = ? AND rule_id = ? AND relative_path = ?"
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM finding_reviews" + where, args
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT id, rule_id, relative_path, status, reason, created_at FROM finding_reviews"
                + where
                + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (*args, limit, offset),
            ).fetchall()
        return FindingReviewPage(
            items=[FindingReview.model_validate(dict(row)) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def set_checklist_item(self, scan_id: UUID, rule_id: str, completed: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO checklist_progress(scan_id, rule_id, completed) VALUES (?, ?, ?) "
                "ON CONFLICT(scan_id, rule_id) DO UPDATE SET completed = excluded.completed",
                (str(scan_id), rule_id, int(completed)),
            )

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

    def save_verification_and_report(
        self,
        scan_id: UUID,
        run: VerificationRun,
        report: ScanReport,
    ) -> None:
        if report.scan_id != scan_id or run.scan_id != scan_id:
            raise ValueError("verification, report, and scan ids must match")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE scan_jobs
                SET verification_json = ?, report_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    run.model_dump_json(),
                    report.model_dump_json(),
                    datetime.now(UTC).isoformat(),
                    str(scan_id),
                ),
            )
            self._ensure_updated(cursor.rowcount, scan_id)
            connection.execute(
                "INSERT INTO verification_runs(scan_id, uploaded_at, verification_json) "
                "VALUES (?, ?, ?)",
                (str(scan_id), datetime.now(UTC).isoformat(), run.model_dump_json()),
            )

    def verification_history(
        self,
        scan_id: UUID,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[tuple[int, datetime | None, VerificationRun]], int, int | None]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            count, latest = connection.execute(
                "SELECT COUNT(*), MAX(id) FROM verification_runs WHERE scan_id = ?",
                (str(scan_id),),
            ).fetchone()
            rows = connection.execute(
                "SELECT * FROM verification_runs WHERE scan_id = ? ORDER BY id DESC "
                "LIMIT ? OFFSET ?",
                (str(scan_id), limit, offset),
            ).fetchall()
        return (
            [
                (
                    row["id"],
                    datetime.fromisoformat(row["uploaded_at"]) if row["uploaded_at"] else None,
                    VerificationRun.model_validate_json(row["verification_json"]),
                )
                for row in rows
            ],
            count,
            latest,
        )

    def verification_detail(
        self,
        scan_id: UUID,
        run_id: int,
    ) -> tuple[datetime | None, VerificationRun, bool] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT *, id = (SELECT MAX(id) FROM verification_runs WHERE scan_id = ?) "
                "AS is_latest FROM verification_runs WHERE scan_id = ? AND id = ?",
                (str(scan_id), str(scan_id), run_id),
            ).fetchone()
        if row is None:
            return None
        return (
            datetime.fromisoformat(row["uploaded_at"]) if row["uploaded_at"] else None,
            VerificationRun.model_validate_json(row["verification_json"]),
            bool(row["is_latest"]),
        )

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
