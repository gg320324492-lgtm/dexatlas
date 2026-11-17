"""A resources question closes on the first successful resource reading.

The M6 narrow-verification traces (``narrow#11``) show a resources question
spending its whole token budget: the model called
``find_resource_declarations`` five times with different names, the loop
counted nothing as the question's key reading, and the budget died before an
answer — the fact the question needed had been in the transcript since the
first round.

The fix is one line in the sufficiency rule: the ``resources`` intent joins
``KEY_TOOLS``, so a successful ``find_resource_declarations`` closes the
intent like a manifest read closes the manifest intent. The model is then
told the reading is complete and asked for its answer.

Red state: without the mapping, a ``find_resource_declarations`` success is
not the key reading of a resources question — the reading stays open, the
grace never starts, and the task ends ``BUDGET_EXHAUSTED``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from dexatlas.agent.sufficiency import KEY_TOOLS, ready_reason
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

RESOURCES_QUESTION = "In which resource file is app_name declared?"

#: The sentence the loop adds to the instructions when the reading is done.
READY_MARK = "The reading for this question is complete"
#: The sentence it adds when the tools have been closed.
CLOSED_MARK = "The tools are now closed"


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def test_find_resource_declarations_is_the_key_tool_of_the_resources_intent() -> None:
    """The mapping says a successful resource lookup closes a resources question."""
    assert "find_resource_declarations" in KEY_TOOLS.get("resources", frozenset())


def test_a_resource_reading_closes_the_resources_question(demo: Demo) -> None:
    """A successful resource read is the key reading of a resources plan."""
    from dexatlas.agent.planner import Planner
    from dexatlas.agent.state import TaskState

    plan = Planner().plan(RESOURCES_QUESTION, project_id=PROJECT_ID)
    assert "resources" in plan.intents, "the question must be planned as a resources question"
    state = TaskState(
        task_id="test-resources-close",
        question=RESOURCES_QUESTION,
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state.plan = plan
    state.project_id = PROJECT_ID
    state.turns.append(_observation("call-1", ok=True))

    reason = ready_reason(plan, state)
    assert reason is not None, (
        "a successful find_resource_declarations read is the fact a resources "
        "question needs; the reading must count as complete"
    )
    assert "resources" in reason


def test_a_resources_task_stops_after_the_first_resource_read(demo: Demo, tmp_path: Path) -> None:
    """The first successful resource read closes the reading; the task answers.

    Red state: with the mapping missing, the read is not the key fact, the
    loop keeps the tools open, and a model that goes on circling dies
    ``BUDGET_EXHAUSTED`` with no answer at all.
    """
    provider = ScriptedProvider(
        responses=[
            tool_call(
                "find_resource_declarations",
                {"project_id": PROJECT_ID, "name": "app_name"},
                call_id="call-1",
            ),
            lambda request: answer(
                [
                    conclusion(
                        "app_name is declared in res/values/strings.xml",
                        evidence_ids=observation_evidence_ids(request)[-1:],
                    )
                ]
            ),
        ]
    )
    state = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=4, max_seconds=60.0),
    ).run(RESOURCES_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED, (
        f"the reading closed after the first resource read; the task answered "
        f"(status={state.status}, error={state.error!r})"
    )
    assert READY_MARK in provider.requests[1].instructions
    assert [event.kind for event in state.events].count("evidence_ready") == 1
    assert state.wrap_up_reason is not None
    assert "find_resource_declarations" in state.wrap_up_reason


def _observation(call_id: str, *, ok: bool):
    """One find_resource_declarations observation, as the executor writes it."""
    from dexatlas.agent.providers.base import Observation

    content = (
        '{"tool": "find_resource_declarations", "ok": true, '
        '"declarations": [{"name": "app_name", "file": "res/values/strings.xml", '
        '"value": "Demo", "qualifiers": []}], "count": 1}'
    )
    return Observation(tool="find_resource_declarations", call_id=call_id, content=content, ok=ok)
