"""Escape terminal control characters before rendering untrusted text."""

from __future__ import annotations

import unicodedata


def safe_text(value: str) -> str:
    """Replace C0/C1 controls (except newline and tab) with visible escapes."""
    return "".join(
        f"\\u{ord(char):04x}"
        if unicodedata.category(char).startswith("C") and char not in "\n\t"
        else char
        for char in value
    )
