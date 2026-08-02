import json
import logging

from mxready.logging_setup import (
    _JsonFormatter,
    _redact_message,
)


def test_redact_url_credentials() -> None:
    value = "cloning https://alice:s3cr3t@github.com/example/repo.git"
    redacted = _redact_message(value)
    assert "s3cr3t" not in redacted
    assert ":***@" in redacted


def test_redact_sensitive_assignment() -> None:
    assert "abc123" not in _redact_message("API_TOKEN=abc123def456")


def test_redact_home_dirs() -> None:
    assert "/home/[USER]" in _redact_message("/home/alice/code/main.cpp")
    assert r"Users\[USER]" in _redact_message(r"C:\Users\alice\code")


def test_redact_token_prefixes() -> None:
    assert _redact_message("token ghp_abcdefghijklmnopq") == "token [REDACTED]"


def test_json_formatter_emits_structured_record_with_redaction() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="mxready.services.scans",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="scan started repo=https://alice:s3cr3t@github.com/example/repo.git",
        args=(),
        exc_info=None,
    )
    record.scan_id = "abc-123"  # type: ignore[attr-defined]
    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "mxready.services.scans"
    assert payload["scan_id"] == "abc-123"
    assert "s3cr3t" not in payload["message"]
    assert ":***@" in payload["message"]
