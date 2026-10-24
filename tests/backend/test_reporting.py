from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from uuid import UUID

import pytest

from mxready.models import (
    AnalysisWarning,
    Finding,
    MigrationChecklistItem,
    ScanStatus,
    Severity,
    StaticStatus,
    VerificationStatus,
)
from mxready.reporting.badge import COLORS, render_badge
from mxready.reporting.markdown import render_markdown
from mxready.reporting.terminal import render_terminal_summary


def test_reports_include_commit_and_escape_untrusted_evidence(
    report_factory,
) -> None:
    report = report_factory(
        repository_name="unsafe-project",
        findings=[
            Finding(
                rule_id="MXR-PATH-001",
                rule_version=1,
                severity=Severity.WARNING,
                category="path",
                title="Unsafe <title> | table",
                relative_path="setup`bad.py",
                line_start=2,
                line_end=2,
                evidence="<script>alert(1)</script> | ```",
                message="Hard-coded <path>",
                recommendation="Make the path configurable.",
                references=[],
            )
        ],
        static_status=StaticStatus.WARNINGS,
    )

    markdown = render_markdown(report)
    badge = render_badge(report)

    assert report.repository.commit in markdown
    assert "<script>" not in markdown
    assert "<title>" not in markdown
    assert "\\| table" in markdown
    assert "静态扫描不能替代" in markdown
    assert "<script>" not in badge
    assert "warnings" in badge
    ElementTree.fromstring(badge)


def test_markdown_contains_all_required_sections_and_grouped_findings(
    report_factory,
) -> None:
    report = report_factory(
        findings=[
            _finding("MXR-BLOCK-001", Severity.BLOCKER),
            _finding("MXR-WARN-001", Severity.WARNING),
            _finding("MXR-INFO-001", Severity.INFO),
        ],
        static_status=StaticStatus.BLOCKED,
    ).model_copy(
        update={
            "migration_checklist": [
                MigrationChecklistItem(
                    rule_id="MXR-BLOCK-001",
                    title="Review blocker",
                    action="Validate the build.",
                    affected_files=["setup.py"],
                )
            ],
            "analysis_warnings": [
                AnalysisWarning(
                    code="FILE_TOO_LARGE",
                    relative_path="large.py",
                    message="Skipped.",
                )
            ],
        }
    )

    markdown = render_markdown(report)

    for heading in [
        "## 扫描元数据",
        "## 结果摘要",
        "## 阻塞项",
        "## 警告",
        "## 提示",
        "## 迁移清单",
        "## 分析警告",
        "## 说明",
    ]:
        assert heading in markdown


@pytest.mark.parametrize(
    ("static_status", "verification_status", "expected_status"),
    [
        (StaticStatus.PASSED, VerificationStatus.NOT_RUN, "static-passed"),
        (StaticStatus.WARNINGS, VerificationStatus.NOT_RUN, "warnings"),
        (StaticStatus.BLOCKED, VerificationStatus.NOT_RUN, "blocked"),
        (StaticStatus.PASSED, VerificationStatus.VERIFIED, "verified"),
        (StaticStatus.PASSED, VerificationStatus.STALE, "verification-stale"),
        (StaticStatus.FAILED, VerificationStatus.NOT_RUN, "scan-failed"),
    ],
)
def test_badge_uses_fixed_status_and_color(
    report_factory,
    static_status: StaticStatus,
    verification_status: VerificationStatus,
    expected_status: str,
) -> None:
    badge = render_badge(
        report_factory(
            static_status=static_status,
            verification_status=verification_status,
        )
    )

    assert expected_status in badge
    assert COLORS[expected_status] in badge
    ElementTree.fromstring(badge)


def test_download_routes_use_safe_names_types_and_cache_headers(
    client,
    report_factory,
) -> None:
    report = _complete_report(client, report_factory)

    markdown = client.get(f"/api/scans/{report.scan_id}/report.md")
    json_response = client.get(f"/api/scans/{report.scan_id}/report.json")
    badge = client.get(f"/api/scans/{report.scan_id}/badge.svg")

    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert (
        f'filename="project-{report.repository.commit[:12]}-mxready.md"'
        in markdown.headers["content-disposition"]
    )
    assert json_response.status_code == 200
    assert json_response.json()["repository"]["commit"] == report.repository.commit
    assert json_response.headers["content-type"].startswith("application/json")
    assert badge.status_code == 200
    assert badge.headers["content-type"].startswith("image/svg+xml")
    assert badge.headers["cache-control"] == "no-store"


def test_download_filename_sanitizes_persisted_repository_name(
    client,
    report_factory,
) -> None:
    report = _complete_report(
        client,
        report_factory,
        repository_name="bad project/../name",
    )

    response = client.get(f"/api/scans/{report.scan_id}/report.md")

    disposition = response.headers["content-disposition"]
    assert f'filename="bad-project-name-{report.repository.commit[:12]}-mxready.md"' in disposition
    assert "../" not in disposition


def _finding(rule_id: str, severity: Severity) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=1,
        severity=severity,
        category="test",
        title=f"{severity.value} finding",
        relative_path="setup.py",
        line_start=1,
        line_end=1,
        evidence="example",
        message="Review this.",
        recommendation="Validate this.",
        references=[],
    )


def _complete_report(client, report_factory, **report_options):
    created = client.post(
        "/api/scans",
        json={"repo_url": "https://github.com/example/project", "ref": None},
    ).json()
    scan_id = UUID(created["id"])
    report = report_factory(scan_id=scan_id, **report_options)
    client.app.state.store.save_report(report)
    client.app.state.store.update_job(
        scan_id,
        status=ScanStatus.COMPLETED,
        stage_message="Complete",
        resolved_commit=report.repository.commit,
    )
    return report


def _terminal_finding(
    rule_id: str,
    severity: Severity,
    title: str,
    relative_path: str,
    line: int,
    count: int = 1,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=1,
        severity=severity,
        category="test",
        title=title,
        relative_path=relative_path,
        line_start=line,
        line_end=line,
        evidence="evidence",
        message="message",
        recommendation="recommendation",
        references=[],
        count=count,
    )


def test_terminal_summary_lists_status_counts_and_findings(report_factory) -> None:
    report = report_factory(
        repository_name="cuda-extension",
        static_status=StaticStatus.BLOCKED,
        findings=[
            _terminal_finding(
                "MXR-TOOLCHAIN-001", Severity.BLOCKER, "检测直接 nvcc 工具调用", "setup.py", 2
            ),
            _terminal_finding(
                "MXR-PATH-001", Severity.WARNING, "检测硬编码 CUDA 安装路径", "build.sh", 3
            ),
        ],
    )

    text = render_terminal_summary(
        report,
        output_note="cuda-extension-aaaaaaaaaaaa.json / .md / .svg",
    )

    lines = text.splitlines()
    assert lines[0] == "MXReady: blocked | 阻断 1 · 警告 1 · 提示 0"
    assert "阻断 MXR-TOOLCHAIN-001 检测直接 nvcc 工具调用 (setup.py:2)" in lines[1]
    assert "警告 MXR-PATH-001 检测硬编码 CUDA 安装路径 (build.sh:3)" in lines[2]
    assert lines[-1] == "报告: cuda-extension-aaaaaaaaaaaa.json / .md / .svg"


def test_terminal_summary_marks_repeated_hits_and_hides_the_rest(report_factory) -> None:
    report = report_factory(
        static_status=StaticStatus.WARNINGS,
        findings=[
            _terminal_finding(
                f"MXR-TOOL-{index + 1:03d}",
                Severity.WARNING,
                f"规则 {index + 1}",
                f"mod_{index}.py",
                index + 1,
                count=2 if index == 0 else 1,
            )
            for index in range(7)
        ],
    )

    text = render_terminal_summary(report)

    assert "x2" in text.splitlines()[1]
    assert "… 其余 2 项见报告文件" in text


def test_terminal_summary_reports_a_clean_project_in_one_breath(report_factory) -> None:
    report = report_factory(static_status=StaticStatus.PASSED, findings=[])

    text = render_terminal_summary(report)

    assert text.splitlines()[:2] == [
        "MXReady: passed | 阻断 0 · 警告 0 · 提示 0",
        "  未命中任何规则",
    ]


def test_terminal_summary_is_gbk_encodable_for_windows_pipes(report_factory) -> None:
    report = report_factory(
        static_status=StaticStatus.BLOCKED,
        findings=[
            _terminal_finding(
                "MXR-TOOLCHAIN-001", Severity.BLOCKER, "检测直接 nvcc 工具调用", "setup.py", 2
            )
        ],
    )

    text = render_terminal_summary(report, output_note="r.json / .md / .svg")

    text.encode("gbk")
