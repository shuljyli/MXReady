"""History and user annotations for a single trusted MXReady deployment."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import StrictBool

from mxready.errors import MxReadyError
from mxready.models import (
    ScanPage,
    ScanReport,
    ScanStatus,
    StrictModel,
    VerificationCheck,
    VerificationCommand,
    VerificationDetail,
    VerificationOutput,
    VerificationPage,
    VerificationRun,
    VerificationSummary,
)
from mxready.verification.validation import VERIFICATION_MAX_AGE, verification_status_at
from mxready_runner.redact import sanitize_output

router = APIRouter(prefix="/scans", tags=["workspace"])


class ChecklistUpdate(StrictModel):
    completed: StrictBool


@router.get("", response_model=ScanPage)
def list_scans(
    request: Request,
    q: str = Query(default="", max_length=200),
    status: ScanStatus | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=1_000_000),
) -> ScanPage:
    return request.app.state.store.list_jobs(
        query=q.strip(), status=status, limit=limit, offset=offset
    )


def _summary(
    run_id: int, uploaded: datetime | None, run: VerificationRun, latest: bool
) -> VerificationSummary:
    return VerificationSummary(
        id=run_id,
        uploaded_at=uploaded,
        started_at=run.started_at,
        finished_at=run.finished_at,
        expires_at=run.finished_at + VERIFICATION_MAX_AGE,
        status=verification_status_at(run, now=datetime.now(UTC)),
        overall_status=run.overall_status,
        repository_commit=run.repository_commit,
        environment_fingerprint=run.environment_fingerprint,
        runner_version=run.runner_version,
        check_count=len(run.checks),
        command_count=len(run.commands),
        is_latest=latest,
    )


@router.get("/{scan_id}/verification-runs", response_model=VerificationPage)
def list_verifications(
    scan_id: UUID,
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=1_000_000),
) -> VerificationPage:
    request.app.state.scan_service.get_scan(scan_id)
    rows, total, latest = request.app.state.store.verification_history(
        scan_id, limit=limit, offset=offset
    )
    return VerificationPage(
        items=[_summary(i, uploaded, run, i == latest) for i, uploaded, run in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{scan_id}/verification-runs/{run_id}", response_model=VerificationDetail)
def verification_detail(scan_id: UUID, run_id: int, request: Request) -> VerificationDetail:
    request.app.state.scan_service.get_scan(scan_id)
    record = request.app.state.store.verification_detail(scan_id, run_id)
    if record is None:
        raise MxReadyError("VERIFICATION_NOT_FOUND", "The verification record does not exist.")
    uploaded, run, latest = record

    # Do not expose command arguments (which may contain credentials). Logs remain bounded
    # and are sanitized again at this new read boundary, including legacy records.
    def outputs(
        items: Sequence[VerificationCheck | VerificationCommand],
    ) -> list[VerificationOutput]:
        return [
            VerificationOutput(
                id=item.id,
                status=item.status,
                return_code=item.return_code,
                duration_ms=item.duration_ms,
                stdout=sanitize_output(item.stdout),
                stderr=sanitize_output(item.stderr),
            )
            for item in items
        ]

    return VerificationDetail(
        summary=_summary(run_id, uploaded, run, latest),
        checks=outputs(run.checks),
        commands=outputs(run.commands),
    )


@router.patch("/{scan_id}/checklist/{rule_id}", response_model=ScanReport)
def update_checklist(
    scan_id: UUID, rule_id: str, payload: ChecklistUpdate, request: Request
) -> ScanReport:
    service = request.app.state.scan_service
    report = service.get_report(scan_id)
    if not any(item.rule_id == rule_id for item in report.migration_checklist):
        raise MxReadyError("CHECKLIST_ITEM_NOT_FOUND", "The checklist item does not exist.")
    request.app.state.store.set_checklist_item(scan_id, rule_id, payload.completed)
    return service.get_report(scan_id)
