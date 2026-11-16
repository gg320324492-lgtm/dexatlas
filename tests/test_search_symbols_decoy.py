"""The decoy-shadowing contract: a string hit does not hide the pool.

The M6 level-2 retest found the agent answering the api-key question with
the decoy constant ``api_key`` while the real key
``sk_live_2f8a91c4e7b3`` sat unseen in the same pool. The tool's word
search had hit the decoy, and the fallback that sweeps the constant pool
only ran when the word search came back *empty* — so one plausible hit
shadowed the enumeration, and the agent concluded from a decoy.

The fix: when a multi-word query already has string-kind hits, the pool's
constants join the answer — the word hits keep their order, the pool
follows, and neither identity is lost. A single-word query is left alone:
one word is usually a name, and widening it would flood the answer with
the whole pool. A multi-word query whose hits are code (classes, methods,
fields) is left alone too: there the index answered the question asked,
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
from dexatlas.mcp.tools.symbols import search_symbols

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


def test_a_single_word_query_is_left_to_the_word_search(analyzer) -> None:
    """One word is a name: the pool does not flood the answer.

    A single-word query that already hits is the normal search path, and
    widening it would bury the hit under every constant in the pool. This
    pins the boundary the union rule draws.
    """
    names = _names(analyzer, "api")
    assert DECOY in names, names
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
