"""A full-screen command workspace for the existing MXReady analysis pipeline."""

from __future__ import annotations

import asyncio
import subprocess
from collections import deque
from collections.abc import Iterable
from dataclasses import asdict
from functools import partial
from pathlib import Path

from rich.table import Table
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Input, LoadingIndicator, OptionList, RichLog, Static
from textual.widgets.option_list import Option
from textual.worker import Worker

from mxready import __version__
from mxready.models import ScanReport, Severity
from mxready.reporting.comparison import compare_reports, normalize_repository
from mxready.reporting.source import describe_source
from mxready.tui.commands import (
    COMMANDS,
    Command,
    make_scan_job,
    new_output_directory,
    parse_command,
    read_report,
    resolve_path,
    safe_text,
)
from mxready.tui.process import run_tool
from mxready.tui.report_browser import FindingFilter, FindingPage, browse
from mxready.tui.report_catalog import load_report, read_batch
from mxready.tui.screens import ComparisonScreen, ReportChoice, ReportPicker
from mxready.tui.screenshot import align_svg_cells
from mxready.tui.state_store import ReportEntry, StateStore
from mxready.verification.bundle import build_verification_bundle

_ACCENT = "#76ddc2"
_MUTED = "#939fb1"


class CommandInput(Input):
    class Navigate(Message):
        def __init__(self, direction: int) -> None:
            super().__init__()
            self.direction = direction

    class Complete(Message):
        pass

    def on_key(self, event: events.Key) -> None:
        if event.key in {"up", "down", "tab"}:
            event.prevent_default()
            event.stop()
            if event.key == "tab":
                self.post_message(self.Complete())
            else:
                self.post_message(self.Navigate(-1 if event.key == "up" else 1))


class TranscriptLog(RichLog):
    class Resized(Message):
        pass

    def on_resize(self, event: events.Resize) -> None:
        super().on_resize(event)
        self.post_message(self.Resized())


class MXReadyApp(App[None]):
    TITLE = "MXReady"
    AUTO_FOCUS = "#command"
    BINDINGS = [
        Binding("ctrl+q", "quit", "退出", priority=True),
        Binding("ctrl+c", "interrupt", "取消 / 清空", priority=True),
        Binding("ctrl+l", "clear", "清屏", priority=True),
        Binding("escape", "dismiss", "", show=False),
        Binding("pageup", "scroll_up", "", show=False),
        Binding("pagedown", "scroll_down", "", show=False),
    ]
    CSS = """
    Screen { background: #0e1118; color: #d7dde8; }
    #topbar { height: 3; padding: 1 2 0 2; background: #0e1118; }
    #brand { width: 1fr; color: #76ddc2; text-style: bold; }
    #version { width: auto; color: #758198; }
    #workspace { height: 1fr; }
    #main { width: 1fr; padding: 0 2; }
    #conversation { height: 1fr; }
    #welcome { height: 1fr; align: center middle; }
    #welcome-text { width: auto; height: auto; text-align: center; }
    #transcript { height: 1fr; padding: 1 0; background: #0e1118; scrollbar-size: 1 1; }
    #suggestions { height: auto; max-height: 12; background: #1b2230;
                   border: round #354258; padding: 0 1; margin-bottom: 1; }
    #composer { height: 5; border-left: thick #76ddc2; background: #181e29; padding: 0 1; }
    #mode { height: 1; color: #76ddc2; padding-left: 1; }
    #command { height: 3; border: none; background: #181e29; padding: 1; }
    #command:focus { border: none; }
    #hint { height: 2; padding-top: 1; color: #758198; }
    #sidebar { width: 30; padding: 1 2; border-left: solid #242c3c; }
    .section { color: #6f819a; margin-top: 1; margin-bottom: 1; text-style: bold; }
    .context { height: auto; margin-bottom: 1; }
    #task-state { color: #76ddc2; }
    #activity { height: 1; width: 12; }
    Footer { background: #111722; color: #939fb1; }
    """

    def __init__(
        self,
        *,
        project_dir: Path,
        output_dir: Path | None = None,
        state_path: Path | None = None,
        default_output_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.project_dir = project_dir
        self.output_dir = output_dir or default_output_dir or project_dir / "reports"
        self._explicit_output = output_dir is not None
        self.store = StateStore(state_path)
        self._state_ready = asyncio.Event()
        self._state_warning_shown = False
        self._shutting_down = False
        self.view_generation = 0
        self._filter_generation = 0
        self.filters = FindingFilter()
        self.finding_page = 1
        self._matched: tuple[int, ...] | None = None
        self._digest = ""
        self._entry_id: int | None = None
        self._scan_worker: Worker[None] | None = None
        self._catalog_cancel = asyncio.Event()
        self.last_report: Path | None = None
        self.current_report: ScanReport | None = None
        self.history: list[str] = []
        self.busy = False
        self._cancel = asyncio.Event()
        self._history_index = 0
        self._draft = ""
        self._history_value: str | None = None
        self._output_buffer = ""
        self._transcript: deque[Text | Table] = deque(maxlen=1000)

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static("MXREADY  /  TERMINAL", id="brand")
            yield Static(f"v{__version__}", id="version")
        with Horizontal(id="workspace"):
            with Vertical(id="main"):
                with Container(id="conversation"):
                    with Container(id="welcome"):
                        yield Static(self._welcome(), id="welcome-text")
                    yield TranscriptLog(max_lines=4000, min_width=20, wrap=True, id="transcript")
                yield OptionList(id="suggestions", markup=False, compact=True)
                with Vertical(id="composer"):
                    yield Static("迁移检查  ·  只读静态分析", id="mode")
                    yield CommandInput(placeholder="输入项目路径、仓库 URL 或 /help", id="command")
                yield Static(
                    "Enter 运行   / 命令   Tab 补全   ↑↓ 历史   Ctrl+P 命令面板", id="hint"
                )
            with Vertical(id="sidebar"):
                yield Static("项目  PROJECT", classes="section")
                yield Static(Text(safe_text(self.project_dir.name)), classes="context")
                yield Static("读取项目状态…", id="branch", classes="context", markup=False)
                yield Static("任务  TASK", classes="section")
                yield Static("● READY", id="task-state", classes="context")
                yield LoadingIndicator(id="activity")
                yield Static("最近报告  REPORT", classes="section")
                yield Static(
                    "还没有扫描结果\n输入 /scan 开始", id="report-state", classes="context"
                )
                yield Static("输出  OUTPUT", classes="section")
                yield Static(
                    Text(safe_text(str(self.output_dir))), id="output-path", classes="context"
                )
                yield Static("静态风险与硬件验证分开记录。", classes="section")
        yield Footer()

    def _welcome(self) -> Text:
        welcome = Text(
            "███╗   ███╗██╗  ██╗\n████╗ ████║╚██╗██╔╝\n"
            "██╔████╔██║ ╚███╔╝ \n██║╚██╔╝██║ ██╔██╗ \n"
            "██║ ╚═╝ ██║██╔╝ ██╗\n╚═╝     ╚═╝╚═╝  ╚═╝",
            style=_ACCENT,
        )
        welcome.append("\n\nM X R E A D Y\n", style="bold #e4eaf4")
        welcome.append("PyTorch CUDA → MetaX MXMACA\n\n", style=_MUTED)
        welcome.append(
            "/scan .     扫描当前项目\n/public URL   扫描公开仓库\n/help       查看全部命令",
            style=_MUTED,
        )
        return welcome

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.query_one("#transcript").display = False
        self.query_one("#suggestions").display = False
        self.query_one("#activity").display = False
        self._responsive(self.size.width, self.size.height)
        self.run_worker(self._load_branch(), exit_on_error=False)
        self.run_worker(self._load_state(), exit_on_error=False)

    async def _load_state(self) -> None:
        try:
            restored = await asyncio.to_thread(self.store.initialize, self.project_dir)
            if self._shutting_down:
                return
            self.history = list(restored.history)
            self._history_index = len(self.history)
            if not self._explicit_output and restored.output_dir is not None:
                self.output_dir = restored.output_dir
                self.query_one("#output-path", Static).update(Text(safe_text(str(self.output_dir))))
            self._state_warning()
        finally:
            self._state_ready.set()

    def _state_warning(self) -> None:
        if self.store.warning and not self._state_warning_shown:
            self._write(self.store.warning, "#f2b47e")
            self._state_warning_shown = True

    async def _remember(self, command: Command) -> None:
        await asyncio.to_thread(self.store.add_history, self.project_dir, command)
        if not self._shutting_down:
            self._state_warning()

    async def _load_branch(self) -> None:
        def branch() -> str:
            try:
                result = subprocess.run(
                    ["git", "-C", str(self.project_dir), "branch", "--show-current"],
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=3,
                    check=False,
                )
                return result.stdout.strip() if result.returncode == 0 else ""
            except (OSError, subprocess.SubprocessError):
                return ""

        value = await asyncio.to_thread(branch)
        if self._shutting_down or not self.query("#branch"):
            return
        self.query_one("#branch", Static).update(
            Text(safe_text(value or "本地目录 / detached HEAD"))
        )

    def on_resize(self, event: events.Resize) -> None:
        if len(self.query("#sidebar")):
            self._responsive(event.size.width, event.size.height)

    @on(TranscriptLog.Resized)
    def reflow_output(self) -> None:
        self._reflow()

    def _reflow(self) -> None:
        # A resize message may outlive the widget while the screen is unmounting.
        for log in self.query(TranscriptLog):
            if log.is_mounted and log.display:
                log.clear()
                for value in self._transcript:
                    log.write(value)

    def _responsive(self, width: int, height: int) -> None:
        self.query_one("#sidebar").display = width >= 100 and height >= 24
        self.query_one("#hint").display = width >= 70 and height >= 24

    def _write(self, value: str, style: str = "") -> None:
        bounded = value[:16_384] + (
            "\n…（显示已截断，完整内容见报告文件）" if len(value) > 16_384 else ""
        )
        self._append(Text(safe_text(bounded), style=style))

    def _append(self, value: Text | Table) -> None:
        self._transcript.append(value)
        self.query_one("#welcome").display = False
        self.query_one("#transcript").display = True
        self.query_one("#transcript", RichLog).write(value)

    def _state(self, label: str) -> None:
        self.query_one("#task-state", Static).update(Text(label, style=_ACCENT))
        self.query_one("#mode", Static).update(
            Text(
                "扫描中  ·  /cancel 或 Ctrl+C 中断" if self.busy else "迁移检查  ·  只读静态分析",
                style=_ACCENT,
            )
        )
        self.query_one("#activity").display = self.busy

    @on(Input.Changed, "#command")
    def suggest(self, event: Input.Changed) -> None:
        choices = self.query_one("#suggestions", OptionList)
        value = event.value
        if value == self._history_value:
            choices.display = False
            return
        self._history_value = None
        matches = [name for name in COMMANDS if f"/{name}".startswith(value)]
        choices.clear_options()
        choices.display = bool(
            value.startswith("/") and " " not in value and value[1:] not in COMMANDS and matches
        )
        if choices.display:
            for name in matches:
                choices.add_option(Option(Text(f"/{name:<10} {COMMANDS[name][1]}"), id=name))
            choices.highlighted = 0

    @on(CommandInput.Navigate)
    def navigate(self, event: CommandInput.Navigate) -> None:
        choices = self.query_one("#suggestions", OptionList)
        if choices.display:
            if event.direction < 0:
                choices.action_cursor_up()
            else:
                choices.action_cursor_down()
            return
        entry = self.query_one("#command", Input)
        if self._history_index == len(self.history):
            self._draft = entry.value
        self._history_index = max(0, min(len(self.history), self._history_index + event.direction))
        value = (
            self.history[self._history_index]
            if self._history_index < len(self.history)
            else self._draft
        )
        self._history_value = value
        entry.value = value
        entry.cursor_position = len(value)

    @on(CommandInput.Complete)
    def complete(self) -> None:
        choices = self.query_one("#suggestions", OptionList)
        if choices.display and choices.highlighted is not None:
            name = choices.get_option_at_index(choices.highlighted).id
            if name is not None:
                self._prefill(name)

    @on(OptionList.OptionSelected, "#suggestions")
    def select_command(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is not None:
            self._prefill(event.option.id)

    def _prefill(self, name: str) -> None:
        entry = self.query_one("#command", Input)
        entry.value = f"/{name}" + (" " if COMMANDS[name][0] else "")
        entry.cursor_position = len(entry.value)
        entry.focus()
        self.query_one("#suggestions").display = False

    @on(Input.Submitted, "#command")
    async def submit(self, event: Input.Submitted) -> None:
        await self._state_ready.wait()
        raw = event.value.strip()
        if not raw:
            return
        if self.query_one("#suggestions").display:
            self.complete()
            return
        self.query_one("#command", Input).value = ""
        if not self.history or self.history[-1] != raw:
            self.history.append(raw)
            self.history = self.history[-200:]
        self._history_index = len(self.history)
        self._write(f"\n› {raw}", "bold #dce5f4")
        try:
            command = parse_command(raw)
            if command.name == "quit":
                await self._remember(command)
                await self.action_quit()
                return
            elif command.name == "cancel":
                self.action_interrupt()
            elif command.name == "help":
                self._help()
            elif command.name == "clear":
                self.action_clear()
            elif command.name == "findings":
                self.run_worker(self._apply_filters(command), exit_on_error=False)
                return
            elif command.name == "output":
                if self.busy:
                    raise ValueError("请等待当前任务结束后再修改输出目录。")
                if command.target:
                    self.output_dir = resolve_path(command.target, self.project_dir)
                    await asyncio.to_thread(
                        self.store.set_output, self.project_dir, self.output_dir
                    )
                self.query_one("#output-path", Static).update(Text(safe_text(str(self.output_dir))))
                self._write(f"报告输出: {self.output_dir}", _ACCENT)
            else:
                if self.busy:
                    raise ValueError("已有任务运行中。可用 /cancel 停止，或等待完成。")
                self.busy = True
                self._cancel = asyncio.Event()
                self._state("● RUNNING")
                worker = self.run_worker(
                    self._execute(command), name="mxready-task", exit_on_error=False
                )
                if command.name in {"scan", "public", "batch"}:
                    self._scan_worker = worker
                return
            await self._remember(command)
        except ValueError as error:
            self._write(str(error), "#f2b47e")

    async def _execute(self, command: Command) -> None:
        self._output_buffer = ""
        try:
            if command.name == "reports":
                await self._reports(command)
                await self._remember(command)
            elif command.name == "compare":
                await self._compare(command)
                await self._remember(command)
            elif command.name in {"scan", "public", "batch"}:
                job = await asyncio.to_thread(
                    make_scan_job, command, project_dir=self.project_dir, output_dir=self.output_dir
                )
                await self._remember(command)
                self._write(f"MXReady  正在分析…\n输出: {job.output_dir}", _MUTED)
                result = await run_tool(
                    job.arguments,
                    cwd=self.project_dir,
                    cancel=self._cancel,
                    on_output=self._tool_output,
                )
                self._flush_output()
                if result.cancelled:
                    self._write("已取消任务。再次扫描会新建任务与输出目录。", "#f2b47e")
                elif result.return_code not in {0, 2}:
                    self._write(
                        f"扫描失败（退出码 {result.return_code}），请查看上方原因。", "#f2b47e"
                    )
                else:
                    self._write(
                        "扫描完成 · 发现阻塞项" if result.return_code == 2 else "扫描完成", _ACCENT
                    )

                # Read files sequentially, including valid completed outputs after failure/cancel.
                self._catalog_cancel = asyncio.Event()

                def collect():
                    return read_batch(
                        job.output_dir,
                        cancelled=lambda: self._shutting_down or self._catalog_cancel.is_set(),
                        on_report=lambda loaded: (
                            self.store.register(self.project_dir, loaded, visited=False).id
                        ),
                    )

                results = await asyncio.to_thread(collect)
                if command.name == "batch":
                    status = (
                        "cancelled"
                        if result.cancelled
                        else ("completed" if result.return_code in {0, 2} else "failed")
                    )
                    await asyncio.to_thread(
                        self.store.save_batch,
                        self.project_dir,
                        job.output_dir.name,
                        job.output_dir,
                        result.return_code,
                        status,
                        results,
                    )
                    if not self._shutting_down:
                        self._cancel = asyncio.Event()
                        await self._reports(Command("reports", batch=job.output_dir.name))
                elif not result.cancelled:
                    valid = [item.loaded for item in results.items if item.loaded is not None]
                    if len(valid) == 1:
                        await self._open_report(valid[0].path)
                    elif valid:
                        await self._reports(Command("reports"))
            else:
                path = (
                    resolve_path(command.target, self.project_dir)
                    if command.target
                    else self.last_report
                )
                if path is None and command.name == "report":
                    latest = await asyncio.to_thread(self.store.latest, self.project_dir)
                    path = latest.metadata.path if latest else None
                if path is None:
                    raise ValueError("还没有可恢复的报告。请 /reports 选择或提供 JSON 报告路径。")
                if command.name == "report":
                    await self._open_report(path)
                elif command.name == "bundle":
                    report = await asyncio.to_thread(read_report, path)
                    payload = await asyncio.to_thread(build_verification_bundle, report)
                    if not self._cancel.is_set():
                        output = (
                            new_output_directory(self.output_dir, "bundle") / "verification.zip"
                        )
                        with output.open("xb") as stream:
                            stream.write(payload)
                        self._write(
                            f"验证包已生成: {output}\n请在受控沐曦主机审阅并运行 runner。", _ACCENT
                        )
                if not self._cancel.is_set():
                    await self._remember(command)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if not self._shutting_down:
                self._write(f"操作失败: {error}；可用 /reports 选择其他报告。", "#f2b47e")
        finally:
            self.busy = False
            if not self._shutting_down:
                self._state("● READY")

    def _tool_output(self, value: str) -> None:
        self._output_buffer += value
        while "\n" in self._output_buffer or len(self._output_buffer) >= 2048:
            if "\n" in self._output_buffer:
                line, self._output_buffer = self._output_buffer.split("\n", 1)
            else:
                line, self._output_buffer = self._output_buffer[:2048], self._output_buffer[2048:]
            self._write(line, _MUTED)

    def _flush_output(self) -> None:
        if self._output_buffer:
            self._write(self._output_buffer, _MUTED)
        self._output_buffer = ""

    async def _open_report(self, path: Path) -> None:
        self.view_generation += 1
        generation = self.view_generation

        def read():
            try:
                loaded = load_report(path)
            except (OSError, ValueError) as error:
                self.store.mark_unavailable(self.project_dir, path, str(error))
                raise
            entry = self.store.register(self.project_dir, loaded)
            view = self.store.view(entry.id, str(loaded.report.scan_id), loaded.digest)
            filters, page = FindingFilter(), 1
            if view:
                try:
                    values, page = view
                    filters = FindingFilter(
                        Severity(str(values["severity"])) if values.get("severity") else None,
                        str(values.get("rule_id", "")),
                        str(values.get("file_query", "")),
                        str(values.get("text_query", "")),
                    )
                except (TypeError, ValueError):
                    filters, page = FindingFilter(), 1
            browsing = browse(loaded.report, filters, page, Command("findings"), restore=True)
            return loaded, entry, browsing

        loaded, entry, browsing = await asyncio.to_thread(read)
        if not self._valid_view(generation) or self._cancel.is_set():
            return
        report = loaded.report
        self.filters, finding_page, self._matched = browsing
        self.finding_page = finding_page.page
        self._digest, self._entry_id = loaded.digest, entry.id
        self._filter_generation += 1
        self.last_report, self.current_report = path, report
        summary = report.summary
        self._write(
            f"\n{report.repository.owner}/{report.repository.name}"
            f"  ·  {report.repository.commit[:12]}",
            "bold",
        )
        self._write(
            f"{report.static_status.value}   阻塞 {summary.blocker_count}"
            f"   警告 {summary.warning_count}   提示 {summary.info_count}",
            _ACCENT,
        )
        self._write(f"JSON: {path}", _MUTED)
        source = describe_source(report)
        self._write(f"来源: {source.label} · {source.explanation}", _MUTED)
        for label, value in source.fields:
            self._write(f"{label}: {value}", _MUTED)
        for warning in source.warnings:
            self._write(warning, "#f2b47e")
        self._write(
            f"硬件状态（导出时快照）: {report.verification_status.value}；"
            "当前有效期需在 Web 服务读取。",
            _MUTED,
        )
        if report.coverage:
            self._write(
                f"分析范围: {report.coverage.analyzed_files} 文件 / "
                f"{report.coverage.analyzed_bytes} 字节",
                _MUTED,
            )
        for warning in report.analysis_warnings[:10]:
            self._write(f"范围提示: {warning.code} {warning.message[:600]}", "#f2b47e")
        self.query_one("#report-state", Static).update(
            Text(
                safe_text(
                    f"{report.repository.name}\n{report.static_status.value}\n"
                    f"阻塞 {summary.blocker_count} · 警告 {summary.warning_count}\n\n{path}"
                )
            )
        )
        self._render_findings(finding_page)
        self._state_warning()

    async def _apply_filters(self, command: Command) -> None:
        report = self.current_report
        if report is None:
            self._write("请先 /report 打开一份报告。", "#f2b47e")
            return
        generation = self.view_generation
        self._filter_generation += 1
        request = self._filter_generation
        try:
            filters, page, indices = await asyncio.to_thread(
                browse, report, self.filters, self.finding_page, command, self._matched
            )
            if not self._valid_view(generation) or request != self._filter_generation:
                return
            self.filters, self.finding_page, self._matched = filters, page.page, indices
            self._render_findings(page)
            if self._entry_id is not None:
                await asyncio.to_thread(
                    self.store.save_view,
                    self._entry_id,
                    str(report.scan_id),
                    self._digest,
                    asdict(filters),
                    page.page,
                )
            await self._remember(command)
        except ValueError as error:
            if self._valid_view(generation) and request == self._filter_generation:
                self._write(str(error), "#f2b47e")

    def _render_findings(self, page: FindingPage) -> None:
        report = self.current_report
        if report is None:
            return
        filters = self.filters
        self._write(
            f"\n发现 {page.page}/{page.page_count} 页 · "
            f"匹配 {page.matched_total} / 全部 {page.report_total} 项\n"
            f"条件: 级别 {filters.severity or 'all'} · 规则 {filters.rule_id or '全部'} · "
            f"文件 {filters.file_query or '全部'} · 关键词 {filters.text_query or '无'}",
            _MUTED,
        )
        for index in page.indices:
            finding = report.findings[index]
            color = "#ee9e9e" if finding.severity.value == "blocker" else "#e7c580"
            self._write(
                f"\n{finding.severity.value.upper()}  {finding.rule_id}  {finding.title[:200]}",
                color,
            )
            self._write(f"{finding.relative_path}:{finding.line_start}  ×{finding.count}", _MUTED)
            self._write(f"证据: {finding.evidence[:600]}")
            self._write(f"建议: {finding.recommendation[:1000]}")
        if page.page < page.page_count:
            self._write(f"下一页: /findings {page.page + 1}  ·  完整内容保留在报告文件", _MUTED)

    def _valid_view(self, generation: int) -> bool:
        return not self._shutting_down and self.is_running and generation == self.view_generation

    async def _reports(self, command: Command, *, comparison: bool = False) -> None:
        self.view_generation += 1
        generation = self.view_generation
        current = self.current_report

        def listing():
            entries = self.store.entries(self.project_dir, all_projects=command.all_projects)
            by_id = {entry.id: entry for entry in entries}
            choices = []

            def choice(entry: ReportEntry, key: str, prefix: str = "") -> ReportChoice:
                meta = entry.metadata
                available = meta.path.is_file()
                return ReportChoice(
                    key,
                    entry.id,
                    f"{prefix}{meta.repository} · {meta.commit[:12]} · {meta.static_status}\n"
                    f"扫描 {meta.scanned_at} · "
                    f"阻塞 {meta.blocker} 警告 {meta.warning} 提示 {meta.info}\n"
                    f"{meta.source}（上次读取）· 访问 {entry.last_access}\n{meta.path}",
                    entry.error if available else "报告文件缺失或不可读",
                )

            heading = "报告选择器 · Enter 打开 · Esc 返回"
            if command.batch:
                batches = self.store.batches(self.project_dir, all_projects=command.all_projects)
                batch = next((b for b in batches if b.batch_id == command.batch), None)
                if batch is None:
                    raise ValueError("批次不存在或不属于当前项目。")
                heading = (
                    f"批次 {batch.batch_id} · {batch.status} · 退出码 {batch.return_code}\n"
                    + (batch.warning or f"完整汇总: {batch.output_dir / 'batch-summary.csv'}")
                )
                for item in batch.items:
                    if item.entry_id in by_id:
                        choices.append(
                            choice(
                                by_id[item.entry_id],
                                f"batch-{item.ordinal}",
                                f"{item.status} · ref {item.ref or '默认'} · ",
                            )
                        )
                    else:
                        choices.append(
                            ReportChoice(
                                f"batch-{item.ordinal}",
                                None,
                                f"{item.repository} · ref {item.ref or '默认'} · {item.status}",
                                item.error or "报告未登记或目录索引已淘汰；扫描执行状态保持原记录",
                            )
                        )
            else:
                for entry in entries:
                    if (
                        comparison
                        and current
                        and (
                            entry.metadata.scan_id == str(current.scan_id)
                            or normalize_repository(entry.metadata.repository)
                            != normalize_repository(current.repository.url)
                        )
                    ):
                        continue
                    choices.append(choice(entry, f"entry-{entry.id}"))
                batches = self.store.batches(self.project_dir, all_projects=command.all_projects)
                if batches:
                    heading += "\n最近批次（/reports --batch ID）: " + " · ".join(
                        f"{batch.batch_id} {batch.status}" for batch in batches[:3]
                    )
            return tuple(choices), by_id, heading

        choices, by_id, heading = await asyncio.to_thread(listing)
        if not self._valid_view(generation) or self._cancel.is_set():
            return

        def selected(entry_id: int | None) -> None:
            if not self._valid_view(generation):
                return
            self.view_generation += 1
            self.query_one("#command", Input).focus()
            if entry_id is not None and entry_id in by_id and not self.busy:
                path = by_id[entry_id].metadata.path
                next_command = (
                    Command("compare", str(path)) if comparison else Command("report", str(path))
                )
                self.busy = True
                self._cancel = asyncio.Event()
                self._state("● RUNNING")
                self.run_worker(self._execute(next_command), exit_on_error=False)

        self.push_screen(ReportPicker(choices, query=command.query or "", title=heading), selected)

    async def _compare(self, command: Command) -> None:
        if command.target is None:
            if self.current_report is None:
                raise ValueError("请先 /report 打开当前报告，再选择基线。")
            await self._reports(Command("reports"), comparison=True)
            return
        self.view_generation += 1
        generation = self.view_generation
        current = self.current_report

        def compare():
            baseline = read_report(resolve_path(command.target or "", self.project_dir))
            after = (
                read_report(resolve_path(command.current, self.project_dir))
                if command.current
                else current
            )
            if after is None:
                raise ValueError("请先打开当前报告，或提供两个 JSON 路径。")
            return baseline, after, compare_reports(baseline, after)

        baseline, after, difference = await asyncio.to_thread(compare)
        if not self._valid_view(generation) or self._cancel.is_set():
            return

        def closed(_: None) -> None:
            if self._valid_view(generation):
                self.view_generation += 1
                self.query_one("#command", Input).focus()

        self.push_screen(ComparisonScreen(baseline, after, difference), closed)

    def _help(self) -> None:
        table = Table(box=None, padding=(0, 2, 1, 0), show_header=False)
        table.add_column(style=_ACCENT, no_wrap=False)
        table.add_column(style="#d7dde8")
        for name, (usage, description) in COMMANDS.items():
            table.add_row(Text(f"/{name} {usage}"), Text(description))
        self._append(table)
        self._write(
            "带空格的路径请加引号。相对路径以启动时的项目目录为基准。\n"
            "Enter 运行 · Tab 补全 · ↑↓ 命令历史 · PgUp/PgDn 滚动 · Ctrl+P 命令面板\n"
            "仅命令交互，无模型调用；不会执行项目代码或任意 shell 命令。",
            _MUTED,
        )

    def action_interrupt(self) -> None:
        self._filter_generation += 1
        self._catalog_cancel.set()
        if self.busy:
            self._cancel.set()
            self._write("正在取消当前任务…", "#f2b47e")
        else:
            self.query_one("#command", Input).value = ""

    def action_dismiss(self) -> None:
        self.query_one("#suggestions").display = False
        self.query_one("#command", Input).focus()

    def action_clear(self) -> None:
        self._transcript.clear()
        self.query_one("#transcript", RichLog).clear()
        self.query_one("#transcript").display = False
        self.query_one("#welcome").display = True

    def action_scroll_up(self) -> None:
        self.query_one("#transcript", RichLog).scroll_page_up()

    def action_scroll_down(self) -> None:
        self.query_one("#transcript", RichLog).scroll_page_down()

    async def action_quit(self) -> None:
        self._shutting_down = True
        self.view_generation += 1
        self._filter_generation += 1
        if self.busy:
            self._cancel.set()
        if self._scan_worker is not None and not self._scan_worker.is_finished:
            await self._scan_worker.wait()
        self.workers.cancel_all()
        await asyncio.to_thread(self.store.close)
        self.exit()

    def on_unmount(self) -> None:
        self._shutting_down = True
        self.view_generation += 1
        self.store.close()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        for name, (_, description) in COMMANDS.items():
            yield SystemCommand(f"/{name}", description, partial(self._prefill, name))

    def export_screenshot(self, *, title: str | None = None, simplify: bool = False) -> str:
        svg = super().export_screenshot(title=title, simplify=simplify)
        return align_svg_cells(svg, columns=self.size.width)
