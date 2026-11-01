import { useEffect, useRef, useState } from "react";

import type { RuleCatalog } from "../api/types";
import { referenceUrl, toolExample } from "../lib/integration";
import { CopyButton } from "./CopyButton";
import { PageHeading } from "./PageHeading";

type Props = {
  catalog: RuleCatalog | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selectedRule?: string;
  historicalVersion?: number;
};

const labels = { blocker: "阻塞", warning: "警告", info: "提示" };

export function RuleCatalogView({ catalog, loading, error, onRetry, selectedRule, historicalVersion }: Props) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState("");
  const selected = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (selectedRule) {
      setSearch(""); setCategory(""); setSeverity("");
      selected.current?.focus();
    }
  }, [selectedRule, catalog]);
  const categories = [...new Set(catalog?.rules.map((rule) => rule.category))].sort();
  const query = search.trim().toLocaleLowerCase();
  const visible = catalog?.rules.filter((rule) => (!category || rule.category === category)
    && (!severity || rule.severity === severity)
    && `${rule.id} ${rule.title}`.toLocaleLowerCase().includes(query)) ?? [];
  const selectedDefinition = catalog?.rules.find((rule) => rule.id === selectedRule);

  return <div className="feature-page">
    <PageHeading title="规则库" description="查看当前服务加载的迁移检查规则、判据与资料依据。" />
    <section className="report-section prose">
      {loading ? <p role="status">正在加载规则库…</p> : null}
      {error ? <div role="alert"><p>{error}</p><button className="secondary-button" onClick={onRetry}>重试加载规则</button></div> : null}
      {catalog ? <>
        <p>当前规则集 v{catalog.version} · {catalog.rules.length} 项{catalog.extra_version ? ` · 扩展规则 ${catalog.extra_version}` : ""}</p>
        <p className="muted">这里展示规则默认级别。历史报告的级别可能受路径上下文和工具链画像影响，应以报告证据与版本为准。</p>
        {selectedRule && !selectedDefinition ? <p role="status">当前规则库未包含 {selectedRule}，请以历史报告中的说明为准。</p> : null}
        <div className="filter-grid">
          <label className="field">搜索规则<input value={search} type="search" placeholder="规则 ID 或标题" onChange={(event) => setSearch(event.target.value)} /></label>
          <label className="field">规则分类<select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">全部分类</option>{categories.map((value) => <option key={value}>{value}</option>)}
          </select></label>
          <label className="field">规则严重级别<select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="">全部级别</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
        </div>
        <p role="status">显示 {visible.length} / {catalog.rules.length} 条规则</p>
      </> : null}
    </section>
    {catalog ? <section className="rule-list" aria-label="规则列表">
      {visible.map((rule) => <details className="report-section rule-detail" key={rule.id}
        ref={rule.id === selectedRule ? selected : undefined} tabIndex={-1}
        open={rule.id === selectedRule ? true : undefined}>
        <summary><span className="rule-summary"><code>{rule.id}</code><strong>{rule.title}</strong>
          <span className="status-label">{labels[rule.severity]}</span><small>{rule.category} · v{rule.version}</small></span></summary>
        <div className="prose">
          {rule.id === selectedRule && historicalVersion !== undefined && historicalVersion !== rule.version
            ? <p className="notice">历史报告使用 v{historicalVersion}，当前规则为 v{rule.version}。以下为当前规则定义，不会覆盖历史发现。</p> : null}
          <p>{rule.message}</p><p><strong>建议：</strong>{rule.recommendation}</p>
          <dl className="detail-list">
            <div><dt>适用文件</dt><dd>{rule.file_globs.join(" · ")}</dd></div>
            <div><dt>依据状态</dt><dd>{rule.confidence === "documented" ? "有资料依据" : "需人工复核"}</dd></div>
            <div><dt>更新时间</dt><dd>{rule.updated ?? "未记录"}</dd></div>
          </dl>
          <ul>{rule.references.map((reference) => <li key={reference.url}>{referenceUrl(reference.url)
            ? <a href={referenceUrl(reference.url)} target="_blank" rel="noreferrer">{reference.title}</a>
            : <span>{reference.title}（无有效 HTTPS 链接）</span>}</li>)}</ul>
          <CopyButton label={"复制 " + rule.id + " 的 MCP 解释参数"} text={toolExample("explain_rule", { rule_id: rule.id })} />
          <details><summary>匹配模式技术详情</summary><pre className="technical-output"><code>{JSON.stringify(rule.patterns, null, 2)}</code></pre></details>
        </div>
      </details>)}
      {!visible.length ? <p className="report-section">没有匹配的规则</p> : null}
    </section> : null}
  </div>;
}
