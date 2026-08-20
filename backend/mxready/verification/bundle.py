from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from mxready_runner.inspect import DEFAULT_CHECKS

from mxready import __version__
from mxready.errors import MxReadyError
from mxready.models import ScanReport

_RUNNER_FILES = (
    "__init__.py",
    "__main__.py",
    "cli.py",
    "execute.py",
    "inspect.py",
    "redact.py",
    "schema.py",
)
_SECURITY_NOTE = """# MXReady remote verification safety

This archive runs only on a host controlled by you.

- Read `mxready.yml` and every project command before running it.
- Environment inspection uses the fixed commands listed in the manifest.
- Project commands run only after your explicit approval.
- The runner never uses `sudo`, installs packages, or changes GPU drivers.
- Commands use argument arrays with `shell=False` and bounded timeouts.
- Output is redacted and truncated, but review `result.json` before sharing it.
"""

_PROJECT_COMMANDS_EXAMPLE = json.dumps(
    [
        {
            "id": "example-cuda-smoke",
            "command": [
                "python",
                "-c",
                (
                    "import torch, your_extension; "
                    "a=torch.randn(1024, device='cuda'); "
                    "b=torch.randn(1024, device='cuda'); "
                    "actual=your_extension.ops.mymuladd(a, b, 1.0); "
                    "torch.testing.assert_close(actual, a * b + 1.0); "
                    "print('MXReady example CUDA smoke passed')"
                ),
            ],
            "timeout_seconds": 120,
        }
    ],
    ensure_ascii=False,
    indent=2,
) + "\n"


def build_verification_bundle(report: ScanReport) -> bytes:
    """Build a deterministic, self-contained verification ZIP."""
    root = Path(__file__).resolve().parents[3]
    files: list[tuple[str, bytes]] = [
        (
            "mxready.yml",
            (
                json.dumps(
                    _build_manifest(report),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        ),
        ("SECURITY.md", _SECURITY_NOTE.encode("utf-8")),
        (
            "project-commands.example.json",
            _PROJECT_COMMANDS_EXAMPLE.encode("utf-8"),
        ),
    ]

    for filename in _RUNNER_FILES:
        files.append(
            (
                f"mxready_runner/{filename}",
                _read_required_file(root / "runner" / "mxready_runner" / filename),
            )
        )
    files.append(
        (
            "schemas/verification-result-v1.json",
            _read_required_file(root / "schemas" / "verification-result-v1.json"),
        )
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w") as archive:
        for name, content in files:
            _write_deterministic_file(archive, name, content)
    return output.getvalue()


def _build_manifest(report: ScanReport) -> dict:
    return {
        "schema_version": "1.0",
        "scan_id": str(report.scan_id),
        "repository_url": report.repository.url,
        "repository_commit": report.repository.commit,
        "runner_version": __version__,
        "checks": [
            {
                "id": check.id,
                "command": check.command,
                "timeout_seconds": check.timeout_seconds,
            }
            for check in DEFAULT_CHECKS
        ],
        "project_commands": [],
    }


def _read_required_file(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise MxReadyError(
            "SCAN_INTERNAL_ERROR",
            "The verification bundle source files are unavailable.",
        ) from error


def _write_deterministic_file(
    archive: zipfile.ZipFile,
    name: str,
    content: bytes,
) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, content)
