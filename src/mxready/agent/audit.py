"""Append-only, bounded JSONL audit for code workspace tool decisions."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

MAX_AUDIT_BYTES = 5 * 1024 * 1024
MAX_AUDIT_RECORDS = 3
MAX_FIELD = 1000
_SENSITIVE_FLAG = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|credential|authorization)\s*[=:]\s*\S+"
)
_SENSITIVE_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def redact(value: str) -> str:
    cleaned = _SENSITIVE_TOKEN.sub("sk-***", value)
    cleaned = _SENSITIVE_FLAG.sub(lambda match: match.group(1) + "=***", cleaned)
    return cleaned[:MAX_FIELD]


class AuditLog:
    """Record tool decisions without file content, model messages, or keys."""

    def __init__(self, path: Path, *, session_id: str) -> None:
        self.path = path
        self.session_id = session_id
        self._lock = threading.Lock()

    def _rotate(self) -> None:
        if not self.path.is_file() or self.path.stat().st_size < MAX_AUDIT_BYTES:
            return
        for index in range(MAX_AUDIT_RECORDS - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            if source.is_file():
                os.replace(source, self.path.with_name(f"{self.path.name}.{index + 1}"))
        os.replace(self.path, self.path.with_name(f"{self.path.name}.1"))

    def record(
        self,
        *,
        tool: str,
        decision: str,
        target: str = "",
        result: str = "",
        error: str = "",
        duration_ms: int = 0,
    ) -> None:
        payload = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "session": self.session_id,
            "tool": tool,
            "decision": decision,
            "target": redact(target),
            "result": redact(result),
            "error": redact(error),
            "duration_ms": max(0, duration_ms),
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)[:8192] + "\n"
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate()
                descriptor = os.open(
                    self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600
                )
                try:
                    os.write(descriptor, line.encode("utf-8"))
                finally:
                    os.close(descriptor)
            except OSError:
                # Auditing must never crash the agent; the UI still shows the decision.
                pass


def record_duration(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
