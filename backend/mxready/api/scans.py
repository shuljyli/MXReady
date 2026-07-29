from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.responses import Response
from pydantic import Field, HttpUrl

from mxready.models import ScanJob, ScanReport, StrictModel
from mxready.reporting.badge import render_badge
from mxready.reporting.markdown import render_markdown

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


@router.get("/{scan_id}/report.md")
def download_markdown_report(scan_id: UUID, request: Request) -> Response:
    report = request.app.state.scan_service.get_report(scan_id)
    return Response(
        content=render_markdown(report),
        media_type="text/markdown",
        headers=_attachment_headers(report, "md"),
    )


@router.get("/{scan_id}/report.json")
def download_json_report(scan_id: UUID, request: Request) -> Response:
    report = request.app.state.scan_service.get_report(scan_id)
    return Response(
        content=report.model_dump_json(indent=2),
        media_type="application/json",
        headers=_attachment_headers(report, "json"),
    )


@router.get("/{scan_id}/badge.svg")
def get_badge(scan_id: UUID, request: Request) -> Response:
    report = request.app.state.scan_service.get_report(scan_id)
    return Response(
        content=render_badge(report),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _attachment_headers(report: ScanReport, extension: str) -> dict[str, str]:
    safe_repository_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "-",
        report.repository.name,
    ).strip("-_")[:64]
    safe_repository_name = safe_repository_name or "repository"
    filename = f"{safe_repository_name}-{report.repository.commit[:12]}-mxready.{extension}"
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
