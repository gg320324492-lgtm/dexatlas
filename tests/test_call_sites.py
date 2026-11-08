"""A call site and a call edge are two different things, and the index keeps both.

The cross-reference index used to hold one row per *call*, with no primary key,
so the same edge could be written twice and the project record counted the
calls where it meant the relationships. A reader who read "23 cross-references"
was reading 21 edges twice over, and the API's ``total`` answered "4" to the
question "how many places call this method" when there were 2.

These tests pin the two units apart:

* a **call site** is one place in the bytecode — a dex file, an instruction
  offset, an opcode, a caller and a callee;
* a **call edge** is the relationship between two methods, derived from the
  call sites.

The two kinds of duplication need different treatment, and a design that only
handles one of them is the bug this file exists for:

* one method calling the same target twice is **two call sites and one edge**;
* the same method defined in two dex files is **two call sites and one edge**
  as well — the sites differ in the dex file rather than in the offset.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.calls import CallSite, derive_edges
from dexatlas.core.models import (
    ApkMetadata,
    InvocationKind,
    Project,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.storage import Store
from dexatlas.tools.androguard.adapter import androguard_available

DEMO_APK = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"
MULTIDEX_APK = Path(__file__).parent.parent / "examples" / "multidex-app" / "multidex.apk"

#: The method the demo app calls twice. Its body appends to a StringBuilder
#: once for each of its two arguments.
_TWICE_CALLED = "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"

#: The method that calls it twice.
_CALLS_TWICE = (
    "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
)


@pytest.fixture
def demo(settings: Settings):
    """The demo app, analysed, with the store it was written to."""
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")
    if not androguard_available():
        pytest.skip("androguard not installed")
    analyzer = Analyzer(settings)
    return analyzer, analyzer.analyze(DEMO_APK)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A client wired to an isolated workspace."""
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


# -- one method, two calls ---------------------------------------------------


def test_one_method_calling_the_same_target_twice_is_two_call_sites(demo) -> None:
    """Two invoke instructions are two places in the bytecode.

    The index used to hold one row per call with no primary key, so these two
    calls were two rows that no query could tell apart, and the edge they make
    was counted twice.
    """
    analyzer, _ = demo
    project_id = analyzer.store.get_project(next(iter(analyzer.store.list_projects())).id).id

    sites = analyzer.store.get_method_call_sites(project_id, _TWICE_CALLED)

    # Two callers, each calling it twice.
    assert len(sites) == 4
    sign_sites = [site for site in sites if site.caller == _CALLS_TWICE]
    assert len(sign_sites) == 2
    # The two calls sit at different offsets: that is what tells them apart.
    assert len({site.instruction_offset for site in sign_sites}) == 2
    assert all(site.dex_name == "classes.dex" for site in sign_sites)


def test_the_same_two_calls_make_one_edge(demo) -> None:
    """The relationship between two methods is one thing, not two."""
    analyzer, _ = demo
    project_id = next(iter(analyzer.store.list_projects())).id

    edges = analyzer.store.get_method_references(project_id, _TWICE_CALLED)

    # Two callers, one edge each.
    assert len(edges) == 2
    assert {edge.caller for edge in edges} == {
        _CALLS_TWICE,
        "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;",
    }
    # And the edge says how many call sites it is made of.
    sign_edge = next(edge for edge in edges if edge.caller == _CALLS_TWICE)
    assert sign_edge.site_count == 2


def test_the_index_holds_one_row_per_edge(demo) -> None:
    """The cross-reference table is keyed, so an edge cannot be written twice."""
    analyzer, _ = demo
    project_id = next(iter(analyzer.store.list_projects())).id

    with analyzer.store.transaction() as connection:
        columns = list(connection.execute("PRAGMA table_info(xrefs)"))
        rows = connection.execute(
            "SELECT caller, callee FROM xrefs WHERE project_id = ?", (project_id,)
        ).fetchall()

    # The table has a primary key: the old one had none, so the same edge could
    # be written twice and nothing would say so.
    assert any(column["pk"] for column in columns)
    # One row per edge: the rows are distinct where they used to be duplicated.
    assert len(rows) == len({(row["caller"], row["callee"]) for row in rows})
    assert len(rows) == 21


def test_the_project_counts_the_edges_and_the_result_counts_the_sites(demo) -> None:
    """The two numbers are both there, and neither stands in for the other."""
    _, result = demo

    # The project record counts the relationships between two methods.
    assert result.project.reference_count == 21
    # The result counts the places in the bytecode where a call happens.
    assert result.call_site_count == 23


# -- the two kinds of duplication --------------------------------------------


def test_a_method_duplicated_across_two_dex_files_is_one_edge(settings: Settings) -> None:
    """The same call read from two dex files is one relationship.

    The two copies of the method are two places in the bytecode, so they are
    two call sites; but they are the same call made by the same method, so
    they are one edge. A design that keyed the edge on the dex file would
    count one call twice.
    """
    if not MULTIDEX_APK.is_file():
        pytest.skip("multi-dex sample missing")
    if not androguard_available():
        pytest.skip("androguard not installed")

    analyzer = Analyzer(settings)
    result = analyzer.analyze(MULTIDEX_APK)
    project_id = result.project.id

    # The duplicated class's constructor calls Object's constructor from both
    # dex files.
    sites = analyzer.store.get_method_call_sites(project_id, "java.lang.Object.<init>()V")
    shared = [site for site in sites if "SharedConfig" in site.caller]
    assert len(shared) == 2
    # Two dex files, one logical call.
    assert {site.dex_name for site in shared} == {"classes.dex", "classes2.dex"}

    # And the edge they make is one.
    edges = analyzer.store.get_method_references(project_id, "java.lang.Object.<init>()V")
    shared_edges = [edge for edge in edges if "SharedConfig" in edge.caller]
    assert len(shared_edges) == 1
    assert shared_edges[0].site_count == 2


def test_the_edges_are_derived_from_the_call_sites(demo) -> None:
    """The edge is what the sites add up to, never the other way round."""
    analyzer, _ = demo
    project_id = next(iter(analyzer.store.list_projects())).id

    with analyzer.store.transaction() as connection:
        rows = connection.execute(
            "SELECT dex_name, caller, callee, kind, instruction_offset, provenance"
            " FROM call_sites WHERE project_id = ?",
            (project_id,),
        ).fetchall()

    sites = [
        CallSite(
            caller=row["caller"],
            callee=row["callee"],
            kind=InvocationKind(row["kind"]),
            dex_name=row["dex_name"],
            instruction_offset=row["instruction_offset"],
            provenance=[Provenance.model_validate(item) for item in json.loads(row["provenance"])],
        )
        for row in rows
    ]
    derived = derive_edges(sites)

    # The edges derived from the sites are the edges the table holds.
    assert len(derived) == 21
    with analyzer.store.transaction() as connection:
        stored = connection.execute(
            "SELECT caller, callee, kind FROM xrefs WHERE project_id = ?", (project_id,)
        ).fetchall()
    assert {(row["caller"], row["callee"], row["kind"]) for row in stored} == {
        (edge.caller, edge.callee, edge.kind.value) for edge in derived
    }


# -- the boundary ------------------------------------------------------------


def test_a_call_site_survives_the_worker_boundary() -> None:
    """The offset has to come back with the site.

    The DEX files are parsed in a process of their own, and what comes back is
    JSON. A field the receiving side does not rebuild is a field that was
    never read, and the two calls a method makes to the same target would
    collapse into one.
    """
    from dexatlas.tools.androguard.isolation import WorkerResult, decode_result, encode_result

    site = CallSite(
        caller="com.example.demo.Crypto.sign(Ljava/lang/String;)Ljava/lang/String;",
        callee="java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;",
        kind=InvocationKind.VIRTUAL,
        dex_name="classes.dex",
        instruction_offset=26,
        provenance=[
            Provenance(
                tool="androguard",
                tool_version="4.1.4",
                apk_sha256="c" * 64,
                locator="androguard:classes.dex#com.example.demo.Crypto"
                "#com.example.demo.Crypto.sign(Ljava/lang/String;)Ljava/lang/String;",
            )
        ],
    )
    payload = encode_result(
        WorkerResult(classes=[], methods=[], fields=[], references=[site], strings=[])
    )
    decoded = decode_result(payload)

    assert len(decoded.references) == 1
    assert decoded.references[0].instruction_offset == 26
    assert decoded.references[0].dex_name == "classes.dex"


# -- the migration -----------------------------------------------------------


_OLD_XREFS_TABLE = """
CREATE TABLE xrefs (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    caller     TEXT NOT NULL,
    callee     TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'invoke',
    provenance TEXT NOT NULL DEFAULT '[]'
);
"""


def test_a_workspace_written_before_the_call_sites_existed_is_rebuilt(
    tmp_path: Path,
) -> None:
    """An older workspace is brought forward, and its count is corrected.

    The old table held one row per call and had no primary key. The new one
    holds one row per edge, so the count on the project record has to be
    corrected with it: a record that says 23 while the table holds 21 is a
    number a reader cannot check.
    """
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE projects (id TEXT PRIMARY KEY, reference_count INTEGER NOT NULL DEFAULT 0)"
        )
        connection.execute(_OLD_XREFS_TABLE)
        connection.execute("INSERT INTO projects (id, reference_count) VALUES ('p1', 23)")
        # Two rows for the same edge -- the duplication the old table allowed --
        # and one more edge of its own.
        for callee in ("com.example.A.m()V", "com.example.A.m()V", "com.example.B.n()V"):
            connection.execute(
                "INSERT INTO xrefs (project_id, caller, callee, kind, provenance)"
                " VALUES (?,?,?,?,?)",
                (
                    "p1",
                    "com.example.Caller.c()V",
                    callee,
                    "invoke",
                    json.dumps(
                        [
                            {
                                "tool": "androguard",
                                "tool_version": "4.1.4",
                                "apk_sha256": "c" * 64,
                                "locator": (
                                    "androguard:classes.dex#com.example.Caller.c()V->" + callee
                                ),
                            }
                        ]
                    ),
                ),
            )
        connection.commit()
    finally:
        connection.close()

    store = Store.open(path)

    with store.transaction() as connection:
        columns = list(connection.execute("PRAGMA table_info(xrefs)"))
        rows = connection.execute(
            "SELECT caller, callee, provenance FROM xrefs WHERE project_id = ?", ("p1",)
        ).fetchall()
        counted = connection.execute(
            "SELECT reference_count FROM projects WHERE id = 'p1'"
        ).fetchone()

    # The table was rebuilt, so it has its primary key now.
    assert any(column["pk"] for column in columns)
    # The two rows of the same edge became one, and the other edge is still there.
    assert len(rows) == 2
    assert {row["callee"] for row in rows} == {"com.example.A.m()V", "com.example.B.n()V"}
    # No citation was lost in the rebuild.
    locators = [
        Provenance.model_validate(item).locator
        for row in rows
        for item in json.loads(row["provenance"])
    ]
    assert len(locators) == 2
    assert any("com.example.A.m()V" in locator for locator in locators)
    # And the project's own count agrees with the table.
    assert counted is not None
    assert counted["reference_count"] == len(rows) == 2


# -- what the API says --------------------------------------------------------


def test_the_api_states_which_unit_its_total_counts(client: TestClient, tmp_path: Path) -> None:
    """The number says what it counts, and the other count is beside it.

    The endpoint used to answer "4" to "how many places call this method",
    when there were two callers — a reader drew the wrong conclusion from a
    number that never said what it was counting.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    store = Store.open(settings.database_path)
    project = Project.create(ApkMetadata(sha256="c" * 64, size_bytes=1, path=tmp_path / "demo.apk"))
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(
        project.id,
        classes=[],
        methods=[],
        fields=[],
        call_sites=[
            CallSite(
                caller="com.example.Caller.c()V",
                callee="com.example.Target.m()V",
                kind=InvocationKind.VIRTUAL,
                dex_name="classes.dex",
                instruction_offset=offset,
                provenance=[
                    Provenance(
                        tool="androguard",
                        tool_version="4.1.4",
                        apk_sha256="c" * 64,
                        locator="androguard:classes.dex#com.example.Caller#com.example.Caller.c()V",
                    )
                ],
            )
            for offset in (4, 12)
        ],
        strings=[],
    )

    response = client.get(f"/projects/{project.id}/xrefs/com.example.Target.m()V")

    assert response.status_code == 200
    body = response.json()
    # The total counts the call edges -- one relationship, made of two calls.
    assert body["total"] == 1
    assert body["total_unit"] == "call_edges"
    assert body["call_edge_count"] == 1
    assert body["call_site_count"] == 2
    # And the places the calls were made are listed, with the offset each was
    # read from.
    assert len(body["call_sites"]) == 2
    assert {site["instruction_offset"] for site in body["call_sites"]} == {4, 12}
