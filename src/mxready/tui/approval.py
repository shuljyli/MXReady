"""One-time approval modal for elevated tools and session elevation."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.sanitize import safe_text


def _bindings(language: str) -> list[BindingType]:
    return [
        Binding("y", "approve", tr(language, "允许一次", "Allow once")),
        Binding("n", "deny", tr(language, "拒绝", "Deny")),
        Binding("escape", "deny", tr(language, "拒绝", "Deny")),
    ]


class ApprovalScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ApprovalScreen { align: center middle; background: #00000099; }
    ApprovalScreen > Vertical { width: 80; height: auto; border: round #f2b47e;
        background: #181e29; padding: 1 2; }
    ApprovalScreen #approval-title { height: auto; text-style: bold; color: #f2b47e; }
    ApprovalScreen #approval-summary { height: auto; text-style: bold; }
    ApprovalScreen #approval-detail { height: auto; max-height: 16; color: #d7dde8; }
    ApprovalScreen #approval-note { height: auto; color: #939fb1; margin-top: 1; }
    ApprovalScreen Horizontal { height: 3; align: right middle; margin-top: 1; }
    ApprovalScreen Button { margin-left: 2; }
    """

    def __init__(
        self, *, tool: str, summary: str, detail: str, language: str = DEFAULT_LANGUAGE
    ) -> None:
        super().__init__()
        self.language = normalize_language(language) or DEFAULT_LANGUAGE
        self.tool = tool
        self.summary = summary
        self.detail = detail
        self._bindings = BindingsMap(_bindings(self.language))

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                tr(self.language, "需要你的批准", "Approval required"),
                id="approval-title",
                markup=False,
            )
            yield Static(safe_text(self.summary), id="approval-summary", markup=False)
            yield Static(safe_text(self.detail), id="approval-detail", markup=False)
            yield Static(
                tr(
                    self.language,
                    f"工具 {self.tool} · y 允许一次 / n 拒绝",
                    f"Tool {self.tool} · y allow once / n deny",
                ),
                id="approval-note",
                markup=False,
            )
            with Horizontal():
                yield Button(
                    tr(self.language, "允许一次", "Allow once"),
                    id="approval-allow",
                    variant="warning",
                )
                yield Button(tr(self.language, "拒绝", "Deny"), id="approval-deny")

    def on_mount(self) -> None:
        self.refresh_bindings()
        self.query_one("#approval-deny", Button).focus()

    @on(Button.Pressed, "#approval-allow")
    def allow(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#approval-deny")
    def deny(self) -> None:
        self.dismiss(False)

    def action_approve(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)
