from __future__ import annotations

import warnings
from pathlib import Path

from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index

FIXTURE = Path("tests/fixtures/repositories/cuda_extension")


def test_extracts_dependencies_build_systems_and_cuda_extension_facts() -> None:
    facts = extract_project_facts(build_file_index(FIXTURE))

    assert {"torch", "flash-attn", "ninja"} <= facts.dependencies
    assert {"setuptools", "cmake"} <= facts.build_systems
    assert facts.flags["uses_torch_cuda_extension"] is True
    assert facts.flags["uses_cmake_cuda_language"] is True
    assert facts.flags["uses_cmake_torch_package"] is True
    assert facts.flags["references_cuda_home"] is True


def test_every_true_boolean_fact_has_deterministic_source_locations() -> None:
    facts = extract_project_facts(build_file_index(FIXTURE))

    for name, value in facts.flags.items():
        if value is True:
            assert facts.locations[f"fact:{name}"]

    cuda_extension = facts.locations["fact:uses_torch_cuda_extension"]
    assert cuda_extension[0].relative_path == "setup.py"
    assert cuda_extension[0].line > 0
    assert "CUDAExtension" in cuda_extension[0].evidence
    assert list(facts.locations) == sorted(facts.locations)


def test_fact_extraction_parses_but_never_executes_python_build_files(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "EXECUTED"
    (tmp_path / "setup.py").write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "from torch.utils.cpp_extension import CUDAExtension",
                "Path('EXECUTED').write_text('unsafe')",
                "extension = CUDAExtension('demo', ['kernel.cu'])",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["uses_torch_cuda_extension"] is True
    assert not marker.exists()


def test_python_facts_resolve_fully_qualified_and_aliased_torch_calls(
    tmp_path: Path,
) -> None:
    (tmp_path / "setup.py").write_text(
        "\n".join(
            [
                "import torch.utils.cpp_extension",
                "import torch.utils.cpp_extension as extension",
                "jit = torch.utils.cpp_extension.load('jit', ['kernel.cpp'])",
                "cpp = extension.CppExtension('cpp', ['kernel.cpp'])",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["uses_torch_cpp_extension_load"] is True
    assert facts.flags["uses_torch_cpp_extension"] is True


def test_apex_imports_set_the_imports_apex_fact(tmp_path: Path) -> None:
    (tmp_path / "train.py").write_text(
        "\n".join(
            [
                "import apex",
                "from apex import amp",
                "import apex.parallel",
                "import torch",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["imports_apex"] is True
    assert all(
        location.relative_path == "train.py"
        for location in facts.locations["fact:imports_apex"]
    )


def test_similar_module_names_do_not_set_the_imports_apex_fact(
    tmp_path: Path,
) -> None:
    (tmp_path / "train.py").write_text(
        "\n".join(
            [
                "import apex_docs",
                "from apex_utils import helpers",
                "import torch",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["imports_apex"] is False
    assert "fact:imports_apex" not in facts.locations


def test_shell_facts_ignore_comments_and_match_code_lines(tmp_path: Path) -> None:
    (tmp_path / "build.sh").write_text(
        "\n".join(
            [
                "# nvcc and nvidia-smi live under /usr/local/cuda",
                "nvcc -c kernel.cu",
                "nvidia-smi --query-gpu=name",
                'export CUDA_HOME="/usr/local/cuda"',
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["invokes_nvcc_directly"] is True
    assert facts.flags["invokes_nvidia_smi"] is True
    assert facts.flags["references_cuda_home"] is True
    assert facts.flags["uses_hardcoded_cuda_path"] is True
    assert [location.line for location in facts.locations["fact:invokes_nvcc_directly"]] == [2]


def test_shell_comment_lines_do_not_set_shell_facts(tmp_path: Path) -> None:
    (tmp_path / "build.sh").write_text(
        "\n".join(
            [
                "# nvcc would build this kernel",
                "# nvidia-smi reports device info",
                "# export CUDA_HOME=/usr/local/cuda",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["invokes_nvcc_directly"] is False
    assert facts.flags["invokes_nvidia_smi"] is False
    assert facts.flags["references_cuda_home"] is False
    assert facts.flags["uses_hardcoded_cuda_path"] is False


def test_requirement_parser_normalizes_names_and_ignores_include_options(
    tmp_path: Path,
) -> None:
    (tmp_path / "requirements-dev.txt").write_text(
        "\n".join(
            [
                "Flash_Attn[dev]>=2.0 ; platform_system == 'Linux'",
                "-r requirements-base.txt",
                "--index-url https://example.invalid/simple",
                "# comment",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.dependencies == frozenset({"flash-attn"})
    assert facts.locations["dependency:flash-attn"][0].relative_path == "requirements-dev.txt"


def test_python_fact_parsing_does_not_emit_repository_syntax_warnings(
    tmp_path: Path,
) -> None:
    (tmp_path / "setup.py").write_text(
        r'pattern = "\d"' + "\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        extract_project_facts(build_file_index(tmp_path))

    assert caught == []
