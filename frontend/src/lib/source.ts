import type { ScanReport } from "../api/types";

export function describeSource(report: ScanReport) {
  const source = report.source;
  const labels = {
    "git-commit": ["干净 Git 提交", "报告记录的实际 HEAD；不代表签名、完整仓库或构建来源认证。"],
    "working-tree": ["工作区快照", "HEAD 不包含未提交修改；扫描对象是当时纳入分析的内容。"],
    "declared-directory": ["显式声明目录", "仓库和提交由调用者声明，Git 来源未核对。"],
  } as const;
  const [initialLabel, explanation] = source ? labels[source.kind]
    : ["未记录来源元数据", "可能是旧报告或未采集来源的扫描路径，无法推断为干净提交。"];
  const inconsistent = !!source && ((source.kind === "git-commit" && source.dirty === true)
    || (!!source.actual_commit && source.actual_commit !== report.repository.commit));
  const warnings: string[] = [];
  if (inconsistent) warnings.push("HEAD、关联提交或工作区状态矛盾。");
  if (source && (!source.input_digest || (source.kind !== "declared-directory"
    && (!source.actual_commit || source.dirty == null)))) warnings.push("来源记录不完整，缺少关键值。");
  if (source && source.kind !== "git-commit") warnings.push("文件集合摘要相同不代表硬件运行相同。");
  return { label: inconsistent ? "来源记录不一致" : initialLabel, explanation, warnings };
}

export function sourceLinkLabel(source: ScanReport["source"] | undefined, commit: string | undefined) {
  if (source?.kind === "working-tree") return "查看关联提交（可能与工作区不同）";
  if (source?.kind === "declared-directory") return "声明提交（未核对来源）";
  if (!source) return "查看固定提交源码（来源未记录）";
  if (source.dirty !== false || !source.actual_commit || source.actual_commit !== commit)
    return "查看关联提交（来源异常或不完整）";
  return "查看固定提交源码";
}
