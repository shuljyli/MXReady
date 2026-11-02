import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { getHealth, getReport, getRules, uploadVerification } from "./api/client";
import type { ScanJob, ScanReport } from "./api/types";
import { staticPassedFixture } from "./test/fixtures";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>();
  return { ...actual, getHealth: vi.fn(), getReport: vi.fn(), getRules: vi.fn(), uploadVerification: vi.fn() };
});

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/");
  vi.mocked(getHealth).mockResolvedValue({ status: "ok", version: "0.3.1" });
  vi.mocked(getRules).mockResolvedValue({ version: "4", extra_version: null, rules: [] });
  vi.mocked(getReport).mockResolvedValue(staticPassedFixture);
});

it("keeps the new scan view when an earlier verification upload completes", async () => {
  let finishUpload!: (report: ScanReport) => void;
  vi.mocked(uploadVerification).mockImplementation(() => new Promise((resolve) => { finishUpload = resolve; }));
  const job: ScanJob = {
    id: staticPassedFixture.scan_id, repo_url: staticPassedFixture.repository.url,
    requested_ref: null, resolved_commit: staticPassedFixture.repository.commit,
    status: "completed", stage_message: "扫描完成",
    created_at: staticPassedFixture.scanned_at, updated_at: staticPassedFixture.scanned_at,
    failure_code: null, failure_message: null,
  };
  const user = userEvent.setup();
  render(<App initialJob={job} />);
  await screen.findByRole("heading", { name: "迁移报告" });
  await user.upload(screen.getByLabelText("选择验证结果 JSON"), new File(["{}"], "result.json", { type: "application/json" }));
  await user.click(screen.getByRole("button", { name: "上传验证结果" }));
  expect(uploadVerification).toHaveBeenCalledOnce();
  await user.click(screen.getByRole("button", { name: "新建体检" }));
  expect(screen.getByRole("heading", { name: "新建体检" })).toBeInTheDocument();
  await act(async () => { finishUpload({ ...staticPassedFixture, verification_status: "verified" }); });
  expect(screen.queryByRole("heading", { name: "新建体检" })).toBeInTheDocument();
  expect(new URL(window.location.href).searchParams.has("scan")).toBe(false);
});
