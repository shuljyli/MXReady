"""终端极简结果摘要：一行状态 + 前若干条命中 + 报告文件位置。

中文输出只用 GBK 可编码字符（中文、…、—、·、ASCII）；``english=True`` 时
输出纯 ASCII，供 cp1252 等无法编码中文的旧代码页回退使用。
"""

from __future__ import annotations

from mxready.models import ScanReport, Severity

_MAX_LISTED_FINDINGS = 5
_SEVERITY_LABELS = {
    Severity.BLOCKER: "阻断",
    Severity.WARNING: "警告",
    Severity.INFO: "提示",
}
_SEVERITY_LABELS_EN = {
    Severity.BLOCKER: "BLOCKER",
    Severity.WARNING: "WARNING",
    Severity.INFO: "INFO",
}


def render_terminal_summary(
    report: ScanReport,
    *,
    output_note: str | None = None,
    max_listed: int = _MAX_LISTED_FINDINGS,
    english: bool = False,
) -> str:
    """渲染适合直接阅读的极简检查结果；命中按严重程度排序，只列前若干条。

    英文模式省略规则标题，避免中文标题在 cp1252 等旧代码页中无法输出。
    """
    summary = report.summary
    if english:
        labels = _SEVERITY_LABELS_EN
        lines = [
            f"MXReady: {report.static_status.value} | "
            f"blockers {summary.blocker_count}, "
            f"warnings {summary.warning_count}, "
            f"info {summary.info_count}"
        ]
    else:
        labels = _SEVERITY_LABELS
        lines = [
            f"MXReady: {report.static_status.value} | "
            f"阻断 {summary.blocker_count} · "
            f"警告 {summary.warning_count} · "
            f"提示 {summary.info_count}"
        ]
    if report.findings:
        for finding in report.findings[:max_listed]:
            count = f" x{finding.count}" if finding.count > 1 else ""
            if english:
                lines.append(
                    f"  {labels[finding.severity]} {finding.rule_id}"
                    f" ({finding.relative_path}:{finding.line_start}{count})"
                )
            else:
                lines.append(
                    f"  {labels[finding.severity]} {finding.rule_id}"
                    f" {finding.title} ({finding.relative_path}:{finding.line_start}{count})"
                )
        hidden = len(report.findings) - max_listed
        if hidden > 0:
            if english:
                lines.append(f"  ... {hidden} more in the report file")
            else:
                lines.append(f"  … 其余 {hidden} 项见报告文件")
    else:
        lines.append("  No rule matches" if english else "  未命中任何规则")
    if output_note:
        lines.append(f"Report: {output_note}" if english else f"报告: {output_note}")
    return "\n".join(lines)
