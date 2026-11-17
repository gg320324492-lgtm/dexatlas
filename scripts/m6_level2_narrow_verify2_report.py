#!/usr/bin/env python3
"""Regenerate the M6 level-2 narrow-verification round-2 report from traces.

    uv run --no-sync python scripts/m6_level2_narrow_verify2_report.py

Reads the committed trace file of the narrow-verification round-2 run
(``docs/benchmarks/m6-level2-narrow-verify2-traces.json`` — three
configurations x 6 tasks x 3 rounds) and writes
``docs/benchmarks/m6-level2-narrow-verify2.md``.

This run verifies the four-fix set that followed the first narrow
verification (``docs/benchmarks/m6-level2-narrow-verify2.md``): the
protocol-leak retry carries an explicit correction to the model, the
instructions spell out the backend-failure phrases a partial answer must
use, a field-name hit is sent to the constant pool (sk_/AKIA/AIza/ghp_),
and a method identity must be written as one contiguous string. The six
tasks cover every known failure surface (failure analysis §2; acceptance
plan §2.2).

Every figure is recomputed from the trace files; nothing is asserted from
memory. Regenerating the report must byte-reproduce the committed one. A
missing or incomplete trace file is a ``SystemExit`` that names the
problem, never a traceback: an unfinished run must not silently produce a
partial report.

The run was produced by ``benchmarks/comparison/run.py`` (see the report's
own reproduction section); the API key travelled in the
``MINIMAX_API_KEY`` environment variable and appears nowhere in a trace.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.comparison.metrics import compare  # noqa: E402
from benchmarks.comparison.model import TaskTrace  # noqa: E402

TRACE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-narrow-verify2-traces.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-narrow-verify2.md"

#: The six narrow-verification tasks, in acceptance-plan §2.2 order. Each
#: covers a named failure surface from the three-round retest analysis.
NARROW_TASK_IDS: tuple[str, ...] = (
    "partial.no-apktool-there-is-no-manifest",  # limitations reach the scorer
    "strings.api-key.demo",  # C2 union fires on one-word queries
    "overloads.method-identity.descriptor-distinguishes",  # C1 answer width
    "manifest.permission.count-obfuscated",  # C3 findings discipline
    "resources.app-name.demo",  # B: the 24,000 per-task gate
    "multidex.dex-file-count",  # B: the 24,000 per-task gate, near-line
)

#: Three rounds of the same six tasks: 6 x 3 x 3 = 54 traces.
ROUNDS = 3

#: The budget this run ran under: a 410,000 cumulative circuit break
#: (this round's authorisation) and the 24,000 per-task break.
ROUND_BREAK = 410_000
PER_TASK_BREAK = 24_000

#: The narrow-verification gate (acceptance plan §2.2): at least 4 of the
#: 6 tasks convert (DexAtlas, ≥12 of 18 across the three rounds), and the
#: five non-descriptor tasks — the ones the deterministic fixes target —
#: convert at least 3 of 5. Falling short of 4 tasks stops the investment.
CONVERT_LINE = 4
DETERMINISTIC_LINE = 3
DETERMINISTIC_IDS = frozenset(NARROW_TASK_IDS) - {
    "overloads.method-identity.descriptor-distinguishes",
}

#: The system whose verdict this run is about.
AGENT = "DexAtlas"

CODE_STATE = "claude/m6-level2-verify 9b25835"


@dataclass(frozen=True, slots=True)
class _Run:
    """One loaded trace file: the traces and their recomputed metrics."""

    name: str
    traces: tuple[TaskTrace, ...]
    metrics: dict[str, dict[str, Any]]
    #: the round each trace belongs to, parallel to ``traces``; read from the
    #: committed file's ``_round`` field (one run.py invocation per task per
    #: round), falling back to the positional round of a uniform run.
    rounds: tuple[int, ...] = ()

    def tokens(self) -> int:
        return sum(
            trace.result.prompt_tokens + trace.result.completion_tokens for trace in self.traces
        )

    def by_task(self) -> dict[str, list[TaskTrace]]:
        grouped: dict[str, list[TaskTrace]] = {task_id: [] for task_id in NARROW_TASK_IDS}
        for trace in self.traces:
            grouped[trace.task_id].append(trace)
        return grouped

    def by_round_and_task(self) -> dict[int, dict[str, list[TaskTrace]]]:
        """Traces grouped by the round recorded beside each trace."""
        rounds: dict[int, dict[str, list[TaskTrace]]] = {
            r: {t: [] for t in NARROW_TASK_IDS} for r in range(ROUNDS)
        }
        for round_index, trace in zip(self.rounds, self.traces, strict=True):
            rounds[round_index][trace.task_id].append(trace)
        return rounds


def _load_run(path: Path) -> _Run:
    """Load the trace file or refuse to write a report from a partial run."""
    if not path.exists():
        raise SystemExit(
            f"trace file is missing: {path}\n"
            f"the run is not complete; refusing to write a partial report"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["traces"]
    expected = len(NARROW_TASK_IDS) * ROUNDS * 3
    if len(items) != expected:
        raise SystemExit(
            f"expected {expected} traces "
            f"(3 configurations x {len(NARROW_TASK_IDS)} tasks x {ROUNDS} rounds), "
            f"found {len(items)}; the run is not complete, refusing to write a partial report"
        )
    traces = tuple(TaskTrace.from_dict(item) for item in items)
    counts = Counter((trace.system.value, trace.task_id) for trace in traces)
    bad = {key for key, count in counts.items() if count != ROUNDS}
    if bad:
        raise SystemExit(
            f"these (system, task) pairs do not have exactly {ROUNDS} traces: "
            + ", ".join(f"{system}/{task}" for system, task in sorted(bad))
        )
    missing = {
        task_id for task_id in NARROW_TASK_IDS if task_id not in {trace.task_id for trace in traces}
    }
    if missing:
        raise SystemExit(f"trace file is missing tasks: {', '.join(sorted(missing))}")
    per_round = len(items) // ROUNDS  # traces per round in a uniform file
    # ``_round`` is 1-based in the committed file; the grouping below is
    # 0-based, and the positional fallback keeps that convention.
    rounds = tuple(
        int(item.get("_round", index // per_round + 1)) - 1 for index, item in enumerate(items)
    )
    return _Run(name=path.name, traces=traces, metrics=compare(traces), rounds=rounds)


def _outcome(trace: TaskTrace) -> str:
    """One word for how a scored trace ended (same vocabulary as retest 3).

    A ``budget-exhausted`` outcome travels in the trace itself now, so it
    is read from there; the error-text guesses are only for old traces.
    """
    if trace.result.outcome == "budget-exhausted":
        return "budget-exhausted"
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


def _verdict_counts(run: _Run, system: str) -> Counter[str]:
    return Counter(_outcome(trace) for trace in run.traces if trace.system.value == system)


def _metric_rows(run: _Run) -> list[str]:
    rows = []
    for name in (
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
        for system in ("A", "B", AGENT):
            value = run.metrics[system].get(name)
            rendered = (
                "n/a"
                if value is None
                else (
                    f"{value * 100:.1f}%"
                    if isinstance(value, float) and value <= 1
                    else (f"{value:,.1f}" if isinstance(value, float) else f"{value:,}")
                )
            )
            cells.append(rendered)
        rows.append(f"| `{name}` | {cells[0]} | {cells[1]} | {cells[2]} |")
    return rows


def _task_tables(run: _Run) -> str:
    lines = [
        "| task | 失败面 | r1 判定 | r2 判定 | r3 判定 | 3 轮合计 |",
        "|---|---|---|---|---|---|",
    ]
    surfaces = {
        "partial.no-apktool-there-is-no-manifest": "判分通道（limitations）",
        "strings.api-key.demo": "C2 触发条件（单词并集）",
        "overloads.method-identity.descriptor-distinguishes": "C1 回答宽度",
        "manifest.permission.count-obfuscated": "C3 findings 纪律",
        "resources.app-name.demo": "B 单题预算",
        "multidex.dex-file-count": "B 单题预算（近闸值）",
    }
    by_round = run.by_round_and_task()
    for task_id in NARROW_TASK_IDS:
        cells = []
        converted = 0
        for round_index in range(ROUNDS):
            verdicts = [
                _outcome(trace)
                for trace in by_round[round_index][task_id]
                if trace.system.value == AGENT
            ]
            passed = sum(1 for verdict in verdicts if verdict == "correct")
            converted += passed
            cells.append(f"{passed}/1（{'、'.join(verdicts)}）" if verdicts else "not-run")
        lines.append(
            f"| `{task_id}` | {surfaces[task_id]} | {cells[0]} | {cells[1]} | {cells[2]} "
            f"| **{converted}/3** |"
        )
    return "\n".join(lines)


def _agent_conversion(run: _Run) -> tuple[list[str], list[str]]:
    """Per-task conversion counts and the deterministic-fix subset."""
    converted: list[str] = []
    deterministic: list[str] = []
    for task_id, traces in run.by_task().items():
        passed = sum(1 for trace in traces if trace.system.value == AGENT and trace.passed)
        if passed >= 2:  # 转通过: 3 轮中 ≥2 轮判过
            converted.append(task_id)
            if task_id in DETERMINISTIC_IDS:
                deterministic.append(task_id)
    return converted, deterministic


def _render(run: _Run) -> str:
    total_tokens = run.tokens()
    agent_counts = _verdict_counts(run, AGENT)
    a_counts = _verdict_counts(run, "A")
    b_counts = _verdict_counts(run, "B")
    converted, deterministic = _agent_conversion(run)
    budget_hits = sorted(
        {
            trace.task_id
            for trace in run.traces
            if _outcome(trace) == "budget-exhausted" and trace.system.value == AGENT
        }
    )
    protocol_leaks = [
        trace
        for trace in run.traces
        if trace.system.value == AGENT
        and trace.result.failed
        and "protocol fragment" in trace.result.error
    ]
    gate_passed = len(converted) >= CONVERT_LINE and len(deterministic) >= DETERMINISTIC_LINE
    gate_text = (
        f"**达到窄验证通过判据**（转通过 {len(converted)}/6 ≥ {CONVERT_LINE}，"
        f"确定性修复相关题 {len(deterministic)}/5 ≥ {DETERMINISTIC_LINE}）——"
        "按验收方案 §3.1，可申请完整三轮复测（B1 关闭测量）。"
        if gate_passed
        else f"**未达到窄验证通过判据**（转通过 {len(converted)}/6，门槛 ≥{CONVERT_LINE}；"
        f"确定性修复相关题 {len(deterministic)}/5，门槛 ≥{DETERMINISTIC_LINE}）。"
        "若转通过 ≤2/6，按验收方案停止投入，转方案 3（现状披露）；"
        "否则按失败模式再分析后决定。"
    )

    parts = [
        "# M6 层级 2 —— 修复后窄验证二轮（6 题 × 3 轮）",
        "",
        f"**状态：本 run 验证首轮窄验证（`m6-level2-narrow-verify-incomplete.md`）之后的四项修复"
        f"（协议泄漏纠偏重试、partial 后端缺失措辞对齐、api-key 常量池检索引导、"
        f"descriptor 连写模板）。代码状态 `{CODE_STATE}`。"
        f"本文所有数字由 `scripts/m6_level2_narrow_verify2_report.py` 从"
        f" [m6-level2-narrow-verify2-traces.json](m6-level2-narrow-verify2-traces.json) "
        f"重算生成，未手改任何数字；trace 缺失或不完整时本脚本拒绝生成报告。**",
        "",
        "本文回答验收方案（§2.2）的两个问题：",
        "",
        "1. 六道覆盖已知失败面的题，DexAtlas 三轮合计是否 ≥4 题转通过（≥12/18）；",
        "2. 确定性修复直接相关的五题（除 descriptor 外）是否 ≥3 题转通过。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 题集 | 6 题（验收方案 §2.2，覆盖全部已知失败面） |",
        "| 轮次 | 6 题 × 3 轮 × 3 配置 = 54 条 trace |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与三轮复测一致） |",
        "| 每任务 token 预算 | DexAtlas 24,000（单题闸） |",
        "| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |",
        "| 总额熔断 | 累计 410,000 tokens（逐题批间核对累计 usage） |",
        f"| 代码状态 | `{CODE_STATE}`（含四项修复：泄漏纠偏重试 / partial 措辞 / "
        f"api-key 常量检索 / descriptor 连写） |",
        "| 采样 | temperature 0（provider 默认） |",
        "",
        "## 八指标（54 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）",
        "",
        "| metric | A | B | DexAtlas |",
        "|---|---:|---:|---:|",
        *_metric_rows(run),
        "",
        "## 逐题结果（DexAtlas；每轮一格：通过数（判定））",
        "",
        _task_tables(run),
        "",
        "## 判定分布（3 轮合计，每配置 18 条）",
        "",
        "| 配置 | correct | wrong | empty | no-answer | budget-exhausted | errored |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| A | {a_counts.get('correct', 0)} | {a_counts.get('wrong', 0)} "
        f"| {a_counts.get('empty', 0)} | {a_counts.get('no-answer', 0)} "
        f"| {a_counts.get('budget-exhausted', 0)} | {a_counts.get('errored', 0)} |",
        f"| B | {b_counts.get('correct', 0)} | {b_counts.get('wrong', 0)} "
        f"| {b_counts.get('empty', 0)} | {b_counts.get('no-answer', 0)} "
        f"| {b_counts.get('budget-exhausted', 0)} | {b_counts.get('errored', 0)} |",
        f"| DexAtlas | {agent_counts.get('correct', 0)} | {agent_counts.get('wrong', 0)} "
        f"| {agent_counts.get('empty', 0)} | {agent_counts.get('no-answer', 0)} "
        f"| {agent_counts.get('budget-exhausted', 0)} | {agent_counts.get('errored', 0)} |",
        "",
        "## 窄验证判定（验收方案 §2.2 的闸）",
        "",
        f"- 转通过题（DexAtlas，3 轮中 ≥2 轮判过）：**{len(converted)}/6**"
        + (f"（{'、'.join(f'`{t}`' for t in converted)}）" if converted else ""),
        f"- 确定性修复相关题转通过（partial、api-key、count、两道预算题）："
        f"**{len(deterministic)}/5**"
        + (f"（{'、'.join(f'`{t}`' for t in deterministic)}）" if deterministic else ""),
        f"- 判定：{gate_text}",
        "",
        "## 修复验证关注点",
        "",
        f"- 单题 24,000 闸触发（DexAtlas）：**{len(budget_hits)} 题**"
        + (f"（{'、'.join(f'`{t}`' for t in budget_hits)}）" if budget_hits else "")
        + "，均如实判 budget-exhausted 计失败。",
        f"- XML 工具调用协议泄漏（retryable 处理）：**{len(protocol_leaks)} 条**"
        + ("——泄漏文本未进入最终答案。" if protocol_leaks else "。"),
        "- 判分失败与空答未重跑；errored 的基础设施性失败按 service-regression-set §6 处置。",
        "",
        "## 成本与停止条件（照实陈述）",
        "",
        f"- 本 run 实测 token 合计 **{total_tokens:,}**（API `usage` 字段逐 trace 加总），"
        f"授权上限 {ROUND_BREAK:,}（"
        + ("未触发" if total_tokens <= ROUND_BREAK else "已触发熔断，超出部分如实记录")
        + "）。",
        "- 逐题分批执行，批间核对累计 usage；单题 24,000 闸由 `--total-tokens 24000` 落实。",
        "",
        "## 已知局限",
        "",
        "- **窄题集**：6 题覆盖已知失败面，但通过率不能外推到 20 题完整服务回归集；",
        "  进入完整三轮（B1 关闭测量）需另按验收方案 §3 的触发条件申请。",
        "- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。",
        "- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同。",
        "- **first-party 小样本**：样本全部为 first-party 小型 APK（examples/），"
        "不外推到真实规模或加固样本。",
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
        "# 逐题执行（验收方案 §2.2），每题每轮一次调用，批间核对累计 token：",
        "uv run --no-sync python benchmarks/comparison/run.py \\",
        "  --provider openai-compat --api-key-env MINIMAX_API_KEY \\",
        "  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \\",
        "  --budget 16384 --agent-budget 120000 --total-tokens 24000 \\",
        "  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \\",
        "  --output .scratch/m6-narrow-verify2/<task-id> --task <task-id>",
        "# 报告再生：",
        "uv run --no-sync python scripts/m6_level2_narrow_verify2_report.py",
        "```",
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    run = _load_run(TRACE_PATH)
    report = _render(run)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(
        f"wrote {REPORT_PATH.relative_to(REPOSITORY_ROOT)} "
        f"({len(run.traces)} traces, {run.tokens():,} tokens)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
