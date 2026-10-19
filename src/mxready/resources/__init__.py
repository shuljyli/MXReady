"""Versioned resources distributed with MXReady."""

from importlib.resources import files
from pathlib import Path


def default_rules_directory() -> Path:
    """Installed wheels and source checkouts share the same packaged rules."""
    return Path(str(files(__package__).joinpath("rules", "v1")))


def verification_schema_bytes() -> bytes:
    return files(__package__).joinpath("schemas", "verification-result-v1.json").read_bytes()
