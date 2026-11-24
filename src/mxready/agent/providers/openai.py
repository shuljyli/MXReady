"""OpenAI-compatible ``/chat/completions`` provider."""

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


def _client() -> httpx.Client:
    return httpx.Client(
        verify=True,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(180.0, connect=10.0),
    )


def _message_payload(message: Message) -> dict[str, object]:
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id or "",
            "content": message.content,
        }
    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls[:MAX_TOOL_CALLS]
            ],
        }
    return {"role": message.role, "content": message.content}


def _tool_payload(spec: ToolSpec) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


def _content_text(value: object) -> str:
    if isinstance(value, str):
        return value[:MAX_TEXT]
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)[:MAX_TEXT]
    return ""


def _parse_tool_calls(value: object) -> tuple[ToolCall, ...]:
    if not isinstance(value, list):
        return ()
    calls: list[ToolCall] = []
    for index, item in enumerate(value[:MAX_TOOL_CALLS]):
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        arguments = function.get("arguments", "{}")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False)
        if len(arguments) > 64 * 1024:
            arguments = "{}"
        call_id = item.get("id")
        calls.append(
            ToolCall(
                id=str(call_id) if isinstance(call_id, str) and call_id else f"call_{index}",
                name=name[:100],
                arguments=arguments,
            )
        )
    return tuple(calls)


def _usage(value: object) -> Usage:
    if not isinstance(value, dict):
        return Usage()
    prompt = value.get("prompt_tokens", 0)
    completion = value.get("completion_tokens", 0)
    return Usage(
        input_tokens=prompt if isinstance(prompt, int) and prompt >= 0 else 0,
        output_tokens=completion if isinstance(completion, int) and completion >= 0 else 0,
    )


class OpenAIProvider(ChatProvider):
    def __init__(self, config: ProviderConfig, api_key: str) -> None:
        if not api_key.strip():
            raise ProviderError("missing-key", "No API key is configured for this provider")
        self.config = config
        self._api_key = api_key.strip()

    @property
    def url(self) -> str:
        return endpoint_url(self.config.base_url, "openai")

    def complete(
        self, messages: list[Message], tools: tuple[ToolSpec, ...] = ()
    ) -> Completion:
        payload: dict[str, object] = {
            "model": self.config.model,
            "messages": [_message_payload(message) for message in messages],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = [_tool_payload(spec) for spec in tools]
            payload["tool_choice"] = "auto"
        client = _client()
        try:
            with client:
                response = client.post(
                    self.url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
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
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("invalid-response", "The provider returned no choices")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise ProviderError("invalid-response", "The provider returned an invalid choice")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderError("invalid-response", "The provider returned no message")
        return Completion(
            text=_content_text(message.get("content")),
            tool_calls=_parse_tool_calls(message.get("tool_calls")),
            usage=_usage(data.get("usage")),
            stop_reason=str(choice.get("finish_reason") or "")[:100],
        )
