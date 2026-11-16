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
        tool_calls = _read_tool_calls(message.get("tool_calls"))
        if not (isinstance(content, str) and content.strip()) and not tool_calls:
            # An endpoint that answers with an empty message — no content and
            # no tool calls — has not answered. Parsing it as a normal turn
            # made the orchestration record a completed task with zero
            # findings, which the benchmark then graded as a failure with no
            # error. It is a transient endpoint failure instead: raise it as
            # retryable, so the orchestrator's backoff asks again.
            raise ProviderError("the model endpoint answered with an empty message", retryable=True)
        if isinstance(content, str) and _is_tool_call_leak(content):
            if tool_calls:
                # The same message can carry a leaked ``<invoke>`` fragment
                # in ``content`` *and* well-formed tool calls. The calls are
                # the turn's actionable part, so they win: the fragment is
                # dropped (it is protocol, not prose, and it must not reach
                # a report as an answer), and the calls are returned. Raising
                # here would discard an answer the endpoint did give and
                # spend a retry on a model that would answer the same way
                # again.
                content = ""
            else:
                # A model that speaks the tool-call protocol inside its prose
                # — MiniMax's occasional ``<invoke>`` blocks — has not
                # answered: the text is a protocol fragment, and parsing it
                # as an answer let XML reach a benchmark as the final word on
                # a question. The turn is broken the same way an empty
                # message is, and retryable for the same reason: asking again
                # is how the loop recovers a transient model failure.
                raise ProviderError(
                    "the model answered with a tool-call protocol fragment instead of an answer",
                    retryable=True,
                )
        usage = body.get("usage")
        usage_map = usage if isinstance(usage, dict) else {}
        return ModelResponse(
            content=content if isinstance(content, str) else "",
            tool_calls=tool_calls,
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


#: The tool-call protocol tags a model may leak into its prose. The open
#: tag is what the leak looks like — a ``<invoke>`` the model wrote instead
#: of an answer, sometimes with a ``<parameter>`` block inside it. Prose
#: that only *mentions* one of these does not match: the tag has to appear
#: with its bracket, which ordinary XML discussion rarely carries.
_TOOL_CALL_LEAK_MARKERS: tuple[str, ...] = (
    "<invoke",
    "</invoke>",
    "<function_call",
    "<|tool_calls|>",
    "<tool_call>",
)


def _is_tool_call_leak(content: str) -> bool:
    """Whether the content is a tool-call protocol fragment, not an answer.

    A model that is speaking the *tool-call* channel inside its ``content``
    — an ``<invoke name="...">`` block with parameters — has not answered
    the question. The fragment is raised as a retryable provider failure, so
    the loop asks again, instead of the XML reaching a report as prose.
    """
    text = content.strip()
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _TOOL_CALL_LEAK_MARKERS)


__all__ = ["OpenAICompatibleProvider", "build_messages", "build_tools"]
