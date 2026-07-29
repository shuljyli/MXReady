from pathlib import Path

import pytest
from mxready.models import Severity
from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import load_rule_catalog

EXPECTED_RULES = {
    "MXR-TOOLCHAIN-001": Severity.BLOCKER,
    "MXR-PATH-001": Severity.WARNING,
    "MXR-PYTORCH-001": Severity.INFO,
    "MXR-DEPENDENCY-001": Severity.WARNING,
    "MXR-CMAKE-001": Severity.INFO,
    "MXR-CMAKE-002": Severity.WARNING,
    "MXR-ARCH-001": Severity.WARNING,
    "MXR-ARCH-002": Severity.WARNING,
    "MXR-TOOL-001": Severity.WARNING,
    "MXR-COMM-001": Severity.WARNING,
    "MXR-DEPENDENCY-002": Severity.WARNING,
    "MXR-DEPENDENCY-003": Severity.WARNING,
    "MXR-DEPENDENCY-004": Severity.BLOCKER,
    "MXR-HEADER-001": Severity.INFO,
    "MXR-HEADER-002": Severity.INFO,
    "MXR-INTRINSIC-001": Severity.WARNING,
    "MXR-KERNEL-001": Severity.WARNING,
    "MXR-GRAPH-001": Severity.WARNING,
    "MXR-BUILD-001": Severity.WARNING,
    "MXR-PYTORCH-002": Severity.INFO,
}
PRIMARY_SOURCE_PREFIXES = {
    "https://gitee.com/metax-maca/cu-bridge",
    "https://gitee.com/metax-maca/mxmaca-performance-tuning-guide",
    "https://docs.pytorch.org/docs/stable/cpp_extension.html",
    "https://cmake.org/cmake/help/latest/module/FindCUDAToolkit.html",
    "https://docs.nvidia.com/cuda/cuda-programming-guide/",
}
RULE_CASES = {
    "MXR-TOOLCHAIN-001": (
        "setup.py",
        'import subprocess\nsubprocess.run(["nvcc", "kernel.cu"], check=True)\n',
        (
            'compiler_documentation = "nvcc is described in the build guide"\n'
            "nvcc = _join_rocm_home('bin', 'hipcc')\n"
        ),
    ),
    "MXR-PATH-001": (
        "setup.py",
        'CUDA_HOME = "/usr/local/cuda"\n',
        "CUDA_HOME = discover_toolchain_path()\n",
    ),
    "MXR-PYTORCH-001": (
        "setup.py",
        (
            "from torch.utils.cpp_extension import CUDAExtension\n"
            "extension = CUDAExtension('demo', ['kernel.cu'])\n"
        ),
        'CUDAExtension_name = "documented symbol"\n',
    ),
    "MXR-DEPENDENCY-001": (
        "requirements.txt",
        "flash-attn==2.7.4\n",
        "flash-attention-docs==1.0\n",
    ),
    "MXR-CMAKE-001": (
        "CMakeLists.txt",
        "project(demo LANGUAGES CXX CUDA)\n",
        ("# project(fake LANGUAGES CXX CUDA)\nproject(demo LANGUAGES CXX)\n"),
    ),
    "MXR-CMAKE-002": (
        "CMakeLists.txt",
        "find_package(CUDAToolkit REQUIRED)\n",
        'set(CUDAToolkit_note "resolve the toolkit dynamically")\n',
    ),
    "MXR-ARCH-001": (
        "setup.py",
        'extra_args = ["-gencode=arch=compute_80,code=sm_80"]\n',
        'gencode_help = "select architecture dynamically"\n',
    ),
    "MXR-ARCH-002": (
        "setup.py",
        'target_arch = "sm_80"\n',
        "sm_count = 80\ncompute_units = detect_units()\n",
    ),
    "MXR-TOOL-001": (
        "diagnostics.py",
        'import subprocess\nsubprocess.run(["nvidia-smi"], check=True)\n',
        'diagnostic_documentation = "nvidia-smi is an NVIDIA utility"\n',
    ),
    "MXR-COMM-001": (
        "setup.py",
        'import os\nos.environ["NCCL_DEBUG"] = "INFO"\n',
        'NCCL_option_name = "selected at runtime"\n',
    ),
    "MXR-DEPENDENCY-002": (
        "requirements.txt",
        "bitsandbytes==0.46.0\n",
        "bits-and-bytes-docs==1.0\n",
    ),
    "MXR-DEPENDENCY-003": (
        "requirements.txt",
        "xformers==0.0.30\n",
        "transformers==4.55.0\n",
    ),
    "MXR-DEPENDENCY-004": (
        "setup.py",
        "import tensorrt\n",
        'backend_name = "tensorrt"\n',
    ),
    "MXR-HEADER-001": (
        "kernel.cu",
        "#include <cuda_runtime.h>\n",
        "// The cuda_runtime.h header is mentioned in this comment.\n",
    ),
    "MXR-HEADER-002": (
        "kernel.cu",
        '#include "cuda.h"\n',
        "#include <cuda_runtime.h>\n",
    ),
    "MXR-INTRINSIC-001": (
        "kernel.cu",
        "value = __shfl_sync(0xffffffff, value, 0);\n",
        "value = shfl_sync_helper(value);\n",
    ),
    "MXR-KERNEL-001": (
        "kernel.cu",
        "__global__ __launch_bounds__(256) void kernel() {}\n",
        "int launch_bounds_description = 256;\n",
    ),
    "MXR-GRAPH-001": (
        "kernel.cu",
        "cudaGraphCreate(&graph, 0);\n",
        'const char* graph_api_note = "cudaGraphCreate";\n',
    ),
    "MXR-BUILD-001": (
        "setup.py",
        'import os\nos.environ["TORCH_CUDA_ARCH_LIST"] = "8.0"\n',
        'TORCH_CUDA_ARCH_LIST_HELP = "choose targets dynamically"\n',
    ),
    "MXR-PYTORCH-002": (
        "setup.py",
        (
            "from torch.utils.cpp_extension import load\n"
            "module = load(name='demo', sources=['kernel.cpp'])\n"
        ),
        "from json import load\nmodule = load(open('metadata.json'))\n",
    ),
}


def test_mvp_rule_pack_has_exact_documented_inventory() -> None:
    catalog = load_rule_catalog(Path("rules/v1"))
    actual = {rule.id: rule.severity for rule in catalog.rules}

    assert actual == EXPECTED_RULES
    assert all(rule.references for rule in catalog.rules)
    assert all(
        any(reference.url.startswith(prefix) for prefix in PRIMARY_SOURCE_PREFIXES)
        for rule in catalog.rules
        for reference in rule.references
    )
    assert all(
        "复核" in rule.recommendation or "验证" in rule.recommendation for rule in catalog.rules
    )


@pytest.mark.parametrize("rule_id", RULE_CASES)
def test_each_rule_has_a_minimal_positive_case(
    tmp_path: Path,
    rule_id: str,
) -> None:
    filename, positive, _ = RULE_CASES[rule_id]
    (tmp_path / filename).write_text(positive, encoding="utf-8")

    findings = _evaluate(tmp_path)

    assert rule_id in {finding.rule_id for finding in findings}


@pytest.mark.parametrize("rule_id", RULE_CASES)
def test_each_rule_ignores_a_similar_negative_case(
    tmp_path: Path,
    rule_id: str,
) -> None:
    filename, _, negative = RULE_CASES[rule_id]
    (tmp_path / filename).write_text(negative, encoding="utf-8")

    findings = _evaluate(tmp_path)

    assert rule_id not in {finding.rule_id for finding in findings}


def test_combined_fixture_hits_all_rules_without_using_negative_python() -> None:
    root = Path("tests/fixtures/repositories/rule_cases")

    findings = _evaluate(root)

    assert {finding.rule_id for finding in findings} == set(EXPECTED_RULES)
    assert all(finding.relative_path != "negative.py" for finding in findings)


def _evaluate(root: Path):
    index = build_file_index(root)
    facts = extract_project_facts(index)
    return evaluate_rules(load_rule_catalog(Path("rules/v1")), index, facts)
