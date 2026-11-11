from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

from mxready import __version__
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.models import ScanReport
from mxready.reporting.badge import render_badge
from mxready.reporting.comparison import new_blockers
from mxready.reporting.markdown import render_markdown
from mxready.reporting.sarif import render_sarif
from mxready.reporting.terminal import render_terminal_summary
from mxready.repository.identity import parse_repository_url
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog

_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SCP_LIKE_REMOTE = re.compile(
    r"^(?:[^@/:]+@)?(?P<host>[A-Za-z0-9._-]*\.[A-Za-z0-9-]+):(?P<path>[A-Za-z0-9._~/-]+)$"
)
_SSH_URL_REMOTE = re.compile(
    r"^ssh://(?:[^@/]+@)?(?P<host>[A-Za-z0-9._-]+)/(?P<path>[A-Za-z0-9._~/-]+)$"
)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        baseline = _load_baseline(arguments.baseline, fail_on=arguments.fail_on)
        repository_root = _local_repository(arguments.local_path)
        commit = _commit_sha(arguments.commit or _detect_commit(repository_root))
        identity = parse_repository_url(
            arguments.repo_url or _detect_repository_url(repository_root)
        )
        settings = Settings.from_env()
        report = ScanAnalyzer(
            load_rule_catalog(
                settings.rules_dir,
                extra_directory=settings.extra_rules_dir,
            ),
            enable_prefilter=settings.prefilter_enabled,
        ).analyze(
            repository_root,
            repository_url=identity.clone_url,
            commit=commit,
            scan_id=uuid4(),
            stage_callback=lambda status: None,
        )
        blockers = [f for f in report.findings if f.severity.value == "blocker"]
        if baseline is not None:
            blockers = new_blockers(baseline, report)

        output_dir = Path(arguments.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = _write_outputs(output_dir, f"{identity.name}-{commit[:12]}", report)
        if baseline is not None:
            print(f"New or increased blocker groups: {len(blockers)}")
    except (MxReadyError, OSError, ValueError) as error:
        print(f"MXReady scan error: {error}", file=sys.stderr)
        return 1

    print(
        _terminal_summary(
            report, output_note=f"{stem}.json / {stem}.md / {stem}.svg / {stem}.sarif"
        )
    )
    return 2 if blockers else 0


def _load_baseline(value: str | None, *, fail_on: str) -> ScanReport | None:
    if fail_on != "new-blockers":
        if value is not None:
            raise ValueError("--baseline requires --fail-on new-blockers")
        return None
    if value is None:
        raise ValueError("--baseline is required with --fail-on new-blockers")
    maximum = 20 * 1024 * 1024
    with Path(value).open("rb") as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("Baseline exceeds 20 MiB")
    return ScanReport.model_validate_json(content)


def _terminal_summary(report: ScanReport, *, output_note: str) -> str:
    """按标准输出编码选取摘要语言；旧代码页无法编码中文时回退纯 ASCII。"""
    summary = render_terminal_summary(report, output_note=output_note)
    if _can_encode(summary):
        return summary
    summary = render_terminal_summary(report, output_note=output_note, english=True)
    if _can_encode(summary):
        return summary
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    return summary.encode(encoding, errors="backslashreplace").decode(encoding)


def _can_encode(text: str) -> bool:
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return True
    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-scan",
        description="Generate MXReady reports from a trusted local source directory.",
    )
    parser.add_argument("--version", action="version", version=f"MXReady {__version__}")
    parser.add_argument("local_path", help="Local repository directory to inspect")
    parser.add_argument(
        "--repo-url",
        help="Canonical public GitHub/Gitee URL; defaults to the local origin remote",
    )
    parser.add_argument(
        "--commit",
        help="Resolved 40-character Git commit SHA; defaults to the local HEAD",
    )
    parser.add_argument(
        "--output", required=True, help="Directory for JSON, Markdown, SVG, and SARIF"
    )
    parser.add_argument("--baseline", type=Path, help="Trusted baseline report JSON")
    parser.add_argument(
        "--fail-on", choices=("all-blockers", "new-blockers"), default="all-blockers"
    )
    return parser


def _local_repository(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Local repository directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Local repository path is not a directory: {path}")
    return path.resolve()


def _commit_sha(value: str) -> str:
    if not _COMMIT_PATTERN.fullmatch(value):
        raise ValueError("Commit must be a 40-character lowercase hexadecimal SHA.")
    return value


def _run_git(repository_root: Path, *arguments: str) -> str:
    """在只读模式下询问本地仓库；git 不可用或命令失败时返回空字符串。"""
    try:
        completed = subprocess.run(
            ("git", "-C", str(repository_root), *arguments),
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            shell=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _detect_commit(repository_root: Path) -> str:
    commit = _run_git(repository_root, "rev-parse", "HEAD")
    if not commit:
        raise ValueError(
            "Cannot resolve the local HEAD (git rev-parse HEAD failed); "
            "pass --commit with a 40-character commit SHA."
        )
    return commit


def _detect_repository_url(repository_root: Path) -> str:
    remote = _run_git(repository_root, "remote", "get-url", "origin")
    normalized = _normalize_remote_url(remote)
    if not normalized.startswith("https://"):
        raise ValueError(
            "Cannot resolve a public origin remote (git remote get-url origin failed); "
            "pass --repo-url with a GitHub/Gitee HTTPS URL."
        )
    return normalized


def _normalize_remote_url(value: str) -> str:
    """把 SSH 形式的 origin 地址转成 parse_repository_url 接受的 HTTPS 形式。"""
    candidate = value.strip()
    if "://" in candidate:
        match = _SSH_URL_REMOTE.fullmatch(candidate) if candidate.startswith("ssh://") else None
    else:
        match = _SCP_LIKE_REMOTE.fullmatch(candidate)
    if match is None:
        return candidate
    return f"https://{match.group('host')}/{match.group('path')}"


def _write_outputs(output_dir: Path, stem: str, report: ScanReport) -> str:
    """Reserve all four files without replacing evidence or following existing symlinks."""
    outputs = {
        "json": report.model_dump_json(indent=2) + "\n",
        "md": render_markdown(report),
        "svg": render_badge(report),
        "sarif": render_sarif(report),
    }
    for candidate in (stem, f"{stem}-{report.scan_id.hex}"):
        created: list[Path] = []
        try:
            with ExitStack() as stack:
                streams = []
                for extension, content in outputs.items():
                    path = output_dir / f"{candidate}.{extension}"
                    stream = stack.enter_context(path.open("x", encoding="utf-8"))
                    created.append(path)
                    streams.append((stream, content))
                for stream, content in streams:
                    stream.write(content)
        except BaseException as error:
            for path in created:
                path.unlink(missing_ok=True)
            if isinstance(error, FileExistsError):
                continue
            raise
        return candidate
    raise FileExistsError("Report output names already exist; use a different output directory")


if __name__ == "__main__":
    raise SystemExit(main())
