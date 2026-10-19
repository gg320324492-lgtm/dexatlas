"""Reading a stored coverage back out of the evidence.

The analysis records what the decompiler could read as an evidence record, and
the reports read it back rather than recomputing it. A report built from a
stored project has no method list to recompute from — the REST API exports one
on demand, from the database alone — so the record is the only place the
coverage can come from, and the only place it can come from that both entry
points share.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dexatlas.core.models import DECOMPILATION_DETAIL, Evidence


def decompilation_coverage(evidence: Sequence[Evidence]) -> dict[str, Any] | None:
    """The decompilation coverage an analysis recorded, if it recorded one.

    ``None`` means the analysis said nothing about decompilation: the
    decompiler was not installed, or it produced nothing.
    """
    for item in evidence:
        coverage = item.detail.get(DECOMPILATION_DETAIL)
        if isinstance(coverage, dict):
            return coverage
    return None


__all__ = ["decompilation_coverage"]
