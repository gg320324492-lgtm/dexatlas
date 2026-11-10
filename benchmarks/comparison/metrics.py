"""从 TaskTrace 计算 M3 的八项指标.

每个指标都写明分母. "无数据"用 ``None`` 而不是 0.0 或 1.0:一个没有
调用工具的配置不可以说成工具成功率 100%,一个没有产出断言的运行不可以
说成无支撑断言率 0%. 这是 §5 里"comparison never claims an improvement
the measurements do not support"在代码里的落点.

指标定义:

======================== ==========================================================
指标                      分子 / 分母
======================== ==========================================================
correct_answer_rate      判分通过的题 / 全部题
evidence_grounding_rate  有证据支撑的断言 / 全部断言
unsupported_assertion_rt 无证据支撑的断言 / 全部断言
false_positive_rate      未通过判分的非空断言 / 全部非空断言
tool_call_success_rate   成功的工具调用 / 全部工具调用
recovery_rate            从工具或模型失败中恢复并作答 / 发生过失败的运行
token_consumption        prompt + completion tokens 的总和 (计数,不是率)
execution_duration      全部运行的秒数总和 (计数,不是率)
======================== ==========================================================

``None`` 只在分母为零时出现;报告把这种情况写成 "n/a",不写成数字.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from benchmarks.comparison.model import TaskTrace

#: 八个指标的名字,顺序与 Phase 2 plan §5 一致.
METRIC_NAMES: tuple[str, ...] = (
    "correct_answer_rate",
    "evidence_grounding_rate",
    "unsupported_assertion_rate",
    "false_positive_rate",
    "tool_call_success_rate",
    "recovery_rate",
    "token_consumption",
    "execution_duration",
)

_RATE_NAMES = frozenset(METRIC_NAMES[:6])
_COUNT_NAMES = frozenset(METRIC_NAMES[6:])


@dataclass(slots=True)
class _Bucket:
    numerator: int = 0
    denominator: int = 0


def _rate(bucket: _Bucket) -> float | None:
    if bucket.denominator == 0:
        return None
    return bucket.numerator / bucket.denominator


def _add(bucket: _Bucket, numerator: int, denominator: int = 1) -> None:
    bucket.numerator += numerator
    bucket.denominator += denominator


def metrics_for(traces: Sequence[TaskTrace]) -> dict[str, float | int | None]:
    """计算一批 trace 的八项指标. 只接受同一个配置的 trace."""
    correct = _Bucket()
    grounding = _Bucket()
    false_positive = _Bucket()
    tool_success = _Bucket()
    recovery = _Bucket()

    for trace in traces:
        result = trace.result
        _add(correct, int(trace.passed))
        for assertion in result.assertions:
            _add(grounding, int(assertion.grounded))

        # A false positive is an assertion made on a task the scorer failed.
        # The denominator is every assertion made, not every task.
        _add(
            false_positive,
            len(result.assertions) * int(not trace.passed),
            len(result.assertions),
        )

        for call in result.tool_calls:
            _add(tool_success, int(call.ok))

        had_failure = any(not call.ok for call in result.tool_calls) or bool(result.error)
        if had_failure:
            _add(recovery, int(result.recovered and not result.failed))

    unsupported_num = grounding.denominator - grounding.numerator
    rates: dict[str, float | int | None] = {
        "correct_answer_rate": _rate(correct),
        "evidence_grounding_rate": _rate(grounding),
        "unsupported_assertion_rate": (
            None if grounding.denominator == 0 else unsupported_num / grounding.denominator
        ),
        "false_positive_rate": _rate(false_positive),
        "tool_call_success_rate": _rate(tool_success),
        "recovery_rate": _rate(recovery),
        "token_consumption": sum(trace.tokens for trace in traces),
        "execution_duration": round(sum(t.result.duration_seconds for t in traces), 3),
    }
    return rates


def compare(
    traces: Sequence[TaskTrace],
) -> dict[str, dict[str, float | int | None]]:
    """按配置分组计算指标,返回 ``{system.value: metrics}``."""
    grouped: dict[str, list[TaskTrace]] = {}
    for trace in traces:
        grouped.setdefault(trace.system.value, []).append(trace)
    return {name: metrics_for(group) for name, group in sorted(grouped.items())}


def format_value(name: str, value: float | int | None) -> str:
    """把指标写成报告里的文本;没有分母时是 ``n/a``,不是 0%."""
    if value is None:
        return "n/a"
    if name in _COUNT_NAMES:
        return str(value)
    return f"{value * 100:.1f}%"


def is_rate(name: str) -> bool:
    """这个指标是不是一个率. 测试与报告都用同一个判断."""
    return name in _RATE_NAMES
