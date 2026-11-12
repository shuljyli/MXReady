import type { ScanReport } from "../api/types";
import { reportUrl } from "../lib/integration";
import { CodeSnippet } from "./CodeSnippet";
import { CopyButton } from "./CopyButton";
import { Icon } from "./Icon";

export function ReportExports({ report }: { report: ScanReport }) {
  const base = `/api/scans/${encodeURIComponent(report.scan_id)}`;
  const badgeUrl = new URL(base + "/badge.svg", window.location.origin).href;
  return <section className="report-section export-section">
    <div className="section-heading"><h2>导出报告</h2></div>
    <div className="download-grid">
      <a aria-label="JSON" href={base + "/report.json"}><Icon name="file" /><span>JSON</span></a>
      <a aria-label="Markdown" href={base + "/report.md"}><Icon name="file" /><span>Markdown</span></a>
      <a aria-label="HTML" href={base + "/report.html"}><Icon name="file" /><span>HTML</span></a>
      <a aria-label="SARIF" href={base + "/report.sarif"}><Icon name="file" /><span>SARIF</span></a>
      <a aria-label="Badge" href={base + "/badge.svg"}><Icon name="shield" /><span>Badge</span></a>
    </div>
    <p>绑定当前提交；项目更新后请重新扫描。HTML 报告可离线分享，浏览器打开后可直接打印为 PDF。</p>
    <details className="prose badge-tools"><summary>徽章预览与嵌入</summary>
      <img key={report.verification_status} src={base + "/badge.svg"} alt="当前报告状态徽章" />
      <CopyButton label="复制徽章地址" text={badgeUrl} />
      <CodeSnippet label="复制徽章 Markdown" text={`[![MXReady](${badgeUrl})](${reportUrl(report.scan_id)})`} />
      <p>公开 README 需要能从外部访问此地址。localhost 或内网地址不能用于公开展示。</p>
    </details>
  </section>;
}
