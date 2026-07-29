from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path = Path("data")
    rules_dir: Path = Path("rules/v1")
    temp_dir: Path = Path("data/tmp")
    frontend_dist: Path = Path("frontend/dist")
