"""识别 Python 文档字符串占用的行区间。

静态规则按词法匹配，分不清"可执行代码"与"文档里对代码的描述"。本仓库自身就有
反例：`scanning/toolchain.py` 的模块文档字符串写了
`subprocess.run(["nvcc", ...])` 作为反例说明，于是被 `MXR-TOOLCHAIN-001`
判成 blocker——一条描述规则的文字被当成了违反规则的行为。

这里的判定刻意收得很窄，只处理**文档字符串**：

- 只有模块、类、函数的首条语句、且是字符串常量，才算文档字符串；
- 普通字符串字面量**不**豁免。`os.system("nvcc main.cu")` 命令就在字符串里，
  豁免它会制造真实的漏报，而漏报比多报危险得多；
- 解析失败（Python 2 源码、生成代码、语法错误）一律返回空区间，即不豁免。

因此这是"去掉文档噪音"，不是"忽略字符串"。
"""

from __future__ import annotations

import ast


def docstring_spans(text: str) -> tuple[tuple[int, int], ...]:
    """返回文档字符串占用的闭区间行号（1-based），供命中行范围比对。"""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return ()

    spans: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        start = first.lineno
        end = getattr(first, "end_lineno", None) or start
        spans.append((start, end))
    return tuple(spans)


def is_inside_docstring(
    spans: tuple[tuple[int, int], ...],
    line_start: int,
    line_end: int,
) -> bool:
    """命中行范围必须**完整**落在文档字符串内才豁免。"""
    return any(start <= line_start and line_end <= end for start, end in spans)
