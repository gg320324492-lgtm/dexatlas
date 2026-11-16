"""The decoy-shadowing contract: a string hit does not hide the pool.

The M6 level-2 retest found the agent answering the api-key question with
the decoy constant ``api_key`` while the real key
``sk_live_2f8a91c4e7b3`` sat unseen in the same pool. The tool's word
search had hit the decoy, and the fallback that sweeps the constant pool
only ran when the word search came back *empty* — so one plausible hit
shadowed the enumeration, and the agent concluded from a decoy.

The fix: when a query already has string-kind hits, the pool's
constants join the answer — the word hits keep their order, the pool
follows, and neither identity is lost. The original fix drew the line at
two words; the M6 single-turn verification then showed the agent asking
``api_key`` — one word — and taking the decoy for the answer all over
again, so the line moved: any query whose word hits are string constants
joins the pool. A query whose hits are code (classes, methods,
fields) is left alone: there the index answered the question asked,
and the pool would only pollute the answer.

The workspace here is built by hand, as :mod:`tests.agent_harness` does,
but with the decoy and the secret in the pool — the shape the failure
analysis reproduced against the real demo APK.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    MethodRef,
    Project,
    ProjectStatus,
    Provenance,
    StringConstant,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.tools.symbols import _dedupe_by_identity, search_symbols

DECOY = "api_key"
SECRET = "sk_live_2f8a91c4e7b3"
URL = "https://api.example.com/collect"

FAKE_SHA256 = "c" * 64
PROJECT_ID = Project.new_id(FAKE_SHA256)

#: The pool the failure analysis described: a decoy whose name spells the
#: query's words, the real key beside it, and an ordinary URL constant.
POOL = (DECOY, SECRET, URL)


def _provenance() -> list[Provenance]:
    return [
        Provenance(
            tool="androguard",
            apk_sha256=FAKE_SHA256,
            locator="androguard:classes.dex#com.example.demo.MainActivity",
        )
    ]


@pytest.fixture
def analyzer(settings, tmp_path: Path) -> Analyzer:
    """An analysed workspace whose string pool holds a decoy and a secret."""
    app = Analyzer(settings)
    project = Project(
        id=PROJECT_ID,
        apk=ApkMetadata(
            sha256=FAKE_SHA256,
            size_bytes=1024,
            path=Path("decoy.apk"),
            dex_files=["classes.dex"],
        ),
        status=ProjectStatus.COMPLETED,
    )
    app.store.save_project(project, tmp_path / "workspace", None)
    app.store.save_symbols(
        PROJECT_ID,
        [
            ClassRef(
                name="com.example.demo.Crypto",
                kind=ClassKind.CLASS,
                access_flags=["public", "final"],
                method_count=1,
                provenance=_provenance(),
            )
        ],
        [
            MethodRef(
                class_name="com.example.demo.Crypto",
                name="sign",
                descriptor="(Ljava/lang/String;)Ljava/lang/String;",
                access_flags=["public", "static"],
                provenance=_provenance(),
            )
        ],
        [],
        [],
        [
            StringConstant(
                value=value,
                class_name="com.example.demo.MainActivity",
                method_name="onCreate",
                provenance=_provenance(),
            )
            for value in POOL
        ],
    )
    return app


def _names(analyzer: Analyzer, query: str, *, limit: int = 50, offset: int = 0) -> list[str]:
    result = search_symbols(analyzer, PROJECT_ID, query, limit=limit, offset=offset)
    return [str(getattr(symbol.name, "text", symbol.name)) for symbol in result.symbols]


def test_a_multiword_query_that_hits_a_decoy_still_enumerates_the_pool(analyzer) -> None:
    """The decoy hit and the real key come back together.

    The old implementation stopped at the word hits: "api key" matched the
    decoy ``api_key`` (FTS splits it into api + key) and never showed the
    real key the pool holds. The union is the answer a string question
    asks for — the words the agent typed, then the constants that exist.
    """
    names = _names(analyzer, "api key")
    assert DECOY in names, names
    assert SECRET in names, names
    # The word hits keep their place at the front; the pool follows.
    assert names.index(DECOY) < names.index(SECRET), names


def test_a_single_word_query_that_hits_a_decoy_still_enumerates_the_pool(analyzer) -> None:
    """The union is not a phrase rule: one word that shadows is shadowing.

    The single-turn verification had the agent query ``api_key`` — one
    word, the decoy's own name — and the word search answered with the
    decoy alone while the real key sat in the same pool. The old rule
    widened only phrase-length queries, so the one-word shadowing case
    kept its blind spot. Now the pool follows the word hits whatever the
    word count, and the hit still leads.
    """
    names = _names(analyzer, "api_key")
    assert DECOY in names, names
    assert SECRET in names, names
    assert names.index(DECOY) < names.index(SECRET), names


def test_a_snake_free_single_word_query_still_enumerates_the_pool(analyzer) -> None:
    """A one-word query FTS cannot split still finds the pool.

    ``apikey`` is one token — FTS gives no word hits for it at all — so
    the answer is the substring sweep's and the enumeration's, and the
    real key must be among them. This is the exact shape of the
    verification's failing question.
    """
    names = _names(analyzer, "apikey")
    assert SECRET in names, names
    assert URL in names, names


def test_a_single_word_code_hit_is_left_to_the_word_search(analyzer) -> None:
    """One word answered by code stays as it is.

    The union rule fires when the word hits are string constants — the
    case where the pool is plainly part of the answer. A one-word query
    answered by a class or a method was answered, and adding the pool
    would only bury the code the reader asked about.
    """
    names = _names(analyzer, "Crypto")
    assert any("Crypto" in name for name in names), names
    assert SECRET not in names, names


def test_a_multiword_query_that_hits_code_does_not_join_the_pool(analyzer) -> None:
    """A multi-word query the index answers with code stays as it is.

    The union rule fires when the word search's own hits are string
    constants — the case where the pool is plainly part of the answer. A
    query answered by classes or methods was answered, and adding the pool
    would only bury the code the reader asked about.
    """
    names = _names(analyzer, "crypto sign")
    assert any("sign" in name for name in names), names
    assert SECRET not in names, names


def test_the_pool_union_is_deduplicated_and_paged(analyzer) -> None:
    """The pool adds what the word search missed, and never a copy of it.

    The URL constant is one the word search also finds, so it must appear
    once — and paging cuts the combined list, not each source separately.
    """
    names = _names(analyzer, "api.example.com collect", limit=3)
    assert len(names) == len(set(names)), names
    assert len(names) == 3, names
    assert URL in names and SECRET in names, names


def test_the_union_page_never_exceeds_the_limit_and_total_covers_the_union(analyzer) -> None:
    """A deduplicated union is cut to the page's limit, and total says so.

    The first union implementation concatenated the word hits and the pool
    and cut the *read* at ``offset + limit`` before de-duplicating, so a
    query whose word hits repeat inside the pool came back with more rows
    than the caller asked for — and its ``total`` was the word search's
    count, a number that described neither the union nor the page. The
    page a caller gets is at most ``limit`` rows, and ``total`` is the
    count of the union the page is cut from.
    """
    # "api.example.com collect" word-hits the URL, and the pool holds the
    # URL again, the decoy and the secret: the de-duplicated union is the
    # three constants, which is more than the read of limit=2 rows carried.
    result = search_symbols(analyzer, PROJECT_ID, "api.example.com collect", limit=2, offset=0)
    names = [str(getattr(symbol.name, "text", symbol.name)) for symbol in result.symbols]
    assert len(names) <= 2, names
    assert len(names) == len(set(names)), names
    # The total is the union's size — the distinct rows the page is cut
    # from — not the word search's own hit count.
    union_size = len(
        {_kind_and_name(entry) for entry in _union_rows(analyzer, "api.example.com collect")}
    )
    assert result.total == union_size

    # Paging walks the same union without repeating or skipping a row.
    first = search_symbols(analyzer, PROJECT_ID, "api.example.com collect", limit=2, offset=0)
    second = search_symbols(analyzer, PROJECT_ID, "api.example.com collect", limit=2, offset=2)
    first_names = [str(getattr(symbol.name, "text", symbol.name)) for symbol in first.symbols]
    second_names = [str(getattr(symbol.name, "text", symbol.name)) for symbol in second.symbols]
    assert first_names + second_names == _union_names_in_order(analyzer, "api.example.com collect")
    assert second.total == first.total


def _kind_and_name(entry: dict) -> tuple[str, str]:
    return (str(entry.get("kind", "")), str(entry.get("name", "")))


def _union_rows(analyzer: Analyzer, query: str) -> list[dict]:
    """The union the tool builds, read straight from the store."""
    found = analyzer.store.search(PROJECT_ID, query, limit=50)
    pool = analyzer.store.list_string_constants(PROJECT_ID, limit=50)
    return _dedupe_by_identity([*found, *pool])


def _union_names_in_order(analyzer: Analyzer, query: str) -> list[str]:
    rows = _union_rows(analyzer, query)
    return [str(getattr(entry["name"], "text", entry["name"])) for entry in rows]
