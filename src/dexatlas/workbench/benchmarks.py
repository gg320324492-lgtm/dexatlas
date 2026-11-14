"""The benchmark view of the M3 comparison, served read-only.

The [M3 comparison](../../../benchmarks/comparison/run.py) measures three
configurations over the same 92 tasks, twice: once with a scripted provider
and once with a real model. The two measurements were committed as traces —
`docs/benchmarks/comparison-traces.json` and
`docs/benchmarks/comparison-real-traces.json` — and every figure the
reports under `docs/benchmarks/` state is derived from those traces by
`_run_from_document` + `compare`.

This screen serves the same derivation. It adds no number of its own: the
metrics the browser receives are recomputed from the committed traces on
every request, by the same functions that wrote the reports, so a screen
figure and a report figure cannot drift apart. Nothing is cached and
nothing is written; a workspace that has no trace file simply answers
without that measurement.

The disclosures travel with the numbers, because the numbers without them
invite exactly the reading the M3 rules forbid: a scripted provider is not
a model baseline, a real-model run is not reproducible to the digit, and
neither measurement claims that one configuration is better than another.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The two committed measurements. Their names say what they are: the
#: scripted run proves the harness, the real-model run compares what each
#: configuration could see. Neither is a baseline the other is judged
#: against.
SCRIPTED_TRACES = REPOSITORY_ROOT / "docs" / "benchmarks" / "comparison-traces.json"
REAL_TRACES = REPOSITORY_ROOT / "docs" / "benchmarks" / "comparison-real-traces.json"

#: The benchmark module is a repository tool, not an installed package. It
#: inserts the repository root into ``sys.path`` itself when run as a
#: script; imported as a module, it needs the root already importable, which
#: is what the workbench's own checkout provides. The import is deferred to
#: call time so that a wheel without the benchmarks tree still serves the
#: rest of the workbench.
_TRACES_KEY = "traces"


class ConfigurationMetrics(BaseModel):
    """One configuration's eight metrics, as the comparison harness computed them."""

    configuration: str
    provider: str
    model: str
    metrics: dict[str, float | int | None]
    #: The same metrics as the harness's ``format_value`` writes them into the
    #: reports — percentages with one decimal, counts as counted, ``n/a``
    #: where a denominator was zero. The browser renders these verbatim, so a
    #: table cell cannot drift from the report line it mirrors.
    display: dict[str, str]


class FailureCause(BaseModel):
    """Why one configuration's failed tasks failed, with the count of each cause."""

    configuration: str
    cause: str
    tasks: int


class BenchmarkMeasurement(BaseModel):
    """One measurement: what was run, the eight metrics, and why tasks failed."""

    kind: str
    label: str
    traces_file: str
    task_count: int
    budget: int
    configurations: list[ConfigurationMetrics]
    failure_causes: list[FailureCause]


class BenchmarkSet(BaseModel):
    """The committed M3 measurements, recomputed, with the disclosures that bound them."""

    measurements: list[BenchmarkMeasurement]
    disclosures: list[str] = Field(
        default_factory=lambda: [
            "A scripted provider is a stand-in that proves the comparison machinery "
            "runs on every task; it is not a model baseline, and its numbers measure "
            "the harness.",
            "A real-model run is not reproducible to the digit: the same question "
            "twice does not get the same answer twice, so these figures describe the "
            "run whose traces sit beside them, and a difference smaller than that "
            "spread is noise.",
            "Neither measurement claims that one configuration is better than "
            "another. A difference between configurations is a difference between "
            "what each could see, and a comparison never claims an improvement the "
            "measurements do not support.",
        ]
    )


def _failure_causes(traces: list[dict[str, Any]]) -> list[FailureCause]:
    """Group the failed tasks by why they failed, in the report's own words.

    The causes are the harness's (`_failure_causes` in
    `benchmarks/comparison/run.py`); this reads the same fields the report
    reads rather than importing the report formatter, so the screen and the
    report stay two renderings of one computation.
    """
    counts: dict[tuple[str, str], int] = {}
    for trace in traces:
        if trace["passed"]:
            continue
        system = trace["system"]
        error = trace["result"]["error"]
        if "tool-call budget" in error:
            cause = "ran out of tool calls"
        elif "iteration budget" in error:
            cause = "ran out of iterations"
        elif "token budget" in error:
            cause = "ran out of tokens"
        elif error:
            cause = "the run failed"
        elif not trace["result"]["assertions"]:
            cause = "answered with no claim"
        else:
            cause = "answered, and the answer was wrong"
        key = (system, cause)
        counts[key] = counts.get(key, 0) + 1
    return [
        FailureCause(configuration=system, cause=cause, tasks=count)
        for (system, cause), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _measurement(path: Path, kind: str, label: str) -> BenchmarkMeasurement:
    """One measurement, recomputed from its committed traces.

    The import is local because the benchmarks package is a repository tool
    rather than a dependency of the installed package; a workbench running
    from a checkout has it, and this is the one screen that needs it.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    repository_root = str(REPOSITORY_ROOT)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    from benchmarks.comparison.metrics import METRIC_NAMES, format_value
    from benchmarks.comparison.run import _run_from_document

    run = _run_from_document(document)
    traces = document[_TRACES_KEY]
    return BenchmarkMeasurement(
        kind=kind,
        label=label,
        traces_file=path.name,
        task_count=run.task_count,
        budget=run.budget,
        configurations=[
            ConfigurationMetrics(
                configuration=system,
                provider=run.providers.get(system, ""),
                model=run.models.get(system, ""),
                metrics=run.metrics[system],
                display={
                    name: format_value(name, run.metrics[system].get(name)) for name in METRIC_NAMES
                },
            )
            for system in sorted(run.metrics)
        ],
        failure_causes=_failure_causes(traces),
    )


def benchmark_set() -> BenchmarkSet:
    """Both committed measurements, recomputed now.

    A missing trace file is a fact about this checkout, not an error to
    retry: the measurement simply is not here, and the screen answers with
    the ones that are. Nothing is cached — the traces are the evidence, and
    re-reading them is what keeps a served number identical to a regenerated
    one.
    """
    measurements: list[BenchmarkMeasurement] = []
    for path, kind, label in (
        (SCRIPTED_TRACES, "scripted", "Scripted provider (harness check, not a model baseline)"),
        (REAL_TRACES, "real-model", "Real model (MiniMax-M3.1-Flash, openai-compatible)"),
    ):
        if path.is_file():
            measurements.append(_measurement(path, kind, label))
    return BenchmarkSet(measurements=measurements)
