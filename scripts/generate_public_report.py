from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from mxready.errors import MxReadyError
from mxready.models import ScanReport, StaticStatus
from mxready.reporting.markdown import render_markdown
from mxready.repository.git_client import GitClient
from mxready.repository.github_archive import GitHubArchiveClient
from mxready.repository.identity import parse_repository_url
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog

_LABEL_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_public_report(
    repository_url: str,
    *,
    label: str,
    output_dir: Path,
    work_dir: Path,
    requested_ref: str | None = None,
    git_client: GitClient | None = None,
    archive_client: GitHubArchiveClient | None = None,
) -> ScanReport:
    """Safely clone a public repository and write commit-pinned evidence."""
    if _LABEL_PATTERN.fullmatch(label) is None:
        raise ValueError("Label must contain lowercase letters, numbers, and hyphens only.")

    identity = parse_repository_url(repository_url)
    output_dir = Path(output_dir)
    work_dir = Path(work_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    client = git_client or GitClient()
    with tempfile.TemporaryDirectory(prefix="mxready-evidence-", dir=work_dir) as temporary:
        repository_root = Path(temporary) / "git-repository"
        try:
            commit = client.clone(identity, requested_ref, repository_root)
        except MxReadyError as error:
            if (
                identity.provider != "github"
                or error.code not in {"CLONE_TIMEOUT", "SCAN_INTERNAL_ERROR"}
            ):
                raise
            repository_root = Path(temporary) / "archive-repository"
            commit = (archive_client or GitHubArchiveClient()).clone(
                identity,
                requested_ref,
                repository_root,
            )
        report = ScanAnalyzer(
            load_rule_catalog(_PROJECT_ROOT / "rules" / "v1")
        ).analyze(
            repository_root,
            repository_url=identity.clone_url,
            commit=commit,
            scan_id=uuid5(NAMESPACE_URL, f"{identity.clone_url}@{commit}"),
            stage_callback=lambda status: None,
        )

    (output_dir / f"{label}.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{label}.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        report = generate_public_report(
            arguments.repository_url,
            label=arguments.label,
            output_dir=Path(arguments.output),
            work_dir=Path(arguments.work_dir),
            requested_ref=arguments.ref,
        )
    except (MxReadyError, OSError, ValueError) as error:
        print(f"MXReady public scan error: {error}", file=sys.stderr)
        return 1

    print(
        f"MXReady: wrote {arguments.label}.json and {arguments.label}.md "
        f"for {report.repository.commit} ({report.summary.total_count} findings)"
    )
    return 2 if report.static_status is StaticStatus.BLOCKED else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-scan-public",
        description=(
            "Safely clone a public GitHub/Gitee repository and generate "
            "commit-pinned MXReady evidence."
        ),
    )
    parser.add_argument("repository_url", help="Public GitHub/Gitee HTTPS URL")
    parser.add_argument(
        "--label",
        required=True,
        help="Lowercase output label containing only letters, numbers, and hyphens",
    )
    parser.add_argument("--ref", help="Optional branch, tag, or 40-character commit")
    parser.add_argument("--output", required=True, help="Directory for JSON and Markdown")
    parser.add_argument(
        "--work-dir",
        default="data/public-scan-work",
        help="Temporary clone parent (clones are removed after each scan)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
