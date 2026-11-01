import { useState } from "react";

import type { ScanReport } from "../api/types";
import { agentHandoff, toolExample } from "../lib/integration";
import { CodeSnippet } from "./CodeSnippet";
import { CopyButton } from "./CopyButton";
import { PageHeading } from "./PageHeading";

const examples = {
  windows: { python: "C:\\path\\to\\python-env\\Scripts\\python.exe", data: "C:\\path\\to\\mxready-data" },
  unix: { python: "/path/to/python-env/bin/python", data: "/path/to/mxready-data" },
};

function absolutePath(value: string) {
  return /^(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\[^\\]+|\/)/.test(value.trim())
    && !/[\u0000-\u001f]/.test(value);
}

export function McpIntegration({ report }: { report?: ScanReport }) {
  const [platform, setPlatform] = useState<keyof typeof examples>("windows");
  const [python, setPython] = useState(examples.windows.python);
  const [data, setData] = useState(examples.windows.data);
  const [rules, setRules] = useState("");
  const [extraRules, setExtraRules] = useState("");
  const valid = [python, data, ...[rules, extraRules].filter(Boolean)].every(absolutePath);
  const config = JSON.stringify({ mcpServers: { mxready: {
    command: python.trim(), args: ["-m", "mxready.mcp.server"], env: {
      MXREADY_DATA_DIR: data.trim(),
      MXREADY_TEMP_DIR: data.trim().replace(/[\\/]+$/, "") + (platform === "windows" ? "\\tmp" : "/tmp"),
      ...(rules.trim() ? { MXREADY_RULES_DIR: rules.trim() } : {}),
      ...(extraRules.trim() ? { MXREADY_EXTRA_RULES_DIR: extraRules.trim() } : {}),
    },
  } } }, null, 2);

  const tools = [
    { name: "scan_repository", description: "扫描公开 GitHub / Gitee 仓库并等待结果。",
      parameters: "repo_url 必填；ref 默认 null；timeout_seconds 默认 300（30–1800）；max_findings 默认 20（1–500）。",
      args: { repo_url: report?.repository.url ?? "https://github.com/pytorch/extension-cpp",
        ref: report?.repository.commit ?? null, timeout_seconds: 300, max_findings: 20 } },
    { name: "get_report", description: "按扫描 ID 读取同一数据库里的已完成报告。",
      parameters: "scan_id 必填；max_findings 默认 50（1–500）。",
      args: { scan_id: report?.scan_id ?? "请替换为实际扫描 UUID", max_findings: 50 } },
    { name: "list_rules", description: "列出当前规则，可按分类和默认严重级别过滤。",
      parameters: "category、severity 默认 null；过滤不区分大小写；级别为 blocker / warning / info。",
      args: { category: null, severity: "blocker" } },
    { name: "explain_rule", description: "查看单条规则的判据、建议与一手资料。",
      parameters: "rule_id 必填，精确匹配。",
      args: { rule_id: "MXR-WARP-001" } },
  ];

  return <div className="feature-page">
    <PageHeading title="MCP 接入" description="让编码 Agent 根据文件、行号和静态证据制定迁移方案。" />
    <section className="report-section prose">
      <span className="status-label">stdio 接入方式</span>
      <h2>让 Agent 使用 MXReady</h2>
      <p>MCP 是模型上下文协议（Model Context Protocol）。支持该协议的编码 Agent 可调用下列四个工具。静态结果与真机验证分开，不提供兼容率。</p>
      <p>这里提供安装和配置说明。网页无法检测本机 MCP 依赖或客户端连接状态；Web 服务正常也不代表 MCP 已连接。</p>
    </section>

    {report ? <section className="report-section prose" aria-label="当前报告交接">
      <h2>交给 Agent 继续分析</h2><p>当前报告：{report.repository.owner}/{report.repository.name} · {report.repository.commit.slice(0, 12)}</p>
      <p>交接内容带完整提交、扫描 ID、报告地址和调用参数。未共享数据库时，使用固定提交重新扫描。</p>
      <CopyButton label="复制 Agent 交接内容" text={agentHandoff(report)} />
    </section> : null}

    <section className="report-section prose">
      <h2>1. 安装可选依赖</h2>
      <p>准备 Python 3.11+、Git 和独立 Python 环境。在源码根目录，激活目标环境后执行：</p>
      <CodeSnippet label="复制 MCP 安装命令" text={'python -m pip install -e ".[mcp]"'} />
      <p>由客户端启动 <code>mxready-mcp</code>。下方配置使用同一环境的 Python 绝对路径和 <code>-m mxready.mcp.server</code>，避免调用错误环境。日志写入 stderr，stdout 用于协议消息。</p>
    </section>

    <section className="report-section prose" aria-labelledby="mcp-config-title">
      <h2 id="mcp-config-title">2. 配置客户端</h2>
      <p>以下路径是示例，请替换为实际路径。适用于使用 <code>mcpServers</code> 配置格式的客户端，其他客户端需按自身格式转换。</p>
      <div className="form-grid">
        <label className="field">路径示例平台<select value={platform} onChange={(event) => {
          const next = event.target.value as keyof typeof examples;
          setPlatform(next); setPython(examples[next].python); setData(examples[next].data);
        }}><option value="windows">Windows</option><option value="unix">Linux / macOS</option></select></label>
        <label className="field">Python 可执行文件绝对路径<input value={python} spellCheck={false}
          onChange={(event) => setPython(event.target.value)} /></label>
        <label className="field">Web 与 MCP 共用的数据目录<input value={data} spellCheck={false}
          onChange={(event) => setData(event.target.value)} /></label>
        <label className="field">规则目录（可选，绝对路径）<input value={rules} placeholder="默认使用包内规则"
          onChange={(event) => setRules(event.target.value)} /></label>
        <label className="field">扩展规则目录（可选，绝对路径）<input value={extraRules}
          onChange={(event) => setExtraRules(event.target.value)} /></label>
      </div>
      {valid ? <CodeSnippet label="复制 MCP 配置" text={config} />
        : <p role="alert">请填写绝对路径，且不要包含换行或控制字符。</p>}
      <div className="notice">
        <strong>与 Web 共用报告时，先统一数据目录</strong>
        <p><code>mxready-serve</code> 默认使用系统用户数据目录；MCP 默认使用工作目录下的 <code>data/</code>。请为两端设置相同的 <code>MXREADY_DATA_DIR</code>，并保持规则与相关配置一致。</p>
        <p>两端须能访问同一个本地 SQLite 数据库。远程网页的地址不能替代磁盘目录；本机 MCP 也不能通过填写远程路径直接读取服务器数据库。网页不会读取或修改这些路径。</p>
      </div>
    </section>

    <section className="report-section prose" aria-label="MCP 工具目录">
      <h2>3. 四个可用工具</h2>
      <p>以下示例是工具名与参数说明，供客户端调用时参考，并非通用协议报文。</p>
      <div className="tool-list">{tools.map((tool) => <article className="tool-card" key={tool.name}>
        <h3>{tool.name}</h3><p>{tool.description}</p><p className="muted">{tool.parameters}</p>
        <CodeSnippet label={"复制 " + tool.name + " 参数"} text={toolExample(tool.name, tool.args)} />
      </article>)}</div>
      <p>扫描和报告工具按严重级别、路径、起始行排序；留意 <code>findings_truncated</code>、<code>returned_findings</code> 与 <code>total_findings</code>，默认返回可能只包含部分发现。</p>
    </section>

    <section className="report-section prose">
      <h2>排查接入问题</h2>
      <dl className="detail-list">
        <div><dt>找不到 mcp 模块</dt><dd>确认在配置指定的 Python 环境中安装了可选依赖。</dd></div>
        <div><dt>SCAN_NOT_FOUND</dt><dd>核对扫描 ID，以及两端实际使用的数据目录是否相同。</dd></div>
        <div><dt>SCAN_TIMEOUT</dt><dd>等待超时不会取消扫描。保留错误中的扫描 ID，稍后使用 get_report 查询。</dd></div>
        <div><dt>SCAN_NOT_COMPLETED</dt><dd>报告尚未完成，稍后重查；失败或中断任务需要新建扫描。</dd></div>
      </dl>
      <p>现有服务仅提供 stdio MCP，不提供网页 HTTP/SSE 连接地址。MCP 不运行仓库代码；真机执行继续使用人工审阅的 runner。</p>
    </section>
  </div>;
}
