from __future__ import annotations

import html
from collections import defaultdict

from mxready.models import Finding, ScanReport, Severity

_SEVERITY_HEADINGS = {
    Severity.BLOCKER: "阻塞项",
    Severity.WARNING: "警告",
    Severity.INFO: "提示",
}
_MARKDOWN_CONTROL_CHARACTERS = "\\`*_{}[]()#+-.!|>"


def render_markdown(report: ScanReport) -> str:
    """Render a deterministic, portable report with untrusted text escaped."""
    lines = [
        f"# MXReady 适配体检报告：{_markdown_text(report.repository.name)}",
        "",
        "## 扫描元数据",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 仓库 | {_table_cell(report.repository.url)} |",
        f"| 提交 | `{report.repository.commit}` |",
        f"| MXReady 版本 | {_table_cell(report.tool_version)} |",
        f"| 规则集版本 | {_table_cell(report.ruleset_version)} |",
        f"| 扫描时间 | {_table_cell(report.scanned_at.isoformat())} |",
        f"| 静态状态 | `{report.static_status.value}` |",
        f"| 硬件验证状态 | `{report.verification_status.value}` |",
        "",
        "## 结果摘要",
        "",
        "| 阻塞项 | 警告 | 提示 | 总计 |",
        "| ---: | ---: | ---: | ---: |",
        (
            f"| {report.summary.blocker_count} | {report.summary.warning_count} "
            f"| {report.summary.info_count} | {report.summary.total_count} |"
        ),
        "",
    ]

    grouped: defaultdict[Severity, list[Finding]] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.severity].append(finding)

    for severity in (Severity.BLOCKER, Severity.WARNING, Severity.INFO):
        lines.extend([f"## {_SEVERITY_HEADINGS[severity]}", ""])
        findings = grouped[severity]
        if not findings:
            lines.extend(["无。", ""])
            continue
        for finding in findings:
            lines.extend(_render_finding(finding))

    lines.extend(["## 迁移清单", ""])
    if report.migration_checklist:
        for item in report.migration_checklist:
            files = "、".join(_inline_code(path) for path in item.affected_files)
            lines.append(
                f"- [ ] `{item.rule_id}` {_markdown_text(item.title)}："
                f"{_markdown_text(item.action)}"
            )
            lines.append(f"  - 涉及文件：{files or '无'}")
    else:
        lines.append("当前没有由阻塞项或警告生成的迁移任务。")
    lines.append("")

    lines.extend(["## 分析警告", ""])
    if report.analysis_warnings:
        for warning in report.analysis_warnings:
            location = f"（{_inline_code(warning.relative_path)}）" if warning.relative_path else ""
            lines.append(f"- `{warning.code}`{location}：{_markdown_text(warning.message)}")
    else:
        lines.append("无。")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            (
                "静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，"
                "也不能作为项目安全性或完整兼容性的证明。"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _render_finding(finding: Finding) -> list[str]:
    lines = [
        f"### `{finding.rule_id}` — {_markdown_text(finding.title)}",
        "",
        (
            f"- 位置：{_inline_code(finding.relative_path)}，"
            f"第 {finding.line_start}–{finding.line_end} 行"
        ),
        f"- 分类：`{_markdown_text(finding.category)}`",
        f"- 说明：{_markdown_text(finding.message)}",
        f"- 建议：{_markdown_text(finding.recommendation)}",
        "- 证据：",
        "",
    ]
    evidence_lines = finding.evidence.splitlines() or [""]
    lines.extend(f"    {html.escape(line, quote=False)}" for line in evidence_lines)
    if finding.references:
        lines.extend(["", "- 参考："])
        for reference in finding.references:
            lines.append(f"  - [{_markdown_text(reference.title)}]({reference.url})")
    lines.extend(["", ""])
    return lines


def _markdown_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    for character in _MARKDOWN_CONTROL_CHARACTERS:
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r", " ").replace("\n", " ")


def _table_cell(value: str) -> str:
    return _markdown_text(value)


def _inline_code(value: str) -> str:
    escaped = html.escape(value, quote=False).replace("`", "&#96;")
    return f"`{escaped.replace(chr(10), ' ').replace(chr(13), ' ')}`"
