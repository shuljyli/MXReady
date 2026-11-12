import { useEffect, useState } from "react";
import { getDashboard } from "../api/client";
import type { ProgressPage, ProgressTrendPoint } from "../api/types";
import { PageHeading } from "./PageHeading";
import { Pagination } from "./Pagination";

const statuses: Record<string, string> = { queued: "排队中", cloning: "获取仓库", indexing: "建立索引", analyzing: "分析中", completed: "已完成", failed: "失败" };

function TrendSparkline({ trend }: { trend: ProgressTrendPoint[] }) {
  if (!trend.length) return <small>暂无已完成扫描的趋势数据</small>;
  const counts = trend.map((point) => point.blocker_count);
  const max = Math.max(...counts, 1);
  const barWidth = 8;
  const gap = 3;
  return <svg role="img" width={trend.length * (barWidth + gap)} height={32} aria-label={"阻塞项趋势：" + counts.join("、")}>
    {trend.map((point, index) => {
      const height = Math.max((point.blocker_count / max) * 26, point.blocker_count > 0 ? 2 : 1);
      return <rect key={point.scan_id} x={index * (barWidth + gap)} y={28 - height} width={barWidth} height={height} fill="#c81e1e" />;
    })}
  </svg>;
}

export function MigrationDashboard({ onOpen }: { onOpen: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState({ q: "", offset: 0 });
  const [page, setPage] = useState<ProgressPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    getDashboard(query, controller.signal).then((value) => {
      if (!controller.signal.aborted) setPage(value);
    }).catch((err) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "读取迁移进度失败"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query]);
  return <div className="feature-page">
    <PageHeading title="迁移进度" description="按仓库聚合扫描次数与阻塞项趋势，仅展示数量变化，不代表兼容率。" />
    <form className="filter-grid" onSubmit={(event) => { event.preventDefault(); setQuery({ q, offset: 0 }); }}>
      <label className="field">搜索仓库<input type="search" value={q} maxLength={200} onChange={(event) => setQ(event.target.value)} /></label>
      <button type="submit" className="secondary-button">查询进度</button>
    </form>
    {loading ? <p role="status">正在读取迁移进度…</p> : error ? <div role="alert"><p>{error}</p><button type="button" onClick={() => setQuery({ ...query })}>重试进度</button></div> : page ? <>
      <div className="history-list">{page.items.map((item) => <article className="history-item" key={item.repo_url}>
        <div><strong>{item.repo_url}</strong>
          <p>{statuses[item.latest_status] ?? item.latest_status} · 共 {item.scan_count} 次扫描 · 最近 {new Date(item.latest_created_at).toLocaleString("zh-CN")}</p>
          <TrendSparkline trend={item.blocker_trend} />
        </div>
        <button type="button" className="secondary-button compact-button" aria-label={"打开仓库最新扫描 " + item.latest_scan_id} onClick={() => onOpen(item.latest_scan_id)}>打开最新扫描</button>
      </article>)}</div>
      {!page.total ? <p>没有符合条件的仓库。可以新建体检或调整搜索。</p> : null}
      <Pagination label="迁移进度" {...page} onChange={(offset) => setQuery({ ...query, offset })} />
    </> : null}
  </div>;
}
