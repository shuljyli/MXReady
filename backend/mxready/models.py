from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScanStatus(StrEnum):
    QUEUED = "queued"
    CLONING = "cloning"
    INDEXING = "indexing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class StaticStatus(StrEnum):
    PASSED = "passed"
    WARNINGS = "warnings"
    BLOCKED = "blocked"
    FAILED = "failed"


class VerificationStatus(StrEnum):
    NOT_RUN = "not-run"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"


class BadgeStatus(StrEnum):
    STATIC_PASSED = "static-passed"
    WARNINGS = "warnings"
    BLOCKED = "blocked"
    VERIFIED = "verified"
    VERIFICATION_STALE = "verification-stale"
    SCAN_FAILED = "scan-failed"


class ScanJob(StrictModel):
    id: UUID
    repo_url: str
    requested_ref: str | None = None
    resolved_commit: str | None = None
    status: ScanStatus = ScanStatus.QUEUED
    stage_message: str
    created_at: datetime
    updated_at: datetime
    failure_code: str | None = None
    failure_message: str | None = None


class SourceReference(StrictModel):
    title: str
    url: str


class RepositorySnapshot(StrictModel):
    provider: Literal["github", "gitee"]
    owner: str
    name: str
    url: str
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")


class Finding(StrictModel):
    rule_id: str
    rule_version: int = Field(ge=1)
    severity: Severity
    category: str
    title: str
    relative_path: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    evidence: str
    message: str
    recommendation: str
    references: list[SourceReference]

    @model_validator(mode="after")
    def line_range_is_ordered(self) -> "Finding":
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class ScanSummary(StrictModel):
    total_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)


class MigrationChecklistItem(StrictModel):
    rule_id: str
    title: str
    action: str
    affected_files: list[str]
    completed: bool = False


class AnalysisWarning(StrictModel):
    code: str
    relative_path: str | None = None
    message: str


class ScanReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    scan_id: UUID
    repository: RepositorySnapshot
    tool_version: str
    ruleset_version: str
    scanned_at: datetime
    summary: ScanSummary
    findings: list[Finding]
    migration_checklist: list[MigrationChecklistItem]
    analysis_warnings: list[AnalysisWarning]
    static_status: StaticStatus
    verification_status: VerificationStatus


class VerificationCheck(StrictModel):
    id: str
    command: list[str]
    status: Literal["passed", "failed", "unavailable"]
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = Field(ge=0)


class VerificationCommand(StrictModel):
    id: str
    command: list[str]
    timeout_seconds: int = Field(ge=1, le=600)
    status: Literal["passed", "failed", "timeout", "cancelled"]
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = Field(ge=0)


class VerificationRun(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    scan_id: UUID
    repository_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    runner_version: str
    environment_fingerprint: str
    checks: list[VerificationCheck]
    commands: list[VerificationCommand]
    started_at: datetime
    finished_at: datetime
    overall_status: Literal["passed", "failed", "cancelled"]


def summarize_findings(findings: list[Finding]) -> ScanSummary:
    return ScanSummary(
        total_count=len(findings),
        blocker_count=sum(item.severity is Severity.BLOCKER for item in findings),
        warning_count=sum(item.severity is Severity.WARNING for item in findings),
        info_count=sum(item.severity is Severity.INFO for item in findings),
    )


def calculate_static_status(summary: ScanSummary) -> StaticStatus:
    if summary.blocker_count:
        return StaticStatus.BLOCKED
    if summary.warning_count:
        return StaticStatus.WARNINGS
    return StaticStatus.PASSED


def calculate_badge_status(report: ScanReport) -> BadgeStatus:
    if report.static_status is StaticStatus.FAILED:
        return BadgeStatus.SCAN_FAILED
    if report.static_status is StaticStatus.BLOCKED:
        return BadgeStatus.BLOCKED
    if report.verification_status is VerificationStatus.VERIFIED:
        return BadgeStatus.VERIFIED
    if report.verification_status is VerificationStatus.STALE:
        return BadgeStatus.VERIFICATION_STALE
    if report.static_status is StaticStatus.WARNINGS:
        return BadgeStatus.WARNINGS
    return BadgeStatus.STATIC_PASSED
