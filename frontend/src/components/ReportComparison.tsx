import { useEffect, useId, useRef, useState } from "react";
import { getReport, listScans } from "../api/client";
import type { ScanJob, ScanReport } from "../api/types";
import { compareReports } from "../lib/comparison";
import { Pagination } from "./Pagination";

export function ReportComparison({ report }: { report: ScanReport }) {
  const [id, setId] = useState("");
  const [baseline, setBaseline] = useState<ScanReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [opened, setOpened] = useState(false);
  const [candidates, setCandidates] = useState<ScanJob[]>([]);
  const [candidatesUnavailable, setCandidatesUnavailable] = useState(false);
  const [group, setGroup] = useState<"added" | "removed" | "retained" | "severityChanged" | "countChanged">("added");
  const [offset, setOffset] = useState(0);
  const active = useRef<AbortController | null>(null);
  const candidatesId = useId();
  useEffect(() => () => active.current?.abort(), [report.scan_id]);
  // 只在面板展开后取候选，避免每次打开报告都多一次历史查询；历史不可用时仍可手工粘贴 ID。
  useEffect(() => {
    if (!opened) return;
    const controller = new AbortController();
    setCandidatesUnavailable(false);
    listScans({ q: report.repository.url, status: "completed", offset: 0 }, controller.signal).then((page) => {
      if (controller.signal.aborted) return;
      setCandidates(page.items.filter((job) => job.id !== report.scan_id));
    }).catch(() => {
      if (controller.signal.aborted) return;
      setCandidates([]); setCandidatesUnavailable(true);
    });
    return () => controller.abort();
  }, [opened, report.repository.url, report.scan_id]);
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
  return <details className="report-section report-comparison" onToggle={(event) => setOpened(event.currentTarget.open)}><summary>对比另一份报告</summary>
    <form onSubmit={(event) => { event.preventDefault(); void compare(); }} className="comparison-form">
      <label className="field">基线扫描 ID<input list={candidatesId} value={id} onChange={(event) => setId(event.target.value)} /></label>
      <datalist id={candidatesId}>{candidates.map((job) => <option key={job.id} value={job.id}>
        {`${job.resolved_commit?.slice(0, 12) ?? job.requested_ref ?? "默认分支"} · ${new Date(job.created_at).toLocaleString("zh-CN")}`}
      </option>)}</datalist>
      <button className="secondary-button compact-button" type="submit" disabled={busy}>{busy ? "正在对比…" : "开始对比"}</button>
    </form>
    {candidatesUnavailable ? <p className="muted">未能读取扫描历史，仍可直接粘贴基线扫描 ID。</p> : null}
    <p className="muted">候选列表来自同一仓库的已完成扫描，也可直接粘贴扫描历史中的扫描 ID。按规则和文件匹配；行号移动不算新问题，严重级别与命中次数单独比较，消失项仍需人工确认。</p>
    {error ? <p role="alert">{error}</p> : null}
    {comparison && baseline ? <>
      <p>基线 {baseline.repository.commit.slice(0, 12)} → 当前 {report.repository.commit.slice(0, 12)}</p>
      <p>基线规则 v{baseline.ruleset_version} / 工具 v{baseline.tool_version} → 当前规则 v{report.ruleset_version} / 工具 v{report.tool_version}</p>
      {comparison.conditionsChanged ? <p role="status">规则、工具或分析配置已变化；差异可能来自分析条件变化，不能全部视为代码整改效果。</p> : null}
      {!baseline.ruleset_digest || !report.ruleset_digest ? <p>旧报告缺少规则摘要，无法确认规则内容完全相同。</p> : null}
      <p role="status">新增 {comparison.added.length} · 消失 {comparison.removed.length} · 保留 {comparison.retained.length} · 级别变化 {comparison.severityChanged.length} · 次数变化 {comparison.countChanged.length}</p>
      <label className="field">差异类别<select value={group} onChange={(event) => { setGroup(event.target.value as typeof group); setOffset(0); }}>
        <option value="added">新增</option><option value="removed">消失</option><option value="retained">保留</option><option value="severityChanged">级别变化</option><option value="countChanged">次数变化</option>
      </select></label>
      <ul>{comparison[group].slice(offset, offset + 50).map((finding, index) => <li key={index}>
        <code>{finding.rule_id} · {finding.relative_path}:{finding.line_start}</code><p>{finding.title} · {finding.severity} · {finding.count} 次</p>
        {comparison.changes.filter(c => c.after === finding).map(c => <p key="change">{c.before.severity} → {c.after.severity}；{c.before.count} → {c.after.count} 次</p>)}
      </li>)}</ul>
      <Pagination label="对比" offset={offset} limit={50} total={comparison[group].length} onChange={setOffset} />
    </> : null}
  </details>;
}
