from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from mxready.errors import MxReadyError
from mxready.models import VerificationStatus
from mxready.verification.validation import validate_verification_upload


def test_rejects_result_for_a_different_commit(report_factory) -> None:
    report = report_factory(commit="a" * 40)
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit="b" * 40,
        finished_at=datetime.now(UTC),
    )

    with pytest.raises(MxReadyError) as error:
        validate_verification_upload(report, payload, now=datetime.now(UTC))

    assert error.value.code == "VERIFICATION_COMMIT_MISMATCH"


def test_marks_result_older_than_30_days_stale(report_factory) -> None:
    now = datetime.now(UTC)
    report = report_factory()
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now - timedelta(days=31),
    )

    validated = validate_verification_upload(report, payload, now=now)

    assert validated.status is VerificationStatus.STALE


def test_fresh_success_is_verified(report_factory) -> None:
    now = datetime.now(UTC)
    report = report_factory()
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now,
    )

    validated = validate_verification_upload(report, payload, now=now)

    assert validated.status is VerificationStatus.VERIFIED


@pytest.mark.parametrize("overall_status", ["failed", "cancelled"])
def test_fresh_non_success_is_failed(
    report_factory,
    overall_status: str,
) -> None:
    now = datetime.now(UTC)
    report = report_factory()

    validated = validate_verification_upload(
        report,
        make_payload(
            scan_id=report.scan_id,
            repository_commit=report.repository.commit,
            finished_at=now,
            overall_status=overall_status,
        ),
        now=now,
    )

    assert validated.status is VerificationStatus.FAILED


@pytest.mark.parametrize(
    ("payload_mutation", "expected_code"),
    [
        (lambda body: body.update(scan_id=str(uuid4())), "VERIFICATION_SCHEMA_INVALID"),
        (
            lambda body: body.update(finished_at="2999-01-01T00:00:00+00:00"),
            "VERIFICATION_SCHEMA_INVALID",
        ),
        (
            lambda body: body.update(unexpected=True),
            "VERIFICATION_SCHEMA_INVALID",
        ),
        (
            lambda body: body.update(environment_fingerprint="not-a-fingerprint"),
            "VERIFICATION_SCHEMA_INVALID",
        ),
    ],
)
def test_rejects_wrong_scan_future_unknown_or_malformed_results(
    report_factory,
    payload_mutation,
    expected_code: str,
) -> None:
    now = datetime.now(UTC)
    report = report_factory()
    body = make_payload_dict(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now,
    )
    payload_mutation(body)

    with pytest.raises(MxReadyError) as error:
        validate_verification_upload(
            report,
            json.dumps(body).encode(),
            now=now,
        )

    assert error.value.code == expected_code


def test_rejects_payload_over_one_mib(report_factory) -> None:
    with pytest.raises(MxReadyError) as error:
        validate_verification_upload(
            report_factory(),
            b"x" * 1_048_577,
            now=datetime.now(UTC),
        )

    assert error.value.code == "UPLOAD_TOO_LARGE"


def test_rejects_semantically_inconsistent_passed_result(report_factory) -> None:
    now = datetime.now(UTC)
    report = report_factory()
    body = make_payload_dict(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now,
    )
    body["commands"] = [
        {
            "id": "tests",
            "command": ["python", "-m", "pytest"],
            "timeout_seconds": 60,
            "status": "failed",
            "return_code": 1,
            "stdout": "",
            "stderr": "failed",
            "duration_ms": 10,
        }
    ]

    with pytest.raises(MxReadyError) as error:
        validate_verification_upload(
            report,
            json.dumps(body).encode(),
            now=now,
        )

    assert error.value.code == "VERIFICATION_SCHEMA_INVALID"


def make_payload(
    *,
    scan_id,
    repository_commit: str,
    finished_at: datetime,
    overall_status: str = "passed",
) -> bytes:
    return json.dumps(
        make_payload_dict(
            scan_id=scan_id,
            repository_commit=repository_commit,
            finished_at=finished_at,
            overall_status=overall_status,
        )
    ).encode()


def make_payload_dict(
    *,
    scan_id,
    repository_commit: str,
    finished_at: datetime,
    overall_status: str = "passed",
) -> dict:
    started_at = finished_at - timedelta(minutes=1)
    return {
        "schema_version": "1.0",
        "scan_id": str(scan_id),
        "repository_commit": repository_commit,
        "runner_version": "0.1.0",
        "environment_fingerprint": f"sha256:{'f' * 64}",
        "checks": [],
        "commands": [],
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "overall_status": overall_status,
    }
