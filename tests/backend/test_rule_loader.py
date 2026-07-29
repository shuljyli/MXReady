from __future__ import annotations

from pathlib import Path

import pytest
from mxready.errors import MxReadyError
from mxready.models import Severity
from mxready.scanning.rule_loader import load_rule_catalog


def test_seed_rule_catalog_is_versioned_strict_and_unique() -> None:
    catalog = load_rule_catalog(Path("rules/v1"))

    assert catalog.version == "1"
    assert [rule.id for rule in catalog.rules] == [
        "MXR-TOOLCHAIN-001",
        "MXR-PATH-001",
        "MXR-PYTORCH-001",
        "MXR-DEPENDENCY-001",
    ]
    assert catalog.rules[0].severity is Severity.BLOCKER
    assert all(rule.recommendation for rule in catalog.rules)
    assert all(
        reference.url.startswith("https://")
        for rule in catalog.rules
        for reference in rule.references
    )


def test_invalid_rule_set_fails_with_stable_error() -> None:
    with pytest.raises(MxReadyError) as error:
        load_rule_catalog(Path("tests/fixtures/rules"))

    assert error.value.code == "RULESET_INVALID"


@pytest.mark.parametrize(
    "rule_document",
    [
        """
- id: MXR-TEST-001
  version: 1
  title: Invalid regex
  category: test
  severity: warning
  file_globs: ["**/*.py"]
  patterns:
    - type: regex
      expression: "["
  message: Invalid
  recommendation: Review it.
  references:
    - title: Primary
      url: https://example.com/docs
""",
        """
- id: MXR-TEST-001
  version: 1
  title: Insecure reference
  category: test
  severity: warning
  file_globs: ["**/*.py"]
  patterns:
    - type: fact
      name: uses_test
      equals: true
  message: Invalid
  recommendation: Review it.
  references:
    - title: Primary
      url: http://example.com/docs
""",
        """
- id: MXR-TEST-001
  version: 1
  title: Unknown field
  category: test
  severity: warning
  file_globs: ["**/*.py"]
  patterns:
    - type: dependency
      name: torch
  message: Invalid
  recommendation: Review it.
  references:
    - title: Primary
      url: https://example.com/docs
  unexpected_field: true
""",
    ],
)
def test_invalid_regex_reference_or_unknown_field_is_rejected(
    tmp_path: Path,
    rule_document: str,
) -> None:
    _write_catalog(tmp_path, rule_document)

    with pytest.raises(MxReadyError) as error:
        load_rule_catalog(tmp_path)

    assert error.value.code == "RULESET_INVALID"


def test_duplicate_rule_ids_are_rejected(tmp_path: Path) -> None:
    rule = """
- id: MXR-TEST-001
  version: 1
  title: Duplicate
  category: test
  severity: info
  file_globs: ["**/*.py"]
  patterns:
    - type: dependency
      name: torch
  message: Duplicate
  recommendation: Review it.
  references:
    - title: Primary
      url: https://example.com/docs
"""
    _write_catalog(tmp_path, rule + rule)

    with pytest.raises(MxReadyError) as error:
        load_rule_catalog(tmp_path)

    assert error.value.code == "RULESET_INVALID"


def _write_catalog(directory: Path, rule_document: str) -> None:
    (directory / "manifest.yml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                'ruleset_version: "test"',
                "rule_files: [core.yml]",
            ]
        ),
        encoding="utf-8",
    )
    (directory / "core.yml").write_text(rule_document, encoding="utf-8")
