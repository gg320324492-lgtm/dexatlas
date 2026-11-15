"""``benchmarks/run.py`` 按配置路由任务集的回归测试(Phase 3 M6 层级 3 复验发现).

``--configuration no-*`` 的直觉用法是「只跑该配置的题、只建该配置的工作区」,
但旧实现只把所选配置加入 Analyze 集, 任务集仍返回全部 92 题, ``_run_tasks``
随即在 ``analyses[(task.configuration, task.sample)]`` 处 KeyError
(m6-level3-recheck.md §6). 这里锁住三件事:

* no-* 配置只路由**声明**适用该配置的题;
* 组合出空集时是明确的「no tasks selected」退出码 2, 不是静默全选;
* 不带 ``--configuration`` 的正常路径仍是全量 92 题, 判分与题号不受影响.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from benchmarks.model import Category, Configuration
from benchmarks.run import _selected_tasks
from benchmarks.tasks import ALL_TASKS


def _args(**overrides: object) -> argparse.Namespace:
    """A parsed-args stand-in with the runner's defaults."""
    values: dict[str, object] = {
        "configuration": None,
        "category": None,
        "task": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_configuration_filter_routes_only_declared_tasks() -> None:
    """--configuration no-jadx 只选题面声明 no-jadx 的题, 不再全选 92 题."""
    selected = _selected_tasks(_args(configuration=["no-jadx"]))
    assert selected, "no-jadx 配置在题集中有声明它的题"
    assert all(task.configuration is Configuration.NO_JADX for task in selected)
    assert len(selected) < len(ALL_TASKS)
    # 全集里确实存在声明 no-jadx 的题, 过滤不是碰巧为空.
    declared = [task for task in ALL_TASKS if task.configuration is Configuration.NO_JADX]
    assert {task.id for task in selected} == {task.id for task in declared}


def test_configuration_filter_keeps_full_set_order() -> None:
    """过滤不重排: 子集仍按全集顺序出现(报告可比性的前提)."""
    selected = _selected_tasks(_args(configuration=["no-apktool"]))
    expected = [task.id for task in ALL_TASKS if task.configuration is Configuration.NO_APKTOOL]
    assert [task.id for task in selected] == expected


def test_no_jadx_and_no_apktool_each_select_their_own_tasks() -> None:
    """两个 no-* 配置各自路由到自己的题, 互不串集."""
    jadx = {task.id for task in _selected_tasks(_args(configuration=["no-jadx"]))}
    apktool = {task.id for task in _selected_tasks(_args(configuration=["no-apktool"]))}
    assert jadx and apktool
    assert jadx.isdisjoint(apktool)


def test_task_prefix_combined_with_configuration_intersects() -> None:
    """--task 与 --configuration 同时给出时取交集(与 --category 同一语义)."""
    selected = _selected_tasks(
        _args(configuration=["no-jadx"], task=["partial.no-jadx-the-failure-is-recorded"])
    )
    assert [task.id for task in selected] == ["partial.no-jadx-the-failure-is-recorded"]
    assert selected[0].configuration is Configuration.NO_JADX


def test_configuration_filter_with_no_matching_task_is_empty() -> None:
    """配置与 --task 组合不出任何题时返回空集; main 把它报成明确错误."""
    selected = _selected_tasks(_args(configuration=["no-jadx"], task=["manifest.package.demo"]))
    assert selected == []


def test_category_filter_still_works_alongside_configuration() -> None:
    """--category 与 --configuration 叠加仍取交集, 不受新过滤影响."""
    selected = _selected_tasks(_args(configuration=["no-jadx"], category=[Category.PARTIAL.value]))
    assert selected
    assert all(
        task.configuration is Configuration.NO_JADX and task.category is Category.PARTIAL
        for task in selected
    )


def test_without_configuration_filter_the_full_set_is_selected() -> None:
    """正常路径(不带 --configuration)仍覆盖全集, 判分集不变."""
    selected = _selected_tasks(_args())
    assert len(selected) == len(ALL_TASKS)
    assert [task.id for task in selected] == [task.id for task in ALL_TASKS]


def test_main_reports_no_tasks_selected_for_an_impossible_combination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """端到端: 不适用的组合得到退出码 2 与明确提示, 而不是 KeyError."""
    from benchmarks.run import main

    code = main(
        [
            "--configuration",
            "no-jadx",
            "--task",
            "manifest.package.demo",
            "--workspace",
            str(tmp_path / "ws"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "no tasks selected" in captured.err
