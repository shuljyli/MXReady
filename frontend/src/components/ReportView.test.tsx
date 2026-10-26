import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { ReportView } from "./ReportView";

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
