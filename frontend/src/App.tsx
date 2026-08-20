import { useEffect, useState } from "react";

import { getReport, getRules, getScan, MxReadyApiError } from "./api/client";
import type { ScanJob, ScanReport } from "./api/types";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ReportSkeleton } from "./components/ReportSkeleton";
import { ReportView } from "./components/ReportView";
import { ScanForm } from "./components/ScanForm";
import { ScanProgress } from "./components/ScanProgress";

type ViewState =
  | { kind: "idle" }
  | { kind: "scanning"; job: ScanJob }
  | { kind: "report-loading"; job: ScanJob }
  | { kind: "report"; report: ScanReport }
  | { kind: "error"; code: string; message: string };

type AppProps = {
  initialJob?: ScanJob;
  pollIntervalMs?: number;
};

const activeStatuses = new Set([
  "queued",
  "cloning",
  "indexing",
  "analyzing",
]);

type ErrorStage = "polling" | "report";

function visibleError(
  error: unknown,
  stage: ErrorStage,
): { code: string; message: string } {
  if (error instanceof MxReadyApiError) {
    return { code: error.code, message: error.message };
  }
  if (stage === "report") {
    return {
      code: "REPORT_LOAD_FAILED",
      message: "读取报告失败，请稍后重新开始。",
    };
  }
  return {
    code: "POLLING_FAILED",
    message: "读取扫描进度失败，请稍后重新开始。",
  };
}

function initialView(initialJob: ScanJob | undefined): ViewState {
  if (initialJob === undefined) {
    return { kind: "idle" };
  }
  if (initialJob.status === "completed") {
    return { kind: "report-loading", job: initialJob };
  }
  if (initialJob.status === "failed") {
    return {
      kind: "error",
      code: initialJob.failure_code ?? "SCAN_FAILED",
      message: initialJob.failure_message ?? "扫描未能完成。",
    };
  }
  return { kind: "scanning", job: initialJob };
}

export function App({ initialJob, pollIntervalMs = 1_500 }: AppProps) {
  const [view, setView] = useState<ViewState>(() => initialView(initialJob));
  const [ruleCount, setRuleCount] = useState<number | null>(null);

  useEffect(() => {
    getRules()
      .then((catalog) => setRuleCount(catalog.rules.length))
      .catch(() => {
        // The header stays usable without the rule count.
      });
  }, []);

  useEffect(() => {
    if (
      view.kind !== "scanning" ||
      !activeStatuses.has(view.job.status)
    ) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const nextJob = await getScan(view.job.id);
        if (cancelled) {
          return;
        }
        if (nextJob.status === "completed") {
          setView({ kind: "report-loading", job: nextJob });
          return;
        }
        if (nextJob.status === "failed") {
          setView({
            kind: "error",
            code: nextJob.failure_code ?? "SCAN_FAILED",
            message: nextJob.failure_message ?? "扫描未能完成。",
          });
          return;
        }
        setView({ kind: "scanning", job: nextJob });
      } catch (error) {
        if (!cancelled) {
          setView({ kind: "error", ...visibleError(error, "polling") });
        }
      }
    }, pollIntervalMs);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [pollIntervalMs, view]);

  useEffect(() => {
    if (view.kind !== "report-loading") {
      return;
    }

    let cancelled = false;
    getReport(view.job.id)
      .then((report) => {
        if (!cancelled) {
          setView({ kind: "report", report });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setView({ kind: "error", ...visibleError(error, "report") });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [view]);

  function reset() {
    setView({ kind: "idle" });
  }

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
              onCreated={(job) => setView({ kind: "scanning", job })}
            />
          </div>
        ) : null}

        {view.kind === "scanning" ? (
          <ErrorBoundary label="扫描进度">
            <ScanProgress job={view.job} />
          </ErrorBoundary>
        ) : null}

        {view.kind === "report-loading" ? <ReportSkeleton /> : null}

        {view.kind === "report" ? (
          <ErrorBoundary label="报告内容">
            <ReportView
              onReset={reset}
              onUpdated={(report) => setView({ kind: "report", report })}
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
