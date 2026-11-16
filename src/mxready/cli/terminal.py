"""Launch the optional full-screen terminal; help/version need no TUI dependencies."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from mxready import __version__
from mxready.cli.serve import default_data_directory


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mxready", description="MXReady full-screen terminal.")
    parser.add_argument("--version", action="version", version=f"MXReady {__version__}")
    parser.add_argument(
        "project", nargs="?", type=Path, default=Path.cwd(), help="Project directory"
    )
    parser.add_argument("--output-dir", type=Path, help="Directory for scan reports and bundles")
    parser.add_argument(
        "--no-state", action="store_true", help="Do not read or write TUI history/catalog"
    )
    args = parser.parse_args(argv)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            "MXReady requires an interactive terminal. For scripts use mxready-scan.",
            file=sys.stderr,
        )
        return 1
    project_dir = args.project.expanduser().resolve()
    if not project_dir.is_dir():
        print(f"Project directory does not exist: {project_dir}", file=sys.stderr)
        return 1
    data_dir = Path(os.getenv("MXREADY_DATA_DIR", str(default_data_directory())))
    output_dir = args.output_dir.expanduser().absolute() if args.output_dir else None
    try:
        from mxready.tui.app import MXReadyApp
    except ModuleNotFoundError as error:
        if error.name is None or not error.name.startswith(("textual", "rich")):
            raise
        print(
            'Install terminal support first: python -m pip install "mxready[tui]"', file=sys.stderr
        )
        return 1
    MXReadyApp(
        project_dir=project_dir,
        output_dir=output_dir,
        default_output_dir=(data_dir / "reports").expanduser().absolute(),
        state_path=None
        if args.no_state
        else (data_dir / "tui" / "state.db").expanduser().absolute(),
    ).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
