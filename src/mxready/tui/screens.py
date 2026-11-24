"""Bounded report selection and comparison views; no filesystem/DB work here."""

from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option

from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.models import Finding, ScanReport
from mxready.reporting.comparison import ReportDifference
from mxready.reporting.source import describe_source
from mxready.sanitize import safe_text

CATALOG_PAGE_SIZE = 20


def _merge_bindings(current: BindingsMap, bindings: list[BindingType]) -> BindingsMap:
    """Localize our bindings without dropping default Tab/Escape handling."""
    merged = BindingsMap(bindings)
    for key, values in current.key_to_bindings.items():
        if key not in merged.key_to_bindings:
            merged.key_to_bindings[key] = list(values)
    return merged


def _picker_bindings(language: str) -> list[BindingType]:
    return [
        Binding("escape", "close", tr(language, "返回", "Back")),
        Binding("pageup", "previous", tr(language, "上一页", "Previous page")),
        Binding("pagedown", "next", tr(language, "下一页", "Next page")),
        Binding("i", "details", tr(language, "完整摘要", "Full summary")),
    ]


def _information_bindings(language: str) -> list[BindingType]:
    return [Binding("escape", "close", tr(language, "返回列表", "Back to list"))]


def _comparison_bindings(language: str) -> list[BindingType]:
    return [
        Binding("escape", "close", tr(language, "返回", "Back")),
        Binding("left", "previous_group", tr(language, "上一组", "Previous group")),
        Binding("right", "next_group", tr(language, "下一组", "Next group")),
        Binding("pageup", "previous", tr(language, "上一页", "Previous page")),
        Binding("pagedown", "next", tr(language, "下一页", "Next page")),
        Binding("up", "scroll_content_up", tr(language, "向上滚动", "Scroll up")),
        Binding("down", "scroll_content_down", tr(language, "向下滚动", "Scroll down")),
    ]


def _comparison_groups(language: str) -> tuple[str, ...]:
    if language == "en":
        return ("Added", "Removed", "Retained", "Severity changes", "Count changes")
    return ("新增", "消失", "保留", "级别变化", "次数变化")


@dataclass(frozen=True)
class ReportChoice:
    key: str
    entry_id: int | None
    label: str
    reason: str = ""


class ReportPicker(ModalScreen[int | None]):
    BINDINGS = _picker_bindings(DEFAULT_LANGUAGE)
    DEFAULT_CSS = """
    ReportPicker { align: center middle; background: #00000099; }
    ReportPicker > Vertical { width: 95%; height: 90%; border: round #76ddc2;
        background: #181e29; padding: 1; }
    ReportPicker #picker-title { height: auto; max-height: 5; }
    ReportPicker Input { height: 3; }
    ReportPicker OptionList { height: 1fr; }
    ReportPicker #picker-page { height: auto; }
    """

    def __init__(
        self,
        choices: tuple[ReportChoice, ...],
        *,
        query: str = "",
        title: str | None = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self.choices = choices
        self.search = query
        self.heading = (
            title if title is not None else tr(self.language, "报告选择器", "Report selector")
        )
        self.page = 1
        self._bindings = _merge_bindings(self._bindings, _picker_bindings(self.language))

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(safe_text(self.heading), id="picker-title", markup=False)
            yield Input(
                value=self.search,
                placeholder=tr(
                    self.language,
                    "搜索仓库、提交、路径或批次状态",
                    "Search repository, commit, path, or batch status",
                ),
                max_length=256,
                id="report-query",
            )
            yield OptionList(id="report-choices", markup=False)
            yield Static(id="picker-page", markup=False)

    def on_mount(self) -> None:
        self.refresh_bindings()
        self._render_page()
        self.query_one("#report-choices").focus()

    def _render_page(self) -> None:
        matched = [item for item in self.choices if self.search.casefold() in item.label.casefold()]
        pages = max(1, (len(matched) + CATALOG_PAGE_SIZE - 1) // CATALOG_PAGE_SIZE)
        self.page = max(1, min(self.page, pages))
        options = self.query_one("#report-choices", OptionList)
        options.clear_options()
        for item in matched[(self.page - 1) * CATALOG_PAGE_SIZE : self.page * CATALOG_PAGE_SIZE]:
            options.add_option(
                Option(
                    Text(
                        safe_text(
                            item.label[:8192] + (f"\n{item.reason[:1000]}" if item.reason else "")
                        )
                    ),
                    id=item.key,
                    disabled=item.entry_id is None or bool(item.reason),
                )
            )
        if options.option_count:
            options.highlighted = 0
        self.query_one("#picker-page", Static).update(
            tr(
                self.language,
                f"{self.page}/{pages} 页 · {len(matched)} 条 · 缓存摘要为上次读取\n"
                "↑↓ 选择 · Enter 打开 · Tab 搜索 · i 完整摘要 · PgUp/PgDn 翻页 · Esc 返回",
                f"{self.page}/{pages} pages · {len(matched)} entries · cached summaries are from "
                "the last read\n"
                "↑↓ select · Enter open · Tab search · i full summary · PgUp/PgDn pages · Esc back",
            )
        )

    @on(Input.Changed, "#report-query")
    def search_changed(self, event: Input.Changed) -> None:
        self.search, self.page = event.value, 1
        self._render_page()

    @on(Input.Submitted, "#report-query")
    def focus_results(self) -> None:
        self.query_one("#report-choices").focus()

    @on(OptionList.OptionSelected, "#report-choices")
    def selected(self, event: OptionList.OptionSelected) -> None:
        choice = next((item for item in self.choices if item.key == event.option.id), None)
        if choice and choice.entry_id is not None and not choice.reason:
            self.dismiss(choice.entry_id)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_details(self) -> None:
        options = self.query_one("#report-choices", OptionList)
        if options.highlighted is None:
            return
        key = options.get_option_at_index(options.highlighted).id
        item = next((item for item in self.choices if item.key == key), None)
        if item:
            self.app.push_screen(ReportInformationScreen(item, language=self.language))

    def action_previous(self) -> None:
        self.page = max(1, self.page - 1)
        self._render_page()

    def action_next(self) -> None:
        self.page += 1
        self._render_page()


class ReportInformationScreen(ModalScreen[None]):
    """Let keyboard users read a wrapped catalog row even on very small terminals."""

    BINDINGS = _information_bindings(DEFAULT_LANGUAGE)
    DEFAULT_CSS = """
    ReportInformationScreen { align: center middle; background: #00000099; }
    ReportInformationScreen > Vertical { width: 95%; height: 90%;
        border: round #76ddc2; background: #181e29; padding: 1; }
    ReportInformationScreen RichLog { height: 1fr; }
    ReportInformationScreen Static { height: auto; }
    """

    def __init__(self, item: ReportChoice, language: str = DEFAULT_LANGUAGE) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self.item = item
        self._bindings = _merge_bindings(self._bindings, _information_bindings(self.language))

    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(wrap=True, min_width=10, auto_scroll=False, id="catalog-information")
            yield Static(
                tr(
                    self.language,
                    "上次读取的摘要 · ↑↓ / PgUp/PgDn 滚动 · Esc 返回列表",
                    "Summary from the last read · ↑↓ / PgUp/PgDn scroll · Esc back to list",
                ),
                markup=False,
            )

    def on_mount(self) -> None:
        self.refresh_bindings()
        log = self.query_one("#catalog-information", RichLog)
        log.write(Text(safe_text(self.item.label[:8192] + "\n" + self.item.reason[:1000])))
        log.focus()

    def action_close(self) -> None:
        self.dismiss(None)


class ComparisonScreen(ModalScreen[None]):
    BINDINGS = _comparison_bindings(DEFAULT_LANGUAGE)
    DEFAULT_CSS = """
    ComparisonScreen { align: center middle; background: #00000099; }
    ComparisonScreen > Vertical { width: 95%; height: 95%; border: round #76ddc2;
        background: #181e29; padding: 0 1; }
    ComparisonScreen #compare-groups { height: auto; }
    ComparisonScreen Button { min-width: 6; width: 1fr; padding: 0; }
    ComparisonScreen RichLog { height: 1fr; }
    ComparisonScreen #compare-page { height: auto; }
    """
    GROUPS = _comparison_groups(DEFAULT_LANGUAGE)

    def __init__(
        self,
        baseline: ScanReport,
        current: ScanReport,
        difference: ReportDifference,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self.groups = _comparison_groups(self.language)
        self.baseline, self.current, self.difference = baseline, current, difference
        self.group, self.page = 0, 1
        self._bindings = _merge_bindings(self._bindings, _comparison_bindings(self.language))

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="compare-groups"):
                for index, label in enumerate(self.groups):
                    yield Button(label, id=f"group-{index}")
            yield RichLog(
                max_lines=1000, wrap=True, min_width=10, auto_scroll=False, id="difference"
            )
            yield Static(id="compare-page", markup=False)

    def on_mount(self) -> None:
        self.refresh_bindings()
        self._render_page()

    def _items(self) -> tuple[Finding, ...]:
        diff = self.difference
        return (
            diff.added,
            diff.removed,
            diff.retained,
            tuple(c.after for c in diff.changes if c.severity_changed),
            tuple(c.after for c in diff.changes if c.count_changed),
        )[self.group]

    def _render_page(self) -> None:
        log = self.query_one("#difference", RichLog)
        log.clear()

        def write(value: str) -> None:
            log.write(Text(safe_text(value[:8192])))

        baseline_label = tr(self.language, "基线", "Baseline")
        current_label = tr(self.language, "当前", "Current")
        for side, report in ((baseline_label, self.baseline), (current_label, self.current)):
            source = describe_source(report, self.language)
            write(
                tr(
                    self.language,
                    f"{side}: {report.scan_id}\n提交 {report.repository.commit}\n"
                    f"扫描 {report.scanned_at.isoformat()} · {source.label}",
                    f"{side}: {report.scan_id}\nCommit {report.repository.commit}\n"
                    f"Scanned {report.scanned_at.isoformat()} · {source.label}",
                )
            )
            for label, value in source.fields:
                write(f"{label}: {value}")
            if report.coverage:
                write(
                    tr(
                        self.language,
                        f"范围 {report.coverage.analyzed_files} 文件 / "
                        f"{report.coverage.analyzed_bytes} 字节；"
                        f"跳过 {report.coverage.skipped_by_reason}；"
                        f"排除目录 {report.coverage.excluded_directories}",
                        f"Scope {report.coverage.analyzed_files} files / "
                        f"{report.coverage.analyzed_bytes} bytes; "
                        f"skipped {report.coverage.skipped_by_reason}; "
                        f"excluded directories {report.coverage.excluded_directories}",
                    )
                )
            else:
                write(tr(self.language, "扫描范围未记录", "Scan scope not recorded"))
        diff = self.difference
        write(
            tr(
                self.language,
                f"分析条件: {diff.conditions_status}；来源差异单独展示。",
                f"Analysis conditions: {diff.conditions_status}; source differences are shown "
                "separately.",
            )
        )
        for condition in diff.condition_differences:
            write(
                f"{condition.field}: {str(condition.before)[:1200]} → {str(condition.after)[:1200]}"
            )
        for warning in (*diff.condition_warnings, *diff.source_warnings):
            write(warning)
        write(
            tr(
                self.language,
                "消失不等于已修复；排除、规则及扫描范围均可能影响结果。级别与次数变化可重叠。",
                "Removed does not mean fixed; exclusions, rules, and scan scope can all affect "
                "results. Severity and count changes may overlap.",
            )
        )
        items = self._items()
        pages = max(1, (len(items) + 4) // 5)
        self.page = max(1, min(self.page, pages))
        write(
            tr(
                self.language,
                f"\n{self.groups[self.group]} · {len(items)} 项",
                f"\n{self.groups[self.group]} · {len(items)} items",
            )
        )
        changes = {(c.after.rule_id, c.after.relative_path): c for c in diff.changes}
        for item in items[(self.page - 1) * 5 : self.page * 5]:
            write(
                f"\n{item.rule_id} {item.title[:200]}\n{item.relative_path}:{item.line_start}\n"
                f"{item.severity.value} ×{item.count}"
            )
            change = changes.get((item.rule_id, item.relative_path))
            if change and self.group >= 3:
                write(
                    tr(
                        self.language,
                        f"原先 {change.before.severity.value} ×{change.before.count} → "
                        f"现在 {item.severity.value} ×{item.count}",
                        f"Before {change.before.severity.value} ×{change.before.count} → "
                        f"now {item.severity.value} ×{item.count}",
                    )
                )
            write(
                tr(
                    self.language,
                    f"证据: {item.evidence[:600]}\n建议: {item.recommendation[:1000]}",
                    f"Evidence: {item.evidence[:600]}\n"
                    f"Recommendation: {item.recommendation[:1000]}",
                )
            )
        self.query_one("#compare-page", Static).update(
            tr(
                self.language,
                f"{self.groups[self.group]} {self.page}/{pages} 页 · "
                "←→ 切组 · ↑↓ 滚动 · PgUp/PgDn 翻页 · Esc 返回",
                f"{self.groups[self.group]} page {self.page}/{pages} · "
                "←→ switch group · ↑↓ scroll · PgUp/PgDn page · Esc back",
            )
        )

    @on(Button.Pressed)
    def change_group(self, event: Button.Pressed) -> None:
        self.group, self.page = int((event.button.id or "group-0").split("-")[1]), 1
        self._render_page()

    def action_previous_group(self) -> None:
        self.group, self.page = (self.group - 1) % 5, 1
        self._render_page()

    def action_next_group(self) -> None:
        self.group, self.page = (self.group + 1) % 5, 1
        self._render_page()

    def action_previous(self) -> None:
        self.page = max(1, self.page - 1)
        self._render_page()

    def action_next(self) -> None:
        self.page += 1
        self._render_page()

    def action_close(self) -> None:
        self.dismiss(None)

    def action_scroll_content_up(self) -> None:
        self.query_one("#difference", RichLog).scroll_up()

    def action_scroll_content_down(self) -> None:
        self.query_one("#difference", RichLog).scroll_down()


class SecretInputScreen(ModalScreen[str | None]):
    """Collect a secret without echoing it or adding it to command history."""

    DEFAULT_CSS = """
    SecretInputScreen { align: center middle; background: #00000099; }
    SecretInputScreen > Vertical { width: 70; height: auto; border: round #76ddc2;
        background: #181e29; padding: 1 2; }
    SecretInputScreen #secret-title { height: auto; text-style: bold; color: #76ddc2; }
    SecretInputScreen #secret-prompt { height: auto; margin-bottom: 1; }
    SecretInputScreen Input { height: 3; }
    SecretInputScreen #secret-error { height: auto; color: #f2b47e; }
    SecretInputScreen Horizontal { height: 3; align: right middle; }
    SecretInputScreen Button { margin-left: 2; }
    """

    def __init__(
        self,
        *,
        title: str,
        prompt: str,
        language: str = DEFAULT_LANGUAGE,
        max_length: int = 8192,
        minimum_length: int = 1,
    ) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self.heading = title
        self.prompt = prompt
        self.max_length = max(1, min(max_length, 8192))
        self.minimum_length = max(1, min(minimum_length, self.max_length))
        self._bindings = _merge_bindings(
            self._bindings,
            [Binding("escape", "cancel", tr(self.language, "取消", "Cancel"))],
        )

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(safe_text(self.heading), id="secret-title", markup=False)
            yield Static(safe_text(self.prompt), id="secret-prompt", markup=False)
            yield Input(
                password=True,
                max_length=self.max_length,
                id="secret-value",
            )
            yield Static("", id="secret-error", markup=False)
            with Horizontal():
                yield Button(
                    tr(self.language, "保存", "Save"), id="secret-save", variant="primary"
                )
                yield Button(tr(self.language, "取消", "Cancel"), id="secret-cancel")

    def on_mount(self) -> None:
        self.refresh_bindings()
        self.query_one("#secret-value", Input).focus()

    @on(Input.Submitted, "#secret-value")
    def submitted(self) -> None:
        self._submit()

    @on(Button.Pressed, "#secret-save")
    def save(self) -> None:
        self._submit()

    @on(Button.Pressed, "#secret-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        value = self.query_one("#secret-value", Input).value.strip()
        if len(value) < self.minimum_length:
            self.query_one("#secret-error", Static).update(
                tr(
                    self.language,
                    f"至少需要 {self.minimum_length} 个字符。",
                    f"At least {self.minimum_length} characters are required.",
                )
            )
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
