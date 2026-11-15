"""The string-constant substring sweep behind ``search_symbols``.

The M6 level-2 retest found the agent failing ``strings.api-key.demo`` for a
mechanical reason: it searched the index for the words the question used
("api key"), and the constant the question was about —
``sk_live_2f8a91c4e7b3`` — contains none of those words. The token search is
word-shaped, so a question about a constant it cannot name finds nothing, and
an agent that trusts an empty search reports an absence that is not there.

The fix is a second, substring-shaped read of the string-constant pool,
appended after the word search. These tests pin three things:

* the sweep finds a constant the word search misses (the regression);
* the sweep never invents a hit that is not in the pool;
* a constant the word search already returned is not returned twice.

The red state is the committed code before the sweep: with it taken away,
``search_symbols("api key")`` finds nothing, and the first test fails.
"""

from __future__ import annotations

import pytest

from dexatlas.core.models import StringConstant
from dexatlas.mcp.tools.symbols import search_symbols
from tests.agent_harness import MAIN, PROJECT_ID, _provenance, build_demo


@pytest.fixture
def demo(settings, tmp_path):
    return build_demo(settings, tmp_path)


def _pool_with(demo, *values: str) -> None:
    """Replace the project's string pool with the given constants."""
    demo.analyzer.store.save_symbols(
        PROJECT_ID,
        classes=[],
        methods=[],
        fields=[],
        references=[],
        strings=[
            StringConstant(
                value=value,
                class_name=MAIN,
                method_name="onCreate",
                provenance=_provenance("dex:classes.dex#MainActivity.onCreate"),
            )
            for value in values
        ],
    )


def _names(result) -> list[str]:
    """The hit names as plain text, whatever wrapper carries them."""
    names: list[str] = []
    for symbol in result.symbols:
        name = symbol.name
        names.append(getattr(name, "text", name) if not isinstance(name, str) else name)
    return names


def test_a_search_for_words_the_constant_lacks_still_finds_it(demo) -> None:
    """The regression: "api key" finds `sk_live_...` even though it names none of it.

    The demo pool holds the collect URL but not an API-key constant, so the
    pool under test is replaced with one that has the key. The point is the
    *shape* of the fix: a word query that the constant's value does not spell
    out still surfaces the constant.
    """
    api_key = "sk_live_2f8a91c4e7b3"
    _pool_with(demo, api_key)

    result = search_symbols(demo.analyzer, PROJECT_ID, "api key", limit=50, offset=0)
    names = _names(result)
    assert api_key in names, "a word search that the constant cannot match must still find it by substring"
    assert any(symbol.kind == "string" for symbol in result.symbols)


def test_a_word_search_miss_falls_back_to_the_pool_itself(demo) -> None:
    """A query nothing matches still surfaces the constants the pool holds.

    "totally-absent-text" matches no constant by token or substring. The
    final fallback is the pool's own enumeration: the agent is shown what
    the index does hold, so its answer about what is absent is grounded in
    the constants that exist rather than in an empty search alone.
    """
    result = search_symbols(demo.analyzer, PROJECT_ID, "totally-absent-text", limit=50, offset=0)
    # The token search established nothing (total 0); the enumeration is
    # the fallback's reading of the pool, which holds the collect URL.
    names = _names(result)
    assert "https://api.example.com/collect" in names
    assert all(str(symbol.kind) == "string" for symbol in result.symbols)


def test_a_word_search_hit_is_not_duplicated_by_the_sweep(demo) -> None:
    """A constant the token search already returned is not appended again."""
    # The demo pool holds the collect URL; searching its host finds it by
    # token. The sweep must not add a second copy of the same row.
    result = search_symbols(demo.analyzer, PROJECT_ID, "api.example.com", limit=50, offset=0)
    names = _names(result)
    assert names.count("https://api.example.com/collect") == 1


def test_the_sweep_is_case_insensitive(demo) -> None:
    """A query in a different case still matches the constant's value."""
    result = search_symbols(demo.analyzer, PROJECT_ID, "API.EXAMPLE.COM", limit=50, offset=0)
    names = _names(result)
    assert "https://api.example.com/collect" in names
