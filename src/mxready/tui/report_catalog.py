"""Bounded, explicit report reads and untrusted batch-summary ingestion."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mxready.models import ScanReport
from mxready.reporting.comparison import normalize_repository
from mxready.reporting.source import describe_source
from mxready.tui.commands import safe_text

MAX_REPORT_BYTES = 20 * 1024 * 1024
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_BATCH_ITEMS = 1000


@dataclass(frozen=True)
class LoadedReport:
    path: Path
    digest: str
    report: ScanReport


@dataclass(frozen=True)
class ReportMetadata:
    path: Path
    digest: str
    scan_id: str
    repository: str
    commit: str
    scanned_at: str
    blocker: int
    warning: int
    info: int
    source: str
    static_status: str


def metadata(loaded: LoadedReport) -> ReportMetadata:
    report = loaded.report
    return ReportMetadata(
        loaded.path,
        loaded.digest,
        str(report.scan_id),
        report.repository.url,
        report.repository.commit,
        report.scanned_at.isoformat(),
        report.summary.blocker_count,
        report.summary.warning_count,
        report.summary.info_count,
        describe_source(report).label,
        report.static_status.value,
    )


def load_report(path: Path) -> LoadedReport:
    if not path.is_file():
        raise ValueError(f"JSON 报告不存在或不可读: {path}")
    with path.open("rb") as stream:
        payload = stream.read(MAX_REPORT_BYTES + 1)
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("报告不能超过 20 MiB。")
    try:
        report = ScanReport.model_validate_json(payload.decode("utf-8-sig"))
    except ValueError as error:
        raise ValueError(f"JSON/模型无效: {str(error)[:1000]}") from error
    return LoadedReport(path.resolve(), hashlib.sha256(payload).hexdigest(), report)


@dataclass(frozen=True)
class BatchItem:
    repository: str
    ref: str
    status: str
    error: str = ""
    loaded: ReportMetadata | None = None
    entry_id: int | None = None


@dataclass(frozen=True)
class BatchRead:
    items: tuple[BatchItem, ...]
    warning: str | None


def batch_report_path(output_dir: Path, value: str) -> Path:
    if (
        not value
        or value in {".", ".."}
        or any(c in value for c in "/\\:")
        or ".." in value
        or not value.endswith(".md")
    ):
        raise ValueError("批次报告路径必须是本次输出目录的直接子文件。")
    path = output_dir / (value[:-3] + ".json")
    if path.is_symlink() or path.resolve().parent != output_dir.resolve():
        raise ValueError("批次报告路径或符号链接越界。")
    return path


def read_batch(
    output_dir: Path,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_report: Callable[[LoadedReport], int | None] = lambda loaded: None,
) -> BatchRead:
    """Process one body at a time; retain only metadata, never all report bodies."""
    warning = None
    items: list[BatchItem] = []
    seen: set[Path] = set()
    try:
        path = output_dir / "batch-summary.csv"
        if path.is_symlink() or path.resolve().parent != output_dir.resolve():
            raise ValueError("汇总路径越界")
        with path.open("rb") as stream:
            payload = stream.read(MAX_CSV_BYTES + 1)
        if len(payload) > MAX_CSV_BYTES:
            raise ValueError("CSV 超过 2 MiB")
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        if not {"repository", "ref", "commit", "status", "report", "error"}.issubset(
            reader.fieldnames or []
        ):
            raise ValueError("CSV 字段缺失")
        for row in reader:
            if cancelled():
                warning = "批次结果读取已取消，未读取的任务状态未知。"
                break
            if len(items) >= MAX_BATCH_ITEMS:
                warning = f"条目已截断（最多 {MAX_BATCH_ITEMS}）；完整汇总: {path}"
                break
            if None in row or any(value is None for value in row.values()):
                raise ValueError("CSV 行字段数不一致")
            repository, ref, status = row["repository"], row["ref"], row["status"]
            if status == "failed":
                items.append(BatchItem(repository, ref, status, safe_text(row["error"][:1000])))
                continue
            try:
                if status not in {"passed", "warnings", "blocked"}:
                    raise ValueError("汇总状态无效")
                report_path = batch_report_path(output_dir, row["report"])
                seen.add(report_path.resolve())
                loaded = load_report(report_path)
                if (
                    normalize_repository(loaded.report.repository.url)
                    != normalize_repository(repository)
                    or loaded.report.repository.commit != row["commit"]
                ):
                    raise ValueError("汇总不一致：仓库或提交与 JSON 不匹配。")
                entry_id = on_report(loaded)
                items.append(
                    BatchItem(
                        repository,
                        ref,
                        loaded.report.static_status.value,
                        loaded=metadata(loaded),
                        entry_id=entry_id,
                    )
                )
            except (OSError, ValueError) as error:
                items.append(BatchItem(repository, ref, status, safe_text(str(error)[:1000])))
    except (OSError, ValueError, csv.Error) as error:
        warning = f"批次汇总不可用: {str(error)[:600]}；失败数量未知。"
        items.clear()
        seen.clear()
    # Also retain completed JSONs when the process failed/cancelled before writing CSV.
    for path in sorted(output_dir.glob("*.json")):
        if cancelled() or len(items) >= MAX_BATCH_ITEMS:
            if len(items) >= MAX_BATCH_ITEMS:
                warning = f"条目已截断；完整汇总: {output_dir / 'batch-summary.csv'}"
            break
        if (
            path.is_symlink()
            or path.resolve() in seen
            or path.resolve().parent != output_dir.resolve()
        ):
            continue
        try:
            loaded = load_report(path)
            entry_id = on_report(loaded)
            items.append(
                BatchItem(
                    loaded.report.repository.url,
                    "",
                    loaded.report.static_status.value,
                    loaded=metadata(loaded),
                    entry_id=entry_id,
                )
            )
        except (OSError, ValueError) as error:
            items.append(BatchItem(path.name, "", "invalid", safe_text(str(error)[:1000])))
    return BatchRead(tuple(items), warning)
