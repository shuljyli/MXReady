import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import type { ScanReport, Severity, StaticStatus } from "../api/types";
import { getReport, updateChecklist } from "../api/client";
import { agentHandoff, reportUrl } from "../lib/integration";
import { CopyButton } from "./CopyButton";
import { FindingCard } from "./FindingCard";
import { Icon } from "./Icon";
import { VerificationPanel } from "./VerificationPanel";
import { ReportDetails } from "./ReportDetails";
import { ReportExports } from "./ReportExports";
import { Pagination } from "./Pagination";
import { VerificationHistory } from "./VerificationHistory";
import { ReportComparison } from "./ReportComparison";

type FindingFilter = "all" | Severity;

type ReportViewProps = {
  report: ScanReport;
  onReset: () => void;
  onUpdated?: (report: ScanReport, source?: "verification" | "checklist") => void;
  onRescan?: (report: ScanReport) => void;
  onMcp?: () => void;
  onOpenRule?: (id: string, version: number) => void;
};

const staticCopy: Record<
  StaticStatus,
  { heading: string; label: string; description: string }
> = {
  passed: {
    heading: "静态检查已通过",
    label: "PASS",
    description: "没有命中阻塞项或警告项，仍需完成沐曦真机验证。",
  },
  warnings: {
    heading: "发现需要复核的迁移风险",
    label: "REVIEW",
    description: "没有阻塞项，但建议在远程验证前处理下列警告。",
  },
  blocked: {
    heading: "发现阻塞迁移的问题",
    label: "BLOCKED",
    description: "建议先处理阻塞项，再申请宝贵的沐曦远程算力。",
  },
  failed: {
    heading: "静态检查失败",
    label: "FAILED",
    description: "报告生成未完成，请查看分析警告或重新扫描。",
  },
};

const verificationLabels = {
  "not-run": "未做真机验证",
  verified: "真机环境已验证",
  failed: "真机验证失败",
  stale: "真机结果已过期",
} as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    hour12: false,
  }).format(new Date(value));
}

function savedFilters(scanId: string): Record<string, string> {
  try {
    const value = JSON.parse(sessionStorage.getItem(`mxready:filters:${scanId}`) ?? "{}");
    if (!value || typeof value !== "object") return {};
    return Object.fromEntries(Object.entries(value).filter(([key, text]) =>
      ["filter", "category", "rule", "file", "search"].includes(key) && typeof text === "string" && text.length <= 1024)) as Record<string, string>;
  } catch { return {}; }
}

export function ReportView({
  report,
  onReset,
  onUpdated = () => undefined,
  onRescan,
  onMcp,
  onOpenRule,
}: ReportViewProps) {
  const [saved] = useState(() => savedFilters(report.scan_id));
  const [filter, setFilter] = useState<FindingFilter>(["blocker", "warning", "info"].includes(saved.filter) ? saved.filter as FindingFilter : "all");
  const [category, setCategory] = useState(saved.category ?? "");
  const [rule, setRule] = useState(saved.rule ?? "");
  const [file, setFile] = useState(saved.file ?? "");
  const [search, setSearch] = useState(saved.search ?? "");
  const [offset, setOffset] = useState(0);
  const [savingItem, setSavingItem] = useState<string | null>(null);
  const [savingCompleted, setSavingCompleted] = useState(false);
  const [saveError, setSaveError] = useState("");
  const checklistRequest = useRef<AbortController | null>(null);
  useEffect(() => () => checklistRequest.current?.abort(), [report.scan_id]);
  useEffect(() => {
    setOffset(0);
    try { sessionStorage.setItem(`mxready:filters:${report.scan_id}`, JSON.stringify({ filter, category, rule, file, search })); } catch { /* Storage may be disabled. */ }
  }, [filter, category, rule, file, search, report.scan_id]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const refreshRequest = useRef<AbortController | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const findingsHeading = useRef<HTMLHeadingElement>(null);
  const visibleFindings = useMemo(
    () => report.findings.filter((finding) => (filter === "all" || finding.severity === filter)
      && (!category || finding.category === category) && (!rule || finding.rule_id === rule)
      && (!file || finding.relative_path === file)
      && `${finding.title} ${finding.rule_id} ${finding.relative_path} ${finding.message}`
        .toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())),
    [filter, category, rule, file, search, report.findings],
  );
  const status = staticCopy[report.static_status];
  const categories = [...new Set(report.findings.map((finding) => finding.category))].sort();
  const ruleIds = [...new Set(report.findings.map((finding) => finding.rule_id))].sort();
  const files = [...new Set(report.findings.map((finding) => finding.relative_path))].sort();
  const pageOffset = Math.min(offset, Math.max(0, Math.ceil(visibleFindings.length / 50) - 1) * 50);

  async function saveItem(ruleId: string, completed: boolean) {
    if (savingItem) return;
    const controller = new AbortController(); checklistRequest.current = controller;
    refreshRequest.current?.abort(); setRefreshing(false); setSavingItem(ruleId); setSavingCompleted(completed); setSaveError("");
    try {
      const updated = await updateChecklist(report.scan_id, ruleId, completed, controller.signal);
      if (!controller.signal.aborted) { refreshRequest.current?.abort(); onUpdated(updated, "checklist"); }
    } catch (err) { if (!controller.signal.aborted) setSaveError(err instanceof Error ? err.message : "保存清单失败"); }
    finally { if (!controller.signal.aborted) setSavingItem(null); }
  }

  useEffect(() => {
    setRefreshing(false);
    return () => refreshRequest.current?.abort();
  }, [report]);

  async function refresh() {
    refreshRequest.current?.abort();
    const controller = new AbortController();
    refreshRequest.current = controller;
    setRefreshing(true); setRefreshError(null);
    try {
      const updated = await getReport(report.scan_id, controller.signal);
      if (!controller.signal.aborted) onUpdated(updated);
    } catch (error) {
      if (!controller.signal.aborted) setRefreshError(error instanceof Error ? error.message : "刷新失败，请重试。");
    } finally {
      if (!controller.signal.aborted) setRefreshing(false);
    }
  }

  function clearFilters() {
    setFilter("all"); setCategory(""); setRule(""); setFile(""); setSearch("");
  }
  function showFile(path: string) {
    clearFilters(); setFile(path); findingsHeading.current?.focus();
  }
  function showRule(id: string) {
    clearFilters(); setRule(id); findingsHeading.current?.focus();
  }

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  function handleFilterKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const buttons = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>(
        "[data-filter-button]",
      ),
    );
    if (!buttons.length) {
      return;
    }
    const currentIndex = buttons.indexOf(
      document.activeElement as HTMLButtonElement,
    );
    let nextIndex = currentIndex;
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        nextIndex =
          currentIndex === -1 ? 0 : (currentIndex + 1) % buttons.length;
        break;
      case "ArrowLeft":
      case "ArrowUp":
        nextIndex =
          currentIndex === -1
            ? 0
            : (currentIndex - 1 + buttons.length) % buttons.length;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = buttons.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    buttons[nextIndex].focus();
    setFilter(filterOptions[nextIndex].value);
  }

  const filterOptions: Array<{
    value: FindingFilter;
    text: string;
    ariaLabel: string;
    count: number;
  }> = [
    {
      value: "all",
      text: "全部",
      ariaLabel: `查看全部结果（${report.summary.total_count}）`,
      count: report.summary.total_count,
    },
    {
      value: "blocker",
      text: "阻塞",
      ariaLabel: `只看阻塞项（${report.summary.blocker_count}）`,
      count: report.summary.blocker_count,
    },
    {
      value: "warning",
      text: "警告",
      ariaLabel: `只看警告项（${report.summary.warning_count}）`,
      count: report.summary.warning_count,
    },
    {
      value: "info",
      text: "提示",
      ariaLabel: `只看提示项（${report.summary.info_count}）`,
      count: report.summary.info_count,
    },
  ];

  return (
    <div className="report-view">
      <header className="report-heading">
        <div>
          <h1 id="report-title" ref={headingRef} tabIndex={-1}>迁移报告</h1>
          <div className="repository-identity">
            <span className="provider-label">{report.repository.provider}</span>
            <a href={report.repository.url} rel="noreferrer" target="_blank">
              {report.repository.owner}/{report.repository.name}
            </a>
            <code title={report.repository.commit}>{report.repository.commit.slice(0, 12)}</code>
          </div>
        </div>
        <button className="secondary-button" onClick={onReset} type="button">新建体检</button>
      </header>

      <div className="report-actions">
        <CopyButton label="复制报告链接" text={reportUrl(report.scan_id)} />
        <button className="secondary-button compact-button" type="button" onClick={refresh} disabled={refreshing}>{refreshing ? "正在刷新…" : "刷新报告"}</button>
        {onRescan ? <button className="secondary-button compact-button" type="button" onClick={() => onRescan(report)}>同仓库重新扫描</button> : null}
        {onMcp ? <button className="secondary-button compact-button" type="button" onClick={onMcp}>交给 Agent 继续分析</button> : null}
        <CopyButton label="复制 Agent 交接内容" text={agentHandoff(report)} />
      </div>
      {refreshError ? <p role="alert">{refreshError}</p> : null}

      <div className="status-grid">
        <section className={"status-card report-status-" + report.static_status} aria-label="静态检查">
          <span className="panel-icon"><Icon name="file" /></span>
          <div><h2>静态检查</h2><strong className="status-label">{status.heading}</strong><p>{status.description}</p></div>
        </section>
        <section className={"status-card hardware-status-" + report.verification_status} aria-label="真机验证状态">
          <span className="panel-icon"><Icon name="chip" /></span>
          <div><h2>真机验证</h2><strong className="status-label">{verificationLabels[report.verification_status]}</strong><p>与静态检查独立，绑定当前提交。</p></div>
        </section>
      </div>

      <section className="report-summary" aria-label="扫描摘要">
        <dl className="summary-counts">
          <div><dt>发现</dt><dd>{report.summary.total_count}</dd></div>
          <div className="summary-blocker" aria-label={"阻塞项 " + report.summary.blocker_count}><dt>阻塞</dt><dd>{report.summary.blocker_count}</dd></div>
          <div className="summary-warning" aria-label={"警告项 " + report.summary.warning_count}><dt>警告</dt><dd>{report.summary.warning_count}</dd></div>
          <div className="summary-info"><dt>提示</dt><dd>{report.summary.info_count}</dd></div>
        </dl>
        <dl className="summary-meta">
          <div><dt>扫描时间</dt><dd>{formatDate(report.scanned_at)}</dd></div>
          <div><dt>规则 / 工具</dt><dd>v{report.ruleset_version} / v{report.tool_version}</dd></div>
        </dl>
      </section>

      <section className="report-section priority-files" aria-label="优先复核文件">
        <h2>优先复核文件</h2><p className="muted">优先列出存在阻塞项的文件；没有阻塞项时列出警告文件。数量按聚合后的发现统计。</p>
        {report.summary.top_blockers.length ? <ol>{report.summary.top_blockers.map((path) => <li key={path}>
          <button type="button" className="text-button compact-button" aria-label={"优先复核 " + path}
            onClick={() => showFile(path)}>{path}</button>
        </li>)}</ol> : <p>暂无优先复核文件</p>}
      </section>
      <ReportDetails report={report} />
      <ReportComparison report={report} />

      <div className="report-layout">
        <div className="report-main">
          {report.analysis_warnings.length ? (
            <section className="analysis-warnings" aria-labelledby="warnings-title">
              <h2 id="warnings-title"><Icon name="info" />扫描范围提示</h2>
              <ul>{report.analysis_warnings.map((warning, index) => (
                <li key={warning.code + "-" + index}>
                  <code>{warning.code}</code>
                  <span>{warning.relative_path ?? "repository"}</span>
                  <p>{warning.message}</p>
                </li>
              ))}</ul>
            </section>
          ) : null}

          <section className="report-section findings-section">
            <div className="section-heading">
              <h2 ref={findingsHeading} tabIndex={-1}>源码发现</h2>
              <div aria-label="按严重级别筛选" className="finding-filters"
                onKeyDown={handleFilterKeyDown} role="group">
                {filterOptions.map((option) => (
                  <button aria-label={option.ariaLabel} aria-pressed={filter === option.value}
                    data-filter-button="" key={option.value} onClick={() => setFilter(option.value)}
                    tabIndex={filter === option.value ? 0 : -1} type="button">
                    {option.text}<span>{option.count}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="filter-grid">
              <label className="field">搜索发现<input type="search" value={search} placeholder="标题、规则、文件或消息"
                onChange={(event) => setSearch(event.target.value)} /></label>
              <label className="field">发现分类<select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">全部分类</option>{categories.map((value) => <option key={value}>{value}</option>)}
              </select></label>
              <label className="field">发现规则<select value={rule} onChange={(event) => setRule(event.target.value)}>
                <option value="">全部规则</option>{ruleIds.map((value) => <option key={value}>{value}</option>)}
              </select></label>
              <label className="field">发现文件<select value={file} onChange={(event) => setFile(event.target.value)}>
                <option value="">全部文件</option>{files.map((value) => <option key={value}>{value}</option>)}
              </select></label>
            </div>
            <div className="filter-summary"><p role="status">显示 {visibleFindings.length} / {report.summary.total_count} 条发现</p>
              <button type="button" className="text-button compact-button" onClick={clearFilters}>清除筛选</button></div>
            {visibleFindings.length ? (
              <div className="finding-list">{visibleFindings.slice(pageOffset, pageOffset + 50).map((finding, index) => (
                <FindingCard finding={finding} onOpenRule={onOpenRule}
                  key={finding.rule_id + "-" + finding.relative_path + "-" + finding.line_start + "-" + index} />
              ))}</div>
            ) : (
              <div className="empty-findings">
                <span className="panel-icon"><Icon name="file" /></span>
                <strong>当前筛选下没有结果</strong>
                <p>这不代表已经完成 MXMACA 真机兼容验证。</p>
              </div>
            )}
            {visibleFindings.length > 50 ? <Pagination label="发现" offset={pageOffset} limit={50} total={visibleFindings.length}
              onChange={(value) => { setOffset(value); findingsHeading.current?.focus(); }} /> : null}
          </section>

          <section className="report-section checklist-section">
            <div className="section-heading"><h2>迁移清单</h2></div>
            <p className="muted">勾选仅记录人工处理进度，不改变静态结论或真机验证状态。</p>
            {saveError ? <p role="alert">{saveError}</p> : null}
            {report.migration_checklist.length ? (
              <ol className="checklist">{report.migration_checklist.map((item, index) => (
                <li key={item.rule_id + "-" + index}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div><strong>{item.title}</strong><p>{item.action}</p>
                    <label className="checklist-toggle"><input type="checkbox" checked={savingItem === item.rule_id ? savingCompleted : item.completed} disabled={savingItem !== null}
                      aria-label={"标记已处理：" + item.title} onChange={(event) => void saveItem(item.rule_id, event.target.checked)} />
                      {savingItem === item.rule_id ? "正在保存…" : item.completed ? "已处理（人工记录）" : "待处理"}</label>
                    <small>{item.rule_id}</small>
                    <button className="text-button compact-button" type="button" onClick={() => showRule(item.rule_id)}>查看此规则的发现</button>
                    <details><summary>受影响文件（{item.affected_files.length}）</summary><ul>{item.affected_files.map((path) => <li key={path}>
                      <button type="button" className="text-button compact-button" onClick={() => showFile(path)}>{path}</button>
                    </li>)}</ul></details>
                  </div>
                </li>
              ))}</ol>
            ) : <p className="section-empty">没有从静态结果生成迁移动作。</p>}
          </section>
        </div>

        <aside className="report-tools" aria-label="报告工具">
          <ReportExports report={report} />
          <VerificationPanel report={report} onUpdated={(value) => onUpdated(value, "verification")} />
          <VerificationHistory report={report} />
        </aside>
      </div>

      <div className="report-reset">
        <button className="text-button" onClick={onReset} type="button">扫描另一个仓库<Icon name="arrow" /></button>
      </div>
    </div>
  );
}
