import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { ReportView } from "./ReportView";

it("shows exact counts and code evidence without inventing a score", () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  expect(screen.getByText("阻塞项 1")).toBeInTheDocument();
  expect(screen.getByText("警告项 1")).toBeInTheDocument();
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
    screen.getByRole("heading", { name: "发现阻塞迁移的问题" }),
  ).toHaveFocus();
});

it("navigates severity filters with arrow keys", async () => {
  render(<ReportView report={blockedReportFixture} onReset={vi.fn()} />);

  screen.getByRole("button", { name: "查看全部结果（2）" }).focus();
  await userEvent.keyboard("{ArrowRight}");

  expect(screen.getByRole("button", { name: "只看阻塞项（1）" })).toHaveFocus();
  expect(screen.getByText("直接调用 nvcc")).toBeInTheDocument();
  expect(screen.queryByText("硬编码 CUDA 路径")).not.toBeInTheDocument();
});
