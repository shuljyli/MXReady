from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase

from mxready.models import Finding, Severity
from mxready.scanning.facts import ProjectFacts, SourceLocation
from mxready.scanning.indexer import FileIndex, IndexedFile
from mxready.scanning.rule_loader import (
    RuleCatalog,
    RuleDefinition,
    RulePattern,
    regex_flags,
)

_SEVERITY_ORDER = {
    Severity.BLOCKER: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


@dataclass(frozen=True, slots=True)
class _RuleMatch:
    location: SourceLocation
    line_end: int


def evaluate_rules(
    catalog: RuleCatalog,
    index: FileIndex,
    facts: ProjectFacts,
) -> list[Finding]:
    """Evaluate trusted rule data deterministically against a static index."""
    findings: dict[tuple[str, str, int, str], Finding] = {}

    for rule in catalog.rules:
        for pattern in rule.patterns:
            for match in _evaluate_pattern(rule, pattern, index, facts):
                finding = Finding(
                    rule_id=rule.id,
                    rule_version=rule.version,
                    severity=rule.severity,
                    category=rule.category,
                    title=rule.title,
                    relative_path=match.location.relative_path,
                    line_start=match.location.line,
                    line_end=match.line_end,
                    evidence=match.location.evidence[:240],
                    message=rule.message,
                    recommendation=rule.recommendation,
                    references=list(rule.references),
                )
                key = (
                    finding.rule_id,
                    finding.relative_path,
                    finding.line_start,
                    finding.evidence,
                )
                findings.setdefault(key, finding)

    return sorted(
        findings.values(),
        key=lambda item: (
            _SEVERITY_ORDER[item.severity],
            item.relative_path,
            item.line_start,
            item.rule_id,
        ),
    )


def _evaluate_pattern(
    rule: RuleDefinition,
    pattern: RulePattern,
    index: FileIndex,
    facts: ProjectFacts,
) -> list[_RuleMatch]:
    if pattern.type == "regex":
        return _evaluate_regex(rule, pattern, index)
    if pattern.type == "dependency":
        return _evaluate_dependency(rule, pattern, facts)
    return _evaluate_fact(rule, pattern, facts)


def _evaluate_regex(
    rule: RuleDefinition,
    pattern: RulePattern,
    index: FileIndex,
) -> list[_RuleMatch]:
    expression = pattern.expression
    if expression is None:
        return []
    compiled = re.compile(expression, regex_flags(pattern.flags))
    matches: list[_RuleMatch] = []

    for indexed_file in index.files:
        if not _matches_any_glob(indexed_file.relative_path, rule.file_globs):
            continue
        for regex_match in compiled.finditer(indexed_file.text):
            line_start = indexed_file.text.count("\n", 0, regex_match.start()) + 1
            last_character = max(regex_match.start(), regex_match.end() - 1)
            line_end = indexed_file.text.count("\n", 0, last_character) + 1
            matches.append(
                _RuleMatch(
                    location=SourceLocation(
                        relative_path=indexed_file.relative_path,
                        line=line_start,
                        evidence=_line_evidence(
                            indexed_file,
                            line_start,
                            line_end,
                        ),
                    ),
                    line_end=line_end,
                )
            )
    return matches


def _evaluate_dependency(
    rule: RuleDefinition,
    pattern: RulePattern,
    facts: ProjectFacts,
) -> list[_RuleMatch]:
    if pattern.name is None:
        return []
    name = _canonicalize_dependency(pattern.name)
    if name not in facts.dependencies:
        return []
    return _location_matches(
        facts.locations.get(f"dependency:{name}", ()),
        rule.file_globs,
    )


def _evaluate_fact(
    rule: RuleDefinition,
    pattern: RulePattern,
    facts: ProjectFacts,
) -> list[_RuleMatch]:
    if (
        pattern.name is None
        or pattern.name not in facts.flags
        or facts.flags[pattern.name] != pattern.equals
    ):
        return []
    return _location_matches(
        facts.locations.get(f"fact:{pattern.name}", ()),
        rule.file_globs,
    )


def _location_matches(
    locations: tuple[SourceLocation, ...],
    file_globs: list[str],
) -> list[_RuleMatch]:
    return [
        _RuleMatch(location=location, line_end=location.line)
        for location in locations
        if _matches_any_glob(location.relative_path, file_globs)
    ]


def _matches_any_glob(relative_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatchcase(relative_path, pattern):
            return True
        if pattern.startswith("**/") and fnmatchcase(relative_path, pattern[3:]):
            return True
    return False


def _line_evidence(
    indexed_file: IndexedFile,
    line_start: int,
    line_end: int,
) -> str:
    lines = indexed_file.text.splitlines()
    evidence = "\n".join(lines[line_start - 1 : line_end]).strip()
    return evidence[:240]


def _canonicalize_dependency(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()
