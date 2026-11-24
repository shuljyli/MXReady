"""A full-screen command workspace for the existing MXReady analysis pipeline."""

from __future__ import annotations

import asyncio
import contextlib
import subprocess
import threading
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import asdict, replace
from functools import partial
from pathlib import Path
from typing import Any

from rich.table import Table
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding, BindingsMap, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Input, LoadingIndicator, OptionList, RichLog, Static
from textual.widgets.option_list import Option
from textual.worker import Worker

from mxready import __version__
from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.models import ScanReport, Severity
from mxready.reporting.comparison import compare_reports, normalize_repository
from mxready.reporting.source import describe_source, localized_source_label
from mxready.sanitize import safe_text
from mxready.tui.commands import (
    CodeCommand,
    Command,
    code_command_catalog,
    command_catalog,
    make_scan_job,
    new_output_directory,
    parse_code_command,
    parse_command,
    read_report,
    resolve_path,
)
from mxready.tui.process import ToolResult, run_tool
from mxready.tui.report_browser import FindingFilter, FindingPage, browse
from mxready.tui.report_catalog import load_report, read_batch
from mxready.tui.screens import ComparisonScreen, ReportChoice, ReportPicker, SecretInputScreen
from mxready.tui.screenshot import align_svg_cells
from mxready.tui.state_store import ReportEntry, StateStore
from mxready.verification.bundle import build_verification_bundle

_ACCENT = "#76ddc2"
_MUTED = "#939fb1"


def _app_bindings(language: str) -> list[BindingType]:
    return [
        Binding("ctrl+q", "quit", tr(language, "退出", "Quit"), priority=True),
        Binding(
            "ctrl+c", "interrupt", tr(language, "取消 / 清空", "Cancel / clear"), priority=True
        ),
        Binding("ctrl+l", "clear", tr(language, "清屏", "Clear screen"), priority=True),
        Binding("escape", "dismiss", "", show=False),
        Binding("pageup", "scroll_up", "", show=False),
        Binding("pagedown", "scroll_down", "", show=False),
    ]


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
    BINDINGS = _app_bindings(DEFAULT_LANGUAGE)
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
    #sidebar-scan, #sidebar-code { height: auto; }
    .section { color: #6f819a; margin-top: 1; margin-bottom: 1; text-style: bold; }
    .context { height: auto; margin-bottom: 1; }
    #task-state { color: #76ddc2; }
    #activity { height: 1; width: 12; }
    #code-task-state { color: #76ddc2; }
    #code-activity { height: 1; width: 12; }
    Footer { background: #111722; color: #939fb1; }
    """

    def __init__(
        self,
        *,
        project_dir: Path,
        output_dir: Path | None = None,
        state_path: Path | None = None,
        default_output_dir: Path | None = None,
        language: str | None = None,
        agent_dir: Path | None = None,
        workspace_mode: str | None = None,
    ) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self._explicit_language = language is not None
        self.project_dir = project_dir
        self.output_dir = output_dir or default_output_dir or project_dir / "reports"
        self._explicit_output = output_dir is not None
        self.agent_dir = agent_dir or project_dir / ".mxready-agent"
        self.workspace_mode = workspace_mode if workspace_mode in {"scan", "code"} else "scan"
        self._explicit_workspace = workspace_mode in {"scan", "code"}
        self.store = StateStore(state_path)
        self.store.language = self.language
        self._bindings = self._localized_bindings()
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
        self._task_running = False
        self._branch_text: str | None = None
        self._cancel = asyncio.Event()
        self._history_index = 0
        self._draft = ""
        self._history_value: str | None = None
        self._output_buffer = ""
        self._transcripts: dict[str, deque[Text | Table]] = {
            "scan": deque(maxlen=1000),
            "code": deque(maxlen=1000),
        }
        self._transcript = self._transcripts[self.workspace_mode]
        self.code_history: list[str] = []
        self._code_history_index = 0
        self._code_draft = ""
        self._code_history_value: str | None = None
        self._code_cancel = threading.Event()
        self._agent_session: Any = None
        self._agent_signature: tuple[str, str] | None = None
        self._agent_config: Any = None
        self._agent_config_error: str | None = None
        self._agent_permissions: Any = None
        self._agent_audit: Any = None
        self.agent_elevated = False
        self._vault_password: str | None = None
        self._agent_tokens = 0
        self._agent_provider_label = ""
        self._code_onboarding_shown = False
        self._code_ready_shown = False

    def _localized_bindings(self) -> BindingsMap:
        """Override visible descriptions while keeping App defaults such as Ctrl+P."""
        merged = BindingsMap(_app_bindings(self.language))
        for key, bindings in self._bindings.key_to_bindings.items():
            if key not in merged.key_to_bindings:
                merged.key_to_bindings[key] = list(bindings)
        return merged

    def _t(self, zh: str, en: str) -> str:
        return tr(self.language, zh, en)

    def _active_catalog(self) -> dict[str, tuple[str, str]]:
        if self.workspace_mode == "code":
            return code_command_catalog(self.language)
        return command_catalog(self.language)

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
                    yield Static(self._mode_text(), id="mode")
                    yield CommandInput(placeholder=self._command_placeholder(), id="command")
                yield Static(self._hint_text(), id="hint")
            with Vertical(id="sidebar"):
                with Vertical(id="sidebar-scan"):
                    yield Static(self._projects_heading(), id="projects-heading", classes="section")
                    yield Static(Text(safe_text(self.project_dir.name)), classes="context")
                    yield Static(
                        self._branch_placeholder(), id="branch", classes="context", markup=False
                    )
                    yield Static(self._tasks_heading(), id="tasks-heading", classes="section")
                    yield Static("● READY", id="task-state", classes="context")
                    yield LoadingIndicator(id="activity")
                    yield Static(self._reports_heading(), id="reports-heading", classes="section")
                    yield Static(
                        self._t(
                            "还没有扫描结果\n输入 /scan 开始",
                            "No scans yet\nType /scan to start",
                        ),
                        id="report-state",
                        classes="context",
                    )
                    yield Static(
                        self._outputs_heading(), id="outputs-heading", classes="section"
                    )
                    yield Static(
                        Text(safe_text(str(self.output_dir))),
                        id="output-path",
                        classes="context",
                    )
                    yield Static(self._sidebar_note(), id="sidebar-note", classes="section")
                with Vertical(id="sidebar-code"):
                    yield Static(self._code_heading(), id="code-heading", classes="section")
                    yield Static("● READY", id="code-task-state", classes="context")
                    yield LoadingIndicator(id="code-activity")
                    yield Static(
                        self._code_provider_heading(),
                        id="code-provider-heading",
                        classes="section",
                    )
                    yield Static("", id="code-provider", classes="context", markup=False)
                    yield Static(
                        self._code_permissions_heading(),
                        id="code-permissions-heading",
                        classes="section",
                    )
                    yield Static("", id="code-permissions", classes="context", markup=False)
                    yield Static(
                        self._code_workspace_heading(),
                        id="code-workspace-heading",
                        classes="section",
                    )
                    yield Static(
                        Text(safe_text(str(self.project_dir))),
                        id="code-workspace",
                        classes="context",
                    )
                    yield Static(
                        self._code_usage_heading(), id="code-usage-heading", classes="section"
                    )
                    yield Static("0 tokens", id="code-usage", classes="context", markup=False)
                    yield Static(self._code_note(), id="code-note", classes="section")
        yield Footer()

    def _code_heading(self) -> str:
        return self._t("代码  CODE", "CODE")

    def _code_provider_heading(self) -> str:
        return self._t("模型  MODEL", "MODEL")

    def _code_permissions_heading(self) -> str:
        return self._t("权限  ACCESS", "ACCESS")

    def _code_workspace_heading(self) -> str:
        return self._t("工作区  WORKSPACE", "WORKSPACE")

    def _code_usage_heading(self) -> str:
        return self._t("用量  USAGE", "USAGE")

    def _code_note(self) -> str:
        return self._t(
            "默认只读；写文件与命令需 /elevate 且逐次批准。\n"
            "密钥只保存在本机，不写入命令历史或日志。",
            "Read-only by default; writes and commands need /elevate and per-call approval.\n"
            "Keys stay on this machine and never enter command history or logs.",
        )

    def _projects_heading(self) -> str:
        return self._t("项目  PROJECT", "PROJECT")

    def _tasks_heading(self) -> str:
        return self._t("任务  TASK", "TASK")

    def _reports_heading(self) -> str:
        return self._t("最近报告  REPORT", "RECENT REPORTS")

    def _outputs_heading(self) -> str:
        return self._t("输出  OUTPUT", "OUTPUT")

    def _sidebar_note(self) -> str:
        return self._t(
            "静态风险与硬件验证分开记录。",
            "Static risk and hardware verification are recorded separately.",
        )

    def _command_placeholder(self) -> str:
        if self.workspace_mode == "code":
            return self._t(
                "输入消息，或 /help 查看 code 命令",
                "Enter a message, or /help for code commands",
            )
        return self._t(
            "输入项目路径、仓库 URL 或 /help", "Enter a project path, repository URL, or /help"
        )

    def _hint_text(self) -> str:
        return self._t(
            "Enter 运行   / 命令   Tab 补全   ↑↓ 历史   Ctrl+P 命令面板",
            "Enter run   / commands   Tab complete   ↑↓ history   Ctrl+P command palette",
        )

    def _branch_placeholder(self) -> str:
        return self._t("读取项目状态…", "Reading project status…")

    def _mode_text(self) -> str:
        if self.workspace_mode == "code":
            if self.busy:
                return self._t(
                    "思考中  ·  /cancel 或 Ctrl+C 中断",
                    "Thinking  ·  /cancel or Ctrl+C to stop",
                )
            provider = self._agent_provider_label or self._t("未配置模型", "No model configured")
            access = self._t("只读", "read-only")
            if self.agent_elevated:
                access = self._t("已提权 · 逐次批准", "elevated · per-call approval")
            return f"CODE  ·  {provider}  ·  {access}"
        if self._task_running:
            return self._t(
                "扫描中  ·  /cancel 或 Ctrl+C 中断",
                "Scanning  ·  /cancel or Ctrl+C to stop",
            )
        return self._t("迁移检查  ·  只读静态分析", "Migration check  ·  read-only static analysis")

    def _welcome(self) -> Text:
        welcome = Text(
            "███╗   ███╗██╗  ██╗\n████╗ ████║╚██╗██╔╝\n"
            "██╔████╔██║ ╚███╔╝ \n██║╚██╔╝██║ ██╔██╗ \n"
            "██║ ╚═╝ ██║██╔╝ ██╗\n╚═╝     ╚═╝╚═╝  ╚═╝",
            style=_ACCENT,
        )
        if self.workspace_mode == "code":
            welcome.append("\n\nM X R E A D Y   C O D E\n", style="bold #e4eaf4")
            welcome.append(
                self._t(
                    "自己的 API 密钥 · 默认只读 · 密钥只保存在本机\n\n"
                    "/provider add ...   配置模型服务\n"
                    "/help               查看 code 命令\n"
                    "/scan               返回扫描工作区",
                    "Your own API key · read-only by default · keys stay local\n\n"
                    "/provider add ...   Configure a model provider\n"
                    "/help               View code commands\n"
                    "/scan               Return to the scan workspace",
                ),
                style=_MUTED,
            )
            return welcome
        welcome.append("\n\nM X R E A D Y\n", style="bold #e4eaf4")
        welcome.append("PyTorch CUDA → MetaX MXMACA\n\n", style=_MUTED)
        welcome.append(
            self._t(
                "/scan .     扫描当前项目\n/public URL   扫描公开仓库\n/help       查看全部命令",
                "/scan .     Scan the current project\n"
                "/public URL   Scan a public repository\n"
                "/help       View all commands",
            ),
            style=_MUTED,
        )
        return welcome

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.query_one("#transcript").display = False
        self.query_one("#suggestions").display = False
        self.query_one("#activity").display = False
        self.query_one("#code-activity").display = False
        self._apply_workspace()
        self._responsive(self.size.width, self.size.height)
        self.run_worker(self._load_branch(), exit_on_error=False)
        self.run_worker(self._load_state(), exit_on_error=False)

    async def _load_state(self) -> None:
        try:
            restored = await asyncio.to_thread(self.store.initialize, self.project_dir)
            if self._shutting_down:
                return
            if not self._explicit_language and restored.language is not None:
                self.language = restored.language
            if not self._explicit_workspace and restored.workspace_mode is not None:
                self.workspace_mode = restored.workspace_mode
                self._transcript = self._transcripts[self.workspace_mode]
            self.store.language = self.language
            self.history = list(restored.history)
            self._history_index = len(self.history)
            if not self._explicit_output and restored.output_dir is not None:
                self.output_dir = restored.output_dir
                self.query_one("#output-path", Static).update(Text(safe_text(str(self.output_dir))))
            self._state_warning()
        finally:
            self._state_ready.set()
            if not self._shutting_down:
                self._apply_language()
                self._apply_workspace()
                if self.workspace_mode == "code":
                    await self._enter_code()

    def _apply_language(self) -> None:
        self._bindings = self._localized_bindings()
        self.refresh_bindings()
        if self.query("#welcome-text"):
            self.query_one("#welcome-text", Static).update(self._welcome())
        if self.query("#command"):
            self.query_one("#command", CommandInput).placeholder = self._command_placeholder()
        if self.query("#hint"):
            self.query_one("#hint", Static).update(self._hint_text())
        for selector, value in (
            ("#projects-heading", self._projects_heading()),
            ("#tasks-heading", self._tasks_heading()),
            ("#reports-heading", self._reports_heading()),
            ("#outputs-heading", self._outputs_heading()),
            ("#sidebar-note", self._sidebar_note()),
            ("#code-heading", self._code_heading()),
            ("#code-provider-heading", self._code_provider_heading()),
            ("#code-permissions-heading", self._code_permissions_heading()),
            ("#code-workspace-heading", self._code_workspace_heading()),
            ("#code-usage-heading", self._code_usage_heading()),
            ("#code-note", self._code_note()),
        ):
            if self.query(selector):
                self.query_one(selector, Static).update(value)
        self._render_branch()
        self._render_report_sidebar()
        self._render_agent_sidebar()
        self._state(self._task_running)
        if self.query("#suggestions"):
            self.query_one("#suggestions").display = False

    def _apply_workspace(self) -> None:
        if self.query("#sidebar-scan"):
            self.query_one("#sidebar-scan").display = self.workspace_mode == "scan"
        if self.query("#sidebar-code"):
            self.query_one("#sidebar-code").display = self.workspace_mode == "code"
        if self.query("#welcome-text"):
            self.query_one("#welcome-text", Static).update(self._welcome())
        if self.query("#command"):
            self.query_one("#command", CommandInput).placeholder = self._command_placeholder()
        if self.query("#mode"):
            self.query_one("#mode", Static).update(Text(self._mode_text(), style=_ACCENT))
        self._render_agent_sidebar()
        self._show_active_transcript()

    def _show_active_transcript(self) -> None:
        if not self.query("#transcript"):
            return
        has_content = bool(self._transcript)
        self.query_one("#welcome").display = not has_content
        self.query_one("#transcript").display = has_content

    def _render_active_transcript(self) -> None:
        log = self.query_one("#transcript", RichLog)
        log.clear()
        for value in self._transcript:
            log.write(value)
        self._show_active_transcript()

    async def _switch_workspace(self, mode: str, *, persist: bool = True) -> None:
        if mode not in {"scan", "code"}:
            raise ValueError(f"Unsupported workspace mode: {mode}")
        if mode == self.workspace_mode:
            return
        if self.busy:
            raise ValueError(
                self._t(
                    "请等待当前任务结束再切换工作区。",
                    "Wait for the current task to finish before switching workspaces.",
                )
            )
        self.workspace_mode = mode
        self._transcript = self._transcripts[mode]
        self._history_index = len(self.history)
        self._code_history_index = len(self.code_history)
        if persist:
            await asyncio.to_thread(self.store.set_workspace_mode, mode)
        self._render_active_transcript()
        self._apply_workspace()
        if mode == "code":
            await self._enter_code()

    async def _enter_code(self) -> None:
        if not self._agent_config:
            await self._reload_agent_config()
        provider = self._agent_provider()
        if provider is None:
            if not self._code_onboarding_shown:
                self._write(self._onboarding_text(), "#f2b47e")
                self._code_onboarding_shown = True
        elif not self._code_ready_shown:
            self._write(
                self._t(
                    f"code 工作区 · {provider.name} · {provider.model} · 只读\n"
                    "直接输入问题；/help 查看命令；/scan 返回扫描。",
                    f"code workspace · {provider.name} · {provider.model} · read-only\n"
                    "Type a question; /help lists commands; /scan returns to scanning.",
                ),
                _ACCENT,
            )
            self._code_ready_shown = True
        self._render_agent_sidebar()

    def _render_branch(self) -> None:
        if not self.query("#branch"):
            return
        if self._branch_text is None:
            value = self._branch_placeholder()
        else:
            value = self._branch_text or self._t(
                "本地目录 / detached HEAD", "Local directory / detached HEAD"
            )
        self.query_one("#branch", Static).update(Text(safe_text(value)))

    def _render_report_sidebar(self) -> None:
        if not self.query("#report-state"):
            return
        report = self.current_report
        if report is None:
            value = self._t("还没有扫描结果\n输入 /scan 开始", "No scans yet\nType /scan to start")
        else:
            summary = report.summary
            value = (
                f"{report.repository.name}\n{report.static_status.value}\n"
                f"{self._t('阻塞', 'Blockers')} {summary.blocker_count} · "
                f"{self._t('警告', 'Warnings')} {summary.warning_count}\n\n{self.last_report}"
            )
        self.query_one("#report-state", Static).update(Text(safe_text(value)))

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
        self._branch_text = value
        self._render_branch()

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
            self._t(
                "\n…（显示已截断，完整内容见报告文件）",
                "\n… (display truncated; see the report file for the full content)",
            )
            if len(value) > 16_384
            else ""
        )
        self._append(Text(safe_text(bounded), style=style))

    def _append(self, value: Text | Table) -> None:
        self._transcript.append(value)
        self.query_one("#welcome").display = False
        self.query_one("#transcript").display = True
        self.query_one("#transcript", RichLog).write(value)

    def _state(self, running: bool) -> None:
        self._task_running = running
        for selector in ("#task-state", "#code-task-state"):
            if self.query(selector):
                self.query_one(selector, Static).update(
                    Text("● RUNNING" if running else "● READY", style=_ACCENT)
                )
        if self.query("#mode"):
            self.query_one("#mode", Static).update(Text(self._mode_text(), style=_ACCENT))
        for selector in ("#activity", "#code-activity"):
            if self.query(selector):
                self.query_one(selector).display = running

    def _agent_provider(self) -> Any:
        config = self._agent_config
        return config.provider() if config is not None else None

    def _render_agent_sidebar(self) -> None:
        if not self.query("#code-provider"):
            return
        provider = self._agent_provider()
        if provider is None:
            label = self._t(
                "未配置\n/provider add ...", "Not configured\n/provider add ..."
            )
        else:
            label = f"{provider.name}\n{provider.protocol} · {provider.model}\n{provider.base_url}"
        self.query_one("#code-provider", Static).update(Text(safe_text(label)))
        if self.agent_elevated:
            access = self._t(
                "已提权\n写文件/执行命令需逐次批准",
                "Elevated\nEach write/command needs approval",
            )
        else:
            access = self._t("只读\n/elevate 可本会话提权", "Read-only\n/elevate for this session")
        self.query_one("#code-permissions", Static).update(Text(safe_text(access)))
        self.query_one("#code-usage", Static).update(
            Text(f"{self._agent_tokens} tokens")
        )

    async def _reload_agent_config(self) -> None:
        from mxready.agent.config import AgentConfig, ConfigError, ConfigStore

        try:
            config = await asyncio.to_thread(ConfigStore(self.agent_dir).load)
        except ConfigError as error:
            self._agent_config = AgentConfig()
            self._agent_config_error = str(error)
            self._write(
                self._t(
                    f"读取模型配置失败: {error}",
                    f"Cannot read the model configuration: {error}",
                ),
                "#f2b47e",
            )
            return
        self._agent_config = config
        self._agent_config_error = None
        provider = config.provider()
        self._agent_provider_label = (
            f"{provider.name} · {provider.model}" if provider is not None else ""
        )

    def _onboarding_text(self) -> str:
        return self._t(
            "尚未配置模型服务。密钥只保存在本机（系统凭据库，或加密 vault），"
            "不会进入命令参数、历史或日志。\n\n"
            "/provider add work --protocol openai --base-url https://<host>/v1 "
            "--model <model>\n"
            "/provider add work --protocol anthropic --base-url https://<host>/v1 "
            "--model <model>\n\n"
            "/provider list · use <名称> · test [名称] · remove <名称>\n"
            "/help 查看全部 code 命令；/scan 返回扫描工作区。",
            "No model provider is configured yet. Keys stay on this machine (OS keyring or "
            "an encrypted vault) and never enter arguments, history, or logs.\n\n"
            "/provider add work --protocol openai --base-url https://<host>/v1 "
            "--model <model>\n"
            "/provider add work --protocol anthropic --base-url https://<host>/v1 "
            "--model <model>\n\n"
            "/provider list · use <name> · test [name] · remove <name>\n"
            "/help lists all code commands; /scan returns to scanning.",
        )

    def _permissions_text(self) -> str:
        if self.agent_elevated:
            state = self._t(
                "当前: 已提权（仅本会话）\n可用: 读文件/目录/搜索/报告 + 写文件/补丁/命令\n"
                "写文件与命令每次都需要你批准，并记录到本机审计日志。",
                "Current: elevated (this session only)\n"
                "Available: read/list/search/report + write/patch/command\n"
                "Every write and command needs your approval and is audited locally.",
            )
        else:
            state = self._t(
                "当前: 只读\n可用: 读文件/目录/搜索/报告\n"
                "写文件、补丁与命令需要先运行 /elevate，且每次仍会请求批准。",
                "Current: read-only\nAvailable: read/list/search/report\n"
                "Writing, patching, and commands need /elevate and still ask for approval.",
            )
        return state

    async def _prompt_secret(
        self,
        *,
        title: str,
        prompt: str,
        minimum_length: int = 1,
    ) -> str | None:
        future: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()

        def callback(value: str | None) -> None:
            if not future.done():
                future.set_result(value)

        self.push_screen(
            SecretInputScreen(
                title=title,
                prompt=prompt,
                language=self.language,
                minimum_length=minimum_length,
            ),
            callback,
        )
        return await future

    async def _prompt_vault_password(self) -> str | None:
        return await self._prompt_secret(
            title=self._t("加密密钥库主密码", "Encrypted vault master password"),
            prompt=self._t(
                "系统凭据库不可用。输入 vault 主密码；它只保存在本次会话内存中，"
                "不会写入磁盘。",
                "The OS keyring is unavailable. Enter the vault master password; it is kept "
                "in this session's memory only and never written to disk.",
            ),
            minimum_length=8,
        )

    def _secret_manager(self) -> Any:
        from mxready.agent.secrets import SecretManager

        return SecretManager(self.agent_dir, password=self._vault_password)

    async def _store_secret(self, key_ref: str, value: str) -> str | None:
        from mxready.agent.secrets import VaultPasswordRequired

        manager = self._secret_manager()
        try:
            return await asyncio.to_thread(manager.set, key_ref, value)
        except VaultPasswordRequired:
            password = await self._prompt_vault_password()
            if password is None:
                return None
            self._vault_password = password
            return await asyncio.to_thread(manager.set, key_ref, value, password=password)

    async def _resolve_secret(self, key_ref: str) -> str | None:
        from mxready.agent.secrets import VaultPasswordRequired

        manager = self._secret_manager()
        try:
            return await asyncio.to_thread(manager.get, key_ref)
        except VaultPasswordRequired:
            password = await self._prompt_vault_password()
            if password is None:
                return None
            self._vault_password = password
            return await asyncio.to_thread(self._secret_manager().get, key_ref)

    async def _provider_command(self, command: CodeCommand) -> None:
        from mxready.agent.config import (
            ConfigStore,
            ProviderConfig,
            fingerprint_secret,
            key_reference,
        )
        from mxready.agent.secrets import SecretError

        await self._reload_agent_config()
        config = self._agent_config
        action = command.action
        if action == "add":
            if command.target is None or command.protocol is None:
                self._write(
                    self._t("provider add 参数不完整。", "Incomplete provider add."),
                    "#f2b47e",
                )
                return
            name = command.target
            if name in config.providers:
                self._write(
                    self._t(
                        f"服务 {name} 已存在；请先 remove 或换名。",
                        f"Provider {name} already exists; remove it or choose another name.",
                    ),
                    "#f2b47e",
                )
                return
            try:
                provider = ProviderConfig(
                    name=name,
                    protocol=command.protocol,
                    base_url=command.base_url or "",
                    model=command.model or "",
                    key_ref=key_reference(name),
                )
            except ValueError as error:
                self._write(str(error), "#f2b47e")
                return
            api_key = await self._prompt_secret(
                title=self._t(f"{name} 的 API Key", f"API key for {name}"),
                prompt=self._t(
                    "输入 API Key。它只写入系统凭据库或本机加密 vault，"
                    "不会显示、写入命令历史或日志。",
                    "Enter the API key. It is stored only in the OS keyring or the local "
                    "encrypted vault; it is never displayed, logged, or added to history.",
                ),
            )
            if api_key is None:
                self._write(
                    self._t("已取消，未保存服务。", "Cancelled; provider not saved."), _MUTED
                )
                return
            try:
                backend = await self._store_secret(provider.key_ref, api_key)
            except SecretError as error:
                self._write(
                    self._t(f"保存密钥失败: {error}", f"Cannot save the API key: {error}"),
                    "#f2b47e",
                )
                return
            if backend is None:
                self._write(
                    self._t("已取消，未保存服务。", "Cancelled; provider not saved."), _MUTED
                )
                return
            provider = replace(provider, fingerprint=fingerprint_secret(api_key))
            updated = config.with_provider(provider)
            try:
                await asyncio.to_thread(ConfigStore(self.agent_dir).save, updated)
            except OSError as error:
                with contextlib.suppress(SecretError):
                    await asyncio.to_thread(
                        self._secret_manager().delete,
                        provider.key_ref,
                        password=self._vault_password,
                    )
                self._write(
                    self._t(f"保存配置失败: {error}", f"Cannot save the configuration: {error}"),
                    "#f2b47e",
                )
                return
            self._agent_config = updated
            self._invalidate_agent_session()
            await self._reload_agent_config()
            self._render_agent_sidebar()
            where = "keyring" if backend == "keyring" else self._t("加密 vault", "encrypted vault")
            self._write(
                self._t(
                    f"已添加 {name}（{provider.protocol} · {provider.model}），"
                    f"密钥保存在 {where}。\n直接输入问题即可。",
                    f"Added {name} ({provider.protocol} · {provider.model}); the key is stored in "
                    f"the {where}.\nType a question to start.",
                ),
                _ACCENT,
            )
            return
        if action == "list":
            if not config.providers:
                self._write(
                    self._t(
                        "还没有模型服务。使用 /provider add ...",
                        "No providers yet. Use /provider add ...",
                    ),
                    _MUTED,
                )
                return
            lines = []
            for name, provider in sorted(config.providers.items()):
                marker = "*" if name == config.active else " "
                lines.append(
                    f"{marker} {name}  {provider.protocol}  {provider.model}\n"
                    f"    {provider.base_url}\n"
                    f"    key {provider.fingerprint or 'unset'}"
                )
            self._write("\n".join(lines))
            return
        if action in {"use", "remove"}:
            if command.target is None:
                self._write(self._t("缺少服务名称。", "A provider name is required."), "#f2b47e")
                return
            name = command.target
            provider = config.provider(name)
            if provider is None:
                self._write(self._t(f"未知服务 {name}。", f"Unknown provider {name}."), "#f2b47e")
                return
            if action == "use":
                updated = config.with_active(name)
                await asyncio.to_thread(ConfigStore(self.agent_dir).save, updated)
                self._agent_config = updated
                self._invalidate_agent_session()
                await self._reload_agent_config()
                self._render_agent_sidebar()
                self._write(
                    self._t(f"当前服务: {name}", f"Active provider: {name}"),
                    _ACCENT,
                )
                return
            allowed = await self._approve_action(
                tool="provider remove",
                summary=self._t(f"删除服务 {name}", f"Remove provider {name}"),
                detail=self._t(
                    "将从配置中移除该服务，并尝试删除本机保存的 API Key。",
                    "This removes the provider and deletes its locally stored API key.",
                ),
            )
            if not allowed:
                self._write(self._t("已取消。", "Cancelled."), _MUTED)
                return
            try:
                await asyncio.to_thread(
                    self._secret_manager().delete,
                    provider.key_ref,
                    password=self._vault_password,
                )
            except SecretError as error:
                self._write(
                    self._t(f"删除密钥失败: {error}", f"Cannot delete the API key: {error}"),
                    "#f2b47e",
                )
                return
            updated = config.without(name)
            await asyncio.to_thread(ConfigStore(self.agent_dir).save, updated)
            self._agent_config = updated
            self._invalidate_agent_session()
            await self._reload_agent_config()
            self._render_agent_sidebar()
            self._write(self._t(f"已删除 {name}。", f"Removed {name}."), _ACCENT)
            return
        if action == "test":
            name = command.target or config.active
            provider = config.provider(name)
            if provider is None:
                self._write(self._t("没有可测试的服务。", "No provider to test."), "#f2b47e")
                return
            await self._test_provider(provider)
            return
        self._write(self._t("未知 provider 操作。", "Unknown provider action."), "#f2b47e")

    async def _test_provider(self, provider: Any) -> None:
        from mxready.agent.providers import build_provider
        from mxready.agent.providers.base import Message

        if self.busy:
            self._write(self._t("已有任务运行中。", "A task is already running."), "#f2b47e")
            return
        self.busy = True
        self._state(True)
        try:
            key = await self._resolve_secret(provider.key_ref)
            if key is None:
                self._write(self._t("没有可用的 API Key。", "No API key is available."), "#f2b47e")
                return
            chat = build_provider(provider, key)
            completion = await asyncio.to_thread(
                chat.complete, [Message("user", "Reply with OK.")], ()
            )
            reply = completion.text.strip()[:500] or "(empty)"
            self._write(
                self._t(
                    f"连接成功: {provider.name} · {provider.model}\n响应: {reply}",
                    f"Connection OK: {provider.name} · {provider.model}\nReply: {reply}",
                ),
                _ACCENT,
            )
        except Exception as error:
            self._write_agent_error(error)
        finally:
            self.busy = False
            self._state(False)
            self._render_agent_sidebar()

    async def _model_command(self, command: CodeCommand) -> None:
        from mxready.agent.config import ConfigStore

        await self._reload_agent_config()
        config = self._agent_config
        provider = config.provider()
        if provider is None:
            self._write(self._t("还没有配置模型服务。", "No provider is configured."), "#f2b47e")
            return
        if command.model is None:
            self._write(
                self._t(
                    f"当前模型: {provider.model}\n用法: /model <名称>",
                    f"Current model: {provider.model}\nUsage: /model <name>",
                ),
                _ACCENT,
            )
            return
        updated_provider = replace(provider, model=command.model)
        updated = config.with_provider(updated_provider, activate=False)
        await asyncio.to_thread(ConfigStore(self.agent_dir).save, updated)
        self._agent_config = updated
        self._invalidate_agent_session()
        await self._reload_agent_config()
        self._render_agent_sidebar()
        self._write(
            self._t(f"模型已切换: {command.model}", f"Model changed: {command.model}"),
            _ACCENT,
        )

    def _invalidate_agent_session(self) -> None:
        self._agent_session = None
        self._agent_permissions = None
        self._agent_signature = None
        self._agent_tokens = 0

    async def _approve_action(self, *, tool: str, summary: str, detail: str) -> bool:
        from mxready.tui.approval import ApprovalScreen

        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

        def callback(value: bool | None) -> None:
            if not future.done():
                future.set_result(bool(value))

        self.push_screen(
            ApprovalScreen(
                tool=tool,
                summary=summary,
                detail=detail,
                language=self.language,
            ),
            callback,
        )
        return await future

    async def _set_elevated(self, value: bool) -> None:
        if value == self.agent_elevated:
            self._write(
                self._permissions_text(),
                _ACCENT,
            )
            return
        if value:
            allowed = await self._approve_action(
                tool="elevate",
                summary=self._t("本会话启用写文件与命令工具", "Enable writes and commands"),
                detail=self._t(
                    "提权仅持续到本次终端会话结束，不会保存。"
                    "之后每次写文件、打补丁或执行命令仍会单独请求批准。",
                    "Elevation lasts for this terminal session only and is not saved. "
                    "Every write, patch, or command still asks for approval.",
                ),
            )
            if not allowed:
                self._write(
                    self._t("未提权，保持只读。", "Not elevated; staying read-only."), _MUTED
                )
                return
        self.agent_elevated = value
        if self._agent_permissions is not None:
            self._agent_permissions.set_elevated(value)
        if self._agent_audit is not None:
            self._agent_audit.record(
                tool="elevate",
                decision="allowed" if value else "restricted",
                target="session",
                result="user",
            )
        self._render_agent_sidebar()
        self._state(self._task_running)
        self._write(self._permissions_text(), _ACCENT)

    async def _prepare_session(self) -> Any:
        from mxready.agent.audit import AuditLog
        from mxready.agent.config import ConfigError, ConfigStore
        from mxready.agent.permissions import PermissionManager
        from mxready.agent.providers import build_provider
        from mxready.agent.session import AgentSession
        from mxready.agent.tools import build_tools
        from mxready.agent.tools.base import ToolRegistry, WorkspaceGuard

        try:
            config = await asyncio.to_thread(ConfigStore(self.agent_dir).load)
        except ConfigError as error:
            raise ValueError(
                self._t(f"读取模型配置失败: {error}", f"Cannot read model configuration: {error}")
            ) from error
        provider = config.provider()
        if provider is None:
            raise ValueError(self._onboarding_text())
        key = await self._resolve_secret(provider.key_ref)
        if key is None:
            raise ValueError(
                self._t(
                    "没有可用的 API Key；请运行 /provider add 重新配置。",
                    "No API key is available; run /provider add again.",
                )
            )
        guard = WorkspaceGuard(self.project_dir)
        if self._agent_audit is None:
            import uuid

            self._agent_audit = AuditLog(
                self.agent_dir / "audit.jsonl", session_id=uuid.uuid4().hex
            )
        permissions = PermissionManager(
            elevated=self.agent_elevated,
            approver=self._approval_bridge,
            audit=self._agent_audit,
        )
        tools = ToolRegistry(
            build_tools(
                guard,
                lambda: self.current_report,
                self.language,
                permissions,
                lambda: self._code_cancel,
            )
        )
        chat = build_provider(provider, key)
        session = AgentSession(
            chat,
            tools,
            workspace_root=self.project_dir,
            language=self.language,
        )
        self._agent_config = config
        self._agent_permissions = permissions
        self._agent_provider_label = f"{provider.name} · {provider.model}"
        self._agent_signature = (provider.name, provider.model)
        self._render_agent_sidebar()
        return session

    def _approval_bridge(self, request: Any) -> bool:
        from mxready.tui.approval import ApprovalScreen

        done = threading.Event()
        outcome = {"allowed": False}

        def callback(value: bool | None) -> None:
            outcome["allowed"] = bool(value)
            done.set()

        try:
            self.call_from_thread(
                self.push_screen,
                ApprovalScreen(
                    tool=request.tool,
                    summary=request.summary,
                    detail=request.detail,
                    language=self.language,
                ),
                callback,
            )
        except Exception:
            return False
        while not done.wait(0.2):
            if self._shutting_down:
                return False
            if self._code_cancel.is_set():
                return False
        return outcome["allowed"]

    def _call_ui(self, callback: Any, *args: Any) -> None:
        with contextlib.suppress(Exception):
            self.call_from_thread(callback, *args)

    def _append_to(self, mode: str, value: Text) -> None:
        self._transcripts[mode].append(value)
        if self.workspace_mode == mode:
            self.query_one("#welcome").display = False
            self.query_one("#transcript").display = True
            self.query_one("#transcript", RichLog).write(value)

    async def _agent_request(self, text: str, *, echo: bool = True) -> None:
        from mxready.agent.providers.base import ProviderError
        from mxready.agent.secrets import SecretError, VaultPasswordRequired
        from mxready.agent.session import AgentCancelled, SessionError

        if self.busy:
            self._write(
                self._t(
                    "已有任务运行中；可用 /cancel 停止。",
                    "A task is already running; use /cancel to stop it.",
                ),
                "#f2b47e",
            )
            return
        if not text.strip():
            return
        if len(text) > 32768:
            self._write(
                self._t(
                    "消息最多 32768 字符。",
                    "Messages must be at most 32768 characters.",
                ),
                "#f2b47e",
            )
            return
        if echo:
            self._write(f"\n› {text}", "bold #dce5f4")
            if not self.code_history or self.code_history[-1] != text:
                self.code_history.append(text)
                self.code_history = self.code_history[-200:]
            self._code_history_index = len(self.code_history)
        self.busy = True
        self._code_cancel = threading.Event()
        self._state(True)
        try:
            session = self._agent_session
            for attempt in range(2):
                try:
                    if session is None:
                        session = await self._prepare_session()
                        self._agent_session = session
                    break
                except VaultPasswordRequired:
                    if attempt:
                        raise
                    password = await self._prompt_vault_password()
                    if password is None:
                        self._write(self._t("已取消。", "Cancelled."), _MUTED)
                        return
                    self._vault_password = password
                except ValueError as error:
                    self._write(str(error), "#f2b47e")
                    return
            if session is None:
                return

            def emit_text(value: str) -> None:
                self._call_ui(self._write, value, "")

            def emit_tool(value: str) -> None:
                self._call_ui(self._write, f"\n[{value}]\n", _MUTED)

            await asyncio.to_thread(
                session.send,
                text,
                cancel=self._code_cancel,
                on_text=emit_text,
                on_tool=emit_tool,
            )
            self._agent_tokens = session.usage.total
        except AgentCancelled:
            self._write(self._t("已取消请求。", "Request cancelled."), "#f2b47e")
        except (ProviderError, SessionError, SecretError) as error:
            self._write_agent_error(error)
        except OSError as error:
            self._write(self._t(f"操作失败: {error}", f"Operation failed: {error}"), "#f2b47e")
        finally:
            self.busy = False
            self._state(False)
            self._render_agent_sidebar()

    async def _submit_code(self, raw: str) -> None:
        self._write(f"\n› {raw}", "bold #dce5f4")
        if not self.code_history or self.code_history[-1] != raw:
            self.code_history.append(raw)
            self.code_history = self.code_history[-200:]
        self._code_history_index = len(self.code_history)
        if not raw.startswith("/"):
            await self._agent_request(raw, echo=False)
            return
        try:
            command = parse_code_command(raw, language=self.language)
        except ValueError as error:
            self._write(str(error), "#f2b47e")
            return
        await self._execute_code_command(command)

    async def _execute_code_command(self, command: CodeCommand) -> None:
        if command.name == "code":
            if command.target:
                await self._agent_request(command.target, echo=False)
            else:
                self._help()
        elif command.name == "scan":
            await self._switch_workspace("scan")
            self._write(
                self._t(
                    "已切回扫描工作区；code 对话保留。",
                    "Back in the scan workspace; the code conversation is preserved.",
                ),
                _ACCENT,
            )
        elif command.name == "help":
            self._help()
        elif command.name == "clear":
            self.action_clear()
        elif command.name == "new":
            self._new_conversation()
        elif command.name == "provider":
            await self._provider_command(command)
        elif command.name == "model":
            await self._model_command(command)
        elif command.name == "permissions":
            self._write(self._permissions_text(), _ACCENT)
        elif command.name == "elevate":
            await self._set_elevated(True)
        elif command.name == "restrict":
            await self._set_elevated(False)
        elif command.name == "cancel":
            self.action_interrupt()
        elif command.name == "lang":
            await self._set_language(command.target)
        elif command.name == "quit":
            await self.action_quit()

    def _new_conversation(self) -> None:
        self._agent_session = None
        self._agent_permissions = None
        self._agent_tokens = 0
        self._transcripts["code"].clear()
        self._render_active_transcript()
        self._write(
            self._t("新对话已开始。", "A new conversation has started."),
            _ACCENT,
        )

    async def _set_language(self, target: str | None) -> None:
        language = target or ("en" if self.language == "zh" else "zh")
        self.language = language
        self.store.language = language
        await asyncio.to_thread(self.store.set_language, language)
        self._apply_language()
        self._write(
            self._t("界面语言: 中文", "Interface language: English"),
            _ACCENT,
        )

    def _write_agent_error(self, error: Exception) -> None:
        from mxready.agent.providers.base import ProviderError

        if isinstance(error, ProviderError):
            messages = {
                "missing-key": self._t(
                    "没有可用的 API Key；请运行 /provider add 重新配置。",
                    "No API key is available; run /provider add again.",
                ),
                "invalid-key": self._t(
                    "API Key 被拒绝（401/403）；请运行 /provider add 重新输入。",
                    "The API key was rejected (401/403); run /provider add again.",
                ),
                "not-found": self._t(
                    "端点或模型不存在（404）；请检查 base URL 与 model。",
                    "The endpoint or model was not found (404); check the base URL and model.",
                ),
                "rate-limit": self._t(
                    "请求被限流（429）；请稍后重试。",
                    "The provider is rate limiting requests (429); retry later.",
                ),
                "timeout": self._t("请求超时。", "The request timed out."),
                "network": self._t(
                    "网络错误；请检查网络或代理设置。",
                    "Network error; check the network or proxy settings.",
                ),
                "invalid-response": self._t(
                    "模型返回了无法解析的响应。",
                    "The provider returned an invalid response.",
                ),
                "server-error": self._t(
                    "模型服务端错误；请稍后重试。",
                    "The provider returned a server error; retry later.",
                ),
            }
            self._write(
                messages.get(error.code, self._t(
                    f"模型调用失败: {error.message}",
                    f"Model request failed: {error.message}",
                )),
                "#f2b47e",
            )
            return
        self._write(
            self._t(f"操作失败: {error}", f"Operation failed: {error}"),
            "#f2b47e",
        )

    @on(Input.Changed, "#command")
    def suggest(self, event: Input.Changed) -> None:
        choices = self.query_one("#suggestions", OptionList)
        value = event.value
        if value and (value == self._history_value or value == self._code_history_value):
            choices.display = False
            return
        self._history_value = None
        self._code_history_value = None
        catalog = self._active_catalog()
        matches = [name for name in catalog if f"/{name}".startswith(value)]
        choices.clear_options()
        choices.display = bool(
            value.startswith("/") and " " not in value and value[1:] not in catalog and matches
        )
        if choices.display:
            for name in matches:
                description = catalog[name][1]
                choices.add_option(Option(Text(f"/{name:<10} {description}"), id=name))
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
        if self.workspace_mode == "code":
            history = self.code_history
            if self._code_history_index == len(history):
                self._code_draft = entry.value
            self._code_history_index = max(
                0, min(len(history), self._code_history_index + event.direction)
            )
            value = (
                history[self._code_history_index]
                if self._code_history_index < len(history)
                else self._code_draft
            )
            self._code_history_value = value
        else:
            history = self.history
            if self._history_index == len(history):
                self._draft = entry.value
            self._history_index = max(
                0, min(len(history), self._history_index + event.direction)
            )
            value = (
                history[self._history_index]
                if self._history_index < len(history)
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
        usage = self._active_catalog()[name][0]
        entry.value = f"/{name}" + (" " if usage else "")
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
        if self.workspace_mode == "code":
            await self._submit_code(raw)
            return
        if not self.history or self.history[-1] != raw:
            self.history.append(raw)
            self.history = self.history[-200:]
        self._history_index = len(self.history)
        self._write(f"\n› {raw}", "bold #dce5f4")
        try:
            command = parse_command(raw, language=self.language)
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
            elif command.name == "lang":
                await self._set_language(command.target)
            elif command.name == "code":
                await self._switch_workspace("code")
                if command.target:
                    await self._agent_request(command.target)
                return
            elif command.name == "findings":
                self.run_worker(self._apply_filters(command), exit_on_error=False)
                return
            elif command.name == "output":
                if self.busy:
                    raise ValueError(
                        self._t(
                            "请等待当前任务结束后再修改输出目录。",
                            "Wait for the current task to finish before changing the output "
                            "directory.",
                        )
                    )
                if command.target:
                    self.output_dir = resolve_path(command.target, self.project_dir)
                    await asyncio.to_thread(
                        self.store.set_output, self.project_dir, self.output_dir
                    )
                self.query_one("#output-path", Static).update(Text(safe_text(str(self.output_dir))))
                self._write(
                    self._t(f"报告输出: {self.output_dir}", f"Report output: {self.output_dir}"),
                    _ACCENT,
                )
            else:
                if self.busy:
                    raise ValueError(
                        self._t(
                            "已有任务运行中。可用 /cancel 停止，或等待完成。",
                            "A task is already running. Use /cancel to stop it or wait for "
                            "completion.",
                        )
                    )
                self.busy = True
                self._cancel = asyncio.Event()
                self._state(True)
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
                    make_scan_job,
                    command,
                    project_dir=self.project_dir,
                    output_dir=self.output_dir,
                    language=self.language,
                )
                await self._remember(command)
                self._write(
                    self._t(
                        f"MXReady  正在分析…\n输出: {job.output_dir}",
                        f"MXReady  analyzing…\nOutput: {job.output_dir}",
                    ),
                    _MUTED,
                )
                result = await self._run_tool(job.arguments)
                self._flush_output()
                if result.cancelled:
                    self._write(
                        self._t(
                            "已取消任务。再次扫描会新建任务与输出目录。",
                            "Task cancelled. A new scan creates a new task and output directory.",
                        ),
                        "#f2b47e",
                    )
                elif result.return_code not in {0, 2}:
                    self._write(
                        self._t(
                            f"扫描失败（退出码 {result.return_code}），请查看上方原因。",
                            f"Scan failed (exit code {result.return_code}); see the reason above.",
                        ),
                        "#f2b47e",
                    )
                else:
                    self._write(
                        self._t(
                            "扫描完成 · 发现阻塞项" if result.return_code == 2 else "扫描完成",
                            "Scan complete · blockers found"
                            if result.return_code == 2
                            else "Scan complete",
                        ),
                        _ACCENT,
                    )

                # Read files sequentially, including valid completed outputs after failure/cancel.
                self._catalog_cancel = asyncio.Event()

                def collect():
                    return read_batch(
                        job.output_dir,
                        cancelled=lambda: self._shutting_down or self._catalog_cancel.is_set(),
                        on_report=lambda loaded: (
                            self.store.register(
                                self.project_dir,
                                loaded,
                                visited=False,
                                language=self.language,
                            ).id
                        ),
                        language=self.language,
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
                    raise ValueError(
                        self._t(
                            "还没有可恢复的报告。请 /reports 选择或提供 JSON 报告路径。",
                            "No report to restore. Use /reports to choose one or provide a JSON "
                            "report path.",
                        )
                    )
                if command.name == "report":
                    await self._open_report(path)
                elif command.name == "bundle":
                    report = await asyncio.to_thread(read_report, path, self.language)
                    payload = await asyncio.to_thread(build_verification_bundle, report)
                    if not self._cancel.is_set():
                        output = (
                            new_output_directory(self.output_dir, "bundle") / "verification.zip"
                        )
                        with output.open("xb") as stream:
                            stream.write(payload)
                        self._write(
                            self._t(
                                f"验证包已生成: {output}\n请在受控沐曦主机审阅并运行 runner。",
                                f"Verification bundle created: {output}\nReview and run the "
                                "runner on a controlled MetaX host.",
                            ),
                            _ACCENT,
                        )
                if not self._cancel.is_set():
                    await self._remember(command)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if not self._shutting_down:
                self._write(
                    self._t(
                        f"操作失败: {error}；可用 /reports 选择其他报告。",
                        f"Operation failed: {error}; use /reports to choose another report.",
                    ),
                    "#f2b47e",
                )
        finally:
            self.busy = False
            if not self._shutting_down:
                self._state(False)

    async def _run_tool(self, arguments: Sequence[str]) -> ToolResult:
        options: dict[str, Any] = {}
        if self.language == "en":
            options["truncated_message"] = (
                "\n[TRUNCATED: terminal output reached 256 KiB; see the report file for "
                "full results]\n"
            )
        return await run_tool(
            arguments,
            cwd=self.project_dir,
            cancel=self._cancel,
            on_output=self._tool_output,
            **options,
        )

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
                loaded = load_report(path, self.language)
            except (OSError, ValueError) as error:
                self.store.mark_unavailable(self.project_dir, path, str(error))
                raise
            entry = self.store.register(self.project_dir, loaded, language=self.language)
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
            browsing = browse(
                loaded.report,
                filters,
                page,
                Command("findings"),
                restore=True,
                language=self.language,
            )
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
            self._t(
                f"{report.static_status.value}   阻塞 {summary.blocker_count}"
                f"   警告 {summary.warning_count}   提示 {summary.info_count}",
                f"{report.static_status.value}   Blockers {summary.blocker_count}"
                f"   Warnings {summary.warning_count}   Info {summary.info_count}",
            ),
            _ACCENT,
        )
        self._write(f"JSON: {path}", _MUTED)
        source = describe_source(report, self.language)
        self._write(
            self._t(
                f"来源: {source.label} · {source.explanation}",
                f"Source: {source.label} · {source.explanation}",
            ),
            _MUTED,
        )
        for label, value in source.fields:
            self._write(f"{label}: {value}", _MUTED)
        for warning in source.warnings:
            self._write(warning, "#f2b47e")
        self._write(
            self._t(
                f"硬件状态（导出时快照）: {report.verification_status.value}；"
                "当前有效期需在 Web 服务读取。",
                f"Hardware status (export snapshot): {report.verification_status.value}; "
                "current validity must be read from the Web service.",
            ),
            _MUTED,
        )
        if report.coverage:
            self._write(
                self._t(
                    f"分析范围: {report.coverage.analyzed_files} 文件 / "
                    f"{report.coverage.analyzed_bytes} 字节",
                    f"Analysis scope: {report.coverage.analyzed_files} files / "
                    f"{report.coverage.analyzed_bytes} bytes",
                ),
                _MUTED,
            )
        for warning in report.analysis_warnings[:10]:
            self._write(
                self._t(
                    f"范围提示: {warning.code} {warning.message[:600]}",
                    f"Scope warning: {warning.code} {warning.message[:600]}",
                ),
                "#f2b47e",
            )
        self._render_report_sidebar()
        self._render_findings(finding_page)
        self._state_warning()

    async def _apply_filters(self, command: Command) -> None:
        report = self.current_report
        if report is None:
            self._write(
                self._t("请先 /report 打开一份报告。", "Open a report with /report first."),
                "#f2b47e",
            )
            return
        generation = self.view_generation
        self._filter_generation += 1
        request = self._filter_generation
        try:
            filters, page, indices = await asyncio.to_thread(
                browse,
                report,
                self.filters,
                self.finding_page,
                command,
                self._matched,
                language=self.language,
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
        all_text = self._t("全部", "all")
        none_text = self._t("无", "none")
        self._write(
            self._t(
                f"\n发现 {page.page}/{page.page_count} 页 · "
                f"匹配 {page.matched_total} / 全部 {page.report_total} 项\n"
                f"条件: 级别 {filters.severity or all_text} · "
                f"规则 {filters.rule_id or all_text} · "
                f"文件 {filters.file_query or all_text} · 关键词 {filters.text_query or none_text}",
                f"\nFindings page {page.page}/{page.page_count} · "
                f"matched {page.matched_total} / total {page.report_total}\n"
                f"Filters: severity {filters.severity or 'all'} · "
                f"rule {filters.rule_id or 'all'} · "
                f"file {filters.file_query or 'all'} · query {filters.text_query or 'none'}",
            ),
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
            self._write(
                self._t(f"证据: {finding.evidence[:600]}", f"Evidence: {finding.evidence[:600]}")
            )
            self._write(
                self._t(
                    f"建议: {finding.recommendation[:1000]}",
                    f"Recommendation: {finding.recommendation[:1000]}",
                )
            )
        if page.page < page.page_count:
            self._write(
                self._t(
                    f"下一页: /findings {page.page + 1}  ·  完整内容保留在报告文件",
                    f"Next page: /findings {page.page + 1}  ·  full content remains in the report "
                    "file",
                ),
                _MUTED,
            )

    def _valid_view(self, generation: int) -> bool:
        return not self._shutting_down and self.is_running and generation == self.view_generation

    async def _reports(self, command: Command, *, comparison: bool = False) -> None:
        self.view_generation += 1
        generation = self.view_generation
        current = self.current_report
        language = self.language

        def listing():
            entries = self.store.entries(self.project_dir, all_projects=command.all_projects)
            by_id = {entry.id: entry for entry in entries}
            choices = []

            def choice(entry: ReportEntry, key: str, prefix: str = "") -> ReportChoice:
                meta = entry.metadata
                available = meta.path.is_file()
                source = localized_source_label(meta.source, language)
                summary = tr(
                    language,
                    f"扫描 {meta.scanned_at} · "
                    f"阻塞 {meta.blocker} 警告 {meta.warning} 提示 {meta.info}\n"
                    f"{source}（上次读取）· 访问 {entry.last_access}",
                    f"Scanned {meta.scanned_at} · "
                    f"Blockers {meta.blocker} Warnings {meta.warning} Info {meta.info}\n"
                    f"{source} (last read) · accessed {entry.last_access}",
                )
                return ReportChoice(
                    key,
                    entry.id,
                    f"{prefix}{meta.repository} · {meta.commit[:12]} · {meta.static_status}\n"
                    f"{summary}\n{meta.path}",
                    entry.error
                    if available
                    else tr(language, "报告文件缺失或不可读", "Report file missing or unreadable"),
                )

            heading = tr(
                language,
                "报告选择器 · Enter 打开 · Esc 返回",
                "Report selector · Enter open · Esc back",
            )
            if command.batch:
                batches = self.store.batches(self.project_dir, all_projects=command.all_projects)
                batch = next((b for b in batches if b.batch_id == command.batch), None)
                if batch is None:
                    raise ValueError(
                        tr(
                            language,
                            "批次不存在或不属于当前项目。",
                            "Batch does not exist or does not belong to this project.",
                        )
                    )
                heading = tr(
                    language,
                    f"批次 {batch.batch_id} · {batch.status} · 退出码 {batch.return_code}\n",
                    f"Batch {batch.batch_id} · {batch.status} · exit code {batch.return_code}\n",
                ) + (
                    batch.warning
                    or tr(
                        language,
                        f"完整汇总: {batch.output_dir / 'batch-summary.csv'}",
                        f"Full summary: {batch.output_dir / 'batch-summary.csv'}",
                    )
                )
                for item in batch.items:
                    if item.entry_id in by_id:
                        choices.append(
                            choice(
                                by_id[item.entry_id],
                                f"batch-{item.ordinal}",
                                tr(
                                    language,
                                    f"{item.status} · ref {item.ref or '默认'} · ",
                                    f"{item.status} · ref {item.ref or 'default'} · ",
                                ),
                            )
                        )
                    else:
                        choices.append(
                            ReportChoice(
                                f"batch-{item.ordinal}",
                                None,
                                tr(
                                    language,
                                    f"{item.repository} · ref {item.ref or '默认'} · {item.status}",
                                    f"{item.repository} · ref {item.ref or 'default'} · "
                                    f"{item.status}",
                                ),
                                item.error
                                or tr(
                                    language,
                                    "报告未登记或目录索引已淘汰；扫描执行状态保持原记录",
                                    "Report not registered or catalog entry evicted; the recorded "
                                    "execution status is unchanged",
                                ),
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
                    heading += tr(
                        language,
                        "\n最近批次（/reports --batch ID）: ",
                        "\nRecent batches (/reports --batch ID): ",
                    ) + " · ".join(f"{batch.batch_id} {batch.status}" for batch in batches[:3])
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
                self._state(True)
                self.run_worker(self._execute(next_command), exit_on_error=False)

        self.push_screen(
            ReportPicker(choices, query=command.query or "", title=heading, language=self.language),
            selected,
        )

    async def _compare(self, command: Command) -> None:
        if command.target is None:
            if self.current_report is None:
                raise ValueError(
                    self._t(
                        "请先 /report 打开当前报告，再选择基线。",
                        "Open the current report with /report before choosing a baseline.",
                    )
                )
            await self._reports(Command("reports"), comparison=True)
            return
        self.view_generation += 1
        generation = self.view_generation
        current = self.current_report

        def compare():
            baseline = read_report(
                resolve_path(command.target or "", self.project_dir), self.language
            )
            after = (
                read_report(resolve_path(command.current, self.project_dir), self.language)
                if command.current
                else current
            )
            if after is None:
                raise ValueError(
                    tr(
                        self.language,
                        "请先打开当前报告，或提供两个 JSON 路径。",
                        "Open the current report first, or provide two JSON paths.",
                    )
                )
            return baseline, after, compare_reports(baseline, after)

        baseline, after, difference = await asyncio.to_thread(compare)
        if not self._valid_view(generation) or self._cancel.is_set():
            return

        def closed(_: None) -> None:
            if self._valid_view(generation):
                self.view_generation += 1
                self.query_one("#command", Input).focus()

        self.push_screen(
            ComparisonScreen(baseline, after, difference, language=self.language), closed
        )

    def _help(self) -> None:
        table = Table(box=None, padding=(0, 2, 1, 0), show_header=False)
        table.add_column(style=_ACCENT, no_wrap=False)
        table.add_column(style="#d7dde8")
        for name, (usage, description) in self._active_catalog().items():
            table.add_row(Text(f"/{name} {usage}"), Text(description))
        self._append(table)
        if self.workspace_mode == "code":
            self._write(
                self._t(
                    "直接输入文本会发送给已配置的模型；/code 消息 可快速发送。\n"
                    "默认只读；/elevate 后写文件与执行命令仍需逐次批准，/restrict 立即收回。\n"
                    "API Key 仅保存在系统凭据库或加密 vault，不会写入历史或日志。\n"
                    "Enter 发送 · Tab 补全 · ↑↓ 历史 · /scan 返回扫描 · Ctrl+Q 退出。",
                    "Plain text is sent to the configured model; /code MESSAGE sends directly.\n"
                    "Read-only by default; after /elevate each write and command still needs "
                    "approval, and /restrict revokes access immediately.\n"
                    "API keys live only in the system keyring or an encrypted vault, never in "
                    "history or logs.\n"
                    "Enter send · Tab complete · ↑↓ history · /scan back to scanning · "
                    "Ctrl+Q quit.",
                ),
                _MUTED,
            )
            return
        self._write(
            self._t(
                "带空格的路径请加引号。相对路径以启动时的项目目录为基准。\n"
                "Enter 运行 · Tab 补全 · ↑↓ 命令历史 · PgUp/PgDn 滚动 · Ctrl+P 命令面板\n"
                "仅命令交互，无模型调用；/code 进入只读 AI 代码工作区。",
                "Quote paths that contain spaces. Relative paths resolve against the project "
                "directory used at startup.\n"
                "Enter run · Tab complete · ↑↓ command history · PgUp/PgDn scroll · Ctrl+P "
                "command palette\n"
                "Command-only interaction; /code opens the read-only AI code workspace.",
            ),
            _MUTED,
        )

    def action_interrupt(self) -> None:
        if self.workspace_mode == "code":
            if self.busy:
                self._code_cancel.set()
                self._write(
                    self._t("正在取消当前请求…", "Cancelling the current request…"), "#f2b47e"
                )
            else:
                self.query_one("#command", Input).value = ""
            return
        self._filter_generation += 1
        self._catalog_cancel.set()
        if self.busy:
            self._cancel.set()
            self._write(self._t("正在取消当前任务…", "Cancelling the current task…"), "#f2b47e")
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
        self._code_cancel.set()
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
        for name, (_, description) in self._active_catalog().items():
            yield SystemCommand(f"/{name}", description, partial(self._prefill, name))

    def export_screenshot(self, *, title: str | None = None, simplify: bool = False) -> str:
        svg = super().export_screenshot(title=title, simplify=simplify)
        return align_svg_cells(svg, columns=self.size.width)
