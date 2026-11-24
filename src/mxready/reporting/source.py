"""Describe recorded provenance without probing the current filesystem or Git."""

from dataclasses import dataclass

from mxready.i18n import DEFAULT_LANGUAGE, tr
from mxready.models import ScanReport

_SOURCE_LABELS = {
    "zh": {
        "git-commit": (
            "干净 Git 提交",
            "报告记录的实际 HEAD；不代表签名、完整仓库或构建来源认证。",
        ),
        "working-tree": ("工作区快照", "HEAD 不包含未提交修改；扫描对象是当时纳入分析的内容。"),
        "declared-directory": ("显式声明目录", "仓库和提交由调用者声明，Git 来源未核对。"),
    },
    "en": {
        "git-commit": (
            "Clean Git commit",
            "Actual HEAD recorded in the report; not proof of signing, a complete repository, "
            "or build-source attestation.",
        ),
        "working-tree": (
            "Working-tree snapshot",
            "HEAD does not include uncommitted changes; the scan covered the content analyzed "
            "at that time.",
        ),
        "declared-directory": (
            "Declared directory",
            "Repository and commit were declared by the caller; Git provenance was not verified.",
        ),
    },
}
_MISSING_SOURCE = {
    "zh": (
        "未记录来源元数据",
        "可能是旧报告或未采集来源的扫描路径，无法推断为干净提交。",
    ),
    "en": (
        "Source metadata not recorded",
        "Possibly a legacy report or a scan path that did not capture source metadata; "
        "it cannot be inferred as a clean commit.",
    ),
}
_INCONSISTENT_LABEL = {"zh": "来源记录不一致", "en": "Inconsistent source record"}
_FIELDS = {
    "zh": (
        "报告关联/声明的提交",
        "探测到的 HEAD",
        "工作区状态",
        "已索引文件集合摘要",
    ),
    "en": (
        "Reported/declared commit",
        "Detected HEAD",
        "Worktree state",
        "Indexed file-set digest",
    ),
}
_VALUES = {
    "zh": {"missing": "未记录", "unknown": "未知", "dirty": "有修改", "clean": "无修改"},
    "en": {"missing": "not recorded", "unknown": "unknown", "dirty": "modified", "clean": "clean"},
}
_LABEL_EN = {
    label[0]: other[0]
    for label, other in zip(
        _SOURCE_LABELS["zh"].values(), _SOURCE_LABELS["en"].values(), strict=True
    )
} | {
    _MISSING_SOURCE["zh"][0]: _MISSING_SOURCE["en"][0],
    _INCONSISTENT_LABEL["zh"]: _INCONSISTENT_LABEL["en"],
}
_LABEL_ZH = {value: key for key, value in _LABEL_EN.items()}


@dataclass(frozen=True)
class SourceDescription:
    label: str
    explanation: str
    fields: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]


def localized_source_label(value: str, language: str) -> str:
    """Convert known cached source labels; leave unknown text untouched."""
    if language == "en":
        return _LABEL_EN.get(value, value)
    return _LABEL_ZH.get(value, value)


def describe_source(report: ScanReport, language: str = DEFAULT_LANGUAGE) -> SourceDescription:
    source = report.source
    language = "en" if language == "en" else "zh"
    labels = _SOURCE_LABELS[language]
    if source:
        label, explanation = labels[source.kind]
    else:
        label, explanation = _MISSING_SOURCE[language]
    warnings = []
    if source:
        if (source.kind == "git-commit" and source.dirty is True) or (
            source.actual_commit is not None and source.actual_commit != report.repository.commit
        ):
            label = _INCONSISTENT_LABEL[language]
            warnings.append(
                tr(
                    language,
                    "来源记录不一致：HEAD、关联提交或工作区状态矛盾。",
                    "Inconsistent source record: HEAD, associated commit, or worktree state "
                    "contradict each other.",
                )
            )
        if not source.input_digest or (
            source.kind != "declared-directory"
            and (source.actual_commit is None or source.dirty is None)
        ):
            warnings.append(
                tr(
                    language,
                    "来源记录不完整，缺少关键值。",
                    "Source record is incomplete and lacks key values.",
                )
            )
        if source.kind in {"working-tree", "declared-directory"}:
            warnings.append(
                tr(
                    language,
                    "文件集合摘要相同不代表硬件运行相同。",
                    "An identical file-set digest does not mean identical hardware execution.",
                )
            )
    commit_field, head_field, state_field, digest_field = _FIELDS[language]
    values = _VALUES[language]
    fields = (
        (commit_field, report.repository.commit),
        (
            head_field,
            source.actual_commit if source and source.actual_commit else values["missing"],
        ),
        (
            state_field,
            values["unknown"]
            if source is None or source.dirty is None
            else (values["dirty"] if source.dirty else values["clean"]),
        ),
        (
            digest_field,
            source.input_digest if source and source.input_digest else values["missing"],
        ),
    )
    return SourceDescription(label, explanation, fields, tuple(warnings))
