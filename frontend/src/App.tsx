import { useEffect, useState } from "react";

import { getHealth, getRules } from "./api/client";
import type { RuleCatalog, ScanJob, ScanReport, ServiceHealth } from "./api/types";
import { BatchScans } from "./components/BatchScans";
import { CliGuide } from "./components/CliGuide";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Icon } from "./components/Icon";
import { McpIntegration } from "./components/McpIntegration";
import { OpenScanForm } from "./components/OpenScanForm";
import { ReportSkeleton } from "./components/ReportSkeleton";
import { ReportView } from "./components/ReportView";
import { RuleCatalogView } from "./components/RuleCatalogView";
import { ScanForm } from "./components/ScanForm";
import { ScanProgress } from "./components/ScanProgress";
import { TaskDetails } from "./components/TaskDetails";
import { ScanHistory } from "./components/ScanHistory";
import { useScan } from "./hooks/useScan";
import { useWorkspacePage, workspaceHref, type WorkspacePage } from "./hooks/useWorkspacePage";

const chipIllustration = new URL("./assets/mx-chip.webp", import.meta.url).href;
const pages: Array<{ page: WorkspacePage; label: string; icon: "scan" | "file" | "chip" }> = [
  { page: "scan", label: "源码体检", icon: "scan" },
  { page: "batch", label: "批量扫描", icon: "scan" },
  { page: "history", label: "扫描历史", icon: "file" },
  { page: "rules", label: "规则库", icon: "file" },
  { page: "mcp", label: "MCP 接入", icon: "chip" },
  { page: "cli", label: "命令行使用", icon: "file" },
];

// 只覆盖能到达本页错误面板的错误码：job.failure_code 与轮询请求失败。
// 提交阶段的准入错误（限流、并发上限）由 ScanForm 直接展示服务端文案，不在此列。
const failureHints: Record<string, string> = {
  SCAN_INTERRUPTED: "任务执行已中断，请新建扫描。原任务不会自动重放。",
  SCAN_INTERNAL_ERROR: "扫描过程中出现未预期的错误，请新建扫描；若持续失败请查看服务日志。",
  SCAN_FAILED: "扫描未能产出结果，请新建扫描；若持续失败请核对仓库地址与提交。",
  SCAN_NOT_FOUND: "找不到这个扫描任务，可能已被清理，请核对扫描 ID 或重新发起。",
  CLONE_FAILED: "无法获取该公开仓库，请确认仓库可公开访问后重新扫描。",
  REPOSITORY_UNAVAILABLE: "该仓库暂时无法访问，请稍后重新扫描。",
  REPOSITORY_NOT_FOUND: "该仓库不存在或已设为私有，请检查地址后重新扫描。",
  GIT_NOT_FOUND: "本机未安装 Git，命令行扫描与克隆式分析无法执行，请安装 Git 或改用压缩包分析。",
  INVALID_REPOSITORY_URL: "仓库地址需要是完整的 GitHub 或 Gitee 公开 HTTPS 地址。",
  UNSUPPORTED_REPOSITORY_HOST: "目前只支持 GitHub 和 Gitee 的公开仓库。",
  INVALID_GIT_REF: "分支、标签或提交编号格式不合法，请检查后重新提交。",
  ARCHIVE_FETCH_FAILED: "无法下载仓库压缩包，请稍后重试，或改用其它分支、提交。",
  ARCHIVE_FALLBACK_UNAVAILABLE: "无法退回压缩包获取，请检查 Git 是否可用或稍后重试。",
  INVALID_REPOSITORY_ARCHIVE: "仓库压缩包结构异常，无法安全解压，请重新扫描。",
  TOO_MANY_FILES: "仓库文件数超过分析上限，请精简仓库或只扫描核心目录。",
  REPOSITORY_TOO_LARGE: "仓库体积超过下载上限，请清理大文件后重试。",
  ANALYSIS_LIMIT_EXCEEDED: "规则评估超过时间预算，请缩小扫描范围后重试。",
  REQUEST_TIMEOUT: "读取服务超时，请确认 Web 服务仍在运行后重试。",
  NETWORK_ERROR: "无法连接 Web 服务，请确认服务已启动、地址与代理配置正确。",
  HTTP_ERROR: "服务返回了无法识别的错误，请刷新页面或查看服务日志。",
  POLLING_FAILED: "暂时读不到任务状态，请稍后点击“继续查看扫描”。",
};

type AppProps = { initialJob?: ScanJob; pollIntervalMs?: number };

export function App({ initialJob, pollIntervalMs = 1_500 }: AppProps) {
  const { view, reset, open, onCreated, onUpdated, retry } = useScan(initialJob, pollIntervalMs);
  const { page, ruleId, ruleVersion, navigate } = useWorkspacePage();
  const [catalog, setCatalog] = useState<RuleCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [healthFailed, setHealthFailed] = useState(false);
  const [healthAttempt, setHealthAttempt] = useState(0);
  const [draft, setDraft] = useState({ repository: "", ref: "" });

  useEffect(() => {
    const controller = new AbortController();
    setCatalogLoading(true); setCatalogError(null);
    getRules(controller.signal).then((value) => {
      if (!controller.signal.aborted) setCatalog(value);
    }).catch(() => {
      if (!controller.signal.aborted) setCatalogError("规则集暂不可用");
    }).finally(() => {
      if (!controller.signal.aborted) setCatalogLoading(false);
    });
    return () => controller.abort();
  }, [catalogAttempt]);

  useEffect(() => {
    const controller = new AbortController();
    setHealthFailed(false);
    getHealth(controller.signal).then((value) => {
      if (!controller.signal.aborted) setHealth(value);
    }).catch(() => {
      if (!controller.signal.aborted) setHealthFailed(true);
    });
    return () => controller.abort();
  }, [healthAttempt]);

  function newScan() {
    setDraft({ repository: "", ref: "" }); reset(); navigate("scan");
  }
  function rescan(report: ScanReport) {
    setDraft({ repository: report.repository.url, ref: report.repository.commit });
    reset(); navigate("scan");
  }
  const pageTitle = page === "scan" && view.kind === "report" ? "迁移报告"
    : pages.find((entry) => entry.page === page)!.label;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">跳至主要内容</a>
      <aside className="workspace-sidebar" aria-label="工作区">
        <a className="brand" href="/" aria-label="MXReady 首页">
          <svg className="brand-mark" viewBox="0 0 36 36" aria-hidden="true">
            <path d="M3 31V5l15 11L33 5v26h-7V19l-8 6-8-6v12Z" fill="currentColor" />
            <path d="m3 5 15 11v9L3 14Zm30 0L18 16v9l15-11Z" fill="#399780" />
          </svg><strong>MXReady</strong>
        </a>
        <nav className="workspace-nav" aria-label="主要导航">{pages.map((entry) => (
          <a key={entry.page} href={workspaceHref(entry.page)} aria-current={entry.page === page ? "page" : undefined}
            onClick={(event) => {
              if (event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
                event.preventDefault(); navigate(entry.page);
              }
            }}><Icon name={entry.icon} /><span>{entry.label}</span></a>
        ))}</nav>
        <span className="sidebar-caption">CUDA <span aria-hidden="true">→</span> MXMACA</span>
      </aside>

      <div className="workspace">
        <header className="workspace-header">
          <div className="breadcrumb"><span>工作台</span><span aria-hidden="true">/</span><span>{pageTitle}</span></div>
          <span className="header-meta">{catalog
            ? `规则集 v${catalog.version} · ${catalog.rules.length} 项${catalog.extra_version ? ` · 扩展 ${catalog.extra_version}` : ""}`
            : catalogError ?? "正在加载规则集…"}</span>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div hidden={page !== "batch"}><ErrorBoundary label="批量扫描"><BatchScans onOpen={id => { open(id); navigate("scan"); }} /></ErrorBoundary></div>
          {page === "history" ? <ErrorBoundary label="扫描历史"><ScanHistory onOpen={(id) => { open(id); navigate("scan"); }} /></ErrorBoundary> : null}
          {page === "rules" ? <ErrorBoundary label="规则库"><RuleCatalogView catalog={catalog}
            loading={catalogLoading} error={catalogError} onRetry={() => setCatalogAttempt((value) => value + 1)}
            selectedRule={ruleId} historicalVersion={ruleVersion} /></ErrorBoundary> : null}
          {page === "mcp" ? <ErrorBoundary label="MCP 接入"><McpIntegration
            report={view.kind === "report" ? view.report : undefined} /></ErrorBoundary> : null}
          {page === "cli" ? <CliGuide /> : null}
          {page === "scan" ? <>
            {view.kind === "idle" ? <div className="scan-workspace">
              <div className="page-heading"><h1>新建体检</h1><p>PyTorch CUDA <span aria-hidden="true">→</span> MXMACA</p></div>
              <section className="scan-card" aria-label="新建源码体检">
                <ScanForm onCreated={onCreated} initialRepository={draft.repository} initialRef={draft.ref} />
                <div className="chip-art" aria-hidden="true"><span>CUDA → MXMACA</span>
                  <img src={chipIllustration} alt="" width="1086" height="1448" /></div>
              </section>
              <ol className="workflow" aria-label="迁移流程">
                <li><span className="workflow-icon"><Icon name="scan" /></span><div><small>01</small><strong>源码扫描</strong></div></li>
                <li><span className="workflow-icon"><Icon name="file" /></span><div><small>02</small><strong>迁移报告</strong></div></li>
                <li><span className="workflow-icon"><Icon name="chip" /></span><div><small>03</small><strong>真机验证</strong></div></li>
              </ol>
              <div className="home-shortcuts">
                <button className="secondary-button" type="button" onClick={() => navigate("mcp")}>让编码 Agent 使用 MXReady<Icon name="arrow" /></button>
                <button className="text-button" type="button" onClick={() => navigate("cli")}>本地目录与批量扫描</button>
              </div>
              <OpenScanForm onOpen={open} />
            </div> : null}
            {view.kind === "scanning" ? <ErrorBoundary label="扫描进度"><ScanProgress job={view.job} /></ErrorBoundary> : null}
            {view.kind === "report-loading" || view.kind === "restoring" ? <ReportSkeleton /> : null}
            {view.kind === "report" ? <ErrorBoundary label="报告内容"><ReportView key={view.report.scan_id}
              report={view.report} onReset={newScan} onUpdated={onUpdated} onRescan={rescan}
              onMcp={() => navigate("mcp")} onOpenRule={(id, version) => navigate("rules", id, version)} />
            </ErrorBoundary> : null}
            {view.kind === "error" ? <section className="error-panel" role="alert">
              <span className="panel-icon"><Icon name="info" /></span><p className="eyebrow">任务中止</p>
              <h1>这次体检没有完成</h1><code className="error-code">{view.code}</code><p>{view.message}</p>
              {failureHints[view.code] ? <p>{failureHints[view.code]}</p> : null}
              {view.job ? <TaskDetails job={view.job} /> : null}
              <div className="error-actions">
                {view.scanId && !view.job ? <button className="primary-button" onClick={retry} type="button">继续查看扫描</button> : null}
                <button className="secondary-button" onClick={newScan} type="button">重新开始</button>
              </div>
            </section> : null}
          </> : null}
          <footer className="workspace-footer"><Icon name="info" /><span>静态检查不等于硬件兼容认证</span>
            <span className="service-info">{healthFailed ? <>Web 服务信息暂不可用 <button type="button" className="text-button compact-button"
              onClick={() => setHealthAttempt((value) => value + 1)}>重试服务信息</button></>
              : health ? `Web 服务 v${health.version} · ${health.status === "ok" ? "服务正常" : health.status}` : "正在读取服务信息…"}</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
