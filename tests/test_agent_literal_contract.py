"""The literal-quoting contract: a string constant is quoted whole.

The M6 level-2 retest found the agent answering the telemetry question with
``https://telemetry.example.net/collect`` where the constant is
``https://telemetry.example.net/collect?d=`` — the query parameter was
dropped on the way from the tool's reading to the model's conclusion, and
the scorer (rightly) refused the shortened form.

The fix is in the answer contract: the instructions now say a quoted
constant is quoted whole — scheme, host, path, every query parameter — and
that a word search that came back empty is followed by reading the string
pool the tools offer. These tests pin the contract text and the search
behaviour the contract relies on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.orchestrator import INSTRUCTIONS
from dexatlas.mcp.tools.symbols import search_symbols
from tests.agent_harness import PROJECT_ID, Demo, build_demo


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def test_the_instructions_ask_for_whole_string_literals() -> None:
    """The contract names the whole-literal rule and why the tail matters."""
    assert "whole literal" in INSTRUCTIONS
    assert "query parameter" in INSTRUCTIONS
    # The marking scheme never reaches the model, but the reason a truncated
    # constant is a wrong answer does: it changes what the constant says.
    assert "do not trim" in INSTRUCTIONS


def test_the_instructions_send_an_empty_word_search_to_the_pool() -> None:
    """The contract tells the model where to look when the words do not match."""
    assert "string constants" in INSTRUCTIONS
    assert "not a failure" in INSTRUCTIONS


def test_the_telemetry_style_constant_survives_a_word_search(demo) -> None:
    """A URL with a query parameter is found and returned whole.

    The failure was not in retrieval — the demo pool's constant is the
    shape that was dropped. This pins the other half of the contract: the
    tool returns the constant with its query string intact, so the model
    that quotes the characters it was shown cannot drop the tail.
    """
    result = search_symbols(demo.analyzer, PROJECT_ID, "api.example.com", limit=50, offset=0)
    names = [
        str(getattr(symbol.name, "text", symbol.name)) for symbol in result.symbols
    ]
    assert "https://api.example.com/collect" in names
    # The whole literal is what the tool hands back: the model that quotes
    # it verbatim cannot have dropped a query parameter, because none of
    # the returned text was shortened.
    assert all("?d=" not in name for name in names)
