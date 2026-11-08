"""What happens when things go wrong.

Three failure modes, and each of them has to be survivable and visible:

* a **timeout** — a tool that takes too long is abandoned, and the task
  carries on with what it has;
* a **backend failure** — an analysis that did not read everything says so,
  and the agent says it too;
* a **model failure** — an endpoint that is down is tried again, and when the
  attempts run out the task fails with its state saved, so it can be picked
  up later.

And two more that are the same kind of thing: an **interruption**, which
leaves a task that can be resumed, and a **confirmation**, which leaves a
task waiting for a person to say yes.

The rule behind all of them: a task that did not finish says that it did
not finish. It does not say it found nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.base import ProviderError
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from dexatlas.agent.tool_executor import ToolExecutor
from dexatlas.core.models import EvidenceLevel
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    scripted_provider,
)


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


# -- a timeout ---------------------------------------------------------------


def test_a_tool_that_hangs_does_not_stop_the_task(demo: Demo, tmp_path: Path) -> None:
    """A call that takes too long is abandoned, and the task carries on.

    The task does not wait for the abandoned call, and the log says the call
    was abandoned rather than that it failed.
    """
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    executor = ToolExecutor(_HangingClient(demo), timeout=0.05, max_attempts=1)
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))
    orchestrator._executor = executor  # the harness's client is replaced wholesale

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    timed_out = [record for record in state.tool_calls if record.error_kind == "timeout"]
    assert timed_out, "the call that hung is in the log"


class _HangingClient:
    """A client whose calls never come back."""

    def __init__(self, demo: Demo) -> None:
        self._inner = demo.analyzer

    def call(self, tool: str, arguments: object) -> object:
        import time

        time.sleep(0.5)
        return {}

    def describe(self, tool: str) -> object:
        from dexatlas.agent.providers.base import ToolSpec

        return ToolSpec(name=tool, description="")

    def signature(self, tool: str) -> object:
        import inspect

        return inspect.Signature()


# -- a backend failure -------------------------------------------------------


def test_an_incomplete_analysis_says_so(settings, tmp_path: Path) -> None:
    """A backend that did not take part means rows are missing.

    The agent has to know that before it repeats a count, and the reader has
    to know that before they believe one.
    """
    demo = build_demo(settings, tmp_path / "partial", missing_backends=("jadx",))
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    completeness = [item for item in state.findings if "missing_backends" in item.detail]
    assert completeness, "the status was recorded"
    assert completeness[0].detail["missing_backends"] == ["jadx"]
    assert "incomplete" in completeness[0].summary, (
        "the record says the analysis was incomplete, because a backend that did not "
        "take part is not a backend that found nothing"
    )


# -- a model failure ---------------------------------------------------------


def test_a_model_that_is_down_is_tried_again(demo: Demo, tmp_path: Path) -> None:
    """The endpoint is tried again before the task gives up."""
    provider = ScriptedProvider(
        responses=[
            ProviderError("the model endpoint answered 503", retryable=True),
            ProviderError("the model endpoint answered 503", retryable=True),
            answer([conclusion("the manifest says so", evidence_ids=["E-0001"])]),
        ]
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert len(provider.requests) == 3


def test_a_model_that_stays_down_fails_the_task_and_saves_it(demo: Demo, tmp_path: Path) -> None:
    """The task fails, and its state is saved so it can be picked up."""
    store = TaskStore(tmp_path / "tasks")
    provider = ScriptedProvider(
        responses=[ProviderError("the model endpoint answered 503", retryable=True)] * 3
    )
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.FAILED
    assert "503" in (state.error or "")
    assert store.load(state.task_id) is not None, "the state was saved"
    assert store.load(state.task_id).status is TaskStatus.FAILED  # type: ignore[union-attr]
    assert not [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED], (
        "a failed task reported no conclusion"
    )


# -- an interruption ---------------------------------------------------------


def test_an_interrupted_task_can_be_picked_up_again(demo: Demo, tmp_path: Path) -> None:
    """The state is written down, and the task continues where it stopped.

    The work that was already done is not done twice: the tool calls that
    were answered stay answered.
    """
    store = TaskStore(tmp_path / "tasks")
    interrupted = ScriptedProvider(
        responses=[
            KeyboardInterrupt(),
        ]
    )
    orchestrator = make_orchestrator(demo, interrupted, store=store)

    with pytest.raises(KeyboardInterrupt):
        orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    saved = store.list_tasks()
    assert saved, "the task was saved"
    state = store.load(saved[0])
    assert state is not None
    assert state.status is TaskStatus.INTERRUPTED
    assert state.resumable

    calls_before = len(state.tool_calls)

    resumed_provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    resumed = make_orchestrator(demo, resumed_provider, store=store)
    final = resumed.resume(saved[0])

    assert final.status is TaskStatus.COMPLETED, final.error
    assert final.tool_calls[:calls_before] == state.tool_calls, (
        "the calls that were already made were not made again"
    )
    assert len(final.findings) >= len(state.findings)


# -- a confirmation ----------------------------------------------------------


def test_a_sensitive_call_waits_for_a_person(demo: Demo, tmp_path: Path) -> None:
    """The second sensitive call stops the task, and the task says what it wants.

    Reading the APK's source is where the untrusted text is largest, so a
    task may read a bounded amount of it and then has to ask.
    """
    store = TaskStore(tmp_path / "tasks")
    provider = scripted_provider(
        [
            (
                "get_class_source",
                {"project_id": PROJECT_ID, "class_name": "com.example.demo.Crypto"},
            ),
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": "com.example.demo.Main"}),
        ],
        statement="the sources say so",
    )
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run("Show me the source of the classes.", project_id=demo.project_id)

    assert state.status is TaskStatus.AWAITING_CONFIRMATION
    assert state.pending_approval is not None
    assert state.pending_approval.tool == "get_class_source"
    assert "needs a person to say yes" in state.pending_approval.reason
    assert store.load(state.task_id) is not None, "the task was saved while it waited"


def test_an_approved_task_carries_on(demo: Demo, tmp_path: Path) -> None:
    """The person says yes, and the task finishes."""
    store = TaskStore(tmp_path / "tasks")
    provider = scripted_provider(
        [
            (
                "get_class_source",
                {"project_id": PROJECT_ID, "class_name": "com.example.demo.Crypto"},
            ),
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": "com.example.demo.Main"}),
        ],
        statement="the sources say so",
    )
    orchestrator = make_orchestrator(demo, provider, store=store)
    state = orchestrator.run("Show me the source of the classes.", project_id=demo.project_id)
    assert state.status is TaskStatus.AWAITING_CONFIRMATION

    resumed_provider = scripted_provider([], statement="the sources say so")
    resumed = make_orchestrator(demo, resumed_provider, store=store)
    final = resumed.resume(state.task_id, approved=True)

    assert final.status is TaskStatus.COMPLETED, final.error
    assert final.pending_approval is None
    assert final.sensitive_calls == 2


def test_a_task_that_is_not_approved_keeps_waiting(demo: Demo, tmp_path: Path) -> None:
    """A task that is picked up again without a yes keeps waiting."""
    store = TaskStore(tmp_path / "tasks")
    provider = scripted_provider(
        [
            (
                "get_class_source",
                {"project_id": PROJECT_ID, "class_name": "com.example.demo.Crypto"},
            ),
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": "com.example.demo.Main"}),
        ],
        statement="the sources say so",
    )
    orchestrator = make_orchestrator(demo, provider, store=store)
    state = orchestrator.run("Show me the source of the classes.", project_id=demo.project_id)

    resumed = make_orchestrator(demo, ScriptedProvider(), store=store)
    final = resumed.resume(state.task_id)

    assert final.status is TaskStatus.AWAITING_CONFIRMATION
    assert final.pending_approval is not None


# -- the budget --------------------------------------------------------------


def test_a_task_that_runs_out_of_iterations_says_so(demo: Demo, tmp_path: Path) -> None:
    """A task that ran out of budget did not finish, and it says that.

    It does not say it found nothing: that is a different claim.
    """
    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-1"),
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-2"),
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-3"),
        ]
    )
    orchestrator = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=1000, max_iterations=2, max_seconds=30.0),
    )

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.BUDGET_EXHAUSTED
    assert "iteration budget" in (state.error or "")

    report = orchestrator.report(state)
    from dexatlas.agent.reporter import render_agent_markdown

    markdown = render_agent_markdown(report)
    assert "did not finish" in markdown
    assert "ran out of budget" in markdown
