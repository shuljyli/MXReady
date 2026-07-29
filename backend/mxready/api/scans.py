from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, status
from pydantic import Field, HttpUrl

from mxready.models import ScanJob, ScanReport, StrictModel

router = APIRouter(prefix="/scans", tags=["scans"])


class CreateScanRequest(StrictModel):
    repo_url: HttpUrl
    ref: str | None = Field(default=None, max_length=200)


@router.post("", response_model=ScanJob, status_code=status.HTTP_202_ACCEPTED)
def create_scan(
    payload: CreateScanRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> ScanJob:
    service = request.app.state.scan_service
    job = service.create_scan(str(payload.repo_url), payload.ref)
    background_tasks.add_task(service.run_scan, job.id)
    return job


@router.get("/{scan_id}", response_model=ScanJob)
def get_scan(scan_id: UUID, request: Request) -> ScanJob:
    return request.app.state.scan_service.get_scan(scan_id)


@router.get("/{scan_id}/report", response_model=ScanReport)
def get_report(scan_id: UUID, request: Request) -> ScanReport:
    return request.app.state.scan_service.get_report(scan_id)
