"""Protocol-neutral chat messages, tool specs, and provider errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str = "{}"


@dataclass(frozen=True)
class Message:
    role: str
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Completion:
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = ""


class ProviderError(RuntimeError):
    """A provider request failed; ``code`` is stable for UI localization."""

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class ChatProvider(Protocol):
    def complete(
        self, messages: list[Message], tools: tuple[ToolSpec, ...] = ()
    ) -> Completion: ...


def error_for_status(status: int, body: str) -> ProviderError:
    detail = " ".join(body.split())[:300]
    suffix = f": {detail}" if detail else ""
    if status in {401, 403}:
        return ProviderError(
            "invalid-key", f"The provider rejected the API key (HTTP {status})", status=status
        )
    if status == 404:
        return ProviderError(
            "not-found",
            f"The endpoint or model was not found (HTTP 404){suffix}",
            status=status,
        )
    if status == 429:
        return ProviderError(
            "rate-limit",
            f"The provider is rate limiting requests (HTTP 429){suffix}",
            status=status,
        )
    if status >= 500:
        return ProviderError(
            "server-error", f"The provider failed (HTTP {status}){suffix}", status=status
        )
    return ProviderError("http-error", f"HTTP {status}{suffix}", status=status)
