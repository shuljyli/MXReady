import type { ScanReport } from "../api/types";
import { CopyButton } from "./CopyButton";

export function ReportDetails({ report }: { report: ScanReport }) {
  return <details className="report-section report-details"><summary>报告详情</summary>
    <dl className="detail-list">
      <div><dt>扫描 ID</dt><dd><code>{report.scan_id}</code><CopyButton label="复制扫描 ID" text={report.scan_id} /></dd></div>
      <div><dt>报告格式版本</dt><dd>{report.schema_version}</dd></div>
      <div><dt>完整提交</dt><dd><code>{report.repository.commit}</code><CopyButton label="复制完整提交" text={report.repository.commit} /></dd></div>
      <div><dt>规则集摘要</dt><dd><code>{report.ruleset_digest ?? "未记录"}</code>{report.ruleset_digest
        ? <CopyButton label="复制规则集摘要" text={report.ruleset_digest} /> : null}</dd></div>
      <div><dt>扩展规则版本</dt><dd>{report.extra_ruleset_version ?? "无扩展规则版本记录"}</dd></div>
      <div><dt>分析配置</dt><dd>{Object.keys(report.analysis_config).length
        ? <pre className="technical-output"><code>{JSON.stringify(report.analysis_config, null, 2)}</code></pre>
        : "未记录分析配置"}</dd></div>
    </dl>
    {report.analysis_config.prefilter ? <p className="muted">预过滤状态：on 为启用，off 为配置关闭，unavailable 为不可用而退回完整匹配；这是分析时的实际状态。</p> : null}
  </details>;
}
