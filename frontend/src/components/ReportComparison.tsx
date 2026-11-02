import { useEffect, useRef, useState } from "react";
import { getReport } from "../api/client";
import type { ScanReport } from "../api/types";
import { compareReports } from "../lib/comparison";
import { Pagination } from "./Pagination";

export function ReportComparison({ report }: { report: ScanReport }) {
  const [id, setId] = useState("");
  const [baseline, setBaseline] = useState<ScanReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [group, setGroup] = useState<"added" | "removed" | "retained">("added");
  const [offset, setOffset] = useState(0);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), [report.scan_id]);
  const comparison = baseline ? compareReports(baseline, report) : null;
  async function compare() {
    active.current?.abort(); setBaseline(null); setError(""); setOffset(0);
    if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id.trim())) { setError("请输入完整的扫描 UUID。"); return; }
    const controller = new AbortController(); active.current = controller; setBusy(true);
    try {
      const value = await getReport(id.trim(), controller.signal);
      compareReports(value, report);
      if (!controller.signal.aborted) setBaseline(value);
    } catch (err) { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "无法对比报告"); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <details className="report-section report-comparison"><summary>对比另一份报告</summary>
    <form onSubmit={(event) => { event.preventDefault(); void compare(); }} className="comparison-form">
      <label className="field">基线扫描 ID<input value={id} onChange={(event) => setId(event.target.value)} /></label>
      <button className="secondary-button compact-button" type="submit" disabled={busy}>{busy ? "正在对比…" : "开始对比"}</button>
    </form><p className="muted">从扫描历史复制同一仓库的扫描 ID。按规则、文件和证据匹配；行号移动不算新问题，消失项仍需人工确认。</p>
    {error ? <p role="alert">{error}</p> : null}
    {comparison && baseline ? <>
      <p>基线 {baseline.repository.commit.slice(0, 12)} → 当前 {report.repository.commit.slice(0, 12)}</p>
      <p>基线规则 v{baseline.ruleset_version} / 工具 v{baseline.tool_version} → 当前规则 v{report.ruleset_version} / 工具 v{report.tool_version}</p>
      {comparison.conditionsChanged ? <p role="status">规则、工具或分析配置已变化；差异可能来自分析条件变化，不能全部视为代码整改效果。</p> : null}
      {!baseline.ruleset_digest || !report.ruleset_digest ? <p>旧报告缺少规则摘要，无法确认规则内容完全相同。</p> : null}
      <p role="status">新增 {comparison.added.length} · 消失 {comparison.removed.length} · 保留 {comparison.retained.length}</p>
      <label className="field">差异类别<select value={group} onChange={(event) => { setGroup(event.target.value as typeof group); setOffset(0); }}>
        <option value="added">新增</option><option value="removed">消失</option><option value="retained">保留</option>
      </select></label>
      <ul>{comparison[group].slice(offset, offset + 50).map((finding, index) => <li key={index}>
        <code>{finding.rule_id} · {finding.relative_path}:{finding.line_start}</code><p>{finding.title} · {finding.severity} · {finding.count} 次</p>
      </li>)}</ul>
      <Pagination label="对比" offset={offset} limit={50} total={comparison[group].length} onChange={setOffset} />
    </> : null}
  </details>;
}
