"""One tool call at a time.

A real model asks for several tools in one assistant turn — the M4 end-to-end
run measured two to five per round — and the loop used to run all of them
before coming back to the model. That burned the tool-call budget in three or
four rounds and the task never reached its answer, which is the failure the
e2e report records as P1. The loop now takes one call per round: the extra
calls the model asked for are refused in the round they were made, so the
model sees what happened, and it asks for the next one the following round.

The refusal is an observation in the transcript, not an exception: a model
that over-asks is behaving the way models do, and the task carries on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dexatlas.agent.providers.base import AssistantTurn, ModelRequest, ModelResponse
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_calls
from dexatlas.agent.state import TaskStatus, TaskStore
from tests.agent_harness import (
    CRYPTO,
    MAIN,
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)


def _response(request: ModelRequest) -> ModelResponse:
    """The answer that cites the evidence the tools produced."""
    ids = observation_evidence_ids(request)
    return answer(
        [
            conclusion(
                "the manifest is read and the Crypto class is decompiled",
                evidence_ids=ids[-2:],
            )
        ]
    )


class _ParallelThenScriptedProvider:
    """A model that asks for several tools at once, then answers.

    The first response is the point of this provider: a real endpoint sends
    several tool calls in one assistant turn, and the loop used to run them
    all in the same round. Everything after the first response is a script,
    so the rest of the task behaves exactly as it does against the scripted
    provider.
    """

    def __init__(
        self,
        first: ModelResponse,
        rest: list[Any],
    ) -> None:
        self._first: Any = first
        self._rest = list(rest)
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self._first is not _USED:
            first, self._first = self._first, _USED
            return first
        if not self._rest:
            raise AssertionError("the provider ran out of scripted responses")
        step = self._rest.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step(request) if callable(step) else step


_USED = object()


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


@pytest.fixture
def task_store(tmp_path: Path) -> TaskStore:
    return TaskStore(tmp_path / "tasks")


def _model_tools(state: Any) -> list[str]:
    """The tools the task ran for the model's tool calls, without the plan's own.

    The verifier also reads the analysis's own evidence when a conclusion
    cites an id it did not record; those reads are not tool calls the model
    asked for either.
    """
    bootstrap = {
        "get_project_status",
        "resolve_locator",
        "list_projects",
        "get_evidence",
    }
    return [record.tool for record in state.tool_calls if record.tool not in bootstrap]


def _refusals(state: Any) -> list[Any]:
    """The observations that refused a call the model asked for."""
    return [
        turn
        for turn in state.turns
        if not isinstance(turn, AssistantTurn) and turn.error == "one tool call per round"
    ]


def test_a_round_that_asks_for_several_tools_runs_one_and_refuses_the_rest(
    demo: Demo, task_store: TaskStore
) -> None:
    """Two calls in one assistant turn: one runs, the others are refused."""
    first = tool_calls(
        [
            ("get_manifest", {"project_id": PROJECT_ID}),
            ("search_symbols", {"project_id": PROJECT_ID, "query": "Crypto"}),
        ],
        prefix="batch",
    )
    provider = _ParallelThenScriptedProvider(first, [_response])
    orchestrator = make_orchestrator(demo, provider, store=task_store)  # type: ignore[arg-type]

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert _model_tools(state) == ["get_manifest"], "the second call of the round was not made"

    # The turn keeps both calls the model asked for, so a strict endpoint
    # sees an answer for each one: the manifest, and the refusal.
    ask_rounds = [
        turn for turn in state.turns if isinstance(turn, AssistantTurn) and turn.tool_calls
    ]
    assert len(ask_rounds) == 1
    assert [call.id for call in ask_rounds[0].tool_calls] == ["batch-1", "batch-2"]
    observations = [turn for turn in state.turns if not isinstance(turn, AssistantTurn)]
    answered = {turn.call_id for turn in observations if turn.call_id}
    assert answered == {"batch-1", "batch-2"}

    refusal_turn = next(turn for turn in observations if turn.call_id == "batch-2")
    refusal = json.loads(refusal_turn.content)  # type: ignore[union-attr]
    assert refusal["ok"] is False
    assert "one tool call per assistant turn" in refusal["error"]
    assert refusal["deferred_tool"] == "search_symbols"
    assert refusal_turn.ok is False
    assert refusal_turn.error == "one tool call per round"

    assert any("one tool call per round" in event.message for event in state.events), (
        "the task says in its events that a call was deferred"
    )


def test_the_refusal_reaches_the_model_as_an_answer_to_its_own_call(
    demo: Demo, task_store: TaskStore
) -> None:
    """The refusal is an observation whose call_id the model asked for.

    The OpenAI protocol reserves the ``tool`` channel for answers to calls
    the model made. A refusal that arrived with a call_id the transcript
    could not match would be a 400 at a strict endpoint; this one has to
    travel as the answer it is.
    """
    from dexatlas.agent.providers.openai_compat import build_messages

    first = tool_calls(
        [
            ("get_manifest", {"project_id": PROJECT_ID}),
            ("search_symbols", {"project_id": PROJECT_ID, "query": "Crypto"}),
        ],
        prefix="batch",
    )
    provider = _ParallelThenScriptedProvider(first, [_response])
    orchestrator = make_orchestrator(demo, provider, store=task_store)  # type: ignore[arg-type]

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    messages = build_messages(
        ModelRequest(
            instructions="you are the agent",
            question=state.question,
            turns=tuple(state.turns),
        )
    )
    roles = [message["role"] for message in messages]
    assert roles.count("tool") == 2, roles
    tool_messages = [message for message in messages if message["role"] == "tool"]
    assert {message["tool_call_id"] for message in tool_messages} == {"batch-1", "batch-2"}
    refusal_message = next(
        message for message in tool_messages if message["tool_call_id"] == "batch-2"
    )
    assert "one tool call per assistant turn" in refusal_message["content"]


def test_a_deferred_call_is_not_made_on_resume(demo: Demo, task_store: TaskStore) -> None:
    """A task that stops after a suppressed round does not run the refusal twice.

    The refusal is an answer in the transcript, so the call it answers is
    answered: a resume picks up after it, at the model, and asks for what
    the model wants next. The deferred call is not waiting anywhere.
    """
    first = tool_calls(
        [
            ("get_manifest", {"project_id": PROJECT_ID}),
            ("search_symbols", {"project_id": PROJECT_ID, "query": "Crypto"}),
        ],
        prefix="batch",
    )
    interrupted = _ParallelThenScriptedProvider(first, [KeyboardInterrupt()])
    orchestrator = make_orchestrator(demo, interrupted, store=task_store)  # type: ignore[arg-type]

    with pytest.raises(KeyboardInterrupt):
        orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    saved = task_store.list_tasks()
    assert saved, "the task was saved"
    state = task_store.load(saved[0])
    assert state is not None

    resumed_provider = ScriptedProvider(
        responses=[
            tool_calls([("search_symbols", {"project_id": PROJECT_ID, "query": "Crypto"})]),
            _response,
        ]
    )
    resumed = make_orchestrator(demo, resumed_provider, store=task_store)
    final = resumed.resume(saved[0])

    assert final.status is TaskStatus.COMPLETED, final.error
    assert _model_tools(final) == ["get_manifest", "search_symbols"], (
        "the resume asked the model, and the model asked for the deferred tool as a new call"
    )
    assert len(_refusals(final)) == 1, "the refusal was recorded once, and only once"


def test_one_tool_per_round_is_what_the_instructions_ask_for(
    demo: Demo, task_store: TaskStore
) -> None:
    """The instruction channel says one call per round, before any tool ran.

    The instruction is the part the model reads every round; the refusal
    only reaches it after the first over-ask. Both say the same thing.
    """
    provider = ScriptedProvider(responses=[_response])
    orchestrator = make_orchestrator(demo, provider, store=task_store)

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    request = provider.requests[0]
    assert "one tool call per assistant turn" in request.instructions


def test_a_single_tool_round_is_answered_exactly_as_before(
    demo: Demo, task_store: TaskStore
) -> None:
    """One call per turn is the common case, and it is untouched.

    The tool runs, the observation is recorded, the evidence id travels with
    it, and the answer cites it — the same turns, the same records, the same
    answer the fixed suite has always checked.
    """
    from dexatlas.agent.providers.scripted import tool_call

    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-1"),
            answer([conclusion("the manifest asks for two permissions", evidence_ids=["E-0002"])]),
        ]
    )
    orchestrator = make_orchestrator(demo, provider, store=task_store)

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert _model_tools(state) == ["get_manifest"]
    ask_rounds = [
        turn for turn in state.turns if isinstance(turn, AssistantTurn) and turn.tool_calls
    ]
    assert len(ask_rounds) == 1 and [call.id for call in ask_rounds[0].tool_calls] == ["call-1"]
    manifest = [
        turn
        for turn in state.turns
        if not isinstance(turn, AssistantTurn) and turn.tool == "get_manifest"
    ]
    assert len(manifest) == 1
    manifest_payload = json.loads(manifest[0].content)["data"]  # type: ignore[union-attr]
    assert manifest_payload["package"] == "com.example.demo"  # type: ignore[index]
    assert not _refusals(state), "no refusal was recorded: the model asked for one tool"
    assert any(
        item.level.value == "lead" and "two permissions" in item.summary for item in state.findings
    )


def test_three_calls_in_a_round_run_one_and_refuse_two(demo: Demo, task_store: TaskStore) -> None:
    """The rule is one call per round, whatever the model asked for."""
    first = tool_calls(
        [
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": CRYPTO}),
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": MAIN}),
            (
                "get_class_source",
                {"project_id": PROJECT_ID, "class_name": "com.example.demo.Other"},
            ),
        ],
        prefix="batch",
    )
    provider = _ParallelThenScriptedProvider(first, [_response])
    orchestrator = make_orchestrator(demo, provider, store=task_store)  # type: ignore[arg-type]

    state = orchestrator.run("Show me the sources.", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert _model_tools(state) == ["get_class_source"]
    refusals = _refusals(state)
    assert len(refusals) == 2, "one refusal per call the round did not run"
    deferred = [json.loads(turn.content).get("deferred_tool") for turn in refusals]  # type: ignore[union-attr]
    assert deferred == ["get_class_source", "get_class_source"]


def test_the_class_source_the_model_wanted_comes_back_later(
    demo: Demo, task_store: TaskStore
) -> None:
    """The suppressed work is not lost: the model asks again, and it is read.

    The source task needs the class the first round refused to read. The
    refusal sends the model back to ask, the model asks for the source, the
    task asks the person (a second source read needs a yes), the person says
    yes, and the answer cites the evidence the source produced.
    """
    first = tool_calls(
        [
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": CRYPTO}),
            ("get_class_source", {"project_id": PROJECT_ID, "class_name": MAIN}),
        ],
        prefix="batch",
    )

    def answer_with_source(request: ModelRequest) -> ModelResponse:
        ids = observation_evidence_ids(request)
        return answer(
            [conclusion("the Crypto class is decompiled Java", evidence_ids=ids[-1:])],
        )

    provider = _ParallelThenScriptedProvider(
        first,
        [
            tool_calls(
                [("get_class_source", {"project_id": PROJECT_ID, "class_name": CRYPTO})],
                prefix="again",
            ),
            answer_with_source,
        ],
    )
    orchestrator = make_orchestrator(demo, provider, store=task_store)  # type: ignore[arg-type]

    state = orchestrator.run(f"Show me the source of {CRYPTO}.", project_id=demo.project_id)
    assert state.status is TaskStatus.AWAITING_CONFIRMATION, (
        "the second source read is the sensitive call the person has to approve"
    )

    final = make_orchestrator(demo, provider, store=task_store).resume(state.task_id, approved=True)

    assert final.status is TaskStatus.COMPLETED, final.error
    assert _model_tools(final) == ["get_class_source", "get_class_source"]
    assert any("Crypto" in item.summary for item in final.findings), "the source was read"
