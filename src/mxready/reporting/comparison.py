"""Conservative CI baseline policy: never silently compare different analyzers."""

from mxready.models import Finding, ScanReport, Severity


def new_blockers(baseline: ScanReport, current: ScanReport) -> list[Finding]:
    def normalize(url: str) -> str:
        return url.rstrip("/").removesuffix(".git").lower()

    if normalize(baseline.repository.url) != normalize(current.repository.url):
        raise ValueError("Baseline must describe the same repository")
    fields = (
        "ruleset_digest",
        "ruleset_version",
        "extra_ruleset_version",
        "tool_version",
        "analysis_config",
    )
    if not baseline.ruleset_digest or any(
        getattr(baseline, k) != getattr(current, k) for k in fields
    ):
        raise ValueError(
            "Baseline analysis conditions differ or ruleset digest is missing; regenerate it"
        )
    before = {(f.rule_id, f.relative_path): f for f in baseline.findings}
    result = []
    for finding in current.findings:
        old = before.get((finding.rule_id, finding.relative_path))
        if finding.severity == Severity.BLOCKER and (
            old is None or old.severity != Severity.BLOCKER or finding.count > old.count
        ):
            result.append(finding)
    return result
