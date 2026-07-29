from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from mxready.errors import MxReadyError
from mxready.models import ScanReport, VerificationRun, VerificationStatus

MAX_VERIFICATION_UPLOAD_BYTES = 1_048_576
MAX_FUTURE_SKEW = timedelta(minutes=10)
VERIFICATION_MAX_AGE = timedelta(days=30)
_REQUIRED_HARDWARE_CHECKS = frozenset({"mx-smi", "pytorch-device"})


@dataclass(frozen=True, slots=True)
class ValidatedVerification:
    run: VerificationRun
    status: VerificationStatus


def validate_verification_upload(
    report: ScanReport,
    payload: bytes,
    *,
    now: datetime,
) -> ValidatedVerification:
    if len(payload) > MAX_VERIFICATION_UPLOAD_BYTES:
        raise MxReadyError(
            "UPLOAD_TOO_LARGE",
            "Verification results must not exceed 1 MiB.",
        )
    try:
        run = VerificationRun.model_validate_json(payload)
    except (ValidationError, ValueError, UnicodeError) as error:
        raise _invalid_schema() from error

    if run.scan_id != report.scan_id:
        raise MxReadyError(
            "VERIFICATION_SCHEMA_INVALID",
            "The verification result belongs to a different scan.",
        )
    if run.repository_commit != report.repository.commit:
        raise MxReadyError(
            "VERIFICATION_COMMIT_MISMATCH",
            "The verification result was produced for a different commit.",
        )

    now_utc = _require_aware(now, "current time").astimezone(UTC)
    started_at = _require_aware(run.started_at, "start time").astimezone(UTC)
    finished_at = _require_aware(run.finished_at, "finish time").astimezone(UTC)
    if finished_at < started_at:
        raise _invalid_schema()
    if finished_at > now_utc + MAX_FUTURE_SKEW:
        raise _invalid_schema()

    if now_utc - finished_at > VERIFICATION_MAX_AGE:
        status = VerificationStatus.STALE
    elif run.overall_status == "passed" and _hardware_checks_passed(run):
        status = VerificationStatus.VERIFIED
    else:
        status = VerificationStatus.FAILED
    return ValidatedVerification(run=run, status=status)


def _hardware_checks_passed(run: VerificationRun) -> bool:
    passed = {check.id for check in run.checks if check.status == "passed"}
    return passed >= _REQUIRED_HARDWARE_CHECKS


def _require_aware(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MxReadyError(
            "VERIFICATION_SCHEMA_INVALID",
            f"The verification {label} must include a UTC offset.",
        )
    return value


def _invalid_schema() -> MxReadyError:
    return MxReadyError(
        "VERIFICATION_SCHEMA_INVALID",
        "The verification result does not match schema version 1.0.",
    )
