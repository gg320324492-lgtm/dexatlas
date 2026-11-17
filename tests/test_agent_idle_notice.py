"""A soft notice when the same tool keeps coming back without new rows.

The M6 narrow traces show the shape of a wasted budget: the model asks a
tool again with slightly different arguments — a different name, a different
page — the answer is the same empty rows it has already read, and the loop
says nothing, so the model asks again, and the transcript grows on every
turn until the budget dies. The duplicate-call rule catches an *identical*
call; this notice covers the neighbour of that case: a call that is not
identical but reads the same.

The notice is soft. It does not refuse the call, close the tools or stop the
task — a caller paging a genuinely long list is doing the right thing, and a
hard stop would kill the multidex reads that need several pages. What it
does is tell the model, in the instructions, that its last calls to one tool
returned no new rows, so it can decide to answer instead of reading on.

The counter watches the *rows* a call brought back, not its arguments: a
page that returns new rows resets it, so legitimate paging is never
noticed. The tests page ``list_projects`` past the end of a one-project
workspace — the smallest case that is not an identical call and not a
refusal, but still reads nothing new.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.orchestrator import IDLE_TOOL_NOTICE, IDLE_TOOL_THRESHOLD
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

QUESTION = "Which permissions does this APK request?"
IDLE_MARK = "each returned no new rows"


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _answering(request) -> object:
    ids = observation_evidence_ids(request)
    return answer([conclusion("the manifest is read", evidence_ids=ids[:1])])


def _idle_script(count: int, tail) -> list[object]:
    """A script that pages list_projects past the end of the workspace,
    count times, then the tail. Each page has a different offset, so no call
    is an exact repeat, and every page comes back empty."""
    responses: list[object] = []
    for index in range(count):
        responses.append(
            tool_call(
                "list_projects",
                {"limit": 1, "offset": 1 + index},
                call_id=f"call-{index + 1}",
            )
        )
    if tail is not None:
        responses.append(tail)
    return responses


def _run(demo: Demo, tmp_path: Path, responses: list[object]):
    provider = ScriptedProvider(responses=responses)
    state = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=12, max_seconds=60.0),
    ).run(QUESTION, project_id=PROJECT_ID)
    return provider, state


def test_threshold_is_three_and_the_notice_is_soft() -> None:
    """Three row-less repeats are noticed; the notice asks, it does not stop."""
    assert IDLE_TOOL_THRESHOLD == 3
    assert "answer" in IDLE_TOOL_NOTICE.lower()


def test_a_read_that_brought_new_rows_is_not_idling(demo: Demo, tmp_path: Path) -> None:
    """The counter watches rows: a read that brought rows is never noticed."""
    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-1"),
            tool_call("list_projects", {"limit": 1, "offset": 0}, call_id="call-2"),
            _answering,
        ]
    )
    state = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    ).run(QUESTION, project_id=PROJECT_ID)
    assert state.status is TaskStatus.COMPLETED
    assert not any(event.kind == "idle_reads" for event in state.events)


def test_row_less_repeats_in_a_row_reach_the_notice(demo: Demo, tmp_path: Path) -> None:
    """Three row-less reads of one tool in a row raise the soft notice."""
    provider, state = _run(demo, tmp_path, _idle_script(IDLE_TOOL_THRESHOLD, _answering))
    assert state.status is TaskStatus.COMPLETED

    idle_events = [event for event in state.events if event.kind == "idle_reads"]
    assert len(idle_events) == 1, "the notice is raised once, when the threshold is met"
    assert "list_projects" in idle_events[0].message
    assert str(IDLE_TOOL_THRESHOLD) in idle_events[0].message
    assert any(IDLE_MARK in request.instructions for request in provider.requests)


def test_two_row_less_repeats_stay_below_the_notice(demo: Demo, tmp_path: Path) -> None:
    """Two misses are a lookup that found nothing, not idling yet."""
    provider, state = _run(demo, tmp_path, _idle_script(IDLE_TOOL_THRESHOLD - 1, _answering))
    assert state.status is TaskStatus.COMPLETED
    assert not any(event.kind == "idle_reads" for event in state.events)
    assert not any(IDLE_MARK in request.instructions for request in provider.requests)


def test_a_read_with_new_rows_clears_the_notice(demo: Demo, tmp_path: Path) -> None:
    """Paging that finds rows is legitimate: the notice does not stick."""
    responses = _idle_script(IDLE_TOOL_THRESHOLD, None)
    # A read that brings rows — the first page, with rows in it — resets the
    # counter.
    responses.append(tool_call("list_projects", {"limit": 1, "offset": 0}, call_id="call-9"))
    responses.append(_answering)
    provider, state = _run(demo, tmp_path, responses)
    assert state.status is TaskStatus.COMPLETED
    assert any(event.kind == "idle_reads" for event in state.events), (
        "the notice was raised before the row-bearing read"
    )
    # The request that followed the row-bearing read carries no idle notice:
    # the counter was reset, and the model is not told to stop reading.
    assert IDLE_MARK not in provider.requests[-1].instructions


def test_the_notice_does_not_stop_the_task(demo: Demo, tmp_path: Path) -> None:
    """The notice is advice: the task can still finish with an answer."""
    _, state = _run(demo, tmp_path, _idle_script(IDLE_TOOL_THRESHOLD + 1, _answering))
    assert state.status is TaskStatus.COMPLETED, "the notice never stops the task"
    assert any(event.kind == "idle_reads" for event in state.events)
