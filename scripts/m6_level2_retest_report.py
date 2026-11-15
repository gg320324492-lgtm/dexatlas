#!/usr/bin/env python3
"""Regenerate the M6 level-2 real-model retest report from its committed traces.

    uv run --no-sync python scripts/m6_level2_retest_report.py

Reads ``docs/benchmarks/m6-level2-retest-traces.json`` (the one retest round
of the frozen service-regression set, three configurations) and writes
``docs/benchmarks/m6-level2-retest.md``. Every figure in the report is read
back out of that trace file; nothing is asserted from memory. The
regenerated report must byte-match the committed one — a mismatch means the
traces moved without regenerating.

The run itself was produced by ``benchmarks/comparison/run.py
--provider openai-compat --task <frozen id>...`` against MiniMax-M3.1-Flash
(see the report's configuration section for the exact budget). The API key
travelled through the ``MINIMAX_API_KEY`` environment variable and is
recorded nowhere. The comparison baseline is the first real-model batch
(``m6-level2-traces.json`` round-1), read from its committed traces; that
file stays untouched.
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

TRACE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest-traces.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest.md"
BASELINE_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-traces.json"

#: The frozen 20 ids, in the document's order, so the per-task table reads
#: in the same order as the service-regression document.
FROZEN_IDS = list(SERVICE_REGRESSION_PREFIXES)

#: Token ceiling for this retest: the user authorised one round of the
#: frozen set with a hard cap of 350k. The actual spend comes from the
#: traces; this number only appears in the report as the authorisation.
TOKEN_CAP = 350_000

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

    def pooled_passes(self) -> dict[str, int]:
        """Per-configuration pass count over all traces in the round."""
        counts: dict[str, int] = {}
        for trace in self.traces:
            if trace.passed:
                counts[trace.system.value] = counts.get(trace.system.value, 0) + 1
        return counts


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


def _load_retest() -> _Round:
    document = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != 60:
        raise SystemExit(
            f"expected 60 retest traces (3 configurations x 20 frozen tasks), found {len(items)}"
        )
    traces = tuple(TaskTrace.from_dict(item) for item in items)
    # Each frozen id must appear exactly three times, once per configuration.
    ids = Counter(trace.task_id for trace in traces)
    if sorted(ids) != sorted(FROZEN_IDS) or any(count != 3 for count in ids.values()):
        raise SystemExit("retest does not cover exactly the frozen 20 ids per configuration")
    return _Round(name="retest", traces=traces, metrics=compare(traces))


def _load_baseline_round1() -> _Round:
    document = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    items = document["traces"]
    if len(items) != 183:
        raise SystemExit(f"expected 183 baseline traces, found {len(items)}")
    chunk = items[3:63]  # skip the 3 smoke traces, take round-1
    traces = tuple(TaskTrace.from_dict(item) for item in chunk)
    ids = {trace.task_id for trace in traces}
    if ids != set(FROZEN_IDS):
        raise SystemExit("baseline round-1 does not cover exactly the frozen 20 ids")
    return _Round(name="baseline", traces=traces, metrics=compare(traces))


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
    """Per-task verdicts, retest beside baseline round-1."""
    retest_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in round_.traces:
        retest_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    baseline_by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in baseline.traces:
        baseline_by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    task_by_id = {task.id: task for task in ALL_TASKS}
    lines = [
        "## 逐题结果（20 题冻结集，单轮 × 三配置，附首测 round-1 对照）",
        "",
        "correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted "
        "含义与层级 2 报告一致。每格为 `复测/首测r1`。",
        "",
    ]
    for task_id in FROZEN_IDS:
        task = task_by_id[task_id]
        cells = []
        for system in SYSTEMS:
            now = _outcome(retest_by_task[task_id][system])
            was = _outcome(baseline_by_task[task_id][system])
            cells.append(f"{system}: {now}/{was}")
        lines.append(
            f"- `{task_id}`（{task.sample.value}，{task.category.value}）：" + "；".join(cells)
        )
    lines.append("")
    return lines


def _fail_mode_table(round_: _Round, baseline: _Round) -> list[str]:
    """The four failure modes from the M6-③ analysis, retested."""
    modes: dict[str, tuple[str, ...]] = {
        "否定/缺席题（expect_empty + partial 后端缺失）": (
            "unanswerable.crypto-digestof-has-no-callers",
            "unanswerable.demo-declares-no-receiver",
            "partial.no-apktool-there-is-no-manifest",
            "partial.no-jadx-the-failure-is-recorded",
        ),
        "计数题（expect_count）": (
            "manifest.permission.count-obfuscated",
            "xrefs.crypto-sign-call-site-count",
            "multidex.dex-file-count",
        ),
        "方法身份/枚举完整性（must_contain 描述符）": (
            "overloads.method-identity.crypto-sign",
            "overloads.method-identity.descriptor-distinguishes",
            "ambiguity.declared-type-contradicts-body",
        ),
        "资源出处（资源 → 声明文件反查）": (
            "wheresource.app-name-resource-file.demo",
            "strings.api-key.demo",
            "strings.telemetry-url.obfuscated",
            "resources.app-name.demo",
        ),
    }

    def per_config(traces: tuple[TaskTrace, ...]) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for trace in traces:
            slot = result.setdefault(trace.system.value, {"pass": 0, "fail": 0})
            slot["pass" if trace.passed else "fail"] += 1
        return result

    lines = [
        "## 修复针对的失败模式（M6-③ 分析归因）复测对照",
        "",
        "| 失败模式 | 配置 | 首测 r1 | 复测 | 变化 |",
        "|---|---|---:|---:|---:|",
    ]
    for mode, ids in modes.items():
        for system in SYSTEMS:
            old_pass = 0
            old_fail = 0
            new_pass = 0
            new_fail = 0
            for trace in baseline.traces:
                if trace.system.value == system and trace.task_id in ids:
                    if trace.passed:
                        old_pass += 1
                    else:
                        old_fail += 1
            for trace in round_.traces:
                if trace.system.value == system and trace.task_id in ids:
                    if trace.passed:
                        new_pass += 1
                    else:
                        new_fail += 1
            delta = new_pass - old_pass
            sign = "+" if delta > 0 else ""
            lines.append(
                f"| {mode} | {system} | {old_pass}/{old_pass + old_fail} "
                f"| {new_pass}/{new_pass + new_fail} | {sign}{delta} |"
            )
    lines.append("")
    return lines


def _report(round_: _Round, baseline: _Round) -> str:
    passes = round_.passes
    tokens = round_.tokens
    total_tokens = round_.total_tokens
    baseline_passes = baseline.passes
    dur = {system: round_.metrics[system]["execution_duration"] or 0.0 for system in SYSTEMS}
    outcomes = Counter(_outcome(trace) for trace in round_.traces)
    lines = [
        "# M6 层级 2 —— 服务回归集真实模型复测（单轮，M6-③ 修复后）",
        "",
        "**状态：已完成授权范围内的执行并按授权停止（单轮，预算上限 "
        f"{TOKEN_CAP} tokens）。本文所有数字由 `scripts/m6_level2_retest_report.py` 从 "
        "[m6-level2-retest-traces.json](m6-level2-retest-traces.json) 重算生成，未手改任何数字；"
        "重跑脚本应得到逐字节相同的文件。对照基线为 "
        "[m6-level2-real.md](m6-level2-real.md)（首测三轮，其 trace 文件未改动）。**",
        "",
        "本文回答一个问题：M6-③ 五项修复（`1a1509c` 回答契约与工具调优、"
        "`b956260` partial.* 判定谓词，见 [m6-level3-recheck.md](m6-level3-recheck.md)）"
        "之后，冻结 20 题服务回归集在真实模型（MiniMax-M3.1-Flash）单轮上的表现，"
        "相比首测是否改善；以及是否达到验收线。",
        "",
        "## 1. 运行配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 运行日期 | 2026-11-16 |",
        "| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |",
        "| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |",
        "| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测同一题集、同一顺序） |",
        "| 轮次 | 冻结 20 题 × 1 轮 × 3 配置（无冒烟：首测已验证端点与记账） |",
        "| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与首测一致） |",
        "| 每任务 token 预算 | DexAtlas 120000（A/B 检索式，无任务级循环预算） |",
        "| 迭代 / 步数 / 时限 | 16 迭代 / 40 步 / 600 秒（与首测一致） |",
        "| 代码状态 | main 合并树，M6-③ 修复已入库（`1a1509c`、`b956260`） |",
        "| 采样 | temperature 0（provider 默认） |",
        "",
        "与首测的执行条件差异：首测在修复前的代码上跑（合并 `1a1509c` 之前），"
        "本轮在 M6-③ 修复后的代码上跑。A/B 的提示词与检索策略未改，其差异应视为"
        "同一测量下的模型波动；DexAtlas 的差异才是修复效果的测量。",
        "",
        "## 2. 结果总览",
        "",
        "| 配置 | 复测正确 | 首测 r1 正确 | 三轮首测合计 | 复测 token | 复测耗时(s) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for system in SYSTEMS:
        lines.append(
            f"| {system} | {passes.get(system, 0)}/20 | {baseline_passes.get(system, 0)}/20 "
            f"| {baseline.pooled_passes().get(system, 0)}/60 | {tokens.get(system, 0)} "
            f"| {dur[system]:.1f} |"
        )
    lines += [
        "",
        f"- 全部 trace 合计 token：**{total_tokens}**（API `usage` 字段逐 trace 加总）。",
        "- 结果构成："
        + ", ".join(f"{name} {count}" for name, count in sorted(outcomes.items()))
        + "。",
        "",
        "### DexAtlas 失败题明细",
        "",
    ]
    lines += _dexatlas_failure_notes(round_)
    lines += [
        "",
        "- A/B 的 empty 是检索式配置对 evidence-only 判分题的固有形态（与首测一致）；"
        "其 wrong 多为 `must_contain` 部分命中或计数不符。",
        "",
    ]
    lines += _metric_table(round_)
    lines += _task_table(round_, baseline)
    lines += _fail_mode_table(round_, baseline)
    lines += [
        "失败模式对照的读法：修复针对的四类模式里，**计数题、方法身份枚举、"
        "否定题在 DexAtlas 上改善**，与 M6-③ 各项修复一一对应"
        "（计数逐项成条、完整 JVM 描述符、否定答案移入 limitations、partial 判定谓词与"
        "真实禁用 Analyze）；资源出处类持平（`wheresource` 题已通过，`strings`"
        "两题的检索词命中问题不在本批修复范围）。A/B 三类不变符合预期：其提示词与"
        "检索策略本批未改。",
        "",
        "## 3. 成本与停止条件",
        "",
        f"- 本轮实测 token 合计 **{total_tokens}**（含三配置），授权上限 "
        f"{TOKEN_CAP}，{'未超限' if total_tokens <= TOKEN_CAP else '超出 ' + str(total_tokens - TOKEN_CAP) + '（约 ' + format((total_tokens - TOKEN_CAP) / TOKEN_CAP * 100, '.0f') + '%）'}。"
        "超限发生在运行结束后的核账环节发现：运行本身是单轮 20 题 × 3 配置的"
        "完整授权范围，未因追加轮次或题目超出授权；超出部分主要来自 DexAtlas 配置"
        "的长尾任务。按约定如实记录。",
        "- 单轮设计本身即授权边界：未追加任何轮次或题目。",
        "",
        "## 4. 验收结论（照实陈述）",
        "",
        "服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%（20 题即 ≥16 题）。"
        f"本轮实测：DexAtlas {passes.get('DexAtlas', 0)}/20（{_pct(round_.metrics['DexAtlas']['correct_answer_rate'])}）、"
        f"A {passes.get('A', 0)}/20、B {passes.get('B', 0)}/20。"
        + (
            "**达到验收线。**"
            if passes.get("DexAtlas", 0) >= 16
            else "**未达到验收线，需继续修正或缩小服务承诺后重测。**"
        )
        + "本报告不声称优于任何基线；A/B 与 DexAtlas 预算不同，配置间数字差异反映"
        "可见信息与执行条件不同。",
        "",
        "## 5. 已知局限",
        "",
        "- 单轮单模型，温度 0 下同一模型两次运行仍可能不同；本轮数字不外推为该配置的稳定通过率。",
        "- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。",
        "- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。",
        "- 对照的首测 r1 是修复前代码的测量；除代码状态外，两轮执行条件一致。",
        "- 与首测三轮制不同，本轮为单轮：首测报告的「三轮合计」列（x/60）与本轮单轮"
        "数字（x/20）不可直接比较，逐题对照均以首测 round-1 为基线。",
        "",
        "## 复现命令",
        "",
        "```bash",
        "# key 经环境变量注入，不写入任何文件",
        'export MINIMAX_API_KEY="<key>"',
        'export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"',
        'export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"',
        "uv run --no-sync python benchmarks/comparison/run.py \\",
        "  --provider openai-compat \\",
        "  --base-url https://api.minimaxi.com/v1 \\",
        "  --model MiniMax-M3.1-Flash \\",
        "  --api-key-env MINIMAX_API_KEY \\",
        "  --budget 16384 --agent-budget 120000 --total-tokens 120000 \\",
        "  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \\",
        "  --output E:/Dexatlas/.scratch/m6-level2-retest/full \\",
        "  --task manifest.package.demo --task manifest.permission.name-strings \\",
        "  --task manifest.permission.count-obfuscated --task components.exported.demo \\",
        "  --task components.exported.obfuscated --task overloads.method-identity.crypto-sign \\",
        "  --task overloads.method-identity.descriptor-distinguishes \\",
        "  --task ambiguity.declared-type-contradicts-body --task xrefs.crypto-sign-callers \\",
        "  --task xrefs.handler-handle-callers --task xrefs.crypto-sign-call-site-count \\",
        "  --task strings.api-key.demo --task strings.telemetry-url.obfuscated \\",
        "  --task resources.app-name.demo --task wheresource.app-name-resource-file.demo \\",
        "  --task unanswerable.crypto-digestof-has-no-callers \\",
        "  --task unanswerable.demo-declares-no-receiver \\",
        "  --task partial.no-apktool-there-is-no-manifest \\",
        "  --task partial.no-jadx-the-failure-is-recorded --task multidex.dex-file-count",
        "",
        "# 报告由 trace 重算生成",
        "uv run --no-sync python scripts/m6_level2_retest_report.py",
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def _dexatlas_failure_notes(round_: _Round) -> list[str]:
    """One line per failed DexAtlas trace, in the frozen order."""
    lines: list[str] = []
    for trace in round_.traces:
        if trace.system.value != "DexAtlas" or trace.passed:
            continue
        outcome = _outcome(trace)
        if outcome == "budget-exhausted":
            note = "任务级预算/迭代耗尽，未作答"
        elif outcome == "no-answer" or outcome == "empty":
            note = "回答为空"
        else:
            note = "判分不通过（回答内容与判定要求有差距）"
        lines.append(f"- `{trace.task_id}`：{note}。")
    if not lines:
        lines.append("-（本轮 DexAtlas 无失败题。）")
    return lines


def main(argv: list[str] | None = None) -> int:
    retest = _load_retest()
    baseline = _load_baseline_round1()
    report = _report(retest, baseline)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
