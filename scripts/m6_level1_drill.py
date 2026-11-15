#!/usr/bin/env python3
"""Run the M6 level-1 scripted drill and write its evidence.

    uv run --no-sync python scripts/m6_level1_drill.py --workspace E:/Dexatlas/.scratch/m6-level1

The drill is the level-1 run defined by ``docs/benchmarks/service-regression-set.md``
§6: the frozen 20-task service-regression set and the full 92-task legacy set,
each run once over the three comparison configurations (A, B, DexAtlas) with
the scripted provider. It proves the comparison machinery — question issue,
tool loop, trace writing, scoring — works end to end on the frozen set; it is
NOT a model baseline and its numbers measure the harness.

Everything written here is generated: the per-task table comes from the run's
traces, the level-0 comparison comes from a ``benchmarks/run.py --json``
document produced by the level-0 command in the same document's appendix, and
the script never hard-codes a result. Re-running it rewrites both outputs
from the fresh traces.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.comparison.model import TaskTrace  # noqa: E402
from benchmarks.comparison.run import run_comparison  # noqa: E402
from benchmarks.m6_service_set import SERVICE_REGRESSION_PREFIXES  # noqa: E402
from benchmarks.tasks import ALL_TASKS  # noqa: E402

#: The two runs the drill is made of. The frozen set first: it is the subset
#: the service promises, and if it cannot run, the full set will not rescue it.
DRILLS = (
    ("service-regression-20", SERVICE_REGRESSION_PREFIXES),
    ("legacy-full-92", ()),
)

OUTCOME_COLUMN = {
    True: "correct",
}


@dataclass(frozen=True, slots=True)
class _TaskRow:
    """One task's verdict across the three configurations."""

    task_id: str
    reference: str
    sample: str
    configuration: str
    category: str
    outcomes: dict[str, str]
    """configuration name -> correct / wrong / empty / budget-exhausted / errored."""
    tool_calls: dict[str, str]
    """configuration name -> "3 calls, all ok" style summary."""
    seconds: dict[str, float]


def _outcome(trace: TaskTrace) -> str:
    """One word for how a scored trace ended.

    The scorer's verdict comes first: ``passed`` is the drill's answer, and
    ``budget-exhausted`` names only a run that was stopped before it could
    answer. The scripted provider's "the script ran out of answers" looks
    like a failure in ``result.failed``, but an expect-empty task is *scored*
    on that empty script — the scorer passes it, and this function must say
    ``correct``, not name the mechanics. ``result.failed`` therefore decides
    only the outcome of a trace the scorer did not pass.
    """
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


def _call_summary(trace: TaskTrace) -> str:
    calls = trace.result.tool_calls
    if not calls:
        return "no tool calls"
    ok = sum(1 for call in calls if call.ok)
    return f"{len(calls)} call(s), {ok} ok"


def _rows(traces: tuple[TaskTrace, ...]) -> list[_TaskRow]:
    by_task: dict[str, dict[str, TaskTrace]] = {}
    for trace in traces:
        by_task.setdefault(trace.task_id, {})[trace.system.value] = trace
    rows: list[_TaskRow] = []
    for task in ALL_TASKS:
        per_system = by_task.get(task.id)
        if not per_system:
            continue
        rows.append(
            _TaskRow(
                task_id=task.id,
                reference=next(iter(per_system.values())).reference,
                sample=task.sample.value,
                configuration=task.configuration.value,
                category=task.category.value,
                outcomes={name: _outcome(trace) for name, trace in per_system.items()},
                tool_calls={name: _call_summary(trace) for name, trace in per_system.items()},
                seconds={
                    name: round(trace.result.duration_seconds, 3)
                    for name, trace in per_system.items()
                },
            )
        )
    return rows


def _metrics(traces: tuple[TaskTrace, ...]) -> dict[str, dict[str, float | int | None]]:
    from benchmarks.comparison.metrics import compare

    return compare(traces)


def _write_trace(run: object, path: Path) -> None:
    document = run.to_dict()  # type: ignore[attr-defined]
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")


def _task_table(name: str, rows: list[_TaskRow], traces: tuple[TaskTrace, ...]) -> str:
    """The per-task verdict table, every cell read off a trace."""
    systems = sorted({trace.system.value for trace in traces})
    lines = [f"### {name}", ""]
    if not traces:
        lines += ["This run did not happen, so there is nothing to table.", ""]
        return "\n".join(lines)
    lines += [
        f"{len(rows)} task(s), {len(traces)} scored trace(s).",
        "",
        "| reference | task id | sample | asked-in | category | "
        + " | ".join(f"{system} outcome" for system in systems)
        + " | tool calls (per config) | seconds (per config) |",
        "|---|---|---|---|---|" + "---|" * len(systems) + "---|---|",
    ]
    for row in rows:
        outcomes = " | ".join(row.outcomes.get(system, "-") for system in systems)
        calls = "; ".join(f"{system}: {row.tool_calls.get(system, '-')}" for system in systems)
        seconds = "; ".join(f"{system}: {row.seconds.get(system, '-')}s" for system in systems)
        lines.append(
            f"| {row.reference} | `{row.task_id}` | {row.sample} | {row.configuration} "
            f"| {row.category} | {outcomes} | {calls} | {seconds} |"
        )
    tally = Counter(_outcome(trace) for trace in traces)
    lines += [
        "",
        "Outcome tally over all scored traces: "
        + ", ".join(f"{name} {count}" for name, count in sorted(tally.items()))
        + ".",
        "",
    ]
    return "\n".join(lines)


def _level0_section(level0_path: Path, rows: list[_TaskRow]) -> str:
    """Compare the drill with the level-0 deterministic run.

    The level-0 document is a ``benchmarks/run.py --json`` output over the
    same 20 frozen ids. Both sides are read, never asserted: a level-0 run
    that did not happen leaves this section saying so, and a drill row the
    level-0 record does not cover is marked as uncovered rather than guessed.
    """
    lines = [
        "## Against the level-0 deterministic run",
        "",
        "Level 0 asks DexAtlas's own API the same 20 questions with no model "
        "in the loop (`benchmarks/run.py --task ... --json`). The drill is "
        "the same questions through the comparison harness with the scripted "
        "provider. The two agree when both record a pass on the same task; "
        "they disagree when the harness's scripted loop changes the verdict, "
        "and every disagreement is a fact about the scripted machinery, not "
        "about a model.",
        "",
    ]
    if not level0_path.is_file():
        return "\n".join(
            [
                *lines,
                f"The level-0 document `{level0_path}` was not found, so this "
                "comparison could not be made. Re-run the level-0 command in "
                "the frozen document's appendix A and regenerate this report.",
            ]
        )
    document = json.loads(level0_path.read_text(encoding="utf-8"))
    level0 = {result["id"]: result["passed"] for result in document["results"]}
    agree: list[str] = []
    disagree: list[str] = []
    uncovered: list[str] = []
    for row in rows:
        if row.task_id not in level0:
            uncovered.append(row.task_id)
            continue
        # "correct" on every configuration is the drill's pass; anything
        # else is a task the scripted harness did not carry through.
        drill_passed = all(outcome == "correct" for outcome in row.outcomes.values())
        if drill_passed == level0[row.task_id]:
            agree.append(row.task_id)
        else:
            disagree.append(
                f"{row.task_id} (level-0 {'pass' if level0[row.task_id] else 'fail'}, "
                f"drill {', '.join(f'{name}={outcome}' for name, outcome in sorted(row.outcomes.items()))})"
            )
    lines += [
        f"Tasks covered by both: {len(agree) + len(disagree)} of {len(rows)}.",
        f"Same verdict on both: {len(agree)}.",
        f"Different verdict: {len(disagree)}"
        + (":\n  - " + "\n  - ".join(disagree) if disagree else "."),
    ]
    if uncovered:
        lines.append(f"Drill rows the level-0 record does not cover: {', '.join(uncovered)}.")
    return "\n".join(lines)


def _report(
    runs: list[tuple[str, object, tuple[TaskTrace, ...], list[_TaskRow]]],
    level0_path: Path,
) -> str:
    started = [
        "# M6 level 1 — scripted drill over the service-regression set",
        "",
        "Generated by `scripts/m6_level1_drill.py --traces-only` from the "
        "traces named in [Traces](#traces); every figure below is read back "
        "out of those traces. Regenerate the run, regenerate this file; do "
        "not edit a number.",
        "",
        "This is the level-1 run of the frozen document's no-model plan: the "
        "scripted provider is a stand-in, so these numbers prove the "
        "comparison machinery — question issue, tool loop, trace, scoring — "
        "runs on the frozen set. They are NOT a model baseline, and no "
        "difference between configurations here is a claim about model "
        "quality. The real-model batch (level 2) is a separate, authorised "
        "measurement.",
        "",
    ]
    for name, _run, traces, rows in runs:
        started.append(_task_table(name, rows, traces))
        metrics = _metrics(traces)
        if not metrics:
            continue
        started += [
            f"Eight-metric summary for {name} (from the same traces):",
            "",
            "| metric | " + " | ".join(sorted(metrics)) + " |",
            "|---|" + "---:|" * len(metrics),
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
            cells = " | ".join(
                f"{metrics[system][metric]:.3f}"
                if isinstance(metrics[system][metric], float)
                else str(metrics[system][metric])
                for system in sorted(metrics)
            )
            started.append(f"| `{metric}` | {cells} |")
        started.append("")
    started.append(_level0_section(level0_path, runs[0][3]))
    started.append(_traces_section(runs))
    return "\n".join(started) + "\n"


def _traces_section(
    runs: list[tuple[str, object, tuple[TaskTrace, ...], list[_TaskRow]]],
) -> str:
    """Name the trace files this report was generated from, with their sizes."""
    lines = ["## Traces", "", "The evidence this report was generated from:", ""]
    for name, _run, traces, _rows in runs:
        if not traces:
            continue
        path = REPOSITORY_ROOT / ".scratch" / "m6-level1" / f"{name}-traces.json"
        lines.append(f"- `{path}` — {len(traces)} scored trace(s)")
    lines += [
        "",
        "Regenerate the report without re-running the analysis:",
        "",
        "```bash",
        "uv run --no-sync python scripts/m6_level1_drill.py \\",
        "  --workspace E:/Dexatlas/.scratch/m6-level1/ws --traces-only",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/m6_level1_drill.py",
        description="Run the M6 level-1 scripted drill (frozen 20 + full 92).",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Where the harness builds its analysis workspace (under .scratch).",
    )
    parser.add_argument(
        "--level0-json",
        type=Path,
        default=REPOSITORY_ROOT / ".scratch" / "m6-level0" / "level0-20.json",
        help="The level-0 run's --json document, for the comparison section.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / ".scratch" / "m6-level1",
        help="Where the traces and the generated report are written.",
    )
    parser.add_argument(
        "--skip-full-set",
        action="store_true",
        help="Run only the frozen 20 (smoke); the report then says the full set did not run.",
    )
    parser.add_argument(
        "--traces-only",
        action="store_true",
        help=(
            "Skip the runs: rebuild the report from trace files already in "
            "--output-dir. The report is always derived from traces, so this "
            "is how the report file is regenerated without re-running."
        ),
    )
    args = parser.parse_args(argv)

    drills = DRILLS if not args.skip_full_set else DRILLS[:1]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    runs: list[tuple[str, object, tuple[TaskTrace, ...], list[_TaskRow]]] = []
    for name, prefixes in drills:
        trace_path = args.output_dir / f"{name}-traces.json"
        if args.traces_only:
            if not trace_path.is_file():
                raise SystemExit(f"--traces-only needs {trace_path}, which is not there")
            print(f"[{name}] reading {trace_path}", flush=True)
        else:
            args.workspace.mkdir(parents=True, exist_ok=True)
            print(f"[{name}] running {len(prefixes) or len(ALL_TASKS)} task(s)...", flush=True)
            run = run_comparison(
                workspace=args.workspace / name,
                budget=2048,
                provider_factory=None,  # scripted, zero model calls
                task_prefixes=prefixes,
            )
            _write_trace(run, trace_path)
            print(f"[{name}] {len(run.traces)} traces -> {trace_path}", flush=True)
        traces = tuple(
            TaskTrace.from_dict(item)
            for item in json.loads(trace_path.read_text(encoding="utf-8"))["traces"]
        )
        runs.append((name, None, traces, _rows(traces)))

    if args.skip_full_set:
        runs.append(("legacy-full-92 (NOT RUN — --skip-full-set)", None, (), []))

    report_path = args.output_dir / "m6-level1-report.md"
    report_path.write_text(_report(runs, args.level0_json), encoding="utf-8")
    print(f"report -> {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
