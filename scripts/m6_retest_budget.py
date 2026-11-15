#!/usr/bin/env python3
# ruff: noqa: RUF001 — the failure messages are user-facing Chinese text; the
# fullwidth punctuation is intentional, same as the report scripts.
"""Validate the token budget of an M6 level-2 retest round against its plan.

    uv run --no-sync python scripts/m6_retest_budget.py [trace.json ...]
    uv run --no-sync python scripts/m6_retest_budget.py --check-plan

Reads the run output of the next M6 level-2 retest round (a ``traces.json``
written by ``benchmarks/comparison/run.py --output <dir>``, or the committed
``docs/benchmarks/*-traces.json``) and checks, per task and in total, that
the token spend stays inside the budget fixed in
``docs/benchmarks/m6-level2-retest-plan.md``. Any overshoot exits non-zero;
the report must not be generated from a run that failed this check.

With no trace file given, the script looks for the run output of the planned
round (``.scratch/m6-retest-r2/traces.json``) and then for the committed
retest traces; finding neither, it prints that there is nothing to check and
exits 0 — the plan document itself is still validated for shape.

No network, no model calls: this is a local arithmetic gate over data that
already exists on disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

#: Per-task token budget for the DexAtlas agent configuration, fixed in
#: docs/benchmarks/m6-level2-retest-plan.md §2.1. A task whose cumulative
#: prompt+completion tokens exceed this has hit the per-task fuse; the run
#: records it as budget-exhausted and the plan scores it as a failure.
TASK_TOKEN_LIMIT = 24_000

#: Total token budget for the whole round (all 20 tasks, three
#: configurations), plan §2.1. The authorisation ceiling is 350,000; the
#: plan's operating cap sits 50,000 below it as buffer for per-task fuse
#: overshoot (the budget is checked after a request completes, so one task
#: can end slightly past 24,000).
TOTAL_TOKEN_LIMIT = 300_000

#: The hard authorisation ceiling. Crossing it is a plan violation to report
#: loudly, not a number to average away.
AUTHORISATION_LIMIT = 350_000

#: Retrieval configurations have no task-level loop: one request answers the
#: question. Their per-request ``max_tokens`` is 16,384; a trace past twice
#: that is an anomaly worth naming even though it cannot break the round's
#: budget.
RETRIEVAL_PER_TASK_LIMIT = 2 * 16_384

#: Where the planned run writes its traces, and the committed traces of the
#: previous round (used as a fallback example of the format).
RUN_OUTPUT_TRACES = REPOSITORY_ROOT / ".scratch" / "m6-retest-r2" / "traces.json"
COMMITTED_TRACES = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest-traces.json"

PLAN_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-retest-plan.md"

#: Strings the plan document must carry: the budget figures this script
#: enforces and the run command's fuse argument. If one goes missing, the
#: plan and the gate have drifted apart and the plan is not executable.
PLAN_REQUIRED_SNIPPETS = (
    "300,000",
    "24,000",
    "--total-tokens 24000",
    "350,000",
)

AGENT_SYSTEM = "DexAtlas"
RETRIEVAL_SYSTEMS = ("A", "B")


def _trace_tokens(trace: dict[str, object]) -> int:
    """Total tokens one trace records (prompt + completion)."""
    result = trace.get("result")
    if not isinstance(result, dict):
        return 0
    total = 0
    for key in ("prompt_tokens", "completion_tokens"):
        value = result.get(key, 0)
        total += value if isinstance(value, int) else 0
    return total


def _load_traces(paths: list[Path]) -> list[dict[str, object]]:
    traces: list[dict[str, object]] = []
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        loaded = document.get("traces") if isinstance(document, dict) else None
        if not isinstance(loaded, list):
            raise SystemExit(f"{path}: 不是有效的 trace 文件（缺少 traces 数组）")
        traces.extend(item for item in loaded if isinstance(item, dict))
    return traces


def check_traces(traces: list[dict[str, object]]) -> int:
    """Check every trace against the plan's budgets; return an exit code."""
    failures: list[str] = []
    total = 0
    per_task: dict[tuple[str, str], int] = {}

    for trace in traces:
        system = str(trace.get("system", ""))
        task_id = str(trace.get("task_id", "<unknown>"))
        tokens = _trace_tokens(trace)
        total += tokens
        key = (system, task_id)
        per_task[key] = per_task.get(key, 0) + tokens

        if system == AGENT_SYSTEM and tokens > TASK_TOKEN_LIMIT:
            failures.append(
                f"单题超预算: {task_id} 用了 {tokens} tokens（上限 {TASK_TOKEN_LIMIT}）"
            )
        elif system in RETRIEVAL_SYSTEMS and tokens > RETRIEVAL_PER_TASK_LIMIT:
            failures.append(
                f"检索式配置单题异常: [{system}] {task_id} 用了 {tokens} tokens"
                f"（告警线 {RETRIEVAL_PER_TASK_LIMIT}）"
            )

    if total > AUTHORISATION_LIMIT:
        failures.append(f"超出授权上限: 全部 trace 合计 {total} tokens > {AUTHORISATION_LIMIT}")
    elif total > TOTAL_TOKEN_LIMIT:
        failures.append(f"超出本轮总预算: 全部 trace 合计 {total} tokens > {TOTAL_TOKEN_LIMIT}")

    agent_total = sum(v for (system, _), v in per_task.items() if system == AGENT_SYSTEM)
    print(
        f"trace 共 {len(traces)} 条，token 合计 {total}（预算 {TOTAL_TOKEN_LIMIT}，"
        f"授权 {AUTHORISATION_LIMIT}）"
    )
    print(f"DexAtlas 合计 {agent_total} tokens；单题上限 {TASK_TOKEN_LIMIT}")
    for (system, task_id), tokens in sorted(per_task.items(), key=lambda item: -item[1]):
        if system == AGENT_SYSTEM:
            marker = " [超预算]" if tokens > TASK_TOKEN_LIMIT else ""
            print(f"  DexAtlas {task_id}: {tokens}{marker}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("预算校验通过。")
    return 0


def check_plan() -> int:
    """Validate the plan document's shape without any trace data."""
    if not PLAN_PATH.is_file():
        print(f"FAIL: 方案文件不存在: {PLAN_PATH.relative_to(REPOSITORY_ROOT)}")
        return 1
    text = PLAN_PATH.read_text(encoding="utf-8")
    missing = [snippet for snippet in PLAN_REQUIRED_SNIPPETS if snippet not in text]
    if missing:
        for snippet in missing:
            print(f"FAIL: 方案文件缺少预算关键内容: {snippet!r}")
        return 1
    print(f"方案文件校验通过: {PLAN_PATH.relative_to(REPOSITORY_ROOT)}")
    print("无 trace 数据，仅校验方案文件存在且格式正确")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "traces",
        nargs="*",
        type=Path,
        help="要校验的 trace JSON 文件（可多个）；缺省时自动探测运行输出。",
    )
    parser.add_argument(
        "--check-plan",
        action="store_true",
        help="只校验方案文件存在且包含预算关键数字，不读取 trace。",
    )
    args = parser.parse_args(argv)

    if args.check_plan:
        return check_plan()

    paths = list(args.traces)
    if not paths:
        if RUN_OUTPUT_TRACES.is_file():
            paths = [RUN_OUTPUT_TRACES]
        elif COMMITTED_TRACES.is_file():
            paths = [COMMITTED_TRACES]
    if not paths:
        return check_plan()

    traces = _load_traces(paths)
    if not traces:
        print("trace 文件存在但没有记录；按无数据处理。")
        return check_plan()
    return check_traces(traces)


if __name__ == "__main__":
    sys.exit(main())
