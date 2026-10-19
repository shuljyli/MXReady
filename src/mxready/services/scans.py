from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from uuid import UUID, uuid4

from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import ScanJob, ScanReport, ScanStatus
from mxready.persistence.sqlite import SQLiteStore
from mxready.repository.git_client import GitClient
from mxready.repository.identity import parse_repository_url, validate_git_ref
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.verification.validation import (
    validate_verification_upload,
    verification_status_at,
)

logger = logging.getLogger(__name__)

_STAGE_MESSAGES = {
    ScanStatus.CLONING: "正在安全获取仓库",
    ScanStatus.INDEXING: "正在建立源码索引",
    ScanStatus.ANALYZING: "正在执行兼容性规则",
    ScanStatus.COMPLETED: "扫描完成",
    ScanStatus.FAILED: "扫描失败",
}


class ScanService:
    def __init__(
        self,
        store: SQLiteStore,
        git_client: GitClient,
        analyzer: ScanAnalyzer,
        settings: Settings,
        providers: Mapping[str, str] | None = None,
    ) -> None:
        self.store = store
        self.git_client = git_client
        self.analyzer = analyzer
        self.settings = settings
        self.providers = providers

    def create_scan(
        self,
        repo_url: str,
        requested_ref: str | None,
    ) -> ScanJob:
        identity = parse_repository_url(repo_url, self.providers)
        reference = validate_git_ref(requested_ref)
        canonical_url = identity.clone_url.removesuffix(".git")
        return self.store.create_job(
            canonical_url,
            reference,
            max_active=self.settings.max_concurrent_scans,
        )

    def get_scan(self, scan_id: UUID) -> ScanJob:
        job = self.store.get_job(scan_id)
        if job is None:
            raise MxReadyError(
                "SCAN_NOT_FOUND",
                "The requested scan does not exist.",
            )
        return job

    def get_report(self, scan_id: UUID) -> ScanReport:
        job = self.get_scan(scan_id)
        if job.status is not ScanStatus.COMPLETED:
            raise MxReadyError(
                "SCAN_NOT_COMPLETED",
                "The requested scan has not completed successfully.",
            )
        report = self.store.get_report(scan_id)
        if report is None:
            raise MxReadyError(
                "SCAN_INTERNAL_ERROR",
                "The completed scan report could not be loaded.",
            )
        run = self.store.get_verification(scan_id)
        if run is not None:
            report = report.model_copy(
                update={
                    "verification_status": verification_status_at(run, now=datetime.now(UTC)),
                }
            )
        return report

    def run_scan(self, scan_id: UUID) -> None:
        job = self.get_scan(scan_id)
        token = str(uuid4())
        if not self.store.claim_job(scan_id, token, lease_seconds=self.settings.task_lease_seconds):
            return
        with self._heartbeat(scan_id, token):
            self._run_claimed_scan(job, token)

    @contextmanager
    def _heartbeat(self, scan_id: UUID, token: str):
        stopped = Event()

        def renew() -> None:
            while not stopped.wait(self.settings.task_lease_seconds / 3):
                try:
                    if not self.store.renew_lease(
                        scan_id,
                        token,
                        lease_seconds=self.settings.task_lease_seconds,
                    ):
                        return
                except Exception:
                    logger.exception("scan lease renewal failed", extra={"scan_id": str(scan_id)})
                    return

        thread = Thread(target=renew, name=f"scan-heartbeat-{scan_id}", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            thread.join()

    def _run_claimed_scan(self, job: ScanJob, token: str) -> None:
        scan_id = job.id

        logger.info("scan started", extra={"scan_id": str(scan_id)})
        try:
            self.store.update_job(
                scan_id,
                status=ScanStatus.CLONING,
                stage_message=_STAGE_MESSAGES[ScanStatus.CLONING],
                worker_token=token,
            )
            identity = parse_repository_url(job.repo_url, self.providers)

            with TemporaryDirectory(
                prefix=f"mxready-{scan_id}-",
                dir=self.settings.temp_dir,
            ) as temporary_directory:
                repository_root = Path(temporary_directory) / "repository"
                commit = self.git_client.clone(
                    identity,
                    job.requested_ref,
                    repository_root,
                )
                logger.info(
                    "repository cloned",
                    extra={"scan_id": str(scan_id), "commit": commit},
                )

                def persist_stage(status: ScanStatus) -> None:
                    self.store.update_job(
                        scan_id,
                        status=status,
                        stage_message=_STAGE_MESSAGES[status],
                        resolved_commit=commit,
                        worker_token=token,
                    )

                report = self.analyzer.analyze(
                    repository_root,
                    repository_url=job.repo_url,
                    commit=commit,
                    scan_id=scan_id,
                    stage_callback=persist_stage,
                )
                self.store.save_report(report, worker_token=token)
                logger.info(
                    "scan analysis completed",
                    extra={"scan_id": str(scan_id)},
                )

            self.store.update_job(
                scan_id,
                status=ScanStatus.COMPLETED,
                stage_message=_STAGE_MESSAGES[ScanStatus.COMPLETED],
                resolved_commit=commit,
                worker_token=token,
            )
        except MxReadyError as error:
            if error.code != "SCAN_LEASE_LOST":
                self._mark_failed(scan_id, error.code, error.message, token)
        except Exception:
            logger.exception(
                "Unexpected scan failure for scan_id=%s",
                scan_id,
            )
            self._mark_failed(
                scan_id,
                "SCAN_INTERNAL_ERROR",
                "The scan failed unexpectedly. Start a new scan and try again.",
                token,
            )

    def attach_verification(
        self,
        scan_id: UUID,
        payload: bytes,
        *,
        now: datetime | None = None,
    ) -> ScanReport:
        report = self.get_report(scan_id)
        validated = validate_verification_upload(
            report,
            payload,
            now=now or datetime.now(UTC),
        )
        updated_report = report.model_copy(update={"verification_status": validated.status})
        self.store.save_verification_and_report(
            scan_id,
            validated.run,
            updated_report,
        )
        return updated_report

    def _mark_failed(
        self,
        scan_id: UUID,
        code: str,
        message: str,
        token: str,
    ) -> None:
        try:
            self.store.update_job(
                scan_id,
                status=ScanStatus.FAILED,
                stage_message=_STAGE_MESSAGES[ScanStatus.FAILED],
                failure_code=code,
                failure_message=message,
                worker_token=token,
            )
        except MxReadyError as error:
            if error.code != "SCAN_LEASE_LOST":
                raise
