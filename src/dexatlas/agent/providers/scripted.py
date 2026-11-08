"""The scripted provider — a model that answers from a script.

This is the provider the tests run against, and it is in the package rather
than in the test tree on purpose: the fixed task suite, the benchmark harness
and a reviewer running the agent offline all need the same thing — a model
whose answer is the same on every machine and in every run, without a key and
without a network.

A script is a list of steps. A step is a response, a callable that builds one
from the request, or an exception to raise. The provider records every
request it was given, so a test can check what the model was told as well as
what it answered.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from dexatlas.agent.providers.base import ModelRequest, ModelResponse, ToolCall

#: One step of a script: a response, something that builds one, or a failure.
ScriptStep = ModelResponse | Callable[[ModelRequest], ModelResponse] | BaseException


@dataclass
class ScriptedProvider:
    """A provider that answers from a script, in order."""

    responses: list[ScriptStep] = field(default_factory=list)
    requests: list[ModelRequest] = field(default_factory=list)
    name: str = "scripted"

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Answer the next step of the script."""
        self.requests.append(request)
        if not self.responses:
            raise _ran_out()
        step = self.responses.pop(0)
        if isinstance(step, BaseException):
            raise step
        if callable(step):
            return step(request)
        return step

    @property
    def remaining(self) -> int:
        """How many steps of the script are left."""
        return len(self.responses)

    def last_request(self) -> ModelRequest | None:
        """The request the provider was given last."""
        return self.requests[-1] if self.requests else None


def _ran_out() -> Exception:
    from dexatlas.agent.providers.base import ProviderError

    return ProviderError("the script ran out of answers", retryable=False)


def tool_call(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    call_id: str = "call-1",
    content: str = "",
) -> ModelResponse:
    """A scripted answer that asks for one tool."""
    return ModelResponse(
        content=content,
        tool_calls=(ToolCall(id=call_id, name=name, arguments=dict(arguments or {})),),
        model="scripted",
    )


def tool_calls(
    calls: list[tuple[str, dict[str, Any]]],
    *,
    content: str = "",
    prefix: str = "call",
) -> ModelResponse:
    """A scripted answer that asks for several tools at once."""
    return ModelResponse(
        content=content,
        tool_calls=tuple(
            ToolCall(id=f"{prefix}-{index + 1}", name=name, arguments=dict(arguments))
            for index, (name, arguments) in enumerate(calls)
        ),
        model="scripted",
    )


def conclusion(
    statement: str,
    *,
    evidence_ids: list[str] | None = None,
    locators: list[str] | None = None,
    confidence: str = "",
) -> dict[str, Any]:
    """One conclusion, in the shape the model is asked to answer in."""
    return {
        "statement": statement,
        "evidence_ids": list(evidence_ids or []),
        "locators": list(locators or []),
        "confidence": confidence,
    }


def answer(
    conclusions: list[dict[str, Any]], *, limitations: list[str] | None = None
) -> ModelResponse:
    """A scripted final answer: the conclusions and what could not be settled."""
    document: dict[str, Any] = {"conclusions": conclusions}
    if limitations:
        document["limitations"] = list(limitations)
    return ModelResponse(content=json.dumps(document), model="scripted")


__all__ = [
    "ScriptStep",
    "ScriptedProvider",
    "answer",
    "conclusion",
    "tool_call",
    "tool_calls",
]
