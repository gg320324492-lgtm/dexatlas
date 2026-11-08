"""JSON report — the machine-readable form, and the CLI/API's shared shape."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dexatlas.core.calls import cross_reference_edge_count, cross_reference_site_count
from dexatlas.core.models import (
    Evidence,
    Project,
    cross_reference_records,
    index_gaps,
)
from dexatlas.core.paths import display_path
from dexatlas.core.pipeline import AnalysisResult, analysis_duration
from dexatlas.reports.coverage import decompilation_coverage


def build_json_report(result: AnalysisResult) -> dict[str, Any]:
    """Assemble the full analysis as a serializable document.

    Backend failures are included in ``errors`` rather than omitted: a report that hides
    which steps did not run is exactly the report that gets over-trusted.
    """
    project = result.project
    return {
        # 2 adds the run the report describes, and the status of a later
        # attempt that published nothing. Both are additive; a reader of a
        # version 1 document that ignores unknown keys is unaffected.
        #
        # 3 says which of the two things a cross-reference count is counting.
        # The indexed count is the call **edges** now -- the relationships
        # between two methods -- and it used to be the rows of the index,
        # which counted the places in the bytecode where a call happened. The
        # call sites are counted in their own key, so a reader of a version 2
        # document that ignores unknown keys is unaffected, and a reader that
        # reads them has both numbers.
        "schema_version": 3,
        "generated_at": datetime.now(UTC).isoformat(),
        "project": _project_block(project, result),
        "run": _run_block(result),
        "latest_attempt_status": (
            result.latest_attempt_status.value if result.latest_attempt_status is not None else None
        ),
        "tools": project.tool_versions,
        "errors": [e.model_dump(mode="json") for e in project.errors],
        "manifest": result.manifest.model_dump(mode="json") if result.manifest else None,
        "evidence": [e.model_dump(mode="json") for e in result.evidence],
        "summary": _summary_block(result),
    }


def _run_block(result: AnalysisResult) -> dict[str, Any] | None:
    """The run this report describes.

    The run has an identity of its own, and a document that does not name it
    cannot say which attempt its numbers come from.
    """
    run = result.run
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status.value,
        "completeness": run.completeness.value,
        "apk_sha256": run.apk_sha256,
        "tool_versions": run.tool_versions,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_seconds": run.duration_seconds,
    }


def _project_block(project: Project, result: AnalysisResult) -> dict[str, Any]:
    return {
        "id": project.id,
        "apk": {
            "sha256": project.apk.sha256,
            "size_bytes": project.apk.size_bytes,
            # The file's name, not the path to it. A report is written to a
            # file, diffed and pasted into issues, and the server's filesystem
            # layout is not part of the analysis.
            "path": display_path(project.apk.path),
            "dex_files": project.apk.dex_files,
            "native_libraries": project.apk.native_libraries,
            "has_signed_certificate": project.apk.has_signed_certificate,
        },
        "status": project.status.value,
        "created_at": project.created_at.isoformat(),
        "class_count": project.class_count,
        "method_count": project.method_count,
        "reference_count": project.reference_count,
        "call_site_count": result.call_site_count,
        "call_edge_count": project.reference_count,
        "evidence_count": project.evidence_count,
        "resource_count": project.resource_count,
    }


def _summary_block(result: AnalysisResult) -> dict[str, Any]:
    gaps = index_gaps(result.project.errors)
    duration = analysis_duration(result)
    return {
        "classes": result.project.class_count,
        "methods": result.project.method_count,
        # The indexed call edges. The key keeps its name; the number it holds
        # is the edges now, which is what the cross-reference table holds.
        "cross_references": result.project.reference_count,
        # The two units of the index, each under its own name. The call sites
        # are the places in the bytecode where a call happens; the call edges
        # are the relationships between two methods. One method that calls the
        # same target twice is one edge and two sites.
        "call_sites": result.call_site_count,
        "call_edges": result.project.reference_count,
        # The strings the resource table declared. A separate number from the
        # DEX string pool, because they are separate things: one is what the
        # code loads, the other is what a person wrote.
        "resource_strings": result.project.resource_count,
        # How many of those cross-references are backed by an evidence record.
        # The unit is the call edge: one record covers every call site of the
        # method it is about, so the edges the records cover are the indexed
        # cross-references that have a record behind them. The two numbers
        # differ on purpose: an indexed call into library code is a fact about
        # the JDK, not a conclusion about this app.
        "cross_references_with_evidence": cross_reference_edge_count(result.evidence),
        # The same records counted the other way: the places in the bytecode
        # the covered calls were read from.
        "call_sites_with_evidence": cross_reference_site_count(result.evidence),
        "call_edges_with_evidence": cross_reference_edge_count(result.evidence),
        # The number of records themselves — one per called method of this APK.
        # It is a different number about a different thing, and it is stated
        # next to the other one so that neither can be read as the other.
        "cross_reference_records": cross_reference_records(result.evidence),
        "evidence_by_level": _evidence_counts(result.evidence),
        # How much of the indexed code the decompiler turned into Java. It is
        # what the ``decompiled`` flag on a method means, counted.
        "decompilation": decompilation_coverage(result.evidence),
        # Whether the index covers the whole APK. Every count above is a count
        # of what was indexed; a reader who does not know the index is short
        # reads them as counts of what the APK holds.
        "index_complete": not gaps,
        "index_gaps": [
            {"tool": gap.tool, "code": gap.code.value, "message": gap.message} for gap in gaps
        ],
        # How long the analysis took, or null when it was never timed. A
        # report that states 0.0 seconds for a run nobody timed states a
        # measurement that was never made.
        "duration_seconds": None if duration is None else round(duration, 2),
        "backends_with_errors": sorted({e.tool for e in result.project.errors}),
    }


def _evidence_counts(evidence: list[Evidence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence:
        counts[item.level.value] = counts.get(item.level.value, 0) + 1
    return counts


__all__ = ["build_json_report"]
