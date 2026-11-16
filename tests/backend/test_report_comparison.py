import json
from pathlib import Path

import pytest
from test_tui_report_browser import finding

from mxready.reporting.comparison import compare_reports, new_blockers


def test_diff_order_identity_changes_and_unknown_conditions(report_factory):
    before = report_factory(findings=[finding(), finding(relative_path="gone.cu")])
    current = report_factory(
        findings=[
            finding(count=3, severity="warning", line_start=10, line_end=10),
            finding(relative_path="new.cu"),
        ]
    )
    result = compare_reports(before, current)
    assert [f.relative_path for f in result.added] == ["new.cu"]
    assert [f.relative_path for f in result.removed] == ["gone.cu"]
    assert len(result.retained) == len(result.changes) == 1
    assert result.changes[0].severity_changed and result.changes[0].count_changed
    assert result.conditions_status == "unknown"
    with pytest.raises(ValueError, match="conditions"):
        new_blockers(before, current)


def test_known_changes_take_precedence_and_config_order_is_irrelevant(report_factory):
    before = report_factory().model_copy(update={"analysis_config": {"a": 1, "b": 2}})
    current = report_factory().model_copy(update={"analysis_config": {"b": 2, "a": 1}})
    assert compare_reports(before, current).conditions_status == "unknown"
    changed = current.model_copy(update={"tool_version": "other"})
    assert compare_reports(before, changed).conditions_status == "different"
    assert compare_reports(before, changed).condition_differences[0].field == "tool_version"


def test_ambiguous_keys_repository_and_scan_identity_are_rejected(report_factory):
    baseline = report_factory(findings=[finding()])
    with pytest.raises(ValueError, match="重复"):
        compare_reports(baseline, report_factory(findings=[finding(), finding()]))
    with pytest.raises(ValueError, match="仓库"):
        compare_reports(baseline, report_factory(repository_name="other"))
    with pytest.raises(ValueError, match="身份冲突"):
        compare_reports(baseline, baseline.model_copy(update={"tool_version": "other"}))
    assert not compare_reports(baseline, baseline).added


@pytest.mark.parametrize(
    "case",
    json.loads(Path("frontend/src/test/report-comparison-cases.json").read_text()),
    ids=lambda case: case["name"],
)
def test_shared_web_comparison_semantics(case, report_factory):
    def report(side, conditions):
        return report_factory(
            findings=[finding(**(item | {"line_end": item["line_start"]})) for item in case[side]]
        ).model_copy(update={"ruleset_digest": "sha256:" + "d" * 64, **case[conditions]})

    result = compare_reports(
        report("before", "conditions_before"), report("after", "conditions_after")
    )
    expected = case["expected"]
    assert [len(result.added), len(result.removed), len(result.retained)] == [
        expected["added"],
        expected["removed"],
        expected["retained"],
    ]
    assert sum(change.severity_changed for change in result.changes) == expected["severity"]
    assert sum(change.count_changed for change in result.changes) == expected["count"]
    assert (result.conditions_status == "different") == expected["conditions_changed"]
