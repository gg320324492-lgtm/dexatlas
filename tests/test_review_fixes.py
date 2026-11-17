"""The review fixes: clipped readings stay reachable, and wide pages clip.

Two findings from the read-only review of the M6 budget work:

**M-1 (medium).** The clip notice said "the full text is recorded as
evidence", but the evidence record for a source read carried only the tool
and the kind — never the text. A class whose source is larger than the
transcript's per-field limit was clipped in the transcript, and the tail was
then unreachable: ``get_evidence`` handed back a record without the text,
re-reading the source clipped again, and ``resolve_locator`` clipped too.

The fix gives the record the text, in bounded parts, and gives the source
tools an ``offset``/``limit`` so the model can page to what was dropped. The
notice now says what is actually true: how much was shown, and that the next
page is one ``offset`` away.

**L-1 (low).** ``_clip_rows`` only clipped ``symbols`` and ``declarations``
pages, so a ``find_callers`` answer at the 200-row cap — every row carrying
two long class names and a provenance locator — sailed past the row clip
whole, and was re-billed on every turn. ``call_sites`` and ``callees`` join
the clipped keys, and the reference tools gain an ``offset`` so the "page
again with offset=" notice points at a call that really exists.

Red state: on the code before these fixes, the evidence record carries no
text parts, the source and reference tools accept no ``offset``, the notice
still claims the full text is recorded, and a wide call-site page comes back
unclipped.
"""

from __future__ import annotations

import json
from pathlib import Path

from dexatlas.agent.orchestrator import _record_as_evidence
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from dexatlas.agent.tool_executor import MAX_FIELD_TEXT, clip_tool_content
from dexatlas.core.models import EvidenceKind
from dexatlas.mcp.schemas import SourceView, UntrustedText
from dexatlas.mcp.tools.references import find_callees, find_callers
from dexatlas.mcp.tools.symbols import class_source
from tests.agent_harness import (
    CRYPTO,
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    scripted_provider,
)

#: A source text big enough that the transcript clip cuts it: well past the
#: 4,000-character field limit, but small enough that the whole of it fits in
#: the evidence record.
BIG_SOURCE = (
    "const-string v0, 'head_marker'\n" + ("filler line\n" * 800) + "TAIL_MARKER_reaches_the_end\n"
)

#: A source text bigger than the evidence record's own allowance, so the
#: record keeps its head and says what was left out.
HUGE_SOURCE = ("x" * 100) + "\n" + ("filler line\n" * 20_000) + "TAIL_MARKER_beyond_the_record\n"


def _source_view(text: str) -> SourceView:
    """A successful source read, as the tool returns it."""
    return SourceView(
        found=True,
        kind="smali",
        text=UntrustedText(text=text),
        provenance=["androguard:classes.dex#com.example.demo.Crypto"],
    )


def _record_source_text(demo: Demo, text: str) -> dict[str, object]:
    """Record a source read through the orchestrator's own path."""
    builder = demo.builder()
    record = _record_as_evidence(builder, "get_class_source", _source_view(text))
    assert record is not None
    return record.detail


# -- M-1: the evidence record carries the text the transcript clipped --------


def test_a_clipped_source_read_is_whole_in_the_evidence_record(settings, tmp_path: Path) -> None:
    """The record holds every character the transcript dropped.

    A model that trusts the old notice and asks ``get_evidence`` for the
    record must find the text there — all of it, in parts it can join — or
    the notice was a lie and the tail of the class was unreachable.
    """
    demo = build_demo(settings, tmp_path)
    detail = _record_source_text(demo, BIG_SOURCE)

    parts = detail["text_parts"]
    assert isinstance(parts, list) and parts, "the record carries the text in parts"
    assert "".join(str(part) for part in parts) == BIG_SOURCE
    assert detail["text_total_chars"] == len(BIG_SOURCE)
    assert detail["text_parts_truncated"] is False


def test_a_source_read_bigger_than_the_record_keeps_its_head_and_says_so(
    settings, tmp_path: Path
) -> None:
    """The record is bounded, and the bound is stated, not silent.

    A 50 KB class and a 5 MB class cost the record the same bounded size;
    what the record gives up is named by the total and the truncation flag,
    so a reader knows the parts are a head, not the whole.
    """
    demo = build_demo(settings, tmp_path)
    detail = _record_source_text(demo, HUGE_SOURCE)

    parts = detail["text_parts"]
    assert isinstance(parts, list) and parts
    joined = "".join(str(part) for part in parts)
    assert len(joined) < len(HUGE_SOURCE), "the record is bounded"
    assert joined == HUGE_SOURCE[: len(joined)], "the record keeps the head"
    assert "TAIL_MARKER_beyond_the_record" not in joined
    assert detail["text_total_chars"] == len(HUGE_SOURCE)
    assert detail["text_parts_truncated"] is True


def test_the_source_tools_page_to_what_the_transcript_dropped(settings, tmp_path: Path) -> None:
    """``offset``/``limit`` reach the tail the clip left out of the transcript.

    Re-reading a clipped source with the same arguments would clip again —
    the cut is a function of the text, not of the ask. Paging is the way to
    the tail, so the tools have to offer it.
    """
    demo = build_demo(settings, tmp_path)
    crypto_java = demo.workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    crypto_java.write_text(BIG_SOURCE, encoding="utf-8")

    whole = class_source(demo.analyzer, demo.project_id, CRYPTO)
    assert whole.found
    assert whole.text is not None
    assert whole.text.text == BIG_SOURCE, "no paging asked, whole source back — as before"
    assert whole.text_total_chars == len(BIG_SOURCE)

    page = class_source(demo.analyzer, demo.project_id, CRYPTO, offset=MAX_FIELD_TEXT)
    assert page.text is not None
    assert page.text.text == BIG_SOURCE[MAX_FIELD_TEXT:], "the second page reaches the tail"
    assert page.text_offset == MAX_FIELD_TEXT
    assert page.text_total_chars == len(BIG_SOURCE)

    window = class_source(demo.analyzer, demo.project_id, CRYPTO, offset=10, limit=20)
    assert window.text is not None
    assert window.text.text == BIG_SOURCE[10:30], "offset and limit cut one window"


# -- M-1: the notice tells the truth -----------------------------------------


def test_the_clip_notice_says_how_to_read_the_rest() -> None:
    """The notice points at paging, not at a record that never had the text.

    "The full text is recorded as evidence" sent the model to ``get_evidence``,
    which answered without the text. The notice now names the one path that
    really reaches the tail: the same tool, one offset further.
    """
    content = json.dumps(
        {"tool": "get_class_source", "ok": True, "data": {"found": True, "text": BIG_SOURCE}}
    )
    clipped = clip_tool_content(content)
    assert clipped != content

    document = json.loads(clipped)
    text = document["data"]["text"]
    assert "recorded as evidence" not in text, "the old promise is gone"
    assert "offset=" in text, "the notice names the paging argument"
    assert "clipped" in text, "the notice still says a cut happened"


# -- L-1: a wide call-site page is clipped like every other page -------------


def _call_site_page(count: int) -> str:
    """A ``find_callers`` answer at the row cap, serialized as the agent sees it."""
    sites = [
        {
            "caller": f"com.example.app.Feature{i}.handle(Landroid/os/Bundle;)V",
            "callee": "com.example.core.Crypto.sign(Ljava/lang/String;)Ljava/lang/String;",
            "kind": "static",
            "dex_name": "classes.dex",
            "instruction_offset": 12 * i,
            "provenance": [
                f"androguard:classes.dex#com.example.app.Feature{i}.handle(Landroid/os/Bundle;)V"
            ],
        }
        for i in range(count)
    ]
    return json.dumps(
        {
            "tool": "find_callers",
            "ok": True,
            "data": {"call_sites": sites, "call_site_count": count, "call_edge_count": count},
        },
        sort_keys=True,
    )


def test_a_wide_call_site_page_is_clipped_to_the_transcript_allowance() -> None:
    """A 200-row caller page does not sail past the row clip whole.

    The page is far larger than the transcript allowance; the clipped answer
    keeps its first rows and its counts, and the cut names the offset that
    pages to what was dropped.
    """
    content = _call_site_page(200)
    assert len(content) > 12_000, "the page is big enough to need the clip"

    clipped = clip_tool_content(content)
    assert clipped != content, "a page this wide is clipped"
    assert len(clipped) < len(content)

    document = json.loads(clipped)
    data = document["data"]
    assert len(data["call_sites"]) < 200, "only the head rows survive"
    assert data["call_site_count"] == 200, "the count is the count the question asked about"
    assert data["call_edge_count"] == 200
    last = data["call_sites"][-1]
    assert "row_clip" in last, "the cut is announced where it happened"
    assert "offset=" in last["row_clip"], "the notice pages to what was dropped"


def test_a_wide_callee_page_is_clipped_too() -> None:
    """``callees`` pages clip under the same rule."""
    rows = [
        {
            "kind": "method",
            "name": {
                "text": f"com.example.lib.Util{i}.run()V",
                "truncated": False,
                "bytes": 0,
                "notice": "data notice",
            },
            "detail": {"text": "virtual", "truncated": False, "bytes": 0, "notice": "data notice"},
            "provenance": [f"androguard:classes.dex#com.example.lib.Util{i}"],
        }
        for i in range(120)
    ]
    content = json.dumps(
        {
            "tool": "find_callees",
            "ok": True,
            "data": {"callees": rows, "call_site_count": 120, "call_edge_count": 120},
        },
        sort_keys=True,
    )
    assert len(content) > 12_000

    clipped = json.loads(clip_tool_content(content))
    assert len(clipped["data"]["callees"]) < 120
    assert clipped["data"]["call_site_count"] == 120


def test_find_callers_offset_pages_through_the_sites(settings, tmp_path: Path) -> None:
    """The offset the row-clip notice names is a real argument.

    A caller with more sites than one page holds is read page by page: the
    second page carries the sites the first dropped, and no page repeats one.
    """
    demo = build_demo(settings, tmp_path)
    method_id = "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"
    store = demo.analyzer.store
    from dexatlas.core.models import InvocationKind, MethodReference

    sites = [
        MethodReference(
            caller=f"com.example.demo.Caller{i}.call()V",
            callee=method_id,
            kind=InvocationKind.STATIC,
            provenance=[],
        )
        for i in range(60)
    ]
    store.save_symbols(demo.project_id, [], [], [], sites, [])

    first = find_callers(demo.analyzer, demo.project_id, method_id, limit=50)
    assert len(first.call_sites) == 50
    assert first.call_site_count == 60
    assert first.offset == 0

    second = find_callers(demo.analyzer, demo.project_id, method_id, limit=50, offset=50)
    assert len(second.call_sites) == 10
    assert second.offset == 50
    first_ids = {site.caller for site in first.call_sites}
    second_ids = {site.caller for site in second.call_sites}
    assert not first_ids & second_ids, "the pages do not repeat a site"


def test_find_callees_offset_pages_through_the_sites(settings, tmp_path: Path) -> None:
    """The same paging reaches the callees direction."""
    demo = build_demo(settings, tmp_path)
    method_id = "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"
    store = demo.analyzer.store
    from dexatlas.core.models import InvocationKind, MethodReference

    sites = [
        MethodReference(
            caller=method_id,
            callee=f"com.example.demo.Target{i}.run()V",
            kind=InvocationKind.STATIC,
            provenance=[],
        )
        for i in range(60)
    ]
    store.save_symbols(demo.project_id, [], [], [], sites, [])

    second = find_callees(demo.analyzer, demo.project_id, method_id, limit=50, offset=50)
    assert len(second.callees) == 10
    assert second.offset == 50
    assert second.call_site_count == 60


# -- the whole loop: a big class is clipped in the transcript and whole in
#    the evidence --------------------------------------------------------------


def test_a_task_reading_a_big_class_clips_the_transcript_and_keeps_the_tail_reachable(
    settings, tmp_path: Path
) -> None:
    """End to end: the transcript is clipped, the record carries the text.

    The model reads a class whose source is far larger than the transcript
    allowance. The observation it is shown is clipped; the evidence record
    the observation names carries the whole text in parts; and paging the
    tool reaches the tail. Nothing about the answer's shape changes.
    """
    demo = build_demo(settings, tmp_path)
    crypto_java = demo.workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    crypto_java.write_text(BIG_SOURCE, encoding="utf-8")

    provider = scripted_provider(
        [(("get_class_source", {"project_id": PROJECT_ID, "class_name": CRYPTO}))],
        statement="the class reads as recorded",
    )
    orchestrator = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=60_000, max_iterations=6, max_seconds=60.0),
    )
    state = orchestrator.run(
        "Show me the source of com.example.demo.Crypto", project_id=demo.project_id
    )

    assert state.status is TaskStatus.COMPLETED, state.error

    # The transcript was clipped, and says so.
    observations = [turn for turn in state.turns if type(turn).__name__ == "Observation"]
    source_observations = [
        turn for turn in observations if getattr(turn, "tool", "") == "get_class_source"
    ]
    assert source_observations, "the task read the class"
    shown = source_observations[0].content
    assert "clipped" in shown, "the transcript says the text was cut"
    assert len(shown) < len(BIG_SOURCE)

    # The record the observation names carries the whole text, in parts.
    document = json.loads(shown)
    record_id = document["evidence_id"]
    record = next(item for item in state.findings if item.id == record_id)
    assert record.kind is EvidenceKind.CODE_LOCATED
    parts = record.detail["text_parts"]
    assert "".join(str(part) for part in parts) == BIG_SOURCE, (
        "the evidence record holds the text the transcript dropped"
    )
