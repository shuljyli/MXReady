from __future__ import annotations

import html
from collections import defaultdict

from mxready.models import Finding, FindingOccurrence, ScanReport, Severity

_SEVERITY_HEADINGS = {
    Severity.BLOCKER: "阻塞项",
    Severity.WARNING: "警告",
    Severity.INFO: "提示",
}

_SEVERITY_CLASSES = {
    Severity.BLOCKER: "blocker",
    Severity.WARNING: "warning",
    Severity.INFO: "info",
}

_STYLES = """
:root { color-scheme: light; }
body { margin: 0 auto; max-width: 60rem; padding: 2rem 1.5rem 4rem;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif; color: #1f2933; line-height: 1.6; }
h1 { font-size: 1.6rem; border-bottom: 2px solid #1f2933; padding-bottom: .5rem; }
h2 { font-size: 1.25rem; margin-top: 2rem;
    border-bottom: 1px solid #d9e2ec; padding-bottom: .3rem; }
h3 { font-size: 1.05rem; margin: 0 0 .4rem; }
table { border-collapse: collapse; width: 100%; margin: .8rem 0; }
th, td { border: 1px solid #d9e2ec; padding: .45rem .6rem; text-align: left;
    word-break: break-all; }
th { background: #f0f4f8; }
code, pre { font-family: Consolas, "Courier New", monospace; }
code { background: #f0f4f8; padding: .1rem .3rem; border-radius: 3px; }
pre { background: #f0f4f8; border: 1px solid #d9e2ec; border-radius: 4px;
    padding: .6rem .8rem; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
.finding { border: 1px solid #d9e2ec; border-radius: 6px; padding: .8rem 1rem; margin: .8rem 0; }
.finding.blocker { border-left: 4px solid #c81e1e; }
.finding.warning { border-left: 4px solid #b7791f; }
.finding.info { border-left: 4px solid #2b6cb0; }
.meta { color: #52606d; font-size: .9rem; }
.note { background: #f0f4f8; border-radius: 6px; padding: .6rem 1rem; }
@media print {
    @page { size: A4; margin: 16mm; }
    body { max-width: none; padding: 0; font-size: 11pt; }
    .finding { break-inside: avoid; }
    a { color: inherit; text-decoration: none; }
}
"""


def render_html(report: ScanReport) -> str:
    """Render a self-contained, printable HTML report with untrusted text escaped."""
    body: list[str] = [
        f"<h1>MXReady 适配体检报告：{_e(report.repository.name)}</h1>",
        "<h2>扫描元数据</h2>",
        "<table><tbody>",
        _row("仓库", report.repository.url),
        _row("提交", report.repository.commit),
        _row("MXReady 版本", report.tool_version),
        _row("规则集版本", report.ruleset_version),
        _row("规则集摘要", report.ruleset_digest or "未记录"),
        _row("扩展规则版本", report.extra_ruleset_version or "无"),
        _row("分析配置", str(report.analysis_config)),
        _row("扫描时间", report.scanned_at.isoformat()),
        _row("静态状态", report.static_status.value),
        _row("硬件验证状态", report.verification_status.value),
        "</tbody></table>",
        "<h2>结果摘要</h2>",
        "<table><thead><tr>"
        "<th>阻塞项</th><th>警告</th><th>提示</th><th>总计</th>"
        "</tr></thead><tbody><tr>"
        f"<td>{report.summary.blocker_count}</td>"
        f"<td>{report.summary.warning_count}</td>"
        f"<td>{report.summary.info_count}</td>"
        f"<td>{report.summary.total_count}</td>"
        "</tr></tbody></table>",
        "<h2>扫描范围</h2>",
    ]
    if report.coverage:
        c = report.coverage
        body.append(
            f"<p>分析文件：{c.analyzed_files}；字节：{c.analyzed_bytes}；"
            f"排除目录：{c.excluded_directories}（未遍历内容）。</p>"
        )
        body.append(f"<p>文件类型：<code>{_e(str(c.files_by_type))}</code></p>")
        body.append(f"<p>跳过原因：<code>{_e(str(c.skipped_by_reason))}</code></p>")
    else:
        body.append("<p>旧报告未记录扫描范围，请重新扫描。</p>")
    body.append('<p class="meta">仅表示支持的文件类型与限制内的扫描范围，不是完整仓库覆盖率。</p>')

    grouped: defaultdict[Severity, list[Finding]] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.severity].append(finding)
    for severity in (Severity.BLOCKER, Severity.WARNING, Severity.INFO):
        body.append(f"<h2>{_SEVERITY_HEADINGS[severity]}</h2>")
        findings = grouped[severity]
        if not findings:
            body.append("<p>无。</p>")
            continue
        body.extend(_render_finding(finding) for finding in findings)

    body.append("<h2>迁移清单</h2>")
    if report.migration_checklist:
        body.append("<ul>")
        for item in report.migration_checklist:
            files = "、".join(f"<code>{_e(path)}</code>" for path in item.affected_files) or "无"
            body.append(
                f"<li><code>{_e(item.rule_id)}</code> {_e(item.title)}：{_e(item.action)}"
                f'<br><span class="meta">涉及文件：{files}</span></li>'
            )
        body.append("</ul>")
    else:
        body.append("<p>当前没有由阻塞项或警告生成的迁移任务。</p>")

    body.append("<h2>分析警告</h2>")
    if report.analysis_warnings:
        body.append("<ul>")
        for warning in report.analysis_warnings:
            location = (
                f"（<code>{_e(warning.relative_path)}</code>）" if warning.relative_path else ""
            )
            body.append(
                f"<li><code>{_e(warning.code)}</code>{location}：{_e(warning.message)}</li>"
            )
        body.append("</ul>")
    else:
        body.append("<p>无。</p>")

    body.append("<h2>说明</h2>")
    body.append(
        '<p class="note">静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，'
        "也不能作为项目安全性或完整兼容性的证明。</p>"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>MXReady 适配体检报告：{_e(report.repository.name)}</title>\n"
        f"<style>{_STYLES}</style>\n"
        "</head>\n"
        f"<body>\n{''.join(body)}\n</body>\n</html>\n"
    )


def _render_finding(finding: Finding) -> str:
    parts = [
        f'<section class="finding {_SEVERITY_CLASSES[finding.severity]}">',
        f"<h3><code>{_e(finding.rule_id)}</code> — {_e(finding.title)}</h3>",
        (
            f"<p>位置：<code>{_e(finding.relative_path)}</code>，"
            f"第 {finding.line_start}–{finding.line_end} 行</p>"
        ),
        f"<p>分类：<code>{_e(finding.category)}</code></p>",
        f"<p>说明：{_e(finding.message)}</p>",
        f"<p>建议：{_e(finding.recommendation)}</p>",
    ]
    occurrences = finding.occurrences or [
        FindingOccurrence(
            line_start=finding.line_start, line_end=finding.line_end, evidence=finding.evidence
        )
    ]
    parts.append("<p>证据：</p>")
    for occurrence in occurrences:
        parts.append(f'<p class="meta">第 {occurrence.line_start}–{occurrence.line_end} 行</p>')
        parts.append(f"<pre>{_e(occurrence.evidence)}</pre>")
    if not finding.occurrences and finding.count > 1:
        parts.append('<p class="meta">旧报告仅保留聚合证据，无法恢复所有命中位置。</p>')
    if finding.references:
        parts.append("<p>参考：</p><ul>")
        for reference in finding.references:
            if reference.url.startswith(("http://", "https://")):
                parts.append(f'<li><a href="{_e(reference.url)}">{_e(reference.title)}</a></li>')
            else:
                parts.append(f"<li>{_e(reference.title)}（{_e(reference.url)}）</li>")
        parts.append("</ul>")
    parts.append("</section>")
    return "".join(parts)


def _row(label: str, value: str) -> str:
    return f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>"


def _e(value: str) -> str:
    return html.escape(value, quote=True)
