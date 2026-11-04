import { useEffect, useRef, useState } from "react";
import { createScan, getReport, getScan, MxReadyApiError } from "../api/client";
import type { ScanJob, ScanSummary } from "../api/types";

type Row = { key: string; repo: string; ref: string | null; id?: string; job?: ScanJob; summary?: ScanSummary; error?: string; uncertain?: boolean; pollFailures?: number };
const storageKey = "mxready-batch-v1";
function restore(): Row[] {
  try {
    const data: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? "[]");
    if (!Array.isArray(data)) return [];
    return data.slice(0, 10).filter(r => r && typeof r.key === "string" && typeof r.repo === "string" && (r.ref === null || typeof r.ref === "string") && (!r.id || typeof r.id === "string"));
  } catch { return []; }
}
export function BatchScans({ onOpen }: { onOpen: (id: string) => void }) {
  const [input, setInput] = useState("");
  const [rows, setRows] = useState<Row[]>(restore);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const current = useRef(rows); current.current = rows;
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { try { sessionStorage.setItem(storageKey, JSON.stringify(rows)); } catch { /* storage can be unavailable */ } }, [rows]);
  const update = (key: string, patch: Partial<Row>) => setRows(old => old.map(r => r.key === key ? { ...r, ...patch } : r));
  useEffect(() => {
    const controller = new AbortController();
    let polling = false;
    async function poll() {
      if (polling) return; polling = true;
      try {
        for (const row of current.current) {
          if (controller.signal.aborted) return;
          if ((row.pollFailures ?? 0) >= 3 || !row.id || row.summary || row.job?.status === "failed") continue;
          try {
            const job = await getScan(row.id, controller.signal);
            let summary: ScanSummary | undefined;
            if (job.status === "completed") summary = (await getReport(row.id, controller.signal)).summary;
            if (!controller.signal.aborted) update(row.key, { job, summary, error: undefined, pollFailures: 0 });
          } catch (err) { if (!controller.signal.aborted) update(row.key, { error: String(err), pollFailures: (row.pollFailures ?? 0) + 1 }); }
        }
      } finally { polling = false; }
    }
    void poll(); const timer = setInterval(() => void poll(), 5000);
    return () => { controller.abort(); clearInterval(timer); };
  }, []);
  async function submit(targets: Row[]) {
    setBusy(true);
    for (const row of targets) {
      if (!mounted.current) break;
      // Save uncertainty before POST: refreshing mid-request must not silently resubmit.
      setRows(old => old.map(r => r.key === row.key ? { ...r, uncertain: true, error: "提交中；若刷新后无任务 ID，请先在扫描历史核对。" } : r));
      try { sessionStorage.setItem(storageKey, JSON.stringify(current.current.map(r => r.key === row.key ? { ...r, uncertain: true } : r))); } catch { /* optional persistence */ }
      try {
        const job = await createScan({ repo_url: row.repo, ref: row.ref });
        if (mounted.current) update(row.key, { id: job.id, job, summary: undefined, error: undefined, uncertain: false, pollFailures: 0 });
      } catch (err) {
        const uncertain = !(err instanceof MxReadyApiError) || !err.status || err.status >= 500;
        if (mounted.current) update(row.key, { error: String(err), uncertain });
      }
    }
    if (mounted.current) setBusy(false);
  }
  function start() {
    const lines = input.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    if (!lines.length || lines.length > 10) { setError("每批请输入 1–10 个仓库。"); return; }
    const next: Row[] = [];
    for (const line of lines) {
      const parts = line.split(/\s+/);
      if (parts.length > 2 || !/^https:\/\/(github\.com|gitee\.com)\/[^/\s]+\/[^/\s]+\/?$/.test(parts[0])) { setError("每行填写公开 GitHub/Gitee 仓库 URL，可在空格后填写 ref。"); return; }
      if (next.some(r => r.repo === parts[0] && r.ref === (parts[1] ?? null))) continue;
      next.push({ key: crypto.randomUUID(), repo: parts[0], ref: parts[1] ?? null });
    }
    setError(""); current.current = next; setRows(next); void submit(next);
  }
  function download() {
    const blob = new Blob([JSON.stringify(rows.map(r => ({ repository: r.repo, ref: r.ref, scan_id: r.id, status: r.job?.status ?? "not-submitted", summary: r.summary, error: r.error })), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "mxready-batch-summary.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const active = rows.some(r => r.id && r.job?.status !== "completed" && r.job?.status !== "failed");
  return <section className="report-section batch-scans"><h1>批量扫描</h1>
    <p>每行一个公开仓库 URL，可附加分支、标签或提交；每批最多 10 项。任务使用服务现有队列与并发限制，刷新后可继续查看当前标签页记录。</p>
    <label className="field">批量仓库列表<textarea rows={6} value={input} onChange={e => setInput(e.target.value)} disabled={busy} /></label>
    <button type="button" className="primary-button" disabled={busy || active} onClick={start}>提交批量扫描</button>
    {error ? <p role="alert">{error}</p> : null}
    {rows.length ? <><button type="button" className="secondary-button" onClick={download}>下载批量汇总 JSON</button>
      <p>完成 {rows.filter(r => r.job?.status === "completed").length} / {rows.length}。失败重试创建新扫描，旧任务仍保留在扫描历史中。</p>
      <ul>{rows.map(row => <li key={row.key}><strong>{row.repo}</strong><p>{row.ref ?? "默认分支"} · {row.job?.stage_message ?? "未取得任务 ID"}</p>
        {row.summary ? <p>阻塞 {row.summary.blocker_count} · 警告 {row.summary.warning_count} · 提示 {row.summary.info_count}</p> : null}
        {row.error ? <p role="status">{row.error}</p> : null}
        {row.job?.failure_message ? <p>{row.job.failure_message}</p> : null}
        {row.id ? <button type="button" onClick={() => onOpen(row.id!)}>打开任务 {row.id}</button> : null}
        {(row.pollFailures ?? 0) >= 3 ? <button type="button" onClick={() => update(row.key, { pollFailures: 0, error: undefined })}>恢复任务状态查询</button> : null}
        {row.uncertain ? <p>提交状态不确定，请先在扫描历史核对。不会自动重复提交。</p> : (!row.id || row.job?.status === "failed") ? <button type="button" disabled={busy} onClick={() => void submit([row])}>为 {row.repo} 新建重试</button> : null}
      </li>)}</ul></> : null}
  </section>;
}
