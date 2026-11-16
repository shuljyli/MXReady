"""Conservative CI baseline policy: never silently compare different analyzers."""

from dataclasses import dataclass
from typing import Literal

from mxready.models import Finding, ScanReport, Severity
from mxready.reporting.source import describe_source


def normalize_repository(url: str) -> str:
    return url.rstrip("/").removesuffix(".git").lower()


@dataclass(frozen=True)
class FindingChange:
    before: Finding
    after: Finding
    severity_changed: bool
    count_changed: bool


@dataclass(frozen=True)
class ConditionDifference:
    field: str
    before: object
    after: object


@dataclass(frozen=True)
class ReportDifference:
    added: tuple[Finding, ...]
    removed: tuple[Finding, ...]
    retained: tuple[Finding, ...]
    changes: tuple[FindingChange, ...]
    condition_differences: tuple[ConditionDifference, ...]
    conditions_status: Literal["same", "different", "unknown"]
    source_warnings: tuple[str, ...]
    condition_warnings: tuple[str, ...]


def compare_reports(baseline: ScanReport, current: ScanReport) -> ReportDifference:
    """Browse changes across conditions, independently of the strict CI policy below."""
    if normalize_repository(baseline.repository.url) != normalize_repository(
        current.repository.url
    ):
        raise ValueError("只能对比同一仓库的报告。")
    if baseline.scan_id == current.scan_id and baseline != current:
        raise ValueError("相同 scan ID 内容不同：报告身份冲突。")

    def keyed(report: ScanReport) -> dict[tuple[str, str], Finding]:
        result = {}
        for finding in report.findings:
            key = (finding.rule_id, finding.relative_path)
            if key in result:
                raise ValueError(f"重复发现键，报告结构存在歧义: {key}")
            result[key] = finding
        return result

    before, after = keyed(baseline), keyed(current)
    differences = tuple(
        ConditionDifference(field, getattr(baseline, field), getattr(current, field))
        for field in (
            "tool_version",
            "ruleset_digest",
            "ruleset_version",
            "extra_ruleset_version",
            "analysis_config",
        )
        if getattr(baseline, field) != getattr(current, field)
        and not (
            field == "ruleset_digest"
            and (not baseline.ruleset_digest or not current.ruleset_digest)
        )
    )
    missing = not baseline.ruleset_digest or not current.ruleset_digest
    changes = tuple(
        FindingChange(
            before[key],
            item,
            before[key].severity != item.severity,
            before[key].count != item.count,
        )
        for key, item in after.items()
        if key in before
        and (before[key].severity != item.severity or before[key].count != item.count)
    )
    source_warnings = []
    for side, report in (("基线", baseline), ("当前", current)):
        source = describe_source(report)
        if source.label != "干净 Git 提交" or source.warnings:
            source_warnings.append(f"{side}: {source.label}；{source.explanation}")
            source_warnings.extend(f"{side}: {warning}" for warning in source.warnings)
    return ReportDifference(
        tuple(item for key, item in after.items() if key not in before),
        tuple(item for key, item in before.items() if key not in after),
        tuple(item for key, item in after.items() if key in before),
        changes,
        differences,
        "different" if differences else "unknown" if missing else "same",
        tuple(source_warnings),
        ("缺少规则集摘要，无法确认分析条件一致。",) if missing else (),
    )


def new_blockers(baseline: ScanReport, current: ScanReport) -> list[Finding]:
    def normalize(url: str) -> str:
        return url.rstrip("/").removesuffix(".git").lower()

    if normalize(baseline.repository.url) != normalize(current.repository.url):
        raise ValueError("Baseline must describe the same repository")
    fields = (
        "ruleset_digest",
        "ruleset_version",
        "extra_ruleset_version",
        "tool_version",
        "analysis_config",
    )
    if not baseline.ruleset_digest or any(
        getattr(baseline, k) != getattr(current, k) for k in fields
    ):
        raise ValueError(
            "Baseline analysis conditions differ or ruleset digest is missing; regenerate it"
        )
    before = {(f.rule_id, f.relative_path): f for f in baseline.findings}
    result = []
    for finding in current.findings:
        old = before.get((finding.rule_id, finding.relative_path))
        if finding.severity == Severity.BLOCKER and (
            old is None or old.severity != Severity.BLOCKER or finding.count > old.count
        ):
            result.append(finding)
    return result
