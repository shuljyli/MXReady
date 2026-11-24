import json
import sys
import threading

import pytest

from mxready.agent.audit import AuditLog
from mxready.agent.permissions import (
    ApprovalRequest,
    PermissionDenied,
    PermissionManager,
)
from mxready.agent.tools import build_tools
from mxready.agent.tools.base import ToolError, WorkspaceGuard
from mxready.agent.tools.exec import RunCommandTool
from mxready.agent.tools.read import ListDirTool, ReadFileTool, SearchTextTool
from mxready.agent.tools.write import ApplyPatchTool, WriteFileTool


def _workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\nSECRET_LINE\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("token", encoding="utf-8")
    (root / ".env").write_text("API_KEY=sk-leak", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("x", encoding="utf-8")
    return root


def test_guard_blocks_escapes_sensitive_names_and_symlinks(tmp_path):
    root = _workspace(tmp_path)
    guard = WorkspaceGuard(root)
    assert guard.resolve("src/app.py", must_exist=True) == root / "src" / "app.py"
    for value in ("../outside", "..", str(tmp_path / "outside"), "~/secret", ".env", ".git/config"):
        with pytest.raises(ToolError):
            guard.resolve(value, must_exist=True)
    with pytest.raises(ToolError):
        guard.resolve("missing.txt", must_exist=True)
    with pytest.raises(ToolError):
        guard.resolve("bad\x00name", must_exist=False)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")
    with pytest.raises(ToolError):
        guard.resolve("link.txt", must_exist=True)


def test_read_list_and_search_are_bounded_and_skip_sensitive_entries(tmp_path):
    root = _workspace(tmp_path)
    guard = WorkspaceGuard(root)
    text = ReadFileTool(guard).run({"path": "src/app.py", "offset": 2, "limit": 1})
    assert "     2  SECRET_LINE" in text
    assert "print" not in text
    with pytest.raises(ToolError, match="not a file"):
        ReadFileTool(guard).run({"path": "src"})
    listing = ListDirTool(guard).run({})
    assert "src/app.py" in listing
    assert ".git" not in listing
    assert "node_modules" not in listing
    assert ".env" not in listing
    results = SearchTextTool(guard).run({"query": "secret_line"})
    assert "src/app.py:2" in results
    assert "sk-leak" not in results
    assert SearchTextTool(guard).run({"query": "absent"}) == "(no matches)"
    with pytest.raises(ToolError):
        SearchTextTool(guard).run({"query": "x", "glob": "../*"})


def test_write_and_patch_require_elevation_and_approval(tmp_path):
    root = _workspace(tmp_path)
    guard = WorkspaceGuard(root)
    denied_audit = AuditLog(tmp_path / "audit.jsonl", session_id="denied")
    readonly = PermissionManager(audit=denied_audit)
    with pytest.raises(PermissionDenied):
        WriteFileTool(guard, readonly).run({"path": "new.txt", "content": "x"})
    assert not (root / "new.txt").exists()

    refusal = PermissionManager(elevated=True, approver=lambda request: False)
    with pytest.raises(PermissionDenied):
        ApplyPatchTool(guard, refusal).run(
            {"path": "src/app.py", "old": "hello", "new": "bye"}
        )
    assert "hello" in (root / "src" / "app.py").read_text(encoding="utf-8")

    allowed = PermissionManager(elevated=True, approver=lambda request: True)
    WriteFileTool(guard, allowed).run({"path": "new.txt", "content": "new"})
    assert (root / "new.txt").read_text(encoding="utf-8") == "new"
    ApplyPatchTool(guard, allowed).run(
        {"path": "src/app.py", "old": "hello", "new": "bye"}
    )
    assert "bye" in (root / "src" / "app.py").read_text(encoding="utf-8")
    with pytest.raises(ToolError, match="exactly once"):
        ApplyPatchTool(guard, allowed).run(
            {"path": "src/app.py", "old": "absent", "new": "x"}
        )
    with pytest.raises(ToolError):
        WriteFileTool(guard, allowed).run({"path": ".env", "content": "x"})


def test_permission_decisions_are_audited_without_request_contents(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path, session_id="s1")
    manager = PermissionManager(elevated=True, approver=lambda request: True, audit=audit)
    manager.require(ApprovalRequest("write_file", "write a.txt", "3 bytes"))
    denied = PermissionManager(audit=audit)
    with pytest.raises(PermissionDenied):
        denied.require(ApprovalRequest("run_command", "run python", "argv"))
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [item["decision"] for item in records] == ["allowed", "denied"]
    assert records[1]["result"] == "read-only"
    assert all(item["session"] == "s1" for item in records)


def test_audit_redacts_secret_like_values(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path, session_id="s1")
    audit.record(
        tool="run_command",
        decision="allowed",
        target="api_key=sk-abcdefgh12345678 token: 123456",
        result="password=hunter2",
    )
    text = path.read_text(encoding="utf-8")
    assert "hunter2" not in text
    assert "sk-abcdefgh12345678" not in text
    assert "***" in text


def test_command_tool_rejects_shell_hosts_and_limits_argv(tmp_path):
    root = _workspace(tmp_path)
    permissions = PermissionManager(elevated=True, approver=lambda request: True)
    tool = RunCommandTool(WorkspaceGuard(root), permissions)
    for argv in (["bash", "-c", "rm -rf /"], ["cmd.exe", "/c", "dir"], ["sudo", "true"]):
        with pytest.raises(ToolError, match="Shell hosts"):
            tool.run({"argv": argv})
    with pytest.raises(ToolError):
        tool.run({"argv": []})
    with pytest.raises(ToolError):
        tool.run({"argv": ["python", "x" * 5000]})


def test_command_tool_runs_without_shell_and_strips_sensitive_environment(
    tmp_path, monkeypatch
):
    root = _workspace(tmp_path)
    permissions = PermissionManager(elevated=True, approver=lambda request: True)
    tool = RunCommandTool(WorkspaceGuard(root), permissions)
    monkeypatch.setenv("MXREADY_AGENT_API_KEY", "sk-test")
    monkeypatch.setenv("MY_SECRET_TOKEN", "leak")
    output = tool.run(
        {
            "argv": [
                sys.executable,
                "-c",
                "import os;print(os.environ.get('MY_SECRET_TOKEN', 'missing'))",
            ],
            "cwd": "src",
            "timeout": 30,
        }
    )
    assert "exit code: 0" in output
    assert "missing" in output
    assert "leak" not in output


def test_command_tool_times_out_and_reports_bounded_output(tmp_path):
    root = _workspace(tmp_path)
    permissions = PermissionManager(elevated=True, approver=lambda request: True)
    tool = RunCommandTool(WorkspaceGuard(root), permissions)
    output = tool.run(
        {
            "argv": [sys.executable, "-c", "print('x' * 40000)"],
            "timeout": 30,
        }
    )
    assert "[stream truncated]" in output
    output = tool.run(
        {"argv": [sys.executable, "-c", "import time;time.sleep(3)"], "timeout": 1}
    )
    assert "[timed out after 1s]" in output


def test_command_tool_honours_cancellation(tmp_path):
    root = _workspace(tmp_path)
    permissions = PermissionManager(elevated=True, approver=lambda request: True)
    cancel = threading.Event()
    cancel.set()
    tool = RunCommandTool(WorkspaceGuard(root), permissions, lambda: cancel)
    output = tool.run(
        {"argv": [sys.executable, "-c", "import time;time.sleep(3)"], "timeout": 30}
    )
    assert "[cancelled]" in output


def test_report_tools_report_when_no_scan_is_open(tmp_path):
    root = _workspace(tmp_path)
    tools = build_tools(
        WorkspaceGuard(root),
        lambda: None,
        "en",
        PermissionManager(),
    )
    names = [tool.name for tool in tools]
    assert names == [
        "read_file",
        "list_dir",
        "search_text",
        "report_summary",
        "search_findings",
        "write_file",
        "apply_patch",
        "run_command",
    ]
    summary = next(tool for tool in tools if tool.name == "report_summary")
    assert "No scan report" in summary.run({})
    findings = next(tool for tool in tools if tool.name == "search_findings")
    assert "No scan report" in findings.run({})
