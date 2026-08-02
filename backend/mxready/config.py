"""应用配置：默认值 + 环境变量注入（12-factor）。

所有可配置项均支持通过 `MXREADY_*` 环境变量覆盖，未设置时使用内置默认值。
参见仓库根目录 `.env.example` 与 `docs/deployment.md`。
"""

import os
from dataclasses import dataclass
from pathlib import Path

_ENV_PREFIX = "MXREADY_"


def _path_env(name: str, default: str) -> Path:
    return Path(os.getenv(_ENV_PREFIX + name, default))


def _optional_path_env(name: str) -> Path | None:
    raw = os.getenv(_ENV_PREFIX + name)
    if raw is None or not raw.strip():
        return None
    return Path(raw.strip())


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(_ENV_PREFIX + name, str(default)))
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(_ENV_PREFIX + name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


def _hosts_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(_ENV_PREFIX + name)
    if raw is None or not raw.strip():
        return default
    return tuple(host.strip() for host in raw.split(",") if host.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    # 路径
    data_dir: Path = Path("data")
    rules_dir: Path = Path("rules/v1")
    extra_rules_dir: Path | None = None
    temp_dir: Path = Path("data/tmp")
    frontend_dist: Path = Path("frontend/dist")
    # 日志
    log_level: str = "INFO"
    # 托管平台白名单（保持安全默认值）
    allowed_hosts: tuple[str, ...] = ("github.com", "gitee.com")
    # 数据保留（0 = 不自动清理，默认关闭以保护申报证据）
    scan_retention_days: int = 0
    # 防护（默认关闭限流，公网部署时按需开启）
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 20
    max_concurrent_scans: int = 2
    max_request_bytes: int = 1_048_576

    @classmethod
    def from_env(cls) -> "Settings":
        """读取 `MXREADY_*` 环境变量构造配置，未设置项使用默认值。"""
        return cls(
            data_dir=_path_env("DATA_DIR", "data"),
            rules_dir=_path_env("RULES_DIR", "rules/v1"),
            extra_rules_dir=_optional_path_env("EXTRA_RULES_DIR"),
            temp_dir=_path_env("TEMP_DIR", "data/tmp"),
            frontend_dist=_path_env("FRONTEND_DIR", "frontend/dist"),
            log_level=os.getenv(_ENV_PREFIX + "LOG_LEVEL", "INFO"),
            allowed_hosts=_hosts_env("ALLOWED_HOSTS", ("github.com", "gitee.com")),
            scan_retention_days=_int_env("SCAN_RETENTION_DAYS", 0),
            rate_limit_enabled=_bool_env("RATE_LIMIT_ENABLED", False),
            rate_limit_per_minute=_int_env("RATE_LIMIT_PER_MINUTE", 20),
            max_concurrent_scans=_int_env("MAX_CONCURRENT_SCANS", 2),
            max_request_bytes=_int_env("MAX_REQUEST_BYTES", 1_048_576),
        )
