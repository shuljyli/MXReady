"""Read-only tools: files, directory listing, text search, and report queries."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Callable
from pathlib import Path

from mxready.agent.tools.base import (
    SENSITIVE_NAMES,
    SKIP_DIRECTORIES,
    ToolError,
    WorkspaceGuard,
    int_argument,
    text_argument,
)
from mxready.models import ScanReport, Severity
from mxready.reporting.source import describe_source
from mxready.sanitize import safe_text

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_OUTPUT = 64 * 1024
MAX_SEARCH_FILE_BYTES = 1024 * 1024
MAX_SEARCH_FILES = 5000
MAX_RESULTS = 100
MAX_FINDINGS = 50


def _is_sensitive(name: str) -> bool:
    folded = name.casefold()
    return folded in SENSITIVE_NAMES or folded.startswith(".env")


def _read_text(path: Path, limit: int) -> str:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise ToolError(f"Cannot stat {path.name}: {error}") from error
    if size > limit:
        raise ToolError(f"The file exceeds the {limit} byte limit")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ToolError(f"Cannot read {path.name}: {error}") from error
    if b"\x00" in data[:8192]:
        raise ToolError("Binary files are not supported")
    return data.decode("utf-8-sig", errors="replace")


def _bound(value: str, limit: int = MAX_OUTPUT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n[output truncated]"


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file inside the workspace, with optional line paging."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path"},
            "offset": {"type": "integer", "minimum": 1, "description": "First line (1-based)"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 2000},
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, guard: WorkspaceGuard) -> None:
        self.guard = guard

    def run(self, arguments: dict[str, object]) -> str:
        value = text_argument(arguments, "path")
        path = self.guard.resolve(value, must_exist=True)
        if not path.is_file():
            raise ToolError("The path is not a file")
        offset = int_argument(arguments, "offset", default=1, minimum=1, maximum=10_000_000)
        limit = int_argument(arguments, "limit", default=400, minimum=1, maximum=2000)
        lines = _read_text(path, MAX_FILE_BYTES).splitlines()
        selected = lines[offset - 1 : offset - 1 + limit]
        if not selected:
            return "(no lines in this range)"
        numbered = [
            f"{number:>6}  {safe_text(line)}"
            for number, line in enumerate(selected, start=offset)
        ]
        suffix = ""
        if offset - 1 + limit < len(lines):
            suffix = f"\n[file has {len(lines)} lines; page with offset]"
        return _bound("\n".join(numbered) + suffix)


class ListDirTool:
    name = "list_dir"
    description = "List workspace files and directories, skipping caches and virtualenvs."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative directory"},
            "depth": {"type": "integer", "minimum": 1, "maximum": 3},
        },
        "additionalProperties": False,
    }

    def __init__(self, guard: WorkspaceGuard) -> None:
        self.guard = guard

    def run(self, arguments: dict[str, object]) -> str:
        value = text_argument(arguments, "path", required=False)
        path = self.guard.resolve(value, must_exist=True, default_root=True)
        if not path.is_dir():
            raise ToolError("The path is not a directory")
        depth = int_argument(arguments, "depth", default=2, minimum=1, maximum=3)
        entries: list[str] = []
        count = 0
        base_depth = len(path.parts)
        for root, directories, files in os.walk(path, followlinks=False):
            current = Path(root)
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in SKIP_DIRECTORIES
                and not _is_sensitive(name)
                and not (current / name).is_symlink()
            )
            level = len(current.parts) - base_depth
            for name in directories:
                if count >= 500:
                    break
                entries.append(
                    f"d  {safe_text((current / name).relative_to(path).as_posix())}"
                )
                count += 1
            for name in sorted(files):
                if count >= 500:
                    break
                if _is_sensitive(name):
                    continue
                target = current / name
                if target.is_symlink():
                    continue
                try:
                    size = target.stat().st_size
                except OSError:
                    continue
                entries.append(
                    f"f  {safe_text(target.relative_to(path).as_posix())} ({size} bytes)"
                )
                count += 1
            if level + 1 >= depth:
                directories[:] = []
            if count >= 500:
                break
        if not entries:
            return "(empty directory)"
        suffix = "\n[listing truncated]" if count >= 500 else ""
        return _bound("\n".join(entries) + suffix)


class SearchTextTool:
    name = "search_text"
    description = "Search workspace text files for a literal query (case-insensitive)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Literal text to find"},
            "glob": {"type": "string", "description": "Optional filename glob, e.g. *.py"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, guard: WorkspaceGuard) -> None:
        self.guard = guard

    def run(self, arguments: dict[str, object]) -> str:
        query = text_argument(arguments, "query", limit=256)
        assert query is not None
        if not query:
            raise ToolError("The query must not be empty")
        pattern = text_argument(arguments, "glob", required=False, limit=256)
        if pattern and (".." in pattern or "/" in pattern or "\\" in pattern):
            raise ToolError("The glob must be a file name pattern")
        maximum = int_argument(
            arguments, "max_results", default=50, minimum=1, maximum=MAX_RESULTS
        )
        needle = query.casefold()
        results: list[str] = []
        scanned = 0
        seen = 0
        for root, directories, files in os.walk(self.guard.root, followlinks=False):
            current = Path(root)
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in SKIP_DIRECTORIES
                and not _is_sensitive(name)
                and not (current / name).is_symlink()
            )
            for name in sorted(files):
                if seen >= maximum:
                    break
                if _is_sensitive(name):
                    continue
                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue
                target = current / name
                if target.is_symlink():
                    continue
                scanned += 1
                if scanned > MAX_SEARCH_FILES:
                    results.append("[search stopped after 5000 files]")
                    return _bound("\n".join(results))
                try:
                    if target.stat().st_size > MAX_SEARCH_FILE_BYTES:
                        continue
                    data = target.read_bytes()
                except OSError:
                    continue
                if b"\x00" in data[:8192]:
                    continue
                try:
                    lines = data.decode("utf-8-sig").splitlines()
                except UnicodeDecodeError:
                    continue
                relative = target.relative_to(self.guard.root).as_posix()
                for number, line in enumerate(lines, start=1):
                    if needle in line.casefold():
                        results.append(
                            f"{safe_text(relative)}:{number}: {safe_text(line.strip()[:300])}"
                        )
                        seen += 1
                        if seen >= maximum:
                            break
                if seen >= maximum:
                    break
            if seen >= maximum:
                break
        if not results:
            return "(no matches)"
        return _bound("\n".join(results))


class ReportSummaryTool:
    name = "report_summary"
    description = "Summarize the scan report currently open in the MXReady scan workspace."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(
        self, report_provider: Callable[[], ScanReport | None], language: str
    ) -> None:
        self.report_provider = report_provider
        self.language = language

    def run(self, arguments: dict[str, object]) -> str:
        del arguments
        report = self.report_provider()
        if report is None:
            return "No scan report is open. Switch to /scan, run a scan, then return to /code."
        summary = report.summary
        source = describe_source(report, self.language)
        lines = [
            f"repository: {safe_text(report.repository.owner)}/{safe_text(report.repository.name)}",
            f"url: {safe_text(report.repository.url)}",
            f"commit: {report.repository.commit}",
            f"scanned_at: {report.scanned_at.isoformat()}",
            f"static_status: {report.static_status.value}",
            f"verification_status: {report.verification_status}",
            f"source: {safe_text(source.label)}",
            "findings: "
            f"total={summary.total_count} blocker={summary.blocker_count} "
            f"warning={summary.warning_count} info={summary.info_count}",
        ]
        if report.coverage is not None:
            lines.append(
                f"coverage: files={report.coverage.analyzed_files} "
                f"bytes={report.coverage.analyzed_bytes}"
            )
        if summary.top_blockers:
            lines.append("top_blockers:")
            lines.extend(f"  - {safe_text(item)}" for item in summary.top_blockers[:10])
        return "\n".join(lines)


class SearchFindingsTool:
    name = "search_findings"
    description = "Filter findings from the currently open scan report."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text in title, rule, path, or message"},
            "severity": {
                "type": "string",
                "enum": ["blocker", "warning", "info"],
            },
            "rule": {"type": "string", "description": "Rule ID or prefix"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "additionalProperties": False,
    }

    def __init__(self, report_provider: Callable[[], ScanReport | None]) -> None:
        self.report_provider = report_provider

    def run(self, arguments: dict[str, object]) -> str:
        report = self.report_provider()
        if report is None:
            return "No scan report is open. Switch to /scan, run a scan, then return to /code."
        query = text_argument(arguments, "query", required=False, limit=256) or ""
        severity = text_argument(arguments, "severity", required=False, limit=20)
        if severity is not None and severity not in {"blocker", "warning", "info"}:
            raise ToolError("severity must be blocker, warning, or info")
        rule = text_argument(arguments, "rule", required=False, limit=100)
        maximum = int_argument(
            arguments, "max_results", default=20, minimum=1, maximum=MAX_FINDINGS
        )
        needle = query.casefold()
        selected = []
        for finding in report.findings:
            if severity is not None and finding.severity.value != severity:
                continue
            if rule and not finding.rule_id.upper().startswith(rule.upper()):
                continue
            if needle:
                haystack = " ".join(
                    [
                        finding.rule_id,
                        finding.title,
                        finding.relative_path,
                        finding.message,
                        finding.evidence,
                    ]
                ).casefold()
                if needle not in haystack:
                    continue
            selected.append(finding)
            if len(selected) >= maximum:
                break
        if not selected:
            return "(no matching findings)"
        lines = [f"showing {len(selected)} of {len(report.findings)} findings"]
        for finding in selected:
            marker = "!"
            if finding.severity == Severity.WARNING:
                marker = "?"
            elif finding.severity == Severity.INFO:
                marker = "i"
            lines.append(
                f"[{marker}] {finding.rule_id} {safe_text(finding.title)} "
                f"@ {safe_text(finding.relative_path)}:{finding.line_start} "
                f"(x{finding.count})"
            )
            lines.append(f"    {safe_text(finding.message[:400])}")
            if finding.recommendation:
                lines.append(f"    fix: {safe_text(finding.recommendation[:400])}")
        return _bound("\n".join(lines))
