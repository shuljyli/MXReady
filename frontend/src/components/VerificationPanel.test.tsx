import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { uploadVerification } from "../api/client";
import { staticPassedFixture } from "../test/fixtures";
import { VerificationPanel } from "./VerificationPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, uploadVerification: vi.fn() };
});

it("explains that static pass is not hardware verification", () => {
  render(
    <VerificationPanel
      report={staticPassedFixture}
      onUpdated={vi.fn()}
    />,
  );

  expect(screen.getByText(/尚未在沐曦 GPU 上验证/)).toBeInTheDocument();
  expect(screen.getByText(/静态检查只会发现已编码的迁移风险/)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "下载远程验证包" }),
  ).toHaveAttribute(
    "href",
    `/api/scans/${staticPassedFixture.scan_id}/verification-bundle`,
  );
});

it("rejects verification files larger than one MiB before upload", async () => {
  render(
    <VerificationPanel
      report={staticPassedFixture}
      onUpdated={vi.fn()}
    />,
  );
  const largeFile = new File(
    [new Uint8Array(1_048_577)],
    "verification-result.json",
    { type: "application/json" },
  );

  await userEvent.upload(
    screen.getByLabelText("选择验证结果 JSON"),
    largeFile,
  );
  await userEvent.click(screen.getByRole("button", { name: "上传验证结果" }));

  expect(screen.getByRole("alert")).toHaveTextContent("不能超过 1 MiB");
  expect(uploadVerification).not.toHaveBeenCalled();
});

it("uploads one JSON result and returns the updated report", async () => {
  const verified = {
    ...staticPassedFixture,
    verification_status: "verified" as const,
  };
  vi.mocked(uploadVerification).mockResolvedValue(verified);
  const onUpdated = vi.fn();
  render(
    <VerificationPanel
      report={staticPassedFixture}
      onUpdated={onUpdated}
    />,
  );
  const file = new File(["{}"], "verification-result.json", {
    type: "application/json",
  });

  await userEvent.upload(
    screen.getByLabelText("选择验证结果 JSON"),
    file,
  );
  await userEvent.click(screen.getByRole("button", { name: "上传验证结果" }));

  expect(uploadVerification).toHaveBeenCalledWith(
    staticPassedFixture.scan_id,
    file,
  );
  expect(onUpdated).toHaveBeenCalledWith(verified);
});
