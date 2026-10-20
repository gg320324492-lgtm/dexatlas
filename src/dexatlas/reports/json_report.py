"""JSON report — the machine-readable form, and the CLI/API's shared shape."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dexatlas.core.models import Evidence, EvidenceKind, Project, index_gaps
from dexatlas.core.paths import display_path
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.reports.coverage import decompilation_coverage


def build_json_report(result: AnalysisResult) -> dict[str, Any]:
    """Assemble the full analysis as a serializable document.

    Backend failures are included in ``errors`` rather than omitted: a report that hides
    which steps did not run is exactly the report that gets over-trusted.
    """
    project = result.project
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "project": _project_block(project),
        "tools": project.tool_versions,
        "errors": [e.model_dump(mode="json") for e in project.errors],
        "manifest": result.manifest.model_dump(mode="json") if result.manifest else None,
        "evidence": [e.model_dump(mode="json") for e in result.evidence],
        "summary": _summary_block(result),
    }


def _project_block(project: Project) -> dict[str, Any]:
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
        "evidence_count": project.evidence_count,
        "resource_count": project.resource_count,
    }


def _summary_block(result: AnalysisResult) -> dict[str, Any]:
    gaps = index_gaps(result.project.errors)
    return {
        "classes": result.project.class_count,
        "methods": result.project.method_count,
        "cross_references": result.project.reference_count,
        # The strings the resource table declared. A separate number from the
        # DEX string pool, because they are separate things: one is what the
        # code loads, the other is what a person wrote.
        "resource_strings": result.project.resource_count,
        # How many of those cross-references are backed by an evidence record.
        # The two numbers differ on purpose: an indexed call into library code
        # is a fact about the JDK, not a conclusion about this app.
        "cross_references_with_evidence": sum(
            1 for item in result.evidence if item.kind == EvidenceKind.CROSS_REFERENCE
        ),
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
        "duration_seconds": round(result.duration_seconds, 2),
        "backends_with_errors": sorted({e.tool for e in result.project.errors}),
    }


def _evidence_counts(evidence: list[Evidence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence:
        counts[item.level.value] = counts.get(item.level.value, 0) + 1
    return counts


__all__ = ["build_json_report"]
