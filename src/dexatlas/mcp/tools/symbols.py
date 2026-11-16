"""The tools that find symbols and hand back their source."""

from __future__ import annotations

from typing import Any

from dexatlas.core.methods import AmbiguousMethodError
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import unknown_project
from dexatlas.mcp.schemas import SourceView, SymbolList, SymbolView, UntrustedText
from dexatlas.mcp.security import bounded_text

#: How much of a symbol's text comes back.
#:
#: A name is one line and an excerpt is a handful, so the limits are tighter
#: than the ones a source file gets — but the point is the same: nothing
#: comes back unbounded, and the cut is stated in the response.
_SYMBOL_TEXT_LIMITS = {"max_lines": 8, "max_bytes": 4096}

#: The smallest query the pool-union rule answers. A query whose word
#: search hits string constants is a question about the pool's contents —
#: one word included, because the M6 single-turn verification had the agent
#: ask ``api_key`` and take the decoy constant for the whole answer while
#: the real key sat in the same pool. A query whose hits are code is left
#: to the index that answered it.
_MIN_WORD_COUNT = 1


def _page_symbols(entries: list[dict[str, Any]]) -> list[SymbolView]:
    """Turn store rows into the response's symbol views."""
    return [
        SymbolView(
            kind=str(entry.get("kind", "")),
            name=bounded_text(str(entry.get("name", "")), **_SYMBOL_TEXT_LIMITS),
            detail=bounded_text(str(entry.get("excerpt", "")), **_SYMBOL_TEXT_LIMITS),
            provenance=[],
        )
        for entry in entries
    ]


def _dedupe_by_identity(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop repeat rows, keeping the first order each identity appeared in.

    The word search and the pool enumerate the same constants by different
    routes, and a constant twice in one answer would read as two
    constants. The first occurrence — the word search's own ranking — is
    the one that stays.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for entry in entries:
        identity = (str(entry.get("kind", "")), str(entry.get("name", "")))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(entry)
    return unique


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

    The token search answers "what does the index say about these words". A
    string constant whose value never spells the query as words — "api key"
    asked, `sk_live_4eC39...` held — is invisible to it, so when the word
    search comes back empty the constant pool is swept for the query as a
    *substring*, and failing that the pool's constants are enumerated as
    candidates. Both fallbacks are deterministic and free; they answer the
    question a string-constant question actually asks — is there text in
    this APK that a reader would want to see — rather than leaving an empty
    word match to stand for an absence that was never established.

    A word search that *did* hit string constants does not end the
    question, because a hit can shadow its neighbours. The M6 level-2
    retest had the agent query "api key" and take the decoy constant
    ``api_key`` for the whole answer while the real key sat in the same
    pool, unseen — a decoy hit had silenced the enumeration. So when a
    query's word hits are string constants, the pool's constants join the
    answer: the word hits keep their order, the pool follows, and no
    identity appears twice. The first fix drew the line at two words; the
    single-turn verification re-ran the same failure with one — the agent
    asked ``api_key`` and got the decoy — so any word count joins now. A
    query whose hits are classes, methods or fields was answered as asked
    and is left alone.
    """
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)

    # The store takes a limit and not an offset, so the page is cut from a
    # longer read. Reading `offset + limit` rows and slicing them keeps the
    # paging honest: the total is what the index holds, not what this page
    # happens to show.
    found = analyzer.store.search(project_id, query, limit=offset + limit)
    page = found[offset : offset + limit]

    # The fallbacks run when the word search found nothing — a question
    # about a string constant whose value does not spell the query out is
    # the case the failure analysis named — or when the word hits are
    # themselves string constants, where a hit can shadow the rest of the
    # pool. The sweep adds constants that contain the query as characters;
    # the enumeration, last, shows the pool itself, so the answer "the
    # index holds no such constant" is backed by the constants the index
    # *does* hold.
    word_query = len(query.split()) >= _MIN_WORD_COUNT
    hit_strings = bool(page) and all(str(entry.get("kind", "")) == "string" for entry in page)
    union_pool = query.strip() and word_query and hit_strings
    if not page and query.strip():
        page = list(analyzer.store.search_string_substring(project_id, query, limit=offset + limit))
    if (not page or union_pool) and query.strip():
        pool = analyzer.store.list_string_constants(project_id, limit=offset + limit)
        page = _dedupe_by_identity([*page, *pool])

    return SymbolList(
        symbols=_page_symbols(page),
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
