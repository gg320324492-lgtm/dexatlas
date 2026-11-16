#!/usr/bin/env python3
"""Regenerate the M6 level-2 three-round full-rerun acceptance report from traces.

    uv run --no-sync python scripts/m6_level2_retest4_report.py

Reads the three committed trace files of the post-fix full three-round
service-regression-set rerun (``docs/benchmarks/m6-level2-retest4-traces-r1.json``,
``-r2.json`` and ``-r3.json`` — three configurations x 20 frozen tasks per
round) and writes ``docs/benchmarks/m6-level2-retest4.md``. This is the
acceptance measurement that follows the narrow verification
(``docs/benchmarks/m6-level2-narrow-verify-incomplete.md``): the acceptance
line comes from ``docs/benchmarks/service-regression-set.md`` §5 and
``docs/roadmap/phase3-plan.md`` §5 (M6) — DexAtlas ≥16/20 (≥80%) in each
round and ≥54/60 (≥90%) across the three rounds combined.

Every figure in the report is recomputed from the three trace files; nothing
is asserted from memory. Regenerating the report must byte-reproduce the
committed one — a mismatch means the traces moved without regenerating. A
missing or incomplete round is a ``SystemExit`` that names the round, never
a traceback: an unfinished run must not silently produce a partial report.

The runs were produced by ``benchmarks/comparison/run.py --provider
openai-compat --api-key-env MINIMAX_API_KEY --task <frozen id>``, one task
per invocation, against MiniMax-M3.1-Flash at ``claude/m6-level2-verify``
``f9d9fd8`` (the execution-layer fix set plus the single-word C2 union). The
budget followed the same discipline as ``docs/benchmarks/m6-level2-retest-plan.md``:
per-task ``--total-tokens 24000`` and a 1,200,000 authorization across the
three rounds. The API key travelled through the ``MINIMAX_API_KEY``
environment variable and is recorded nowhere.
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

TRACE_PATHS = (
    REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest4-traces-r1.json",
    REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest4-traces-r2.json",
    REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest4-traces-r3.json",
)
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest4.md"

#: The frozen 20 ids, in the document's order, so the per-task table reads
#: in the same order as the service-regression document.
FROZEN_IDS = list(SERVICE_REGRESSION_PREFIXES)

#: The authorisation the three rounds ran under: a 1,200,000 total cap and a
#: 24,000 per-task break (same discipline as the retest plan).
TOTAL_CAP = 1_200_000
PER_TASK_BREAK = 24_000

#: The per-round acceptance line and the combined three-round line
#: (service-regression-set.md §5, phase3-plan.md §5 M6).
PER_ROUND_LINE = 16  # ≥16/20 = ≥80% per round
TOTAL_LINE = 54  # ≥54/60 = ≥90% across three rounds

SYSTEMS = ("A", "B", "DexAtlas")

CODE_STATE = "`claude/m6-level2-verify` `f9d9fd8`"
RUN_DATE = "2026-11-17"


@dataclass(frozen=True, slots=True)
class _Round:
    """One round's traces and derived numbers."""

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
            counts[trace.system.value] = counts.get(trace.system.value, 0) + trace.tokens
        return counts

    @property
    def total_tokens(self) -> int:
        return sum(self.tokens.values())

    def ids(self) -> set[str]:
        return {trace.task_id for trace in self.traces}


def _outcome(trace: TaskTrace) -> str:
    """One word for how a scored trace ended (same vocabulary as level 2)."""
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


def _load_round(path: Path, name: str, expected_tasks: int) -> _Round:
    if not path.exists():
        raise SystemExit(
            f"{name} trace file is missing: {path}\n"
            f"the three-round rerun is not complete; refusing to write a "
            f"partial acceptance report"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != expected_tasks * 3:
        raise SystemExit(
            f"expected {expected_tasks * 3} {name} traces "
            f"(3 configurations x {expected_tasks} tasks), found {len(items)}; "
            f"the round is not complete, refusing to write a partial report"
        )
    traces = tuple(TaskTrace.from_dict(item) for item in items)
    counts = Counter(trace.task_id for trace in traces)
    if any(count != 3 for count in counts.values()):
        raise SystemExit(f"{name} does not cover each task exactly three times")
    return _Round(name=name, traces=traces, metrics=compare(traces))


def _pct(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _metric_table(metrics: dict[str, dict[str, float | int | None]]) -> list[str]:
    lines = [
        "## 八指标（三轮合并，由 180 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）",
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
        for system in SYSTEMS:
            value = metrics[system][metric]
            if value is None:
                cells.append("n/a")
            elif metric in ("token_consumption", "execution_duration"):
                cells.append(f"{value:g}")
            else:
                cells.append(_pct(value))
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _round_overview(rounds: tuple[_Round, ...]) -> list[str]:
    lines = [
        "## 逐轮结果总览",
        "",
        "| 轮次 | A | B | DexAtlas | 该轮 token 合计 |",
        "|---|---:|---:|---:|---:|",
    ]
    for index, round_ in enumerate(rounds, start=1):
        passes = round_.passes
        lines.append(
            f"| r{index} | {passes.get('A', 0)}/20 | {passes.get('B', 0)}/20 "
            f"| {passes.get('DexAtlas', 0)}/20 | {round_.total_tokens} |"
        )
    lines.append("")
    return lines


def _combined_table(rounds: tuple[_Round, ...]) -> list[str]:
    lines = [
        "## 三轮合计",
        "",
        "| 配置 | 三轮正确合计 | 正确率 |",
        "|---|---:|---:|",
    ]
    for system in SYSTEMS:
        total = sum(round_.passes.get(system, 0) for round_ in rounds)
        lines.append(f"| {system} | {total}/60 | {total / 60 * 100:.1f}% |")
    lines += [
        "",
        f"三轮全部 trace 合计 token：**{sum(round_.total_tokens for round_ in rounds)}**"
        "（API `usage` 字段逐 trace 加总）。",
        "",
    ]
    return lines


def _task_table(rounds: tuple[_Round, ...]) -> list[str]:
    """Per-task verdicts: one row per frozen task, one cell per system."""
    by_task: dict[str, dict[str, list[TaskTrace]]] = {}
    for round_ in rounds:
        for trace in round_.traces:
            by_task.setdefault(trace.task_id, {}).setdefault(trace.system.value, []).append(trace)
    lines = [
        "## 逐轮 × 逐题结果（冻结集顺序；每格为该配置三轮的判定，`r1/r2/r3`）",
        "",
        "correct = 判分通过；wrong = 判分不通过；empty = 空答；errored = 运行"
        "错误；budget-exhausted = 任务级预算耗尽。**空答与预算耗尽均计为失败**"
        "（`passed` 判定与 `_outcome` 语义已保证这一点）。20 题完整分母，无 "
        "not-run。",
        "",
    ]
    for task_id in FROZEN_IDS:
        cells = []
        for system in SYSTEMS:
            outcomes = [_outcome(trace) for trace in by_task.get(task_id, {}).get(system, [])]
            cell = "/".join(outcomes) if outcomes else "n/a"
            cells.append(cell)
        lines.append(f"| {task_id} | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _verdict(rounds: tuple[_Round, ...]) -> list[str]:
    passes = [round_.passes.get("DexAtlas", 0) for round_ in rounds]
    combined = sum(passes)
    per_round_ok = all(count >= PER_ROUND_LINE for count in passes)
    combined_ok = combined >= TOTAL_LINE
    overall_ok = per_round_ok and combined_ok
    lines = [
        "## 验收判定（对照 service-regression-set.md §5 与 phase3-plan.md §5 M6）",
        "",
        "- 逐轮判定（DexAtlas）："
        + "；".join(
            f"r{index} {count}/20 = {count / 20 * 100:.1f}%（"
            + ("达到 ≥16/20" if count >= PER_ROUND_LINE else "未达 ≥16/20")
            + "）"
            for index, count in enumerate(passes, start=1)
        )
        + "。",
        f"- 三轮合计判定：DexAtlas {combined}/60 = {combined / 60 * 100:.1f}%，"
        + ("达到 ≥54/60（≥90%）" if combined_ok else "未达 ≥54/60（≥90%）")
        + "。",
    ]
    if overall_ok:
        lines += [
            "",
            "**总结论：达标。** 每轮 DexAtlas 均 ≥16/20，且三轮合计 ≥54/60；"
            "两条验收线同时满足，B1（服务回归集三轮真实模型复测）可关闭。",
        ]
    else:
        lines += [
            "",
            "**总结论：未达标。**"
            + ("" if per_round_ok else " 存在未达 ≥16/20 的轮次；")
            + ("" if combined_ok else " 三轮合计未达 ≥54/60；")
            + "按冻结纪律（service-regression-set.md §5）只能修正系统或缩小并"
            "重述服务承诺后重测，不得删题换通过率。",
        ]
    lines += [
        "",
        "对照参考（同轮 A/B，不构成优劣结论）：",
        "",
        "| 配置 | r1 | r2 | r3 | 三轮合计 |",
        "|---|---:|---:|---:|---:|",
    ]
    for system in ("A", "B"):
        counts = [round_.passes.get(system, 0) for round_ in rounds]
        lines.append(
            f"| {system} | {counts[0]}/20 | {counts[1]}/20 | {counts[2]}/20 | {sum(counts)}/60 |"
        )
    lines += [
        "",
        "A/B 与 DexAtlas 的预算不同（每请求 max_tokens 16384 对 120000、"
        "任务预算仅 DexAtlas 24,000），配置间数字差异反映可见信息与"
        "执行条件不同，不构成优劣结论。",
        "",
    ]
    return lines


def _cost_notes(rounds: tuple[_Round, ...]) -> list[str]:
    """Cost and stop-condition notes, stated from the traces, as level 2 does."""
    total = sum(round_.total_tokens for round_ in rounds)
    lines = [
        "## 3. 成本与停止条件（照实陈述）",
        "",
        f"- 三轮实测 token 合计 **{total}**（三轮分别为 "
        + "、".join(
            f"r{index} {round_.total_tokens}" for index, round_ in enumerate(rounds, start=1)
        )
        + f"），在三轮总授权 {TOTAL_CAP:,} 之内（余 {TOTAL_CAP - total}）。",
        f"- 每任务 token 闸 {PER_TASK_BREAK:,}（`--total-tokens 24000`）按方案"
        "启用；判分失败与空答不重跑，预算耗尽如实按 `budget-exhausted` 计。",
        "- 三轮均跑满 20 题，无熔断中止、无 not-run 题目。",
        "",
    ]
    return lines


def _report(rounds: tuple[_Round, ...]) -> str:
    for index, round_ in enumerate(rounds, start=1):
        ran_ids = round_.ids()
        missing = [task_id for task_id in FROZEN_IDS if task_id not in ran_ids]
        assert not missing, f"r{index} traces missing frozen tasks: {missing}"
    combined_metrics = compare([trace for round_ in rounds for trace in round_.traces])
    lines = [
        "# M6 层级 2 —— 服务回归集真实模型三轮完整重测（执行层修复后验收测量）",
        "",
        "**状态：这是执行层修复成套落地后的三轮完整重测（B1 验收测量），按 "
        "[m6-level2-retest-plan.md](m6-level2-retest-plan.md) 的预算纪律执行；验收线来自 "
        "[service-regression-set.md](service-regression-set.md) §5 与 "
        "[phase3-plan.md](../roadmap/phase3-plan.md) §5 M6（每轮 ≥16/20，三轮"
        "合计 ≥54/60）。本文所有数字由 `scripts/m6_level2_retest4_report.py` 从 "
        "[m6-level2-retest4-traces-r1.json](m6-level2-retest4-traces-r1.json)、"
        "[m6-level2-retest4-traces-r2.json](m6-level2-retest4-traces-r2.json)、"
        "[m6-level2-retest4-traces-r3.json](m6-level2-retest4-traces-r3.json) "
        "三个 trace 文件重算生成，未手改任何数字；重跑脚本应得到逐字节相同的"
        "文件。任一轮 trace 缺失或不完整时本脚本拒绝生成报告。**",
        "",
        "本文回答一个问题：执行层修复（limitations 判分、预算耗尽单列 outcome、"
        "端点故障重试、XML 泄漏容错）与 C2 单词并集兜底落地后，冻结 20 题服务"
        "回归集在真实模型（MiniMax-M3.1-Flash）上完整跑满三轮，DexAtlas 是否"
        "同时满足每轮 ≥80% 与三轮合计 ≥90% 的验收线。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 运行日期 | {RUN_DATE} |",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、前三轮复测同一题集、同一顺序） |",
        "| 轮次 | 冻结 20 题 × 3 轮 × 3 配置 = 180 条 trace；三轮均为完整 20 题 |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与前几轮一致） |",
        f"| 每任务 token 预算 | DexAtlas {PER_TASK_BREAK:,}（方案 §2.1 单题闸） |",
        "| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |",
        f"| 总额熔断 | 三轮总授权 {TOTAL_CAP:,} tokens |",
        f"| 代码状态 | {CODE_STATE} |",
        "",
        f"三轮在同一代码（{CODE_STATE}，含执行层修复成套与 C2 单词并集兜底）、"
        "同一模型、同一题集、同一配置下完成。",
        "",
    ]
    lines += _round_overview(rounds)
    lines += _combined_table(rounds)
    lines += _metric_table(combined_metrics)
    lines += _task_table(rounds)
    lines += _verdict(rounds)
    lines += _cost_notes(rounds)
    lines += [
        "## 已知局限",
        "",
        "- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。",
        "- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同；三轮合计"
        "数字不外推为该配置的稳定通过率。",
        "- **first-party 小样本**：样本全部为 first-party 小型 APK（examples/ "
        "五样本），不外推到真实规模或加固样本。",
        "- **预算不对等**：A/B 与 DexAtlas 的每请求 max_tokens 与任务预算不同，"
        "配置间数字差异不构成优劣结论。",
        "- **token 口径**：token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。",
        "",
        "## 复现命令",
        "",
        "```bash",
        "# key 经环境变量注入，不写入任何文件",
        'export MINIMAX_API_KEY="<key>"',
        'export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"',
        'export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"',
        "# 逐题执行，每题一次调用，批间核对累计 token：",
        "uv run --no-sync python benchmarks/comparison/run.py \\",
        "  --provider openai-compat --api-key-env MINIMAX_API_KEY \\",
        "  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \\",
        "  --budget 16384 --agent-budget 120000 --total-tokens 24000 \\",
        "  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \\",
        "  --output .scratch/m6-retest-verify/full-rerun/r1/<task-id> --task <task-id>",
        "# round2、round3 同式，仅 --output 目录不同：",
        "#   .scratch/m6-retest-verify/full-rerun/r2/<task-id>",
        "#   .scratch/m6-retest-verify/full-rerun/r3/<task-id>",
        "# 报告再生：",
        "uv run --no-sync python scripts/m6_level2_retest4_report.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rounds = tuple(
        _load_round(path, f"round{index}", expected_tasks=20)
        for index, path in enumerate(TRACE_PATHS, start=1)
    )
    report = _report(rounds)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
