import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { FindingCard } from "./FindingCard";

const finding = blockedReportFixture.findings[0];

it("collapses and expands details with a click", async () => {
  render(<FindingCard finding={finding} />);
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();

  const toggle = screen.getByRole("button", { name: /收起详情/ });
  await userEvent.click(toggle);

  expect(screen.queryByText("compiler = 'nvcc'")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /展开详情/ })).toHaveAttribute(
    "aria-expanded",
    "false",
  );

  await userEvent.click(screen.getByRole("button", { name: /展开详情/ }));
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();
});

it("toggles with Enter and Space keys", async () => {
  render(<FindingCard finding={finding} />);

  const toggle = screen.getByRole("button", { name: /收起详情/ });
  toggle.focus();
  await userEvent.keyboard("{Enter}");
  expect(screen.queryByText("compiler = 'nvcc'")).not.toBeInTheDocument();

  // user-event 14 中 `{Space}` 标记解析异常（key 变成 "Space" 而非空格字符），
  // 直接输入空格字符才能命中 keyMap 触发原生按钮激活行为。
  await userEvent.keyboard(" ");
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();
});

it("keeps location and severity metadata in the always-visible header", () => {
  render(<FindingCard finding={finding} />);

  expect(screen.getByText("setup.py:12")).toBeInTheDocument();
  expect(screen.getByText("阻塞")).toBeInTheDocument();
  expect(screen.getByText("MXR-TOOLCHAIN-001")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "直接调用 nvcc" })).toBeInTheDocument();
});

it("expands individual evidence and links the exact commit", async () => {
  render(<FindingCard repository={blockedReportFixture.repository} finding={{ ...finding, count: 2,
    occurrences: [{ line_start: 12, line_end: 12, evidence: "first" }, { line_start: 28, line_end: 28, evidence: "second" }] }} />);
  await userEvent.click(screen.getByText("命中位置与证据（2）"));
  expect(screen.getByText("second")).toBeVisible();
  expect(screen.getByRole("link", { name: /setup.py:28-28/ })).toHaveAttribute("href", `https://github.com/example/project/blob/${blockedReportFixture.repository.commit}/setup.py#L28`);
});
