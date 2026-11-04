import pytest

from mxready.models import Finding, Severity


def test_baseline_new_blockers_include_escalation_and_count_growth(report_factory):
    from mxready.reporting.comparison import new_blockers

    f = Finding(
        rule_id="MXR-TEST-001",
        rule_version=1,
        severity=Severity.WARNING,
        category="test",
        title="test",
        relative_path="a.cu",
        line_start=1,
        line_end=1,
        evidence="old",
        message="test",
        recommendation="test",
        references=[],
    )
    before = report_factory(findings=[f]).model_copy(
        update={"ruleset_digest": "sha256:" + "a" * 64}
    )
    after = before.model_copy(
        update={
            "findings": [f.model_copy(update={"severity": Severity.BLOCKER, "evidence": "new"})]
        }
    )
    assert len(new_blockers(before, after)) == 1
    assert not new_blockers(after, after)
    grown = after.model_copy(
        update={"findings": [after.findings[0].model_copy(update={"count": 2})]}
    )
    assert len(new_blockers(after, grown)) == 1
    with pytest.raises(ValueError, match="conditions"):
        new_blockers(before, after.model_copy(update={"tool_version": "other"}))
    with pytest.raises(ValueError, match="repository"):
        new_blockers(
            before,
            after.model_copy(
                update={
                    "repository": after.repository.model_copy(
                        update={"url": "https://github.com/another/repo"}
                    )
                }
            ),
        )


def test_cli_baseline_keeps_full_report_and_changes_only_exit_policy(tmp_path):
    import json

    from mxready.cli.scan_repository import main

    args = [
        "tests/fixtures/repositories/cuda_extension",
        "--repo-url",
        "https://github.com/example/project",
        "--commit",
        "a" * 40,
        "--output",
        str(tmp_path / "before"),
    ]
    assert main(args) == 2
    baseline = tmp_path / "before" / ("project-" + "a" * 12 + ".json")
    args[-1] = str(tmp_path / "after")
    assert main([*args, "--baseline", str(baseline), "--fail-on", "new-blockers"]) == 0
    current = json.loads((tmp_path / "after" / baseline.name).read_text(encoding="utf-8"))
    assert current["summary"]["blocker_count"] > 0
    assert current["static_status"] == "blocked"
    assert main([*args, "--fail-on", "new-blockers"]) == 1
