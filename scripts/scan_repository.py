from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from mxready.errors import MxReadyError
from mxready.models import ScanReport, StaticStatus
from mxready.reporting.badge import render_badge
from mxready.reporting.markdown import render_markdown
from mxready.repository.identity import parse_repository_url
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog

_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        repository_root = _local_repository(arguments.local_path)
        commit = _commit_sha(arguments.commit)
        identity = parse_repository_url(arguments.repo_url)
        report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
            repository_root,
            repository_url=identity.clone_url,
            commit=commit,
            scan_id=uuid5(NAMESPACE_URL, f"{identity.clone_url}@{commit}"),
            stage_callback=lambda status: None,
        )
        output_dir = Path(arguments.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{identity.name}-{commit[:12]}"
        _write_outputs(output_dir, stem, report)
    except (MxReadyError, OSError, ValueError) as error:
        print(f"MXReady scan error: {error}", file=sys.stderr)
        return 1

    print(
        f"MXReady: wrote {stem}.json, {stem}.md, and {stem}.svg "
        f"({report.summary.total_count} findings)"
    )
    return 2 if report.static_status is StaticStatus.BLOCKED else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-scan",
        description="Generate MXReady reports from a trusted local source directory.",
    )
    parser.add_argument("local_path", help="Local repository directory to inspect")
    parser.add_argument("--repo-url", required=True, help="Canonical public GitHub/Gitee URL")
    parser.add_argument("--commit", required=True, help="Resolved 40-character Git commit SHA")
    parser.add_argument("--output", required=True, help="Directory for JSON, Markdown, and SVG")
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


def _write_outputs(output_dir: Path, stem: str, report: ScanReport) -> None:
    (output_dir / f"{stem}.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.svg").write_text(
        render_badge(report),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
