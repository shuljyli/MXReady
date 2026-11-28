import pytest

from mxready.models import CompatibleAlternative, Finding, FindingOccurrence, Severity
from mxready.tui.commands import parse_command
from mxready.tui.report_browser import FindingFilter, browse, matching_indices


def finding(**updates):
    values = dict(
        rule_id="MXR-WARP-001",
        rule_version=1,
        severity="blocker",
        category="warp",
        title="Straße 内核",
        relative_path="Csrc/Kernel.cu",
        line_start=1,
        line_end=1,
        evidence="primary",
        message="说明",
        recommendation="整改",
        references=[],
    )
    return Finding(**(values | updates))


def test_full_evidence_unicode_and_literal_path_filters_are_pure(report_factory):
    item = finding(
        occurrences=[FindingOccurrence(line_start=2, line_end=2, evidence="x" * 800 + "NEEDLE")]
    )
    report = report_factory(findings=[item, finding(relative_path="other.cu")])
    original = report.model_dump_json()
    filters = FindingFilter(Severity.BLOCKER, "MXR-WARP-001", "csrc\\", "needle")
    assert matching_indices(report, filters) == (0,)
    assert matching_indices(report, FindingFilter(text_query="STRASSE")) == (0, 1)
    assert report.model_dump_json() == original


def test_browse_retains_conditions_and_commits_only_valid_pages(report_factory):
    report = report_factory(findings=[finding(relative_path=f"{i}.cu") for i in range(12)])
    filters, page, indices = browse(report, FindingFilter(), 1, parse_command("/findings 2"))
    assert page.indices == (5, 6, 7, 8, 9)
    assert browse(report, filters, 2, parse_command("/findings"), indices)[1].page == 2
    filters, page, _ = browse(report, filters, 2, parse_command('/findings --query "missing"'))
    assert (page.page, page.page_count, page.matched_total, page.report_total) == (1, 1, 0, 12)
    with pytest.raises(ValueError, match="1-1"):
        browse(report, filters, 1, parse_command("/findings 2"))
    assert browse(report, filters, 10, parse_command("/findings"), restore=True)[1].page == 1


@pytest.mark.parametrize(
    "value",
    [
        "/findings 0",
        "/findings -1",
        "/findings nope",
        "/findings --reset 2",
        "/findings --reset --query x",
        "/findings --severity bad",
        "/findings --query " + "x" * 257,
    ],
)
def test_filter_validation_is_atomic(value):
    with pytest.raises(ValueError):
        parse_command(value)


def test_filter_clear_and_rule_normalization():
    command = parse_command('/findings --rule " mxr-warp-001 " --file "" --severity all')
    assert command.rule == "MXR-WARP-001" and command.file == "" and command.severity == "all"


def test_text_filter_matches_compatible_alternatives(report_factory):
    with_alt = finding(
        compatible_alternatives=[
            CompatibleAlternative(
                operator="scaled_dot_product_attention",
                summary="Cross-platform attention kernel",
                applies_when="Standard attention",
                caveat="Verify parity",
            )
        ]
    )
    report = report_factory(findings=[with_alt, finding(relative_path="plain.cu")])
    assert matching_indices(report, FindingFilter(text_query="scaled_dot_product_attention")) == (
        0,
    )
    assert matching_indices(report, FindingFilter(text_query="cross-platform")) == (0,)
