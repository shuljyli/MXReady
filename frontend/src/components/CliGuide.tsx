import { CodeSnippet } from "./CodeSnippet";
import { PageHeading } from "./PageHeading";

export function CliGuide() {
  return <div className="feature-page">
    <PageHeading title="命令行使用" description="在自己的主机分析本地目录，或逐仓评估多个公开仓库。" />
    <section className="report-section prose"><h2>本地目录扫描</h2>
      <p>安装 MXReady 后，在用户控制的主机运行。把示例目录、公开仓库地址和完整提交替换为实际值；不会执行仓库代码。</p>
      <CodeSnippet label="复制本地扫描命令" text={"mxready-scan ./my-project --repo-url https://github.com/owner/repository --commit " + "d".repeat(40) + " --output data/reports"} />
      <p>输出 JSON、Markdown 和 SVG。退出码：0 为无阻塞项，2 为存在阻塞项，1 为操作失败。</p>
    </section>
    <section className="report-section prose"><h2>批量评估</h2>
      <p>创建 UTF-8 文本清单 repos.txt，每行一个公开仓库 URL，可跟分支、标签或完整提交；支持 # 注释。</p>
      <pre className="technical-output"><code>{"https://github.com/pytorch/extension-cpp main\n# 添加其他公开仓库"}</code></pre>
      <CodeSnippet label="复制批量扫描命令" text="mxready-scan-batch repos.txt --output data/batch" />
      <p>生成逐仓报告与 batch-summary.csv / batch-summary.md。退出码：0 为全部成功且无阻塞，2 为存在阻塞仓库，1 为存在扫描失败。</p>
    </section>
    <section className="report-section prose"><h2>输入和报告范围</h2>
      <p>Web 界面一次扫描一个公开仓库 URL。本地目录和批量清单交给对应 CLI；网页不接收源码 ZIP。runner 的 result.json 是验证结果，不是源码输入。</p>
      <p>CLI 写出的报告文件不会自动进入 Web 数据库。静态结果不等于沐曦硬件认证。</p>
    </section>
  </div>;
}
