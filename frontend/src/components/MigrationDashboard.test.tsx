import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { getDashboard } from "../api/client";
import type { ProgressPage, RepositoryProgress } from "../api/types";
import { MigrationDashboard } from "./MigrationDashboard";

vi.mock("../api/client", async (original) => ({
  ...await original<typeof import("../api/client")>(),
  getDashboard: vi.fn(),
}));

beforeEach(() => {
  vi.resetAllMocks();
});

const alpha: RepositoryProgress = {
  repo_url: "https://github.com/example/alpha",
  scan_count: 2,
  latest_scan_id: "00000000-0000-0000-0000-000000000002",
  latest_status: "completed",
  latest_created_at: "2026-02-01T00:00:00Z",
  blocker_trend: [
    { scan_id: "00000000-0000-0000-0000-000000000001", scanned_at: "2026-01-01T00:00:00Z", blocker_count: 1 },
    { scan_id: "00000000-0000-0000-0000-000000000002", scanned_at: "2026-02-01T00:00:00Z", blocker_count: 3 },
  ],
};

const page = (items: RepositoryProgress[], total = items.length): ProgressPage => ({
  items,
  total,
  limit: 20,
  offset: 0,
});

it("renders repository progress with an accessible trend and opens the latest scan", async () => {
  vi.mocked(getDashboard).mockResolvedValue(page([alpha]));
  const onOpen = vi.fn();

  render(<MigrationDashboard onOpen={onOpen} />);

  expect(await screen.findByText("https://github.com/example/alpha")).toBeInTheDocument();
  expect(screen.getByText(/已完成 · 共 2 次扫描/)).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "阻塞项趋势：1、3" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /打开仓库最新扫描/ }));
  expect(onOpen).toHaveBeenCalledWith("00000000-0000-0000-0000-000000000002");
});

it("shows an empty hint when no repositories match", async () => {
  vi.mocked(getDashboard).mockResolvedValue(page([]));

  render(<MigrationDashboard onOpen={vi.fn()} />);

  expect(await screen.findByText(/没有符合条件的仓库/)).toBeInTheDocument();
});

it("shows an error and retries loading progress", async () => {
  vi.mocked(getDashboard)
    .mockRejectedValueOnce(new Error("网络错误"))
    .mockResolvedValue(page([]));

  render(<MigrationDashboard onOpen={vi.fn()} />);

  expect(await screen.findByRole("alert")).toHaveTextContent("网络错误");
  await userEvent.click(screen.getByRole("button", { name: "重试进度" }));
  await waitFor(() => expect(getDashboard).toHaveBeenCalledTimes(2));
});

it("submits a repository search and refetches with the query", async () => {
  vi.mocked(getDashboard).mockResolvedValue(page([]));

  render(<MigrationDashboard onOpen={vi.fn()} />);

  await screen.findByText(/没有符合条件的仓库/);
  await userEvent.type(screen.getByLabelText("搜索仓库"), "alpha");
  await userEvent.click(screen.getByRole("button", { name: "查询进度" }));
  await waitFor(() =>
    expect(getDashboard).toHaveBeenLastCalledWith({ q: "alpha", offset: 0 }, expect.any(AbortSignal)),
  );
});
