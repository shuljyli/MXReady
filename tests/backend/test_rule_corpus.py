from pathlib import Path
from runpy import run_path


def test_reviewed_source_excerpts_have_no_labeled_regressions():
    namespace = run_path(str(Path("scripts/evaluate_rule_corpus.py")))
    result = namespace["evaluate"](Path("tests/fixtures/corpus/reviewed.json"))
    assert result["cases"] == 4
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert result["severity_changes"] == []
