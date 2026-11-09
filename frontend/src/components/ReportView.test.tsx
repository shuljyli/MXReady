import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { getReport } from "../api/client";
import { ReportView } from "./ReportView";

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(), getReport: vi.fn(),
}));

it("combines file and text filters without confusing occurrences with findings", async () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "展开详情：硬编码 CUDA 路径" }));
  expect(screen.getByText("同规则在此文件聚合命中 2 次")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "优先复核 setup.py" }));
  expect(screen.queryByText("硬编码 CUDA 路径")).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("搜索发现"), "不存在");
  expect(screen.getByText("当前筛选下没有结果")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "清除筛选" }));
  expect(screen.getByText("硬编码 CUDA 路径")).toBeInTheDocument();
});

it("refreshes verification from the server and shows missing historical metadata", async () => {
  const onUpdated = vi.fn();
  const updated = { ...blockedReportFixture, verification_status: "stale" as const };
  vi.mocked(getReport).mockResolvedValue(updated);
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} onUpdated={onUpdated} />);
  await userEvent.click(screen.getByText("报告详情"));
  expect(screen.getByText("未记录分析配置")).toBeVisible();
  expect(screen.getByText("无扩展规则版本记录")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "刷新报告" }));
  expect(getReport).toHaveBeenCalledWith(blockedReportFixture.scan_id, expect.any(AbortSignal));
  expect(onUpdated).toHaveBeenCalledWith(updated);
});

it("discards an older refresh after an uploaded report replaces it", async () => {
  let finish!: (value: typeof blockedReportFixture) => void;
  vi.mocked(getReport).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  const onUpdated = vi.fn();
  const { rerender } = render(<ReportView report={blockedReportFixture} onReset={vi.fn()} onUpdated={onUpdated} />);
  await userEvent.click(screen.getByRole("button", { name: "刷新报告" }));
  const signal = vi.mocked(getReport).mock.calls.at(-1)![1];
  rerender(<ReportView report={{ ...blockedReportFixture, verification_status: "verified" }}
    onReset={vi.fn()} onUpdated={onUpdated} />);
  expect(signal?.aborted).toBe(true);
  await act(async () => { finish(blockedReportFixture); });
  expect(onUpdated).not.toHaveBeenCalled();
  expect(screen.getByRole("region", { name: "真机验证状态" })).toHaveTextContent("真机环境已验证");
});

it("keeps a warning-only priority list useful and renders metadata from its snapshot", async () => {
  const report = { ...blockedReportFixture, static_status: "warnings" as const,
    findings: [blockedReportFixture.findings[1]], ruleset_digest: "sha256:" + "f".repeat(64),
    extra_ruleset_version: "custom-1", analysis_config: { prefilter: "unavailable", max_findings: 100 },
    summary: { total_count: 1, blocker_count: 0, warning_count: 1, info_count: 0, top_blockers: ["CMakeLists.txt"] },
  };
  render(<ReportView report={report} onReset={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "优先复核 CMakeLists.txt" }));
  expect(screen.getByLabelText("发现文件")).toHaveValue("CMakeLists.txt");
  await userEvent.click(screen.getByText("报告详情"));
  expect(screen.getByText(report.ruleset_digest)).toBeVisible();
  expect(screen.getByText("custom-1")).toBeVisible();
  expect(screen.getByText(/"prefilter": "unavailable"/)).toBeVisible();
});

it("keeps the current report usable when a refresh fails", async () => {
  vi.mocked(getReport).mockRejectedValue(new Error("刷新连接中断"));
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "刷新报告" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("刷新连接中断");
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "刷新报告" })).toBeEnabled();
});

it("shows exact counts and code evidence without inventing a score", () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  expect(screen.getByLabelText("阻塞项 1")).toBeInTheDocument();
  expect(screen.getByLabelText("警告项 1")).toBeInTheDocument();
  expect(screen.getByText("setup.py:12")).toBeInTheDocument();
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();
  expect(screen.getByText("aaaaaaaaaaaa")).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

it("filters findings by severity and exposes authoritative references", async () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  await userEvent.click(
    screen.getByRole("button", { name: "只看阻塞项（1）" }),
  );
  expect(screen.getByText("直接调用 nvcc")).toBeInTheDocument();
  expect(screen.queryByText("硬编码 CUDA 路径")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "cu-bridge README" })).toHaveAttribute(
    "rel",
    "noreferrer",
  );
});

it("offers deterministic report, badge, and verification downloads", () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  const base = `/api/scans/${blockedReportFixture.scan_id}`;

  expect(screen.getByRole("link", { name: "JSON" })).toHaveAttribute(
    "href",
    `${base}/report.json`,
  );
  expect(screen.getByRole("link", { name: "Markdown" })).toHaveAttribute(
    "href",
    `${base}/report.md`,
  );
  expect(screen.getByRole("link", { name: "Badge" })).toHaveAttribute(
    "href",
    `${base}/badge.svg`,
  );
  expect(
    screen.getByRole("link", { name: "下载远程验证包" }),
  ).toHaveAttribute("href", `${base}/verification-bundle`);
});

it("moves focus to the report heading when the view opens", () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  expect(
    screen.getByRole("heading", { name: "迁移报告" }),
  ).toHaveFocus();
});

it("keeps static and hardware conclusions in separately named regions", () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);
  expect(screen.getByRole("region", { name: "静态检查" })).toHaveTextContent("发现阻塞迁移的问题");
  expect(screen.getByRole("region", { name: "真机验证状态" })).toHaveTextContent("未做真机验证");
});

it("preserves scan scope warnings and metadata in the redesigned report", () => {
  render(<ReportView report={{ ...blockedReportFixture, analysis_warnings: [{
    code: "FILE_SKIPPED", relative_path: "large.cu", message: "文件超过分析限制。",
  }] }} onReset={vi.fn()} />);
  expect(screen.getByRole("region", { name: "扫描范围提示" })).toHaveTextContent("large.cu");
  expect(screen.getByText("文件超过分析限制。")).toBeInTheDocument();
  expect(screen.getByText("规则 / 工具")).toBeInTheDocument();
  expect(screen.getByText("扫描时间")).toBeInTheDocument();
});

it("navigates severity filters with arrow keys", async () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  screen.getByRole("button", { name: "查看全部结果（2）" }).focus();
  await userEvent.keyboard("{ArrowRight}");

  expect(screen.getByRole("button", { name: "只看阻塞项（1）" })).toHaveFocus();
  expect(screen.getByText("直接调用 nvcc")).toBeInTheDocument();
  expect(screen.queryByText("硬编码 CUDA 路径")).not.toBeInTheDocument();
});
