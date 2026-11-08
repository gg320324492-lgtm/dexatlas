"""The providers the agent can talk to.

One interface, and three implementations:

* :class:`~dexatlas.agent.providers.openai_compat.OpenAICompatibleProvider` —
  an endpoint that speaks the OpenAI chat-completions shape;
* :class:`~dexatlas.agent.providers.local.LocalModelProvider` — a local model
  endpoint;
* :class:`~dexatlas.agent.providers.scripted.ScriptedProvider` — a model that
  answers from a script, for tests, benchmarks and offline runs.

The orchestration does not know which one it is talking to, and the request
keeps the instructions and the tool observations in separate channels: the
text that came out of an analysed APK is data, and the check that refuses a
request whose instructions carry it is in
:func:`~dexatlas.agent.providers.base.assert_instructions_are_clean`.
"""

from __future__ import annotations

from dexatlas.agent.providers.base import (
    DATA_NOTICE,
    AssistantTurn,
    InstructionsAreNotClean,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    Observation,
    ProviderError,
    ToolCall,
    ToolSpec,
    assert_instructions_are_clean,
)
from dexatlas.agent.providers.local import LocalModelProvider
from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider
from dexatlas.agent.providers.scripted import ScriptedProvider

__all__ = [
    "DATA_NOTICE",
    "AssistantTurn",
    "InstructionsAreNotClean",
    "LocalModelProvider",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "Observation",
    "OpenAICompatibleProvider",
    "ProviderError",
    "ScriptedProvider",
    "ToolCall",
    "ToolSpec",
    "assert_instructions_are_clean",
]
