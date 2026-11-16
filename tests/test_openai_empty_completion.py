"""An endpoint that answers with an empty message is a retryable failure.

MiniMax and other OpenAI-compatible endpoints occasionally return a
``200`` whose ``choices[0].message`` carries an empty ``content`` and no
``tool_calls`` (``completion_tokens=0``). Parsed as a normal answer this
became a completed task with zero findings — a grading failure with no
error — instead of the transient endpoint failure it is.

Two levels are pinned here:

* the provider raises a **retryable** :class:`ProviderError` for an empty
  message, so the orchestrator's ``_ask`` backoff can try again;
* the orchestration survives such a failure: the first attempt raises it,
  the second attempt answers, and the task completes with a real answer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.base import ProviderError
from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion
from dexatlas.agent.state import TaskStatus, TaskStore
from tests.agent_harness import Demo, build_demo, make_orchestrator


def _empty_completion() -> dict:
    """The body an endpoint sends when it answers with nothing at all."""
    return {
        "model": "a-model",
        "choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 0},
    }


def test_an_empty_completion_is_a_retryable_model_failure() -> None:
    """An answer with no content and no tool calls is a failure to retry."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    with pytest.raises(ProviderError) as raised:
        provider.parse_response(_empty_completion())

    assert raised.value.retryable is True
    assert "empty" in raised.value.message


def test_a_missing_content_field_is_the_same_failure() -> None:
    """A ``content`` the endpoint left out entirely is empty too."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    with pytest.raises(ProviderError) as raised:
        provider.parse_response({"choices": [{"message": {"role": "assistant"}}]})

    assert raised.value.retryable is True


def test_a_none_content_is_the_same_failure() -> None:
    """An explicit ``null`` content is empty as well."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")

    with pytest.raises(ProviderError) as raised:
        provider.parse_response({"choices": [{"message": {"role": "assistant", "content": None}}]})

    assert raised.value.retryable is True


def test_an_empty_content_with_tool_calls_is_still_an_answer() -> None:
    """A tool round whose content is empty is a normal turn, not a failure."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
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
        ]
    }

    response = provider.parse_response(body)

    assert response.content == ""
    assert response.tool_calls[0].name == "get_manifest"


def test_a_real_answer_still_parses_after_the_fix() -> None:
    """The ordinary path is untouched: content is content."""
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")
    body = {
        "choices": [{"message": {"role": "assistant", "content": "two permissions"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    response = provider.parse_response(body)

    assert response.content == "two permissions"
    assert response.total_tokens == 15


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def test_an_empty_completion_is_retried_and_the_task_completes(demo: Demo, tmp_path: Path) -> None:
    """The orchestration retries the empty message and finishes with an answer.

    The first attempt raises the retryable failure the provider now raises
    for an empty completion; the second attempt answers. The task must
    complete with the answer rather than being graded as a failure with no
    error.
    """
    provider = ScriptedProvider(
        responses=[
            ProviderError("the model endpoint answered with an empty message", retryable=True),
            answer([conclusion("the manifest asks for two permissions", evidence_ids=["E-0001"])]),
        ]
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert len(provider.requests) == 2, "the empty message was retried once"
    assert state.findings, "the completed task carries a real finding"
