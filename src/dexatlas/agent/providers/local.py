"""The local model endpoint.

A local model is reached over HTTP like any other, but it speaks a different
shape: the request carries an ``options`` object rather than a top-level
temperature, the answer counts its tokens as ``prompt_eval_count`` and
``eval_count``, and its tool calls arrive with their arguments already
decoded. This provider is that shape, and it is tested separately from the
OpenAI-compatible one — a second provider that were really the first one
again would not be a second provider at all.

The model may be anything that serves this shape: Ollama, a llama.cpp server
in its native mode, or a small local gateway.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dexatlas.agent.providers.base import (
    ModelRequest,
    ModelResponse,
    ProviderError,
    ToolCall,
)
from dexatlas.agent.providers.openai_compat import build_messages, build_tools
from dexatlas.agent.providers.transport import Transport, urllib_transport


@dataclass(frozen=True, slots=True)
class LocalModelProvider:
    """A model endpoint that serves a local model."""

    base_url: str
    model: str
    timeout: float = 300.0
    transport: Transport | None = field(default=None)
    name: str = "local-model"

    def endpoint(self) -> str:
        """The URL this provider posts to."""
        return f"{self.base_url.rstrip('/')}/api/chat"

    def headers(self) -> dict[str, str]:
        """The headers this provider sends.

        A local model usually has no key, and a header for a key that does not
        exist is a header that has to be configured somewhere else.
        """
        return {}

    def build_payload(self, request: ModelRequest) -> dict[str, Any]:
        """The request as the JSON document that goes on the wire."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(request),
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        if request.tools:
            payload["tools"] = build_tools(request.tools)
        return payload

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Ask the local model, and answer with what it said."""
        transport = self.transport or urllib_transport
        body = transport(self.endpoint(), self.build_payload(request), self.headers(), self.timeout)
        return self.parse_response(body)

    def parse_response(self, body: dict[str, Any]) -> ModelResponse:
        """Read the local model's answer."""
        message = body.get("message")
        if not isinstance(message, dict):
            raise ProviderError("the local model answered without a message", retryable=False)
        content = message.get("content")
        return ModelResponse(
            content=content if isinstance(content, str) else "",
            tool_calls=_read_tool_calls(message.get("tool_calls")),
            model=str(body.get("model", self.model)),
            prompt_tokens=_as_int(body.get("prompt_eval_count")),
            completion_tokens=_as_int(body.get("eval_count")),
        )


def _read_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    """The tool calls the local model asked for.

    This protocol sends the arguments already decoded, and it does not number
    the calls — so the numbers here are ours, and they are only ever used to
    match an answer to the question that asked for it.
    """
    if not isinstance(raw, list):
        return ()
    calls: list[ToolCall] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ProviderError(
                "the local model asked for a tool call that is not an object", retryable=False
            )
        function = entry.get("function")
        if not isinstance(function, dict):
            raise ProviderError(
                "the local model asked for a tool call without a function", retryable=False
            )
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise ProviderError(
                "the local model asked for a tool call without a name", retryable=False
            )
        arguments = function.get("arguments")
        calls.append(
            ToolCall(
                id=f"call-{index + 1}",
                name=name,
                arguments=arguments if isinstance(arguments, dict) else {},
            )
        )
    return tuple(calls)


def _as_int(value: Any) -> int:
    """A number the endpoint reported, or zero when it did not report one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


__all__ = ["LocalModelProvider"]
