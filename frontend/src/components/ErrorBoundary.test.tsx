import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";

function Exploding(): never {
  throw new Error("boom");
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders a scoped fallback when a child throws", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);

  render(
    <ErrorBoundary label="报告内容">
      <Exploding />
    </ErrorBoundary>,
  );

  expect(screen.getByRole("alert")).toBeInTheDocument();
  expect(screen.getByText(/报告内容渲染出错/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
});

it("passes healthy children through unchanged", () => {
  render(
    <ErrorBoundary label="报告内容">
      <p>正常内容</p>
    </ErrorBoundary>,
  );

  expect(screen.getByText("正常内容")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
