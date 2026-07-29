import type { Finding } from "../api/types";

type FindingCardProps = {
  finding: Finding;
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

export function FindingCard({ finding }: FindingCardProps) {
  return (
    <article className={`finding-card finding-${finding.severity}`}>
      <header className="finding-header">
        <div>
          <span className="finding-severity">
            {severityLabels[finding.severity]}
          </span>
          <span className="finding-rule">{finding.rule_id}</span>
        </div>
        <code className="finding-location">{lineLabel(finding)}</code>
      </header>

      <h3>{finding.title}</h3>
      <p className="finding-message">{finding.message}</p>
      <pre className="evidence-block">
        <code>{finding.evidence}</code>
      </pre>

      <div className="recommendation">
        <span>建议动作</span>
        <p>{finding.recommendation}</p>
      </div>

      {finding.references.length ? (
        <div className="finding-references">
          <span>依据</span>
          {finding.references.map((reference) => (
            <a
              href={reference.url}
              key={reference.url}
              rel="noreferrer"
              target="_blank"
            >
              {reference.title}
              <span aria-hidden="true">↗</span>
            </a>
          ))}
        </div>
      ) : null}
    </article>
  );
}
