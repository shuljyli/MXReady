"""Anthropic Messages API provider."""

from __future__ import annotations

import json

import httpx

from mxready import __version__
from mxready.agent.config import ProviderConfig, endpoint_url
from mxready.agent.providers.base import (
    ChatProvider,
    Completion,
    Message,
    ProviderError,
    ToolCall,
    ToolSpec,
    Usage,
    error_for_status,
)

MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_TEXT = 200_000
MAX_TOOL_CALLS = 32
ANTHROPIC_VERSION = "2023-06-01"


def _client() -> httpx.Client:
    return httpx.Client(
        verify=True,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(180.0, connect=10.0),
    )


def _tool_input(arguments: str) -> dict[str, object]:
    try:
        value = json.loads(arguments) if arguments.strip() else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {"value": value}


def _message_payload(messages: list[Message]) -> tuple[str, list[dict[str, object]]]:
    system_parts: list[str] = []
    converted: list[dict[str, object]] = []

    def append(role: str, blocks: list[dict[str, object]]) -> None:
        if not blocks:
            return
        if converted and converted[-1]["role"] == role:
            existing = converted[-1]["content"]
            if isinstance(existing, list):
                existing.extend(blocks)
            return
        converted.append({"role": role, "content": blocks})

    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
        elif message.role == "user":
            append("user", [{"type": "text", "text": message.content}])
        elif message.role == "assistant":
            blocks: list[dict[str, object]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls[:MAX_TOOL_CALLS]:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": _tool_input(call.arguments),
                    }
                )
            append("assistant", blocks)
        elif message.role == "tool":
            append(
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id or "",
                        "content": message.content,
                    }
                ],
            )
    return "\n\n".join(part for part in system_parts if part), converted


def _tool_payload(spec: ToolSpec) -> dict[str, object]:
    return {
        "name": spec.name,
        "description": spec.description,
        "input_schema": spec.parameters,
    }


def _parse_content(value: object) -> tuple[str, tuple[ToolCall, ...]]:
    if not isinstance(value, list):
        return "", ()
    texts: list[str] = []
    calls: list[ToolCall] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
        elif kind == "tool_use" and len(calls) < MAX_TOOL_CALLS:
            name = item.get("name")
            if not isinstance(name, str) or not name:
                continue
            arguments = item.get("input", {})
            calls.append(
                ToolCall(
                    id=str(item.get("id") or f"call_{len(calls)}"),
                    name=name[:100],
                    arguments=json.dumps(arguments, ensure_ascii=False),
                )
            )
    return "".join(texts)[:MAX_TEXT], tuple(calls)


def _usage(value: object) -> Usage:
    if not isinstance(value, dict):
        return Usage()
    prompt = value.get("input_tokens", 0)
    completion = value.get("output_tokens", 0)
    return Usage(
        input_tokens=prompt if isinstance(prompt, int) and prompt >= 0 else 0,
        output_tokens=completion if isinstance(completion, int) and completion >= 0 else 0,
    )


class AnthropicProvider(ChatProvider):
    def __init__(self, config: ProviderConfig, api_key: str) -> None:
        if not api_key.strip():
            raise ProviderError("missing-key", "No API key is configured for this provider")
        self.config = config
        self._api_key = api_key.strip()

    @property
    def url(self) -> str:
        return endpoint_url(self.config.base_url, "anthropic")

    def complete(
        self, messages: list[Message], tools: tuple[ToolSpec, ...] = ()
    ) -> Completion:
        system, converted = _message_payload(messages)
        payload: dict[str, object] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": converted,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [_tool_payload(spec) for spec in tools]
        client = _client()
        try:
            with client:
                response = client.post(
                    self.url,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": ANTHROPIC_VERSION,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": f"mxready-agent/{__version__}",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise ProviderError("timeout", "The provider request timed out") from error
        except httpx.HTTPError as error:
            raise ProviderError("network", f"Network error: {error}") from error
        if response.status_code >= 400:
            raise error_for_status(response.status_code, response.text)
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ProviderError("invalid-response", "The provider response is too large")
        try:
            data = response.json()
        except ValueError as error:
            raise ProviderError("invalid-response", "The provider returned invalid JSON") from error
        if not isinstance(data, dict):
            raise ProviderError("invalid-response", "The provider returned an invalid payload")
        text, calls = _parse_content(data.get("content"))
        return Completion(
            text=text,
            tool_calls=calls,
            usage=_usage(data.get("usage")),
            stop_reason=str(data.get("stop_reason") or "")[:100],
        )
