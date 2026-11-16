#!/usr/bin/env python3
"""Regenerate the M6 level-2 single-round verification report from traces.

    uv run --no-sync python scripts/m6_level2_verify_report.py

Reads the committed trace file of the single-round verification run
(``docs/benchmarks/m6-level2-verify-traces.json`` — three configurations x
20 frozen tasks) and writes ``docs/benchmarks/m6-level2-verify.md``.

This run verifies the two code-level fixes that came out of the three-round
retest failure analysis (``docs/benchmarks/m6-level2-retest3-failure-analysis.md``):

- **A** (commit ``1a7add6``): an empty assistant message from the model
  endpoint was recorded as a task failure; the fix makes an empty
  completion an execution-layer outcome instead of a wrong answer.
- **C2** (commit ``192382f``): the string-search decoy shadowed the
  constant-pool enumeration fallback; the fix unions the constant pool
  back in when a multi-word query hits ``string``.

The run answers two questions, and the report states both:

1. did the three tasks DexAtlas failed in retest round 1
   (``overloads.method-identity.descriptor-distinguishes``,
   ``strings.api-key.demo``,
   ``partial.no-apktool-there-is-no-manifest``) pass this round;
2. did the class-A empty response recur.

Every figure is recomputed from the trace files; nothing is asserted from
memory. Regenerating the report must byte-reproduce the committed one. A
missing or incomplete trace file is a ``SystemExit`` that names the
problem, never a traceback: an unfinished run must not silently produce a
partial report.

The run was produced by ``benchmarks/comparison/run.py --provider
openai-compat --api-key-env MINIMAX_API_KEY --task <frozen id>``, one task
per invocation, against MiniMax-M3.1-Flash at ``main`` ``fbca3d5``. The
budget followed the three-round retest plan: per-task ``--total-tokens
24000`` and a 400,000 per-round cumulative circuit break. The API key
travelled through the ``MINIMAX_API_KEY`` environment variable and is
recorded nowhere.
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

TRACE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-verify-traces.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-verify.md"

#: The retest-3 round-1 traces, for the per-task comparison this run exists
#: to make: did the fixes move the tasks that failed in round 1?
RETEST3_R1_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest3-traces-r1.json"

#: The frozen 20 ids, in the document's order, so the per-task table reads
#: in the same order as the service-regression document.
FROZEN_IDS = list(SERVICE_REGRESSION_PREFIXES)

#: The budget this single round ran under: a 400,000 cumulative circuit
#: break and a 24,000 per-task break (docs/benchmarks/m6-level2-retest-plan.md).
ROUND_BREAK = 400_000
PER_TASK_BREAK = 24_000

#: The per-round acceptance line the three-round retest was held to; this
#: single round is compared against it as a reference, not as a verdict.
PER_ROUND_LINE = 16  # ≥16/20 = ≥80%

#: The three tasks the failure analysis named as fix targets for this run
#: (failure analysis §2.1, §2.2, §2.3; commits 1a7add6 and 192382f).
FIX_TARGET_IDS = (
    "overloads.method-identity.descriptor-distinguishes",
    "strings.api-key.demo",
    "partial.no-apktool-there-is-no-manifest",
)

SYSTEMS = ("A", "B", "DexAtlas")


@dataclass(frozen=True, slots=True)
class _Run:
    """One run's traces and derived numbers."""

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

    def by_task(self) -> dict[str, dict[str, TaskTrace]]:
        table: dict[str, dict[str, TaskTrace]] = {}
        for trace in self.traces:
            table.setdefault(trace.task_id, {})[trace.system.value] = trace
        return table

    def ids(self) -> set[str]:
        return {trace.task_id for trace in self.traces}


def _outcome(trace: TaskTrace) -> str:
    """One word for how a scored trace ended (same vocabulary as retest 3)."""
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


def _load_run(path: Path, name: str, expected_tasks: int) -> _Run:
    if not path.exists():
        raise SystemExit(
            f"{name} trace file is missing: {path}\n"
            f"the run is not complete; refusing to write a partial report"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != expected_tasks * 3:
        raise SystemExit(
            f"expected {expected_tasks * 3} {name} traces "
            f"(3 configurations x {expected_tasks} tasks), found {len(items)}; "
            f"the run is not complete, refusing to write a partial report"
        )
    traces = tuple(TaskTrace.from_dict(item) for item in items)
    counts = Counter(trace.task_id for trace in traces)
    if any(count != 3 for count in counts.values()):
        raise SystemExit(f"{name} does not cover each task exactly three times")
    missing = [task_id for task_id in FROZEN_IDS if task_id not in {t.task_id for t in traces}]
    if missing:
        raise SystemExit(f"{name} is missing frozen tasks: {', '.join(missing)}")
    return _Run(name=name, traces=traces, metrics=compare(traces))


def _load_retest3_r1() -> _Run:
    """Load retest-3 round 1 for the per-task comparison (60 traces)."""
    if not RETEST3_R1_PATH.exists():
        raise SystemExit(
            f"retest round-1 trace file is missing: {RETEST3_R1_PATH}; "
            f"the comparison this report exists to make needs it"
        )
    document = json.loads(RETEST3_R1_PATH.read_text(encoding="utf-8"))
    traces = tuple(TaskTrace.from_dict(item) for item in document["traces"])
    return _Run(name="retest3-r1", traces=traces, metrics=compare(traces))


def _pct(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _metric_table(metrics: dict[str, dict[str, float | int | None]]) -> list[str]:
    lines = [
        "## 八指标（本轮 60 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）",
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
                cells.append(f"{value * 100:.1f}%")
        lines.append(f"| `{metric}` | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _task_table(run: _Run, baseline: _Run) -> list[str]:
    """Per-task verdicts: this round beside retest round 1, one row per task."""
    by_task = run.by_task()
    by_task_base = baseline.by_task()
    task_by_id = {task.id: task for task in ALL_TASKS}
    lines = [
        "## 逐题结果（冻结集顺序；每题两格：本轮判定 / r1 判定）",
        "",
        "correct = 判分通过；wrong = 判分不通过；empty = 空答；errored = 运行"
        "错误；budget-exhausted = 任务级预算耗尽。**空答与预算耗尽均计为失败**。"
        "20 题完整分母，无 not-run。",
        "",
    ]
    for task_id in FROZEN_IDS:
        task = task_by_id[task_id]
        now_cells = []
        base_cells = []
        for system in SYSTEMS:
            trace = by_task.get(task_id, {}).get(system)
            now_cells.append(f"{system}: {_outcome(trace)}" if trace else f"{system}: not-run")
            base = by_task_base.get(task_id, {}).get(system)
            base_cells.append(f"{system}: {_outcome(base)}" if base else f"{system}: not-run")
        marker = " **← r1 失败题（修复目标）**" if task_id in FIX_TARGET_IDS else ""
        lines.append(
            f"- `{task_id}`（{task.sample.value}，{task.category.value}）{marker}："
            + "；".join(now_cells)
            + " ｜ r1："
            + "；".join(base_cells)
        )
    lines.append("")
    return lines


def _fix_questions(run: _Run, baseline: _Run) -> list[str]:
    """The two questions this verification run exists to answer."""
    by_task = run.by_task()
    by_task_base = baseline.by_task()
    lines = [
        "## 修复验证（本轮要回答的两个问题）",
        "",
        "### 1. r1 失败的三道题本轮是否通过（DexAtlas）",
        "",
        "| task | r1 判定 | r1 结果摘要 | 本轮判定 | 本轮结果摘要 |",
        "|---|---|---|---|---|",
    ]
    passed_count = 0
    for task_id in FIX_TARGET_IDS:
        base = by_task_base.get(task_id, {}).get("DexAtlas")
        now = by_task.get(task_id, {}).get("DexAtlas")
        base_verdict = _outcome(base) if base else "not-run"
        now_verdict = _outcome(now) if now else "not-run"
        base_note = (
            ""
            if base is None
            else (
                "passed" if base.passed else (base.result.error or "answer did not meet the rubric")
            )
        )
        now_note = (
            ""
            if now is None
            else (
                "passed" if now.passed else (now.result.error or "answer did not meet the rubric")
            )
        )
        if now is not None and now.passed:
            passed_count += 1
        lines.append(f"| `{task_id}` | {base_verdict} | {base_note} | {now_verdict} | {now_note} |")
    lines += [
        "",
        f"三道 r1 失败题本轮通过 **{passed_count}/3**。",
        "",
        "### 2. A 类空响应（模型端点返回空 assistant 消息）是否还出现",
        "",
    ]
    # The A-class signature is an execution-layer empty response on a task
    # whose right answer is a statement: the task failed (not scored-wrong),
    # carried no error text, and the scorer saw no findings. The two
    # unanswerable tasks are excluded: an empty answer is their *correct*
    # answer (expects_absence), so their failed-and-empty shape is the
    # harness scoring an absence, not the endpoint's empty message.
    empty_traces = [
        trace
        for trace in run.traces
        if trace.system.value == "DexAtlas"
        and not trace.expects_absence
        and trace.result.failed
        and not trace.result.error
        and trace.answer_is_empty
    ]
    if empty_traces:
        lines.append(
            f"本轮 DexAtlas 出现 **{len(empty_traces)}** 条 A 类空响应 trace"
            "（答案型题 failed 且无 error 且判分无 findings，即修复前的执行层"
            "空响应形态）：" + "、".join(f"`{trace.task_id}`" for trace in empty_traces) + "。"
        )
    else:
        lines.append(
            "本轮 DexAtlas **没有出现 A 类空响应**（答案型题无「failed 且无 "
            "error 且判分无 findings」的 trace）。"
        )
    lines += [
        "",
        "判定口径：A 类空响应 = 该题正确答案不是「空」（`expects_absence` 为"
        "假）且 `result.failed` 为真且 `result.error` 为空且 `answer_is_empty` "
        "为真（判分无 findings）——即修复前被记为解题失败的执行层空响应形态。"
        "四项均由 trace 字段直接读出，不经人工判断。`expects_absence` 的题"
        "（unanswerable 两题）空答即正确答案，其 failed+empty 形态是判分器对"
        "「答无所指」的记法，不是端点空响应，故排除；r1 同题同形态，非本轮"
        "新增。注意 MiniMax 端点对全部成功请求都回报 `completion_tokens=0`，"
        "该字段不区分空响应，不作判定依据。",
        "",
    ]
    return lines


def _verdict(run: _Run) -> list[str]:
    passes = run.passes
    dex = passes.get("DexAtlas", 0)
    lines = [
        "## 结果判定（对照参考线，非验收）",
        "",
        "本 run 是单轮验证，不是 B1 的验收测量；验收线（每轮 ≥16/20 且三轮"
        "合计 ≥54/60）属于三轮完整复测。这里只把本轮数字放在同一条参考线旁"
        "读：DexAtlas 本轮 "
        f"{dex}/20 = {dex / 20 * 100:.1f}%（参考线 ≥{PER_ROUND_LINE}/20"
        + ("，本轮在线上" if dex >= PER_ROUND_LINE else "，本轮未到线")
        + "）。",
        "",
        "| 配置 | 本轮正确 | 正确率 | 本轮 token |",
        "|---|---:|---:|---:|",
    ]
    for system in SYSTEMS:
        count = passes.get(system, 0)
        lines.append(
            f"| {system} | {count}/20 | {count / 20 * 100:.1f}% | {run.tokens.get(system, 0)} |"
        )
    lines += [
        "",
        f"本轮全部 trace 合计 token：**{run.total_tokens}**（API `usage` 字段逐 trace 加总）。",
        "",
        "A/B 与 DexAtlas 的预算不同（每请求 max_tokens 16384 对 120000、"
        "任务预算仅 DexAtlas 24,000），配置间数字差异反映可见信息与执行条件"
        "不同，不构成优劣结论。",
        "",
    ]
    return lines


def _cost_notes(run: _Run) -> list[str]:
    """Cost and stop-condition notes, stated from the traces, as retest 3 does."""
    if run.total_tokens <= ROUND_BREAK:
        budget_line = (
            f"- 本轮实测 token 合计 **{run.total_tokens}**，在单轮授权 "
            f"{ROUND_BREAK:,} 之内（余 {ROUND_BREAK - run.total_tokens}）。"
        )
    else:
        budget_line = (
            f"- 本轮实测 token 合计 **{run.total_tokens}**，**超出**单轮授权 "
            f"{ROUND_BREAK:,}（超 {run.total_tokens - ROUND_BREAK}）；熔断未"
            "挡住的部分如实记录。"
        )
    lines = [
        "## 成本与停止条件（照实陈述）",
        "",
        budget_line,
        f"- 单题 {PER_TASK_BREAK:,} 闸共触发 "
        + str(
            sum(
                1
                for trace in run.traces
                if trace.system.value == "DexAtlas"
                and ("budget" in trace.result.error or "ran out" in trace.result.error)
            )
        )
        + " 题（DexAtlas），均如实判 budget-exhausted 计失败；判分失败与空答"
        "未重跑。",
        "",
    ]
    return lines


def _report(run: _Run, baseline: _Run) -> str:
    lines = [
        "# M6 层级 2 —— 服务回归集单轮验证复测（A+C2 修复验证）",
        "",
        "**状态：这是 M6 层级 2 服务回归集的单轮验证复测，用于验证两项代码级"
        "修复的效果：A 类（`1a7add6`，模型端点返回空 assistant 消息被记为解题"
        "失败）与 C2（`192382f`，字符串检索诱饵遮蔽常量池枚举兜底），修复依据"
        "是 [m6-level2-retest3-failure-analysis.md](m6-level2-retest3-failure-analysis.md)"
        " 的失败模式分析。本文所有数字由 `scripts/m6_level2_verify_report.py` 从 "
        "[m6-level2-verify-traces.json](m6-level2-verify-traces.json) 与 "
        "[m6-level2-retest3-traces-r1.json](m6-level2-retest3-traces-r1.json) "
        "重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。trace 缺失"
        "或不完整时本脚本拒绝生成报告。**",
        "",
        "本文回答两个问题：r1 失败的三道题（`overloads.method-identity."
        "descriptor-distinguishes`、`strings.api-key.demo`、`partial."
        "no-apktool-there-is-no-manifest`）本轮是否通过；A 类空响应是否还出现。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 运行日期 | 2026-11-16 |",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、三轮复测同一题集、同一顺序） |",
        "| 轮次 | 冻结 20 题 × 1 轮 × 3 配置 = 60 条 trace |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与三轮复测一致） |",
        f"| 每任务 token 预算 | DexAtlas {PER_TASK_BREAK:,}（方案 §2.1 单题闸） |",
        "| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |",
        f"| 总额熔断 | 单轮累计 {ROUND_BREAK:,} tokens（逐题批间核对累计 usage） |",
        "| 代码状态 | `main` `fbca3d5`（含 A 类修复 `1a7add6` 与 C2 修复 `192382f`） |",
        "| 采样 | temperature 0（provider 默认） |",
        "",
        "本轮与三轮复测（`main` `c4922dc`）的差异只有两处代码修复（`1a7add6`、"
        "`192382f`）；模型、题集、配置、预算全部一致。单轮结果受模型方差影响，"
        "不外推为稳定通过率。",
        "",
    ]
    lines += _metric_table(run.metrics)
    lines += _task_table(run, baseline)
    lines += _fix_questions(run, baseline)
    lines += _verdict(run)
    lines += _cost_notes(run)
    lines += [
        "## 已知局限",
        "",
        "- **单轮**：单轮数字受模型方差影响大（三轮复测同题集同配置逐轮在 "
        "15–17/20 间波动），本轮数字不外推为稳定通过率，也不据此关闭或重开"
        "任何验收。",
        "- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。",
        "- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同。",
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
        "# 逐题执行（方案 §4.3），每题一次调用，批间核对累计 token：",
        "uv run --no-sync python benchmarks/comparison/run.py \\",
        "  --provider openai-compat --api-key-env MINIMAX_API_KEY \\",
        "  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \\",
        "  --budget 16384 --agent-budget 120000 --total-tokens 24000 \\",
        "  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \\",
        "  --output .scratch/m6-retest-verify/<task-id> --task <task-id>",
        "# 报告再生：",
        "uv run --no-sync python scripts/m6_level2_verify_report.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    run = _load_run(TRACE_PATH, "verification", expected_tasks=20)
    baseline = _load_retest3_r1()
    report = _report(run, baseline)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
