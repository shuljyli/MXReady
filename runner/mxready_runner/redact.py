from __future__ import annotations

import re

MAX_OUTPUT_BYTES = 16_384

_SENSITIVE_NAME = r"[A-Z0-9_]*(?:TOKEN|PASSWORD|SECRET|KEY|AUTHORIZATION)"
_BEARER = re.compile(r"(?i)(\bAuthorization\s*:\s*Bearer\s+)\S+")
_QUOTED_ASSIGNMENT = re.compile(rf"(?i)(\b{_SENSITIVE_NAME}\b\s*[:=]\s*)([\"'])(.*?)(\2)")
_ASSIGNMENT = re.compile(rf"(?i)(\b{_SENSITIVE_NAME}\b\s*[:=]\s*)([^\s,;]+)")
_UNIX_HOME = re.compile(r"(?i)(/(?:home|Users)/)[^/\s]+")
_WINDOWS_HOME = re.compile(r"(?i)([A-Z]:\\Users\\)[^\\\s]+")


def redact_text(value: str) -> str:
    redacted = _BEARER.sub(r"\1[REDACTED]", value)
    redacted = _QUOTED_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]{match.group(2)}",
        redacted,
    )
    redacted = _ASSIGNMENT.sub(r"\1[REDACTED]", redacted)
    redacted = _UNIX_HOME.sub(r"\1[USER]", redacted)
    return _WINDOWS_HOME.sub(r"\1[USER]", redacted)


def truncate_text(value: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return value
    suffix = b"[TRUNCATED]"
    prefix = encoded[: max(0, max_bytes - len(suffix))]
    return prefix.decode("utf-8", errors="ignore") + suffix.decode("ascii")


def sanitize_output(value: str | None) -> str:
    return truncate_text(redact_text(value or ""))
