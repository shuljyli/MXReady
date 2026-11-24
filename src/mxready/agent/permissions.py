"""Session permissions: read-only by default; writes and commands need approval."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from mxready.agent.audit import AuditLog, record_duration


class PermissionDenied(RuntimeError):
    """The tool call was not allowed by the current session permissions."""


@dataclass(frozen=True)
class ApprovalRequest:
    tool: str
    summary: str
    detail: str


class PermissionManager:
    def __init__(
        self,
        *,
        elevated: bool = False,
        approver: Callable[[ApprovalRequest], bool] | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.elevated = elevated
        self.approver = approver
        self.audit = audit

    def set_elevated(self, value: bool) -> None:
        self.elevated = value

    def require(self, request: ApprovalRequest) -> None:
        started = time.monotonic()
        if not self.elevated:
            self._record(request, "denied", "read-only", started)
            raise PermissionDenied(
                "This tool requires elevated permissions. Ask the user to run /elevate."
            )
        allowed = False
        if self.approver is not None:
            try:
                allowed = bool(self.approver(request))
            except Exception:
                allowed = False
        if not allowed:
            self._record(request, "denied", "user", started)
            raise PermissionDenied("The user denied this tool call.")
        self._record(request, "allowed", "approved", started)

    def _record(
        self, request: ApprovalRequest, decision: str, reason: str, started: float
    ) -> None:
        if self.audit is not None:
            self.audit.record(
                tool=request.tool,
                decision=decision,
                target=f"{request.summary} | {request.detail}",
                result=reason,
                duration_ms=record_duration(started),
            )
