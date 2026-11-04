"""Portable SARIF 2.1.0 export of static findings (never hardware certification)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from mxready.models import FindingOccurrence, ScanReport, Severity


def render_sarif(report: ScanReport) -> str:
    rules: dict[str, Any] = {}
    results = []
    levels = {Severity.BLOCKER: "error", Severity.WARNING: "warning", Severity.INFO: "note"}
    for finding in report.findings:
        rules.setdefault(
            finding.rule_id,
            {
                "id": finding.rule_id,
                "shortDescription": {"text": finding.title},
                "help": {"text": finding.recommendation},
                "properties": {"ruleVersion": finding.rule_version},
            },
        )
        occurrences = finding.occurrences or [
            FindingOccurrence(
                line_start=finding.line_start,
                line_end=finding.line_end,
                evidence=finding.evidence,
            )
        ]
        for occurrence in occurrences:
            results.append(
                {
                    "ruleId": finding.rule_id,
                    "level": levels[finding.severity],
                    "message": {"text": finding.message + "\n" + finding.recommendation},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": quote(finding.relative_path, safe="/"),
                                    "uriBaseId": "%SRCROOT%",
                                },
                                "region": {
                                    "startLine": occurrence.line_start,
                                    "endLine": occurrence.line_end,
                                    "snippet": {"text": occurrence.evidence},
                                },
                            }
                        }
                    ],
                    "properties": {
                        "aggregateCount": finding.count,
                        "occurrencesComplete": len(finding.occurrences) == finding.count,
                    },
                }
            )
    return (
        json.dumps(
            {
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "MXReady",
                                "version": report.tool_version,
                                "rules": list(rules.values()),
                            }
                        },
                        "versionControlProvenance": [
                            {
                                "repositoryUri": report.repository.url,
                                "revisionId": report.repository.commit,
                            }
                        ],
                        "results": results,
                        "properties": {
                            "scanId": str(report.scan_id),
                            "coverage": report.coverage.model_dump() if report.coverage else None,
                            "analysisWarnings": [w.model_dump() for w in report.analysis_warnings],
                            "scope": "Static analysis only; hardware verification is separate.",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
