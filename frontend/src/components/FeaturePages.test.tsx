import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import type { RuleCatalog } from "../api/types";
import { blockedReportFixture } from "../test/fixtures";
import { CopyButton } from "./CopyButton";
import { McpIntegration } from "./McpIntegration";
import { RuleCatalogView } from "./RuleCatalogView";

export const catalogFixture: RuleCatalog = {
  version: "4", extra_version: "custom-2", rules: [{
    id: "MXR-TOOLCHAIN-001", version: 2, title: "直接调用 nvcc", category: "toolchain",
    severity: "blocker", file_globs: ["*.py"], patterns: [{
      type: "regex", expression: "nvcc", flags: [], name: null, equals: null,
    }], message: "需要复核编译器。", recommendation: "参数化工具链。",
    references: [{ title: "官方依据", url: "https://example.com/reference" }],
    updated: "2026-10-31", confidence: "needs-review",
  }, {
    id: "MXR-PATH-001", version: 1, title: "CUDA 路径", category: "build",
    severity: "warning", file_globs: ["*.txt"], patterns: [], message: "路径需复核。",
    recommendation: "配置路径。", references: [], updated: null, confidence: "documented",
  }],
};

afterEach(() => vi.restoreAllMocks());

it("keeps copy text accessible when clipboard access fails", async () => {
  const user = userEvent.setup();
  vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
  render(<CopyButton label="复制配置" text={'{"path":"C:\\some folder"}'} />);
  screen.getByRole("button", { name: "复制配置" }).focus();
  await user.keyboard("{Enter}");
  expect(screen.getByRole("status")).toHaveTextContent("请手动复制");
  expect(screen.getByRole("textbox", { name: "复制内容：复制配置" })).toHaveValue(
    '{"path":"C:\\some folder"}',
  );
});

it("builds escaped stdio configuration and copies a commit-pinned handoff", async () => {
  const user = userEvent.setup();
  const write = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
  render(<McpIntegration report={blockedReportFixture} />);
  await user.clear(screen.getByLabelText("Python 可执行文件绝对路径"));
  await user.type(screen.getByLabelText("Python 可执行文件绝对路径"), 'C:\\My Env\\python.exe');
  await user.clear(screen.getByLabelText("Web 与 MCP 共用的数据目录"));
  await user.type(screen.getByLabelText("Web 与 MCP 共用的数据目录"), 'C:\\data "shared"');
  await user.click(screen.getByRole("button", { name: "复制 MCP 配置" }));
  const config = JSON.parse(write.mock.calls[0][0]);
  expect(config.mcpServers.mxready).toMatchObject({
    command: 'C:\\My Env\\python.exe', args: ["-m", "mxready.mcp.server"],
    env: { MXREADY_DATA_DIR: 'C:\\data "shared"' },
  });
  for (const name of ["scan_repository", "get_report", "list_rules", "explain_rule"]) {
    expect(screen.getByRole("heading", { name })).toBeInTheDocument();
  }
  await user.click(screen.getByRole("button", { name: "复制 Agent 交接内容" }));
  const handoff = write.mock.calls.at(-1)![0];
  expect(handoff).toContain(blockedReportFixture.scan_id);
  expect(handoff).toContain(blockedReportFixture.repository.commit);
  expect(handoff).toContain("findings_truncated");
  expect(screen.queryByText("已连接")).not.toBeInTheDocument();
});

it("filters complete rules and warns about historical rule versions", async () => {
  const user = userEvent.setup();
  render(<RuleCatalogView catalog={catalogFixture} loading={false} error={null}
    onRetry={vi.fn()} selectedRule="MXR-TOOLCHAIN-001" historicalVersion={1} />);
  expect(screen.getByText(/历史报告使用 v1/)).toBeVisible();
  expect(screen.getByText("需人工复核")).toBeVisible();
  await user.selectOptions(screen.getByLabelText("规则严重级别"), "warning");
  const results = screen.getByRole("region", { name: "规则列表" });
  expect(within(results).getByText("CUDA 路径")).toBeInTheDocument();
  expect(within(results).queryByText("直接调用 nvcc")).not.toBeInTheDocument();
  await user.type(screen.getByLabelText("搜索规则"), "不存在");
  expect(screen.getByText("没有匹配的规则")).toBeInTheDocument();
});

it("switches to Unix paths and rejects relative configuration paths", async () => {
  const user = userEvent.setup();
  const write = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
  render(<McpIntegration />);
  await user.selectOptions(screen.getByLabelText("路径示例平台"), "unix");
  await user.click(screen.getByRole("button", { name: "复制 MCP 配置" }));
  const config = JSON.parse(write.mock.calls[0][0]).mcpServers.mxready;
  expect(config.command).toBe("/path/to/python-env/bin/python");
  expect(config.env.MXREADY_TEMP_DIR).toBe("/path/to/mxready-data/tmp");
  await user.clear(screen.getByLabelText("Python 可执行文件绝对路径"));
  await user.type(screen.getByLabelText("Python 可执行文件绝对路径"), "./python");
  expect(screen.getByRole("alert")).toHaveTextContent("请填写绝对路径");
  expect(screen.queryByRole("button", { name: "复制 MCP 配置" })).not.toBeInTheDocument();
});

it("renders untrusted rule prose as text and blocks unsafe reference URLs", async () => {
  const hostile = '<img src=x onerror="alert(1)">';
  const catalog = { ...catalogFixture, rules: [{ ...catalogFixture.rules[0],
    message: hostile, references: [{ title: "恶意链接", url: "javascript:alert(1)" }],
  }] };
  const { container } = render(<RuleCatalogView catalog={catalog} loading={false} error={null}
    onRetry={vi.fn()} selectedRule={catalog.rules[0].id} />);
  expect(screen.getByText(hostile)).toBeVisible();
  expect(container.querySelector("img")).toBeNull();
  expect(screen.queryByRole("link", { name: "恶意链接" })).not.toBeInTheDocument();
});

it("retries failed rules and explains an unavailable historical rule", async () => {
  const retry = vi.fn();
  const { rerender } = render(<RuleCatalogView catalog={null} loading={false} error="无法读取规则"
    onRetry={retry} />);
  await userEvent.click(screen.getByRole("button", { name: "重试加载规则" }));
  expect(retry).toHaveBeenCalledOnce();
  rerender(<RuleCatalogView catalog={catalogFixture} loading={false} error={null} onRetry={retry}
    selectedRule="MXR-REMOVED-001" historicalVersion={1} />);
  expect(screen.getByText(/当前规则库未包含 MXR-REMOVED-001/)).toBeVisible();
});
