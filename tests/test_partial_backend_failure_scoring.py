"""partial.* 两题的判分回归测试(Phase 3 M6-③).

失败分析(docs/benchmarks/m6-level2-failure-analysis.md §5.6/§9)指出:
comparison harness 只用 ``Configuration.FULL`` Analyze, 题面声明的
``no-jadx`` / ``no-apktool`` 配置没有任何消费者; 于是「后端缺失时系统是否
诚实记录失败」这两题, agent 如实回答反而判负(层级 2 三轮 6 题次全败).

修复分两层, 本文件各给红→绿证据:

* 判分层: ``Task.expect_backend_failure`` 判定谓词——回答必须把缺失后端
  与其失败标记写在同一处, 编造数据(答出 manifest/包名)仍判负, 空答也
  判负(「什么都没说」不是「记录了失败」);
* 执行层: comparison harness 按题面配置 Analyze(后端路径置空即禁用),
  B 按题路由到对应工作区, D 的工具与证据读同一份分析; A 的检索面按题
  藏掉缺失后端的文件类别.
"""

from __future__ import annotations

from benchmarks.comparison.adapters import answer_from_result
from benchmarks.comparison.model import Assertion, Question, SystemResult
from benchmarks.model import Answer, Configuration, Finding, check
from benchmarks.tasks import ALL_TASKS

Q066 = "partial.no-jadx-the-failure-is-recorded"
Q067 = "partial.no-apktool-there-is-no-manifest"


def _task(task_id: str):
    """按 id 取题的小助手, 类型由调用点断言."""
    return next(task for task in ALL_TASKS if task.id == task_id)


def _question(task_id: str) -> Question:
    task = _task(task_id)
    number = ALL_TASKS.index(task) + 1
    return Question(
        reference=f"q{number:03d}",
        question=task.question,
        sample=task.sample.value,
        configuration=task.configuration.value,
    )


def test_the_two_partial_tasks_declare_the_new_predicate() -> None:
    """题面用 expect_backend_failure 声明判定, 不再依赖 expect_empty."""
    q066 = _task(Q066)
    q067 = _task(Q067)
    assert q066.expect_backend_failure == ("jadx",)
    assert q066.configuration is Configuration.NO_JADX
    assert not q066.expect_empty
    assert q067.expect_backend_failure == ("apktool",)
    assert q067.configuration is Configuration.NO_APKTOOL
    assert not q067.expect_empty
    # q067 的「不得答出包名」防线保留: 编造 manifest 仍判负.
    assert "com.example.demo" in q067.must_not_contain


def test_an_honest_failure_record_passes_q066() -> None:
    """「jadx 缺失已记录」的诚实回答, 以 not_installed 形态判过."""
    task = _task(Q066)
    recorded = Answer(
        findings=(Finding(text="jadx/not_installed: jadx is not installed or not on PATH"),)
    )
    assert check(task, recorded).passed
    # 语义等价词形(自然语言 not installed)同样判过: MCP 错误文本是空格形.
    prose = Answer(text="The analysis records that jadx is not installed.")
    assert check(task, prose).passed


def test_a_denial_of_the_failure_fails_q066() -> None:
    """「没有缺失」的否认(旧 harness 下的真实 trace 形态)判负."""
    task = _task(Q066)
    denial = Answer(
        findings=(
            Finding(
                text="the analysis is complete, missing_backends is empty, no backend is missing"
            ),
        )
    )
    result = check(task, denial)
    assert not result.passed
    assert "does not record the failure of jadx" in result.reason


def test_a_failure_named_apart_from_its_marker_fails_q066() -> None:
    """后端名与失败标记拆在两条 finding 里, 没有相连, 判负."""
    task = _task(Q066)
    split = Answer(
        findings=(
            Finding(text="jadx was one of the configured tools"),
            Finding(text="not_installed codes are recorded for absent tools"),
        )
    )
    assert not check(task, split).passed


def test_an_honest_failure_record_passes_q067() -> None:
    """「Apktool 缺失, manifest 未能解码, 错误已记录」判过.

    这正是失败分析里描述的、在旧 expect_empty 口径下必判负的诚实回答.
    """
    task = _task(Q067)
    honest = Answer(
        findings=(
            Finding(text="apktool/not_installed: apktool did not take part in this analysis"),
        ),
        text="No manifest is available: the APK reader (apktool) is not installed, "
        "and the analysis records the failure instead of producing an empty report.",
    )
    assert check(task, honest).passed


def test_q067_still_rejects_a_confabulated_manifest() -> None:
    """编造包名(旧 harness 下 DexAtlas 的真实失败形态)仍判负.

    该回答同时违反两条规则(未记录失败 + 答出禁止的包名), 判定先命中
    失败记录谓词; 这里锁的是结果(判负)而不是原因的先后.
    """
    task = _task(Q067)
    confabulated = Answer(
        findings=(Finding(text="package=com.example.demo"),),
        text="The manifest declares the package com.example.demo.",
    )
    assert not check(task, confabulated).passed


def test_q067_still_rejects_an_empty_answer() -> None:
    """空答(检索没找到所以什么都没说, A 的旧通过方式)不再判过."""
    task = _task(Q067)
    result = check(task, Answer())
    assert not result.passed
    assert "does not record the failure of apktool" in result.reason


def test_old_empty_expectation_would_have_failed_the_honest_answer() -> None:
    """红证据: 把同一诚实回答放进旧 expect_empty 口径, 它判负.

    这个测试锁定修订的动机——旧口径把「失败已记录」当成了「有证据即编造」,
    诚实回答无路可走. 若将来有人把 q067 改回 expect_empty, 这里会红.
    """
    from dataclasses import replace

    task = _task(Q067)
    honest = Answer(
        findings=(
            Finding(text="apktool/not_installed: apktool did not take part in this analysis"),
        ),
    )
    assert not task.expect_empty
    legacy = replace(task, expect_empty=True, expect_backend_failure=())
    assert not check(legacy, honest).passed


def test_prose_adapter_feeds_the_predicate_for_dexatlas() -> None:
    """D 的回答经 answer_from_result 进判分, 失败记录在结论里仍可判.

    adapter 把 assertions 变成 findings、把结论原文并成 Answer.text;
    这里按真实链路传入 Assertion, 而不是只填 answer_text.
    """
    honest = SystemResult(
        answer_text="The analysis records that the APK reader (apktool) is not "
        "installed; there is no manifest to read.",
        assertions=(
            Assertion(
                "The analysis records that the APK reader (apktool) "
                "is not installed; there is no manifest to read."
            ),
        ),
    )
    assert check(_task(Q067), answer_from_result(honest)).passed
    # 同一 adapter 下, 编造包名的 prose 答案仍判负.
    fabricated = SystemResult(
        answer_text="The manifest declares the package com.example.demo.",
        assertions=(Assertion("The manifest declares the package com.example.demo."),),
    )
    assert not check(_task(Q067), answer_from_result(fabricated)).passed
