import type { ScanReport } from "../api/types";

export function reportUrl(scanId: string) {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("scan", scanId);
  return url.href;
}

export function toolExample(tool: string, args: Record<string, unknown>) {
  return JSON.stringify({ tool, arguments: args }, null, 2);
}

export function agentHandoff(report: ScanReport) {
  return [
    "请根据 MXReady 的静态证据分析迁移风险，静态结果不代表真机认证。",
    `仓库：${report.repository.url}`,
    `完整提交：${report.repository.commit}`,
    `扫描 ID：${report.scan_id}`,
    `报告：${reportUrl(report.scan_id)}`,
    `工具版本：${report.tool_version}；报告规则集版本：${report.ruleset_version}`,
    "Web 与 MCP 使用同一本地数据目录时，可按以下工具名和参数读取报告（非协议报文）：",
    toolExample("get_report", { scan_id: report.scan_id, max_findings: 50 }),
    "检查 findings_truncated、returned_findings 和 total_findings，默认返回可能不完整。",
    "若 MCP 与 Web 不共享数据库，请固定到上述完整提交重新扫描：",
    toolExample("scan_repository", {
      repo_url: report.repository.url, ref: report.repository.commit,
      timeout_seconds: 300, max_findings: 20,
    }),
  ].join("\n\n");
}

export function referenceUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : undefined;
  } catch {
    return undefined;
  }
}
