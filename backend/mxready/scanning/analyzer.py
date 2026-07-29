from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from mxready import __version__
from mxready.models import (
    AnalysisWarning,
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
    def __init__(self, catalog: RuleCatalog) -> None:
        self.catalog = catalog

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
        findings = evaluate_rules(self.catalog, index, facts)
        summary = summarize_findings(findings)
        identity = parse_repository_url(repository_url)

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
