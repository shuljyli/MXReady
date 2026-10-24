"""终端极简结果摘要：一行状态 + 前若干条命中 + 报告文件位置。

输出只用 GBK 可编码字符（中文、…、—、·、ASCII），保证在 Windows
传统代码页的重定向管道中也不会触发 UnicodeEncodeError。
"""

from __future__ import annotations

from mxready.models import ScanReport, Severity

_MAX_LISTED_FINDINGS = 5
_SEVERITY_LABELS = {
    Severity.BLOCKER: "阻断",
    Severity.WARNING: "警告",
    Severity.INFO: "提示",
}


def render_terminal_summary(
    report: ScanReport,
    *,
    output_note: str | None = None,
    max_listed: int = _MAX_LISTED_FINDINGS,
) -> str:
    """渲染适合直接阅读的极简检查结果；命中按严重程度排序，只列前若干条。"""
    summary = report.summary
    lines = [
        f"MXReady: {report.static_status.value} | "
        f"阻断 {summary.blocker_count} · 警告 {summary.warning_count} · 提示 {summary.info_count}"
    ]
    if report.findings:
        for finding in report.findings[:max_listed]:
            count = f" x{finding.count}" if finding.count > 1 else ""
            lines.append(
                f"  {_SEVERITY_LABELS[finding.severity]} {finding.rule_id}"
                f" {finding.title} ({finding.relative_path}:{finding.line_start}{count})"
            )
        hidden = len(report.findings) - max_listed
        if hidden > 0:
            lines.append(f"  … 其余 {hidden} 项见报告文件")
    else:
        lines.append("  未命中任何规则")
    if output_note:
        lines.append(f"报告: {output_note}")
    return "\n".join(lines)
