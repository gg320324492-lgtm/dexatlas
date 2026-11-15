"""按题 id 选子集的回归测试(Phase 3 M6 层级 1 引入的 --task 过滤).

服务回归集要在这台 harness 上跑 20 题子集, 而判分靠 reference 题号对回
``ALL_TASKS``. 过滤必须只改"问哪些题", 绝不能改动题号--否则判分器拿到
的题号与题目错位, 判出来的成绩是另一套题的. 这里守住三件事: 子集的题号
仍是全集题号、判分对象仍是题号指向的那道题、空匹配是错误而不是空跑.
"""

from __future__ import annotations

import pytest
from benchmarks.comparison.adapters import answer_from_result
from benchmarks.comparison.model import SystemResult, TaskTrace
from benchmarks.comparison.run import _questions, _score, _select_tasks
from benchmarks.m6_service_set import SERVICE_REGRESSION_PREFIXES
from benchmarks.model import check


def _frozen_ids() -> list[str]:
    """The service-regression ids, as the frozen document lists them."""
    assert len(SERVICE_REGRESSION_PREFIXES) == 20
    return list(SERVICE_REGRESSION_PREFIXES)


def test_task_prefixes_select_exactly_the_named_tasks() -> None:
    selected = _select_tasks(["manifest.package.demo", "multidex.dex-file-count"])
    assert [task.id for task in selected] == [
        "manifest.package.demo",
        "multidex.dex-file-count",
    ]


def test_a_prefix_selects_every_task_that_starts_with_it() -> None:
    selected = _select_tasks(["components.exported"])
    assert [task.id for task in selected] == [
        "components.exported.demo",
        "components.exported.obfuscated",
        "components.exported.multidex-single",
    ]


def test_no_match_is_an_error_not_an_empty_run() -> None:
    with pytest.raises(SystemExit, match="no task id starts with"):
        _select_tasks(["no-such-prefix"])


def test_subset_questions_keep_their_full_set_references() -> None:
    """A subset question keeps its full-set number: scoring depends on it."""
    full = {question.question: question.reference for question in _questions()}
    tasks = _select_tasks(_frozen_ids())
    for question in _questions(tasks):
        assert question.reference == full[question.question]


def test_scoring_a_subset_trace_resolves_the_same_task() -> None:
    """The scorer maps a subset trace's reference back to the same task."""
    tasks = _select_tasks(["manifest.package.demo"])
    (question,) = _questions(tasks)
    raw = TaskTrace(
        reference=question.reference,
        system="A",
        provider="scripted",
        model="",
        max_tokens=2048,
        question=question.question,
        result=SystemResult(),
    )
    scored = _score(question, raw)
    assert scored.task_id == "manifest.package.demo"
    # And the verdict is the one the same answer gets under direct check().
    direct = check(tasks[0], answer_from_result(raw.result))
    assert scored.passed == direct.passed
