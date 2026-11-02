import { expect, it } from "vitest";
import { blockedReportFixture } from "../test/fixtures";
import { compareReports } from "./comparison";

it("keeps relocated evidence and flags changed analysis conditions", () => {
  const shifted = { ...blockedReportFixture, ruleset_version: "new", findings:
    blockedReportFixture.findings.map((finding) => ({ ...finding, line_start: finding.line_start + 10, line_end: finding.line_end + 10 })) };
  const result = compareReports(blockedReportFixture, shifted);
  expect(result.added).toHaveLength(0);
  expect(result.removed).toHaveLength(0);
  expect(result.retained).toHaveLength(2);
  expect(result.conditionsChanged).toBe(true);
});

it("compares configuration values independently of object key insertion order", () => {
  const before = { ...blockedReportFixture, analysis_config: { a: 1, b: 2 } };
  const after = { ...blockedReportFixture, analysis_config: { b: 2, a: 1 } };
  expect(compareReports(before, after).conditionsChanged).toBe(false);
});
