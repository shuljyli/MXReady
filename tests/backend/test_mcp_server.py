"""Tests for the optional Model Context Protocol front end.

The ``mcp`` SDK is an optional dependency, so the whole module skips when it is
not installed. CI installs it through the ``mcp`` extra.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4

import pytest

pytest.importorskip("mcp")

import mxready.mcp.server as mcp_server  # noqa: E402
from mxready.errors import MxReadyError  # noqa: E402
from mxready.mcp.server import (  # noqa: E402
    _bounded_findings,
    _bounded_timeout,
    _error_payload,
    _report_payload,
    build_server,
)
from mxready.models import (  # noqa: E402
    Finding,
    RepositorySnapshot,
    ScanReport,
    ScanSummary,
    Severity,
    StaticStatus,
    VerificationStatus,
)
from mxready.scanning.rule_loader import load_rule_catalog  # noqa: E402

_RULES_DIR = Path(__file__).resolve().parents[2] / "src" / "mxready" / "resources" / "rules" / "v1"


def _finding(rule_id: str, severity: Severity, path: str, line: int) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=1,
        severity=severity,
        category="warp",
        title="检测硬编码 32 线程束假设",
        relative_path=path,
        line_start=line,
        line_end=line,
        evidence="threadIdx.x % 32",
        message="按 32 线程一组计算 lane。",
        recommendation="改用运行时查询的线程束宽度。",
        references=[],
    )


def _report(findings: list[Finding]) -> ScanReport:
    return ScanReport(
        scan_id=uuid4(),
        repository=RepositorySnapshot(
            provider="github",
            owner="pytorch",
            name="extension-cpp",
            url="https://github.com/pytorch/extension-cpp",
            commit="a" * 40,
        ),
        tool_version="0.3.0",
        ruleset_version="4",
        scanned_at=datetime.now(UTC),
        summary=ScanSummary(
            total_count=len(findings),
            blocker_count=0,
            warning_count=0,
            info_count=0,
        ),
        findings=findings,
        migration_checklist=[],
        analysis_warnings=[],
        static_status=StaticStatus.BLOCKED,
        verification_status=VerificationStatus.NOT_RUN,
    )


async def _call(server: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await server.call_tool(name, arguments)
    payload = result[1] if isinstance(result, tuple) and len(result) > 1 else result
    assert isinstance(payload, dict), payload
    return payload


def test_payload_orders_findings_by_severity() -> None:
    report = _report(
        [
            _finding("MXR-HEADER-001", Severity.INFO, "csrc/a.cu", 3),
            _finding("MXR-PTX-001", Severity.BLOCKER, "csrc/z.cu", 9),
            _finding("MXR-ARCH-001", Severity.WARNING, "csrc/m.cu", 5),
        ]
    )

    payload = _report_payload(report, max_findings=10)

    assert [item["severity"] for item in payload["findings"]] == [
        "blocker",
        "warning",
        "info",
    ]
    assert payload["total_findings"] == 3
    assert payload["findings_truncated"] is False


def test_payload_truncates_and_reports_the_remainder() -> None:
    report = _report(
        [
            _finding(f"MXR-TEST-{index:03d}", Severity.WARNING, "csrc/a.cu", index)
            for index in (1, 2)
        ]
    )

    payload = _report_payload(report, max_findings=1)

    assert payload["returned_findings"] == 1
    assert payload["total_findings"] == 2
    assert payload["findings_truncated"] is True


def test_payload_keeps_file_and_line_for_each_finding() -> None:
    report = _report([_finding("MXR-WARP-001", Severity.BLOCKER, "csrc/kernel.cu", 42)])

    finding = _report_payload(report, max_findings=10)["findings"][0]

    assert finding["file"] == "csrc/kernel.cu"
    assert finding["line_start"] == 42
    assert finding["recommendation"]


def test_error_payload_preserves_mxready_codes() -> None:
    payload = _error_payload(MxReadyError("SCAN_NOT_FOUND", "missing", {"scan_id": "x"}))

    assert payload["error"]["code"] == "SCAN_NOT_FOUND"
    assert payload["error"]["details"] == {"scan_id": "x"}


def test_error_payload_falls_back_to_the_exception_name() -> None:
    payload = _error_payload(ValueError("bad input"))

    assert payload["error"]["code"] == "ValueError"
    assert payload["error"]["message"] == "bad input"


def test_bounds_clamp_timeouts_and_finding_limits() -> None:
    assert _bounded_timeout(1) == mcp_server._MIN_TIMEOUT_SECONDS
    assert _bounded_timeout(10_000) == mcp_server._MAX_TIMEOUT_SECONDS
    assert _bounded_findings(0) == 1
    assert _bounded_findings(10_000) == mcp_server._MAX_FINDINGS_CEILING


def test_server_exposes_the_documented_tools() -> None:
    server = build_server()

    tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in tools} == {
        "scan_repository",
        "get_report",
        "get_scan",
        "list_rules",
        "explain_rule",
    }


def test_server_reports_the_mxready_version() -> None:
    server = build_server()

    assert server._mcp_server.version == mcp_server.__version__


class _FakeRuntime:
    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog


def test_list_rules_filters_by_severity(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = load_rule_catalog(_RULES_DIR)
    monkeypatch.setattr(mcp_server, "_runtime", lambda: _FakeRuntime(catalog))
    server = build_server()

    payload = asyncio.run(_call(server, "list_rules", {"severity": "blocker"}))

    assert payload["rules"]
    assert all(rule["severity"] == "blocker" for rule in payload["rules"])
    assert payload["total"] == len(payload["rules"])


def test_explain_rule_returns_the_rationale(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = load_rule_catalog(_RULES_DIR)
    monkeypatch.setattr(mcp_server, "_runtime", lambda: _FakeRuntime(catalog))
    server = build_server()

    payload = asyncio.run(_call(server, "explain_rule", {"rule_id": "MXR-WARP-001"}))

    assert payload["id"] == "MXR-WARP-001"
    assert payload["recommendation"]
    assert payload["references"]


def test_explain_rule_reports_unknown_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = load_rule_catalog(_RULES_DIR)
    monkeypatch.setattr(mcp_server, "_runtime", lambda: _FakeRuntime(catalog))
    server = build_server()

    payload = asyncio.run(_call(server, "explain_rule", {"rule_id": "MXR-NOPE-999"}))

    assert payload["error"]["code"] == "RULE_NOT_FOUND"


def test_scan_wait_does_not_block_other_mcp_requests(monkeypatch):
    release = Event()
    runtime = _FakeRuntime(load_rule_catalog(_RULES_DIR))

    def wait_for_scan(*args):
        release.wait(1)
        raise MxReadyError("SCAN_TIMEOUT", "fixture timeout")

    runtime.scan_and_wait = wait_for_scan
    monkeypatch.setattr(mcp_server, "_runtime", lambda: runtime)

    async def check():
        server = build_server()
        task = asyncio.create_task(
            _call(server, "scan_repository", {"repo_url": "https://github.com/example/project"})
        )
        try:
            await asyncio.sleep(0.01)
            assert not task.done(), "scan blocked the event loop until it finished"
            rules = await _call(server, "list_rules", {})
            assert rules["total"] > 0
        finally:
            release.set()
            await task

    asyncio.run(check())


def test_mcp_pagination_reaches_all_findings_and_binds_cursor(monkeypatch):
    report = _report(
        [_finding(f"MXR-TEST-{i:03d}", Severity.WARNING, f"{i:04d}.cu", 1) for i in range(520)]
    )

    class Runtime:
        def get_report(self, scan_id):
            return report

    monkeypatch.setattr(mcp_server, "_runtime", lambda: Runtime())
    server = build_server()
    first = asyncio.run(
        _call(server, "get_report", {"scan_id": str(report.scan_id), "max_findings": 500})
    )
    assert first["next_cursor"]
    second = asyncio.run(
        _call(
            server, "get_report", {"scan_id": str(report.scan_id), "cursor": first["next_cursor"]}
        )
    )
    assert second["returned_findings"] == 20
    assert second["next_cursor"] is None
    assert not set(f["file"] for f in first["findings"]) & set(
        f["file"] for f in second["findings"]
    )
    invalid = asyncio.run(
        _call(server, "get_report", {"scan_id": str(uuid4()), "cursor": first["next_cursor"]})
    )
    assert invalid["error"]["code"] == "INVALID_CURSOR"


@pytest.mark.parametrize("cursor", ["not-base64", "[]", "e30=", "a" * 4097])
def test_malformed_cursor_is_rejected(cursor):
    with pytest.raises(MxReadyError) as error:
        mcp_server._page_options(str(uuid4()), cursor, None, None)
    assert error.value.code == "INVALID_CURSOR"


def test_report_filters_and_cursor_cannot_change_query():
    report = _report(
        [
            _finding("MXR-TEST-001", Severity.WARNING, "a.cu", 1),
            _finding("MXR-TEST-002", Severity.WARNING, "a.cu", 2),
            _finding("MXR-TEST-003", Severity.BLOCKER, "b.cu", 1),
        ]
    )
    first = _report_payload(report, 1, severity="warning", file="a.cu")
    assert first["matched_findings"] == 2 and first["total_findings"] == 3
    assert mcp_server._page_options(str(report.scan_id), first["next_cursor"], None, None) == (
        1,
        "warning",
        "a.cu",
    )
    with pytest.raises(MxReadyError):
        mcp_server._page_options(str(report.scan_id), first["next_cursor"], "blocker", None)
    with pytest.raises(MxReadyError):
        mcp_server._page_options(str(report.scan_id), None, "unknown", None)
