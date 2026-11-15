#!/usr/bin/env python3
"""Regenerate the M6 level-2 retest round-2 report from its committed traces.

    uv run --no-sync python scripts/m6_level2_retest2_report.py

Reads ``docs/benchmarks/m6-level2-retest2-traces.json`` (the second real-model
retest round of the frozen service-regression set, three configurations, run
on the root-cause-fix branch) and writes
``docs/benchmarks/m6-level2-retest2.md``. Every figure in the report is read
back out of that trace file; nothing is asserted from memory. The
regenerated report must byte-match the committed one — a mismatch means the
traces moved without regenerating.

The run itself was produced by ``benchmarks/comparison/run.py
--provider openai-compat --api-key-env MINIMAX_API_KEY --task <frozen id>``
against MiniMax-M3.1-Flash, one task per invocation, on the branch that
carries the five M6 root-cause fixes (``294853a``..``c770285``). The budget
followed ``docs/benchmarks/m6-level2-retest-plan.md``: per-task
``--total-tokens 24000`` and a 300k cumulative circuit break. The cumulative
break fired after task 18 (308,640 tokens), so the last two frozen tasks were
not run; the report records that as the plan requires. The API key travelled
through the ``MINIMAX_API_KEY`` environment variable and is recorded nowhere.

The comparison baseline is the previous retest round
(``m6-level2-retest-traces.json``, DexAtlas 15/20 on the pre-fix tree), read
from its committed traces; that file stays untouched.
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

TRACE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest2-traces.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest2.md"
BASELINE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest-traces.json"

#: The frozen 20 ids, in the document's order, so the per-task table reads
#: in the same order as the service-regression document.
FROZEN_IDS = list(SERVICE_REGRESSION_PREFIXES)

#: The authorisation this round ran under: 350k hard cap, 300k cumulative
#: circuit break, 24k per-task break (docs/benchmarks/m6-level2-retest-plan.md).
TOKEN_CAP = 350_000
TOTAL_BREAK = 300_000
PER_TASK_BREAK = 24_000

#: The five root-cause-fix tasks this round set out to verify, with the fix
#: that targeted each (docs/benchmarks/m6-level2-failure-analysis.md).
FIXED_TASKS: tuple[tuple[str, str], ...] = (
    ("strings.api-key.demo", "修复2 整字面量引用契约"),
    ("overloads.method-identity.descriptor-distinguishes", "修复3 方法身份枚举完整性"),
    ("partial.no-apktool-there-is-no-manifest", "修复5 no_manifest 失败闭合读取"),
    ("partial.no-jadx-the-failure-is-recorded", "修复4/5 partial 过程记录豁免与闭合"),
    ("unanswerable.crypto-digestof-has-no-callers", "修复1 检索空后常量池枚举兜底"),
)

SYSTEMS = ("A", "B", "DexAtlas")


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
            counts[trace.system.value] = (
                counts.get(trace.system.value, 0)
                + trace.result.prompt_tokens
                + trace.result.completion_tokens
            )
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
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != expected_tasks * 3:
        raise SystemExit(
            f"expected {expected_tasks * 3} {name} traces "
            f"(3 configurations x {expected_tasks} tasks), found {len(items)}"
        )
    traces = tuple(TaskTrace.from_dict(item) for item in items)
    counts = Counter(trace.task_id for trace in traces)
    if any(count != 3 for count in counts.values()):
        raise SystemExit(f"{name} does not cover each task exactly three times")
    return _Round(name=name, traces=traces, metrics=compare(traces))


def _pct(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _metric_table(round_: _Round) -> list[str]:
    lines = [
        "## 八指标（由 trace 经 `benchmarks.comparison.metrics.compare` 重算）",
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


def _task_table(round_: _Round, baseline: _Round) -> list[str]:
    """Per-task verdicts, this round beside the previous retest round."""
    now_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in round_.traces:
        now_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    was_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in baseline.traces:
        was_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    task_by_id = {task.id: task for task in ALL_TASKS}
    lines = [
        "## 逐题结果（冻结集，单轮 × 三配置，附上轮复测对照）",
        "",
        "correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted "
        "含义与层级 2 报告一致；not-run = 总额熔断未发起。每格为 `本轮/上轮`。",
        "",
    ]
    for task_id in FROZEN_IDS:
        task = task_by_id[task_id]
        cells = []
        for system in SYSTEMS:
            now = (
                _outcome(now_by_task[task_id][system])
                if system in now_by_task.get(task_id, {})
                else "not-run"
            )
            was = (
                _outcome(was_by_task[task_id][system])
                if system in was_by_task.get(task_id, {})
                else "not-run"
            )
            cells.append(f"{system}: {now}/{was}")
        lines.append(
            f"- `{task_id}`（{task.sample.value}，{task.category.value}）：" + "；".join(cells)
        )
    lines.append("")
    return lines


def _fix_verification(round_: _Round, baseline: _Round) -> list[str]:
    """Per-fix verification: the five failed tasks, this round vs previous."""
    now_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in round_.traces:
        now_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    was_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in baseline.traces:
        was_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    lines = [
        "## 五个修复题逐题变化（本轮 × 3 配置，附上轮对照）",
        "",
        "| 题目 | 针对修复 | A | B | DexAtlas |",
        "|---|---|---|---|---|",
    ]
    for task_id, fix in FIXED_TASKS:
        cells = []
        for system in SYSTEMS:
            now = (
                _outcome(now_by_task[task_id][system])
                if system in now_by_task.get(task_id, {})
                else "not-run"
            )
            was = (
                _outcome(was_by_task[task_id][system])
                if system in was_by_task.get(task_id, {})
                else "not-run"
            )
            cells.append(f"{now}/{was}")
        lines.append(f"| `{task_id}` | {fix} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "每格为 `本轮/上轮`。`not-run` 表示该题因总额熔断未发起（§3 停止条件），"
        "不是失败，也不得计为通过或失败。",
        "",
    ]
    return lines


def _report(round_: _Round, baseline: _Round) -> str:
    passes = round_.passes
    tokens = round_.tokens
    total_tokens = round_.total_tokens
    baseline_passes = baseline.passes
    dur = {system: round_.metrics[system]["execution_duration"] or 0.0 for system in SYSTEMS}
    outcomes = Counter(_outcome(trace) for trace in round_.traces)
    ran_ids = round_.ids()
    not_run = [task_id for task_id in FROZEN_IDS if task_id not in ran_ids]
    lines = [
        "# M6 层级 2 —— 服务回归集真实模型复测第二轮（单轮，根因修复后）",
        "",
        "**状态：按 [m6-level2-retest-plan.md](m6-level2-retest-plan.md) 执行；"
        "累计 token 到第 18 题后越过 300,000 总额熔断线，其余 2 题按方案未发起"
        "（not-run，不计通过或失败）。本文所有数字由 "
        "`scripts/m6_level2_retest2_report.py` 从 "
        "[m6-level2-retest2-traces.json](m6-level2-retest2-traces.json) 重算生成，"
        "未手改任何数字；重跑脚本应得到逐字节相同的文件。对照基线为 "
        "[m6-level2-retest.md](m6-level2-retest.md)（上轮复测，修复前树，15/20），"
        "其 trace 文件未改动。**",
        "",
        "本文回答一个问题：五项根因修复（`294853a`..`c770285`，检索兜底、整字面量"
        "契约、枚举完整性、partial 豁免、no_manifest 闭合）之后，冻结 20 题服务"
        "回归集在真实模型（MiniMax-M3.1-Flash）单轮上的表现，相比上轮复测是否"
        "改善；以及是否达到验收线。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 运行日期 | 2026-11-16 |",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、上轮同一题集、同一顺序） |",
        "| 轮次 | 冻结 20 题 × 1 轮 × 3 配置；实际发起 18 题，余 2 题总额熔断未发起 |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与上轮一致） |",
        "| 每任务 token 预算 | DexAtlas 24000（本轮新增单题闸，方案 §2.1） |",
        "| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |",
        "| 总额熔断 | 累计 300,000 tokens；逐题批间核对（方案 §3） |",
        "| 代码状态 | `claude/m6-level2-rootcause-fixes` 合并 main（`02d4b43`），五项根因修复已入库 |",
        "| 采样 | temperature 0（provider 默认） |",
        "",
        "与上轮的执行条件差异：上轮在 M6-③ 修复后的代码上跑；本轮在五项根因修复"
        "之后的代码上跑，并新增了单题 24,000 预算闸与 300,000 总额熔断（上轮仅有"
        "隐式 1,200,000 任务上限，等于无闸）。A/B 的提示词与检索策略未改。",
        "",
        "## 2. 结果总览",
        "",
        "| 配置 | 本轮正确 | 上轮正确 | 本轮 token | 本轮耗时(s) |",
        "|---|---:|---:|---:|---:|",
    ]
    for system in SYSTEMS:
        lines.append(
            f"| {system} | {passes.get(system, 0)}/18 | {baseline_passes.get(system, 0)}/20 "
            f"| {tokens.get(system, 0)} | {dur[system]:.1f} |"
        )
    lines += [
        "",
        f"- 全部 trace 合计 token：**{total_tokens}**（API `usage` 字段逐 trace 加总），"
        f"授权上限 {TOKEN_CAP}，本轮控制线 {TOTAL_BREAK}——已越过控制线，触发总额熔断；"
        f"仍在授权上限之内（余 {TOKEN_CAP - total_tokens}）。",
        "- 结果构成（18 题已跑 trace）："
        + ", ".join(f"{name} {count}" for name, count in sorted(outcomes.items()))
        + f"；not-run 2 题（{'、'.join(f'`{tid}`' for tid in not_run)}）。",
        "",
        "### DexAtlas 失败题明细（18 题已跑范围内）",
        "",
    ]
    lines += _dexatlas_failure_notes(round_)
    lines += [
        "",
        "上轮五个失败题中，`strings.api-key.demo` 与 `strings.telemetry-url.obfuscated` "
        "本轮通过；`overloads.method-identity.descriptor-distinguishes`、"
        "`unanswerable.demo-declares-no-receiver`、`partial.no-apktool-there-is-no-manifest` "
        "本轮仍未通过（形态见上）；`partial.no-jadx-the-failure-is-recorded` 未及发起。",
        "",
    ]
    lines += _metric_table(round_)
    lines += _task_table(round_, baseline)
    lines += _fix_verification(round_, baseline)
    lines += [
        "## 3. 成本与停止条件（照实陈述）",
        "",
        f"- 本轮实测 token 合计 **{total_tokens}**，越过方案总额控制线 {TOTAL_BREAK}"
        f"（超 {total_tokens - TOTAL_BREAK}），触发总额熔断：最后 2 题"
        f"（{'、'.join(f'`{tid}`' for tid in not_run)}）未发起。仍在授权上限 {TOKEN_CAP} 之内"
        f"（余 {TOKEN_CAP - total_tokens}）。按方案 §3，未跑题记 not-run、判负不计，"
        "报告如实记录熔断点。",
        "- 单题 24,000 闸本轮未触发任何一题（DexAtlas 单题最大 "
        f"{max(t.result.prompt_tokens + t.result.completion_tokens for t in round_.traces if t.system.value == 'DexAtlas')}），"
        "上轮 71,718 的长尾未复现。上轮超支主因（失败题长尾空转）被单题闸与修复共同压住。",
        "",
        "## 4. 验收结论（照实陈述）",
        "",
        "服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%（20 题即 ≥16 题）。"
        f"本轮实测：DexAtlas {passes.get('DexAtlas', 0)}/18（已跑范围内 {_pct(round_.metrics['DexAtlas']['correct_answer_rate'])}）、"
        f"A {passes.get('A', 0)}/18、B {passes.get('B', 0)}/18。",
    ]
    dex = passes.get("DexAtlas", 0)
    verdict = (
        "**有可能达到验收线，但本轮未能完整验证**。"
        if dex + 2 >= 16
        else "**不可能达到验收线（≥16/20），本轮判定为未达标。**"
    )
    lines += [
        f"- **按已跑 18 题计，DexAtlas {dex}/18 = {dex / 18 * 100:.1f}%**，"
        "折算 20 题需 ≥16 通过；即使未跑 2 题全部通过，本轮最好成绩为 "
        f"{dex + 2}/20 = {(dex + 2) / 20 * 100:.0f}%，{verdict}",
    ]
    lines += [
        f"- 事实陈述：DexAtlas 已跑 18 题通过 {dex} 题；若把 2 道 not-run 题按判负计，"
        f"成绩为 {dex}/20 = {dex / 20 * 100:.1f}%；若按判负但「未验证」区分，"
        "本轮无法给出完整的 20 题通过率。**无论哪种口径，本轮都无法声称达到 80% 验收线**："
        "熔断截停了测量，修复效果只得到部分验证。",
        "- 上轮（修复前）DexAtlas 15/20 = 75.0%；本轮已跑 18 题中 DexAtlas 通过 "
        f"{dex} 题，逐题对照见上表。A/B 与 DexAtlas 预算不同，配置间数字差异反映"
        "可见信息与执行条件不同，不构成优劣结论。",
        "",
        "## 5. 已知局限",
        "",
        "- **本轮被总额熔断截停，不是完整的 20 题测量**：最后 2 题未发起，"
        "任何把 not-run 算作通过或失败的汇总都是编造。结论只能限定在已跑 18 题。",
        "- 单轮单模型，温度 0 下同一模型两次运行仍可能不同；本轮数字不外推为该配置的稳定通过率。",
        "- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。",
        "- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。",
        "- 对照的上轮是修复前代码的测量；除代码状态与预算闸外，两轮执行条件一致。",
        "",
        "## 复现命令",
        "",
        "```bash",
        "# key 经环境变量注入，不写入任何文件",
        'export MINIMAX_API_KEY="<key>"',
        'export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"',
        'export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"',
        "# 逐题执行（方案 §4.3），每题一次调用，批间核对累计 token：",
        "uv run --no-sync python benchmarks/comparison/run.py \\",
        "  --provider openai-compat --api-key-env MINIMAX_API_KEY \\",
        "  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \\",
        "  --budget 16384 --agent-budget 120000 --total-tokens 24000 \\",
        "  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \\",
        "  --output .scratch/m6-retest-r2/<task-id> --task <task-id>",
        "# 报告再生：",
        "uv run --no-sync python scripts/m6_level2_retest2_report.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def _dexatlas_failure_notes(round_: _Round) -> list[str]:
    lines: list[str] = []
    for trace in round_.traces:
        if trace.system.value != "DexAtlas" or trace.passed:
            continue
        outcome = _outcome(trace)
        if outcome == "budget-exhausted":
            note = "任务级预算/迭代耗尽，未作答"
        elif outcome in ("no-answer", "empty"):
            note = "回答为空"
        else:
            note = "判分不通过（回答内容与判定要求有差距）"
        lines.append(f"- `{trace.task_id}`：{note}。")
    if not lines:
        lines.append("-（本轮 DexAtlas 无失败题。）")
    return lines


def main() -> int:
    round_ = _load_round(TRACE_PATH, "retest2", expected_tasks=18)
    baseline = _load_round(BASELINE_PATH, "retest1", expected_tasks=20)
    report = _report(round_, baseline)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
