import type { ScanJob } from "../api/types";
import { CopyButton } from "./CopyButton";

export function TaskDetails({ job }: { job: ScanJob }) {
  return <details className="task-details"><summary>任务详情</summary>
    <dl className="detail-list">
      <div><dt>扫描 ID</dt><dd><code>{job.id}</code></dd></div>
      <div><dt>仓库</dt><dd>{job.repo_url}</dd></div>
      <div><dt>请求版本</dt><dd>{job.requested_ref ?? "默认分支"}</dd></div>
      <div><dt>实际提交</dt><dd><code>{job.resolved_commit ?? "等待解析"}</code></dd></div>
      <div><dt>创建时间</dt><dd>{new Date(job.created_at).toLocaleString("zh-CN", { hour12: false })}</dd></div>
      <div><dt>更新时间</dt><dd>{new Date(job.updated_at).toLocaleString("zh-CN", { hour12: false })}</dd></div>
    </dl>
    <CopyButton label="复制任务诊断信息" text={JSON.stringify(job, null, 2)} />
  </details>;
}
