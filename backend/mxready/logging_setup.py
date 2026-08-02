"""统一日志配置：JSON 结构化输出 + 敏感信息脱敏。

只配置 `mxready` 命名空间的 logger；uvicorn 自身与访问日志保持默认，
避免重复输出与格式不一致。脱敏规则与 `runner/mxready_runner/redact.py` 对齐。
"""

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any, Final

_LOGGER_NAME: Final = "mxready"

# stdlib LogRecord 自带的属性不进 JSON 字段
_SKIP_ATTRS: Final = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message", "asctime",
    }
)

_URL_CREDENTIALS = re.compile(r"(://[^/@\s:]+):([^/@\s]+)@")
_SENSITIVE_NAME = r"[A-Z0-9_]*(?:TOKEN|PASSWORD|SECRET|KEY|AUTHORIZATION)"
_ASSIGNMENT = re.compile(rf"(?i)(\b{_SENSITIVE_NAME}\b\s*[:=]\s*)([^\s,;]+)")
_UNIX_HOME = re.compile(r"(?i)(/(?:home|Users)/)[^/\s]+")
_WINDOWS_HOME = re.compile(r"(?i)([A-Z]:\\Users\\)[^\\\s]+")
_TOKEN_PREFIX = re.compile(r"(?i)\b(?:ghp|gho|ghu|glpat|github_pat|hf_)[A-Za-z0-9_\-]{6,}")


def _redact_message(message: str) -> str:
    redacted = _URL_CREDENTIALS.sub(r"\1:***@", message)
    redacted = _ASSIGNMENT.sub(r"\1[REDACTED]", redacted)
    redacted = _UNIX_HOME.sub(r"\1[USER]", redacted)
    redacted = _WINDOWS_HOME.sub(r"\1[USER]", redacted)
    return _TOKEN_PREFIX.sub("[REDACTED]", redacted)


class _JsonFormatter(logging.Formatter):
    """输出单行 JSON：{ts, level, logger, message} + 自定义 extra 字段。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_message(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP_ATTRS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """为 `mxready` logger 配置 JSON 结构化输出（幂等，可重复调用）。"""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return

    level = getattr(logging, str(log_level).upper(), logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
