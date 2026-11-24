import pytest

from mxready.models import ScanSource
from mxready.reporting.source import describe_source


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("git-commit", "干净 Git 提交"),
        ("working-tree", "工作区快照"),
        ("declared-directory", "显式声明目录"),
    ],
)
def test_source_labels_and_full_values(report_factory, kind, label):
    report = report_factory().model_copy(
        update={
            "source": ScanSource(
                kind=kind, actual_commit="a" * 40, dirty=False, input_digest="sha256:" + "d" * 64
            )
        }
    )
    view = describe_source(report)
    assert view.label == label
    assert ("已索引文件集合摘要", "sha256:" + "d" * 64) in view.fields


def test_unknown_incomplete_and_contradictory_sources(report_factory):
    report = report_factory()
    assert describe_source(report).label == "未记录来源元数据"
    source = ScanSource(kind="git-commit", dirty=True, actual_commit="b" * 40)
    assert describe_source(report.model_copy(update={"source": source})).label == "来源记录不一致"
    incomplete = describe_source(
        report.model_copy(update={"source": ScanSource(kind="git-commit")})
    )
    assert any("不完整" in warning for warning in incomplete.warnings)


def test_english_source_description(report_factory):
    report = report_factory()
    view = describe_source(report, "en")
    assert view.label == "Source metadata not recorded"
    assert ("Reported/declared commit", report.repository.commit) in view.fields
    assert ("Detected HEAD", "not recorded") in view.fields
    assert ("Worktree state", "unknown") in view.fields
