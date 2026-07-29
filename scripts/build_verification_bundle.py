from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from mxready.errors import MxReadyError
from mxready.models import ScanReport
from mxready.verification.bundle import build_verification_bundle
from pydantic import ValidationError


def build_bundle_from_report(report_path: Path, output_path: Path) -> None:
    report = ScanReport.model_validate_json(
        Path(report_path).read_text(encoding="utf-8-sig")
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_verification_bundle(report))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        build_bundle_from_report(arguments.report, arguments.output)
    except (MxReadyError, OSError, UnicodeError, ValidationError, ValueError) as error:
        print(f"MXReady bundle error: {error}", file=sys.stderr)
        return 1

    print(f"MXReady: wrote verification bundle to {arguments.output}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-build-bundle",
        description="Build a safe-default MXReady verification ZIP from a JSON report.",
    )
    parser.add_argument("report", type=Path, help="MXReady JSON report")
    parser.add_argument("--output", type=Path, required=True, help="Output ZIP path")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
