"""The offline HTML report — the rendering a client reads without installing anything.

One analysis, three renderings. This one reads the same
:class:`~dexatlas.core.pipeline.AnalysisResult` the Markdown and JSON renderers
read, and it computes no fact of its own: every number and every record comes
from the shared data layer (`reports/summary.py` and the models).

The page is offline in the strict sense: no script runs, no resource is
fetched, no style is loaded from anywhere. Everything the analysis did not
establish — sample strings, class names, tool versions, error messages — is
escaped before it reaches the page, so a hostile APK cannot write markup into
the reader's browser.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from html import escape

from dexatlas.core.models import (
    Evidence,
    EvidenceLevel,
    ManifestInfo,
    Project,
    ToolError,
    cross_reference_records,
    index_gaps,
)
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.core.runs import AnalysisRun
from dexatlas.reports.summary import summary_metrics, tool_line

#: What a cross-reference record is, said where the records are.
_XREF_NOTE = (
    "A cross-reference record is made for a method of this APK that is called from "
    "elsewhere. Calls into library code are indexed as cross-references but are not "
    "evidence: they say something about the JDK, not about this app. One record "
    "covers every call site of the method it is about, so the call sites the records "
    "cover add up to more than the number of records."
)

_LEVEL_NOTE = {
    EvidenceLevel.VERIFIED: (
        "Deterministically established by an analysis tool, with a citation that "
        "resolves inside this analysis."
    ),
    EvidenceLevel.LEAD: "Risk indicator only. Not a confirmed issue.",
    EvidenceLevel.INSUFFICIENT: "Not enough evidence either way; needs human review.",
}

#: The evidence table shows this many rows, like the Markdown report's table.
#: A capped table says what it left out — a table that says nothing reads as
#: the whole.
_MAX_EVIDENCE_ROWS = 200

#: Styles that travel inside the file. No stylesheet is fetched: the page has
#: to render on a machine with no network and no DexAtlas.
_STYLE = """\
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem;
       padding: 0 1rem; color: #1a1a2e; background: #fafafa; }
h1 { border-bottom: 2px solid #4a5568; padding-bottom: .3rem; }
h2 { border-bottom: 1px solid #cbd5e0; margin-top: 2rem; padding-bottom: .2rem; }
table { border-collapse: collapse; margin: .8rem 0; width: 100%; }
th, td { border: 1px solid #cbd5e0; padding: .35rem .6rem; text-align: left;
         vertical-align: top; }
th { background: #edf2f7; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
code { background: #edf2f7; padding: 0 .25rem; border-radius: 3px;
       overflow-wrap: anywhere; }
.note { background: #fffaf0; border-left: 4px solid #ecc94b; padding: .5rem .8rem;
        margin: .8rem 0; }
.error { background: #fff5f5; border-left: 4px solid #c53030; padding: .5rem .8rem;
         margin: .8rem 0; }
footer { border-top: 1px solid #cbd5e0; color: #4a5568; font-size: .9rem;
         margin-top: 2rem; padding-top: .8rem; }
dl.meta { display: grid; grid-template-columns: max-content 1fr; gap: .2rem 1rem; }
dl.meta dt { font-weight: 600; }
dl.meta dd { margin: 0; overflow-wrap: anywhere; }
"""


def render_html(result: AnalysisResult) -> str:
    """Render an analysis as a self-contained HTML page.

    The facts are the shared data layer's; the page is only how they look.
    Every string the analysis did not produce — which is every string — is
    escaped on its way in.
    """
    project = result.project
    run = result.run

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>DexAtlas analysis report — ",
        escape(project.id),
        "</title>",
        "<style>",
        _STYLE,
        "</style>",
        "</head>",
        "<body>",
        "<h1>DexAtlas analysis report</h1>",
        *_meta_section(project, run),
        "<h2>Summary</h2>",
        _metrics_table(result),
    ]

    if result.latest_attempt_status is not None:
        parts += _later_attempt_note(result.latest_attempt_status.value)
    if cross_reference_records(result.evidence):
        parts.append(f'<p class="note">{escape(_XREF_NOTE)}</p>')
    if index_gaps(project.errors):
        parts.append(
            '<p class="note"><strong>This index is incomplete.</strong> The counts above '
            "cover the parts of the APK that could be read, not the whole of it. Read "
            "them as counts of what was indexed, not as counts of what the APK holds."
            "</p>"
        )

    parts += ["<h2>Tools</h2>", f"<p>{escape(tool_line(project))}</p>"]
    parts += _levels_section(result.evidence)
    parts += _errors_section(project.errors)
    if result.manifest is not None:
        parts += _manifest_section(result.manifest)
    parts += _evidence_section(result.evidence)
    parts += _footer()

    parts += ["</body>", "</html>", ""]
    return "\n".join(parts)


def _meta_section(project: Project, run: AnalysisRun | None) -> list[str]:
    """The identity of the analysis: project, APK, hash, run."""
    rows = [
        ("Project", f"<code>{escape(project.id)}</code>"),
        ("APK", f"<code>{escape(project.apk.path.name)}</code>"),
        ("SHA-256", f"<code>{escape(project.apk.sha256)}</code>"),
        ("Status", escape(project.status.value)),
    ]
    if run is not None:
        rows.append(
            (
                "Run",
                f"<code>{escape(run.id)}</code> ({escape(run.status.value)}, "
                f"{escape(run.completeness.value)})",
            )
        )
    items = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    return [f'<dl class="meta">{items}</dl>']


def _metrics_table(result: AnalysisResult) -> str:
    """The shared metrics, in the shared order, as a table."""
    rows = "".join(
        f"<tr><th scope='row'>{escape(name)}</th><td class='num'>{escape(value)}</td></tr>"
        for name, value in summary_metrics(result)
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _later_attempt_note(status: str) -> list[str]:
    """What a later attempt that published nothing means for this report.

    The report describes the *published* snapshot, and a later attempt that
    failed does not change what that snapshot holds. It is still a fact about
    the APK's current state, and a page that said "completed" without saying
    so would be stating the status of the snapshot as if it were the status
    of the project.
    """
    return [
        '<p class="note"><strong>A later attempt to analyse this APK ended as '
        f"<code>{escape(status)}</code>.</strong> The report below describes the "
        "<em>published</em> run — the last one that completed — and every number and "
        "every piece of evidence in it comes from that run. The later attempt "
        "published nothing, and it changed no number in this report.</p>"
    ]


def _levels_section(evidence: list[Evidence]) -> list[str]:
    counts = Counter(e.level.value for e in evidence)
    rows = "".join(
        f"<tr><td><code>{escape(level.value)}</code></td>"
        f"<td class='num'>{counts.get(level.value, 0)}</td>"
        f"<td>{escape(meaning)}</td></tr>"
        for level, meaning in _LEVEL_NOTE.items()
    )
    return ["<h2>Evidence levels</h2>", f"<table><tbody>{rows}</tbody></table>"]


def _errors_section(errors: Sequence[ToolError]) -> list[str]:
    """The steps that did not complete, named where their results would be.

    Results that depend on them are absent, not clean; a page that hid them
    would be the page that gets over-trusted.
    """
    if not errors:
        return []
    items = "".join(
        f"<li><strong>{escape(error.tool)}</strong> (<code>{escape(error.code.value)}</code>): "
        f"{escape(error.message)}"
        + (f" — {escape(error.detail)}" if error.detail else "")
        + "</li>"
        for error in errors
    )
    return [
        '<div class="error"><h2 style="border: none; margin-top: 0;">Backend errors</h2>',
        "<p>These steps did not complete. Results that depend on them are absent, not clean.</p>",
        f"<ul>{items}</ul></div>",
    ]


def _manifest_section(manifest: ManifestInfo) -> list[str]:
    parts = ["<h2>Manifest</h2>"]
    rows = [
        ("Package", f"<code>{escape(manifest.package or '-')}</code>"),
        (
            "Version",
            f"<code>{escape(manifest.version_name or '-')}</code> "
            f"(code <code>{escape(manifest.version_code or '-')}</code>)",
        ),
        (
            "minSdk / targetSdk",
            f"<code>{escape(manifest.min_sdk or '-')}</code> / "
            f"<code>{escape(manifest.target_sdk or '-')}</code>",
        ),
        ("Permissions", str(len(manifest.permissions))),
        ("Components", str(len(manifest.components))),
    ]
    items = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    parts.append(f'<dl class="meta">{items}</dl>')

    exported = manifest.exported_components
    if exported:
        component_rows = "".join(
            f"<tr><td>{escape(c.kind)}</td><td><code>{escape(c.name)}</code></td>"
            f"<td><code>{escape(c.permission or '-')}</code></td></tr>"
            for c in exported
        )
        parts += [
            "<h3>Exported components</h3>",
            "<table><thead><tr><th>Kind</th><th>Name</th><th>Permission</th></tr>"
            f"</thead><tbody>{component_rows}</tbody></table>",
        ]

    if manifest.permissions:
        items = "".join(f"<li><code>{escape(p.name)}</code></li>" for p in manifest.permissions)
        parts += ["<h3>Permissions</h3>", f"<ul>{items}</ul>"]
    return parts


def _evidence_section(evidence: list[Evidence]) -> list[str]:
    parts = ["<h2>Evidence</h2>", f'<p class="note">{escape(_XREF_NOTE)}</p>']
    if not evidence:
        parts.append("<p><em>No evidence records were produced.</em></p>")
        return parts

    shown = evidence[:_MAX_EVIDENCE_ROWS]
    omitted = evidence[_MAX_EVIDENCE_ROWS:]

    if omitted:
        kinds = Counter(item.kind.value for item in omitted)
        breakdown = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
        parts.append(
            f'<p class="note"><strong>The table below is capped at {_MAX_EVIDENCE_ROWS} '
            f"rows.</strong> {len(omitted)} further evidence records omitted "
            f"({escape(breakdown)}). The count in the summary above is the whole "
            "count; this table is not the whole of the evidence.</p>"
        )

    rows = []
    for item in shown:
        source = item.provenance[0].ref() if item.provenance else "-"
        rows.append(
            f"<tr><td><code>{escape(item.id)}</code></td>"
            f"<td><code>{escape(item.level.value)}</code></td>"
            f"<td>{escape(item.kind.value)}</td>"
            f"<td>{escape(item.summary)}</td>"
            f"<td><code>{escape(source)}</code></td></tr>"
        )
    parts += [
        "<table><thead><tr><th>ID</th><th>Level</th><th>Kind</th><th>Summary</th>"
        f"<th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    ]
    if omitted:
        parts.append(f"<p><em>{len(omitted)} further evidence records omitted.</em></p>")
    return parts


def _footer() -> list[str]:
    return [
        "<footer>",
        "<p>Generated by DexAtlas — an evidence-first Android analysis platform.</p>",
        "<p>This report describes only what was deterministically established by the "
        "analysis tools listed above, and a verified record's citation resolves inside "
        "the analysis this report describes. Items marked <code>lead</code> or "
        "<code>insufficient</code> are not confirmed findings and require human "
        "validation.</p>",
        "</footer>",
    ]


__all__ = ["render_html"]
