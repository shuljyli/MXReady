import type { Finding, ScanReport } from "../api/types";

function key(finding: Finding) {
  return JSON.stringify([finding.rule_id, finding.relative_path, finding.evidence.trim()]);
}

export function compareReports(baseline: ScanReport, current: ScanReport) {
  const normalize = (url: string) => url.replace(/\.git\/?$/, "").replace(/\/$/, "").toLowerCase();
  if (normalize(baseline.repository.url) !== normalize(current.repository.url)) {
    throw new Error("只能对比同一仓库的报告。");
  }
  const before = new Map(baseline.findings.map((finding) => [key(finding), finding]));
  const after = new Map(current.findings.map((finding) => [key(finding), finding]));
  return {
    added: current.findings.filter((finding) => !before.has(key(finding))),
    removed: baseline.findings.filter((finding) => !after.has(key(finding))),
    retained: current.findings.filter((finding) => before.has(key(finding))),
    conditionsChanged: baseline.ruleset_digest !== current.ruleset_digest
      || baseline.ruleset_version !== current.ruleset_version
      || baseline.extra_ruleset_version !== current.extra_ruleset_version
      || baseline.tool_version !== current.tool_version
      || JSON.stringify(Object.entries(baseline.analysis_config).sort()) !== JSON.stringify(Object.entries(current.analysis_config).sort()),
  };
}
