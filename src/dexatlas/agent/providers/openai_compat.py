"""The OpenAI-compatible model endpoint.

"OpenAI-compatible" is a shape rather than a product: a ``POST`` to
``{base_url}/chat/completions`` with a ``messages`` array, a ``tools`` array
and a ``choices`` array in the answer. Every endpoint that calls itself
compatible with that shape — the hosted one, a local server, a gateway — is
reachable through this provider without anything else changing.

The provider is thin on purpose: a request, a response, an error. What it
speaks is tested as a shape — the bytes it would send — rather than as a live
call, because a test that needs a key is a test that does not run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from dexatlas.agent.providers.base import (
    AssistantTurn,
    ModelRequest,
    ModelResponse,
    Observation,
    ProviderError,
    ToolCall,
    ToolSpec,
)
from dexatlas.agent.providers.transport import Transport, urllib_transport


def build_messages(request: ModelRequest) -> list[dict[str, Any]]:
    """The request as a ``messages`` array.

    The instructions and the question are the only two things that are *told*
    to the model. Everything the tools read arrives afterwards as a ``tool``
    message, which is the channel the protocol reserves for a tool's answer —
    and the answer carries the notice that says it is data.

    One observation does not fit that channel: a tool the *plan* called, rather
    than one the model asked for. It has no assistant ``tool_calls`` entry to
    answer, and a strict endpoint rejects a ``tool`` message whose
    ``tool_call_id`` matches nothing with a 400 ("tool result's tool id not
    found"). Such an observation is sent as a ``user`` message instead, with
    the same data notice: it still reaches the model as data and never as an
    instruction, and it does not claim the model asked for it.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": request.instructions},
        {"role": "user", "content": request.question},
    ]
    asked_for = {
        call.id
        for turn in request.turns
        if isinstance(turn, AssistantTurn)
        for call in turn.tool_calls
    }
    for turn in request.turns:
        if isinstance(turn, AssistantTurn):
            message: dict[str, Any] = {"role": "assistant", "content": turn.content}
            if turn.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, sort_keys=True),
                        },
                    }
                    for call in turn.tool_calls
                ]
            messages.append(message)
        elif isinstance(turn, Observation):
            if turn.call_id and turn.call_id in asked_for:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": turn.call_id,
                        "content": turn.as_message(),
                    }
                )
            else:
                messages.append({"role": "user", "content": turn.as_message()})
    return messages


def build_tools(tools: tuple[ToolSpec, ...]) -> list[dict[str, Any]]:
    """The request's tools, in the shape the protocol wants."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in tools
    ]


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProvider:
    """A model endpoint that speaks the OpenAI chat-completions shape."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 60.0
    transport: Transport | None = field(default=None)
    name: str = "openai-compatible"

    def endpoint(self) -> str:
        """The URL this provider posts to."""
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def headers(self) -> dict[str, str]:
        """The headers this provider sends."""
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def build_payload(self, request: ModelRequest) -> dict[str, Any]:
        """The request as the JSON document that goes on the wire."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(request),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.tools:
            payload["tools"] = build_tools(request.tools)
        return payload

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Ask the endpoint, and answer with what it said."""
        transport = self.transport or urllib_transport
        body = transport(self.endpoint(), self.build_payload(request), self.headers(), self.timeout)
        return self.parse_response(body)

    def parse_response(self, body: dict[str, Any]) -> ModelResponse:
        """Read the endpoint's answer."""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("the model endpoint answered without a choice", retryable=False)
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderError(
                "the model endpoint answered with a choice that is not an object",
                retryable=False,
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderError("the model endpoint answered without a message", retryable=False)

        content = message.get("content")
        usage = body.get("usage")
        usage_map = usage if isinstance(usage, dict) else {}
        return ModelResponse(
            content=content if isinstance(content, str) else "",
            tool_calls=_read_tool_calls(message.get("tool_calls")),
            model=str(body.get("model", self.model)),
            prompt_tokens=_as_int(usage_map.get("prompt_tokens")),
            completion_tokens=_as_int(usage_map.get("completion_tokens")),
        )


def _read_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    """The tool calls the model asked for.

    The arguments arrive as a JSON string in this protocol, and a string that
    is not JSON is a broken answer rather than an empty call: it is raised, so
    the orchestration treats it as a model failure rather than as a model that
    asked for nothing.
    """
    if not isinstance(raw, list):
        return ()
    calls: list[ToolCall] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ProviderError(
                "the model asked for a tool call that is not an object", retryable=False
            )
        function = entry.get("function")
        if not isinstance(function, dict):
            raise ProviderError(
                "the model asked for a tool call without a function", retryable=False
            )
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise ProviderError("the model asked for a tool call without a name", retryable=False)
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError as exc:
                raise ProviderError(
                    f"the model asked for {name} with arguments that are not JSON",
                    retryable=False,
                ) from exc
        elif isinstance(arguments, dict):
            parsed = arguments
        else:
            parsed = {}
        call_id = entry.get("id")
        calls.append(
            ToolCall(
                id=str(call_id) if isinstance(call_id, str) and call_id else f"call-{index + 1}",
                name=name,
                arguments=parsed,
            )
        )
    return tuple(calls)


def _as_int(value: Any) -> int:
    """A number the endpoint reported, or zero when it did not report one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


__all__ = ["OpenAICompatibleProvider", "build_messages", "build_tools"]
