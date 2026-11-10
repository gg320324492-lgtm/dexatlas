"""M3 的三配置对比: harness, metrics and artifacts.

:mod:`benchmarks.run` validates the 81 tasks' expected answers through
DexAtlas's own probes. This package runs the same questions against three
systems under test, records one auditable trace per run, and derives every
reported figure from those traces.

Two boundaries are not negotiable:

* A system under test sees only the reference, question, sample and
  configuration that ``benchmarks/run.py --emit-questions`` emits. It never
  reads ``benchmarks/tasks/``; the scorer alone holds the marking scheme.
* Every trace records its provider. A run measured with the scripted provider
  proves the machinery works; it is not a model baseline, and the report says
  so.
"""

from __future__ import annotations

from benchmarks.comparison.metrics import compare, metrics_for
from benchmarks.comparison.model import (
    Assertion,
    Question,
    SystemKind,
    SystemResult,
    TaskTrace,
    ToolCallTrace,
)

__all__ = [
    "Assertion",
    "Question",
    "SystemKind",
    "SystemResult",
    "TaskTrace",
    "ToolCallTrace",
    "compare",
    "metrics_for",
]
