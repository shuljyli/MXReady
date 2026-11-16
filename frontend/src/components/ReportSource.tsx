import { useId } from "react";

import type { ScanReport } from "../api/types";
import { describeSource } from "../lib/source";
import { CopyButton } from "./CopyButton";

export function ReportSource({ report }: { report: ScanReport }) {
  const headingId = useId();
  const view = describeSource(report);
  const source = report.source;
  const fields = [
    ["报告关联/声明的提交", report.repository.commit],
    ["探测到的 HEAD", source?.actual_commit],
    ["已索引文件集合摘要", source?.input_digest],
  ];
  return <section aria-labelledby={headingId}>
    <h3 id={headingId}>扫描来源</h3>
    <p><strong>{view.label}</strong></p>
    <p className="muted">{view.explanation}</p>
    {view.warnings.map(warning => <p className="muted" key={warning}>{warning}</p>)}
    <dl className="detail-list">
      {fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>
        <code>{value || "未记录"}</code>
        {value ? <CopyButton label={`复制${label}`} text={value} /> : null}
      </dd></div>)}
      <div><dt>工作区状态</dt><dd>{source?.dirty == null ? "未知" : source.dirty ? "有修改" : "无修改"}</dd></div>
    </dl>
  </section>;
}
