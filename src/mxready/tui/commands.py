"""Parse terminal commands as data and build allowlisted, shell-free scan invocations."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Never
from uuid import uuid4

from mxready.errors import MxReadyError
from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
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
    "code": ("[消息]", "进入只读 AI 代码工作区"),
    "lang": ("[zh|en]", "切换界面语言"),
    "help": ("", "查看命令与键盘操作"),
    "clear": ("", "清空屏幕，保留报告文件与命令历史"),
    "cancel": ("", "中断当前扫描并清理子进程"),
    "quit": ("", "退出终端，运行中任务会先停止"),
}

_ENGLISH_DESCRIPTIONS = {
    "scan": "Scan a local project; defaults to the current directory",
    "public": "Scan a public GitHub / Gitee repository",
    "batch": "Scan a batch of repositories and produce a summary",
    "report": "Open a report; defaults to the latest result",
    "findings": "Search and filter findings, five per page",
    "reports": "Select registered reports and batch results",
    "compare": "Compare offline reports from the same repository",
    "bundle": "Build a verification ZIP; defaults to the latest result",
    "output": "View or set the report output directory",
    "code": "Enter the read-only AI code workspace",
    "lang": "Switch the interface language (zh/en)",
    "help": "View commands and keyboard shortcuts",
    "clear": "Clear the screen; keep report files and command history",
    "cancel": "Interrupt the current scan and clean up child processes",
    "quit": "Exit the terminal; running tasks are stopped first",
}


def command_catalog(language: str = DEFAULT_LANGUAGE) -> dict[str, tuple[str, str]]:
    return {
        name: (usage, tr(language, description, _ENGLISH_DESCRIPTIONS[name]))
        for name, (usage, description) in COMMANDS.items()
    }


CODE_COMMANDS = {
    "code": ("[消息]", "发送消息给代码助手"),
    "scan": ("", "切回扫描工作区"),
    "help": ("", "查看 code 工作区命令"),
    "clear": ("", "清屏，保留对话上下文"),
    "new": ("", "清空对话上下文并重新开始"),
    "provider": (
        "add <名称> --protocol openai|anthropic --base-url URL --model 模型 | "
        "list | use <名称> | test [名称] | remove <名称>",
        "管理模型服务；密钥会单独安全输入",
    ),
    "model": ("[名称]", "查看或修改当前模型"),
    "permissions": ("", "查看只读/提权状态与可用工具"),
    "elevate": ("", "本会话提权，允许逐次审批写文件/执行命令"),
    "restrict": ("", "立即恢复只读"),
    "cancel": ("", "取消当前模型请求"),
    "lang": ("[zh|en]", "切换界面语言"),
    "quit": ("", "退出终端"),
}

_CODE_ENGLISH_DESCRIPTIONS = {
    "code": "Send a message to the code assistant",
    "scan": "Switch back to the scan workspace",
    "help": "View code workspace commands",
    "clear": "Clear the screen; keep the conversation context",
    "new": "Reset the conversation context",
    "provider": "Manage model providers; the API key is prompted separately",
    "model": "View or change the current model",
    "permissions": "View read-only/elevated state and available tools",
    "elevate": "Elevate this session; each write/command still needs approval",
    "restrict": "Return to read-only mode immediately",
    "cancel": "Cancel the current model request",
    "lang": "Switch the interface language (zh/en)",
    "quit": "Exit the terminal",
}


def code_command_catalog(language: str = DEFAULT_LANGUAGE) -> dict[str, tuple[str, str]]:
    return {
        name: (usage, tr(language, description, _CODE_ENGLISH_DESCRIPTIONS[name]))
        for name, (usage, description) in CODE_COMMANDS.items()
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
class CodeCommand:
    name: str
    target: str | None = None
    action: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class ScanJob:
    arguments: tuple[str, ...]
    output_dir: Path


class _Parser(argparse.ArgumentParser):
    language: str = DEFAULT_LANGUAGE

    def error(self, message: str) -> Never:
        hint = tr(self.language, "输入 /help 查看用法。", "Type /help for usage.")
        separator = "；" if self.language != "en" else "; "
        raise ValueError(f"{self.prog}: {message}{separator}{hint}")


def parse_command(value: str, language: str = DEFAULT_LANGUAGE) -> Command:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    catalog = command_catalog(language)
    if "\n" in value or "\r" in value or len(value) > 8192:
        raise ValueError(
            tr(
                language,
                "每次输入一条命令（最多 8192 字符）。",
                "Enter one command at a time (maximum 8192 characters).",
            )
        )
    # Code prompts are free text, not shell-like arguments.
    stripped = value.strip()
    if stripped.casefold() == "/code" or stripped.casefold().startswith("/code "):
        return Command(name="code", target=stripped[5:].strip() or None)
    # Backslashes are path characters on Windows, never shell escapes or commands.
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    parts = list(lexer)
    if not parts:
        raise ValueError(
            tr(
                language,
                "请输入目录、公开 URL 或 /help。",
                "Enter a directory, public URL, or /help.",
            )
        )
    if not parts[0].startswith("/"):
        parts.insert(0, "/public" if parts[0].startswith("https://") else "/scan")
    # An existing absolute path is also a useful scan shortcut.
    elif parts[0][1:].split("/", 1)[0] not in catalog and Path(parts[0]).is_dir():
        parts.insert(0, "/scan")
    name = parts[0][1:].casefold()
    if name not in catalog:
        raise ValueError(
            tr(
                language,
                f"未知命令 {parts[0]}；输入 /help 查看用法。",
                f"Unknown command {parts[0]}; type /help for usage.",
            )
        )
    parser = _Parser(prog=f"/{name}", add_help=False, allow_abbrev=False)
    parser.language = language
    if name in {
        "scan",
        "public",
        "batch",
        "report",
        "bundle",
        "output",
        "findings",
        "compare",
        "lang",
    }:
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
            raise ValueError(
                tr(
                    language,
                    f"--{field} 最多 {limit} 字符。",
                    f"--{field} must be at most {limit} characters.",
                )
            )
    if name == "lang":
        target = args.get("target")
        if target is not None:
            normalized = normalize_language(target)
            if normalized is None:
                raise ValueError(
                    tr(
                        language,
                        f"不支持的语言 {target}；请使用 zh 或 en。",
                        f"Unsupported language {target}; use zh or en.",
                    )
                )
            args["target"] = normalized
        return Command(name=name, **args)
    if name == "findings":
        if args.get("reset") and any(
            args.get(k) is not None for k in ("target", "severity", "rule", "file", "query")
        ):
            raise ValueError(
                tr(
                    language,
                    "--reset 不能与页码或筛选条件混用。",
                    "--reset cannot be combined with a page or filters.",
                )
            )
        if args.get("target") is not None and (
            not args["target"].isascii() or not args["target"].isdigit() or int(args["target"]) < 1
        ):
            raise ValueError(tr(language, "页码必须为正整数。", "Page must be a positive integer."))
        if args.get("rule") is not None:
            args["rule"] = args["rule"].strip().upper()
    return Command(name=name, **args)


def _validate_model_name(value: str, language: str) -> str:
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > 200
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in cleaned)
    ):
        raise ValueError(
            tr(
                language,
                "--model 必须是 1-200 个不含空白或控制字符的字符。",
                "--model must be 1-200 characters without whitespace or control characters.",
            )
        )
    return cleaned


def parse_code_command(value: str, language: str = DEFAULT_LANGUAGE) -> CodeCommand:
    """Parse the code workspace command set; plain text is never parsed here."""
    language = normalize_language(language) or DEFAULT_LANGUAGE
    catalog = code_command_catalog(language)
    if "\n" in value or "\r" in value or len(value) > 32768:
        raise ValueError(
            tr(
                language,
                "每次输入一条命令或消息（最多 32768 字符）。",
                "Enter one command or message at a time (maximum 32768 characters).",
            )
        )
    stripped = value.strip()
    if stripped.casefold() == "/code" or stripped.casefold().startswith("/code "):
        return CodeCommand(name="code", target=stripped[5:].strip() or None)
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    parts = list(lexer)
    if not parts or not parts[0].startswith("/"):
        raise ValueError(
            tr(
                language,
                "命令必须以 / 开头；直接输入文本会发送给代码助手。",
                "Commands must start with /; plain text is sent to the code assistant.",
            )
        )
    name = parts[0][1:].casefold()
    if name not in catalog:
        raise ValueError(
            tr(
                language,
                f"未知 code 命令 {parts[0]}；输入 /help 查看用法。",
                f"Unknown code command {parts[0]}; type /help for usage.",
            )
        )
    parser = _Parser(prog=f"/{name}", add_help=False, allow_abbrev=False)
    parser.language = language
    if name == "provider":
        parser.add_argument("subcommand", choices=("add", "list", "use", "test", "remove"))
        parser.add_argument("target", nargs="?")
        parser.add_argument("--protocol", choices=("openai", "anthropic"))
        parser.add_argument("--base-url")
        parser.add_argument("--model")
    elif name in {"code", "model", "lang"}:
        parser.add_argument("target", nargs="?")
    args = vars(parser.parse_args(parts[1:]))
    target = args.get("target")
    if name == "code":
        if target is not None and len(target) > 32768:
            raise ValueError(
                tr(language, "消息最多 32768 字符。", "Messages must be at most 32768 characters.")
            )
        return CodeCommand(name=name, target=target or None)
    if name == "model":
        if target is None:
            return CodeCommand(name=name)
        return CodeCommand(name=name, model=_validate_model_name(target, language))
    if name == "lang":
        if target is None:
            return CodeCommand(name=name)
        normalized = normalize_language(target)
        if normalized is None:
            raise ValueError(
                tr(
                    language,
                    f"不支持的语言 {target}；请使用 zh 或 en。",
                    f"Unsupported language {target}; use zh or en.",
                )
            )
        return CodeCommand(name=name, target=normalized)
    if name != "provider":
        return CodeCommand(name=name)
    from mxready.agent.config import validate_base_url, validate_provider_name

    subcommand = args["subcommand"]
    protocol, base_url, model = args.get("protocol"), args.get("base_url"), args.get("model")
    if subcommand == "add":
        if target is None or protocol is None or base_url is None or model is None:
            raise ValueError(
                tr(
                    language,
                    "用法: /provider add <名称> --protocol openai|anthropic "
                    "--base-url URL --model 模型",
                    "Usage: /provider add <name> --protocol openai|anthropic "
                    "--base-url URL --model MODEL",
                )
            )
        try:
            target = validate_provider_name(target)
            base_url = validate_base_url(base_url)
        except ValueError as error:
            raise ValueError(str(error)) from error
        model = _validate_model_name(model, language)
    elif subcommand in {"use", "remove"}:
        if target is None:
            raise ValueError(
                tr(
                    language,
                    f"用法: /provider {subcommand} <名称>",
                    f"Usage: /provider {subcommand} <name>",
                )
            )
        try:
            target = validate_provider_name(target)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if any(value is not None for value in (protocol, base_url, model)):
            raise ValueError(
                tr(
                    language,
                    f"/provider {subcommand} 不接受配置参数。",
                    f"/provider {subcommand} does not accept configuration flags.",
                )
            )
    elif any(value is not None for value in (protocol, base_url, model)):
        raise ValueError(
            tr(
                language,
                f"/provider {subcommand} 不接受配置参数。",
                f"/provider {subcommand} does not accept configuration flags.",
            )
        )
    if subcommand == "test" and target is not None:
        try:
            target = validate_provider_name(target)
        except ValueError as error:
            raise ValueError(str(error)) from error
    return CodeCommand(
        name=name,
        target=target,
        action=subcommand,
        protocol=protocol,
        base_url=base_url,
        model=model,
    )


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


def make_scan_job(
    command: Command,
    *,
    project_dir: Path,
    output_dir: Path,
    language: str = DEFAULT_LANGUAGE,
) -> ScanJob:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    only_scan = tr(
        language,
        "只能创建 scan / public / batch 扫描任务。",
        "Only scan / public / batch jobs can be created.",
    )
    if command.name not in {"scan", "public", "batch"}:
        raise ValueError(only_scan)
    target = command.target or "."
    if command.name == "scan":
        path = resolve_path(target, project_dir)
        if not path.is_dir():
            raise ValueError(
                tr(language, f"本地目录不存在: {path}", f"Local directory does not exist: {path}")
            )
        target = str(path)
        if command.commit is not None and re.fullmatch(r"[0-9a-f]{40}", command.commit) is None:
            raise ValueError(
                tr(
                    language,
                    "提交必须为 40 位小写十六进制 SHA。",
                    "Commit must be a 40-character lowercase hexadecimal SHA.",
                )
            )
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
            raise ValueError(
                tr(language, f"清单文件不存在: {target}", f"Manifest file does not exist: {target}")
            )
    else:
        raise ValueError(only_scan)
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


def read_report(path: Path, language: str = DEFAULT_LANGUAGE) -> ScanReport:
    from mxready.tui.report_catalog import load_report

    return load_report(path, language=language).report
