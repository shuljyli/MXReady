import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import type { ScanReport, Severity, StaticStatus } from "../api/types";
import { FindingCard } from "./FindingCard";
import { Icon } from "./Icon";
import { VerificationPanel } from "./VerificationPanel";

type FindingFilter = "all" | Severity;

type ReportViewProps = {
  report: ScanReport;
  onReset: () => void;
  onUpdated?: (report: ScanReport) => void;
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

export function ReportView({
  report,
  onReset,
  onUpdated = () => undefined,
}: ReportViewProps) {
  const [filter, setFilter] = useState<FindingFilter>("all");
  const headingRef = useRef<HTMLHeadingElement>(null);
  const visibleFindings = useMemo(
    () =>
      filter === "all"
        ? report.findings
        : report.findings.filter((finding) => finding.severity === filter),
    [filter, report.findings],
  );
  const status = staticCopy[report.static_status];
  const downloadBase = `/api/scans/${report.scan_id}`;

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
              <h2>源码发现</h2>
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
            {visibleFindings.length ? (
              <div className="finding-list">{visibleFindings.map((finding, index) => (
                <FindingCard finding={finding}
                  key={finding.rule_id + "-" + finding.relative_path + "-" + finding.line_start + "-" + index} />
              ))}</div>
            ) : (
              <div className="empty-findings">
                <span className="panel-icon"><Icon name="file" /></span>
                <strong>当前筛选下没有结果</strong>
                <p>这不代表已经完成 MXMACA 真机兼容验证。</p>
              </div>
            )}
          </section>

          <section className="report-section checklist-section">
            <div className="section-heading"><h2>迁移清单</h2></div>
            {report.migration_checklist.length ? (
              <ol className="checklist">{report.migration_checklist.map((item, index) => (
                <li key={item.rule_id + "-" + index}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div><strong>{item.title}</strong><p>{item.action}</p><small>{item.affected_files.join(" · ")}</small></div>
                </li>
              ))}</ol>
            ) : <p className="section-empty">没有从静态结果生成迁移动作。</p>}
          </section>
        </div>

        <aside className="report-tools" aria-label="报告工具">
          <section className="report-section export-section">
            <div className="section-heading"><h2>导出报告</h2></div>
            <div className="download-grid">
              <a aria-label="JSON" href={downloadBase + "/report.json"}><Icon name="file" /><span>JSON</span></a>
              <a aria-label="Markdown" href={downloadBase + "/report.md"}><Icon name="file" /><span>Markdown</span></a>
              <a aria-label="Badge" href={downloadBase + "/badge.svg"}><Icon name="shield" /><span>Badge</span></a>
            </div>
            <p>绑定当前提交；项目更新后请重新扫描。</p>
          </section>
          <VerificationPanel report={report} onUpdated={onUpdated} />
        </aside>
      </div>

      <div className="report-reset">
        <button className="text-button" onClick={onReset} type="button">扫描另一个仓库<Icon name="arrow" /></button>
      </div>
    </div>
  );
}
