import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { blockedReportFixture } from "../test/fixtures";
import { ReportSource } from "./ReportSource";

it.each([
  ["git-commit", "干净 Git 提交"],
  ["working-tree", "工作区快照"],
  ["declared-directory", "显式声明目录"],
] as const)("describes %s and exposes complete recorded values", (kind, label) => {
  render(<ReportSource report={{ ...blockedReportFixture, source: { kind,
    actual_commit: blockedReportFixture.repository.commit, dirty: false, input_digest: "sha256:" + "d".repeat(64) } }} />);
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(screen.getByText("sha256:" + "d".repeat(64))).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "复制已索引文件集合摘要" })).toBeInTheDocument();
});

it("handles old runtime JSON without source and incomplete records", () => {
  const { source: _source, ...legacy } = blockedReportFixture;
  const { rerender } = render(<ReportSource report={legacy as typeof blockedReportFixture} />);
  expect(screen.getByText("未记录来源元数据")).toBeInTheDocument();
  rerender(<ReportSource report={{ ...blockedReportFixture, source: { kind: "git-commit", actual_commit: null, dirty: null, input_digest: null } }} />);
  expect(screen.getByText(/来源记录不完整/)).toBeInTheDocument();
});

it("does not describe contradictory provenance as clean", () => {
  render(<ReportSource report={{ ...blockedReportFixture, source: { kind: "git-commit", actual_commit: "b".repeat(40), dirty: true, input_digest: null } }} />);
  expect(screen.getByText("来源记录不一致")).toBeInTheDocument();
  expect(screen.queryByText("干净 Git 提交")).not.toBeInTheDocument();
});
