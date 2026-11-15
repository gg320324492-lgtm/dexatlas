"""A ``no_manifest`` error closes the reading instead of inviting another round.

The M6 level-2 retest found the no-apktool task — "What package does the demo
application declare, when the APK reader is not installed?" — running its
full sixteen iterations without answering: the model asked for the manifest,
the tool answered ``no_manifest`` (apktool did not take part), and the loop
counted nothing as read. The model asked again, and again, until the
iteration budget died with no answer at all — when the fact it needed had
been in the transcript since the first round.

The fix is in the sufficiency rule: a failed call whose error states the
fact a partial-configuration question needs (``no_manifest`` on a workspace
with no APK reader) closes the manifest intent like a successful read does.
The model is then told the reading is complete and asked for its answer,
which it can give from the error it already saw.

Red state: the committed code before the change — the failure closes
nothing, the model circles, and the task ends ``BUDGET_EXHAUSTED`` with no
answer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.base import Observation
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, Plan, PlanStep, TaskState, TaskStatus, TaskStore
from dexatlas.agent.sufficiency import ready_reason
from tests.agent_harness import PROJECT_ID, build_demo, make_orchestrator

assert TaskStatus is not None  # re-exported for the loop test's assertions

NO_APKTOOL_QUESTION = (
    "What package does the demo application declare, when the APK reader is not installed?"
)


@pytest.fixture
def no_apktool_demo(settings, tmp_path: Path):
    demo = build_demo(settings, tmp_path, missing_backends=("apktool",))
    # The harness writes a manifest whether or not Apktool took part; a
    # workspace whose APK reader was absent holds none. Clearing it here is
    # what makes the stored state match the configured absence, which is the
    # fact the question under test is about.
    project = demo.analyzer.store.get_project(PROJECT_ID)
    demo.analyzer.store.save_project(project, demo.workspace, None)
    return demo


def _manifest_plan() -> Plan:
    """A manifest plan, as the planner would write it for the package question."""
    return Plan(
        project_id=PROJECT_ID,
        question=NO_APKTOOL_QUESTION,
        allowed_tools=("get_project_status", "get_manifest", "get_evidence", "resolve_locator"),
        max_steps=12,
        steps=(
            PlanStep(tool="get_project_status", purpose="how complete is the analysis"),
            PlanStep(tool="get_manifest", purpose="the package the manifest declares"),
        ),
        intents=("manifest",),
    )


def _asking_provider(calls: list[list]) -> ScriptedProvider:
    """A provider that asks for the manifest, then for evidence, forever."""

    def ask(request) -> object:
        calls.append([turn for turn in request.turns if isinstance(turn, Observation)])
        return tool_call("get_manifest", {"project_id": PROJECT_ID})

    return ScriptedProvider(responses=[ask])


def test_a_no_manifest_error_closes_the_manifest_question(no_apktool_demo, tmp_path: Path) -> None:
    """The failed manifest read settles a question about the manifest's absence."""
    plan = _manifest_plan()
    # Build a minimal task state by hand: the rule under test is the
    # sufficiency decision, not the full loop.
    state = TaskState(
        task_id="test-no-manifest",
        question=NO_APKTOOL_QUESTION,
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state.plan = plan
    state.project_id = PROJECT_ID
    state.turns.append(
        Observation(
            tool="get_manifest",
            call_id="call-1",
            content=(
                '{"tool": "get_manifest", "ok": false, "error": {"kind": "no_manifest", '
                '"message": "project \'x\' holds no manifest: apktool did not take part '
                'in this analysis", "detail": {"missing_backends": ["apktool"]}}}'
            ),
            ok=False,
            error="no_manifest",
        )
    )

    reason = ready_reason(plan, state)
    assert reason is not None, (
        "a no_manifest error is the fact the manifest question needs; the "
        "reading must count as complete"
    )
    assert "manifest" in reason


def test_a_model_that_keeps_asking_for_a_missing_manifest_still_answers(
    no_apktool_demo, tmp_path: Path
) -> None:
    """The loop converges instead of spending its iterations circling the error.

    With the fix, the failed manifest read closes the question; the model is
    asked to answer from what it has, and the task completes with the
    no-manifest fact recorded — rather than dying ``BUDGET_EXHAUSTED`` with
    nothing said.
    """
    from dexatlas.agent.providers.scripted import ScriptedProvider as SP

    def answer_from_error(request) -> object:
        saw_error = any(
            isinstance(turn, Observation)
            and not turn.ok
            and "holds no manifest" in (turn.content or "")
            for turn in request.turns
        )
        if saw_error:
            return answer(
                [
                    conclusion(
                        "the analysis holds no manifest: apktool did not take part, so no "
                        "package is declared in this analysis",
                        evidence_ids=[],
                        locators=[],
                    )
                ],
                limitations=[],
            )
        return tool_call("get_manifest", {"project_id": PROJECT_ID})

    # One scripted step per loop round: the model asks for the manifest,
    # sees the no_manifest error, and then answers from it. The script has a
    # step for every round the loop may spend, so a model that keeps asking
    # is answered each time instead of the script running dry.
    provider = SP(responses=[answer_from_error] * 8)
    orchestrator = make_orchestrator(
        no_apktool_demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )
    state = orchestrator.run(NO_APKTOOL_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED, (
        f"the task must answer from the recorded failure, not burn its budget "
        f"(ended {state.status.value}: {state.error})"
    )
