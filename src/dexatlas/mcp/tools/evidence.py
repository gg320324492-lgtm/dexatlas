"""The tools that hand back the evidence and the places it was read from."""

from __future__ import annotations

from pathlib import Path

from dexatlas.core.locators import LocatorResolver
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import unknown_project
from dexatlas.mcp.schemas import EvidenceView, LocatorResolution
from dexatlas.mcp.security import excerpt, source_kind


def get_evidence(analyzer: Analyzer, project_id: str, evidence_id: str) -> EvidenceView:
    """One evidence record, and the places it was read from.

    The record is a conclusion; the provenance is where a reader goes to
    check it. A record without its provenance is a claim, and this project
    does not make claims it cannot show the receipts for.
    """
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)

    record = analyzer.store.get_evidence(project_id, evidence_id)
    if record is None:
        raise unknown_project(project_id)

    return EvidenceView(
        id=record.id,
        kind=record.kind.value,
        level=record.level.value,
        summary=record.summary,
        detail=dict(record.detail),
        provenance=[entry.locator for entry in record.provenance],
    )


def resolve_locator(analyzer: Analyzer, project_id: str, locator: str) -> LocatorResolution:
    """Resolve a provenance locator into the source it names.

    The answer says whether the locator resolved, and why it did not when
    it did not: "the decompiler was not installed" and "that file is not in
    this analysis" are different facts, and a caller that cannot tell them
    apart will report a missing place as an absent one.
    """
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise unknown_project(project_id)

    workspace = analyzer.store.get_workspace(project_id)
    if workspace is None:
        return LocatorResolution(
            resolved=False,
            reason="this analysis wrote no workspace, so it holds no source to resolve into",
        )

    resolver = LocatorResolver(Path(workspace), dex_files=project.apk.dex_files)
    resolution = resolver.resolve(locator)

    if not resolution.ok:
        return LocatorResolution(resolved=False, reason=resolution.detail)

    # A locator can resolve to a *symbol* rather than to a file: the DEX
    # reader names a place in the APK's own bytecode, and there is no file to
    # read for it. That is a resolved locator with nothing to show, not a
    # missing one, and a caller that cannot tell them apart will report a
    # place that exists as one that does not.
    if resolution.path is None:
        return LocatorResolution(
            resolved=True,
            reason=resolution.detail,
            provenance=[locator],
        )

    return LocatorResolution(
        resolved=True,
        reason=resolution.detail,
        kind=source_kind(resolution.path),
        text=excerpt(resolution.path, Path(workspace)),
        provenance=[locator],
    )


__all__ = ["get_evidence", "resolve_locator"]
