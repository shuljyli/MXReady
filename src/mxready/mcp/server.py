"""Model Context Protocol front end for the MXReady static readiness pipeline.

The HTTP application and this server build the same scan pipeline; this module
exists so an agent can ask MXReady for migration facts instead of guessing about
CUDA to MXMACA compatibility.

Two constraints shape the implementation:

* stdout is the stdio transport channel, so logging must never reach it;
* the ``mcp`` SDK is an optional dependency, so nothing outside this module may
  import it.
"""

from __future__ import annotations

import atexit
import logging
import sys
from threading import Lock
from time import monotonic, sleep
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from mxready import __version__
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import Finding, ScanJob, ScanReport, ScanStatus
from mxready.persistence.sqlite import SQLiteStore
from mxready.repository.git_client import GitClient
from mxready.repository.identity import build_providers
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import RuleCatalog, load_rule_catalog
from mxready.services.scans import ScanService
from mxready.services.worker import ScanWorker

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_SEVERITY_ORDER = {"blocker": 0, "warning": 1, "info": 2}
_DEFAULT_TIMEOUT_SECONDS = 300
_MIN_TIMEOUT_SECONDS = 30
_MAX_TIMEOUT_SECONDS = 1800
_MAX_FINDINGS_CEILING = 500
_POLL_SECONDS = 0.5

_INSTRUCTIONS = (
    "MXReady returns static, evidence-backed readiness findings for PyTorch CUDA "
    "extension repositories that are being considered for migration to MetaX MXMACA. "
    "Every finding carries a rule id, a file and line, the matched evidence, and a "
    "recommendation, so a migration plan can cite verifiable facts instead of a guessed "
    "compatibility verdict. Findings are advisory: a cleared static check is not a "
    "hardware verification result, and verification_status only becomes 'verified' "
    "after a runner result produced on a MetaX GPU is uploaded for the same commit."
)


class _ScanRuntime:
    """Owns the durable queue, the analyzer and the worker threads for one session."""

    def __init__(self, settings: Settings) -> None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        self.catalog: RuleCatalog = load_rule_catalog(
            settings.rules_dir,
            extra_directory=settings.extra_rules_dir,
        )
        self._store = SQLiteStore(settings.data_dir / "mxready.db")
        self._store.initialize()
        providers = build_providers(settings.allowed_hosts)
        self._service = ScanService(
            self._store,
            GitClient(),
            ScanAnalyzer(
                self.catalog,
                providers=providers,
                enable_prefilter=settings.prefilter_enabled,
            ),
            settings,
            providers=providers,
        )
        self._worker = ScanWorker(self._service)

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._worker.stop()

    def scan_and_wait(
        self,
        repo_url: str,
        ref: str | None,
        timeout_seconds: int,
    ) -> ScanReport:
        job = self._service.create_scan(repo_url, ref)
        finished = self._wait_for(job, timeout_seconds)
        if finished.status is ScanStatus.FAILED:
            raise MxReadyError(
                finished.failure_code or "SCAN_FAILED",
                finished.failure_message or "The scan failed.",
                {"scan_id": str(finished.id)},
            )
        return self._service.get_report(finished.id)

    def get_report(self, scan_id: UUID) -> ScanReport:
        return self._service.get_report(scan_id)

    def _wait_for(self, job: ScanJob, timeout_seconds: int) -> ScanJob:
        deadline = monotonic() + timeout_seconds
        current = job
        while current.status not in (ScanStatus.COMPLETED, ScanStatus.FAILED):
            if monotonic() >= deadline:
                raise MxReadyError(
                    "SCAN_TIMEOUT",
                    f"The scan did not finish within {timeout_seconds} seconds.",
                    {"scan_id": str(job.id), "status": str(current.status)},
                )
            sleep(_POLL_SECONDS)
            current = self._service.get_scan(job.id)
        return current


def _configure_stderr_logging() -> None:
    """Send MXReady logs to stderr; stdout belongs to the stdio transport."""
    target = logging.getLogger("mxready")
    if target.handlers:
        return
    target.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    target.addHandler(handler)
    target.propagate = False


def _bounded_timeout(value: int) -> int:
    return max(_MIN_TIMEOUT_SECONDS, min(value, _MAX_TIMEOUT_SECONDS))


def _bounded_findings(value: int) -> int:
    return max(1, min(value, _MAX_FINDINGS_CEILING))


def _finding_payload(finding: Finding) -> dict[str, Any]:
    return {
        "rule_id": finding.rule_id,
        "severity": str(finding.severity),
        "category": finding.category,
        "title": finding.title,
        "file": finding.relative_path,
        "line_start": finding.line_start,
        "line_end": finding.line_end,
        "occurrences": finding.count,
        "evidence": finding.evidence,
        "message": finding.message,
        "recommendation": finding.recommendation,
        "references": [{"title": item.title, "url": item.url} for item in finding.references],
    }


def _report_payload(report: ScanReport, max_findings: int) -> dict[str, Any]:
    ordered = sorted(
        report.findings,
        key=lambda finding: (
            _SEVERITY_ORDER.get(str(finding.severity), len(_SEVERITY_ORDER)),
            finding.relative_path,
            finding.line_start,
        ),
    )
    selected = ordered[:max_findings]
    return {
        "scan_id": str(report.scan_id),
        "repository": {
            "url": report.repository.url,
            "provider": report.repository.provider,
            "commit": report.repository.commit,
        },
        "scanned_at": report.scanned_at.isoformat(),
        "tool_version": report.tool_version,
        "ruleset_version": report.ruleset_version,
        "static_status": str(report.static_status),
        "verification_status": str(report.verification_status),
        "summary": report.summary.model_dump(mode="json"),
        "findings": [_finding_payload(item) for item in selected],
        "returned_findings": len(selected),
        "total_findings": len(report.findings),
        "findings_truncated": len(report.findings) > len(selected),
        "migration_checklist": [
            item.model_dump(mode="json") for item in report.migration_checklist
        ],
        "analysis_warnings": [item.model_dump(mode="json") for item in report.analysis_warnings],
    }


def _error_payload(error: Exception) -> dict[str, Any]:
    if isinstance(error, MxReadyError):
        return {
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        }
    return {"error": {"code": type(error).__name__, "message": str(error), "details": {}}}


_runtime_lock = Lock()
_runtime_instance: _ScanRuntime | None = None


def _runtime() -> _ScanRuntime:
    global _runtime_instance
    with _runtime_lock:
        if _runtime_instance is None:
            runtime = _ScanRuntime(Settings.from_env())
            runtime.start()
            atexit.register(runtime.stop)
            _runtime_instance = runtime
        return _runtime_instance


def build_server() -> FastMCP:
    """Register the MXReady tools on a fresh FastMCP server."""
    server = FastMCP("MXReady", instructions=_INSTRUCTIONS)
    # The SDK reports its own package version in the initialize result by
    # default; surface the MXReady version so a client can tell which build
    # answered. FastMCP exposes no constructor argument for this.
    server._mcp_server.version = __version__

    @server.tool()
    def scan_repository(
        repo_url: str,
        ref: str | None = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
        max_findings: int = 20,
    ) -> dict[str, Any]:
        """Scan a public GitHub or Gitee repository and return readiness findings.

        Blocks until the scan finishes or the timeout expires. The report is bound
        to the resolved commit, so the same findings can be reproduced later.

        Args:
            repo_url: Public HTTPS repository URL on an allowlisted host.
            ref: Optional branch, tag, or 40-character commit to pin.
            timeout_seconds: Wall-clock budget, clamped to 30..1800.
            max_findings: Maximum findings returned, ordered by severity.
        """
        try:
            report = _runtime().scan_and_wait(
                repo_url,
                ref,
                _bounded_timeout(timeout_seconds),
            )
            return _report_payload(report, _bounded_findings(max_findings))
        except (MxReadyError, OSError, ValueError) as error:
            return _error_payload(error)

    @server.tool()
    def get_report(scan_id: str, max_findings: int = 50) -> dict[str, Any]:
        """Return a previously completed MXReady report by scan id.

        Args:
            scan_id: UUID returned by scan_repository.
            max_findings: Maximum findings returned, ordered by severity.
        """
        try:
            report = _runtime().get_report(UUID(scan_id))
            return _report_payload(report, _bounded_findings(max_findings))
        except (MxReadyError, ValueError) as error:
            return _error_payload(error)

    @server.tool()
    def list_rules(
        category: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """List the bundled MXMACA migration rules, optionally filtered.

        Args:
            category: Case-insensitive category filter, for example "toolchain".
            severity: One of "blocker", "warning", or "info".
        """
        catalog = _runtime().catalog
        rules = catalog.rules
        if category:
            rules = [rule for rule in rules if rule.category.casefold() == category.casefold()]
        if severity:
            rules = [rule for rule in rules if str(rule.severity).casefold() == severity.casefold()]
        return {
            "tool_version": __version__,
            "ruleset_version": catalog.version,
            "total": len(rules),
            "rules": [
                {
                    "id": rule.id,
                    "title": rule.title,
                    "severity": str(rule.severity),
                    "category": rule.category,
                }
                for rule in rules
            ],
        }

    @server.tool()
    def explain_rule(rule_id: str) -> dict[str, Any]:
        """Return one rule with its rationale, recommendation, and sources.

        Args:
            rule_id: Exact rule identifier, for example "MXR-WARP-001".
        """
        for rule in _runtime().catalog.rules:
            if rule.id == rule_id:
                return {
                    "id": rule.id,
                    "version": rule.version,
                    "title": rule.title,
                    "severity": str(rule.severity),
                    "category": rule.category,
                    "file_globs": list(rule.file_globs),
                    "message": rule.message,
                    "recommendation": rule.recommendation,
                    "confidence": rule.confidence,
                    "references": [
                        {"title": item.title, "url": item.url} for item in rule.references
                    ],
                }
        return {
            "error": {
                "code": "RULE_NOT_FOUND",
                "message": f"No rule with id {rule_id}.",
                "details": {},
            }
        }

    return server


def main() -> None:
    _configure_stderr_logging()
    build_server().run()


if __name__ == "__main__":
    main()
