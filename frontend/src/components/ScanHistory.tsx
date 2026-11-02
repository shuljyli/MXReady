import { useEffect, useState } from "react";
import { listScans } from "../api/client";
import type { ScanPage } from "../api/types";
import { PageHeading } from "./PageHeading";
import { Pagination } from "./Pagination";

const statuses: Record<string, string> = { queued: "排队中", cloning: "获取仓库", indexing: "建立索引", analyzing: "分析中", completed: "已完成", failed: "失败" };

export function ScanHistory({ onOpen }: { onOpen: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState({ q: "", status: "", offset: 0 });
  const [page, setPage] = useState<ScanPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    listScans(query, controller.signal).then((value) => {
      if (!controller.signal.aborted) setPage(value);
    }).catch((err) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "读取历史失败"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query]);
  return <div className="feature-page">
    <PageHeading title="扫描历史" description="查看当前服务保存的任务与报告。共享此服务的用户可看到同一份历史。" />
    <form className="filter-grid" onSubmit={(event) => { event.preventDefault(); setQuery({ q, status, offset: 0 }); }}>
      <label className="field">搜索仓库<input type="search" value={q} maxLength={200} onChange={(event) => setQ(event.target.value)} /></label>
      <label className="field">任务状态<select value={status} onChange={(event) => setStatus(event.target.value)}>
        <option value="">全部状态</option>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <button type="submit" className="secondary-button">查询历史</button>
    </form>
    {loading ? <p role="status">正在读取扫描历史…</p> : error ? <div role="alert"><p>{error}</p><button type="button" onClick={() => setQuery({ ...query })}>重试历史</button></div> : page ? <>
      <div className="history-list">{page.items.map((job) => <article className="history-item" key={job.id}>
        <div><strong>{job.repo_url}</strong><p>{statuses[job.status]} · {new Date(job.created_at).toLocaleString("zh-CN")}</p>
          <small>{job.resolved_commit?.slice(0, 12) ?? job.requested_ref ?? "默认分支"} · {job.id}</small>
          {job.failure_code ? <p>{job.failure_code} · {job.failure_message}</p> : null}</div>
        <button type="button" className="secondary-button compact-button" aria-label={"打开扫描 " + job.id} onClick={() => onOpen(job.id)}>打开扫描</button>
      </article>)}</div>
      {!page.total ? <p>没有符合条件的扫描。可以新建体检或调整筛选。</p> : null}
      <Pagination label="历史" {...page} onChange={(offset) => setQuery({ ...query, offset })} />
    </> : null}
  </div>;
}
