import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { blockedReportFixture } from "../test/fixtures";
import { BatchScans } from "./BatchScans";
import { FindingReviews } from "./FindingReviews";
import { RemediationGuide } from "./RemediationGuide";
vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof client>("../api/client");
  return { ...actual, createScan: vi.fn(), getScan: vi.fn(), getReviews: vi.fn(), saveReview: vi.fn() };
});
beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); });
afterEach(cleanup);

it("saves a reason and loads review history without modifying the report", async () => {
  vi.mocked(client.getReviews).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
  vi.mocked(client.saveReview).mockResolvedValue({ id: 1, created_at: new Date().toISOString(), rule_id: "MXR-TOOLCHAIN-001", relative_path: "setup.py", status: "false-positive", reason: "test fixture only" });
  render(<FindingReviews report={blockedReportFixture} />);
  await userEvent.click(screen.getByText("人工复核与误报反馈"));
  await waitFor(() => expect(client.getReviews).toHaveBeenCalled());
  await userEvent.selectOptions(screen.getByLabelText("复核结论"), "false-positive");
  await userEvent.type(screen.getByLabelText("判断依据"), "test fixture only");
  await userEvent.click(screen.getByRole("button", { name: "保存复核记录" }));
  await waitFor(() => expect(client.saveReview).toHaveBeenCalledWith(blockedReportFixture.scan_id, expect.objectContaining({ status: "false-positive", reason: "test fixture only" })));
  expect(blockedReportFixture.static_status).toBe("blocked");
});

it("keeps ambiguous submission failures and never automatically resubmits", async () => {
  vi.mocked(client.createScan).mockRejectedValue(new client.MxReadyApiError("REQUEST_TIMEOUT", "timeout"));
  render(<BatchScans onOpen={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("批量仓库列表"), { target: { value: "https://github.com/example/one main\nhttps://gitee.com/example/two" } });
  await userEvent.click(screen.getByRole("button", { name: "提交批量扫描" }));
  await waitFor(() => expect(client.createScan).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getAllByText(/提交状态不确定/)).toHaveLength(2));
  expect(screen.queryByRole("button", { name: /新建重试/ })).not.toBeInTheDocument();
  expect(JSON.parse(sessionStorage.getItem("mxready-batch-v1")!)).toHaveLength(2);
});

it("rejects oversized batches before creating jobs", async () => {
  render(<BatchScans onOpen={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("批量仓库列表"), { target: { value: Array(11).fill("https://github.com/example/project").join("\n") } });
  await userEvent.click(screen.getByRole("button", { name: "提交批量扫描" }));
  expect(screen.getByRole("alert")).toHaveTextContent("1–10");
  expect(client.createScan).not.toHaveBeenCalled();
});

it("shows conditional remediation examples without executing them", async () => {
  render(<RemediationGuide finding={blockedReportFixture.findings[0]} />);
  await userEvent.click(screen.getByText("整改示例与验证步骤"));
  expect(screen.getByText(/不是对当前文件的自动补丁/)).toBeVisible();
  expect(screen.getByText(/由受控构建环境提供/)).toBeVisible();
});

it("creates a new job only after an explicit retry of a rejected submission", async () => {
  vi.mocked(client.createScan).mockRejectedValueOnce(new client.MxReadyApiError("SCAN_LIMIT_REACHED", "queue full", {}, 429))
    .mockResolvedValueOnce({ id: "new-scan-id", repo_url: "https://github.com/example/one", requested_ref: null,
      resolved_commit: null, status: "queued", stage_message: "Waiting", created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(), failure_code: null, failure_message: null });
  render(<BatchScans onOpen={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("批量仓库列表"), { target: { value: "https://github.com/example/one" } });
  await userEvent.click(screen.getByRole("button", { name: "提交批量扫描" }));
  const retry = await screen.findByRole("button", { name: /新建重试/ });
  expect(client.createScan).toHaveBeenCalledTimes(1);
  await userEvent.click(retry);
  await expect(screen.findByRole("button", { name: "打开任务 new-scan-id" })).resolves.toBeInTheDocument();
  expect(client.createScan).toHaveBeenCalledTimes(2);
});
