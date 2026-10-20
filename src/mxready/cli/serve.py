"""Start the installed Web application with persistent per-user data."""

import argparse
import os
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import uvicorn

from mxready.app import create_app
from mxready.config import Settings


def default_data_directory() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "MXReady"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MXReady"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "mxready"


def _port(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=_port, default=8000)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    if not shutil.which("git"):
        print(
            "Git is required. Install Git and add it to PATH before starting MXReady.",
            file=sys.stderr,
        )
        return 1
    settings = Settings.from_env()
    data_dir = args.data_dir or Path(os.getenv("MXREADY_DATA_DIR", str(default_data_directory())))
    settings = replace(
        settings,
        data_dir=data_dir,
        temp_dir=Path(os.getenv("MXREADY_TEMP_DIR", str(data_dir / "tmp"))),
    )
    uvicorn.run(create_app(settings), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
