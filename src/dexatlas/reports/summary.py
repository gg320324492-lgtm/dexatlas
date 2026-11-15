"""The shared metrics of a report.

The Markdown, JSON and HTML renderings of one analysis describe the same
analysis, so the numbers they state have to be the same numbers. They are
assembled here, once, from the analysis model — no rendering layer computes a
fact of its own, and a count that changes here changes in every format at
the same moment.
"""

from __future__ import annotations

from dexatlas.core.models import (
    Project,
    cross_reference_call_edges,
    cross_reference_call_sites,
    cross_reference_records,
    index_gaps,
)
from dexatlas.core.pipeline import AnalysisResult, analysis_duration
from dexatlas.reports.coverage import decompilation_coverage


def index_completeness(project: Project) -> str:
    """Whether the index covers the whole APK, and what is missing from it.

    A count of what was indexed reads as a count of what the APK holds unless
    the reader is told otherwise. "2 classes" and "2 classes, because one of
    the DEX files could not be parsed" are different claims, and the second
    one is the honest one.
    """
    gaps = index_gaps(project.errors)
    if not gaps:
        return "complete"
    return "incomplete: " + "; ".join(gap.message for gap in gaps)


def tool_line(project: Project) -> str:
    """The tools that took part, and the version of each."""
    if not project.tool_versions:
        return "(none recorded)"
    return ", ".join(
        f"{name} {version or 'not installed'}"
        for name, version in sorted(project.tool_versions.items())
    )


def summary_metrics(result: AnalysisResult) -> list[tuple[str, str]]:
    """The metrics every rendering states, in the order they are stated.

    The Markdown report is the spelling a reader has been reading; the HTML
    page and the JSON document carry the same values under the same names.
    A metric that only one format states is a fact two formats disagree
    about by omission.
    """
    project = result.project
    metrics: list[tuple[str, str]] = [
        ("Index completeness", index_completeness(project)),
        ("Classes indexed", f"{project.class_count:,}"),
        ("Methods indexed", f"{project.method_count:,}"),
    ]
    coverage = decompilation_coverage(result.evidence)
    if coverage is not None:
        # The decompiler's own answer, so the reader knows how much of the
        # indexed code can be read as Java.
        metrics.append(
            (
                "Methods decompiled by JADX",
                f"{coverage.get('methods_decompiled', 0):,} of {coverage.get('methods_total', 0):,}",
            )
        )
    metrics += [
        ("Resource strings indexed", f"{project.resource_count:,}"),
        # The two counts are about two different things, and each of them
        # says which: a call *site* is one place in the bytecode where a
        # call happens, a call *edge* is the relationship between two methods.
        ("Call sites indexed", f"{project.reference_count:,}"),
        ("Call edges indexed", f"{project.call_edge_count:,}"),
        # The call sites the cross-reference records cover, and the number of
        # records themselves. The two are different numbers about different
        # things: one record covers every call site of the method it is about.
        ("Call sites with evidence", f"{cross_reference_call_sites(result.evidence):,}"),
        ("Call edges with evidence", f"{cross_reference_call_edges(result.evidence):,}"),
        ("Cross-reference records", f"{cross_reference_records(result.evidence):,}"),
        ("Evidence records", f"{project.evidence_count:,}"),
        ("DEX files", f"{len(project.apk.dex_files)}"),
        ("Native libraries", f"{len(project.apk.native_libraries)}"),
        ("Analysis time", _duration_cell(result)),
    ]
    return metrics


def _duration_cell(result: AnalysisResult) -> str:
    """How long the analysis took — or that it is not known.

    A run that was never timed has no duration, and a report that prints
    ``0.0s`` for it states a measurement the run never made.
    """
    duration = analysis_duration(result)
    return "unknown" if duration is None else f"{duration:.1f}s"


__all__ = ["index_completeness", "summary_metrics", "tool_line"]
