from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from mxready import __version__
from mxready.models import (
    AnalysisWarning,
    Finding,
    MigrationChecklistItem,
    RepositorySnapshot,
    ScanReport,
    ScanStatus,
    Severity,
    VerificationStatus,
    calculate_static_status,
    summarize_findings,
)
from mxready.repository.identity import parse_repository_url
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import RuleCatalog


class ScanAnalyzer:
    def __init__(
        self,
        catalog: RuleCatalog,
        providers: Mapping[str, str] | None = None,
    ) -> None:
        self.catalog = catalog
        self.providers = providers

    def analyze(
        self,
        repository_root: Path,
        *,
        repository_url: str,
        commit: str,
        scan_id: UUID,
        stage_callback: Callable[[ScanStatus], None],
    ) -> ScanReport:
        stage_callback(ScanStatus.INDEXING)
        index = build_file_index(repository_root)

        stage_callback(ScanStatus.ANALYZING)
        facts = extract_project_facts(index)
        findings = _aggregate_findings(evaluate_rules(self.catalog, index, facts))
        summary = summarize_findings(findings)
        identity = parse_repository_url(repository_url, self.providers)

        return ScanReport(
            scan_id=scan_id,
            repository=RepositorySnapshot(
                provider=identity.provider,
                owner=identity.owner,
                name=identity.name,
                url=identity.clone_url.removesuffix(".git"),
                commit=commit,
            ),
            tool_version=__version__,
            ruleset_version=self.catalog.version,
            scanned_at=datetime.now(UTC),
            summary=summary,
            findings=findings,
            migration_checklist=_build_migration_checklist(findings),
            analysis_warnings=[
                AnalysisWarning(
                    code=warning.code,
                    relative_path=warning.relative_path,
                    message=warning.message,
                )
                for warning in index.warnings
            ],
            static_status=calculate_static_status(summary),
            verification_status=VerificationStatus.NOT_RUN,
        )


def _aggregate_findings(findings: list[Finding]) -> list[Finding]:
    """同一规则在同一文件多次命中时合并为一条并累计命中数，降低报告噪音。"""
    grouped: dict[tuple[str, str], Finding] = {}
    for finding in findings:
        key = (finding.rule_id, finding.relative_path)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = finding
            continue
        grouped[key] = existing.model_copy(
            update={
                "count": existing.count + 1,
                "line_start": min(existing.line_start, finding.line_start),
                "line_end": max(existing.line_end, finding.line_end),
            }
        )
    return list(grouped.values())


def _build_migration_checklist(findings) -> list[MigrationChecklistItem]:
    grouped = {}
    for finding in findings:
        if finding.severity not in {Severity.BLOCKER, Severity.WARNING}:
            continue
        item = grouped.setdefault(
            finding.rule_id,
            {
                "title": finding.title,
                "action": finding.recommendation,
                "files": set(),
            },
        )
        item["files"].add(finding.relative_path)

    return [
        MigrationChecklistItem(
            rule_id=rule_id,
            title=item["title"],
            action=item["action"],
            affected_files=sorted(item["files"]),
        )
        for rule_id, item in grouped.items()
    ]
