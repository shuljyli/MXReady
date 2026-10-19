import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import type { ScanJob } from "../api/types";
import { ScanProgress } from "./ScanProgress";

function job(overrides: Partial<ScanJob> = {}): ScanJob {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    repo_url: "https://github.com/pytorch/extension-cpp",
    requested_ref: null,
    resolved_commit: null,
    status: "queued",
    stage_message: "等待开始",
    created_at: "2026-07-29T00:00:00Z",
    updated_at: "2026-07-29T00:00:00Z",
    failure_code: null,
    failure_message: null,
    ...overrides,
  };
}

function stageState(label: string): string {
  const item = screen.getByText(label).closest("li");
  return item?.className ?? "";
}

it("shows the normalized repository name and the current stage message", () => {
  render(<ScanProgress job={job({ stage_message: "正在安全获取仓库" })} />);

  expect(
    screen.getByRole("heading", { name: "pytorch/extension-cpp" }),
  ).toBeInTheDocument();
  expect(screen.getByText("正在安全获取仓库")).toBeInTheDocument();
});

it("marks earlier stages done, the current stage active and later stages waiting", () => {
  render(<ScanProgress job={job({ status: "indexing" })} />);

  expect(stageState("任务排队")).toContain("stage-done");
  expect(stageState("安全获取")).toContain("stage-done");
  expect(stageState("源码索引")).toContain("stage-active");
  expect(stageState("规则分析")).toContain("stage-waiting");
  expect(stageState("生成报告")).toContain("stage-waiting");
  expect(screen.getByText("进行中")).toBeInTheDocument();
});

it("keeps every stage waiting when the job has failed", () => {
  const { container } = render(
    <ScanProgress job={job({ status: "failed", stage_message: "扫描失败" })} />,
  );

  expect(container.querySelectorAll(".stage-active")).toHaveLength(0);
  expect(container.querySelectorAll(".stage-done")).toHaveLength(0);
  expect(container.querySelectorAll(".stage-waiting")).toHaveLength(5);
});
