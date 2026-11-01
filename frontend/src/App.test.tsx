import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { createScan, getHealth, getReport, getRules, getScan, MxReadyApiError } from "./api/client";
import type { ScanJob, ScanReport } from "./api/types";
import { App } from "./App";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>();
  return {
    ...actual,
    getScan: vi.fn(),
    getReport: vi.fn(),
    getRules: vi.fn(),
    getHealth: vi.fn(),
    createScan: vi.fn(),
  };
});

const queuedJob = {
  id: "00000000-0000-0000-0000-000000000001",
  repo_url: "https://github.com/example/project",
  requested_ref: null,
  resolved_commit: null,
  status: "queued" as const,
  stage_message: "等待开始",
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
  failure_code: null,
  failure_message: null,
};

const completedReport = {
  schema_version: "1.0",
  scan_id: queuedJob.id,
  repository: {
    provider: "github",
    owner: "example",
    name: "project",
    url: queuedJob.repo_url,
    commit: "a".repeat(40),
  },
  tool_version: "0.1.0",
  ruleset_digest: null,
  extra_ruleset_version: null,
  analysis_config: {},
  ruleset_version: "2",
  scanned_at: "2026-07-29T00:00:00Z",
  summary: {
    total_count: 0,
    blocker_count: 0,
    warning_count: 0,
    info_count: 0,
    top_blockers: [],
  },
  findings: [],
  migration_checklist: [],
  analysis_warnings: [],
  static_status: "passed",
  verification_status: "not-run",
} satisfies ScanReport;

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  vi.mocked(getHealth).mockResolvedValue({ status: "ok", version: "0.3.1" });
  vi.mocked(getRules).mockResolvedValue({
    version: "2",
    extra_version: null,
    rules: ["MXR-TEST-001", "MXR-TEST-002", "MXR-TEST-003"].map((id) => ({
      id, version: 1, title: id, category: "build", severity: "warning",
      file_globs: ["*.py"], patterns: [], message: "复核构建", recommendation: "检查工具链",
      references: [], updated: null, confidence: "documented",
    })),
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.resetAllMocks();
});

it("restores a completed scan from the URL after a page refresh", async () => {
  window.history.replaceState(null, "", `/?scan=${queuedJob.id}`);
  vi.mocked(getScan).mockResolvedValue({ ...queuedJob, status: "completed" });
  vi.mocked(getReport).mockResolvedValue(completedReport);
  render(<App />);
  expect(await screen.findByText("静态检查已通过")).toBeInTheDocument();
  expect(window.location.search).toContain(queuedJob.id);
  await userEvent.click(screen.getByRole("button", { name: "扫描另一个仓库" }));
  expect(new URL(window.location.href).searchParams.has("scan")).toBe(false);
});

it("retries a temporary polling failure without abandoning the scan", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan)
    .mockRejectedValueOnce(new MxReadyApiError("NETWORK_ERROR", "暂时断开"))
    .mockResolvedValue({ ...queuedJob, status: "completed" });
  vi.mocked(getReport).mockResolvedValue(completedReport);
  render(<App initialJob={queuedJob} />);
  await act(async () => { await vi.advanceTimersByTimeAsync(1_500); });
  expect(screen.queryByText("任务中止")).not.toBeInTheDocument();
  await act(async () => { await vi.advanceTimersByTimeAsync(3_000); });
  expect(screen.getByText("静态检查已通过")).toBeInTheDocument();
});

it("cancels the active progress request when the view unmounts", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan).mockImplementation(() => new Promise(() => undefined));
  const { unmount } = render(<App initialJob={queuedJob} />);
  await act(async () => { await vi.advanceTimersByTimeAsync(1_500); });
  const signal = vi.mocked(getScan).mock.calls[0][1];
  unmount();
  expect(signal?.aborted).toBe(true);
});

it("bounds retries and lets the user resume the same scan with the keyboard", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan).mockRejectedValue(new MxReadyApiError("NETWORK_ERROR", "连接中断"));
  render(<App initialJob={queuedJob} pollIntervalMs={1} />);
  await act(async () => { await vi.advanceTimersByTimeAsync(4_000); });
  expect(getScan).toHaveBeenCalledTimes(4);
  const resume = screen.getByRole("button", { name: "继续查看扫描" });
  vi.mocked(getScan).mockResolvedValue({ ...queuedJob, status: "completed" });
  vi.mocked(getReport).mockResolvedValue(completedReport);
  vi.useRealTimers();
  resume.focus();
  await userEvent.keyboard("{Enter}");
  expect(await screen.findByText("静态检查已通过")).toBeInTheDocument();
  expect(window.location.search).toContain(queuedJob.id);
});

it("presents the product scope before a scan starts", () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: "新建体检" }),
  ).toBeInTheDocument();
  expect(screen.getByText("静态检查不等于硬件兼容认证")).toBeInTheDocument();
  expect(screen.getByLabelText("公开仓库地址")).toBeInTheDocument();
});

it("polls active jobs and loads the completed report", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan).mockResolvedValue({
    ...queuedJob,
    status: "completed",
    stage_message: "扫描完成",
    resolved_commit: "a".repeat(40),
  });
  vi.mocked(getReport).mockResolvedValue(completedReport);

  render(<App initialJob={queuedJob} />);
  expect(screen.getByText("等待开始")).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(1_500);
  });

  expect(getScan).toHaveBeenCalledWith(queuedJob.id, expect.any(AbortSignal));
  expect(getReport).toHaveBeenCalledWith(queuedJob.id, expect.any(AbortSignal));
  expect(screen.getByText("静态检查已通过")).toBeInTheDocument();
});

it("shows the report when it resolves after the progress view is replaced", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan).mockResolvedValue({
    ...queuedJob,
    status: "completed",
    stage_message: "扫描完成",
    resolved_commit: "a".repeat(40),
  });
  let resolveReport!: (report: ScanReport) => void;
  vi.mocked(getReport).mockImplementation(
    () =>
      new Promise<ScanReport>((resolve) => {
        resolveReport = resolve;
      }),
  );

  render(<App initialJob={queuedJob} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1_500);
  });

  expect(screen.getByLabelText("报告加载中")).toBeInTheDocument();

  await act(async () => {
    resolveReport(completedReport);
  });

  expect(screen.getByText("静态检查已通过")).toBeInTheDocument();
});

it("loads the report directly when the initial job is already completed", async () => {
  vi.mocked(getReport).mockResolvedValue(completedReport);

  render(
    <App
      initialJob={{
        ...queuedJob,
        status: "completed",
        stage_message: "扫描完成",
        resolved_commit: "a".repeat(40),
      }}
    />,
  );

  expect(await screen.findByText("静态检查已通过")).toBeInTheDocument();
  expect(getReport).toHaveBeenCalledWith(queuedJob.id, expect.any(AbortSignal));
});

it("stops on a failed job and can return to the form", async () => {
  vi.mocked(getScan).mockResolvedValue({
    ...queuedJob,
    status: "failed",
    stage_message: "扫描失败",
    failure_code: "CLONE_FAILED",
    failure_message: "无法获取该公开仓库。",
  });

  render(<App initialJob={queuedJob} pollIntervalMs={1} />);
  expect(await screen.findByText("无法获取该公开仓库。")).toBeInTheDocument();
  expect(screen.getByText("CLONE_FAILED")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "重新开始" }));
  expect(screen.getByLabelText("公开仓库地址")).toBeInTheDocument();
});

it("shows a skeleton while the completed report is loading", async () => {
  vi.useFakeTimers();
  vi.mocked(getScan).mockResolvedValue({
    ...queuedJob,
    status: "completed",
    stage_message: "扫描完成",
    resolved_commit: "a".repeat(40),
  });
  vi.mocked(getReport).mockImplementation(
    () => new Promise(() => undefined),
  );

  render(<App initialJob={queuedJob} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1_500);
  });

  expect(screen.getByLabelText("报告加载中")).toBeInTheDocument();
});

it("shows the rule count loaded from the rules API", async () => {
  render(<App />);

  expect(await screen.findByText("规则集 v2 · 3 项")).toBeInTheDocument();
});

it("keeps the form usable when the rules catalog is unavailable", async () => {
  vi.mocked(getRules).mockRejectedValue(new Error("offline"));
  render(<App />);
  expect(await screen.findByLabelText("公开仓库地址")).toBeEnabled();
  expect(await screen.findByText("规则集暂不可用")).toBeInTheDocument();
  expect(screen.queryByText(/规则集 v1 ·/)).not.toBeInTheDocument();
});

it("keeps the active scan across MCP navigation and browser history", async () => {
  vi.mocked(getScan).mockResolvedValue({ ...queuedJob, status: "completed" });
  vi.mocked(getReport).mockResolvedValue(completedReport);
  render(<App initialJob={queuedJob} pollIntervalMs={1} />);
  await userEvent.click(screen.getByRole("link", { name: "MCP 接入" }));
  expect(screen.getByRole("heading", { name: "MCP 接入" })).toHaveFocus();
  expect(window.location.search).toContain("page=mcp");
  expect(window.location.search).toContain(queuedJob.id);
  await userEvent.click(screen.getByRole("link", { name: "源码体检" }));
  expect(await screen.findByText("静态检查已通过")).toBeInTheDocument();
  window.history.replaceState(null, "", `/?page=mcp&scan=${queuedJob.id}`);
  await act(async () => { window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByRole("heading", { name: "MCP 接入" })).toBeInTheDocument();
});

it("opens an existing scan by id and preserves interrupted-task identity", async () => {
  vi.mocked(getScan).mockResolvedValue({ ...queuedJob, status: "failed",
    failure_code: "SCAN_INTERRUPTED", failure_message: "执行租约已过期。" });
  render(<App />);
  await userEvent.click(screen.getByText("打开已有扫描"));
  await userEvent.type(screen.getByLabelText("扫描 ID"), "invalid");
  await userEvent.click(screen.getByRole("button", { name: "打开扫描" }));
  expect(screen.getByRole("alert")).toHaveTextContent("请输入完整的扫描 UUID");
  expect(getScan).not.toHaveBeenCalled();
  await userEvent.clear(screen.getByLabelText("扫描 ID"));
  await userEvent.type(screen.getByLabelText("扫描 ID"), queuedJob.id);
  await userEvent.click(screen.getByRole("button", { name: "打开扫描" }));
  expect(await screen.findByText(/原任务不会自动重放/)).toBeInTheDocument();
  expect(new URL(window.location.href).searchParams.get("scan")).toBe(queuedJob.id);
  await userEvent.click(screen.getByText("任务详情"));
  expect(screen.getByText(queuedJob.id)).toBeVisible();
  expect(screen.queryByRole("button", { name: "继续查看扫描" })).not.toBeInTheDocument();
});

it("prefills a pinned rescan and waits for an explicit submission", async () => {
  vi.mocked(getReport).mockResolvedValue(completedReport);
  render(<App initialJob={{ ...queuedJob, status: "completed" }} />);
  await userEvent.click(await screen.findByRole("button", { name: "同仓库重新扫描" }));
  expect(screen.getByLabelText("公开仓库地址")).toHaveValue(completedReport.repository.url);
  expect(screen.getByLabelText("分支、标签或提交（可选）")).toHaveValue(completedReport.repository.commit);
  expect(createScan).not.toHaveBeenCalled();
});

it("finishes a scan in the background without stealing MCP page focus", async () => {
  const user = userEvent.setup();
  let finish!: (job: ScanJob) => void;
  vi.mocked(getScan).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  vi.mocked(getReport).mockResolvedValue(completedReport);
  render(<App initialJob={queuedJob} pollIntervalMs={1} />);
  await user.click(screen.getByRole("link", { name: "MCP 接入" }));
  await waitFor(() => expect(getScan).toHaveBeenCalledOnce());
  expect(vi.mocked(getScan).mock.calls[0][1]?.aborted).toBe(false);
  await act(async () => { finish({ ...queuedJob, status: "completed" }); });
  expect(screen.getByRole("heading", { name: "MCP 接入" })).toHaveFocus();
  expect(screen.queryByText("静态检查已通过")).not.toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "源码体检" }));
  expect(screen.getByText("静态检查已通过")).toBeInTheDocument();
  expect(getScan).toHaveBeenCalledOnce();
});

it("provides a keyboard skip link to the workspace", async () => {
  render(<App />);
  await userEvent.tab();
  expect(screen.getByRole("link", { name: "跳至主要内容" })).toHaveFocus();
  expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
});
