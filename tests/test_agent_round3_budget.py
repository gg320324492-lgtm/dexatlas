"""Round-3 budget regression tests.

The narrow second verification showed three tasks dying at the per-task
24,000-token gate with almost no completion tokens: the whole spend was the
prompt, and the prompt carried whole-class source and whole-manifest pages
re-sent on every iteration. These tests pin the fix: a tool answer that
carries more text than a model needs is clipped for the *transcript* while
the evidence recorded from it stays whole.
"""

from __future__ import annotations

import json

from dexatlas.agent.tool_executor import clip_tool_content


def test_clip_keeps_a_short_answer_unchanged() -> None:
    """A reading that fits is passed through byte for byte."""
    content = json.dumps({"tool": "get_manifest", "ok": True, "data": {"package": "com.example"}})
    assert clip_tool_content(content) == content


def test_clip_shortens_a_long_text_field_but_keeps_the_shape() -> None:
    """A source read that is far larger than a model needs is clipped.

    The clipped answer keeps the document's shape — tool, ok, found, kind,
    provenance — and says in the text itself that the middle was cut. A model
    that reads the head and the tail of a class still sees its declarations
    and its string constants; the dropped middle is body it can re-read.
    """
    text = "const-string v0, 'sk_live_2f8a91c4e7b3'\n" + ("filler line\n" * 4000)
    content = json.dumps(
        {
            "tool": "get_class_source",
            "ok": True,
            "data": {
                "found": True,
                "kind": "smali",
                "text": text,
                "provenance": ["examples/demo-app/smali/com/example/demo/MainActivity.smali"],
            },
        }
    )
    clipped = clip_tool_content(content)
    assert clipped != content
    assert len(clipped) < len(content)
    document = json.loads(clipped)
    assert document["tool"] == "get_class_source"
    assert document["ok"] is True
    assert document["data"]["found"] is True
    assert document["data"]["provenance"] == [
        "examples/demo-app/smali/com/example/demo/MainActivity.smali"
    ]
    # The head of the text survives — the interesting constants are usually
    # near the declarations — and the clip is announced where it happened.
    kept = document["data"]["text"]
    assert "sk_live_2f8a91c4e7b3" in kept
    assert "clipped" in kept


def test_clip_keeps_a_row_page_whose_rows_are_short() -> None:
    """A page of lean rows is enumerated in full.

    The manifest component list is a long answer made of short rows: each
    row fits, and the page fits the transcript allowance, so the clip keeps
    every row and every value whole — the enumeration *is* the answer.
    """
    rows = [{"name": f"constant_{i}", "value": "x" * 150} for i in range(40)]
    content = json.dumps({"tool": "search_symbols", "ok": True, "data": {"symbols": rows}})
    clipped = clip_tool_content(content)
    document = json.loads(clipped)
    assert len(document["data"]["symbols"]) == 40
    assert all(row["value"] == "x" * 150 for row in document["data"]["symbols"])


def test_clip_cuts_a_page_whose_scaffolding_outweighs_its_rows() -> None:
    """A page of heavy rows is cut to the transcript allowance, with the
    offset that pages to what was dropped.

    The real page that burned the api-key task was twenty rows whose keys,
    bookkeeping and folded notices outweighed the values they carried. The
    clip keeps the first rows, states the cut, and leaves ``total`` and
    ``offset`` intact — the count the question asked about survives.
    """
    heavy = {"kind": "string", "note": "x" * 400, "name": "api_key", "provenance": []}
    content = json.dumps(
        {
            "tool": "search_symbols",
            "ok": True,
            "data": {
                "symbols": [dict(heavy) for _ in range(60)],
                "total": 60,
                "offset": 0,
                "limit": 60,
            },
        }
    )
    clipped = clip_tool_content(content)
    document = json.loads(clipped)
    symbols = document["data"]["symbols"]
    assert len(symbols) < 60
    assert symbols[0]["name"] == "api_key"
    assert "clipped" in symbols[-1]["row_clip"]
    assert "offset=" in symbols[-1]["row_clip"]
    assert document["data"]["total"] == 60
    assert document["data"]["offset"] == 0
