"""Exercise the actual optional MCP entry point over stdio, without network scans."""

import asyncio
import os
import sys
from uuid import uuid4

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def test_stdio_handshake_and_tools(tmp_path):
    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mxready.mcp.server"],
            env={
                **{k: v for k, v in os.environ.items() if not k.startswith("MXREADY_")},
                "MXREADY_DATA_DIR": str(tmp_path / "data"),
                "MXREADY_TEMP_DIR": str(tmp_path / "tmp"),
            },
        )
        async with (
            asyncio.timeout(30),
            stdio_client(params) as (reader, writer),
            ClientSession(reader, writer) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "MXReady"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "scan_repository",
                "get_report",
                "get_scan",
                "list_rules",
                "explain_rule",
            }
            rules = await session.call_tool("list_rules", {"severity": "blocker"})
            assert rules.structuredContent["total"] > 0
            invalid = await session.call_tool(
                "scan_repository", {"repo_url": "file:///tmp/private"}
            )
            assert invalid.structuredContent["error"]["code"] == "INVALID_REPOSITORY_URL"
            missing = await session.call_tool("get_scan", {"scan_id": str(uuid4())})
            assert missing.structuredContent["error"]["code"] == "SCAN_NOT_FOUND"

    asyncio.run(exercise())
