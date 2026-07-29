from datetime import UTC, datetime
from uuid import uuid4

import pytest
from mxready.models import (
    RepositorySnapshot,
    ScanReport,
    StaticStatus,
    VerificationStatus,
    summarize_findings,
)


@pytest.fixture
def report_factory():
    def factory(
        *,
        scan_id=None,
        commit="a" * 40,
        repository_name="project",
        findings=None,
        summary=None,
        static_status=StaticStatus.PASSED,
        verification_status=VerificationStatus.NOT_RUN,
    ):
        resolved_findings = list(findings or [])
        return ScanReport(
            schema_version="1.0",
            scan_id=scan_id or uuid4(),
            repository=RepositorySnapshot(
                provider="github",
                owner="example",
                name=repository_name,
                url=f"https://github.com/example/{repository_name}",
                commit=commit,
            ),
            tool_version="0.1.0",
            ruleset_version="1",
            scanned_at=datetime(2026, 7, 29, tzinfo=UTC),
            summary=summary or summarize_findings(resolved_findings),
            findings=resolved_findings,
            migration_checklist=[],
            analysis_warnings=[],
            static_status=static_status,
            verification_status=verification_status,
        )

    return factory

