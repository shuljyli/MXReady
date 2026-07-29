from __future__ import annotations

from pathlib import Path

from mxready.models import Severity
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import load_rule_catalog

FIXTURE = Path("tests/fixtures/repositories/cuda_extension")


def test_regex_finding_has_line_evidence_and_migration_advice() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    findings = evaluate_rules(load_rule_catalog(Path("rules/v1")), index, facts)

    direct_nvcc = next(item for item in findings if item.rule_id == "MXR-TOOLCHAIN-001")
    assert direct_nvcc.relative_path == "setup.py"
    assert direct_nvcc.line_start > 0
    assert direct_nvcc.line_end >= direct_nvcc.line_start
    assert "nvcc" in direct_nvcc.evidence.casefold()
    assert len(direct_nvcc.evidence) <= 240
    assert direct_nvcc.recommendation
    assert direct_nvcc.references


def test_dependency_and_fact_patterns_use_structured_source_locations() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    findings = evaluate_rules(load_rule_catalog(Path("rules/v1")), index, facts)

    cuda_extension = next(item for item in findings if item.rule_id == "MXR-PYTORCH-001")
    flash_attention = next(item for item in findings if item.rule_id == "MXR-DEPENDENCY-001")

    assert cuda_extension.relative_path == "setup.py"
    assert "CUDAExtension" in cuda_extension.evidence
    assert flash_attention.relative_path in {"pyproject.toml", "requirements.txt"}
    assert "flash-attn" in flash_attention.evidence


def test_findings_are_deduplicated_and_sorted_deterministically() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    findings = evaluate_rules(load_rule_catalog(Path("rules/v1")), index, facts)

    severity_order = {
        Severity.BLOCKER: 0,
        Severity.WARNING: 1,
        Severity.INFO: 2,
    }
    sort_keys = [
        (
            severity_order[item.severity],
            item.relative_path,
            item.line_start,
            item.rule_id,
        )
        for item in findings
    ]
    deduplication_keys = {
        (item.rule_id, item.relative_path, item.line_start, item.evidence) for item in findings
    }

    assert sort_keys == sorted(sort_keys)
    assert len(deduplication_keys) == len(findings)


def test_root_level_files_match_double_star_globs() -> None:
    findings = evaluate_rules(
        load_rule_catalog(Path("rules/v1")),
        build_file_index(FIXTURE),
        extract_project_facts(build_file_index(FIXTURE)),
    )

    assert any(
        item.rule_id == "MXR-PYTORCH-001" and item.relative_path == "setup.py" for item in findings
    )
