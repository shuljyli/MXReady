"""Evaluate manually labeled source excerpts without downloading or executing code."""

import argparse
import hashlib
import json
from pathlib import Path

from mxready.resources import default_rules_directory
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import FileIndex, IndexedFile
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import load_rule_catalog


def evaluate(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = load_rule_catalog(default_rules_directory())
    false_positives: list[str] = []
    false_negatives: list[str] = []
    severity_changes: list[str] = []
    unreviewed: list[str] = []
    for case in manifest["cases"]:
        text = case["excerpt"]
        encoded = text.encode("utf-8")
        index = FileIndex(
            files=(
                IndexedFile(
                    relative_path=case["path"],
                    size=len(encoded),
                    sha256=hashlib.sha256(encoded).hexdigest(),
                    text=text,
                ),
            ),
            warnings=(),
        )
        actual = {
            finding.rule_id: str(finding.severity)
            for finding in evaluate_rules(catalog, index, extract_project_facts(index))
        }
        expected = {item["rule_id"]: item["severity"] for item in case["expected"]}
        false_positives.extend(
            f"{case['id']}:{rule}" for rule in case["forbidden"] if rule in actual
        )
        false_negatives.extend(f"{case['id']}:{rule}" for rule in expected if rule not in actual)
        severity_changes.extend(
            f"{case['id']}:{rule}:{actual[rule]}"
            for rule in expected
            if rule in actual and actual[rule] != expected[rule]
        )
        unreviewed.extend(
            f"{case['id']}:{rule}"
            for rule in actual
            if rule not in expected and rule not in case["forbidden"]
        )
    return {
        "cases": len(manifest["cases"]),
        "ruleset_digest": catalog.digest,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "severity_changes": severity_changes,
        "unreviewed": unreviewed,
        "scope": manifest["scope"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tests/fixtures/corpus/reviewed.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.manifest)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return int(
        bool(result["false_positives"] or result["false_negatives"] or result["severity_changes"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
