"""Pure, stable finding search and atomic pagination. No terminal dependencies."""

from dataclasses import dataclass

from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.models import ScanReport, Severity
from mxready.tui.commands import Command

PAGE_SIZE = 5


@dataclass(frozen=True)
class FindingFilter:
    severity: Severity | None = None
    rule_id: str = ""
    file_query: str = ""
    text_query: str = ""


@dataclass(frozen=True)
class FindingPage:
    indices: tuple[int, ...]
    matched_total: int
    report_total: int
    page: int
    page_count: int


def matching_indices(report: ScanReport, filters: FindingFilter) -> tuple[int, ...]:
    file_query = filters.file_query.replace("\\", "/").casefold()
    query = filters.text_query.casefold()
    result = []
    for index, item in enumerate(report.findings):
        if filters.severity is not None and item.severity != filters.severity:
            continue
        if filters.rule_id and item.rule_id != filters.rule_id:
            continue
        if file_query and file_query not in item.relative_path.replace("\\", "/").casefold():
            continue
        if query and not any(
            query in value.casefold()
            for value in (
                item.title,
                item.rule_id,
                item.relative_path,
                item.evidence,
                item.message,
                item.recommendation,
                *(occurrence.evidence for occurrence in item.occurrences),
            )
        ):
            continue
        result.append(index)
    return tuple(result)


def browse(
    report: ScanReport,
    filters: FindingFilter,
    page: int,
    command: Command,
    cached: tuple[int, ...] | None = None,
    *,
    restore: bool = False,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[FindingFilter, FindingPage, tuple[int, ...]]:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    updated = (
        FindingFilter()
        if command.reset
        else FindingFilter(
            filters.severity
            if command.severity is None
            else (None if command.severity == "all" else Severity(command.severity)),
            filters.rule_id if command.rule is None else command.rule,
            filters.file_query if command.file is None else command.file,
            filters.text_query if command.query is None else command.query,
        )
    )
    indices = (
        cached if cached is not None and updated == filters else matching_indices(report, updated)
    )
    page_count = max(1, (len(indices) + PAGE_SIZE - 1) // PAGE_SIZE)
    target = (
        int(command.target)
        if command.target
        else (1 if command.reset or updated != filters else page)
    )
    if restore:
        target = max(1, min(target, page_count))
    if not 1 <= target <= page_count:
        raise ValueError(
            tr(
                language,
                f"页码范围: 1-{page_count}；当前条件与页码未改变。",
                f"Page range: 1-{page_count}; current filters and page are unchanged.",
            )
        )
    return (
        updated,
        FindingPage(
            indices[(target - 1) * PAGE_SIZE : target * PAGE_SIZE],
            len(indices),
            len(report.findings),
            target,
            page_count,
        ),
        indices,
    )
