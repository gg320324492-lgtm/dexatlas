"""The tools that trace the calls between methods."""

from __future__ import annotations

from dexatlas.core.calls import CallSite
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import unknown_project
from dexatlas.mcp.schemas import CalleeView, CallerView, CallSiteView, SymbolView


def _view(site: CallSite) -> CallSiteView:
    """One call site, as a reader would want to know it."""
    return CallSiteView(
        caller=site.caller,
        callee=site.callee,
        kind=site.kind.value,
        dex_name=site.dex_name,
        instruction_offset=site.instruction_offset,
        provenance=[entry.locator for entry in site.provenance],
    )


def _edge_count(sites: list[CallSite]) -> int:
    """How many relationships the sites make.

    An edge is the caller, the callee and the way the call is made, so one
    caller that calls the same target twice contributes one edge.
    """
    return len({(site.caller, site.callee, site.kind) for site in sites})


def find_callers(
    analyzer: Analyzer,
    project_id: str,
    method_id: str,
    *,
    limit: int,
) -> CallerView:
    """Who calls a method, and where in the bytecode the calls are."""
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)

    sites = analyzer.store.get_method_references(project_id, method_id)
    page = sites[:limit]

    return CallerView(
        call_sites=[_view(site) for site in page],
        call_site_count=len(sites),
        call_edge_count=_edge_count(sites),
        truncated=len(sites) > len(page),
    )


def find_callees(
    analyzer: Analyzer,
    project_id: str,
    method_id: str,
    *,
    limit: int,
) -> CalleeView:
    """What a method calls, and where in the bytecode the calls are."""
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)

    sites = analyzer.store.list_callees(project_id, method_id)
    page = sites[:limit]

    callees: list[SymbolView] = []
    seen: set[str] = set()
    for site in page:
        if site.callee in seen:
            continue
        seen.add(site.callee)
        callees.append(
            SymbolView(
                kind="method",
                name=site.callee,
                detail=site.kind.value,
                provenance=[entry.locator for entry in site.provenance],
            )
        )

    return CalleeView(
        callees=callees,
        call_site_count=len(sites),
        call_edge_count=_edge_count(sites),
        truncated=len(sites) > len(page),
    )


__all__ = ["find_callees", "find_callers"]
