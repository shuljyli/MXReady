"""Standalone BYOK code harness: the code workspace of the full-screen terminal."""

from __future__ import annotations

from collections.abc import Sequence

from mxready.cli.terminal import main as terminal_main


def main(argv: Sequence[str] | None = None) -> int:
    return terminal_main(argv, prog="mxready-agent", force_code=True)


if __name__ == "__main__":
    raise SystemExit(main())
