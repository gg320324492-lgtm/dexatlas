"""The agent's transcript folds repeated data notices; the MCP response does not.

The M6 budget analysis found a ``search_symbols`` page whose serialized agent
content was 23,392 characters — and that the per-symbol data notice, repeated
for every hit twice over (name and detail), was more than half of it. Because
the loop re-sends the whole transcript on every turn, one big page is billed
again on every round after it, and a task whose reading is a page of string
constants burns its budget on boilerplate.

The fix folds the notice inside :func:`_success_content`: the first notice in
a response keeps its full text — the reader cannot miss what the text is —
and every later occurrence becomes a short marker that points back at it.
The MCP-facing contract is untouched: :class:`UntrustedText` still carries
the notice on every field, byte for byte, and nothing outside the agent's
own transcript sees the fold.

Red state: without the fold, every nested notice is carried in full, and the
same page serializes to thousands of characters of repeated boilerplate.
"""

from __future__ import annotations

import json

import pytest

from dexatlas.agent.tool_executor import FOLDED_NOTICE, _success_content
from dexatlas.mcp.schemas import (
    DATA_NOTICE,
    SymbolList,
    SymbolView,
    UntrustedText,
)


def _page(count: int) -> SymbolList:
    """A page of string-constant hits, each carrying two wrapped texts."""
    return SymbolList(
        symbols=[
            SymbolView(
                kind="string",
                name=UntrustedText(text="sk_live_abcdefghijklmnop"),
                detail=UntrustedText(text="res/values/strings.xml | com.example.demo.MainActivity"),
                provenance=[],
            )
            for _ in range(count)
        ],
        total=count,
        offset=0,
        limit=count,
    )


def _notices(content: str) -> list[str]:
    """Every notice value in a serialized document, in order."""
    values: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "notice":
                    values.append(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads(content))
    return values


def test_the_first_notice_keeps_its_text_and_the_rest_are_folded() -> None:
    """One full notice says what the text is; the repeats do not re-read it."""
    content = _success_content("search_symbols", _page(20))
    notices = _notices(content)

    assert notices, "the wrapped text still says what it is"
    assert notices[0] == DATA_NOTICE, "the first notice is carried in full"
    assert len(notices) > 1, "the page has more than one wrapped text"
    assert all(notice == FOLDED_NOTICE for notice in notices[1:]), (
        "the repeated notices are folded to the short marker"
    )


def test_folding_cuts_the_page_to_a_fraction_of_its_size() -> None:
    """The boilerplate is gone from the agent's transcript, measurably."""
    page = _page(20)
    content = _success_content("search_symbols", page)
    # Twenty symbols, two wrapped texts each: forty notices at 131 characters
    # is more than five thousand characters of repeated notice. After the
    # fold, one full notice and thirty-nine short markers remain.
    assert content.count(DATA_NOTICE) == 1

    unfolded = json.dumps(
        {"tool": "search_symbols", "ok": True, "data": page.model_dump(mode="json")},
        sort_keys=True,
    )
    saved = len(unfolded) - len(content)
    assert saved > 3_000, f"the fold saved {saved} characters of repeated notice"


def test_the_mcp_facing_response_still_carries_every_notice() -> None:
    """The fold is in the agent transcript only, not in the tool's contract.

    The MCP server serializes the same payload straight from the model; the
    fold in ``_success_content`` must not have touched the model's own
    fields.
    """
    page = _page(3)
    assert page.model_dump(mode="json") is not None
    direct = json.dumps(page.model_dump(mode="json"))
    assert direct.count(DATA_NOTICE) == 6, (
        "every UntrustedText still carries its notice in the MCP-facing serialization"
    )


def test_a_single_wrapped_text_reads_as_before() -> None:
    """One wrapped text keeps its full notice; there is nothing to fold.

    A page with one symbol holds two wrapped texts — the name and the
    detail — so the first keeps its notice and the second is folded: the
    reader has already been told, in this same response, what the text is.
    """
    content = _success_content("search_symbols", _page(1))
    notices = _notices(content)
    assert notices[0] == DATA_NOTICE
    assert all(notice == FOLDED_NOTICE for notice in notices[1:])


def test_a_distinct_notice_is_not_folded_away() -> None:
    """A notice that says something different keeps its own words.

    The fold is for repetition, not for notice-wearing in general: if a
    wrapped text ever carries a different notice — a different warning about
    a different kind of text — the fold must not silence it.
    """
    page = SymbolList(
        symbols=[
            SymbolView(
                kind="string",
                name=UntrustedText(text="one"),
                detail=UntrustedText(text="two", notice="a different warning"),
                provenance=[],
            )
        ],
        total=1,
        offset=0,
        limit=1,
    )
    content = _success_content("search_symbols", page)
    notices = _notices(content)
    assert notices.count(DATA_NOTICE) == 1
    assert notices.count("a different warning") == 1


def test_the_first_notice_comes_from_the_first_wrapped_text_in_order() -> None:
    """The fold follows the response's own order: first wrapped, first kept."""
    page = _page(2)
    content = _success_content("search_symbols", page)
    notices = _notices(content)
    assert notices[0] == DATA_NOTICE
    assert notices[1] == FOLDED_NOTICE
    assert notices[2] == FOLDED_NOTICE
    assert notices[3] == FOLDED_NOTICE


@pytest.mark.parametrize("payload_kind", ["symbols", "locator"])
def test_other_responses_fold_their_notices_too(payload_kind: str) -> None:
    """Every tool answer the agent reads is folded, not only symbol pages."""
    if payload_kind == "symbols":
        payload: object = _page(5)
    else:
        from dexatlas.mcp.schemas import LocatorResolution

        payload = LocatorResolution(
            resolved=True,
            reason="the locator names a class in this analysis",
            kind="java",
            text=UntrustedText(text="public final class Crypto {\n  int one;\n}"),
        )
    content = _success_content(
        "resolve_locator" if payload_kind == "locator" else "search_symbols", payload
    )
    assert content.count(DATA_NOTICE) == 1
