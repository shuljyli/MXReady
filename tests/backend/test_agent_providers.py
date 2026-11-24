import json

import httpx
import pytest

from mxready.agent.config import ProviderConfig, fingerprint_secret, key_reference
from mxready.agent.providers import build_provider
from mxready.agent.providers.anthropic import AnthropicProvider
from mxready.agent.providers.base import (
    Message,
    ProviderError,
    ToolCall,
    ToolSpec,
)
from mxready.agent.providers.openai import OpenAIProvider


def _config(**overrides):
    values = {
        "name": "work",
        "protocol": "openai",
        "base_url": "https://api.example.com/v1",
        "model": "gpt-x",
        "key_ref": key_reference("work"),
        "fingerprint": fingerprint_secret("sk-test"),
    }
    values.update(overrides)
    return ProviderConfig(**values)


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_openai_request_and_tool_call_parsing(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "checking",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path": "README.md"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    from mxready.agent.providers import openai as module

    monkeypatch.setattr(module, "_client", lambda: _mock_client(handler))
    provider = OpenAIProvider(_config(), "sk-test")
    completion = provider.complete(
        [Message("user", "hi")],
        (ToolSpec("read_file", "read", {"type": "object"}),),
    )
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["payload"]["model"] == "gpt-x"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["tools"][0]["function"]["name"] == "read_file"
    assert completion.text == "checking"
    assert completion.tool_calls[0].arguments == '{"path": "README.md"}'
    assert completion.usage.total == 16
    assert completion.stop_reason == "tool_calls"


def test_anthropic_request_extracts_system_and_tool_results(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["key"] = request.headers["x-api-key"]
        captured["version"] = request.headers["anthropic-version"]
        captured["payload"] = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "done"},
                    {"type": "tool_use", "id": "tool_1", "name": "read_file", "input": {"p": 1}},
                ],
                "usage": {"input_tokens": 5, "output_tokens": 7},
                "stop_reason": "end_turn",
            },
        )

    from mxready.agent.providers import anthropic as module

    monkeypatch.setattr(module, "_client", lambda: _mock_client(handler))
    provider = AnthropicProvider(_config(protocol="anthropic"), "sk-ant")
    completion = provider.complete(
        [
            Message("system", "rules"),
            Message("user", "hi"),
            Message("assistant", "calling", tool_calls=(ToolCall("t1", "read_file", '{"p": 1}'),)),
            Message("tool", "output", tool_call_id="t1"),
        ]
    )
    assert captured["url"] == "https://api.example.com/v1/messages"
    assert captured["key"] == "sk-ant"
    assert captured["version"] == "2023-06-01"
    assert captured["payload"]["system"] == "rules"
    messages = captured["payload"]["messages"]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "tool_result"
    assert completion.text == "done"
    assert completion.tool_calls[0].name == "read_file"
    assert completion.usage.total == 12


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "invalid-key"),
        (403, "invalid-key"),
        (404, "not-found"),
        (429, "rate-limit"),
        (500, "server-error"),
    ],
)
def test_http_errors_are_classified(monkeypatch, status, code):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="provider rejected the request")

    from mxready.agent.providers import openai as module

    monkeypatch.setattr(module, "_client", lambda: _mock_client(handler))
    provider = OpenAIProvider(_config(), "sk-test")
    with pytest.raises(ProviderError) as error:
        provider.complete([Message("user", "hi")])
    assert error.value.code == code
    assert error.value.status == status


def test_invalid_payloads_and_missing_keys_are_reported(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    from mxready.agent.providers import openai as module

    monkeypatch.setattr(module, "_client", lambda: _mock_client(handler))
    with pytest.raises(ProviderError, match="invalid JSON"):
        OpenAIProvider(_config(), "sk-test").complete([Message("user", "hi")])
    with pytest.raises(ProviderError, match="No API key"):
        OpenAIProvider(_config(), "   ")
    with pytest.raises(ProviderError, match="No API key"):
        AnthropicProvider(_config(protocol="anthropic"), "")


def test_build_provider_selects_the_protocol():
    assert isinstance(build_provider(_config(), "sk-test"), OpenAIProvider)
    assert isinstance(
        build_provider(_config(protocol="anthropic"), "sk-test"), AnthropicProvider
    )
