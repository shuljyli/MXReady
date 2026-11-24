"""Dependency-free zh/en helpers shared by reporting and the optional terminal."""

from __future__ import annotations

DEFAULT_LANGUAGE = "zh"

_ALIASES = {
    "zh": "zh",
    "zh-cn": "zh",
    "zh-hans": "zh",
    "cn": "zh",
    "chinese": "zh",
    "中文": "zh",
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "英文": "en",
}


def normalize_language(value: str | None) -> str | None:
    """Return the canonical language code, or None when the value is unsupported."""
    if value is None:
        return None
    return _ALIASES.get(value.strip().casefold())


def tr(language: str, zh: str, en: str) -> str:
    """Pick the English text only for the exact English language code."""
    return en if language == "en" else zh
