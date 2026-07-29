from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import ScanJob, ScanReport, ScanStatus
from mxready.repository.git_client import GitClient
from mxready.repository.identity import parse_repository_url, validate_git_ref
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.storage import SQLiteStore

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
    ) -> None:
        self.store = store
        self.git_client = git_client
        self.analyzer = analyzer
        self.settings = settings

    def create_scan(
        self,
        repo_url: str,
        requested_ref: str | None,
    ) -> ScanJob:
        identity = parse_repository_url(repo_url)
        reference = validate_git_ref(requested_ref)
        canonical_url = identity.clone_url.removesuffix(".git")
        return self.store.create_job(canonical_url, reference)

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
        return report

    def run_scan(self, scan_id: UUID) -> None:
        job = self.get_scan(scan_id)
        if job.status is not ScanStatus.QUEUED:
            return

        try:
            self.store.update_job(
                scan_id,
                status=ScanStatus.CLONING,
                stage_message=_STAGE_MESSAGES[ScanStatus.CLONING],
            )
            identity = parse_repository_url(job.repo_url)

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

                def persist_stage(status: ScanStatus) -> None:
                    self.store.update_job(
                        scan_id,
                        status=status,
                        stage_message=_STAGE_MESSAGES[status],
                        resolved_commit=commit,
                    )

                report = self.analyzer.analyze(
                    repository_root,
                    repository_url=job.repo_url,
                    commit=commit,
                    scan_id=scan_id,
                    stage_callback=persist_stage,
                )
                self.store.save_report(report)

            self.store.update_job(
                scan_id,
                status=ScanStatus.COMPLETED,
                stage_message=_STAGE_MESSAGES[ScanStatus.COMPLETED],
                resolved_commit=commit,
            )
        except MxReadyError as error:
            self._mark_failed(scan_id, error.code, error.message)
        except Exception:
            logger.exception(
                "Unexpected scan failure for scan_id=%s",
                scan_id,
            )
            self._mark_failed(
                scan_id,
                "SCAN_INTERNAL_ERROR",
                "The scan failed unexpectedly. Start a new scan and try again.",
            )

    def _mark_failed(
        self,
        scan_id: UUID,
        code: str,
        message: str,
    ) -> None:
        self.store.update_job(
            scan_id,
            status=ScanStatus.FAILED,
            stage_message=_STAGE_MESSAGES[ScanStatus.FAILED],
            failure_code=code,
            failure_message=message,
        )
