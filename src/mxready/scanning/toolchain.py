"""工具链画像：接入 cu-bridge 之后，部分"未迁移"前提下成立的命中不再是阻塞项。

静态命中本身没有错——`NVCC = nvcc` 确实还在文件里。错的是严重级别所依赖的前提：
"项目尚未接入 MXMACA 兼容层"。cu-bridge 的 `make_maca` / `cucc` 会在构建期接管
这些调用，此时该写法是**预期状态**，继续报 blocker 等于把已迁移项目判成未迁移。

降级必须留痕，否则就变成用规则把结论藏起来。因此每次降级都会：
1. 把严重级别下调一级，并在 message 末尾注明原因；
2. 往 `analysis_warnings` 里写一条可追溯记录（含规则 ID 与文件数）。

只降一级、不降到 info：cu-bridge 接管的是构建入口，无法证明每个 nvcc 调用都走了
包装器——脚本里 `subprocess.run(["nvcc", ...])` 仍然绕过它，那属于真问题，降成
info 会放跑。

同理，降级只作用于**声明式构建文件**（Makefile / `*.mk` / CMakeLists.txt / `*.cmake`）。
这些文件里的 `NVCC = nvcc` 是构建设置，由 cu-bridge 的 conf.json 在编译期改写；
而 `.py` / `.sh` 里的 nvcc 是运行时命令，是否走了包装器只能人工判断，保持 blocker。
"""

from __future__ import annotations

from mxready.models import AnalysisWarning, Finding, Severity
from mxready.scanning.facts import ProjectFacts

CU_BRIDGE_FLAG = "uses_cu_bridge_toolchain"
CU_BRIDGE_WARNING_CODE = "TOOLCHAIN_CU_BRIDGE_DOWNGRADE"

# 规则 ID -> 降级后的级别。只有"前提是未迁移"的规则才该进这张表；
# 描述源码语义（PTX、线程束宽度）的规则与构建方式无关，不适用。
_CU_BRIDGE_DOWNGRADES: dict[str, Severity] = {
    "MXR-TOOLCHAIN-001": Severity.WARNING,
}

# 只在这些文件里认定"构建入口已被接管"。命令式脚本不在内。
_BUILD_DEFINITION_NAMES = {"cmakelists.txt", "gnumakefile", "makefile"}
_BUILD_DEFINITION_SUFFIXES = (".cmake", ".mk")

_DOWNGRADE_NOTE = (
    "（已检测到 cu-bridge 工具链接入：该构建入口通常由 make_maca/cucc 接管，"
    "此项从 blocker 降为 warning，请确认是否有脚本绕过包装器。）"
)


def apply_toolchain_profile(
    findings: list[Finding],
    facts: ProjectFacts,
) -> tuple[list[Finding], list[AnalysisWarning]]:
    """按工具链画像调整严重级别，返回新列表与需要记录到报告的告警。"""
    if not facts.flags.get(CU_BRIDGE_FLAG):
        return findings, []

    adjusted: list[Finding] = []
    downgraded_rules: dict[str, set[str]] = {}
    for finding in findings:
        target = _CU_BRIDGE_DOWNGRADES.get(finding.rule_id)
        if (
            target is None
            or finding.severity is not Severity.BLOCKER
            or not _is_build_definition(finding.relative_path)
        ):
            adjusted.append(finding)
            continue
        downgraded_rules.setdefault(finding.rule_id, set()).add(finding.relative_path)
        adjusted.append(
            finding.model_copy(
                update={
                    "severity": target,
                    "message": _append_note(finding.message),
                }
            )
        )

    if not downgraded_rules:
        return adjusted, []

    details = "；".join(
        f"{rule_id}（{len(paths)} 个文件）" for rule_id, paths in sorted(downgraded_rules.items())
    )
    return adjusted, [
        AnalysisWarning(
            code=CU_BRIDGE_WARNING_CODE,
            relative_path=None,
            message=(
                f"检测到 cu-bridge 工具链接入，已将 {details} 从 blocker 降为 warning。"
                "降级只覆盖声明式构建文件；命令式脚本（.py / .sh）中的 nvcc 调用仍按 "
                "blocker 报告，因为它可能绕过 make_maca 的 PATH 注入。"
            ),
        )
    ]


def _is_build_definition(relative_path: str) -> bool:
    name = relative_path.rsplit("/", 1)[-1].casefold()
    return name in _BUILD_DEFINITION_NAMES or name.endswith(_BUILD_DEFINITION_SUFFIXES)


def _append_note(message: str) -> str:
    if _DOWNGRADE_NOTE in message:
        return message
    return f"{message}{_DOWNGRADE_NOTE}"
