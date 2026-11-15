"""Asking the same tool the same question twice.

A model that is unsure repeats a call it has already made. The answer cannot
change — the analysis is a fixed, read-only workspace — and the repeat costs
a model round, so the loop answers it from the reading it already holds and
says that it did. The repeat is visible in the transcript, in the events and
in the report; it is not silently swallowed.

A *failed* call is not a repeat. The first call may have been refused or may
have timed out, and asking again is the right thing to do, so only successful
readings are reused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dexatlas.agent.providers.base import ModelRequest, ModelResponse, Observation
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.reporter import build_agent_json, render_agent_markdown
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

QUESTION = "Which permissions does this APK request?"


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _answering(request: ModelRequest) -> ModelResponse:
    """The final answer, citing the evidence the tools produced."""
    ids = observation_evidence_ids(request)
    return answer([conclusion("the manifest is read", evidence_ids=ids[:1])])


def _manifest_call(call_id: str) -> ModelResponse:
    return tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id=call_id)


def test_an_identical_call_is_answered_from_the_earlier_reading(demo: Demo, tmp_path: Path) -> None:
    """The second identical call is not made; its answer is reused and noted."""
    provider = ScriptedProvider(
        responses=[
            _manifest_call("call-1"),
            _manifest_call("call-2"),
            _answering,
        ]
    )
    orchestrator = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state = orchestrator.run(QUESTION, project_id=PROJECT_ID)
    assert state.status is TaskStatus.COMPLETED

    executed = [record for record in state.tool_calls if record.tool == "get_manifest"]
    assert len(executed) == 1, "the repeated call was made against the workspace"

    duplicates = [
        turn for turn in state.turns if isinstance(turn, Observation) and turn.duplicate_of
    ]
    assert len(duplicates) == 1
    document = json.loads(duplicates[0].content)
    assert document["duplicate"] is True
    assert document["duplicate_of_call_id"] == "call-1"
    assert document["evidence_id"], "the reused answer names the record it reuses"
    assert duplicates[0].ok is True, "a reused reading is an answered call, not a failure"

    assert [event.kind for event in state.events].count("duplicate_call") == 1


def test_the_report_says_how_many_calls_were_repeats(demo: Demo, tmp_path: Path) -> None:
    """A reader of the report can see the repeat without reading the transcript."""
    provider = ScriptedProvider(
        responses=[
            _manifest_call("call-1"),
            _manifest_call("call-2"),
            _answering,
        ]
    )
    orchestrator = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state = orchestrator.run(QUESTION, project_id=PROJECT_ID)
    report = orchestrator.report(state)

    assert report.repeated_calls == 1

    document = build_agent_json(report)
    assert document["convergence"]["repeated_calls"] == 1

    markdown = render_agent_markdown(report)
    assert "Repeated tool calls answered from the earlier reading: 1" in markdown


def test_a_failed_call_is_not_treated_as_a_repeat(demo: Demo, tmp_path: Path) -> None:
    """A refused call may be asked again: only successful readings are reused."""
    missing = tool_call("get_manifest", {"project_id": "apk_missing"}, call_id="call-1")
    missing_again = tool_call("get_manifest", {"project_id": "apk_missing"}, call_id="call-2")
    provider = ScriptedProvider(responses=[missing, missing_again, answer([])])
    orchestrator = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state = orchestrator.run(QUESTION, project_id=PROJECT_ID)

    failed = [record for record in state.tool_calls if record.tool == "get_manifest"]
    assert len(failed) == 2, "a failed call must be made again, not served from the failure"
    assert all(record.ok is False for record in failed)
    assert not [turn for turn in state.turns if isinstance(turn, Observation) and turn.duplicate_of]
