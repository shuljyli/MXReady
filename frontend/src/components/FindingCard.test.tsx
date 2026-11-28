import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { FindingCard } from "./FindingCard";

const finding = blockedReportFixture.findings[0];

it.each([
  ["working-tree", "查看关联提交（可能与工作区不同）"],
  ["declared-directory", "声明提交（未核对来源）"],
] as const)("qualifies remote links for %s", (kind, label) => {
  render(<FindingCard finding={finding} repository={blockedReportFixture.repository}
    source={{ kind, actual_commit: null, dirty: null, input_digest: null }} />);
  expect(screen.getByRole("link", { name: new RegExp(label.replace(/[（）]/g, ".")) })).toBeInTheDocument();
});

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

it("keeps non-blocking findings collapsed until expanded by keyboard", async () => {
  render(<FindingCard finding={blockedReportFixture.findings[1]} />);

  expect(screen.getByText("硬编码 CUDA 路径")).toBeInTheDocument();
  expect(screen.queryByText("构建配置绑定了 CUDA 默认安装目录。")).not.toBeInTheDocument();

  const toggle = screen.getByRole("button", { name: "展开详情：硬编码 CUDA 路径" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  toggle.focus();
  await userEvent.keyboard("{Enter}");
  expect(screen.getByText("构建配置绑定了 CUDA 默认安装目录。")).toBeInTheDocument();
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

it("renders compatible operator alternatives with safe reference links", () => {
  render(<FindingCard finding={{
    ...finding,
    compatible_alternatives: [
      {
        operator: "torch.nn.functional.scaled_dot_product_attention",
        summary: "PyTorch 原生注意力算子。",
        applies_when: "标准注意力",
        caveat: "需在目标设备实测数值。",
        reference: { title: "PyTorch SDPA", url: "https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html" },
      },
      {
        operator: "unsafe-link-op",
        summary: "测试不安全链接回退。",
        applies_when: "测试",
        caveat: "不可执行",
        reference: { title: "Bad Ref", url: "javascript:alert(1)" },
      },
    ],
  }} />);

  expect(screen.getByText("推荐通用兼容算子")).toBeInTheDocument();
  expect(screen.getByText("torch.nn.functional.scaled_dot_product_attention")).toBeInTheDocument();
  expect(screen.getByText("适用条件：标准注意力")).toBeInTheDocument();
  expect(screen.getByText("注意事项：需在目标设备实测数值。")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /PyTorch SDPA/ })).toHaveAttribute(
    "href",
    "https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html",
  );
  expect(screen.getByText("Bad Ref（无有效 HTTPS 链接）")).toBeInTheDocument();
});
