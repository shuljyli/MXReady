from mxready_runner.redact import redact_text, truncate_text


def test_redacts_tokens_home_paths_and_usernames() -> None:
    raw = "TOKEN=secret123 /home/alice/project Authorization: Bearer abc.def C:\\Users\\Bob\\repo"

    redacted = redact_text(raw)

    assert "secret123" not in redacted
    assert "alice" not in redacted
    assert "abc.def" not in redacted
    assert "Bob" not in redacted
    assert "[REDACTED]" in redacted


def test_truncation_has_a_hard_16_kib_character_ceiling() -> None:
    truncated = truncate_text("x" * 20_000)

    assert len(truncated.encode("utf-8")) <= 16_384
    assert truncated.endswith("[TRUNCATED]")
