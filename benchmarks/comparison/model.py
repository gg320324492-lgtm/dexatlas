"""对比 harness 的数据契约.

一份 trace 是一次"某配置回答某道题"的全部可审计记录. 指标只从 trace
计算,不从运行现场直接读:这样报告里的每个数字都能由
``benchmarks/comparison/run.py --input <trace.json> --metrics`` 重算.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class SystemKind(StrEnum):
    """M3 比较的三个配置."""

    SOURCE_TEXT = "A"
    """LLM + 反编译源码文本检索. """

    STRUCTURED = "B"
    """LLM + 结构化符号搜索与调用引用. """

    AGENT = "DexAtlas"
    """结构化工具 + 溯源 + 完整性感知 + 证据验证. """


@dataclass(frozen=True, slots=True)
class Question:
    """被测系统能看到的全部内容.

    字段与 ``benchmarks/run.py --emit-questions`` 一一对应. 这里没有
    task id,没有期望答案,没有任何 marking scheme.
    """

    reference: str
    question: str
    sample: str
    configuration: str


#: ``SystemResult.outcome`` 的取值: 这一次运行是如何结束的.
#:
#: 结束方式与回答内容是两个维度: 一次被预算闸停下的运行没有作答,它
#: 不能因为题面恰好可空答而判过; 一次作答的运行,其 limitations 记录
#: 它没能确认什么. 旧 trace 没有这个字段,读回时是空串,仍按旧口径
#: (failed/error)解释.
OUTCOME_ANSWERED = "answered"
OUTCOME_BUDGET_EXHAUSTED = "budget-exhausted"
OUTCOME_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Assertion:
    """回答里的一个主张,以及它有没有证据.

    ``grounded`` 只表示"有工具记录/源码定位支撑",不表示"说对了"——
    正确性由 :func:`benchmarks.model.check` 独立判定. 两者分开才能算出
    unsupported-assertion rate 和 false-positive rate.
    """

    text: str
    grounded: bool = False
    locator: str = ""
    verified: bool = False
    """是否由工具确定性建立 (项目自己的 EvidenceLevel 语义). """


@dataclass(frozen=True, slots=True)
class ToolCallTrace:
    """一次工具调用的结果."""

    tool: str
    ok: bool
    error: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class SystemResult:
    """一个配置对一道题的输出."""

    answer_text: str = ""
    findings: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    """What the tools returned, kept for audit but never scored as evidence."""

    assertions: tuple[Assertion, ...] = ()
    tool_calls: tuple[ToolCallTrace, ...] = ()
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0
    recovered: bool = False
    """本次运行是否从一次工具/模型失败中恢复并最终作答. """

    failed: bool = False
    """本次运行是否没能作答. 失败与"回答没有证据"是两件事. """

    outcome: str = ""
    """这次运行是如何结束的: :data:`OUTCOME_ANSWERED`、
    :data:`OUTCOME_BUDGET_EXHAUSTED` 或 :data:`OUTCOME_FAILED`.

    空串是旧 trace 的形状: 那时只有 ``failed``/``error``, 预算耗尽要从
    error 文案里猜. 新 trace 必须写明结束方式——任务级预算闸停下的运行
    没有作答, 不能被当作"回答了但答错", 更不能被当作"回答了且为空".
    """

    limitations: tuple[str, ...] = ()
    """模型自己说没能确认的事, 原样保留.

    一次降级作答 ("数不出来", "后端缺席所以无从读起") 的价值在
    limitations 里, 不在 findings 里. 它们随 trace 落盘、进判分通道,
    但永远不会变成 findings, 也不会替 ``must_contain`` 作证.
    """

    error: str = ""


@dataclass(frozen=True, slots=True)
class TaskTrace:
    """一次"配置 x 任务"的完整记录,是报告里所有数字的唯一来源."""

    reference: str
    system: SystemKind
    provider: str
    model: str
    max_tokens: int
    question: str
    task_id: str = ""
    """判分后才写入;被测系统从未见过这个字段. """

    passed: bool = False
    answer_is_empty: bool = False
    expects_absence: bool = False
    """正确答案是否为"什么都没有". 判分后才写入,不交给被测系统. """

    result: SystemResult = field(default_factory=SystemResult)

    @property
    def tokens(self) -> int:
        return self.result.prompt_tokens + self.result.completion_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "task_id": self.task_id,
            "system": self.system.value,
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "question": self.question,
            "passed": self.passed,
            "answer_is_empty": self.answer_is_empty,
            "expects_absence": self.expects_absence,
            "result": asdict(self.result),
        }

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> TaskTrace:
        raw = dict(document["result"])
        raw["assertions"] = tuple(Assertion(**item) for item in raw["assertions"])
        raw["tool_calls"] = tuple(ToolCallTrace(**item) for item in raw["tool_calls"])
        raw["findings"] = tuple(raw["findings"])
        raw["observations"] = tuple(raw.get("observations", ()))
        raw["limitations"] = tuple(raw.get("limitations", ()))
        raw.setdefault("outcome", "")
        return cls(
            reference=str(document["reference"]),
            task_id=str(document.get("task_id", "")),
            system=SystemKind(document["system"]),
            provider=str(document["provider"]),
            model=str(document["model"]),
            max_tokens=int(document["max_tokens"]),
            question=str(document["question"]),
            passed=bool(document["passed"]),
            answer_is_empty=bool(document["answer_is_empty"]),
            expects_absence=bool(document.get("expects_absence", False)),
            result=SystemResult(**raw),
        )
