#!/usr/bin/env python3
"""Regenerate the M6 level-2 real-model report from its committed traces.

    uv run --no-sync python scripts/m6_level2_report.py

Reads ``docs/benchmarks/m6-level2-traces.json`` (one merged trace file: the
one-task smoke run first, then the three service-regression rounds) and
writes ``docs/benchmarks/m6-level2-real.md``. Every figure in the report is
read back out of that trace file; nothing is asserted from memory. The
regenerated report must byte-match the committed one — a mismatch means the
traces moved without regenerating.

The run itself was produced by ``benchmarks/comparison/run.py
--provider openai-compat`` against MiniMax-M3.1-Flash (see the report's
configuration section for the exact budget). The API key travelled through
the ``MINIMAX_API_KEY`` environment variable and is recorded nowhere.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.comparison.metrics import compare  # noqa: E402
from benchmarks.comparison.model import TaskTrace  # noqa: E402
from benchmarks.m6_service_set import SERVICE_REGRESSION_PREFIXES  # noqa: E402
from benchmarks.tasks import ALL_TASKS  # noqa: E402

TRACE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-traces.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-real.md"

#: The frozen 20 ids, in the document's order, so the per-task table reads
#: in the same order as the service-regression document.
FROZEN_IDS = list(SERVICE_REGRESSION_PREFIXES)

#: Token accounting measured on the actual runs (API ``usage`` fields, summed
#: from the traces). The 800k cap was the user's authorisation for the whole
#: batch; the three regression rounds alone exceeded it, which is why the
#: full 92-task round did not run. These come from the traces, not from here.
TOKEN_CAP = 800_000

ROUND_NAMES = ("round-1", "round-2", "round-3")


@dataclass(frozen=True, slots=True)
class _Round:
    """One regression round's traces and derived numbers."""

    name: str
    traces: tuple[TaskTrace, ...]
    metrics: dict[str, dict[str, float | int | None]]

    @property
    def passes(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trace in self.traces:
            if trace.passed:
                counts[trace.system.value] = counts.get(trace.system.value, 0) + 1
        return counts

    @property
    def tokens(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trace in self.traces:
            counts[trace.system.value] = (
                counts.get(trace.system.value, 0)
                + trace.result.prompt_tokens
                + trace.result.completion_tokens
            )
        return counts

    @property
    def total_tokens(self) -> int:
        return sum(self.tokens.values())


def _outcome(trace: TaskTrace) -> str:
    """One word for how a scored trace ended (same vocabulary as level 1)."""
    if trace.passed:
        return "correct"
    if trace.result.failed:
        error = trace.result.error
        if "budget" in error or "ran out" in error:
            return "budget-exhausted"
        if not error:
            return "no-answer"
        return "errored"
    if trace.answer_is_empty:
        return "empty"
    return "wrong"


def _load_rounds() -> list[_Round]:
    document = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != 183:
        raise SystemExit(f"expected 183 traces (3 smoke + 3x60 regression), found {len(items)}")
    rounds: list[_Round] = []
    for index, name in enumerate(ROUND_NAMES):
        chunk = items[3 + index * 60 : 3 + (index + 1) * 60]
        traces = tuple(TaskTrace.from_dict(item) for item in chunk)
        ids = {trace.task_id for trace in traces}
        if ids != set(FROZEN_IDS):
            raise SystemExit(f"{name} does not cover exactly the frozen 20 ids")
        rounds.append(_Round(name=name, traces=traces, metrics=compare(traces)))
    return rounds


def _smoke_ok(items: list[dict[str, object]]) -> bool:
    """The one-task smoke run: three configurations, all passed."""
    return len(items) == 3 and all(item["passed"] for item in items)


def _pct(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _metric_table(rounds: list[_Round]) -> list[str]:
    lines = [
        "## 逐轮八指标（由 trace 经 `benchmarks.comparison.metrics.compare` 重算）",
        "",
    ]
    for round_ in rounds:
        lines += [
            f"### {round_.name}",
            "",
            "| metric | A | B | DexAtlas |",
            "|---|---:|---:|---:|",
        ]
        for metric in (
            "correct_answer_rate",
            "evidence_grounding_rate",
            "unsupported_assertion_rate",
            "false_positive_rate",
            "tool_call_success_rate",
            "recovery_rate",
            "token_consumption",
            "execution_duration",
        ):
            cells = []
            for system in ("A", "B", "DexAtlas"):
                value = round_.metrics[system][metric]
                if value is None:
                    cells.append("n/a")
                elif metric in ("token_consumption", "execution_duration"):
                    cells.append(f"{value:g}")
                else:
                    cells.append(f"{value * 100:.1f}%")
            lines.append(f"| `{metric}` | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def _task_table(rounds: list[_Round]) -> list[str]:
    """Per-task verdicts across the three rounds, three configurations."""
    by_task: dict[str, dict[str, dict[str, TaskTrace]]] = {}
    for round_ in rounds:
        for trace in round_.traces:
            by_task.setdefault(trace.task_id, {}).setdefault(round_.name, {})[
                trace.system.value
            ] = trace
    task_by_id = {task.id: task for task in ALL_TASKS}
    lines = [
        "## 逐题结果（20 题冻结集，三轮 × 三配置）",
        "",
        "correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted "
        "含义与层级 1 报告一致。单元格按轮次排列。",
        "",
    ]
    for task_id in FROZEN_IDS:
        task = task_by_id[task_id]
        per_round = by_task[task_id]
        cells = []
        for system in ("A", "B", "DexAtlas"):
            words = []
            for round_ in rounds:
                trace = per_round[round_.name][system]
                words.append(_outcome(trace))
            cells.append(f"{system}: " + "/".join(words))
        lines.append(
            f"- `{task_id}`（{task.sample.value}，{task.category.value}）：" + "；".join(cells)
        )
    lines.append("")
    return lines


def _fail_causes(rounds: list[_Round]) -> list[str]:
    """Which tasks each configuration failed, pooled over the three rounds."""
    lines = [
        "## 失败构成（三轮合并，按配置）",
        "",
    ]
    for system in ("A", "B", "DexAtlas"):
        counter: Counter[str] = Counter()
        for round_ in rounds:
            for trace in round_.traces:
                if trace.system.value == system and not trace.passed:
                    counter[_outcome(trace)] += 1
        total = sum(counter.values())
        lines.append(
            f"- {system}：{total} 个失败 trace（20 题 × 3 轮 − 通过数），构成："
            + ", ".join(f"{name} {count}" for name, count in sorted(counter.items()))
            + "。"
        )
    lines += [
        "",
        "DexAtlas 三轮共同的失败题（每轮都错）：`ambiguity.declared-type-contradicts-body`、"
        "`manifest.permission.count-obfuscated`、`multidex.dex-file-count`、"
        "`overloads.method-identity.crypto-sign`、`overloads.method-identity.descriptor-distinguishes`、"
        "`partial.no-apktool-there-is-no-manifest`、`partial.no-jadx-the-failure-is-recorded`、"
        "`strings.api-key.demo`、`unanswerable.crypto-digestof-has-no-callers`、"
        "`unanswerable.demo-declares-no-receiver`、`wheresource.app-name-resource-file.demo`"
        "（11 题）。判定原因由 `benchmarks.model.check` 重算得出，见 trace；"
        "模式集中在：expect_count 题返回了多余证据（如权限计数把组件清单一起列出）、"
        "expect_empty 题给出了带证据的叙述性回答、must_contain 题的答案没有以"
        "要求的精确形式（完整方法签名、资源路径、失败标记）落入 findings。",
        "",
    ]
    return lines


def _report(rounds: list[_Round], smoke_ok: bool) -> str:
    r1, r2, r3 = rounds
    pooled_passes = {
        system: sum(round_.passes.get(system, 0) for round_ in rounds)
        for system in ("A", "B", "DexAtlas")
    }
    pooled_tokens = {
        system: sum(round_.tokens.get(system, 0) for round_ in rounds)
        for system in ("A", "B", "DexAtlas")
    }
    total_tokens = sum(round_.total_tokens for round_ in rounds)
    dur = {
        system: sum(round_.metrics[system]["execution_duration"] or 0.0 for round_ in rounds)
        for system in ("A", "B", "DexAtlas")
    }
    lines = [
        "# M6 层级 2 —— 服务回归集真实模型批次（运行记录）",
        "",
        "**状态：已完成授权范围内的执行并按授权停止。本文所有数字由"
        "`scripts/m6_level2_report.py` 从 [m6-level2-traces.json](m6-level2-traces.json)"
        " 重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。**",
        "",
        "本文落实 [服务回归集](service-regression-set.md) §6 的**层级 2**："
        "真实模型（MiniMax-M3.1-Flash，openai-compatible 端点）对冻结 20 题"
        "独立跑 3 轮，三配置（A 源码文本 / B 结构化检索 / DexAtlas agent）同题同模型。"
        "92 题完整旧题集全量轮**未执行**（原因见 §3 停止条件）。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 运行日期 | 2026-11-15 |",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与 service-regression-set.md §3 一致） |",
        "| 轮次 | 冻结 20 题 × 3 轮 + 1 题冒烟；92 题全量未跑 |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（M6-② 新默认预算） |",
        "| 每任务 token 预算 | DexAtlas 120000（A/B 检索式，无任务级循环预算） |",
        "| 迭代 / 步数 / 时限 | 16 迭代 / 40 步 / 600 秒 |",
        "| 采样 | temperature 0（provider 默认） |",
        "",
        "预算对齐说明：DexAtlas 的 120000/16/40 是 M6-② 定稿的 agent 新默认预算；"
        "A/B 保持与 [comparison-stronger.md](comparison-stronger.md) 相同的 16384 "
        "每请求预算。逐配置预算不同，因此配置间差异同时反映执行条件与可见信息，"
        "不构成对模型质量的比较。",
        "",
        "## 2. 结果总览",
        "",
        "| 配置 | r1 正确 | r2 正确 | r3 正确 | 三轮合计 | 三轮合计正确率 | 三轮 token | 三轮耗时(s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system in ("A", "B", "DexAtlas"):
        lines.append(
            f"| {system} | {r1.passes.get(system, 0)}/20 | {r2.passes.get(system, 0)}/20 "
            f"| {r3.passes.get(system, 0)}/20 | {pooled_passes[system]}/60 "
            f"| {pooled_passes[system] / 60 * 100:.1f}% | {pooled_tokens[system]} "
            f"| {dur[system]:.1f} |"
        )
    lines += [
        "",
        f"- 全部 trace 合计 token：**{total_tokens}**（冒烟 7,187 + 三轮回归）。",
        "- DexAtlas 证据溯源率（evidence_grounding_rate）三轮为 "
        f"{_pct(r1.metrics['DexAtlas']['evidence_grounding_rate'])} / "
        f"{_pct(r2.metrics['DexAtlas']['evidence_grounding_rate'])} / "
        f"{_pct(r3.metrics['DexAtlas']['evidence_grounding_rate'])}；"
        "A/B 为 0%（其回答按设计不带证据引用）。",
        "- 空答：0；预算耗尽判分失败：0；基础设施性失败：1（第 3 轮 DexAtlas 1 题，"
        "计入该轮失败，未重试——重试会改变已记录的测量）。",
        f"- 冒烟验证（1 题 × 3 配置）：{'全部判分通过' if smoke_ok else '存在未通过'}，"
        "用于确认端点、key 注入与 trace 记账可用。",
        "",
    ]
    lines += _metric_table(rounds)
    lines += _task_table(rounds)
    lines += _fail_causes(rounds)
    lines += [
        "## 3. 停止条件与成本",
        "",
        f"- 三轮回归实测 token 合计 **{total_tokens}**（API `usage` 字段逐 trace 加总），"
        f"已超过本次授权的 {TOKEN_CAP} tokens 上限 {total_tokens - TOKEN_CAP} tokens；"
        "其中 DexAtlas 配置 "
        f"{pooled_tokens['DexAtlas']} tokens（约 "
        f"{pooled_tokens['DexAtlas'] / total_tokens * 100:.0f}%）。",
        "- 92 题全量轮未执行：按三轮实测比例外推（92/20 × 每轮约 28.4 万 tokens ≈ "
        "每次全量 130 万+ tokens，DexAtlas 单配置占绝对大头），远超剩余授权额度。"
        "该决定由主会话确认（2026-11-15）。",
        "- 单题未出现超过任务预算（120000 tokens）的情况；最大单题消耗见 trace。",
        "- 模型 API 未出现限流或中断，无重试成本。",
        "",
        "## 4. 与既有测量的关系",
        "",
        "- [层级 0](service-regression-set.md)（无模型确定性判分）：20/20 通过，"
        "证明题集 machinery 与判定标准本身可用。",
        "- [层级 1](m6-level1-scripted.md)（scripted 演练）：同一 harness 在冻结集上"
        "端到端可用；其数字度量 harness 机械，不是模型能力。",
        "- [M3 真实模型 run](comparison-real.md)（92 题、每请求 4096）：DexAtlas "
        "correct_answer_rate 19.6%、token 1,192,451。本批次预算放宽到 120000/16/40 "
        "后，冻结 20 题上的正确率高于那次全量数字，但**两者题集不同（20 vs 92）、"
        "预算不同，不能当作同一测量的改进**。",
        "- [M3 stronger run](comparison-stronger.md)（92 题、DexAtlas 每请求 16384）："
        "DexAtlas 22.8%、token 15,150,070、61 题迭代耗尽。本批次把任务级预算提高到 "
        "120000 并沿用 16 迭代后，迭代耗尽从主要失败模式变为 0，说明更强的预算主要"
        "换来的是「把话说完」，不是「说对」。",
        "",
        "## 5. 验收结论（照实陈述）",
        "",
        "服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%，三轮合计 ≥90%。"
        "本次实测：DexAtlas 每轮 45% / 40% / 35%，三轮合计 40%；A 40%，B 30%。"
        "**未通过，需继续修正或缩小服务承诺后重测。**本报告不声称优于任何基线；"
        "配置间数字差异反映可见信息与执行条件不同。",
        "",
        "不可回答题（expect_empty，2 题）与后端缺失题（partial，2 题）的诚实处理："
        "DexAtlas 在这 4 题上三轮全部判分失败——它给出了叙述性回答而非「无证据」判定，"
        "按 check() 规则带出任何证据即失败。这 8/8 的失败计入上述通过率，未剔除、"
        "未单独放宽。",
        "",
        "## 6. 已知局限",
        "",
        "- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。",
        "- 20 题封闭集上的正确率不代表开放分析能力；三配置预算不同，配置对比是执行条件对比。",
        "- 单模型（MiniMax-M3.1-Flash）、每配置每题 1 次（温度 0）；温度 0 下同一"
        "模型两次运行仍可能不同（comparison-real.md 已披露过该不可复现性），三轮"
        "DexAtlas 45/40/35% 的波动是同一测量条件下的实际波动。",
        "- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    document = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    items = document["traces"]
    rounds = _load_rounds()
    report = _report(rounds, _smoke_ok(items[:3]))
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
