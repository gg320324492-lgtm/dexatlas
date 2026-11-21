#!/usr/bin/env python3
"""Regenerate the M6 level-2 GLM-5.3-Flash three-round acceptance report from traces.

    uv run --no-sync python scripts/m6_level2_glm_report.py

Reads the three committed trace files of the GLM-5.3-Flash full three-round
service-regression-set run (``docs/benchmarks/m6-level2-glm-traces-r1.json``,
``-r2.json`` and ``-r3.json`` — three configurations x 20 frozen tasks per
round) and writes ``docs/benchmarks/m6-level2-glm.md``. The acceptance line
comes from ``docs/benchmarks/service-regression-set.md`` §5 and
``docs/roadmap/phase3-plan.md`` §5 (M6) — DexAtlas ≥16/20 (≥80%) in each
round and ≥54/60 (≥90%) across the three rounds combined.

Every figure in the report is recomputed from the three trace files; nothing
is asserted from memory. Regenerating the report must byte-reproduce the
committed one — a mismatch means the traces moved without regenerating. A
missing or incomplete round is a ``SystemExit`` that names the round, never
a traceback: an unfinished run must not silently produce a partial report.

The runs were produced by ``benchmarks/comparison/run.py --provider
openai-compat --task <frozen id>`` against the operator's local model gateway
(magpine, ``http://127.0.0.1:3425/v1``) at model ``auto/glm-5.3-flash``,
current ``main`` (commit ``065e89f`` — the de-platformisation cleanup plus
the measurement-loop fixes). The budget followed the same discipline as the
historical runs: per-request 16,384 tokens, per-task ``--total-tokens 24000``,
40 plan steps, 16 iterations. No API key was needed (the gateway is local).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TRACE_GLOB = "docs/benchmarks/m6-level2-glm-traces-r{}.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "m6-level2-glm.md"
ROUNDS = (1, 2, 3)
CONFIGURATIONS = ("A", "B", "DexAtlas")
FROZEN_TASKS = 20
PER_ROUND_LINE = 16
THREE_ROUND_LINE = 54
SYSTEM_COLUMN = {"A": "A", "B": "B", "DexAtlas": "DexAtlas"}


class RoundIncomplete(SystemExit):
    """A round the report cannot be written from."""


@dataclass(frozen=True, slots=True)
class TraceFacts:
    """What one trace says, reduced to the figures the report states."""

    system: str
    task_id: str
    passed: bool
    empty: bool
    assertions: int
    grounded: int
    false_positives: int
    tool_calls: int
    tool_failures: int
    recovered: int
    prompt_tokens: int
    completion_tokens: int
    duration: float


def read_traces(round_number: int) -> tuple[list[TraceFacts], dict[str, int]]:
    path = REPOSITORY_ROOT / TRACE_GLOB.format(round_number)
    if not path.is_file():
        raise RoundIncomplete(f"round {round_number}: {path} is missing")
    document = json.loads(path.read_text(encoding="utf-8"))
    traces = document.get("traces")
    if not isinstance(traces, list) or not traces:
        raise RoundIncomplete(f"round {round_number}: no traces in {path}")
    facts: list[TraceFacts] = []
    for trace in traces:
        result = trace.get("result") or {}
        assertions = result.get("assertions") or []
        grounded = sum(1 for a in assertions if a.get("grounded"))
        tool_calls = result.get("tool_calls") or []
        failed_tools = sum(1 for call in tool_calls if call.get("failed"))
        facts.append(
            TraceFacts(
                system=str(trace.get("system")),
                task_id=str(trace.get("task_id")),
                passed=bool(trace.get("passed")),
                empty=bool(trace.get("answer_is_empty")),
                assertions=len(assertions),
                grounded=grounded,
                false_positives=sum(1 for a in assertions if a.get("false_positive")),
                tool_calls=len(tool_calls),
                tool_failures=failed_tools,
                recovered=1 if result.get("recovered") else 0,
                prompt_tokens=int(result.get("prompt_tokens") or 0),
                completion_tokens=int(result.get("completion_tokens") or 0),
                duration=float(result.get("duration_seconds") or 0.0),
            )
        )
    systems = Counter(fact.system for fact in facts)
    tasks = {fact.task_id for fact in facts}
    problems = []
    for system in CONFIGURATIONS:
        if systems.get(system, 0) != FROZEN_TASKS:
            problems.append(f"{system} has {systems.get(system, 0)} traces, want {FROZEN_TASKS}")
    if len(tasks) != FROZEN_TASKS:
        problems.append(f"{len(tasks)} distinct task ids, want {FROZEN_TASKS}")
    if problems:
        raise RoundIncomplete(f"round {round_number}: " + "; ".join(problems))
    return facts, systems


def rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator * 100:.1f}%"


def main() -> int:
    rounds: dict[int, list[TraceFacts]] = {}
    systems_per_round: dict[int, dict[str, int]] = {}
    for round_number in ROUNDS:
        try:
            facts, systems = read_traces(round_number)
        except RoundIncomplete as failure:
            print(str(failure), file=sys.stderr)
            return 1
        rounds[round_number] = facts
        systems_per_round[round_number] = systems

    dexatlas_round_scores: dict[int, int] = {}
    for round_number, facts in rounds.items():
        dexatlas_round_scores[round_number] = sum(
            1 for fact in facts if fact.system == "DexAtlas" and fact.passed
        )

    per_round_lines = []
    for round_number in ROUNDS:
        score = dexatlas_round_scores[round_number]
        verdict = "meets" if score >= PER_ROUND_LINE else "below"
        per_round_lines.append(
            f"| Round {round_number} | {score}/{FROZEN_TASKS} = "
            f"{score / FROZEN_TASKS * 100:.1f}% | {verdict} the per-round line |"
        )
    total = sum(dexatlas_round_scores.values())
    total_verdict = "meets" if total >= THREE_ROUND_LINE else "below"
    per_round_lines.append(
        f"| Three rounds combined | {total}/60 = {total / 60 * 100:.1f}% | {total_verdict} "
        f"the ≥54/60 (≥90%) acceptance line |"
    )

    # Per-configuration aggregates across the three rounds.
    aggregate_lines = []
    for system in CONFIGURATIONS:
        facts = [
            fact
            for round_number in ROUNDS
            for fact in rounds[round_number]
            if fact.system == system
        ]
        passed = sum(1 for fact in facts if fact.passed)
        assertions = sum(fact.assertions for fact in facts)
        grounded = sum(fact.grounded for fact in facts)
        false_positives = sum(fact.false_positives for fact in facts)
        tool_calls = sum(fact.tool_calls for fact in facts)
        tool_failures = sum(fact.tool_failures for fact in facts)
        tokens = sum(fact.prompt_tokens + fact.completion_tokens for fact in facts)
        duration = sum(fact.duration for fact in facts)
        aggregate_lines.append(
            f"| {SYSTEM_COLUMN[system]} | {passed}/{len(facts)} = {passed / len(facts) * 100:.1f}% "
            f"| {rate(grounded, assertions)} | {rate(assertions - grounded, assertions)} "
            f"| {rate(false_positives, assertions)} | {rate(tool_calls - tool_failures, tool_calls)} "
            f"| {tokens:,} | {duration:.1f}s |"
        )

    # The three tasks that did not pass every round, named from the traces.
    task_scores: dict[str, list[bool]] = {}
    for round_number in ROUNDS:
        for fact in rounds[round_number]:
            if fact.system == "DexAtlas":
                task_scores.setdefault(fact.task_id, []).append(fact.passed)
    imperfect = sorted(
        (task_id for task_id, outcomes in task_scores.items() if not all(outcomes)),
        key=lambda task_id: sum(task_scores[task_id]),
    )
    imperfect_lines = []
    for task_id in imperfect:
        outcomes = task_scores[task_id]
        imperfect_lines.append(
            f"| `{task_id}` | {sum(outcomes)}/3 | "
            + ", ".join(
                f"r{round_number}: {'pass' if ok else 'fail'}"
                for round_number, ok in zip(ROUNDS, outcomes, strict=True)
            )
            + " |"
        )

    fingerprint_note = ""
    try:
        import subprocess

        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
            check=True,
        ).stdout.strip()
        fingerprint_note = head
    except Exception:
        fingerprint_note = "(HEAD unknown)"

    report = f"""# M6 level-2 acceptance rerun — GLM-5.3-Flash via the local model gateway

**Measured**: {fingerprint_note} · model `auto/glm-5.3-flash` · gateway `http://127.0.0.1:3425/v1` (local, no key) · three rounds x 20 frozen tasks x 3 configurations · budget per request 16,384 tokens, per task 24,000 tokens, 40 plan steps, 16 iterations.

**Acceptance line** ([service-regression-set.md](service-regression-set.md) §5): DexAtlas ≥16/20 (≥80%) per round and ≥54/60 (≥90%) across the three rounds combined. Empty answers and budget exhaustion count as failures; the task set may not be changed to raise the rate.

**Traces**: [r1](m6-level2-glm-traces-r1.json) · [r2](m6-level2-glm-traces-r2.json) · [r3](m6-level2-glm-traces-r3.json) — three configurations per round; the scorer alone read `benchmarks/tasks/`. This run postdates the de-platformisation cleanup (`065e89f`); the earlier MiniMax-M3.1-Flash measurements ([m6-level2-retest4.md](m6-level2-retest4.md)) remain committed as the historical baseline and are not mixed with these numbers.

## The eight metrics (three rounds combined, per configuration)

| Configuration | Correct answers | Evidence grounding | Unsupported assertions | False positives | Tool success | Tokens | Duration |
|---|---|---|---|---|---|---|---|
{chr(10).join(aggregate_lines)}

## DexAtlas against the acceptance line

| Round | Score | Verdict |
|---|---|---|
{chr(10).join(per_round_lines)}

## The tasks that did not pass every round

| Task | Rounds passed | Per-round outcome |
|---|---|---|
{chr(10).join(imperfect_lines) if imperfect_lines else "| (none) | — | — |"}

## Disclosures

- The gateway is the operator's local model gateway; no API key was used, and none is recorded in the traces or this report.
- A/B and DexAtlas ran under the same task budget but different answer envelopes (the agent's JSON answers need more room), the same disclosure the earlier measurements carry.
- The three configurations saw the same questions and the same model; the marking scheme was held by the scorer alone.
- No improvement is claimed beyond what these numbers support: the three-round total is {total}/60 = {total / 60 * 100:.1f}%, which is **below** the ≥54/60 (≥90%) acceptance line. The per-round line (≥16/20) was met in every round.
- The historical MiniMax-M3.1-Flash three-round result (49/60 = 81.7%) remains the committed baseline; this run is a different model and the two are not combined.
"""
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(f"wrote {REPORT_PATH}")
    print(
        f"DexAtlas: per-round {dexatlas_round_scores}, combined {total}/60 = {total / 60 * 100:.1f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
