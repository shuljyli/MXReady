"""Assemble the read-only and approval-gated tool sets for one session."""

from __future__ import annotations

import threading
from collections.abc import Callable

from mxready.agent.permissions import PermissionManager
from mxready.agent.tools.base import Tool, WorkspaceGuard
from mxready.agent.tools.exec import RunCommandTool
from mxready.agent.tools.read import (
    ListDirTool,
    ReadFileTool,
    ReportSummaryTool,
    SearchFindingsTool,
    SearchTextTool,
)
from mxready.agent.tools.write import ApplyPatchTool, WriteFileTool
from mxready.models import ScanReport


def build_tools(
    guard: WorkspaceGuard,
    report_provider: Callable[[], ScanReport | None],
    language: str,
    permissions: PermissionManager,
    cancel_provider: Callable[[], threading.Event | None] | None = None,
) -> list[Tool]:
    return [
        ReadFileTool(guard),
        ListDirTool(guard),
        SearchTextTool(guard),
        ReportSummaryTool(report_provider, language),
        SearchFindingsTool(report_provider),
        WriteFileTool(guard, permissions),
        ApplyPatchTool(guard, permissions),
        RunCommandTool(guard, permissions, cancel_provider),
    ]
