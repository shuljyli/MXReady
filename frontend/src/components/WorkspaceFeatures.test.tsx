import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { getReport, listScans, updateChecklist } from "../api/client";
import { blockedReportFixture, staticPassedFixture } from "../test/fixtures";
import { ScanHistory } from "./ScanHistory";
import { ReportView } from "./ReportView";

vi.mock("../api/client", async (original) => ({
  ...await original<typeof import("../api/client")>(), listScans: vi.fn(),
  listVerifications: vi.fn(), getVerification: vi.fn(), updateChecklist: vi.fn(), getReport: vi.fn(),
}));

beforeEach(() => {
  vi.resetAllMocks(); sessionStorage.clear();
  vi.mocked(listScans).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
});

it("searches scan history and opens a selected scan", async () => {
  vi.mocked(listScans).mockResolvedValue({ items: [{ id: staticPassedFixture.scan_id,
    repo_url: staticPassedFixture.repository.url, requested_ref: null, resolved_commit: "a".repeat(40),
    status: "completed", stage_message: "完成", created_at: staticPassedFixture.scanned_at,
    updated_at: staticPassedFixture.scanned_at, failure_code: null, failure_message: null }], total: 1, limit: 20, offset: 0 });
  const open = vi.fn();
  render(<ScanHistory onOpen={open} />);
  await userEvent.click(await screen.findByRole("button", { name: /打开扫描/ }));
  expect(open).toHaveBeenCalledWith(staticPassedFixture.scan_id);
  await userEvent.type(screen.getByLabelText("搜索仓库"), "project");
  await userEvent.selectOptions(screen.getByLabelText("任务状态"), "completed");
  await userEvent.click(screen.getByRole("button", { name: "查询历史" }));
  await waitFor(() => expect(listScans).toHaveBeenLastCalledWith(expect.objectContaining({ q: "project", status: "completed", offset: 0 }), expect.any(AbortSignal)));
});

it("bounds large-report rendering and restores saved filters", async () => {
  const report = { ...blockedReportFixture, findings: Array.from({ length: 123 }, (_, i) => ({
    ...blockedReportFixture.findings[0], relative_path: `file-${i}.cu`,
  })), summary: { ...blockedReportFixture.summary, total_count: 123 } };
  const { unmount } = render(<ReportView report={report} onReset={vi.fn()} />);
  expect(screen.getAllByRole("article")).toHaveLength(50);
  await userEvent.click(screen.getByRole("button", { name: "发现下一页" }));
  expect(screen.getAllByRole("article")).toHaveLength(50);
  fireEvent.change(screen.getByRole("searchbox", { name: "搜索发现" }), { target: { value: "file-122" } });
  expect(screen.getAllByRole("article")).toHaveLength(1);
  unmount();
  render(<ReportView report={report} onReset={vi.fn()} />);
  expect(screen.getByRole("searchbox", { name: "搜索发现" })).toHaveValue("file-122");
});

it("persists a manual checklist item without changing static status", async () => {
  const updated = { ...blockedReportFixture, migration_checklist: blockedReportFixture.migration_checklist.map((i) => ({ ...i, completed: true })) };
  vi.mocked(updateChecklist).mockResolvedValue(updated);
  const onUpdated = vi.fn();
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} onUpdated={onUpdated} />);
  await userEvent.click(screen.getAllByRole("checkbox")[0]);
  await waitFor(() => expect(onUpdated).toHaveBeenCalledWith(updated, "checklist"));
  expect(updated.static_status).toBe("blocked");
});

it("compares reports and rejects different repositories", async () => {
  vi.mocked(getReport).mockResolvedValue({ ...staticPassedFixture, scan_id: "00000000-0000-0000-0000-000000000002" });
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  await userEvent.click(screen.getByText("对比另一份报告"));
  await userEvent.type(screen.getByLabelText("基线扫描 ID"), "00000000-0000-0000-0000-000000000002");
  await userEvent.click(screen.getByRole("button", { name: "开始对比" }));
  expect(await screen.findByText("新增 2 · 消失 0 · 保留 0 · 级别变化 0 · 次数变化 0")).toBeInTheDocument();
  vi.mocked(getReport).mockResolvedValue({ ...staticPassedFixture, repository: { ...staticPassedFixture.repository, url: "https://github.com/other/repo" } });
  await userEvent.click(screen.getByRole("button", { name: "开始对比" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("同一仓库");
});

it("offers same-repository completed scans as baseline candidates", async () => {
  const candidate = { id: "00000000-0000-0000-0000-000000000003", repo_url: blockedReportFixture.repository.url,
    requested_ref: null, resolved_commit: "b".repeat(40), status: "completed" as const, stage_message: "完成",
    created_at: blockedReportFixture.scanned_at, updated_at: blockedReportFixture.scanned_at,
    failure_code: null, failure_message: null };
  vi.mocked(listScans).mockResolvedValue({
    items: [{ ...candidate, id: blockedReportFixture.scan_id }, candidate], total: 2, limit: 20, offset: 0 });
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  await userEvent.click(screen.getByText("对比另一份报告"));

  expect(await screen.findByText(/^b{12} ·/)).toHaveAttribute("value", candidate.id);
  expect(screen.queryByText(/^a{12} ·/)).not.toBeInTheDocument();
  expect(listScans).toHaveBeenLastCalledWith(
    expect.objectContaining({ q: blockedReportFixture.repository.url, status: "completed", offset: 0 }),
    expect.any(AbortSignal));
  await userEvent.type(screen.getByLabelText("基线扫描 ID"), candidate.id);
  expect(screen.getByLabelText("基线扫描 ID")).toHaveValue(candidate.id);
});
