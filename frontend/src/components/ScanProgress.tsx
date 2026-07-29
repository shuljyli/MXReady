import type { ScanJob, ScanStatus } from "../api/types";

type ScanProgressProps = {
  job: ScanJob;
};

const stages: Array<{ status: ScanStatus; label: string }> = [
  { status: "queued", label: "任务排队" },
  { status: "cloning", label: "安全获取" },
  { status: "indexing", label: "源码索引" },
  { status: "analyzing", label: "规则分析" },
  { status: "completed", label: "生成报告" },
];

const stageIndex: Record<ScanStatus, number> = {
  queued: 0,
  cloning: 1,
  indexing: 2,
  analyzing: 3,
  completed: 4,
  failed: -1,
};

export function ScanProgress({ job }: ScanProgressProps) {
  const current = stageIndex[job.status];
  const repositoryName =
    job.repo_url.split("/").filter(Boolean).slice(-2).join("/") || job.repo_url;

  return (
    <section className="progress-panel" aria-labelledby="progress-title">
      <div className="progress-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="eyebrow">正在分析</p>
      <h2 id="progress-title">{repositoryName}</h2>
      <p className="stage-message" aria-live="polite">
        {job.stage_message}
      </p>

      <ol className="stage-list">
        {stages.map((stage, index) => {
          const state =
            job.status === "failed"
              ? "waiting"
              : index < current
                ? "done"
                : index === current
                  ? "active"
                  : "waiting";
          return (
            <li className={`stage stage-${state}`} key={stage.status}>
              <span className="stage-dot" aria-hidden="true" />
              <span>{stage.label}</span>
              <small>
                {state === "done"
                  ? "完成"
                  : state === "active"
                    ? "进行中"
                    : "等待"}
              </small>
            </li>
          );
        })}
      </ol>

      <p className="progress-note">
        仅下载受限大小的源码并做静态匹配，不执行安装脚本、构建命令或项目代码。
      </p>
    </section>
  );
}
