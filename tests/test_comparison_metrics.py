"""M3 对比 harness 的回归测试.

这些测试守住三件事: 指标的分母不能凭空出现, 被测系统看不到 marking
scheme, 报告里的每个数字都能从落盘的 trace 重新算出来.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from benchmarks.comparison.adapters import answer_from_result, is_empty, prose_to_conclusions
from benchmarks.comparison.metrics import (
    METRIC_NAMES,
    compare,
    format_value,
    metrics_for,
)
from benchmarks.comparison.model import (
    Assertion,
    SystemKind,
    SystemResult,
    TaskTrace,
    ToolCallTrace,
)
from benchmarks.comparison.run import (
    COMMITTED_TRACES,
    ComparisonRun,
    _markdown,
    _questions,
    _render,
    _run_from_document,
    _score,
)
from benchmarks.comparison.systems import INSTRUCTIONS, scripted_provider
from benchmarks.model import check
from benchmarks.tasks import ALL_TASKS


def trace(
    *,
    system: SystemKind = SystemKind.SOURCE_TEXT,
    passed: bool = True,
    assertions: tuple[Assertion, ...] = (),
    calls: tuple[ToolCallTrace, ...] = (),
    findings: tuple[str, ...] = (),
    text: str = "",
    tokens: int = 0,
    seconds: float = 0.0,
    recovered: bool = False,
    error: str = "",
    reference: str = "q001",
) -> TaskTrace:
    """Build one trace without running any analysis backend."""
    result = SystemResult(
        answer_text=text,
        findings=findings,
        assertions=assertions,
        tool_calls=calls,
        prompt_tokens=tokens,
        duration_seconds=seconds,
        recovered=recovered,
        error=error,
    )
    return TaskTrace(
        reference=reference,
        system=system,
        provider="scripted",
        model="",
        max_tokens=2048,
        question="a question",
        passed=passed,
        answer_is_empty=is_empty(answer_from_result(result)),
        result=result,
    )


def test_every_metric_has_a_name_and_a_denominator_rule() -> None:
    """Eight metrics, and a run with no data reports n/a rather than 0%."""
    values = metrics_for([trace()])
    assert tuple(values) == METRIC_NAMES
    assert values["correct_answer_rate"] == 1.0
    assert values["evidence_grounding_rate"] is None
    assert values["unsupported_assertion_rate"] is None
    assert values["false_positive_rate"] is None
    assert values["tool_call_success_rate"] is None
    assert values["recovery_rate"] is None
    assert format_value("recovery_rate", None) == "n/a"


def test_grounding_and_unsupported_assertions_are_complementary() -> None:
    values = metrics_for(
        [
            trace(
                assertions=(
                    Assertion("backed", grounded=True),
                    Assertion("bare", grounded=False),
                    Assertion("also bare", grounded=False),
                )
            )
        ]
    )
    assert values["evidence_grounding_rate"] == pytest.approx(1 / 3)
    assert values["unsupported_assertion_rate"] == pytest.approx(2 / 3)


def test_false_positive_denominator_is_every_assertion() -> None:
    """A wrong task with two assertions is not a 200% rate.

    The numerator counts the assertions on failed tasks and the denominator
    counts every assertion, so the rate stays inside [0, 1].
    """
    values = metrics_for(
        [
            trace(passed=False, assertions=(Assertion("x"), Assertion("y"))),
            trace(passed=True, assertions=(Assertion("z"),)),
        ]
    )
    assert values["false_positive_rate"] == pytest.approx(2 / 3)


def test_recovery_needs_a_real_failure_and_a_real_recovery() -> None:
    values = metrics_for(
        [
            trace(recovered=True),  # no failure: not a recovery
            trace(calls=(ToolCallTrace("tool", ok=False),), recovered=True),
            trace(calls=(ToolCallTrace("tool", ok=False),), recovered=False),
        ]
    )
    assert values["recovery_rate"] == pytest.approx(0.5)


def test_tool_success_and_token_totals() -> None:
    values = metrics_for(
        [
            trace(
                calls=(
                    ToolCallTrace("a", ok=True),
                    ToolCallTrace("b", ok=False),
                ),
                tokens=17,
                seconds=0.25,
            )
        ]
    )
    assert values["tool_call_success_rate"] == 0.5
    assert values["token_consumption"] == 17
    assert values["execution_duration"] == 0.25


def test_compare_groups_by_system() -> None:
    grouped = compare([trace(system=SystemKind.SOURCE_TEXT), trace(system=SystemKind.STRUCTURED)])
    assert set(grouped) == {"A", "B"}
    assert all(tuple(values) == METRIC_NAMES for values in grouped.values())


def test_questions_never_carry_the_marking_scheme() -> None:
    """The only input a system under test ever sees."""
    questions = _questions()
    assert len(questions) == len(ALL_TASKS)
    for question in questions:
        assert set(question.__dataclass_fields__) == {
            "reference",
            "question",
            "sample",
            "configuration",
        }
        assert question.reference.startswith("q")
        assert "must_contain" not in question.question
    assert "must_contain" not in INSTRUCTIONS
    assert "expect_empty" not in INSTRUCTIONS


def test_scorer_is_the_only_place_a_task_id_appears() -> None:
    """The scorer resolves a reference to a task; the system never gets it."""
    question = _questions()[0]
    raw = trace(reference=question.reference)
    assert raw.task_id == ""
    scored = _score(question, raw)
    assert scored.task_id == ALL_TASKS[0].id
    # The reference is an opaque number: it says nothing about the answer,
    # unlike several task ids ("...has-no-callers").
    assert question.reference == "q001"
    assert ALL_TASKS[0].id not in question.question
    assert not any(word in question.reference for word in ("caller", "sdk", "exported"))


def test_trace_round_trip_makes_metrics_regenerable(tmp_path: Path) -> None:
    """A saved comparison.json recomputes the same numbers without a re-run."""
    traces = (
        trace(assertions=(Assertion("a", grounded=True),), tokens=5),
        trace(
            system=SystemKind.AGENT,
            passed=False,
            assertions=(Assertion("b", grounded=False),),
            calls=(ToolCallTrace("tool", ok=False),),
            recovered=True,
        ),
    )
    document = ComparisonRun(
        traces=traces,
        metrics=compare(traces),
        providers={"A": "scripted"},
        models={"A": ""},
        budget=2048,
        task_count=2,
    ).to_dict()
    path = tmp_path / "comparison.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    restored = tuple(TaskTrace.from_dict(item) for item in json.loads(path.read_text())["traces"])
    assert compare(restored) == document["metrics"]


def test_report_discloses_the_scripted_provider(capsys: pytest.CaptureFixture[str]) -> None:
    """A scripted run may not be presented as a model baseline."""
    run = ComparisonRun(
        traces=(trace(),),
        metrics=compare((trace(),)),
        providers={"A": "scripted", "B": "scripted", "DexAtlas": "scripted"},
        models={"A": "", "B": "", "DexAtlas": ""},
        budget=2048,
        task_count=1,
    )
    _render(run, sys.stdout)
    printed = capsys.readouterr().out
    assert "NOT a model baseline" in printed
    assert "No improvement is claimed" in printed


def test_report_discloses_a_tool_success_shortfall(capsys: pytest.CaptureFixture[str]) -> None:
    """The 95% target is a disclosure rule, not a number to hide."""
    failed = trace(calls=(ToolCallTrace("tool", ok=False),))
    run = ComparisonRun(
        traces=(failed,),
        metrics=compare((failed,)),
        providers={"A": "scripted"},
        models={"A": ""},
        budget=2048,
        task_count=1,
    )
    _render(run, sys.stdout)
    printed = capsys.readouterr().out
    assert "below the 95% target" in printed


def test_prose_adapter_keeps_an_unsupported_answer() -> None:
    """A model that says something without evidence is still an assertion."""
    content = "the manifest declares four components"
    statements = prose_to_conclusions(content)
    assert len(statements) == 1
    assert content in statements[0]
    result = SystemResult(answer_text=content, assertions=(Assertion(statements[0]),))
    answer = answer_from_result(result)
    assert answer.text == statements[0]
    assert answer.findings[0].text == statements[0]
    assert not is_empty(answer)


def test_an_absence_task_rejects_a_prose_confabulation() -> None:
    """An unanswerable task with no forbidden marker must still fail a claim.

    Eight expect_empty tasks have an empty must_not_contain list by design
    (task-set.md section 3.2): a correct answer saying "there is none" would
    contain any such marker too. The adapter therefore has to turn a system's
    conclusions into findings, or those tasks stop rejecting confabulation.
    """
    task = next(task for task in ALL_TASKS if task.expect_empty and not task.must_not_contain)
    claimed = SystemResult(
        answer_text="a caller exists",
        assertions=(Assertion("a caller exists"),),
    )
    assert not check(task, answer_from_result(claimed)).passed

    # Saying "there is none" in limitations produces no conclusion, and thus
    # no finding: this is the shape of a correct absence answer.
    silent = SystemResult(answer_text='{"conclusions":[],"limitations":["none found"]}')
    assert is_empty(answer_from_result(silent))
    assert check(task, answer_from_result(silent)).passed


def test_scripted_provider_reports_deterministic_tokens() -> None:
    """Token consumption has to be measured, not a zero or a made-up constant."""
    from dexatlas.agent.providers.base import ModelRequest, Observation

    request = ModelRequest(
        instructions="answer briefly",
        question="what is here?",
        turns=(Observation(tool="t", call_id="c", content="one two three"),),
    )
    provider = scripted_provider()
    response = provider.complete(request)
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.prompt_tokens == len(request.instruction_text().split()) + 3


def test_committed_traces_regenerate_the_published_report() -> None:
    """Every published figure can be recomputed by a script in the repository.

    The report's regeneration command reads a checked-in trace file, not this
    machine's .scratch. If the evidence disappeared, the report would be a
    number nobody can re-derive -- which the project's rules forbid.
    """
    assert COMMITTED_TRACES.is_file(), "the measurement evidence is not in the repository"
    run = _run_from_document(json.loads(COMMITTED_TRACES.read_text(encoding="utf-8")))
    assert run.task_count == len(ALL_TASKS)
    assert len(run.traces) == 3 * len(ALL_TASKS)
    report = (Path(__file__).resolve().parents[1] / "docs/benchmarks/comparison.md").read_text(
        encoding="utf-8"
    )
    for name, values in run.metrics.items():
        for metric in METRIC_NAMES:
            assert format_value(metric, values[metric]) in report, (name, metric)
    assert _markdown(run) == report
