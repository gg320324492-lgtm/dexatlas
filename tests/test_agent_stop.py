"""Stopping when the question has been answered, not when the budget is gone.

A model that has read the fact its question needs can still go on reading.
That is how the M4 end-to-end run exhausted a token budget with six successful
tool calls and no answer: the loop had no way to say "the reading is done".

This module tests the convergence path. Once the key reading for the
question's category has returned:

* the next request says so, and asks for the answer;
* the model may make a small, bounded number of further reads;
* after that the tools are closed, and the model is asked once more for the
  answer from what it has;
* a model that still will not answer stops the task as failed, with a reason a
  reader can understand. It never becomes a completed task with no answer.

The boundary is unchanged: the model still writes the answer, and a model's
conclusion is still a lead. The loop only decides when reading stops.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.base import ModelRequest, ModelResponse, Observation
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from tests.agent_harness import (
    PROJECT_ID,
    SIGN_METHOD_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

MANIFEST_QUESTION = "Which permissions does this APK request?"
CALLS_QUESTION = "What calls the sign method that takes a String?"

#: The sentence the loop adds to the instructions when the reading is done.
READY_MARK = "The reading for this question is complete"
#: The sentence it adds when the tools have been closed.
CLOSED_MARK = "The tools are now closed"


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _answering(request: ModelRequest) -> ModelResponse:
    ids = observation_evidence_ids(request)
    return answer([conclusion("the question is answered from the reading", evidence_ids=ids[:1])])


def _manifest(call_id: str) -> ModelResponse:
    return tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id=call_id)


def _projects(call_id: str, limit: int) -> ModelResponse:
    return tool_call("list_projects", {"limit": limit, "offset": 0}, call_id=call_id)


def _orchestrator(demo: Demo, provider: ScriptedProvider, tmp_path: Path):
    return make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )


def test_the_request_says_the_reading_is_complete_after_the_key_fact(
    demo: Demo, tmp_path: Path
) -> None:
    """The manifest read is the manifest question's key fact, and it closes the reading."""
    provider = ScriptedProvider(responses=[_manifest("call-1"), _answering])
    state = _orchestrator(demo, provider, tmp_path).run(MANIFEST_QUESTION, project_id=PROJECT_ID)
    assert state.status is TaskStatus.COMPLETED

    assert READY_MARK not in provider.requests[0].instructions
    assert READY_MARK in provider.requests[1].instructions
    assert "Do not ask for more tool calls" in provider.requests[1].instructions
    assert [event.kind for event in state.events].count("evidence_ready") == 1


def test_tools_close_after_the_grace_and_the_model_answers(demo: Demo, tmp_path: Path) -> None:
    """After the reading is complete, two further reads are allowed — then the tools close."""
    provider = ScriptedProvider(
        responses=[
            _manifest("call-1"),
            _projects("call-2", limit=1),
            _projects("call-3", limit=2),
            _answering,
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(MANIFEST_QUESTION, project_id=PROJECT_ID)
    assert state.status is TaskStatus.COMPLETED

    # The first two requests still carry tools; the last one does not.
    assert provider.requests[1].tools, "the grace turns keep the tools open"
    assert provider.requests[2].tools, "the second grace turn keeps the tools open"
    assert provider.requests[-1].tools == (), "the tools are closed before the last ask"
    assert CLOSED_MARK in provider.requests[-1].instructions
    assert [event.kind for event in state.events].count("tools_closed") == 1


def test_a_model_that_will_not_answer_without_tools_fails_with_a_reason(
    demo: Demo, tmp_path: Path
) -> None:
    """Two chances are given; a third refusal to answer stops the task as failed."""

    def asks_again(request: ModelRequest) -> ModelResponse:
        return tool_call("list_projects", {"limit": 3, "offset": 0}, call_id="call-final")

    provider = ScriptedProvider(
        responses=[
            _manifest("call-1"),
            _projects("call-2", limit=1),
            _projects("call-3", limit=2),
            asks_again,
            asks_again,
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(MANIFEST_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.FAILED, "an unanswered task is not a completed one"
    assert state.error is not None
    assert "did not answer" in state.error
    assert [event.kind for event in state.events].count("tools_closed") == 1
    assert provider.requests[-1].tools == ()


def test_a_read_of_another_category_does_not_close_the_question(demo: Demo, tmp_path: Path) -> None:
    """A search is not a caller read: the calls question stays open until the callers arrive."""
    provider = ScriptedProvider(
        responses=[
            tool_call(
                "search_symbols",
                {"project_id": PROJECT_ID, "query": "sign", "limit": 20, "offset": 0},
                call_id="call-1",
            ),
            tool_call(
                "find_callers",
                {"project_id": PROJECT_ID, "method_id": SIGN_METHOD_ID, "limit": 50},
                call_id="call-2",
            ),
            _answering,
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(CALLS_QUESTION, project_id=PROJECT_ID)
    assert state.status is TaskStatus.COMPLETED

    assert READY_MARK not in provider.requests[1].instructions, (
        "a search is not the key reading of a callers question"
    )
    assert READY_MARK in provider.requests[2].instructions

    ready_events = [event for event in state.events if event.kind == "evidence_ready"]
    assert len(ready_events) == 1
    assert "find_callers" in ready_events[0].message


def test_a_resumed_task_carries_the_convergence_it_reached(demo: Demo, tmp_path: Path) -> None:
    """The reading-complete signal is part of the saved state, not of one process."""
    provider = ScriptedProvider(responses=[_manifest("call-1"), _answering])
    orchestrator = _orchestrator(demo, provider, tmp_path)
    state = orchestrator.run(MANIFEST_QUESTION, project_id=PROJECT_ID)

    saved = TaskStore(tmp_path / "tasks").load(state.task_id)
    assert saved is not None
    assert saved.wrap_up_reason, "the saved state says the reading was complete"
    assert [
        turn for turn in saved.turns if isinstance(turn, Observation) and turn.duplicate_of
    ] == []
