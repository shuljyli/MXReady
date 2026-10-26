import { useEffect, useState } from "react";

import { getRules } from "./api/client";
import type { ScanJob } from "./api/types";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Icon } from "./components/Icon";
import { ReportSkeleton } from "./components/ReportSkeleton";
import { ReportView } from "./components/ReportView";
import { ScanForm } from "./components/ScanForm";
import { ScanProgress } from "./components/ScanProgress";
import { useScan } from "./hooks/useScan";

const chipIllustration = new URL("./assets/mx-chip.webp", import.meta.url).href;

type AppProps = {
  initialJob?: ScanJob;
  pollIntervalMs?: number;
};

export function App({ initialJob, pollIntervalMs = 1_500 }: AppProps) {
  const { view, reset, onCreated, onUpdated, retry } = useScan(initialJob, pollIntervalMs);
  const [ruleCount, setRuleCount] = useState<number | null>(null);

  useEffect(() => {
    getRules()
      .then((catalog) => setRuleCount(catalog.rules.length))
      .catch(() => {
        // The workspace remains usable when the catalog is unavailable.
      });
  }, []);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">跳至主要内容</a>
      <aside className="workspace-sidebar" aria-label="工作区">
        <a className="brand" href="/" aria-label="MXReady 首页">
          <svg className="brand-mark" viewBox="0 0 36 36" aria-hidden="true">
            <path d="M3 31V5l15 11L33 5v26h-7V19l-8 6-8-6v12Z" fill="currentColor" />
            <path d="m3 5 15 11v9L3 14Zm30 0L18 16v9l15-11Z" fill="#399780" />
          </svg>
          <strong>MXReady</strong>
        </a>
        <div className="workspace-current"><Icon name="scan" /><span>源码体检</span></div>
        <span className="sidebar-caption">CUDA <span aria-hidden="true">→</span> MXMACA</span>
      </aside>

      <div className="workspace">
        <header className="workspace-header">
          <div className="breadcrumb"><span>工作台</span><span aria-hidden="true">/</span><span>{view.kind === "report" ? "迁移报告" : "源码体检"}</span></div>
          <span className="header-meta">{"规则集 v1" + (ruleCount === null ? "" : " · " + ruleCount + " 项")}</span>
        </header>
        <main id="main-content" tabIndex={-1}>
          {view.kind === "idle" ? (
            <div className="scan-workspace">
              <div className="page-heading">
                <h1>新建体检</h1>
                <p>PyTorch CUDA <span aria-hidden="true">→</span> MXMACA</p>
              </div>
              <section className="scan-card" aria-label="新建源码体检">
                <ScanForm onCreated={onCreated} />
                <div className="chip-art" aria-hidden="true">
                  <span>CUDA → MXMACA</span>
                  <img src={chipIllustration} alt="" width="1086" height="1448" />
                </div>
              </section>
              <ol className="workflow" aria-label="迁移流程">
                <li><span className="workflow-icon"><Icon name="scan" /></span><div><small>01</small><strong>源码扫描</strong></div></li>
                <li><span className="workflow-icon"><Icon name="file" /></span><div><small>02</small><strong>迁移报告</strong></div></li>
                <li><span className="workflow-icon"><Icon name="chip" /></span><div><small>03</small><strong>真机验证</strong></div></li>
              </ol>
            </div>
          ) : null}

          {view.kind === "scanning" ? (
            <ErrorBoundary label="扫描进度"><ScanProgress job={view.job} /></ErrorBoundary>
          ) : null}
          {view.kind === "report-loading" || view.kind === "restoring" ? <ReportSkeleton /> : null}
          {view.kind === "report" ? (
            <ErrorBoundary label="报告内容">
              <ReportView onReset={reset} onUpdated={onUpdated} report={view.report} />
            </ErrorBoundary>
          ) : null}
          {view.kind === "error" ? (
            <section className="error-panel" role="alert">
              <span className="panel-icon"><Icon name="info" /></span>
              <p className="eyebrow">任务中止</p>
              <h1>这次体检没有完成</h1>
              <code className="error-code">{view.code}</code>
              <p>{view.message}</p>
              <div className="error-actions">
                {view.scanId ? <button className="primary-button" onClick={retry} type="button">继续查看扫描</button> : null}
                <button className="secondary-button" onClick={reset} type="button">重新开始</button>
              </div>
            </section>
          ) : null}
          <footer className="workspace-footer"><Icon name="info" /><span>静态检查不等于硬件兼容认证</span></footer>
        </main>
      </div>
    </div>
  );
}
