import threading
from pathlib import Path

import pytest

from mxready.agent.providers.base import Completion, ToolCall, Usage
from mxready.agent.session import AgentCancelled, AgentSession, SessionError
from mxready.agent.tools.base import ToolError, ToolRegistry


class ScriptedProvider:
    def __init__(self, completions):
        self.completions = list(completions)
        self.calls = []

    def complete(self, messages, tools=()):
        self.calls.append((len(messages), tuple(messages)))
        return self.completions.pop(0)


class EchoTool:
    name = "echo"
    description = "echo the text"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}}

    def __init__(self):
        self.calls = []

    def run(self, arguments):
        value = arguments.get("text")
        if not isinstance(value, str):
            raise ToolError("text is required")
        self.calls.append(value)
        return f"echo:{value}"


def _session(provider, tools=(), **kwargs):
    root = kwargs.pop("workspace_root", None)
    return AgentSession(
        provider,
        ToolRegistry(list(tools)),
        workspace_root=root or Path.cwd(),
        language="en",
        **kwargs,
    )


def test_simple_reply_accumulates_usage_and_emits_text():
    provider = ScriptedProvider(
        [Completion("hello", (), Usage(input_tokens=10, output_tokens=2))]
    )
    seen = []
    session = _session(provider)
    assert session.send("hi", on_text=seen.append) == "hello"
    assert seen == ["hello"]
    assert session.usage.total == 12
    assert [message.role for message in session.messages] == ["system", "user", "assistant"]


def test_tool_roundtrip_feeds_output_back_to_the_model():
    tool = EchoTool()
    provider = ScriptedProvider(
        [
            Completion("calling", (ToolCall("t1", "echo", '{"text": "abc"}'),), Usage(1, 1)),
            Completion("done", (), Usage(1, 1)),
        ]
    )
    session = _session(provider, [tool])
    assert session.send("run") == "done"
    assert tool.calls == ["abc"]
    assert [message.role for message in session.messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    assert session.messages[3].content == "echo:abc"
    assert session.messages[3].tool_call_id == "t1"


def test_tool_failures_are_reported_to_the_model_without_raising():
    tool = EchoTool()
    provider = ScriptedProvider(
        [
            Completion("", (ToolCall("t1", "echo", "not json"),), Usage()),
            Completion("done", (), Usage()),
        ]
    )
    session = _session(provider, [tool])
    assert session.send("run") == "done"
    assert "ERROR:" in session.messages[3].content
    assert tool.calls == []


def test_unknown_tool_and_round_limit_stop_the_loop():
    provider = ScriptedProvider(
        [Completion("", (ToolCall("t1", "missing", "{}"),), Usage())] * 2
    )
    session = _session(provider, max_rounds=2)
    with pytest.raises(SessionError, match="2 rounds"):
        session.send("loop")
    assert provider.calls[1][1][-1].role == "tool"
    assert "Unknown tool" in provider.calls[1][1][-1].content


def test_token_budget_is_enforced():
    provider = ScriptedProvider(
        [Completion("x", (), Usage(input_tokens=100, output_tokens=100))]
    )
    session = _session(provider, max_total_tokens=50)
    with pytest.raises(SessionError, match="token budget"):
        session.send("hi")


def test_cancellation_is_checked_before_provider_calls():
    cancel = threading.Event()
    cancel.set()
    provider = ScriptedProvider([Completion("never", (), Usage())])
    session = _session(provider)
    with pytest.raises(AgentCancelled):
        session.send("hi", cancel=cancel)
    assert provider.calls == []


def test_messages_are_validated_before_entering_the_loop():
    provider = ScriptedProvider([])
    session = _session(provider)
    for value in ("   ", "x" * 32769):
        with pytest.raises(SessionError):
            session.send(value)
    assert provider.calls == []


def test_only_one_request_runs_at_a_time():
    started = threading.Event()
    release = threading.Event()

    class BlockingProvider:
        def complete(self, messages, tools=()):
            started.set()
            release.wait(timeout=5)
            return Completion("ok", (), Usage())

    session = _session(BlockingProvider())
    worker = threading.Thread(target=lambda: session.send("hi"))
    worker.start()
    assert started.wait(timeout=5)
    with pytest.raises(SessionError, match="already running"):
        session.send("again")
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()


def test_reset_clears_messages_and_usage():
    provider = ScriptedProvider([Completion("ok", (), Usage(2, 3))])
    session = _session(provider)
    session.send("hi")
    session.reset()
    assert [message.role for message in session.messages] == ["system"]
    assert session.usage.total == 0
