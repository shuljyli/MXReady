import { useEffect, useState } from "react";

import { getRules } from "./api/client";
import type { ScanJob } from "./api/types";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ReportSkeleton } from "./components/ReportSkeleton";
import { ReportView } from "./components/ReportView";
import { ScanForm } from "./components/ScanForm";
import { ScanProgress } from "./components/ScanProgress";
import { useScan } from "./hooks/useScan";

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
        // The header stays usable without the rule count.
      });
  }, []);

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="MXReady 首页">
          <span className="brand-mark" aria-hidden="true">
            MX
          </span>
          <span>
            <strong>MXReady</strong>
            <small>沐曦适配体检</small>
          </span>
        </a>
        <div className="header-meta">
          <span className="live-dot" aria-hidden="true" />
          <span>
            {`规则集 v1${ruleCount === null ? "" : ` · ${ruleCount} 项`}`}
          </span>
        </div>
      </header>

      <main>
        {view.kind === "idle" ? (
          <div className="landing-grid">
            <section className="hero" aria-labelledby="hero-title">
              <p className="eyebrow">MXMACA MIGRATION READINESS</p>
              <h1 id="hero-title">
                让 CUDA 项目
                <br />
                更接近<span>沐曦</span>
              </h1>
              <p className="hero-copy">
                用可解释的静态规则，提前定位 PyTorch CUDA
                扩展迁移到国产 GPU 生态时值得复核的代码、依赖和构建配置。
              </p>
              <div className="scope-strip">
                <span>
                  <strong>{ruleCount ?? "…"}</strong>
                  首批规则
                </span>
                <span>
                  <strong>0</strong>
                  项目代码执行
                </span>
                <span>
                  <strong>1</strong>
                  份迁移清单
                </span>
              </div>
              <aside className="truth-note">
                <span aria-hidden="true">i</span>
                <div>
                  <strong>静态检查不是硬件兼容认证</strong>
                  <p>
                    最终结论仍需在相同提交上使用沐曦 GPU
                    运行验证包，MXReady 会清楚区分两种状态。
                  </p>
                </div>
              </aside>
            </section>
            <ScanForm
              onCreated={onCreated}
            />
          </div>
        ) : null}

        {view.kind === "scanning" ? (
          <ErrorBoundary label="扫描进度">
            <ScanProgress job={view.job} />
          </ErrorBoundary>
        ) : null}

        {view.kind === "report-loading" || view.kind === "restoring" ? <ReportSkeleton /> : null}

        {view.kind === "report" ? (
          <ErrorBoundary label="报告内容">
            <ReportView
              onReset={reset}
              onUpdated={onUpdated}
              report={view.report}
            />
          </ErrorBoundary>
        ) : null}

        {view.kind === "error" ? (
          <section className="error-panel" role="alert">
            <p className="eyebrow">任务中止</p>
            <span className="error-code">{view.code}</span>
            <h1>这次体检没有完成</h1>
            <p>{view.message}</p>
            {view.scanId ? (
              <button className="secondary-button" onClick={retry} type="button">继续查看扫描</button>
            ) : null}
            <button className="secondary-button" onClick={reset} type="button">
              重新开始
            </button>
          </section>
        ) : null}
      </main>

      <footer>
        <span>MXReady · 青年开源专项基金种子计划</span>
        <span>面向公开源码的可解释检查</span>
      </footer>
    </div>
  );
}
