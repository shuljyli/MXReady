import pytest
from mxready.errors import MxReadyError
from mxready.models import (
    BadgeStatus,
    Finding,
    Severity,
    StaticStatus,
    VerificationStatus,
    calculate_badge_status,
    calculate_static_status,
    summarize_findings,
)
from pydantic import ValidationError


def make_finding(severity: Severity) -> Finding:
    return Finding(
        rule_id="MXR-CUDA-001",
        rule_version=1,
        severity=severity,
        category="toolchain",
        title="Hard-coded nvcc",
        relative_path="setup.py",
        line_start=12,
        line_end=12,
        evidence="compiler = 'nvcc'",
        message="The build invokes nvcc directly.",
        recommendation="Use a configurable compiler entry point.",
        references=[],
    )


def test_blocker_controls_static_and_badge_status(report_factory):
    finding = make_finding(Severity.BLOCKER)
    summary = summarize_findings([finding])
    report = report_factory(
        findings=[finding],
        summary=summary,
        static_status=calculate_static_status(summary),
    )

    assert summary.model_dump() == {
        "total_count": 1,
        "blocker_count": 1,
        "warning_count": 0,
        "info_count": 0,
    }
    assert report.static_status is StaticStatus.BLOCKED
    assert calculate_badge_status(report) is BadgeStatus.BLOCKED
    assert report.model_dump(mode="json")["schema_version"] == "1.0"


def test_verified_requires_static_pass_and_fresh_success(report_factory):
    report = report_factory(verification_status=VerificationStatus.VERIFIED)

    assert calculate_badge_status(report) is BadgeStatus.VERIFIED


def test_static_blocker_takes_precedence_over_stale_verification(report_factory):
    finding = make_finding(Severity.BLOCKER)
    report = report_factory(
        findings=[finding],
        static_status=StaticStatus.BLOCKED,
        verification_status=VerificationStatus.STALE,
    )

    assert calculate_badge_status(report) is BadgeStatus.BLOCKED


def test_warning_and_info_counts_produce_warning_status():
    summary = summarize_findings(
        [make_finding(Severity.WARNING), make_finding(Severity.INFO)]
    )

    assert summary.total_count == 2
    assert summary.warning_count == 1
    assert summary.info_count == 1
    assert calculate_static_status(summary) is StaticStatus.WARNINGS


def test_domain_models_reject_unknown_fields():
    with pytest.raises(ValidationError):
        Finding(
            rule_id="MXR-CUDA-001",
            rule_version=1,
            severity=Severity.INFO,
            category="toolchain",
            title="CUDA source",
            relative_path="kernel.cu",
            line_start=1,
            line_end=1,
            evidence="#include <cuda.h>",
            message="CUDA source detected.",
            recommendation="Review the source for MXMACA.",
            references=[],
            unexpected=True,
        )


def test_mxready_error_carries_safe_structured_details():
    error = MxReadyError(
        "INVALID_REPOSITORY_URL",
        "The repository URL is invalid.",
        {"field": "repo_url"},
    )

    assert error.code == "INVALID_REPOSITORY_URL"
    assert error.message == "The repository URL is invalid."
    assert error.details == {"field": "repo_url"}
