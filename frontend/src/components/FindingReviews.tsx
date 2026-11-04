import { useEffect, useState } from "react";
import { getReviews, saveReview } from "../api/client";
import type { FindingReviewPage, ScanReport } from "../api/types";
import { Pagination } from "./Pagination";

const labels = { confirmed: "已确认", "false-positive": "误报", deferred: "暂缓" };
export function FindingReviews({ report }: { report: ScanReport }) {
  const [opened, setOpened] = useState(false);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState<keyof typeof labels>("confirmed");
  const [reason, setReason] = useState("");
  const [history, setHistory] = useState<FindingReviewPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const finding = report.findings[index];
  useEffect(() => {
    if (!opened || !finding) return;
    const controller = new AbortController();
    setHistory(null); setError("");
    getReviews(report.scan_id, finding.rule_id, finding.relative_path, offset, controller.signal)
      .then(value => { if (!controller.signal.aborted) setHistory(value); })
      .catch(err => { if (!controller.signal.aborted) setError(String(err)); });
    return () => controller.abort();
  }, [opened, finding, report.scan_id, offset, attempt]);
  async function submit() {
    if (!finding || !reason.trim()) return;
    setBusy(true); setError("");
    try {
      await saveReview(report.scan_id, { rule_id: finding.rule_id, relative_path: finding.relative_path, status, reason: reason.trim() });
      setReason(""); setOffset(0); setAttempt(v => v + 1);
    } catch (err) { setError(String(err)); }
    finally { setBusy(false); }
  }
  if (!finding) return null;
  return <details className="report-section finding-reviews" onToggle={event => setOpened(event.currentTarget.open)}>
    <summary>人工复核与误报反馈</summary>
    <p>记录当前提交上的判断，不隐藏发现，也不改变静态或硬件结论。本服务实例共享这些记录，暂无个人身份认证。</p>
    <label className="field">复核发现<select value={index} disabled={busy} onChange={e => { setIndex(Number(e.target.value)); setOffset(0); setReason(""); }}>
      {report.findings.map((f, i) => <option key={i} value={i}>{f.rule_id} · {f.relative_path}</option>)}
    </select></label>
    <form onSubmit={e => { e.preventDefault(); void submit(); }}>
      <label className="field">复核结论<select value={status} disabled={busy} onChange={e => setStatus(e.target.value as keyof typeof labels)}>
        {Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label className="field">判断依据<textarea value={reason} required maxLength={1000} disabled={busy} onChange={e => setReason(e.target.value)} /></label>
      <button className="secondary-button" disabled={busy || !reason.trim()} type="submit">{busy ? "保存中…" : "保存复核记录"}</button>
    </form>
    {error ? <p role="alert">{error} <button type="button" onClick={() => setAttempt(v => v + 1)}>重新读取记录</button></p> : null}
    {history ? <><p>记录共 {history.total} 条，最新记录在前。提交超时后请先重新读取，避免重复提交。</p>
      <ul>{history.items.map(r => <li key={r.id}>{labels[r.status]} · {new Date(r.created_at).toLocaleString()}<p>{r.reason}</p></li>)}</ul>
      <Pagination label="复核记录" offset={offset} limit={history.limit} total={history.total} onChange={setOffset} />
    </> : opened ? <p>正在读取记录…</p> : null}
  </details>;
}
