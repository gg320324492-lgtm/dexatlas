"""Report rendering.

Checks that the report never overstates what was established: backend errors must be
visible, and unverified levels must not be presented as findings.
"""

from __future__ import annotations

import json
from pathlib import Path

from dexatlas.core.models import (
    ApkMetadata,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    ManifestComponent,
    ManifestInfo,
    Project,
    ProjectStatus,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown


def _project() -> Project:
    project = Project.create(ApkMetadata(sha256="c" * 64, size_bytes=2048, path=Path("demo.apk")))
    project.status = ProjectStatus.COMPLETED
    project.class_count = 120
    project.method_count = 940
    project.reference_count = 3100
    project.evidence_count = 2
    project.tool_versions = {"jadx": "1.5.2", "apktool": "2.11.1", "androguard": None}
    return project


def _evidence(level: EvidenceLevel, summary: str) -> Evidence:
    return Evidence(
        id="E-0001",
        kind=EvidenceKind.OBSERVATION,
        level=level,
        summary=summary,
        provenance=[
            Provenance(
                tool="androguard", tool_version="4.1", apk_sha256="c" * 64, locator="classes.dex"
            )
        ],
    )


def _cross_reference(
    summary: str = "com.a.Crypto.sign()V is called from 1 location(s)",
) -> Evidence:
    return Evidence(
        id="E-0002",
        kind=EvidenceKind.CROSS_REFERENCE,
        level=EvidenceLevel.VERIFIED,
        summary=summary,
        provenance=[
            Provenance(
                tool="androguard", tool_version="4.1", apk_sha256="c" * 64, locator="classes.dex"
            )
        ],
    )


def _decompilation(decompiled: int = 6, total: int = 8) -> Evidence:
    """The record an analysis leaves behind about what the decompiler could read."""
    return Evidence(
        id="E-0003",
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary=f"jadx produced real Java for {decompiled} of {total} methods",
        provenance=[
            Provenance(
                tool="jadx", tool_version="1.5.2", apk_sha256="c" * 64, locator="jadx:sources"
            )
        ],
        detail={"decompilation": {"methods_decompiled": decompiled, "methods_total": total}},
    )


def _result(
    evidence: list[Evidence] | None = None,
    manifest: ManifestInfo | None = None,
    errors: list[ToolError] | None = None,
) -> AnalysisResult:
    project = _project()
    project.errors = errors or []
    return AnalysisResult(
        project=project,
        manifest=manifest,
        evidence=evidence if evidence is not None else [_evidence(EvidenceLevel.VERIFIED, "ok")],
        duration_seconds=3.5,
    )


# -- JSON -------------------------------------------------------------------


def test_json_report_is_serialisable() -> None:
    report = build_json_report(_result())

    assert json.loads(json.dumps(report))["schema_version"] == 1


def test_json_report_includes_backend_errors() -> None:
    """A report that hides which steps did not run is the report that gets over-trusted."""
    result = _result(
        errors=[
            ToolError(tool="jadx", code=ToolErrorCode.TIMEOUT, message="exceeded its 900s timeout")
        ]
    )

    report = build_json_report(result)

    assert report["errors"][0]["tool"] == "jadx"
    assert report["summary"]["backends_with_errors"] == ["jadx"]


def test_json_report_counts_evidence_by_level() -> None:
    result = _result(
        evidence=[
            _evidence(EvidenceLevel.VERIFIED, "a"),
            _evidence(EvidenceLevel.VERIFIED, "b"),
            _evidence(EvidenceLevel.LEAD, "c"),
        ]
    )

    report = build_json_report(result)

    assert report["summary"]["evidence_by_level"] == {"verified": 2, "lead": 1}


def test_json_report_carries_provenance_for_each_evidence_record() -> None:
    report = build_json_report(_result())

    assert report["evidence"][0]["provenance"][0]["tool"] == "androguard"
    assert report["evidence"][0]["provenance"][0]["locator"] == "classes.dex"


def test_json_report_tells_indexed_cross_references_from_evidence() -> None:
    """Two numbers that look alike must not be mistaken for each other.

    An indexed cross-reference is a fact about the bytecode; a cross-reference
    record is a conclusion about this app's own methods.
    """
    result = _result(evidence=[_cross_reference()])

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == 3100
    assert summary["cross_references_with_evidence"] == 1


# -- Markdown ---------------------------------------------------------------


def test_markdown_reports_identity_and_counts() -> None:
    report = render_markdown(_result())

    assert "apk_c" in report
    assert "c" * 64 in report
    assert "120" in report


def test_markdown_surfaces_backend_errors() -> None:
    result = _result(
        errors=[
            ToolError(
                tool="jadx", code=ToolErrorCode.NOT_INSTALLED, message="jadx is not installed"
            )
        ]
    )

    report = render_markdown(result)

    assert "Backend errors" in report
    assert "jadx is not installed" in report
    assert "not_installed" in report


def test_markdown_explains_each_evidence_level() -> None:
    report = render_markdown(_result())

    assert "verified" in report
    assert "lead" in report
    assert "insufficient" in report


def test_markdown_lists_exported_components() -> None:
    manifest = ManifestInfo(
        package="com.example.demo",
        components=[
            ManifestComponent(kind="activity", name="com.example.Main", exported=True),
            ManifestComponent(kind="service", name="com.example.Hidden", exported=False),
        ],
    )

    report = render_markdown(_result(manifest=manifest))

    assert "Exported components" in report
    assert "com.example.Main" in report
    assert "com.example.Hidden" not in report.split("Exported components")[1].split("\n\n")[0]


def test_markdown_does_not_present_leads_as_confirmed() -> None:
    result = _result(evidence=[_evidence(EvidenceLevel.LEAD, "possible hardcoded key")])

    report = render_markdown(result)

    assert "possible hardcoded key" in report
    assert "`lead`" in report
    assert "not confirmed findings" in report


def test_markdown_handles_a_report_with_no_evidence() -> None:
    report = render_markdown(_result(evidence=[]))

    assert "No evidence records" in report


def test_markdown_escapes_pipes_in_summaries() -> None:
    """An unescaped pipe would break the evidence table's column alignment."""
    result = _result(evidence=[_evidence(EvidenceLevel.VERIFIED, "value is a|b")])

    report = render_markdown(result)

    assert r"a\|b" in report


def test_markdown_records_missing_backends() -> None:
    report = render_markdown(_result())

    assert "androguard not installed" in report


def test_markdown_tells_indexed_cross_references_from_evidence() -> None:
    result = _result(evidence=[_cross_reference()])

    report = render_markdown(result)

    assert "| Cross-references indexed | 3,100 |" in report
    assert "| Cross-references with evidence | 1 |" in report


def test_markdown_explains_which_cross_references_become_evidence() -> None:
    """A report that shows 13 cross-references and no record of one of them
    looks broken. The rule has to be written down where the records are."""
    report = render_markdown(_result(evidence=[_cross_reference()]))

    assert "method of this APK" in report


# -- decompilation coverage --------------------------------------------------


def test_markdown_states_how_much_of_the_code_was_decompiled() -> None:
    """The report says how much of the indexed code can be read as Java.

    The flag on a method means exactly that, so the report has to give the
    number behind it.
    """
    report = render_markdown(_result(evidence=[_decompilation()]))

    assert "| Methods decompiled by JADX | 6 of 8 |" in report


def test_a_report_without_a_decompiler_says_nothing_about_decompilation() -> None:
    """No decompiler means no coverage — not zero coverage."""
    report = render_markdown(_result())

    assert "Methods decompiled" not in report


def test_json_report_states_how_much_of_the_code_was_decompiled() -> None:
    report = build_json_report(_result(evidence=[_decompilation()]))

    coverage = report["summary"]["decompilation"]
    assert coverage["methods_decompiled"] == 6
    assert coverage["methods_total"] == 8


def test_json_report_leaves_decompilation_unset_without_a_decompiler() -> None:
    report = build_json_report(_result())

    assert report["summary"]["decompilation"] is None
