import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { ReportSkeleton } from "./ReportSkeleton";

it("exposes a busy placeholder region for screen readers", () => {
  render(<ReportSkeleton />);

  const skeleton = screen.getByLabelText("报告加载中");
  expect(skeleton).toHaveAttribute("aria-busy", "true");
});

it("renders three placeholder finding cards", () => {
  const { container } = render(<ReportSkeleton />);

  expect(container.querySelectorAll(".skeleton-card")).toHaveLength(3);
  expect(container.querySelector(".report-skeleton")).not.toBeNull();
});
