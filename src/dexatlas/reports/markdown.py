"""Markdown report - the human-readable form.

Written so a reader can check any claim without opening a database: every row carries
its evidence id, and every evidence entry carries its source tool, version and locator.
"""

from __future__ import annotations

from collections import Counter

from dexatlas.core.models import (
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    ManifestInfo,
    Project,
    ProjectStatus,
    cross_reference_call_sites,
    cross_reference_records,
    index_gaps,
)
from dexatlas.core.pipeline import AnalysisResult, analysis_duration
from dexatlas.reports.coverage import decompilation_coverage

_LEVEL_NOTE = {
    EvidenceLevel.VERIFIED: "Deterministically established by an analysis tool.",
    EvidenceLevel.LEAD: "Risk indicator only. Not a confirmed issue.",
    EvidenceLevel.INSUFFICIENT: "Not enough evidence either way; needs human review.",
}

_MAX_EVIDENCE_ROWS = 200

#: What a cross-reference record is, said where the records are.
_XREF_NOTE = (
    "A cross-reference record is made for a method of this APK that is called from "
    "elsewhere. Calls into library code are indexed as cross-references but are not "
    "evidence: they say something about the JDK, not about this app. One record "
    "covers every call site of the method it is about, so the call sites the records "
    "cover add up to more than the number of records."
)

#: What the three cross-reference numbers count, said where they are.
#:
#: They are three numbers about three different things, and they are printed
#: next to each other. A reader who takes them for the same thing reads a
#: ratio out of them that is not there: "3 of 23 cross-references have
#: evidence" is a claim about the same 23 that the third number contradicts.
_XREF_COUNT_NOTE = [
    "> **The cross-reference counts are three numbers about three things.** The",
    "> indexed count is the call edges the index holds, one row per call. The",
    "> count with evidence is the call sites a cross-reference record covers:",
    "> one record is made per called method of this APK, and it covers every call",
    "> site of that method. The record count is the number of those records.",
]

#: What an incomplete index means for the numbers beside it.
_INDEX_GAP_NOTE = [
    "> **This index is incomplete.** The counts above cover the parts of the APK that",
    "> could be read, not the whole of it. Read them as counts of what was indexed,",
    "> not as counts of what the APK holds.",
]


def _later_attempt_note(status: ProjectStatus) -> list[str]:
    """What a later attempt that published nothing means for this report.

    The report describes the *published* snapshot, and a later attempt that
    failed does not change what that snapshot holds. It is still a fact about
    the APK's current state, and a report that said "completed" without
    saying so would be stating the status of the snapshot as if it were the
    status of the project.
    """
    return [
        f"> **A later attempt to analyse this APK ended as `{status.value}`.** The report",
        "> below describes the *published* run — the last one that completed — and every",
        "> number and every piece of evidence in it comes from that run. The later attempt",
        "> published nothing, so it is not in this report; the project record has it.",
    ]


def _run_line(result: AnalysisResult) -> list[str]:
    """The run the report describes, named.

    A run has an identity of its own, and a report that does not name it
    cannot say which attempt its numbers come from — which matters as soon
    as there is more than one.
    """
    run = result.run
    if run is None:
        return []
    return [f"**Run:** `{run.id}` ({run.status.value}, {run.completeness.value})  "]


def render_markdown(result: AnalysisResult) -> str:
    """Render an analysis as a Markdown report."""
    project = result.project
    metrics: list[tuple[str, str]] = [
        ("Index completeness", _index_completeness(project)),
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
        ("Cross-references indexed", f"{project.reference_count:,}"),
        # The call sites the cross-reference records cover, and the number of
        # records themselves. The two are different numbers about different
        # things: one record covers every call site of the method it is about.
        ("Cross-references with evidence", f"{cross_reference_call_sites(result.evidence):,}"),
        ("Cross-reference records", f"{cross_reference_records(result.evidence):,}"),
        ("Evidence records", f"{project.evidence_count:,}"),
        ("DEX files", f"{len(project.apk.dex_files)}"),
        ("Native libraries", f"{len(project.apk.native_libraries)}"),
        ("Analysis time", _duration_cell(result)),
    ]

    lines: list[str] = [
        "# DexAtlas analysis report",
        "",
        f"**Project:** `{project.id}`  ",
        f"**APK:** `{project.apk.path.name}`  ",
        f"**SHA-256:** `{project.apk.sha256}`  ",
        f"**Status:** {project.status.value}  ",
        *(_run_line(result) or [""]),
        f"**Tool versions:** {_tool_line(project)}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines += [f"| {name} | {_cell(value)} |" for name, value in metrics]
    if result.latest_attempt_status is not None:
        lines += ["", *_later_attempt_note(result.latest_attempt_status)]
    if cross_reference_records(result.evidence):
        lines += ["", *_XREF_COUNT_NOTE]
    if index_gaps(project.errors):
        lines += ["", *_INDEX_GAP_NOTE]
    lines += [
        "",
        "## Evidence levels",
        "",
        "| Level | Count | Meaning |",
        "| --- | ---: | --- |",
    ]

    counts = Counter(e.level.value for e in result.evidence)
    for level, meaning in _LEVEL_NOTE.items():
        lines.append(f"| `{level.value}` | {counts.get(level.value, 0)} | {meaning} |")

    if project.errors:
        lines += [
            "",
            "## Backend errors",
            "",
            "> These steps did not complete. Results that",
            "> depend on them are absent, not clean.",
            "",
        ]
        lines += [f"- **{e.tool}** (`{e.code.value}`): {e.message}" for e in project.errors]

    if result.manifest is not None:
        lines += _manifest_section(result.manifest)

    lines += _evidence_section(result.evidence)

    lines += [
        "",
        "---",
        "",
        "Generated by [DexAtlas](https://github.com/gg320324492-lgtm/dexatlas) - "
        "an evidence-first Android analysis platform.",
        "",
        "This report describes only what was deterministically established by the "
        "analysis tools listed above. Items marked `lead` or `insufficient` are not "
        "confirmed findings and require human validation.",
        "",
    ]
    return "\n".join(lines)


def _tool_line(project: Project) -> str:
    if not project.tool_versions:
        return "_(none recorded)_"
    return ", ".join(
        f"{name} {version or 'not installed'}"
        for name, version in sorted(project.tool_versions.items())
    )


def _index_completeness(project: Project) -> str:
    """Whether the index covers the whole APK, and what is missing from it.

    A count of what was indexed reads as a count of what the APK holds unless
    the reader is told otherwise. "2 classes" and "2 classes, because one of
    the DEX files could not be parsed" are different claims, and the report
    has to make the second one — otherwise a reader takes the numbers as
    totals and concludes, for instance, that an APK has no internal calls.

    The reason is the error that was already recorded. The gap is not recorded
    a second time; it is pointed at.
    """
    gaps = index_gaps(project.errors)
    if not gaps:
        return "complete"
    return "incomplete: " + "; ".join(gap.message for gap in gaps)


def _cell(value: str) -> str:
    """A metric value, escaped for a Markdown table cell.

    An unescaped pipe ends the cell early and shifts every column after it.
    """
    return value.replace("|", "\\|")


def _manifest_section(manifest: ManifestInfo) -> list[str]:
    lines = [
        "",
        "## Manifest",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Package | `{manifest.package or '-'}` |",
        f"| Version | `{manifest.version_name or '-'}` (code `{manifest.version_code or '-'}`) |",
        f"| minSdk / targetSdk | `{manifest.min_sdk or '-'}` / `{manifest.target_sdk or '-'}` |",
        f"| Permissions | {len(manifest.permissions)} |",
        f"| Components | {len(manifest.components)} |",
    ]

    exported = manifest.exported_components
    if exported:
        lines += [
            "",
            "### Exported components",
            "",
            "| Kind | Name | Permission |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {c.kind} | `{c.name}` | `{c.permission or '-'}` |" for c in exported]

    if manifest.permissions:
        lines += ["", "<details><summary>Permissions</summary>", ""]
        lines += [f"- `{p.name}`" for p in manifest.permissions]
        lines += ["", "</details>"]

    return lines


def _duration_cell(result: AnalysisResult) -> str:
    """How long the analysis took — or that it is not known.

    A run that was never timed has no duration, and a report that prints
    ``0.0s`` for it states a measurement the run never made.
    """
    duration = analysis_duration(result)
    return "unknown" if duration is None else f"{duration:.1f}s"


def _is_class_declaration(item: Evidence) -> bool:
    """Whether a record is the declaration of a class.

    The class declarations are the index of the APK rather than a finding
    about it, and they are the records a truncated table drops first. The
    summary is what says which record is which: the manifest's record is
    about the package, and the exported components' record is about the
    components.
    """
    return item.kind is EvidenceKind.DECLARATION and item.summary.startswith("Class ")


def _truncation_note(total: int, shown: int, omitted: list[Evidence]) -> list[str]:
    """The note that says the evidence table is not the whole of the evidence.

    A table of two hundred rows that says nothing about the rest reads as a
    report of two hundred records. The reader has to be told while they are
    looking at the table — not in a footnote under it — how many records it
    left out and what they were.
    """
    kinds = Counter(item.kind.value for item in omitted)
    breakdown = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
    note = [
        f"> **This table is truncated.** It shows the first {shown:,} of the {total:,} "
        f"evidence records this analysis produced; the other {len(omitted):,} are not "
        f"shown ({breakdown})."
    ]
    classes = sum(1 for item in omitted if _is_class_declaration(item))
    if classes:
        note.append(
            f"> {classes:,} of them are class declarations: the index of the APK, not a "
            "finding about it. The metrics above count the whole analysis, so a class "
            "with no row here is not a class the analysis failed to find."
        )
    return note


def _evidence_section(evidence: list[Evidence]) -> list[str]:
    if not evidence:
        return ["", "## Evidence", "", "_No evidence records were produced._"]

    shown = evidence[:_MAX_EVIDENCE_ROWS]
    omitted = evidence[_MAX_EVIDENCE_ROWS:]

    lines = [
        "",
        "## Evidence",
        "",
        _XREF_NOTE,
        "",
    ]
    if omitted:
        lines += _truncation_note(len(evidence), len(shown), omitted)
        lines += [""]
    lines += [
        "| ID | Level | Kind | Summary | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in shown:
        source = item.provenance[0].ref() if item.provenance else "-"
        summary = item.summary.replace("|", "\\|")
        lines.append(
            f"| `{item.id}` | `{item.level.value}` | {item.kind.value} | {summary} | `{source}` |"
        )

    if omitted:
        lines += ["", f"_{len(omitted)} further evidence records omitted._"]

    return lines


__all__ = ["render_markdown"]
