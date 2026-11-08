"""The task state machine, and where a task is kept.

A state machine whose transitions are not checked is a set of fields. So the
transitions are checked, and the ones that are not allowed are refused — a
task cannot claim to have completed from a state that never finished, and a
resumed task cannot slip past the checkpoint it was waiting at.

And the state is written down: a task that was interrupted has to be
readable by a later run, which means the state survives a round trip
through the store without losing anything a reader would want.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.state import (
    ALLOWED_TRANSITIONS,
    Budget,
    BudgetExceeded,
    InvalidTransition,
    Plan,
    PlanStep,
    TaskState,
    TaskStatus,
    TaskStore,
)


def _state() -> TaskState:
    return TaskState(
        task_id="task-1",
        question="Which permissions does this APK request?",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_a_new_task_is_pending() -> None:
    """A task starts by waiting to be planned."""
    assert _state().status is TaskStatus.PENDING


def test_a_task_may_not_skip_a_step() -> None:
    """The transitions are the mechanism, and they are checked."""
    state = _state()

    with pytest.raises(InvalidTransition):
        state.transition(TaskStatus.COMPLETED)

    state.transition(TaskStatus.PLANNING)
    state.transition(TaskStatus.RUNNING)
    state.transition(TaskStatus.COMPLETED)
    assert state.status is TaskStatus.COMPLETED


def test_a_finished_task_is_finished() -> None:
    """A completed task does not go anywhere else."""
    state = _state()
    state.transition(TaskStatus.PLANNING)
    state.transition(TaskStatus.RUNNING)
    state.transition(TaskStatus.COMPLETED)

    with pytest.raises(InvalidTransition):
        state.transition(TaskStatus.RUNNING)


def test_a_task_that_is_waiting_may_be_picked_up_again() -> None:
    """A task waiting for a confirmation goes back to running when it gets it."""
    state = _state()
    state.transition(TaskStatus.PLANNING)
    state.transition(TaskStatus.RUNNING)
    state.transition(TaskStatus.AWAITING_CONFIRMATION)

    assert state.resumable
    state.transition(TaskStatus.RUNNING)
    assert state.status is TaskStatus.RUNNING


def test_every_status_that_can_be_reached_is_reachable_from_something() -> None:
    """The table has no orphans."""
    reachable = {TaskStatus.PENDING}
    changed = True
    while changed:
        changed = False
        for status, targets in ALLOWED_TRANSITIONS.items():
            if status not in reachable:
                continue
            new = targets - reachable
            if new:
                reachable.update(new)
                changed = True

    assert reachable == set(TaskStatus), "some status cannot be reached from any other"


def test_the_budget_is_checked_before_the_work_not_after() -> None:
    """A task that has overshot its budget is told, rather than going on."""
    state = _state()
    state.limits = Budget(max_tokens=100, max_iterations=2, max_seconds=1.0)
    state.charge(tokens=50)

    state.check_budget()  # within the budget: nothing to say

    state.charge(tokens=60)
    with pytest.raises(BudgetExceeded) as raised:
        state.check_budget()

    assert raised.value.budget == "token"
    assert raised.value.limit == 100
    assert raised.value.spent == 110


def test_the_state_survives_a_round_trip_through_the_store(tmp_path: Path) -> None:
    """A task that was interrupted has to be readable by a later run."""
    store = TaskStore(tmp_path / "tasks")
    state = _state()
    state.plan = Plan(
        project_id="apk_one",
        question=state.question,
        steps=(PlanStep(tool="get_manifest", purpose="read the manifest"),),
        allowed_tools=("get_manifest",),
        limits=Budget(max_tokens=10, max_iterations=1, max_seconds=2.0),
    )
    state.limits = Budget(max_tokens=10, max_iterations=1, max_seconds=2.0)
    state.project_id = "apk_one"
    state.run_id = "run-1"
    state.sensitive_calls = 2
    state.approved_calls = ["call-2"]
    state.charge(tokens=5, iterations=1, seconds=0.25)
    state.note("tool_call", "get_manifest: ok")

    store.save(state)
    read = store.load("task-1")

    assert read is not None
    assert read.task_id == state.task_id
    assert read.question == state.question
    assert read.project_id == "apk_one"
    assert read.run_id == "run-1"
    assert read.sensitive_calls == 2
    assert read.approved_calls == ["call-2"]
    assert read.usage.tokens == 5
    assert read.usage.iterations == 1
    assert read.usage.seconds == 0.25
    assert read.events[0].message == "get_manifest: ok"
    assert read.plan is not None
    assert read.plan.allowed_tools == ("get_manifest",)
    assert read.limits.max_iterations == 1


def test_a_task_that_is_not_there_is_not_there(tmp_path: Path) -> None:
    """Reading a task that was never written is ``None``, not a crash."""
    store = TaskStore(tmp_path / "tasks")

    assert store.load("task-nope") is None
    assert store.list_tasks() == []


def test_the_store_lists_the_tasks_it_holds(tmp_path: Path) -> None:
    """A caller can find the tasks it can pick up again."""
    store = TaskStore(tmp_path / "tasks")
    first = _state()
    second = _state()
    second.task_id = "task-2"
    store.save(first)
    store.save(second)

    assert store.list_tasks() == ["task-1", "task-2"]
