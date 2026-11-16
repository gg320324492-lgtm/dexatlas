"""The comparison harness's output contract: degradation and budget ends.

Two contracts come out of the M6 level-2 failure analysis
(``docs/benchmarks/m6-level2-retest3-failure-analysis.md``):

* **A count that cannot be established is a declared degradation, not a
  guess.** The agent's instructions say what a count answer looks like, and a
  system that cannot count says so in its limitations. The harness keeps
  those limitations verbatim in the trace and in the answer the scorer sees —
  as a record of what could not be settled, never as findings, and never as
  text that satisfies a ``must_contain`` marker. A degraded answer is honest
  and it still fails a count task: saying "I could not count" is not a count.
* **A task-level budget gate is its own kind of ending.** A run the
  ``total_tokens`` gate stopped did not answer. Its trace says
  ``budget-exhausted``, the report names the cause, and it cannot be scored
  as a pass — an unanswerable task scores an empty answer as a pass, and a
  run that never answered is not that.

Every test here runs without a model endpoint: the provider is scripted.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from benchmarks.comparison.adapters import answer_from_result, is_empty
from benchmarks.comparison.model import (
    OUTCOME_ANSWERED,
    OUTCOME_BUDGET_EXHAUSTED,
    OUTCOME_FAILED,
    Assertion,
    Question,
    SystemKind,
    SystemResult,
    TaskTrace,
)
from benchmarks.comparison.run import ComparisonRun, _failure_causes, _questions, _score
from benchmarks.comparison.systems import AgentSystem, SourceTextSystem
from benchmarks.model import Sample, check
from benchmarks.tasks import ALL_TASKS

from dexatlas.agent.orchestrator import CLOSED_DIRECTIVE, INSTRUCTIONS
from dexatlas.agent.providers.base import ProviderError
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, tool_call
from tests.agent_harness import PROJECT_ID, Demo, build_demo, scripted_provider

#: The instructions are prose with line breaks; the contract's phrases are
#: checked against the text with the breaks folded away.
FLAT = " ".join(INSTRUCTIONS.split())


def _task(task_id: str) -> Any:
    return next(task for task in ALL_TASKS if task.id == task_id)


def _question_for(task_id: str) -> Question:
    return _questions([_task(task_id)])[0]


def _trace(question: Question, result: SystemResult) -> TaskTrace:
    return TaskTrace(
        reference=question.reference,
        system=SystemKind.AGENT,
        provider="scripted",
        model="",
        max_tokens=2048,
        question=question.question,
        result=result,
    )


def _agent_analysis(demo: Demo) -> Any:
    """The analysis shape ``AgentSystem`` needs, over the demo workspace."""
    return SimpleNamespace(
        result=SimpleNamespace(
            project=SimpleNamespace(
                id=demo.project_id,
                tool_versions=dict(demo.versions),
                apk=SimpleNamespace(sha256="0" * 64),
            ),
            workspace=demo.workspace,
        ),
        analyzer=demo.analyzer,
    )


# -- the budget gate is its own kind of ending -------------------------------


def test_a_budget_exhausted_run_cannot_pass_an_unanswerable_task() -> None:
    """A run the total-token gate stopped has not answered, so it cannot pass.

    An unanswerable task scores an empty answer as a pass — that is right for
    a system that answered "there is none", and wrong for a system that was
    stopped before it said anything.
    """
    question = _question_for("unanswerable.demo-mentions-no-google-accounts")
    result = SystemResult(
        outcome=OUTCOME_BUDGET_EXHAUSTED,
        failed=True,
        error="the token budget is spent: 24000 of 24000 used",
    )

    scored = _score(question, _trace(question, result))

    assert scored.passed is False
    assert scored.result.outcome == OUTCOME_BUDGET_EXHAUSTED


def test_an_answered_negative_still_passes_an_unanswerable_task() -> None:
    """The guard is on the run that did not answer, not on the empty answer."""
    question = _question_for("unanswerable.demo-mentions-no-google-accounts")
    result = SystemResult(
        outcome=OUTCOME_ANSWERED,
        limitations=("no account-service string was found anywhere in the sample",),
    )

    scored = _score(question, _trace(question, result))

    assert scored.passed is True


def test_a_task_that_runs_out_of_tokens_ends_budget_exhausted(
    settings: Any, tmp_path: Path
) -> None:
    """The agent's total-token gate ends the task as budget-exhausted.

    The first model round costs one token, and the gate stops the task before
    it can answer. The result says so explicitly, instead of leaving a
    generic failure for the report to guess at.
    """

    def ask_for_tools(request: Any) -> Any:
        response = tool_call("get_manifest", {"project_id": PROJECT_ID})
        return replace(response, prompt_tokens=1)

    demo = build_demo(settings, tmp_path)
    provider = ScriptedProvider(responses=[ask_for_tools])
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
        total_tokens=1,
    )
    question = _question_for("resources.app-name.demo")

    result = system.answer(question)

    assert result.outcome == OUTCOME_BUDGET_EXHAUSTED
    assert result.failed is True
    assert "token budget" in result.error
    assert result.findings == ()

    scored = _score(question, _trace(question, result))
    assert scored.passed is False


def test_the_report_names_a_budget_exhaustion_as_such() -> None:
    """The failure table says the task ran out of its total token budget."""
    question = _question_for("resources.app-name.demo")
    trace = _score(
        question,
        _trace(
            question,
            SystemResult(
                outcome=OUTCOME_BUDGET_EXHAUSTED,
                failed=True,
                error="the token budget is spent: 24000 of 24000 used",
            ),
        ),
    )
    run = ComparisonRun(
        traces=(trace,), metrics={}, providers={}, models={}, budget=2048, task_count=1
    )

    text = "\n".join(_failure_causes(run))

    assert "total token budget" in text


def test_a_failed_run_is_named_as_a_failure_in_the_report() -> None:
    """An outcome-carrying failure keeps its own row, distinct from a budget."""
    question = _question_for("resources.app-name.demo")
    trace = _score(
        question,
        _trace(
            question,
            SystemResult(outcome=OUTCOME_FAILED, failed=True, error="ProviderError: boom"),
        ),
    )
    run = ComparisonRun(
        traces=(trace,), metrics={}, providers={}, models={}, budget=2048, task_count=1
    )

    text = "\n".join(_failure_causes(run))

    assert "the run failed" in text


# -- limitations are kept, and never become findings -------------------------


def test_a_limitation_records_a_backend_failure() -> None:
    """An honest "apktool was not installed" limitation is the evidence a
    partial-configuration task asks for.

    The agent answers ``conclusions=[]`` with the failure named in
    ``limitations``; the scorer's backend-failure predicate reads it from the
    answer's limitations instead of demanding a finding.
    """
    question = _question_for("partial.no-apktool-there-is-no-manifest")
    result = SystemResult(
        outcome=OUTCOME_ANSWERED,
        limitations=(
            "The manifest-declared package could not be established: apktool "
            "was not installed or on PATH (E-0004), so there is no manifest to read.",
        ),
    )

    answer = answer_from_result(result)

    assert answer.findings == ()
    assert is_empty(answer)
    assert "apktool was not installed" in answer.limitations[0]

    scored = _score(question, _trace(question, result))
    assert scored.passed is True


def test_a_limitation_never_satisfies_a_must_contain_marker() -> None:
    """A limitation is a record of what could not be settled, not a claim.

    A task that wants a value in a finding does not get credit from a
    limitation that happens to mention the value.
    """
    question = _question_for("manifest.target-sdk.demo")
    result = SystemResult(
        outcome=OUTCOME_ANSWERED,
        limitations=("the target SDK could not be read: the manifest was unavailable",),
    )

    scored = _score(question, _trace(question, result))

    assert scored.passed is False


def test_a_degraded_count_answer_is_recorded_and_does_not_pass() -> None:
    """ "I could not count" is an honest answer to a count task, and not a count.

    The degradation reaches the trace as a limitation; the task still fails,
    because the scorer asked for three findings and got none.
    """
    question = _question_for("manifest.permission.count-obfuscated")
    result = SystemResult(
        outcome=OUTCOME_ANSWERED,
        limitations=(
            "the exact permission count could not be established: the symbol "
            "index behind the question is incomplete",
        ),
    )

    answer = answer_from_result(result)
    assert answer.findings == ()
    assert "could not be established" in answer.limitations[0]

    scored = _score(question, _trace(question, result))
    assert scored.passed is False


def test_the_agent_system_keeps_the_model_s_limitations(settings: Any, tmp_path: Path) -> None:
    """What the model could not settle survives into the system's result."""
    demo = build_demo(settings, tmp_path)
    provider = ScriptedProvider(
        responses=[answer([], limitations=["apktool was not installed or on PATH"])]
    )
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )
    question = _question_for("partial.no-apktool-there-is-no-manifest")

    result = system.answer(question)

    assert result.outcome == OUTCOME_ANSWERED
    assert result.failed is False
    assert result.limitations == ("apktool was not installed or on PATH",)
    assert result.findings == ()


def test_a_retrieval_system_keeps_the_model_s_limitations() -> None:
    """A and B answer in the same JSON shape, so their limitations survive too."""
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "obfuscated-app" / "AndroidManifest.xml"
    )
    provider = ScriptedProvider(
        responses=[answer([], limitations=["the retrieved material does not settle the count"])]
    )
    system = SourceTextSystem(sources={"obfuscated-app": source}, provider=provider)
    question = _question_for("manifest.permission.count-obfuscated")

    result = system.answer(question)

    assert result.limitations == ("the retrieved material does not settle the count",)
    assert result.outcome == OUTCOME_ANSWERED


# -- the contract is written down where the model and the reader meet --------


def test_the_instructions_demand_a_declared_degradation_over_a_guess() -> None:
    """A count the reading does not settle is a limitation, never a guess."""
    assert "the counted items and nothing else" in FLAT
    assert "could not be established" in FLAT
    assert "a guessed count is not an answer at all" in FLAT


def test_the_wrap_up_directive_carries_the_count_rule() -> None:
    """When the tools close before the count is settled, the model degrades."""
    flat = " ".join(CLOSED_DIRECTIVE.split())
    assert "could not be established" in flat
    assert "limitations" in flat


# -- the trace shape stays compatible ----------------------------------------


def test_outcome_and_limitations_survive_a_trace_round_trip() -> None:
    """A trace written under the contract reads back with the contract."""
    result = SystemResult(
        answer_text="",
        outcome=OUTCOME_BUDGET_EXHAUSTED,
        limitations=("the count could not be established",),
        failed=True,
        error="the token budget is spent: 24000 of 24000 used",
    )
    trace = TaskTrace(
        reference="q001",
        system=SystemKind.AGENT,
        provider="scripted",
        model="",
        max_tokens=2048,
        question="a question",
        result=result,
    )

    restored = TaskTrace.from_dict(trace.to_dict())

    assert restored.result.outcome == OUTCOME_BUDGET_EXHAUSTED
    assert restored.result.limitations == ("the count could not be established",)


def test_a_trace_written_before_the_contract_still_loads() -> None:
    """Old traces have no outcome and no limitations; they load as before."""
    document: dict[str, Any] = {
        "reference": "q001",
        "task_id": "",
        "system": "A",
        "provider": "scripted",
        "model": "",
        "max_tokens": 2048,
        "question": "a question",
        "passed": False,
        "answer_is_empty": True,
        "expects_absence": False,
        "result": {
            "answer_text": "",
            "findings": [],
            "observations": [],
            "assertions": [],
            "tool_calls": [],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "duration_seconds": 0.0,
            "recovered": False,
            "failed": True,
            "error": "ProviderError: boom",
        },
    }

    restored = TaskTrace.from_dict(document)

    assert restored.result.outcome == ""
    assert restored.result.limitations == ()
    assert restored.result.failed is True


# -- the scorer's own shape --------------------------------------------------


def test_check_still_decides_on_findings_and_text_alone() -> None:
    """The limitations channel does not disturb the plain scoring path."""
    task = _task("manifest.target-sdk.demo")
    answer = answer_from_result(
        SystemResult(
            answer_text="target_sdk=34",
            assertions=(Assertion(text="target_sdk=34"),),
            outcome=OUTCOME_ANSWERED,
        )
    )

    result = check(task, answer)

    assert result.passed is True


# -- the agent's answer text carries its limitations -------------------------


def test_the_agent_result_puts_limitations_in_answer_text(settings: Any, tmp_path: Path) -> None:
    """The agent's prose answer keeps the limitations it declared.

    The M6 three-round retest graded two honest ``conclusions=[]`` answers as
    empty because the adapter joined only the conclusion sentences into the
    prose. The result's ``answer_text`` is the prose the scorer's
    backend-failure predicate reads; an answered task that said what it could
    not settle says it there.
    """
    demo = build_demo(settings, tmp_path)
    provider = ScriptedProvider(
        responses=[answer([], limitations=["apktool was not installed, so there is no manifest"])]
    )
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )
    question = _question_for("partial.no-apktool-there-is-no-manifest")

    result = system.answer(question)

    assert result.outcome == OUTCOME_ANSWERED
    assert result.failed is False
    assert result.limitations == ("apktool was not installed, so there is no manifest",)
    assert "apktool was not installed" in result.answer_text

    scored = _score(question, _trace(question, result))
    assert scored.passed is True


def test_a_limitation_is_kept_out_of_the_findings_channel(settings: Any, tmp_path: Path) -> None:
    """The prose gain does not leak the limitations into ``findings``.

    ``expect_empty`` tasks reject any finding; a limitation that became a
    finding would turn a correct "there is none" into a failure. The findings
    stay the model's conclusions and nothing else.
    """
    demo = build_demo(settings, tmp_path)
    provider = ScriptedProvider(
        responses=[answer([], limitations=["no such string was found in the sample"])]
    )
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )
    question = _question_for("unanswerable.demo-mentions-no-google-accounts")

    result = system.answer(question)

    assert result.findings == ()
    assert "no such string was found" in result.answer_text

    scored = _score(question, _trace(question, result))
    assert scored.passed is True


# -- the agent retries a transient endpoint failure --------------------------


def test_the_agent_system_retries_a_retryable_endpoint_failure(
    settings: Any, tmp_path: Path
) -> None:
    """A transient endpoint failure is retried inside the same task.

    The M6 measurement pinned ``model_attempts=1``, so the empty-message
    retry the provider offers never had a second chance. The system now
    passes its model-attempt budget to the orchestrator, and a failure that
    is retryable is asked again. The script reads a tool, then answers from
    the observation, so the completed task carries a real finding.
    """
    demo = build_demo(settings, tmp_path)
    reading = scripted_provider(
        [("get_manifest", {"project_id": PROJECT_ID})],
        statement="the manifest asks for two permissions",
    )
    provider = ScriptedProvider(
        responses=[
            ProviderError("the model endpoint answered with an empty message", retryable=True),
            *reading.responses,
        ]
    )
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )
    question = _question_for("manifest.package.demo")

    result = system.answer(question)

    assert result.failed is False, result.error
    assert result.findings, "the retried task answered"
    assert len(provider.requests) == 3, "the retryable failure was retried once"


def test_a_non_retryable_endpoint_failure_is_not_retried(settings: Any, tmp_path: Path) -> None:
    """A malformed request is not asked again; retrying it only burns budget."""
    demo = build_demo(settings, tmp_path)
    provider = ScriptedProvider(
        responses=[ProviderError("the model endpoint answered 400", retryable=False)]
    )
    system = AgentSystem(
        analyzer=demo.analyzer,
        analyses={Sample.DEMO.value: _agent_analysis(demo)},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )
    question = _question_for("manifest.package.demo")

    result = system.answer(question)

    assert result.failed is True
    assert len(provider.requests) == 1, "a non-retryable failure is not asked again"


# -- a tool-call protocol leak is a retryable provider failure ---------------


def test_an_xml_tool_call_leak_is_a_retryable_provider_failure() -> None:
    """MiniMax sometimes answers with an ``<invoke>`` block instead of JSON.

    The text is the model trying to speak the tool-call protocol inside its
    prose. Parsed as an answer it became conclusions about nothing and
    reached the benchmark as a final answer of XML. It is a broken model
    turn: the provider raises it as retryable, so the orchestrator asks
    again, and the XML never reaches a report as an answer.
    """
    provider = _openai_compat_with_content()

    with pytest.raises(ProviderError) as raised:
        provider.parse_response(_body_with_content('<invoke name="get_manifest">'))

    assert raised.value.retryable is True


def test_a_normal_answer_is_not_mistaken_for_a_protocol_leak() -> None:
    """Prose that merely mentions XML is an answer; only a tool-call shape raises."""
    provider = _openai_compat_with_content()

    response = provider.parse_response(_body_with_content("the strings live in strings.xml"))

    assert response.content == "the strings live in strings.xml"


def _openai_compat_with_content() -> Any:
    from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider

    return OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")


def _body_with_content(content: str) -> dict[str, Any]:
    return {
        "model": "a-model",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
