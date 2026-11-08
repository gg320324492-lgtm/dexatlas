"""The model endpoints, tested as the shapes they speak.

The providers are thin: a request, a response, an error. What they need
tested is not a live call — a test that needs a key is a test that does not
run — but the *shape*: the URL they post to, the document they put on the
wire, and what they do with the answer.

So the tests here check the payload the provider would send, and one of them
checks the real transport against a server on the loopback interface, so
that the shape is a shape the network would accept.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from dexatlas.agent.providers.base import (
    AssistantTurn,
    ModelRequest,
    Observation,
    ProviderError,
    ToolCall,
    ToolSpec,
)
from dexatlas.agent.providers.local import LocalModelProvider
from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider
from dexatlas.agent.providers.transport import urllib_transport


def _request() -> ModelRequest:
    """A request with one tool call and one answer."""
    return ModelRequest(
        instructions="You are the analysis agent.",
        question="Which permissions does this APK request?",
        tools=(
            ToolSpec(
                name="get_manifest",
                description="Read an APK's manifest.",
                parameters={
                    "type": "object",
                    "properties": {"project_id": {"type": "string"}},
                    "required": ["project_id"],
                },
            ),
        ),
        turns=(
            AssistantTurn(
                content="",
                tool_calls=(
                    ToolCall(id="call-1", name="get_manifest", arguments={"project_id": "apk_one"}),
                ),
            ),
            Observation(
                tool="get_manifest",
                call_id="call-1",
                content='{"tool": "get_manifest", "ok": true}',
            ),
        ),
        max_tokens=512,
    )


# -- the OpenAI-compatible endpoint ------------------------------------------


def test_the_openai_endpoint_posts_to_the_chat_completions_url() -> None:
    """The URL is the one the protocol names."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    assert provider.endpoint() == "https://example.invalid/v1/chat/completions"


def test_the_openai_payload_carries_the_instructions_the_question_and_the_tools() -> None:
    """The payload is the shape the protocol wants."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    payload = provider.build_payload(_request())

    assert payload["model"] == "a-model"
    assert payload["max_tokens"] == 512
    assert payload["temperature"] == 0.0
    assert payload["messages"][0] == {
        "role": "system",
        "content": "You are the analysis agent.",
    }
    assert payload["messages"][1] == {
        "role": "user",
        "content": "Which permissions does this APK request?",
    }
    assert payload["tools"][0] == {
        "type": "function",
        "function": {
            "name": "get_manifest",
            "description": "Read an APK's manifest.",
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
    }


def test_the_openai_payload_puts_the_tool_answer_in_the_tool_channel() -> None:
    """A tool's answer arrives as a tool message, not as an instruction."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    messages = provider.build_payload(_request())["messages"]

    assistant = messages[2]
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"][0]["function"]["name"] == "get_manifest"
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {
        "project_id": "apk_one"
    }
    tool = messages[3]
    assert tool["role"] == "tool"
    assert tool["tool_call_id"] == "call-1"
    assert "data" in tool["content"], "the answer says that it is data"


def test_the_openai_provider_reads_the_answer() -> None:
    """The answer is content, tool calls and usage."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")
    body = {
        "model": "a-model",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "the manifest asks for two permissions",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "get_manifest",
                                "arguments": '{"project_id": "apk_one"}',
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30},
    }

    response = provider.parse_response(body)

    assert response.content == "the manifest asks for two permissions"
    assert response.tool_calls[0].name == "get_manifest"
    assert response.tool_calls[0].arguments == {"project_id": "apk_one"}
    assert response.total_tokens == 150


def test_an_answer_with_arguments_that_are_not_json_is_a_model_failure() -> None:
    """A broken answer is a failure, not an empty call."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")
    body = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"id": "call-1", "function": {"name": "get_manifest", "arguments": "{oops"}}
                    ],
                }
            }
        ]
    }

    with pytest.raises(ProviderError) as raised:
        provider.parse_response(body)

    assert raised.value.retryable is False


def test_an_answer_without_a_choice_is_a_model_failure() -> None:
    """An empty answer is a failure the orchestration has to survive."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    with pytest.raises(ProviderError):
        provider.parse_response({"choices": []})


# -- the local model endpoint ------------------------------------------------


def test_the_local_endpoint_posts_to_the_chat_url() -> None:
    """The URL is the one the local protocol names."""
    provider = LocalModelProvider(base_url="http://localhost:11434", model="a-local-model")

    assert provider.endpoint() == "http://localhost:11434/api/chat"


def test_the_local_payload_is_the_local_shape() -> None:
    """The local protocol carries its options in an object of their own."""
    provider = LocalModelProvider(base_url="http://localhost:11434", model="a-local-model")

    payload = provider.build_payload(_request())

    assert payload["model"] == "a-local-model"
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0.0, "num_predict": 512}
    assert payload["messages"][0]["role"] == "system"
    assert payload["tools"][0]["function"]["name"] == "get_manifest"


def test_the_local_provider_reads_the_answer() -> None:
    """The local protocol counts its tokens under other names."""
    provider = LocalModelProvider(base_url="http://localhost:11434", model="a-local-model")
    body = {
        "model": "a-local-model",
        "message": {
            "role": "assistant",
            "content": "the manifest asks for two permissions",
            "tool_calls": [
                {"function": {"name": "get_manifest", "arguments": {"project_id": "apk_one"}}}
            ],
        },
        "prompt_eval_count": 90,
        "eval_count": 12,
    }

    response = provider.parse_response(body)

    assert response.content == "the manifest asks for two permissions"
    assert response.tool_calls[0].name == "get_manifest"
    assert response.tool_calls[0].arguments == {"project_id": "apk_one"}
    assert response.prompt_tokens == 90
    assert response.completion_tokens == 12


# -- the transport -----------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    """A server that answers with whatever it was given."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.received.append(  # type: ignore[attr-defined]
            (self.path, json.loads(body), dict(self.headers))
        )
        answer = getattr(self.server, "answer", {"choices": []})
        status = getattr(self.server, "status", 200)
        data = json.dumps(answer).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        """Keep the test output quiet."""


@pytest.fixture
def server():
    """A server on the loopback interface that records what it was sent."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.received = []  # type: ignore[attr-defined]
    httpd.answer = {  # type: ignore[attr-defined]
        "choices": [{"message": {"role": "assistant", "content": "the manifest says so"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_transport_really_posts(server) -> None:
    """The shape the provider builds is a shape the network accepts."""
    provider = OpenAICompatibleProvider(
        base_url=f"http://127.0.0.1:{server.server_address[1]}", model="a-model"
    )

    response = provider.complete(_request())

    assert response.content == "the manifest says so"
    path, payload, headers = server.received[0]  # type: ignore[attr-defined]
    assert path == "/chat/completions"
    assert payload["model"] == "a-model"
    assert headers["Content-Type"] == "application/json"


def test_a_server_that_refuses_is_a_failure_the_orchestration_can_survive(server) -> None:
    """An endpoint that answers 500 is a retryable failure."""
    server.status = 500  # type: ignore[attr-defined]
    server.answer = {"error": "boom"}  # type: ignore[attr-defined]
    provider = OpenAICompatibleProvider(
        base_url=f"http://127.0.0.1:{server.server_address[1]}", model="a-model"
    )

    with pytest.raises(ProviderError) as raised:
        provider.complete(_request())

    assert raised.value.retryable is True
    assert "500" in raised.value.message


def test_an_endpoint_that_is_not_there_is_a_failure_too() -> None:
    """Nothing listening is a failure the orchestration has to survive.

    There are two ways for a dead endpoint to fail, and which one happens is
    the machine's business rather than the provider's: the connection can be
    refused straight away, or it can be left hanging until the timeout. A
    Linux box answers a dead local port with the second one and a Windows
    box with the first, and the orchestration has to survive either.
    """
    provider = OpenAICompatibleProvider(base_url="http://127.0.0.1:1", model="a-model", timeout=0.5)

    with pytest.raises(ProviderError) as raised:
        provider.complete(_request())

    assert raised.value.retryable is True, "a dead endpoint is worth trying again"
    assert (
        "could not be reached" in raised.value.message
        or "did not answer in time" in raised.value.message
    ), raised.value.message


def test_the_transport_rejects_an_answer_that_is_not_json() -> None:
    """An answer that is not a JSON document is a failure, not a crash."""

    class _Bad:
        def read(self) -> bytes:
            return b"<html>not json</html>"

        def __enter__(self) -> _Bad:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    def fake_urlopen(request: Any, timeout: float = 0.0) -> _Bad:
        return _Bad()

    import urllib.request

    original = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
    try:
        with pytest.raises(ProviderError) as raised:
            urllib_transport("http://example.invalid", {}, {}, 1.0)
    finally:
        urllib.request.urlopen = original  # type: ignore[assignment]

    assert raised.value.retryable is False
    assert "not JSON" in raised.value.message
