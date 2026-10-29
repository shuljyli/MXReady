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
        location.relative_path == "train.py" for location in facts.locations["fact:imports_apex"]
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


def test_cmake_comment_lines_do_not_set_cuda_home_reference(tmp_path: Path) -> None:
    """被注释掉的 `# set(CUDA_HOME ...)` 不是真引用，检测必须走剥离注释后的文本。"""
    (tmp_path / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(demo LANGUAGES CXX CUDA)",
                '# set(CUDA_HOME "/usr/local/cuda-12.1")',
                "# include_directories(${CUDA_HOME}/include)",
                'message(STATUS "no cuda home referenced here")',
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.flags["uses_cmake_cuda_language"] is True
    assert facts.flags["references_cuda_home"] is False
    assert "fact:references_cuda_home" not in facts.locations


def test_cmake_code_lines_still_set_cuda_home_reference(tmp_path: Path) -> None:
    """剥离注释不能把真引用一起剥掉，且 evidence 要指向原文那一行。"""
    (tmp_path / "CMakeLists.txt").write_text(
        "\n".join(
            [
                '# set(CUDA_HOME "/usr/local/cuda-11.8")  # 旧版本，已废弃',
                "project(demo LANGUAGES CXX CUDA)",
                'set(CUDA_HOME "/usr/local/cuda-12.1")',
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    locations = facts.locations["fact:references_cuda_home"]
    assert [location.line for location in locations] == [3]
    assert 'set(CUDA_HOME "/usr/local/cuda-12.1")' in locations[0].evidence


def test_large_pyproject_dependency_line_numbers_stay_accurate(tmp_path: Path) -> None:
    """依赖定位由逐行扫描改为整篇折叠查找后，行号必须仍逐条对得上、evidence 不串行。"""
    dependencies = [f"package-{index}>=1.0.{index}" for index in range(120)]
    body = "\n".join(f'  "{item}",' for item in dependencies)
    text = '[project]\nname = "demo"\ndependencies = [\n' + body + "\n]\n"
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")

    facts = extract_project_facts(build_file_index(tmp_path))

    for offset, name in enumerate(f"package-{index}" for index in range(120)):
        location = facts.locations[f"dependency:{name}"][0]
        assert location.line == 4 + offset, name
        assert name in location.evidence

    # 尾部依赖不能被定位回文件开头
    assert facts.locations["dependency:package-119"][0].line == 123


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


def test_setup_py_keyword_dependencies_are_extracted_without_execution(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        "\n".join(
            [
                "from setuptools import setup",
                "from torch.utils.cpp_extension import CUDAExtension",
                "setup(",
                "    name='demo',",
                "    install_requires=['torch>=2.0', 'Flash_Attn[dev]'],",
                "    extras_require={'dev': ['ninja', 'tensorrt==10.0']},",
                "    ext_modules=[CUDAExtension('demo', ['kernel.cu'])],",
                ")",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert {"torch", "flash-attn", "ninja", "tensorrt"} <= facts.dependencies
    tensorrt = facts.locations["dependency:tensorrt"][0]
    assert tensorrt.relative_path == "setup.py"
    assert "tensorrt" in tensorrt.evidence.casefold()


def test_setup_py_tuple_dependency_values_are_extracted(tmp_path: Path) -> None:
    """`install_requires=("torch",)` 与列表写法等价，只认 List 会整条漏采。"""
    (tmp_path / "setup.py").write_text(
        "\n".join(
            [
                "from setuptools import setup",
                "setup(",
                "    name='demo',",
                "    install_requires=('torch>=2.0', 'ninja'),",
                "    extras_require={'dev': ('tensorrt==10.0',)},",
                ")",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert {"torch", "ninja", "tensorrt"} <= facts.dependencies
    assert facts.locations["dependency:ninja"][0].line == 4


def test_setup_py_dynamic_dependency_values_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        "\n".join(
            [
                "from setuptools import setup",
                "requirements = ['torch']",
                "setup(name='demo', install_requires=requirements)",
            ]
        ),
        encoding="utf-8",
    )

    facts = extract_project_facts(build_file_index(tmp_path))

    assert facts.dependencies == frozenset()


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
