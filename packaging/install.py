"""Shared installer for the release ZIPs. Requires Python 3.11+, pip/venv and Git."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only wheels in packages/")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):  # noqa: UP036 - bootstrap runs before installing the package
        parser.error("Python 3.11 or newer is required")
    if not shutil.which("git"):
        parser.error("Install Git and add it to PATH before installing MXReady")
    root = Path(__file__).resolve().parent
    wheels = list((root / "packages").glob("mxready-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one MXReady wheel in packages/")
    wheel = wheels[0]
    expected = (root / "WHEEL.sha256").read_text(encoding="ascii").strip()
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
        parser.error("Wheel checksum mismatch; download and extract the release again")
    environment = root / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not executable.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    command = [
        str(executable),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--only-binary=:all:",
    ]
    if args.offline:
        command += ["--no-index", "--find-links", str(root / "packages")]
    command.append(str(wheel))
    subprocess.run(command, check=True, timeout=600)
    print("MXReady installed. Run the start script, then open http://127.0.0.1:8000 .")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
