"""每个对外命令都必须接受 `--version`，且打印的版本与 `pyproject.toml` 同源。

用户按安装文档用 `mxready-serve`、`mxready-scan` 等命令起步，现场排查环境问题最先试的
就是 `--version`。此前七个入口全部拒绝它：五个 CLI 报 `unrecognized arguments`（退出码 2），
`mxready-mcp` 因为没有解析参数而静默忽略，runner 同样不认。版本一致性测试已经钉住了产物名、
徽章和文档示例，这条测试补上命令行这最后一个对外表面——漏接任何一个入口都会在这里失败。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from mxready import __version__
from mxready.cli import (
    build_verification_bundle,
    generate_public_report,
    scan_batch,
    scan_repository,
    serve,
)
from mxready.mcp import server as mcp_server
from mxready_runner import __version__ as runner_version
from mxready_runner import cli as runner_cli

EXPECTED_OUTPUT = f"MXReady {__version__}"

HOST_ENTRY_POINTS: list[tuple[str, Callable[[Sequence[str]], int]]] = [
    ("mxready-serve", serve.main),
    ("mxready-scan", scan_repository.main),
    ("mxready-scan-public", generate_public_report.main),
    ("mxready-scan-batch", scan_batch.main),
    ("mxready-build-bundle", build_verification_bundle.main),
    ("mxready-mcp", mcp_server.main),
]


@pytest.mark.parametrize(("prog", "entry_point"), HOST_ENTRY_POINTS)
def test_host_entry_point_prints_version(
    prog: str, entry_point: Callable[[Sequence[str]], int], capsys: pytest.CaptureFixture[str]
) -> None:
    """`--version` 必须打印版本并以 0 退出，且不能先把服务/扫描跑起来。"""
    with pytest.raises(SystemExit) as exit_info:
        entry_point(["--version"])
    assert exit_info.value.code == 0, prog
    captured = capsys.readouterr()
    assert captured.out.strip() == EXPECTED_OUTPUT, prog
    assert captured.err == "", prog


def test_runner_entry_point_prints_its_own_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """runner 独立分发且零依赖，版本串里显式带上 runner 字样，避免与宿主混淆。"""
    with pytest.raises(SystemExit) as exit_info:
        runner_cli.main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"MXReady runner {runner_version}"


def test_runner_and_host_versions_are_the_same_release() -> None:
    assert runner_version == __version__


def test_version_flag_does_not_break_argument_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """未知参数仍要报错退出，`--version` 不是把参数校验整体放宽。"""
    with pytest.raises(SystemExit) as exit_info:
        serve.main(["--not-a-flag"])
    assert exit_info.value.code == 2
    assert "--version" in capsys.readouterr().err
