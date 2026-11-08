"""The tools that find symbols and hand back their source."""

from __future__ import annotations

from dexatlas.core.methods import AmbiguousMethodError
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import unknown_project
from dexatlas.mcp.schemas import SourceView, SymbolList, SymbolView, UntrustedText


def search_symbols(
    analyzer: Analyzer,
    project_id: str,
    query: str,
    *,
    limit: int,
    offset: int,
) -> SymbolList:
    """Find the indexed symbols that mention a phrase.

    The search runs over the whole index — classes, methods, fields and
    strings — and the excerpt is the index's own text around the match, so
    it says why a symbol matched.
    """
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)

    # The store takes a limit and not an offset, so the page is cut from a
    # longer read. Reading `offset + limit` rows and slicing them keeps the
    # paging honest: the total is what the index holds, not what this page
    # happens to show.
    found = analyzer.store.search(project_id, query, limit=offset + limit)
    page = found[offset : offset + limit]

    return SymbolList(
        symbols=[
            SymbolView(
                kind=str(entry.get("kind", "")),
                name=str(entry.get("name", "")),
                detail=str(entry.get("excerpt", "")),
                provenance=[],
            )
            for entry in page
        ],
        total=len(found),
        offset=offset,
        limit=limit,
    )


def class_source(analyzer: Analyzer, project_id: str, class_name: str) -> SourceView:
    """One class's source, and where it was read from."""
    document = analyzer.class_source_document(project_id, class_name)
    if document is None:
        return SourceView(
            found=False,
            reason=(
                "this analysis holds no source for that class: either the class is not "
                "in the APK, or no backend that could produce source was available"
            ),
        )
    return SourceView(
        found=True,
        kind=document.kind.value,
        text=UntrustedText(text=document.text),
        provenance=[entry.locator for entry in document.provenance],
    )


def method_source(
    analyzer: Analyzer,
    project_id: str,
    class_name: str,
    method_name: str,
    descriptor: str | None = None,
) -> SourceView:
    """One method's source — the exact one, when the name is ambiguous.

    A name that matches several methods is answered with the candidates
    rather than with one of them: the body of the wrong overload reads
    exactly like the body of the right one, and it travels straight into
    whatever quotes it.
    """
    try:
        document = analyzer.method_source_document(project_id, class_name, method_name, descriptor)
    except AmbiguousMethodError as ambiguity:
        return SourceView(
            found=False,
            reason=str(ambiguity),
            candidates=[candidate.signature for candidate in ambiguity.candidates],
        )

    if document is None:
        return SourceView(
            found=False,
            reason=(
                "this analysis holds no source for that method: either the method is "
                "not in the APK, or no backend that could produce source was available"
            ),
        )

    return SourceView(
        found=True,
        kind=document.kind.value,
        text=UntrustedText(text=document.text),
        provenance=[entry.locator for entry in document.provenance],
    )


__all__ = ["class_source", "method_source", "search_symbols"]
