"""The M3 benchmark: a task set over the first-party samples, and a runner.

The task set lives in :mod:`benchmarks.tasks`, the shape of a task and the
rules for checking one live in :mod:`benchmarks.model`, and the two readers
that establish the expectations independently of the tool under test live in
:mod:`benchmarks.axmlreader` and :mod:`benchmarks.dexreader`.
"""

from __future__ import annotations

__all__ = ["axmlreader", "dexreader", "model", "probes", "tasks"]
