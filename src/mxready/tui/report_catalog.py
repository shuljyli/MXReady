"""Bounded, explicit report reads and untrusted batch-summary ingestion."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.models import ScanReport
from mxready.reporting.comparison import normalize_repository
from mxready.reporting.source import describe_source
from mxready.sanitize import safe_text

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


def metadata(loaded: LoadedReport, language: str = DEFAULT_LANGUAGE) -> ReportMetadata:
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
        describe_source(report, language).label,
        report.static_status.value,
    )


def load_report(path: Path, language: str = DEFAULT_LANGUAGE) -> LoadedReport:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    if not path.is_file():
        raise ValueError(
            tr(
                language,
                f"JSON 报告不存在或不可读: {path}",
                f"JSON report not found or unreadable: {path}",
            )
        )
    with path.open("rb") as stream:
        payload = stream.read(MAX_REPORT_BYTES + 1)
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError(tr(language, "报告不能超过 20 MiB。", "Report must not exceed 20 MiB."))
    try:
        report = ScanReport.model_validate_json(payload.decode("utf-8-sig"))
    except ValueError as error:
        raise ValueError(
            tr(
                language,
                f"JSON/模型无效: {str(error)[:1000]}",
                f"Invalid JSON/model: {str(error)[:1000]}",
            )
        ) from error
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


def batch_report_path(output_dir: Path, value: str, language: str = DEFAULT_LANGUAGE) -> Path:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    if (
        not value
        or value in {".", ".."}
        or any(c in value for c in "/\\:")
        or ".." in value
        or not value.endswith(".md")
    ):
        raise ValueError(
            tr(
                language,
                "批次报告路径必须是本次输出目录的直接子文件。",
                "Batch report path must be a direct child file of this output directory.",
            )
        )
    path = output_dir / (value[:-3] + ".json")
    if path.is_symlink() or path.resolve().parent != output_dir.resolve():
        raise ValueError(
            tr(
                language,
                "批次报告路径或符号链接越界。",
                "Batch report path or symlink escapes the output directory.",
            )
        )
    return path


def read_batch(
    output_dir: Path,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_report: Callable[[LoadedReport], int | None] = lambda loaded: None,
    language: str = DEFAULT_LANGUAGE,
) -> BatchRead:
    """Process one body at a time; retain only metadata, never all report bodies."""
    language = normalize_language(language) or DEFAULT_LANGUAGE
    warning = None
    items: list[BatchItem] = []
    seen: set[Path] = set()
    try:
        path = output_dir / "batch-summary.csv"
        if path.is_symlink() or path.resolve().parent != output_dir.resolve():
            raise ValueError(
                tr(language, "汇总路径越界", "Summary path escapes the output directory")
            )
        with path.open("rb") as stream:
            payload = stream.read(MAX_CSV_BYTES + 1)
        if len(payload) > MAX_CSV_BYTES:
            raise ValueError(tr(language, "CSV 超过 2 MiB", "CSV exceeds 2 MiB"))
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        if not {"repository", "ref", "commit", "status", "report", "error"}.issubset(
            reader.fieldnames or []
        ):
            raise ValueError(tr(language, "CSV 字段缺失", "CSV fields are missing"))
        for row in reader:
            if cancelled():
                warning = tr(
                    language,
                    "批次结果读取已取消，未读取的任务状态未知。",
                    "Batch result reading was cancelled; statuses of unread tasks are unknown.",
                )
                break
            if len(items) >= MAX_BATCH_ITEMS:
                warning = tr(
                    language,
                    f"条目已截断（最多 {MAX_BATCH_ITEMS}）；完整汇总: {path}",
                    f"Items truncated (maximum {MAX_BATCH_ITEMS}); full summary: {path}",
                )
                break
            if None in row or any(value is None for value in row.values()):
                raise ValueError(tr(language, "CSV 行字段数不一致", "CSV row field count mismatch"))
            repository, ref, status = row["repository"], row["ref"], row["status"]
            if status == "failed":
                items.append(BatchItem(repository, ref, status, safe_text(row["error"][:1000])))
                continue
            try:
                if status not in {"passed", "warnings", "blocked"}:
                    raise ValueError(tr(language, "汇总状态无效", "Invalid summary status"))
                report_path = batch_report_path(output_dir, row["report"], language)
                seen.add(report_path.resolve())
                loaded = load_report(report_path, language)
                if (
                    normalize_repository(loaded.report.repository.url)
                    != normalize_repository(repository)
                    or loaded.report.repository.commit != row["commit"]
                ):
                    raise ValueError(
                        tr(
                            language,
                            "汇总不一致：仓库或提交与 JSON 不匹配。",
                            "Summary mismatch: repository or commit does not match the JSON.",
                        )
                    )
                entry_id = on_report(loaded)
                items.append(
                    BatchItem(
                        repository,
                        ref,
                        loaded.report.static_status.value,
                        loaded=metadata(loaded, language),
                        entry_id=entry_id,
                    )
                )
            except (OSError, ValueError) as error:
                items.append(BatchItem(repository, ref, status, safe_text(str(error)[:1000])))
    except (OSError, ValueError, csv.Error) as error:
        warning = tr(
            language,
            f"批次汇总不可用: {str(error)[:600]}；失败数量未知。",
            f"Batch summary unavailable: {str(error)[:600]}; failure count unknown.",
        )
        items.clear()
        seen.clear()
    # Also retain completed JSONs when the process failed/cancelled before writing CSV.
    for path in sorted(output_dir.glob("*.json")):
        if cancelled() or len(items) >= MAX_BATCH_ITEMS:
            if len(items) >= MAX_BATCH_ITEMS:
                warning = tr(
                    language,
                    f"条目已截断；完整汇总: {output_dir / 'batch-summary.csv'}",
                    f"Items truncated; full summary: {output_dir / 'batch-summary.csv'}",
                )
            break
        if (
            path.is_symlink()
            or path.resolve() in seen
            or path.resolve().parent != output_dir.resolve()
        ):
            continue
        try:
            loaded = load_report(path, language)
            entry_id = on_report(loaded)
            items.append(
                BatchItem(
                    loaded.report.repository.url,
                    "",
                    loaded.report.static_status.value,
                    loaded=metadata(loaded, language),
                    entry_id=entry_id,
                )
            )
        except (OSError, ValueError) as error:
            items.append(BatchItem(path.name, "", "invalid", safe_text(str(error)[:1000])))
    return BatchRead(tuple(items), warning)
