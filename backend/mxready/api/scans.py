from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.responses import Response
from pydantic import Field, HttpUrl

from mxready.errors import MxReadyError
from mxready.models import ScanJob, ScanReport, StrictModel
from mxready.reporting.badge import render_badge
from mxready.reporting.markdown import render_markdown
from mxready.verification.bundle import build_verification_bundle
from mxready.verification.validation import MAX_VERIFICATION_UPLOAD_BYTES

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


@router.get("/{scan_id}/verification-bundle")
def download_verification_bundle(scan_id: UUID, request: Request) -> Response:
    report = request.app.state.scan_service.get_report(scan_id)
    return Response(
        content=build_verification_bundle(report),
        media_type="application/zip",
        headers=_attachment_headers(
            report,
            "zip",
            label="mxready-verification",
        ),
    )


@router.post("/{scan_id}/verification-runs", response_model=ScanReport)
async def upload_verification_run(
    scan_id: UUID,
    request: Request,
) -> ScanReport:
    content_type = request.headers.get("content-type", "").partition(";")[0].strip().casefold()
    if content_type != "application/json":
        raise MxReadyError(
            "VERIFICATION_SCHEMA_INVALID",
            "Verification results must use application/json.",
        )
    payload = await _read_limited_body(request)
    return request.app.state.scan_service.attach_verification(scan_id, payload)


async def _read_limited_body(request: Request) -> bytes:
    declared_size = request.headers.get("content-length")
    if declared_size is not None:
        try:
            if int(declared_size) > MAX_VERIFICATION_UPLOAD_BYTES:
                raise MxReadyError(
                    "UPLOAD_TOO_LARGE",
                    "Verification results must not exceed 1 MiB.",
                )
        except ValueError:
            pass

    body = bytearray()
    async for chunk in request.stream():
        remaining = MAX_VERIFICATION_UPLOAD_BYTES + 1 - len(body)
        body.extend(chunk[: max(0, remaining)])
        if len(body) > MAX_VERIFICATION_UPLOAD_BYTES or len(chunk) > remaining:
            raise MxReadyError(
                "UPLOAD_TOO_LARGE",
                "Verification results must not exceed 1 MiB.",
            )
    return bytes(body)


def _attachment_headers(
    report: ScanReport,
    extension: str,
    *,
    label: str = "mxready",
) -> dict[str, str]:
    safe_repository_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "-",
        report.repository.name,
    ).strip("-_")[:64]
    safe_repository_name = safe_repository_name or "repository"
    filename = f"{safe_repository_name}-{report.repository.commit[:12]}-{label}.{extension}"
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
