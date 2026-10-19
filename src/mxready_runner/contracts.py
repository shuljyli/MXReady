"""Versioned environment-check contract shared with the Web service (stdlib only)."""

from mxready_runner.schema import CommandSpec

DEFAULT_CHECKS = (
    CommandSpec("uname", ["uname", "-a"], 10),
    CommandSpec("python-version", ["python", "--version"], 10),
    CommandSpec("mx-smi-version", ["mx-smi", "--version"], 10),
    CommandSpec("mx-smi", ["mx-smi"], 20),
    CommandSpec(
        "pytorch-device",
        [
            "python",
            "-c",
            (
                "import torch; available=torch.cuda.is_available(); "
                "count=torch.cuda.device_count(); print(torch.__version__); "
                "print(available); print(count); "
                "name=torch.cuda.get_device_name(0) if available and count else ''; "
                "print(name); "
                "raise SystemExit(0 if available and count > 0 else 1)"
            ),
        ],
        30,
    ),
)
