"""Describe recorded provenance without probing the current filesystem or Git."""

from dataclasses import dataclass

from mxready.models import ScanReport


@dataclass(frozen=True)
class SourceDescription:
    label: str
    explanation: str
    fields: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]


def describe_source(report: ScanReport) -> SourceDescription:
    source = report.source
    labels = {
        "git-commit": (
            "干净 Git 提交",
            "报告记录的实际 HEAD；不代表签名、完整仓库或构建来源认证。",
        ),
        "working-tree": ("工作区快照", "HEAD 不包含未提交修改；扫描对象是当时纳入分析的内容。"),
        "declared-directory": ("显式声明目录", "仓库和提交由调用者声明，Git 来源未核对。"),
    }
    label, explanation = (
        labels[source.kind]
        if source
        else ("未记录来源元数据", "可能是旧报告或未采集来源的扫描路径，无法推断为干净提交。")
    )
    warnings = []
    if source:
        if (source.kind == "git-commit" and source.dirty is True) or (
            source.actual_commit is not None and source.actual_commit != report.repository.commit
        ):
            label = "来源记录不一致"
            warnings.append("来源记录不一致：HEAD、关联提交或工作区状态矛盾。")
        if not source.input_digest or (
            source.kind != "declared-directory"
            and (source.actual_commit is None or source.dirty is None)
        ):
            warnings.append("来源记录不完整，缺少关键值。")
        if source.kind in {"working-tree", "declared-directory"}:
            warnings.append("文件集合摘要相同不代表硬件运行相同。")
    fields = (
        ("报告关联/声明的提交", report.repository.commit),
        ("探测到的 HEAD", source.actual_commit if source and source.actual_commit else "未记录"),
        (
            "工作区状态",
            "未知"
            if source is None or source.dirty is None
            else ("有修改" if source.dirty else "无修改"),
        ),
        ("已索引文件集合摘要", source.input_digest if source and source.input_digest else "未记录"),
    )
    return SourceDescription(label, explanation, fields, tuple(warnings))
