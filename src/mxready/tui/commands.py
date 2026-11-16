"""Parse terminal commands as data and build allowlisted, shell-free scan invocations."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Never
from uuid import uuid4

from mxready.errors import MxReadyError
from mxready.models import ScanReport
from mxready.repository.identity import parse_repository_url

COMMANDS = {
    "scan": ("[目录] [--repo-url URL] [--commit SHA]", "扫描本地项目，默认当前目录"),
    "public": ("<URL> [--ref 分支/标签/提交]", "扫描公开 GitHub / Gitee 仓库"),
    "batch": ("<清单文件或URL>", "批量扫描并生成汇总"),
    "report": ("[JSON路径]", "查看报告，默认最近一次结果"),
    "findings": (
        "[页码] [--severity 级别] [--rule ID] [--file 路径] [--query 词] [--reset]",
        "搜索筛选发现，每页五项",
    ),
    "reports": ("[--query 词] [--batch ID] [--all-projects]", "选择已登记报告与批次结果"),
    "compare": ("[基线JSON] [当前JSON]", "同仓库离线报告对比"),
    "bundle": ("[JSON路径]", "生成验证 ZIP，默认最近一次结果"),
    "output": ("[目录]", "查看或设置报告输出目录"),
    "help": ("", "查看命令与键盘操作"),
    "clear": ("", "清空屏幕，保留报告文件与命令历史"),
    "cancel": ("", "中断当前扫描并清理子进程"),
    "quit": ("", "退出终端，运行中任务会先停止"),
}


@dataclass(frozen=True)
class Command:
    name: str
    target: str | None = None
    repo_url: str | None = None
    commit: str | None = None
    ref: str | None = None
    severity: str | None = None
    rule: str | None = None
    file: str | None = None
    query: str | None = None
    reset: bool = False
    all_projects: bool = False
    batch: str | None = None
    current: str | None = None


@dataclass(frozen=True)
class ScanJob:
    arguments: tuple[str, ...]
    output_dir: Path


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ValueError(f"{self.prog}: {message}；输入 /help 查看用法。")


def parse_command(value: str) -> Command:
    if "\n" in value or "\r" in value or len(value) > 8192:
        raise ValueError("每次输入一条命令（最多 8192 字符）。")
    # Backslashes are path characters on Windows, never shell escapes or commands.
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    parts = list(lexer)
    if not parts:
        raise ValueError("请输入目录、公开 URL 或 /help。")
    if not parts[0].startswith("/"):
        parts.insert(0, "/public" if parts[0].startswith("https://") else "/scan")
    # An existing absolute path is also a useful scan shortcut.
    elif parts[0][1:].split("/", 1)[0] not in COMMANDS and Path(parts[0]).is_dir():
        parts.insert(0, "/scan")
    name = parts[0][1:].casefold()
    if name not in COMMANDS:
        raise ValueError(f"未知命令 {parts[0]}；输入 /help 查看用法。")
    parser = _Parser(prog=f"/{name}", add_help=False, allow_abbrev=False)
    if name in {"scan", "public", "batch", "report", "bundle", "output", "findings", "compare"}:
        required = name in {"public", "batch"}
        parser.add_argument("target", nargs=None if required else "?")
    if name == "scan":
        parser.add_argument("--repo-url")
        parser.add_argument("--commit")
    if name == "public":
        parser.add_argument("--ref")
    if name == "compare":
        parser.add_argument("current", nargs="?")
    if name == "findings":
        parser.add_argument("--severity", choices=("blocker", "warning", "info", "all"))
        parser.add_argument("--rule")
        parser.add_argument("--file")
        parser.add_argument("--reset", action="store_true")
    if name in {"findings", "reports"}:
        parser.add_argument("--query")
    if name == "reports":
        parser.add_argument("--batch")
        parser.add_argument("--all-projects", action="store_true")
    args = vars(parser.parse_args(parts[1:]))
    for field, limit in (("rule", 100), ("file", 4096), ("query", 256), ("batch", 100)):
        if args.get(field) is not None and len(args[field]) > limit:
            raise ValueError(f"--{field} 最多 {limit} 字符。")
    if name == "findings":
        if args.get("reset") and any(
            args.get(k) is not None for k in ("target", "severity", "rule", "file", "query")
        ):
            raise ValueError("--reset 不能与页码或筛选条件混用。")
        if args.get("target") is not None and (
            not args["target"].isascii() or not args["target"].isdigit() or int(args["target"]) < 1
        ):
            raise ValueError("页码必须为正整数。")
        if args.get("rule") is not None:
            args["rule"] = args["rule"].strip().upper()
    return Command(name=name, **args)


def format_command(command: Command) -> str:
    """Roundtrip the path-aware lexer, including quotes; this is never shell code."""

    def quote(value: str) -> str:
        if '"' not in value:
            return '"' + value + '"'
        return "'" + value.replace("'", "'\"'\"'") + "'"

    parts = [f"/{command.name}"]
    for field, flag in (
        ("repo_url", "repo-url"),
        ("commit", "commit"),
        ("ref", "ref"),
        ("severity", "severity"),
        ("rule", "rule"),
        ("file", "file"),
        ("query", "query"),
        ("batch", "batch"),
    ):
        value = getattr(command, field)
        if value is not None:
            parts.append(f"--{flag}={quote(value)}")
    if command.reset:
        parts.append("--reset")
    if command.all_projects:
        parts.append("--all-projects")
    if any(
        value is not None and value.startswith("-") for value in (command.target, command.current)
    ):
        parts.append("--")
    if command.target is not None:
        parts.append(quote(command.target))
    if command.current is not None:
        parts.append(quote(command.current))
    result = " ".join(parts)
    if parse_command(result) != command:
        raise ValueError("历史命令无法无损恢复，已跳过。")
    return result


def resolve_path(value: str, project_dir: Path) -> Path:
    path = Path(value).expanduser()
    return path.absolute() if path.is_absolute() else (project_dir / path).absolute()


def new_output_directory(output_dir: Path, kind: str) -> Path:
    path = output_dir / f"{kind}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def make_scan_job(command: Command, *, project_dir: Path, output_dir: Path) -> ScanJob:
    if command.name not in {"scan", "public", "batch"}:
        raise ValueError("只能创建 scan / public / batch 扫描任务。")
    target = command.target or "."
    if command.name == "scan":
        path = resolve_path(target, project_dir)
        if not path.is_dir():
            raise ValueError(f"本地目录不存在: {path}")
        target = str(path)
        if command.commit is not None and re.fullmatch(r"[0-9a-f]{40}", command.commit) is None:
            raise ValueError("提交必须为 40 位小写十六进制 SHA。")
        if command.repo_url:
            try:
                parse_repository_url(command.repo_url)
            except MxReadyError as error:
                raise ValueError(error.message) from error
    elif command.name == "public" or target.startswith("https://"):
        try:
            parse_repository_url(target)
        except MxReadyError as error:
            raise ValueError(error.message) from error
    elif command.name == "batch":
        target = str(resolve_path(target, project_dir))
        if not Path(target).is_file():
            raise ValueError(f"清单文件不存在: {target}")
    else:
        raise ValueError("只能创建 scan / public / batch 扫描任务。")
    output = new_output_directory(output_dir, command.name)
    options = [f"--output={output}"]
    if command.name == "scan":
        module = "scan_repository"
        if command.repo_url:
            options.append(f"--repo-url={command.repo_url}")
        if command.commit:
            options.append(f"--commit={command.commit}")
    else:
        module = "generate_public_report" if command.name == "public" else "scan_batch"
        options.append(f"--work-dir={output / '.work'}")
        if command.name == "public":
            options.append("--label=report")
            if command.ref:
                options.append(f"--ref={command.ref}")
    return ScanJob(
        arguments=(sys.executable, "-u", "-m", f"mxready.cli.{module}", *options, "--", target),
        output_dir=output,
    )


def read_report(path: Path) -> ScanReport:
    from mxready.tui.report_catalog import load_report

    return load_report(path).report


def safe_text(value: str) -> str:
    return "".join(
        f"\\u{ord(char):04x}"
        if unicodedata.category(char).startswith("C") and char not in "\n\t"
        else char
        for char in value
    )
