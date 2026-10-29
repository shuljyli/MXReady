"""批量评估多个公开仓库：逐仓复用安全获取与报告管线，输出汇总总表。

清单格式：每行一个仓库，`<https URL> [分支|标签|40位提交]`，`#` 开头为注释。
来源参数既可以是清单文件路径，也可以直接传仓库 URL。工具只服务开发者本机，
与 `mxready-scan-public` 共享同一套主机白名单、Git 限制和只读分析器。
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mxready.cli.generate_public_report import generate_public_report
from mxready.errors import MxReadyError
from mxready.models import ScanReport, Severity
from mxready.repository.identity import parse_repository_url

_TOP_RULE_LIMIT = 3
_LABEL_SANITIZE = re.compile(r"[^a-z0-9]+")

ScanOne = Callable[..., ScanReport]


@dataclass(frozen=True, slots=True)
class BatchEntry:
    repository_url: str
    requested_ref: str | None
    source_line: int


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    display: str
    label: str
    entry: BatchEntry
    report: ScanReport | None
    error: str | None


def load_batch_entries(source: str) -> list[BatchEntry]:
    """解析一个批量来源：直接 URL 视为单项清单，否则按文件逐行读取。"""
    if source.startswith("https://"):
        return [_entry_from_line(source, 1)]

    path = Path(source)
    if not path.is_file():
        raise ValueError(f"批量清单文件不存在: {path}")
    entries: list[BatchEntry] = []
    seen: set[tuple[str, str | None]] = set()
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entry = _entry_from_line(stripped.split(" #", 1)[0].strip(), line_number)
        key = (entry.repository_url, entry.requested_ref)
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


def _entry_from_line(line: str, line_number: int) -> BatchEntry:
    parts = line.split()
    if not 1 <= len(parts) <= 2:
        raise ValueError(f"批量清单第 {line_number} 行格式无效: {line!r}")
    repository_url, requested_ref = parts[0], parts[1] if len(parts) == 2 else None
    try:
        parse_repository_url(repository_url)
    except MxReadyError as error:
        raise ValueError(f"批量清单第 {line_number} 行仓库地址无效: {error.message}") from error
    return BatchEntry(
        repository_url=repository_url,
        requested_ref=requested_ref,
        source_line=line_number,
    )


def scan_batch(
    entries: Sequence[BatchEntry],
    *,
    output_dir: Path,
    work_dir: Path,
    scan_one: ScanOne | None = None,
    progress: Callable[[BatchOutcome], None] | None = None,
) -> list[BatchOutcome]:
    """逐仓扫描并收集结果；单仓失败不中断批量，错误记录进汇总。"""
    scan_fn: ScanOne = scan_one if scan_one is not None else generate_public_report
    outcomes: list[BatchOutcome] = []
    for entry in entries:
        try:
            identity = parse_repository_url(entry.repository_url)
        except MxReadyError as error:
            outcome = BatchOutcome(
                display=entry.repository_url,
                label="",
                entry=entry,
                report=None,
                error=f"{error.code}: {error.message}",
            )
            outcomes.append(outcome)
            if progress is not None:
                progress(outcome)
            continue

        base = _LABEL_SANITIZE.sub("-", f"{identity.owner}-{identity.name}".casefold()).strip("-")
        label_base = base[:48] or "repository"
        try:
            report = scan_fn(
                entry.repository_url,
                label=label_base,
                output_dir=output_dir,
                work_dir=work_dir,
                requested_ref=entry.requested_ref,
            )
            outcome = BatchOutcome(
                display=f"{identity.owner}/{identity.name}",
                label=f"{label_base}-{report.repository.commit[:12]}",
                entry=entry,
                report=report,
                error=None,
            )
        except (MxReadyError, OSError, ValueError) as error:
            code = error.code if isinstance(error, MxReadyError) else "OPERATIONAL_ERROR"
            message = error.message if isinstance(error, MxReadyError) else str(error)
            outcome = BatchOutcome(
                display=f"{identity.owner}/{identity.name}",
                label="",
                entry=entry,
                report=None,
                error=f"{code}: {message}",
            )
        outcomes.append(outcome)
        if progress is not None:
            progress(outcome)
    return outcomes


_CSV_HEADERS = [
    "repository",
    "ref",
    "commit",
    "status",
    "blocker",
    "warning",
    "info",
    "total",
    "top_rules",
    "report",
    "error",
]


def render_batch_csv(outcomes: Sequence[BatchOutcome]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADERS)
    for outcome in outcomes:
        writer.writerow(_csv_row(outcome))
    return buffer.getvalue()


def _csv_row(outcome: BatchOutcome) -> list[str]:
    report = outcome.report
    if report is None:
        return [
            outcome.display,
            outcome.entry.requested_ref or "",
            "",
            "failed",
            "",
            "",
            "",
            "",
            "",
            "",
            outcome.error or "",
        ]
    summary = report.summary
    return [
        report.repository.url,
        outcome.entry.requested_ref or "",
        report.repository.commit,
        report.static_status.value,
        str(summary.blocker_count),
        str(summary.warning_count),
        str(summary.info_count),
        str(summary.total_count),
        "; ".join(_top_rules(report)),
        f"{outcome.label}.md",
        "",
    ]


def _top_rules(report: ScanReport) -> list[str]:
    rules: list[str] = []
    for finding in report.findings:
        if finding.severity not in {Severity.BLOCKER, Severity.WARNING}:
            continue
        if finding.rule_id not in rules:
            rules.append(finding.rule_id)
        if len(rules) >= _TOP_RULE_LIMIT:
            break
    return rules


def render_batch_markdown(
    outcomes: Sequence[BatchOutcome],
    *,
    ruleset_version: str | None = None,
    ruleset_digest: str | None = None,
) -> str:
    succeeded = [outcome for outcome in outcomes if outcome.report is not None]
    blocked = sum(
        1
        for outcome in succeeded
        if outcome.report is not None and outcome.report.static_status.value == "blocked"
    )
    lines = [
        "# MXReady 批量迁移体检汇总",
        "",
        f"- 生成时间: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- 仓库数: {len(outcomes)}（成功 {len(succeeded)} · 失败 {len(outcomes) - len(succeeded)}"
        f" · 其中阻塞 {blocked}）",
    ]
    if ruleset_version is not None:
        digest_note = f"，规则集摘要 {ruleset_digest}" if ruleset_digest else ""
        lines.append(f"- 规则集版本: {ruleset_version}{digest_note}")
    lines.extend(
        [
            "",
            "| 仓库 | 提交 | 状态 | 阻断 | 警告 | 提示 | 主要规则 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for outcome in outcomes:
        lines.append(_markdown_row(outcome))
    return "\n".join(lines) + "\n"


def _markdown_row(outcome: BatchOutcome) -> str:
    report = outcome.report
    if report is None:
        reason = (outcome.error or "未知错误").replace("|", "\\|")
        return f"| {outcome.display} | - | 失败（{reason}） | - | - | - | - |"
    summary = report.summary
    commit = report.repository.commit[:12]
    rules = "、".join(_top_rules(report)) or "-"
    return (
        f"| [{outcome.display}]({report.repository.url}) "
        f"| `{commit}` | {report.static_status.value} "
        f"| {summary.blocker_count} | {summary.warning_count} | {summary.info_count} | {rules} |"
    )


def format_progress_line(index: int, total: int, outcome: BatchOutcome) -> str:
    if outcome.report is None:
        return f"[{index}/{total}] {outcome.display} → 失败: {outcome.error}"
    summary = outcome.report.summary
    counts = (
        f"阻断 {summary.blocker_count} · 警告 {summary.warning_count} · 提示 {summary.info_count}"
    )
    return f"[{index}/{total}] {outcome.display} → {outcome.report.static_status.value}（{counts}）"


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        entries: list[BatchEntry] = []
        for source in arguments.sources:
            entries.extend(load_batch_entries(source))
    except ValueError as error:
        print(f"MXReady batch error: {error}", file=sys.stderr)
        return 1
    if not entries:
        print("MXReady batch error: 清单为空。", file=sys.stderr)
        return 1

    output_dir = Path(arguments.output)
    work_dir = Path(arguments.work_dir)
    total = len(entries)
    counter = {"index": 0}

    def show(outcome: BatchOutcome) -> None:
        counter["index"] += 1
        print(format_progress_line(counter["index"], total, outcome))

    try:
        outcomes = scan_batch(
            entries,
            output_dir=output_dir,
            work_dir=work_dir,
            progress=show,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "batch-summary.csv").write_text(
            render_batch_csv(outcomes),
            encoding="utf-8-sig",
        )
        succeeded = [outcome.report for outcome in outcomes if outcome.report is not None]
        (output_dir / "batch-summary.md").write_text(
            render_batch_markdown(
                outcomes,
                ruleset_version=succeeded[0].ruleset_version if succeeded else None,
                ruleset_digest=succeeded[0].ruleset_digest if succeeded else None,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        print(f"MXReady batch error: {error}", file=sys.stderr)
        return 1

    succeeded_count = sum(1 for outcome in outcomes if outcome.report is not None)
    blocked_count = sum(
        1
        for outcome in outcomes
        if outcome.report is not None and outcome.report.static_status.value == "blocked"
    )
    print(
        f"汇总: 成功 {succeeded_count} · 失败 {total - succeeded_count}（其中阻塞 {blocked_count}）"
    )
    print(f"报告: {output_dir / 'batch-summary.csv'} 与 {output_dir / 'batch-summary.md'}")
    if succeeded_count < total:
        return 1
    if blocked_count:
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-scan-batch",
        description=(
            "Batch-scan multiple public GitHub/Gitee repositories and write "
            "a CSV/Markdown readiness summary."
        ),
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="清单文件路径或直接传一个仓库 HTTPS URL（可混合多个来源）",
    )
    parser.add_argument(
        "--output",
        default="data/batch",
        help="每仓报告与汇总文件的输出目录（默认 data/batch）",
    )
    parser.add_argument(
        "--work-dir",
        default="data/public-scan-work",
        help="临时克隆父目录，扫描后自动清理（默认 data/public-scan-work）",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
