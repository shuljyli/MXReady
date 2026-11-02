import { useEffect, useState } from "react";
import { getVerification, listVerifications } from "../api/client";
import type { ScanReport, VerificationDetail, VerificationPage } from "../api/types";
import { Pagination } from "./Pagination";

const states: Record<string, string> = { verified: "环境已验证", failed: "验证失败", stale: "已过期", "not-run": "未运行" };

export function VerificationHistory({ report }: { report: ScanReport }) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState<VerificationPage | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController(); setPage(null); setError(""); setSelected(null); setDetail(null);
    listVerifications(report.scan_id, offset, controller.signal).then((value) => { if (!controller.signal.aborted) setPage(value); })
      .catch((err) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "读取验证记录失败"); });
    return () => controller.abort();
  }, [open, offset, attempt, report]);
  useEffect(() => {
    if (selected === null || !open) return;
    const controller = new AbortController(); setDetail(null); setDetailError("");
    getVerification(report.scan_id, selected, controller.signal).then((value) => { if (!controller.signal.aborted) setDetail(value); })
      .catch((err) => { if (!controller.signal.aborted) setDetailError(err instanceof Error ? err.message : "读取详情失败"); });
    return () => controller.abort();
  }, [selected, report.scan_id, open, attempt]);
  return <details className="report-section verification-history" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>验证详情与历史</summary>
    {open ? <>
      <p>按上传顺序保存。当前报告采用最后上传的一次结果；环境验证与项目命令分别展示。旧版本仅能保留升级时已有的最后一次记录。</p>
      <button type="button" className="text-button" onClick={() => setAttempt((n) => n + 1)}>刷新验证记录</button>
      {error ? <p role="alert">{error}</p> : !page ? <p role="status">正在读取验证记录…</p> : <>
        {!page.total ? <p>还没有上传验证结果。</p> : <ul className="verification-records">{page.items.map((item) => <li key={item.id}>
          <button className="text-button" type="button" aria-pressed={item.id === selected} onClick={() => setSelected(item.id)}>
            {new Date(item.finished_at).toLocaleString("zh-CN")} · {states[item.status]}{item.is_latest ? " · 当前采用" : ""}
          </button><small>环境检查 {item.check_count} 项 · 项目命令 {item.command_count} 项</small>
        </li>)}</ul>}
        <Pagination label="验证记录" {...page} onChange={setOffset} />
      </>}
      {detailError ? <p role="alert">{detailError}</p> : null}
      {selected && !detail && !detailError ? <p role="status">正在读取验证详情…</p> : null}
      {detail ? <section aria-label="验证记录详情">
        <dl className="metadata-list"><div><dt>执行开始</dt><dd>{new Date(detail.summary.started_at).toLocaleString("zh-CN")}</dd></div>
          <div><dt>有效期截止</dt><dd>{new Date(detail.summary.expires_at).toLocaleString("zh-CN")}</dd></div>
          <div><dt>上传时间</dt><dd>{detail.summary.uploaded_at ? new Date(detail.summary.uploaded_at).toLocaleString("zh-CN") : "旧记录，上传时间未知"}</dd></div>
          <div><dt>提交</dt><dd><code>{detail.summary.repository_commit}</code></dd></div>
          <div><dt>环境指纹</dt><dd><code>{detail.summary.environment_fingerprint}</code></dd></div>
          <div><dt>Runner</dt><dd>{detail.summary.runner_version}</dd></div></dl>
        {([ ["环境检查", detail.checks], ["项目命令", detail.commands] ] as const).map(([title, entries]) => <div key={title}>
          <h3>{title}</h3>{!entries.length ? <p>未执行项目命令，不能据此认定项目功能或性能已通过。</p> : entries.map((entry) => <details key={entry.id}>
            <summary>{entry.id} · {entry.status} · {entry.duration_ms}ms</summary>
            <p>退出码：{entry.return_code ?? "无"}</p><pre>{entry.stdout || "无标准输出"}</pre><pre>{entry.stderr || "无错误输出"}</pre>
          </details>)}</div>)}
        <p className="muted">日志已再次自动脱敏并限制长度；命令参数不在此公开，上传前仍须人工审阅。</p>
      </section> : null}
    </> : null}
  </details>;
}
