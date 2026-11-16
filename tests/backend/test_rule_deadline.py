"""A failed regex search must be interruptible even before its first match."""

import subprocess
import sys
import time

import pytest

from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import RuleCatalog, RulePattern, load_rule_catalog


def _delayed_worker(connection):
    time.sleep(2)
    connection.recv()
    connection.send((False, []))


def test_slow_worker_startup_cannot_block_a_large_input_send(monkeypatch):
    from mxready.scanning import regex_process

    monkeypatch.setattr(regex_process, "_search_worker", _delayed_worker)
    started = time.monotonic()
    with (
        pytest.raises(MxReadyError) as raised,
        regex_process.RegexMatcher(started + 0.2, 10) as matcher,
    ):
        matcher.search("cuda", 0, "a" * 1_000_000, ("kernel.cu", "0" * 64))
    assert raised.value.code == "ANALYSIS_LIMIT_EXCEEDED"
    assert time.monotonic() - started < 1.5


def test_default_rules_cannot_block_past_the_budget():
    probe = """
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.scanning.facts import ProjectFacts
from mxready.scanning.indexer import FileIndex, IndexedFile
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import load_rule_catalog
text = '\\n' * 30000 + '# nvcc\\n'
index = FileIndex(files=(IndexedFile('build.sh', len(text), '0'*64, text),), warnings=())
try:
    evaluate_rules(load_rule_catalog(Settings().rules_dir), index,
        ProjectFacts(frozenset(), frozenset(), {}, {}), timeout_seconds=0.3)
except MxReadyError as error:
    assert error.code == 'ANALYSIS_LIMIT_EXCEEDED'
else:
    raise AssertionError('Expected the bounded search to time out')
"""
    started = time.monotonic()
    with subprocess.Popen(
        [sys.executable, "-c", probe], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            pytest.fail("Default rule search ignored its deadline")
    assert process.returncode == 0, stdout + stderr
    assert time.monotonic() - started < 3


def test_timeout_does_not_poison_the_next_rule_evaluation(tmp_path):
    (tmp_path / "kernel.cu").write_text("a" * 40 + "!")
    index = build_file_index(tmp_path)
    facts = extract_project_facts(index)
    catalog = load_rule_catalog(Settings().rules_dir)
    dangerous = catalog.rules[0].model_copy(
        update={
            "file_globs": ["**/*.cu"],
            "patterns": [RulePattern(type="regex", expression="^(a+)+$")],
        }
    )
    with pytest.raises(MxReadyError) as raised:
        evaluate_rules(
            RuleCatalog(version="test", rules=[dangerous]), index, facts, timeout_seconds=0.5
        )
    assert raised.value.code == "ANALYSIS_LIMIT_EXCEEDED"
    assert evaluate_rules(catalog, index, facts) == []
