import { useMemo, useState } from "react";

import type { ScanReport, Severity, StaticStatus } from "../api/types";
import { FindingCard } from "./FindingCard";
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
  const visibleFindings = useMemo(
    () =>
      filter === "all"
        ? report.findings
        : report.findings.filter((finding) => finding.severity === filter),
    [filter, report.findings],
  );
  const status = staticCopy[report.static_status];
  const downloadBase = `/api/scans/${report.scan_id}`;
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
      <section
        className={`report-hero report-status-${report.static_status}`}
        aria-labelledby="report-title"
      >
        <div className="report-identity">
          <p className="eyebrow">READINESS REPORT · {status.label}</p>
          <h1 id="report-title">{status.heading}</h1>
          <p>{status.description}</p>
        </div>
        <div className="repository-card">
          <span>{report.repository.provider.toUpperCase()}</span>
          <a href={report.repository.url} rel="noreferrer" target="_blank">
            {report.repository.owner}/{report.repository.name}
          </a>
          <code title={report.repository.commit}>
            {report.repository.commit.slice(0, 12)}
          </code>
        </div>
      </section>

      <section className="report-summary" aria-label="扫描摘要">
        <div className="summary-primary">
          <span>扫描结果</span>
          <strong>{report.summary.total_count}</strong>
          <small>条可解释记录</small>
        </div>
        <div className="summary-count summary-blocker">
          <span>阻塞项 {report.summary.blocker_count}</span>
          <strong>{report.summary.blocker_count}</strong>
        </div>
        <div className="summary-count summary-warning">
          <span>警告项 {report.summary.warning_count}</span>
          <strong>{report.summary.warning_count}</strong>
        </div>
        <div className="summary-count summary-info">
          <span>提示项 {report.summary.info_count}</span>
          <strong>{report.summary.info_count}</strong>
        </div>
        <dl className="summary-meta">
          <div>
            <dt>扫描时间</dt>
            <dd>{formatDate(report.scanned_at)}</dd>
          </div>
          <div>
            <dt>规则 / 工具</dt>
            <dd>
              v{report.ruleset_version} / v{report.tool_version}
            </dd>
          </div>
          <div>
            <dt>硬件状态</dt>
            <dd>{verificationLabels[report.verification_status]}</dd>
          </div>
        </dl>
      </section>

      <section className="report-section findings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">EVIDENCE-BACKED FINDINGS</p>
            <h2>源码发现</h2>
          </div>
          <div className="finding-filters" aria-label="按严重级别筛选">
            {filterOptions.map((option) => (
              <button
                aria-label={option.ariaLabel}
                aria-pressed={filter === option.value}
                key={option.value}
                onClick={() => setFilter(option.value)}
                type="button"
              >
                {option.text}
                <span>{option.count}</span>
              </button>
            ))}
          </div>
        </div>

        {visibleFindings.length ? (
          <div className="finding-list">
            {visibleFindings.map((finding, index) => (
              <FindingCard
                finding={finding}
                key={`${finding.rule_id}-${finding.relative_path}-${finding.line_start}-${index}`}
              />
            ))}
          </div>
        ) : (
          <div className="empty-findings">
            <span aria-hidden="true">✓</span>
            <strong>当前筛选下没有结果</strong>
            <p>这不代表已经完成 MXMACA 真机兼容验证。</p>
          </div>
        )}
      </section>

      <div className="report-columns">
        <section className="report-section checklist-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">MIGRATION CHECKLIST</p>
              <h2>迁移清单</h2>
            </div>
          </div>
          {report.migration_checklist.length ? (
            <ol className="checklist">
              {report.migration_checklist.map((item, index) => (
                <li key={`${item.rule_id}-${index}`}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.action}</p>
                    <small>{item.affected_files.join(" · ")}</small>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="section-empty">没有从静态结果生成迁移动作。</p>
          )}
        </section>

        <section className="report-section export-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">PORTABLE OUTPUTS</p>
              <h2>导出与共享</h2>
            </div>
          </div>
          <p>
            报告与徽章均固定到当前 40 位提交哈希；项目更新后应重新扫描。
          </p>
          <div className="download-grid">
            <a aria-label="JSON" href={`${downloadBase}/report.json`}>
              <span>JSON</span>
              <small>结构化报告 ↓</small>
            </a>
            <a aria-label="Markdown" href={`${downloadBase}/report.md`}>
              <span>Markdown</span>
              <small>适合 Issue / PR ↓</small>
            </a>
            <a aria-label="Badge" href={`${downloadBase}/badge.svg`}>
              <span>Badge</span>
              <small>仓库状态徽章 ↗</small>
            </a>
          </div>
        </section>
      </div>

      {report.analysis_warnings.length ? (
        <section className="analysis-warnings" aria-labelledby="warnings-title">
          <h2 id="warnings-title">扫描范围提示</h2>
          <ul>
            {report.analysis_warnings.map((warning, index) => (
              <li key={`${warning.code}-${index}`}>
                <code>{warning.code}</code>
                <span>{warning.relative_path ?? "repository"}</span>
                <p>{warning.message}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <VerificationPanel report={report} onUpdated={onUpdated} />

      <div className="report-reset">
        <button className="secondary-button" onClick={onReset} type="button">
          扫描另一个仓库
        </button>
      </div>
    </div>
  );
}
