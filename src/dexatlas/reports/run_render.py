"""Render one recorded run to a reviewable directory.

A run is one attempt at analysing an APK. Its published snapshot lives in the
workspace database; its own directory holds the decompiled trees. ``dexatlas
render`` turns one run's record into a directory a reader can archive, diff or
hand to someone else — the reports that describe that run, the same evidence
package ``export`` writes (an archive a reader can verify offline), and the
run record itself, so the attempt's identity travels with its output.

This is a *rendering*, not an analysis: every file is read out of the
workspace. The command adds no new facts and runs no backend. A run that
never published — a failed or cancelled attempt — has a record worth reading
(it says what went wrong), but it has no snapshot to render, so the command
refuses it rather than dressing up an empty answer.
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Any

from dexatlas.core.paths import redact_workspace
from dexatlas.core.runs import RunStatus
from dexatlas.reports.evidence_package import (
    MANIFEST_NAME,
    EvidencePackageError,
    package_contents,
    package_manifest,
    verify_citations,
    verify_package,
)

logger = logging.getLogger(__name__)

#: Where the evidence archive lands inside the render directory.
EVIDENCE_ARCHIVE = "evidence/evidence-package.zip"

#: Where the run's own record lands inside the render directory.
RUN_RECORD = "run.json"


class RunRenderError(ValueError):
    """The run cannot be rendered as asked.

    A run that never published has a record but no snapshot: rendering it
    would mean inventing reports that describe nothing. The error says which
    run was refused and why, so the caller can pick a run that did finish.
    """


def render_run(analyzer: Any, project_id: str, run_id: str, target: Path) -> dict[str, Any]:
    """Write one run's reports, evidence package and record under ``target``.

    Everything is read out of the workspace; no analysis runs. The report is
    the one the run's own snapshot describes — the same reconstruction the
    REST API's export uses — so rendering a run that is not the published
    one shows that run's snapshot, not the project's current one.

    The returned summary names what was written, so the caller can print it
    without re-reading the directory.
    """
    from dexatlas.api.app import _rebuild_result

    store = analyzer.store
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise RunRenderError(f"no run {run_id!r} for project {project_id!r}")
    if run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.CANCELLED}:
        raise RunRenderError(
            f"run {run_id} ended as {run.status.value} and published nothing to render; "
            "render a run that completed"
        )
    if run.status is RunStatus.FAILED:
        # A failed run recorded what went wrong, but it published no snapshot
        # either: the project's tables hold the *published* run's rows. There
        # is nothing here to render, and inventing an empty report would be
        # worse than saying so.
        raise RunRenderError(
            f"run {run_id} failed and published nothing to render; "
            "its error record is in `dexatlas runs` and in the project's errors"
        )

    # The report describes the snapshot this run published. `_rebuild_result`
    # reads the published snapshot of the project; the run that published it
    # is the one the project points at, so a run that is not published has no
    # snapshot of its own in the project tables — but it did publish, so the
    # published snapshot *is* its snapshot only while nothing newer replaced
    # it. Rendering therefore answers from the project's snapshot and names
    # the run that produced it; a run whose snapshot has since been replaced
    # is refused below, because its rows are no longer in the workspace.
    published = store.get_published_run_id(project_id)
    if published != run_id:
        raise RunRenderError(
            f"run {run_id} is not the published run of {project_id} "
            f"(published: {published}); its snapshot has been replaced and its "
            "rows are no longer in the workspace. Re-run the analysis, or render "
            "the published run."
        )

    result = _rebuild_result(analyzer, project_id)
    # The report must name the run it describes. A snapshot whose recorded run
    # is another run cannot be rendered as this one: that would be a report
    # wearing the wrong attempt's name.
    if result.run is not None and result.run.id != run_id:
        raise RunRenderError(
            f"the published snapshot was produced by run {result.run.id}, not {run_id}"
        )

    target.mkdir(parents=True, exist_ok=True)

    # -- the run's own record --------------------------------------------
    # The attempt's identity and its errors, redacted the way every other
    # published surface redacts them: the message may quote a path the
    # analysis was handed, and that path is this machine's.
    settings = analyzer.settings
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run.id,
        "project_id": run.project_id,
        "apk_sha256": run.apk_sha256,
        "status": run.status.value,
        "completeness": run.completeness.value,
        "tool_versions": run.tool_versions,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_seconds": run.duration_seconds,
        "published": True,
        "errors": [
            {
                "tool": error.tool,
                "code": error.code.value,
                "message": redact_workspace(error.message, settings.workspace),
                "detail": (
                    redact_workspace(error.detail, settings.workspace) if error.detail else None
                ),
            }
            for error in run.errors
        ],
    }
    (target / RUN_RECORD).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # -- the reports and the evidence package -----------------------------
    # The package is the same one `export` writes: the three report formats,
    # the evidence records, the cited source fragments, and a manifest that
    # hashes every file. The archive is written to a scratch path beside the
    # target and verified before it is named done — a render that ships an
    # unverifiable package is not a render.
    files = package_contents(analyzer, project_id)
    manifest = package_manifest(analyzer, project_id, files)
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

    archive_path = target / EVIDENCE_ARCHIVE
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    scratch = archive_path.with_name(archive_path.name + ".building")

    try:
        with zipfile.ZipFile(scratch, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, content in sorted(files.items()):
                archive.writestr(path, content)
            archive.writestr(MANIFEST_NAME, manifest_bytes)
        scratch.replace(archive_path)

        # The archive a render leaves behind is one a reader can verify:
        # hashing and citation checks run here, before the command claims
        # success. A mismatch is a defect of this tree, not of the reader's
        # copy, and it fails here rather than in the reader's hands.
        checked = verify_package(archive_path)
        citation_report = verify_citations(archive_path, checked)
    except EvidencePackageError as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise RunRenderError(f"the rendered package failed its own verification: {exc}") from exc

    summary: dict[str, Any] = {
        "run_id": run_id,
        "project_id": project_id,
        "target": target,
        "manifest": manifest,
        "citation_report": citation_report,
    }
    return summary


def render_run_summary_lines(summary: dict[str, Any]) -> list[str]:
    """What the CLI prints after a render, as lines.

    The counts come from the manifest and the citation report, not from the
    files on disk: a count taken from a directory listing after the fact is
    a count of what happened to still be there.
    """
    manifest = summary["manifest"]
    files = manifest.get("files", [])
    reports = sum(1 for entry in files if entry.get("role") == "report")
    sources = sum(1 for entry in files if entry.get("role") == "evidence_source")
    citations = summary.get("citation_report", {})
    unresolved = citations.get("citations_unresolved") or []
    lines = [
        f"run {summary['run_id']} of {summary['project_id']} rendered",
        f"  reports: {reports} (report.md, report.json, report.html)",
        f"  evidence package: {EVIDENCE_ARCHIVE} ({len(files)} listed files + {MANIFEST_NAME})",
        f"  source fragments packaged: {sources}",
        f"  citations unresolved: {len(unresolved)}",
    ]
    for item in unresolved:
        lines.append(f"    {item}")
    return lines
