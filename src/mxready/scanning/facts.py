from __future__ import annotations

import ast
import re
import tomllib
import warnings
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

from mxready.scanning.indexer import FileIndex, IndexedFile

_DEPENDENCY_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_KNOWN_FLAGS = {
    "imports_apex",
    "imports_tensorrt",
    "invokes_nvcc_directly",
    "invokes_nvidia_smi",
    "references_cuda_home",
    "uses_cmake_cuda_language",
    "uses_cmake_cuda_package",
    "uses_cmake_torch_package",
    "uses_cu_bridge_toolchain",
    "uses_hardcoded_cuda_path",
    "uses_torch_cpp_extension",
    "uses_torch_cpp_extension_load",
    "uses_torch_cuda_extension",
}
_MAKEFILE_FILENAMES = {"GNUmakefile", "Makefile", "makefile"}
# cu-bridge 的入口与必配环境变量，均取自其用户手册；命中任一即说明构建层已接入
# MXMACA 兼容层。MACA_CLANG_PATH 单独排除——它由 MACA SDK 设置，原生 MACA 项目
# 也会出现，不能作为 cu-bridge 的证据。
_CU_BRIDGE_MARKERS = re.compile(
    r"\b(?:make_maca|cmake_maca|cucc)\b|\bCUCC_(?:PATH|CMAKE_ENTRY)\b|cu-bridge",
    re.IGNORECASE,
)
_BUILD_SYSTEM_PACKAGES = {
    "flit-core": "flit",
    "hatchling": "hatch",
    "meson-python": "meson",
    "poetry-core": "poetry",
    "scikit-build-core": "scikit-build",
    "setuptools": "setuptools",
}
_SETUP_REQUIRE_KEYWORDS = ("install_requires", "setup_requires", "tests_require")


@dataclass(frozen=True, slots=True, order=True)
class SourceLocation:
    relative_path: str
    line: int
    evidence: str


@dataclass(frozen=True, slots=True)
class ProjectFacts:
    dependencies: frozenset[str]
    build_systems: frozenset[str]
    flags: dict[str, bool]
    locations: dict[str, tuple[SourceLocation, ...]]


class _FactCollector:
    def __init__(self) -> None:
        self.dependencies: set[str] = set()
        self.build_systems: set[str] = set()
        self.flags = dict.fromkeys(sorted(_KNOWN_FLAGS), False)
        self.locations: defaultdict[str, list[SourceLocation]] = defaultdict(list)
        self._seen_locations: defaultdict[str, set[SourceLocation]] = defaultdict(set)

    def add_dependency(
        self,
        specification: str,
        location: SourceLocation,
    ) -> None:
        name = _parse_dependency_name(specification)
        if name is None:
            return
        self.dependencies.add(name)
        self._add_location(f"dependency:{name}", location)

    def add_build_system(self, name: str, location: SourceLocation) -> None:
        normalized = name.casefold()
        self.build_systems.add(normalized)
        self._add_location(f"build_system:{normalized}", location)

    def set_flag(self, name: str, location: SourceLocation) -> None:
        self.flags[name] = True
        self._add_location(f"fact:{name}", location)

    def _add_location(self, key: str, location: SourceLocation) -> None:
        seen = self._seen_locations[key]
        if location in seen:
            return
        seen.add(location)
        self.locations[key].append(location)

    def finish(self) -> ProjectFacts:
        locations = {key: tuple(sorted(value)) for key, value in sorted(self.locations.items())}
        return ProjectFacts(
            dependencies=frozenset(self.dependencies),
            build_systems=frozenset(self.build_systems),
            flags={key: self.flags[key] for key in sorted(self.flags)},
            locations=locations,
        )


def extract_project_facts(index: FileIndex) -> ProjectFacts:
    """Extract conservative facts without importing or executing repository code."""
    collector = _FactCollector()

    for indexed_file in index.files:
        name = indexed_file.relative_path.rsplit("/", 1)[-1]
        lower_name = name.casefold()

        if lower_name == "pyproject.toml":
            _extract_pyproject(indexed_file, collector)
        if lower_name.startswith("requirements") and lower_name.endswith(".txt"):
            _extract_requirements(indexed_file, collector)
        if lower_name.endswith(".py"):
            _extract_python(indexed_file, collector)
        if name == "CMakeLists.txt" or lower_name.endswith(".cmake"):
            _extract_cmake(indexed_file, collector)
        if lower_name.endswith(".sh") or _is_makefile(name, lower_name):
            # Makefile 与 shell 共享 `#` 注释与"一行一条命令"的形态，
            # 同一套逐行提取规则可以直接复用。
            _extract_shell(indexed_file, collector)
        if _may_reference_toolchain(name, lower_name):
            _detect_cu_bridge(indexed_file, collector)

    return collector.finish()


def _is_makefile(name: str, lower_name: str) -> bool:
    return name in _MAKEFILE_FILENAMES or lower_name.endswith(".mk")


def _may_reference_toolchain(name: str, lower_name: str) -> bool:
    """只在构建与部署相关文件里找 cu-bridge 痕迹，避免在 .cu 注释里误命中。"""
    return (
        _is_makefile(name, lower_name)
        or lower_name.endswith((".sh", ".py", ".cmake"))
        or name in {"CMakeLists.txt", "Dockerfile"}
        or lower_name.endswith(".dockerfile")
    )


def _detect_cu_bridge(indexed_file: IndexedFile, collector: _FactCollector) -> None:
    lines = indexed_file.text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        if _CU_BRIDGE_MARKERS.search(_strip_shell_comment(line)):
            collector.set_flag(
                "uses_cu_bridge_toolchain",
                _location(lines, indexed_file.relative_path, line_number),
            )
            return


def _extract_pyproject(indexed_file: IndexedFile, collector: _FactCollector) -> None:
    try:
        document = tomllib.loads(indexed_file.text)
    except (tomllib.TOMLDecodeError, TypeError):
        return

    searcher = _LineSearch(indexed_file)

    def locate(value: str) -> SourceLocation:
        return searcher.locate(value)

    project = document.get("project")
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if isinstance(dependency, str):
                    collector.add_dependency(dependency, locate(dependency))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    for dependency in group:
                        if isinstance(dependency, str):
                            collector.add_dependency(dependency, locate(dependency))

    build_system = document.get("build-system")
    if isinstance(build_system, dict):
        requirements = build_system.get("requires")
        if isinstance(requirements, list):
            for requirement in requirements:
                if not isinstance(requirement, str):
                    continue
                package = _parse_dependency_name(requirement)
                if package in _BUILD_SYSTEM_PACKAGES:
                    collector.add_build_system(
                        _BUILD_SYSTEM_PACKAGES[package],
                        locate(requirement),
                    )

        backend = build_system.get("build-backend")
        if isinstance(backend, str):
            package = _canonicalize_name(backend.split(".", 1)[0])
            if package in _BUILD_SYSTEM_PACKAGES:
                collector.add_build_system(
                    _BUILD_SYSTEM_PACKAGES[package],
                    locate(backend),
                )

    tool = document.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            dependencies = poetry.get("dependencies")
            if isinstance(dependencies, dict):
                for name in dependencies:
                    if isinstance(name, str) and name.casefold() != "python":
                        collector.add_dependency(
                            name,
                            locate(name),
                        )


def _extract_requirements(
    indexed_file: IndexedFile,
    collector: _FactCollector,
) -> None:
    lines = indexed_file.text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-")):
            continue
        if "://" in stripped and " @ " not in stripped:
            continue
        specification = stripped.split(" #", 1)[0].strip()
        collector.add_dependency(
            specification,
            _location(lines, indexed_file.relative_path, line_number),
        )


def _extract_python(indexed_file: IndexedFile, collector: _FactCollector) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            warnings.simplefilter("ignore", DeprecationWarning)
            tree = ast.parse(indexed_file.text, filename=indexed_file.relative_path)
    except (SyntaxError, ValueError):
        return

    visitor = _PythonFactVisitor(indexed_file, collector)
    visitor.visit(tree)


class _PythonFactVisitor(ast.NodeVisitor):
    def __init__(
        self,
        indexed_file: IndexedFile,
        collector: _FactCollector,
    ) -> None:
        self.indexed_file = indexed_file
        self.lines = indexed_file.text.splitlines()
        self.collector = collector
        self.aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self.aliases[local_name] = alias.name if alias.asname else alias.name.split(".", 1)[0]
            self._record_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.aliases[alias.asname or alias.name] = full_name
            self._record_import(full_name, node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if target_names & {"CUDA_HOME", "CUDA_PATH", "CUDA_ROOT"}:
            self.collector.set_flag(
                "references_cuda_home",
                self._location(node.lineno),
            )
        if _node_contains_string(node.value, "/usr/local/cuda"):
            self.collector.set_flag(
                "uses_hardcoded_cuda_path",
                self._location(node.lineno),
            )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id in {
            "CUDA_HOME",
            "CUDA_PATH",
            "CUDA_ROOT",
        }:
            self.collector.set_flag(
                "references_cuda_home",
                self._location(node.lineno),
            )
        if node.value is not None and _node_contains_string(
            node.value,
            "/usr/local/cuda",
        ):
            self.collector.set_flag(
                "uses_hardcoded_cuda_path",
                self._location(node.lineno),
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        function_name = self._resolve_name(node.func)
        location = self._location(node.lineno)
        if function_name == "torch.utils.cpp_extension.CUDAExtension":
            self.collector.set_flag("uses_torch_cuda_extension", location)
        elif function_name == "torch.utils.cpp_extension.CppExtension":
            self.collector.set_flag("uses_torch_cpp_extension", location)
        elif function_name == "torch.utils.cpp_extension.load":
            self.collector.set_flag("uses_torch_cpp_extension_load", location)

        if function_name in {"setuptools.setup", "distutils.core.setup"}:
            self.collector.add_build_system(
                "setuptools" if function_name.startswith("setuptools") else "distutils",
                location,
            )
            self._extract_setup_dependencies(node)
        self.generic_visit(node)

    def _extract_setup_dependencies(self, node: ast.Call) -> None:
        """setup.py 是 CUDA 扩展项目最主流的依赖声明面（PyMigBench 语料证实），
        保守提取字面量字符串列表，不求值任何表达式。"""
        for keyword in node.keywords:
            if keyword.arg in _SETUP_REQUIRE_KEYWORDS:
                for value, line in _string_list_elements(keyword.value):
                    self.collector.add_dependency(
                        value,
                        self._location(line),
                    )
            elif keyword.arg == "extras_require":
                self._extract_extras_require(keyword.value)

    def _extract_extras_require(self, value: ast.expr) -> None:
        if not isinstance(value, ast.Dict):
            return
        for key, group in zip(value.keys, value.values, strict=False):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            for spec, line in _string_list_elements(group):
                self.collector.add_dependency(
                    spec,
                    self._location(line),
                )

    def _record_import(self, full_name: str, line_number: int) -> None:
        location = self._location(line_number)
        if full_name == "setuptools" or full_name.startswith("setuptools."):
            self.collector.add_build_system("setuptools", location)
        if full_name == "tensorrt" or full_name.startswith("tensorrt."):
            self.collector.set_flag("imports_tensorrt", location)
        if full_name == "apex" or full_name.startswith("apex."):
            self.collector.set_flag("imports_apex", location)

    def _resolve_name(self, node: ast.expr) -> str:
        dotted = _dotted_name(node)
        if not dotted:
            return ""
        head, separator, tail = dotted.partition(".")
        resolved_head = self.aliases.get(head, head)
        return f"{resolved_head}{separator}{tail}"

    def _location(self, line_number: int) -> SourceLocation:
        return _location(self.lines, self.indexed_file.relative_path, line_number)


def _string_list_elements(node: ast.expr) -> Iterator[tuple[str, int]]:
    # setup.py 里 `install_requires=("torch",)` 这种元组写法同样常见，只认 List
    # 会整条漏采。仍不求值任何表达式，只取字面量。
    if isinstance(node, (ast.List, ast.Tuple)):
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                yield element.value, element.lineno


def _extract_cmake(indexed_file: IndexedFile, collector: _FactCollector) -> None:
    cmake_source = _strip_cmake_comments(indexed_file.text)
    original_lines = indexed_file.text.splitlines()
    collector.add_build_system("cmake", _location(original_lines, indexed_file.relative_path, 1))
    patterns = {
        "uses_cmake_cuda_language": re.compile(
            r"\b(?:project|enable_language)\s*\([^)]*\bCUDA\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "uses_cmake_cuda_package": re.compile(
            r"\bfind_package\s*\(\s*(?:CUDA|CUDAToolkit)\b",
            re.IGNORECASE,
        ),
        "uses_cmake_torch_package": re.compile(
            r"\bfind_package\s*\(\s*Torch\b",
            re.IGNORECASE,
        ),
    }
    for flag, pattern in patterns.items():
        match = pattern.search(cmake_source)
        if match:
            line_number = cmake_source.count("\n", 0, match.start()) + 1
            collector.set_flag(
                flag,
                _location(original_lines, indexed_file.relative_path, line_number),
            )

    # 在剥离注释后的文本上检测：`# set(CUDA_HOME ...)` 这类被注掉的写法不算引用。
    # _strip_cmake_comments 保持字符偏移与换行不变，行号可直接对回原文取 evidence。
    for line_number, stripped_line in enumerate(cmake_source.splitlines(), start=1):
        if re.search(r"\b(?:CUDA_HOME|CUDA_PATH|CUDA_ROOT)\b", stripped_line):
            collector.set_flag(
                "references_cuda_home",
                _location(original_lines, indexed_file.relative_path, line_number),
            )


def _strip_cmake_comments(value: str) -> str:
    lines = []
    for line in value.splitlines(keepends=True):
        content, marker, comment = line.partition("#")
        if marker:
            lines.append(content + " " * (len(marker) + len(comment.rstrip("\r\n"))))
            if line.endswith("\r\n"):
                lines.append("\r\n")
            elif line.endswith("\n"):
                lines.append("\n")
        else:
            lines.append(line)
    return "".join(lines)


def _extract_shell(indexed_file: IndexedFile, collector: _FactCollector) -> None:
    lines = indexed_file.text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        location = _location(lines, indexed_file.relative_path, line_number)
        code = _strip_shell_comment(line)
        if re.search(r"\bnvcc\b", code, re.IGNORECASE):
            collector.set_flag("invokes_nvcc_directly", location)
        if re.search(r"\bnvidia-smi\b", code, re.IGNORECASE):
            collector.set_flag("invokes_nvidia_smi", location)
        if re.search(r"\b(?:CUDA_HOME|CUDA_PATH|CUDA_ROOT)\b", code):
            collector.set_flag("references_cuda_home", location)
        if "/usr/local/cuda" in code:
            collector.set_flag("uses_hardcoded_cuda_path", location)


def _strip_shell_comment(value: str) -> str:
    content, marker, _comment = value.partition("#")
    return content if marker else value


def _parse_dependency_name(specification: str) -> str | None:
    match = _DEPENDENCY_NAME.match(specification)
    if match is None:
        return None
    return _canonicalize_name(match.group(1))


def _canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _node_contains_string(node: ast.AST, value: str) -> bool:
    return any(
        isinstance(child, ast.Constant) and isinstance(child.value, str) and value in child.value
        for child in ast.walk(node)
    )


class _LineSearch:
    """把"折叠后子串"定位回行号，构建一次、查询多次。

    原实现为每个依赖逐行做 `in` 判断，是 O(依赖数 × 行数) 的 Python 级循环：
    500 条依赖的 pyproject 上单文件耗十几毫秒。改为整篇折叠一次后用 C 层
    `str.find` 定位，再用行首偏移查表，查询降为 O(字符数) + O(log 行数)。

    行首偏移取自 `splitlines(keepends=True)`，与 `str.splitlines()` 的行口径
    严格一致——不像 `\\n` 计数那样在 `\\f`、`\\u2028` 等异体分隔符上错行。
    折叠是逐码位映射，整篇折叠与逐行折叠等价，因此结果与旧实现逐行扫描相同。
    """

    __slots__ = ("_folded", "_lines", "_relative_path", "_starts")

    def __init__(self, indexed_file: IndexedFile) -> None:
        text = indexed_file.text
        self._relative_path = indexed_file.relative_path
        self._lines = text.splitlines()
        self._folded = text.casefold()
        starts: list[int] = []
        offset = 0
        for line in text.splitlines(keepends=True):
            starts.append(offset)
            offset += len(line)
        self._starts = starts

    def locate(self, value: str) -> SourceLocation:
        position = self._folded.find(value.casefold())
        if position < 0:
            return _location(self._lines, self._relative_path, 1)
        return _location(
            self._lines,
            self._relative_path,
            bisect_right(self._starts, position),
        )


def _location(lines: list[str], relative_path: str, line_number: int) -> SourceLocation:
    evidence = lines[line_number - 1].strip() if 0 < line_number <= len(lines) else ""
    return SourceLocation(
        relative_path=relative_path,
        line=max(1, line_number),
        evidence=evidence[:240],
    )
