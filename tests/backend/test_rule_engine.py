from __future__ import annotations

import re
from pathlib import Path

import pytest

from mxready.errors import MxReadyError
from mxready.models import Severity
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import IndexedFile, build_file_index
from mxready.scanning.rule_engine import (
    _FoldedCache,
    _passes_prefilter,
    _required_prefilter,
    evaluate_rules,
)
from mxready.scanning.rule_loader import load_rule_catalog, regex_flags

FIXTURE = Path("tests/fixtures/repositories/cuda_extension")


def test_rule_budget_stops_excessive_findings_instead_of_reporting_a_partial_pass():
    index = build_file_index(FIXTURE)
    with pytest.raises(MxReadyError) as error:
        evaluate_rules(
            load_rule_catalog(Path("src/mxready/resources/rules/v1")),
            index,
            extract_project_facts(index),
            max_findings=1,
        )
    assert error.value.code == "ANALYSIS_LIMIT_EXCEEDED"


def test_rule_time_budget_is_checked_between_patterns(monkeypatch):
    index = build_file_index(FIXTURE)
    clock = iter([0.0, 31.0])
    monkeypatch.setattr("mxready.scanning.rule_engine.time.monotonic", lambda: next(clock))
    with pytest.raises(MxReadyError) as error:
        evaluate_rules(
            load_rule_catalog(Path("src/mxready/resources/rules/v1")),
            index,
            extract_project_facts(index),
        )
    assert error.value.code == "ANALYSIS_LIMIT_EXCEEDED"


def test_regex_finding_has_line_evidence_and_migration_advice() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    findings = evaluate_rules(
        load_rule_catalog(Path("src/mxready/resources/rules/v1")), index, facts
    )

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
    findings = evaluate_rules(
        load_rule_catalog(Path("src/mxready/resources/rules/v1")), index, facts
    )

    cuda_extension = next(item for item in findings if item.rule_id == "MXR-PYTORCH-001")
    flash_attention = next(item for item in findings if item.rule_id == "MXR-DEPENDENCY-001")

    assert cuda_extension.relative_path == "setup.py"
    assert "CUDAExtension" in cuda_extension.evidence
    assert flash_attention.relative_path in {"pyproject.toml", "requirements.txt"}
    assert "flash-attn" in flash_attention.evidence


def test_findings_are_deduplicated_and_sorted_deterministically() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    findings = evaluate_rules(
        load_rule_catalog(Path("src/mxready/resources/rules/v1")), index, facts
    )

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
        load_rule_catalog(Path("src/mxready/resources/rules/v1")),
        build_file_index(FIXTURE),
        extract_project_facts(build_file_index(FIXTURE)),
    )

    assert any(
        item.rule_id == "MXR-PYTORCH-001" and item.relative_path == "setup.py" for item in findings
    )


def test_prefilter_does_not_change_findings_on_fixture_corpus() -> None:
    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    catalog = load_rule_catalog(Path("src/mxready/resources/rules/v1"))

    with_prefilter = evaluate_rules(catalog, index, facts)
    without_prefilter = evaluate_rules(catalog, index, facts, enable_prefilter=False)

    assert with_prefilter == without_prefilter


def test_prefilter_never_skips_a_file_that_the_regex_matches() -> None:
    """预过滤漏放会直接造成漏报：对每条规则正则逐一验证
    “完整正则命中 ⇒ 必需字面量判定放行”。"""
    corpus = [
        file.text for file in build_file_index(FIXTURE).files
    ] + [
        'subprocess.run(["nvcc", "-c", "kernel.cu"], check=True)\n',
        "nvidia-smi --query-gpu=name\n",
        "sm_86 -gencode arch=compute_86,code=sm_86\n",
        "os.environ['TORCH_CUDA_ARCH_LIST'] = '8.0'\n",
        "NVCC = /usr/local/cuda/bin/nvcc\n",
        "#include <cuda_runtime.h>\n#include <cublas_v2.h>\n",
        "__global__ void k(float* a) { __shfl_down_sync(0xffffffff, a[0], 1); }\n",
        "__launch_bounds__(256) __global__ void m() {}\n",
        "torch.distributed.init_process_group(backend='nccl')\n",
        "@pytest.mark.skipif(not torch.cuda.is_available(), reason='no gpu')\n",
        "@unittest.skipUnless(torch.cuda.is_available(), 'cuda')\n",
        "FROM nvidia/cuda:12.1.0-base-ubuntu22.04\nRUN --gpus all x\n",
        "cudaGraphLaunch(graph, stream); cudaMallocAsync(&p, n, s);\n",
        "cudaStreamCreate(&s); cudaMemcpyAsync(d, h, n, cudaMemcpyDeviceToHost, s);\n",
        "cudaSetDevice(0); cudaDeviceSynchronize();\n",
        "export NCCL_DEBUG=INFO\n",
        "os.environ['NCCL_P2P_DISABLE'] = '1'\n",
        "find_package(CUDAToolkit REQUIRED)\nfind_package(Torch REQUIRED)\n",
        "project(demo LANGUAGES CXX CUDA)\nenable_language(CUDA)\n",
        "trainer = GradScaler()\nwith autocast(enabled=True):\n    pass\n",
        "plain documentation text about migration without any markers\n",
        "CMAKE_CUDA_COMPILER=g++\n",
    ]
    catalog = load_rule_catalog(Path("src/mxready/resources/rules/v1"))

    for rule in catalog.rules:
        for pattern in rule.patterns:
            if pattern.type != "regex" or pattern.expression is None:
                continue
            flags = regex_flags(pattern.flags)
            compiled = re.compile(pattern.expression, flags)
            prefilter = _required_prefilter(pattern.expression, flags)
            if prefilter is None:
                continue
            for text in corpus:
                if compiled.search(text) is None:
                    continue
                allowed = _passes_prefilter(
                    prefilter,
                    IndexedFile("corpus.txt", len(text), "0" * 64, text),
                    _FoldedCache(),
                )
                assert allowed, (rule.id, pattern.expression, text)


def test_prefilter_extracts_expected_literals_for_core_rules() -> None:
    catalog = load_rule_catalog(Path("src/mxready/resources/rules/v1"))
    by_id = {rule.id: rule for rule in catalog.rules}

    nvcc_needle = _required_prefilter(
        by_id["MXR-PATH-001"].patterns[0].expression or "",
        re.NOFLAG,
    )
    assert nvcc_needle is not None
    assert [item.text for item in nvcc_needle] == ["/usr/local/cuda"]

    launch_bounds = _required_prefilter(
        by_id["MXR-KERNEL-001"].patterns[0].expression or "",
        re.NOFLAG,
    )
    assert launch_bounds is not None
    assert [item.text for item in launch_bounds] == ["__launch_bounds__"]

    branch_common = _required_prefilter(r"(?:sm_80|sm_86)\b", re.NOFLAG)
    assert branch_common is not None
    assert [item.text for item in branch_common] == ["sm_8"]

    # 分支无共同字面量且唯一片段过短时，预过滤退化为全量扫描而不是冒险。
    no_common = _required_prefilter(r"(?:sm|compute)_[0-9]{2,3}", re.NOFLAG)
    assert no_common is None


@pytest.mark.parametrize(
    "rule_id",
    [
        "MXR-ARCH-001",
        "MXR-DOCKER-001",
        "MXR-INTRINSIC-001",
        "MXR-PYTORCH-003",
        "MXR-RUNTIME-001",
    ],
)
def test_branch_only_rules_gain_a_prefilter(rule_id: str) -> None:
    """这些规则的每个分支都没有共同连续段，旧实现（集合交集）会整体放弃预过滤。"""
    catalog = load_rule_catalog(Path("src/mxready/resources/rules/v1"))
    by_id = {rule.id: rule for rule in catalog.rules}

    for pattern in by_id[rule_id].patterns:
        if pattern.type != "regex" or pattern.expression is None:
            continue
        prefilter = _required_prefilter(pattern.expression, regex_flags(pattern.flags))
        assert prefilter is not None, (rule_id, pattern.expression)
        assert len(prefilter) > 1, (rule_id, pattern.expression)
