"""A call site and a call edge are two different things, and the index says which.

A **call site** is one place in the bytecode where a call happens: the DEX
file it was read out of, the method that made the call, the instruction
offset inside that method, the opcode that carried it, and the method that
was called. A **call edge** is the relationship between two methods,
aggregated over the sites that make it.

The index used to hold one row per call and nothing else, so a method that
called the same target twice held two rows that said exactly the same thing,
and a table keyed on the caller and the callee could not tell them apart.
The rows are call sites now, and the two numbers the report states are
counted apart.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from dexatlas.config.settings import Settings
from dexatlas.core.calls import CallSite, derive_edges
from dexatlas.core.models import InvocationKind
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.storage import SCHEMA_VERSION, Store
from dexatlas.reports.markdown import render_markdown

DEMO_APK = Path(__file__).resolve().parent.parent / "examples" / "demo-app" / "demo.apk"

_APPEND = "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"


def _sites(settings: Settings, project_id: str) -> list[sqlite3.Row]:
    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT caller, callee, kind, dex_name, instruction_offset "
            "FROM call_sites WHERE project_id = ? "
            "ORDER BY caller, callee, kind, dex_name, instruction_offset",
            (project_id,),
        ).fetchall()


# -- the index holds the sites, and the edges are derived from them ----------


def test_two_calls_to_one_target_are_two_sites_and_one_edge(settings: Settings) -> None:
    """The demo app calls StringBuilder.append twice from the same method.

    The two calls are at two different offsets in the caller's bytecode, so
    they are two call sites -- two rows in the index -- and one call edge,
    because the relationship between the two methods did not change. An index
    that cannot tell the two apart says "two calls" without saying where
    they were, and a reader cannot tell that from a call listed twice.
    """
    result = Analyzer(settings).analyze(DEMO_APK)

    sites = _sites(settings, result.project.id)
    repeated = [row for row in sites if row["callee"] == _APPEND]

    by_caller: dict[str, list[sqlite3.Row]] = {}
    for row in repeated:
        by_caller.setdefault(row["caller"], []).append(row)
    twice = {caller: rows for caller, rows in by_caller.items() if len(rows) == 2}

    assert twice, "no caller calls StringBuilder.append twice"
    for caller, rows in twice.items():
        offsets = {row["instruction_offset"] for row in rows}
        assert len(offsets) == 2, f"the two sites of {caller} are at the same offset: {offsets}"
        # One edge: the same caller, the same callee, the same opcode.
        edges = {(row["caller"], row["callee"], row["kind"]) for row in rows}
        assert len(edges) == 1, "the two calls make one edge"


def test_the_index_holds_more_sites_than_it_holds_edges(settings: Settings) -> None:
    """The two numbers are different numbers, and the project says which is which."""
    result = Analyzer(settings).analyze(DEMO_APK)

    sites = _sites(settings, result.project.id)
    edges = {(row["caller"], row["callee"], row["kind"]) for row in sites}

    assert result.project.reference_count == len(sites)
    assert result.project.call_edge_count == len(edges)
    assert result.project.reference_count > result.project.call_edge_count, (
        "a method that calls the same target twice is two sites and one edge"
    )


def test_a_site_says_which_dex_file_and_where_in_the_bytecode(settings: Settings) -> None:
    """A site names the file and the offset; the edge alone cannot."""
    result = Analyzer(settings).analyze(DEMO_APK)

    sites = _sites(settings, result.project.id)

    assert all(row["dex_name"] for row in sites), "every site names the dex file it was read from"
    assert all(row["instruction_offset"] >= 0 for row in sites), (
        "every site names the instruction it was read from"
    )


# -- the edges are derived from the sites, never the other way round ----------


def test_the_edges_come_out_of_the_sites() -> None:
    """Two sites of the same relationship are one edge, and the edge says how many."""
    first = CallSite(
        caller="com.example.A.run()V",
        callee="com.example.B.go()V",
        kind=InvocationKind.VIRTUAL,
        dex_name="classes.dex",
        instruction_offset=0x10,
    )
    second = CallSite(
        caller="com.example.A.run()V",
        callee="com.example.B.go()V",
        kind=InvocationKind.VIRTUAL,
        dex_name="classes.dex",
        instruction_offset=0x20,
    )
    other = CallSite(
        caller="com.example.A.run()V",
        callee="com.example.B.go()V",
        kind=InvocationKind.STATIC,
        dex_name="classes.dex",
        instruction_offset=0x30,
    )

    edges = derive_edges([first, second, other])

    # Two edges: the same two methods called in two different ways are two
    # relationships.
    assert len(edges) == 2
    counts = sorted(edge.site_count for edge in edges)
    assert counts == [1, 2], "the edge made of two sites says so"


def test_the_edges_are_in_a_fixed_order() -> None:
    """Two runs over the same APK produce the same list, and so the same evidence ids."""
    site = CallSite(
        caller="com.example.A.run()V",
        callee="com.example.B.go()V",
        kind=InvocationKind.VIRTUAL,
        dex_name="classes.dex",
        instruction_offset=0x10,
    )

    assert derive_edges([site]) == derive_edges([site])


# -- the report and the API say which of the two they are counting -----------


def test_the_report_states_both_numbers(settings: Settings) -> None:
    """A report that prints both without saying which asks the reader to guess."""
    result = Analyzer(settings).analyze(DEMO_APK)

    report = render_markdown(result)

    assert f"| Call sites indexed | {result.project.reference_count:,} |" in report
    assert f"| Call edges indexed | {result.project.call_edge_count:,} |" in report
    assert "| Call sites with evidence |" in report
    assert "| Call edges with evidence |" in report
    # The note that says what the two are, before the reader moves on.
    assert "call site" in report
    assert "call edge" in report


# -- a workspace written before the call sites existed -----------------------


def test_a_workspace_written_before_the_call_sites_is_rebuilt(tmp_path: Path) -> None:
    """The old table is replaced, and the project's count of it goes with it.

    The table is a cache of an analysis rather than a source of truth: the
    next analysis fills it again. What must not happen is the record saying
    "23 cross-references" while the table holds nothing -- a reader would
    query and find a different answer than the one on the record.
    """
    path = tmp_path / "dexatlas.db"
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                apk_sha256 TEXT NOT NULL UNIQUE,
                apk_path TEXT NOT NULL,
                apk_size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                tool_versions TEXT NOT NULL DEFAULT '{}',
                errors TEXT NOT NULL DEFAULT '[]',
                class_count INTEGER NOT NULL DEFAULT 0,
                method_count INTEGER NOT NULL DEFAULT 0,
                reference_count INTEGER NOT NULL DEFAULT 0,
                evidence_count INTEGER NOT NULL DEFAULT 0,
                resource_count INTEGER NOT NULL DEFAULT 0,
                duration_seconds REAL,
                manifest TEXT,
                workspace TEXT
            );
            CREATE TABLE xrefs (
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                caller     TEXT NOT NULL,
                callee     TEXT NOT NULL,
                kind       TEXT NOT NULL DEFAULT 'invoke',
                provenance TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE schema_info (version INTEGER NOT NULL);
            """
        )
        connection.execute(
            "INSERT INTO projects (id, apk_sha256, apk_path, apk_size_bytes, created_at, status, "
            "reference_count) VALUES ('apk_old', ?, 'old.apk', 1, '2020-01-01T00:00:00+00:00', "
            "'completed', 23)",
            ("f" * 64,),
        )
        connection.execute(
            "INSERT INTO xrefs VALUES ('apk_old', 'com.example.A.run()V', 'com.example.B.go()V', "
            "'invoke', '[]')"
        )
        connection.execute("INSERT INTO schema_info (version) VALUES (4)")
        connection.commit()
    finally:
        connection.close()

    store = Store.open(path)

    with store.transaction() as opened:
        tables = {
            row["name"]
            for row in opened.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "call_sites" in tables, "the call-site table was not created"
        assert "xrefs" not in tables, "the old table is still there"
        row = opened.execute(
            "SELECT reference_count, call_edge_count FROM projects WHERE id = 'apk_old'"
        ).fetchone()
        assert row["reference_count"] == 0, "the count outlived the rows it counted"
        assert row["call_edge_count"] == 0
        sites = opened.execute(
            "SELECT COUNT(*) FROM call_sites WHERE project_id = 'apk_old'"
        ).fetchone()[0]
        assert sites == 0

    assert SCHEMA_VERSION == 5
