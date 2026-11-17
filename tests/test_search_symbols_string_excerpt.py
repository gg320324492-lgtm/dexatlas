"""A string constant's excerpt is one line; a code hit's excerpt is not cut.

The M6 budget analysis measured a ``search_symbols`` page of twenty string
hits whose serialized transcript was more than half copies: each hit carried
its value twice — once as the name, once as the excerpt — and the loop
re-sends the transcript on every turn, so the copies were billed again on
every round. A string constant is one line and usually one token; the
excerpt around it is the string itself, which the name already shows.

The fix cuts a *string* hit's excerpt to one line and 128 bytes, with the
cut stated in the response as every other cut is. Class, method and field
hits keep the wider limits: the excerpt around a code hit is the code the
match sits in, and that is the fact a reader came for.

Red state: without the cut, a string page's excerpts are as wide as a code
page's, and the copies ride along.
"""

from __future__ import annotations

import json

import pytest

from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.tools import symbols as symbol_tools


@pytest.fixture
def analyzed(settings, tmp_path) -> tuple[Analyzer, str]:
    """A workspace with one string constant long enough to be cut."""
    from tests.agent_harness import build_demo

    demo = build_demo(settings, tmp_path)
    return demo.analyzer, demo.project_id


def _string_entries(project_id: str, count: int) -> list[dict]:
    """String-constant rows as the store writes them, for the page builder.

    The constant is a made-up ``sk_live_``-prefixed string, long enough that
    the 128-byte cut has something to cut. It is not a real key: the prefix
    is the shape the search guidance names, and the rest is filler.
    """
    return [
        {
            "kind": "string",
            "name": "sk_live_" + "abcdefghijklmnopqrst" * 6,
            "excerpt": "res/values/strings.xml — com.example.demo.MainActivity.onCreate "
            "— the string constant that pays for everything\nsecond line\nthird line",
        }
        for _ in range(count)
    ]


def test_a_string_hit_s_excerpt_is_one_line(analyzed: tuple[Analyzer, str]) -> None:
    """The excerpt around a string hit is the value, not eight lines of it."""
    _, project_id = analyzed
    views = symbol_tools._page_symbols(_string_entries(project_id, 1))
    assert len(views) == 1
    detail = views[0].detail
    assert len(detail.text.splitlines()) == 1, "a constant's excerpt is one line"
    assert detail.truncated, "the cut is stated in the response"


def test_a_string_hit_s_excerpt_is_bounded_at_128_bytes(analyzed: tuple[Analyzer, str]) -> None:
    """A long constant's excerpt stops at the byte bound, and says so."""
    _, project_id = analyzed
    views = symbol_tools._page_symbols(_string_entries(project_id, 1))
    detail = views[0].detail
    assert len(detail.text.encode("utf-8")) <= 128, "the excerpt fits the byte bound"
    assert detail.truncated


def test_a_code_hit_s_excerpt_keeps_its_wider_limits() -> None:
    """A class, method or field excerpt is not cut by the string rule."""
    entries = [
        {
            "kind": "class",
            "name": "com.example.demo.Crypto",
            "excerpt": "\n".join(f"line {index}" for index in range(8)),
        }
    ]
    views = symbol_tools._page_symbols(entries)
    assert len(views[0].detail.text.splitlines()) == 8, "code excerpts keep their lines"
    assert not views[0].detail.truncated


def test_a_page_of_string_hits_is_a_fraction_of_its_old_size(
    analyzed: tuple[Analyzer, str],
) -> None:
    """Twenty string hits cost a page of facts, not two copies of the pool."""
    _, project_id = analyzed
    entries = _string_entries(project_id, 20)
    views = symbol_tools._page_symbols(entries)
    serialized = json.dumps([view.model_dump(mode="json") for view in views])
    # Forty bounded texts at the old 4096-byte bound would be a huge page;
    # the string cut keeps every excerpt within 128 bytes.
    assert len(serialized) < 20_000, f"the page serialized to {len(serialized)} chars"


def test_the_string_cut_is_in_the_tool_s_description() -> None:
    """The model is told that string hits come back one line at a time."""
    from dexatlas.agent.tool_executor import TOOL_DESCRIPTIONS

    assert "limit=20" in TOOL_DESCRIPTIONS["search_symbols"]
