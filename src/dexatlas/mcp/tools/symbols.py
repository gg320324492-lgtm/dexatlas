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

#: How much of a *string constant's* excerpt comes back.
#:
#: A string constant is one line and usually one token: the excerpt around a
#: string hit is the string itself, and eight lines of it is eight copies of
#: a value the name already shows. The M6 budget analysis measured a page of
#: twenty string hits carrying their values twice over — once as the name,
#: once as the excerpt — and the transcript re-sent on every turn billing
#: the same bytes again. A constant's excerpt is cut to one line and a
#: hundred and twenty-eight bytes: enough to see the value and where it
#: sits, small enough that a page of constants costs a page of facts, not a
#: page of copies. Class, method and field hits keep the wider limits: an
#: excerpt around a code hit is the code the match sits in, and that is the
#: fact a reader came for.
_STRING_EXCERPT_LIMITS = {"max_lines": 1, "max_bytes": 128}

#: The smallest query the pool-union rule answers. A query whose word
#: search hits string constants is a question about the pool's contents —
#: one word included, because the M6 single-turn verification had the agent
#: ask ``api_key`` and take the decoy constant for the whole answer while
#: the real key sat in the same pool. A query whose hits are code is left
#: to the index that answered it.
_MIN_WORD_COUNT = 1


def _page_symbols(entries: list[dict[str, Any]]) -> list[SymbolView]:
    """Turn store rows into the response's symbol views.

    A string constant's excerpt is cut harder than a code hit's: the excerpt
    around a string hit is the string itself, which the name already shows,
    and a page of constants is where a search's bytes go. The cut is stated
    in the response — ``truncated`` says so — like every other cut.
    """
    views: list[SymbolView] = []
    for entry in entries:
        kind = str(entry.get("kind", ""))
        limits = _STRING_EXCERPT_LIMITS if kind == "string" else _SYMBOL_TEXT_LIMITS
        views.append(
            SymbolView(
                kind=kind,
                name=bounded_text(str(entry.get("name", "")), **_SYMBOL_TEXT_LIMITS),
                detail=bounded_text(str(entry.get("excerpt", "")), **limits),
                provenance=[],
            )
        )
    return views


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

    The answer is one list, paged: ``total`` counts the de-duplicated
    union (or the index's own hit count when no union ran), and every page
    is a cut of that same list, so ``total`` never describes a different
    set than the rows on the page.
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
    # The union is de-duplicated *before* it is paged, from reads that are
    # long enough to hold the whole answer: a constant the word search also
    # found arrives twice, and cutting either source to `offset + limit`
    # rows first drops rows behind the cut — which shortened the page and
    # made the deduplicated order depend on the offset. The pool is read
    # with a bound that grows with the page instead, the union's ``total``
    # is the count of the de-duplicated rows — a number that describes the
    # list the page is cut from — and the page itself never exceeds the
    # caller's limit, so walking ``offset`` forward reads the union in
    # order without repeating or skipping a row.
    #
    # The rows the union starts from are the whole first reading — the word
    # search's full read when its hits are string constants, the substring
    # sweep's page when that answered — and not the slice `offset` cut
    # from them: the union's order is "the first reading, then the pool",
    # and the page is cut from that order afterwards, so a later page keeps
    # the rows an earlier page showed instead of replacing them with pool
    # rows the offset moved past.
    word_query = len(query.split()) >= _MIN_WORD_COUNT
    hit_strings = bool(page) and all(str(entry.get("kind", "")) == "string" for entry in page)
    union_pool = bool(query.strip()) and word_query and hit_strings
    total = len(found)
    if not page and query.strip():
        page = list(analyzer.store.search_string_substring(project_id, query, limit=offset + limit))
    if (not page or union_pool) and query.strip():
        first_reading = found if (union_pool or not page) else page
        pool = analyzer.store.list_string_constants(
            project_id, limit=offset + limit + max(len(found), len(page))
        )
        union = _dedupe_by_identity([*first_reading, *pool])
        total = len(union)
        page = union[offset : offset + limit]
    # A page is what its name says: no more than `limit` rows, whatever the
    # reads above produced. The cut sits after `total` is set, so the count
    # keeps describing the list the page was cut from.
    page = page[:limit]

    return SymbolList(
        symbols=_page_symbols(page),
        total=total,
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
