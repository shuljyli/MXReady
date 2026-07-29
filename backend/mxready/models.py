from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    command: list[str] = Field(min_length=1, max_length=32)
    status: Literal["passed", "failed", "unavailable"]
    return_code: int | None = None
    stdout: str = Field(default="", max_length=16_384)
    stderr: str = Field(default="", max_length=16_384)
    duration_ms: int = Field(ge=0)

    @field_validator("command")
    @classmethod
    def command_arguments_are_bounded(cls, value: list[str]) -> list[str]:
        return _validate_result_command(value)

    @model_validator(mode="after")
    def status_matches_return_code(self) -> "VerificationCheck":
        if self.status == "passed" and self.return_code != 0:
            raise ValueError("passed checks must have return_code 0")
        if self.status == "failed" and self.return_code == 0:
            raise ValueError("failed checks cannot have return_code 0")
        if self.status == "unavailable" and self.return_code is not None:
            raise ValueError("unavailable checks cannot have a return code")
        return self


class VerificationCommand(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    command: list[str] = Field(min_length=1, max_length=32)
    timeout_seconds: int = Field(ge=1, le=600)
    status: Literal["passed", "failed", "timeout", "cancelled"]
    return_code: int | None = None
    stdout: str = Field(default="", max_length=16_384)
    stderr: str = Field(default="", max_length=16_384)
    duration_ms: int = Field(ge=0)

    @field_validator("command")
    @classmethod
    def command_arguments_are_bounded(cls, value: list[str]) -> list[str]:
        return _validate_result_command(value)

    @model_validator(mode="after")
    def status_matches_return_code(self) -> "VerificationCommand":
        if self.status == "passed" and self.return_code != 0:
            raise ValueError("passed commands must have return_code 0")
        if self.status == "failed" and self.return_code == 0:
            raise ValueError("failed commands cannot have return_code 0")
        if self.status in {"timeout", "cancelled"} and self.return_code is not None:
            raise ValueError("timed out or cancelled commands cannot have a return code")
        return self


class VerificationRun(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    scan_id: UUID
    repository_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    runner_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    environment_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: list[VerificationCheck] = Field(max_length=64)
    commands: list[VerificationCommand] = Field(max_length=64)
    started_at: datetime
    finished_at: datetime
    overall_status: Literal["passed", "failed", "cancelled"]

    @model_validator(mode="after")
    def result_is_semantically_consistent(self) -> "VerificationRun":
        identifiers = [
            item.id
            for item in [
                *self.checks,
                *self.commands,
            ]
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("verification result ids must be unique")
        if self.overall_status == "passed" and any(
            item.status != "passed" for item in self.checks
        ):
            raise ValueError("passed results cannot contain failed environment checks")
        if self.overall_status == "passed" and any(
            item.status != "passed" for item in self.commands
        ):
            raise ValueError("passed results cannot contain failed commands")
        return self


def _validate_result_command(value: list[str]) -> list[str]:
    if any(
        not argument or len(argument) > 4_096 or any(ord(character) < 32 for character in argument)
        for argument in value
    ):
        raise ValueError("command arguments must be bounded printable strings")
    return value


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
