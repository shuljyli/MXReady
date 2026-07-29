import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { createScan } from "../api/client";
import { ScanForm } from "./ScanForm";

vi.mock("../api/client", () => ({ createScan: vi.fn() }));
const mockedCreateScan = vi.mocked(createScan);

beforeEach(() => {
  mockedCreateScan.mockResolvedValue({
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
  });
});

it("submits a normalized public repository request", async () => {
  const onCreated = vi.fn();
  render(<ScanForm onCreated={onCreated} />);

  await userEvent.type(
    screen.getByLabelText("公开仓库地址"),
    "  https://github.com/pytorch/extension-cpp  ",
  );
  await userEvent.click(screen.getByRole("button", { name: "开始体检" }));

  expect(mockedCreateScan).toHaveBeenCalledWith({
    repo_url: "https://github.com/pytorch/extension-cpp",
    ref: null,
  });
  expect(onCreated).toHaveBeenCalledWith(
    expect.objectContaining({ status: "queued" }),
  );
});

it("submits an optional branch or tag and prevents duplicate submits", async () => {
  let resolveRequest:
    | ((job: Awaited<ReturnType<typeof createScan>>) => void)
    | undefined;
  mockedCreateScan.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );

  render(<ScanForm onCreated={vi.fn()} />);
  await userEvent.type(
    screen.getByLabelText("公开仓库地址"),
    "https://gitee.com/example/project",
  );
  await userEvent.type(screen.getByLabelText("分支、标签或提交（可选）"), " main ");
  const submit = screen.getByRole("button", { name: "开始体检" });
  await userEvent.click(submit);

  expect(mockedCreateScan).toHaveBeenCalledWith({
    repo_url: "https://gitee.com/example/project",
    ref: "main",
  });
  expect(submit).toBeDisabled();
  resolveRequest?.({
    id: "00000000-0000-0000-0000-000000000001",
    repo_url: "https://gitee.com/example/project",
    requested_ref: "main",
    resolved_commit: null,
    status: "queued",
    stage_message: "等待开始",
    created_at: "2026-07-29T00:00:00Z",
    updated_at: "2026-07-29T00:00:00Z",
    failure_code: null,
    failure_message: null,
  });
});

it("shows the structured API error without losing the entered address", async () => {
  mockedCreateScan.mockRejectedValue({
    code: "REPOSITORY_NOT_ALLOWED",
    message: "目前只支持 GitHub 与 Gitee 的公开仓库。",
  });
  render(<ScanForm onCreated={vi.fn()} />);

  const input = screen.getByLabelText("公开仓库地址");
  await userEvent.type(input, "https://example.com/private/repo");
  await userEvent.click(screen.getByRole("button", { name: "开始体检" }));

  expect(
    await screen.findByText("目前只支持 GitHub 与 Gitee 的公开仓库。"),
  ).toHaveAttribute("role", "alert");
  expect(input).toHaveValue("https://example.com/private/repo");
});
