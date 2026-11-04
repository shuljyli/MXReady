import { useId, useState } from "react";

import type { Finding } from "../api/types";
import { referenceUrl, toolExample } from "../lib/integration";
import { CopyButton } from "./CopyButton";
import { Icon } from "./Icon";

type FindingCardProps = {
  finding: Finding;
  repository?: { url: string; commit: string };
  onOpenRule?: (id: string, version: number) => void;
};

const severityLabels = {
  blocker: "阻塞",
  warning: "警告",
  info: "提示",
} as const;

function lineLabel(finding: Finding) {
  if (finding.line_start === finding.line_end) {
    return `${finding.relative_path}:${finding.line_start}`;
  }
  return `${finding.relative_path}:${finding.line_start}-${finding.line_end}`;
}

export function FindingCard({ finding, onOpenRule, repository }: FindingCardProps) {
  const occurrences = finding.occurrences?.length ? finding.occurrences : [finding];
  const sourceUrl = (line: number) => {
    if (!repository || !/^[0-9a-f]{40}$/.test(repository.commit)) return undefined;
    const base = referenceUrl(repository.url);
    if (!base) return undefined;
    return `${base.replace(/\.git$/, "").replace(/\/$/, "")}/blob/${repository.commit}/${finding.relative_path.split("/").map(encodeURIComponent).join("/")}#L${line}`;
  };
  const [expanded, setExpanded] = useState(true);
  const contentId = useId();
  const toggleLabel = `${expanded ? "收起" : "展开"}详情`;

  return (
    <article
      className={`finding-card finding-${finding.severity}${
        expanded ? "" : " finding-card-collapsed"
      }`}
    >
      <header className="finding-header">
        <h3 aria-label={finding.title}>
          <button
            aria-controls={contentId}
            aria-expanded={expanded}
            aria-label={`${toggleLabel}：${finding.title}`}
            className="finding-toggle"
            onClick={() => setExpanded((value) => !value)}
            type="button"
          >
            <span className="finding-badges">
              <span className="finding-severity">
                {severityLabels[finding.severity]}
              </span>
              <span className="finding-rule">{finding.rule_id}</span>
            </span>
            <code className="finding-location">{lineLabel(finding)}</code>
            <span className="finding-title">{finding.title}</span>
            <span
              aria-hidden="true"
              className={`finding-chevron${expanded ? " finding-chevron-open" : ""}`}
            >
              <Icon name="chevron" />
            </span>
          </button>
        </h3>
      </header>

      {expanded ? (
        <div className="finding-body" id={contentId}>
          <div className="finding-metadata">
            <span>分类：{finding.category} · 规则 v{finding.rule_version}</span>
            {finding.count > 1 ? <span>同规则在此文件聚合命中 {finding.count} 次</span> : null}
          </div>
          {finding.count > 1 && !finding.occurrences?.length ? <p className="muted">行号覆盖聚合范围，仅保留一段证据，不表示范围内每一行均命中。</p> : null}
          <p className="finding-message">{finding.message}</p>
          <details open={occurrences.length === 1}><summary>命中位置与证据（{occurrences.length}）</summary>
          {occurrences.map((occurrence, index) => <div key={index}>
            <p>{sourceUrl(occurrence.line_start) ? <a href={sourceUrl(occurrence.line_start)} target="_blank" rel="noreferrer">{finding.relative_path}:{occurrence.line_start}-{occurrence.line_end} · 查看固定提交源码</a> : `${finding.relative_path}:${occurrence.line_start}-${occurrence.line_end}`}</p>
            <pre className="evidence-block"><code>{occurrence.evidence}</code></pre>
          </div>)}
          </details>

          <div className="recommendation">
            <span>建议动作</span>
            <p>{finding.recommendation}</p>
          </div>

          {finding.references.length ? (
            <div className="finding-references">
              <span>依据</span>
              {finding.references.map((reference) => (
                referenceUrl(reference.url) ? <a
                  href={referenceUrl(reference.url)}
                  key={reference.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {reference.title}
                  <span aria-hidden="true">↗</span>
                </a> : <span key={reference.url}>{reference.title}（无有效 HTTPS 链接）</span>
              ))}
            </div>
          ) : null}
          <div className="inline-actions">
            {onOpenRule ? <button className="text-button compact-button" type="button"
              onClick={() => onOpenRule(finding.rule_id, finding.rule_version)}>查看当前规则 {finding.rule_id}</button> : null}
            <CopyButton label={"复制 " + finding.rule_id + " 解释参数"}
              text={toolExample("explain_rule", { rule_id: finding.rule_id })} />
          </div>
        </div>
      ) : null}
    </article>
  );
}
