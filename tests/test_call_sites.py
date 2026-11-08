"""A call site and a call edge are two different things, and the index keeps both.

The cross-reference index used to hold one row per *call*, with no primary key,
so the same relationship could be written twice and the project record counted
the calls where it meant the relationships. A reader who read "23
cross-references" was reading 21 relationships twice over.

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

And the index holds the sites, because a site says *where*: the dex file and
the offset are what let a reader follow a citation back to the bytes it came
from. The edges are derived from them, never stored beside them, so the two
cannot disagree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.calls import CallSite, derive_edges
from dexatlas.core.models import (
    ApkMetadata,
    InvocationKind,
    Project,
    ProjectStatus,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.androguard.adapter import androguard_available

DEMO_APK = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"

#: The method the demo app calls twice. Its body appends to a StringBuilder
#: once for each of its two arguments.
_TWICE_CALLED = "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"

#: The method that calls it twice.
_CALLS_TWICE = (
    "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
)

_PROVENANCE = [
    Provenance(
        tool="androguard",
        tool_version="4.1.4",
        apk_sha256="c" * 64,
        locator="androguard:classes.dex#com.example.demo.Crypto",
    )
]


@pytest.fixture
def demo(settings: Settings):
    """The demo app, analysed, with the store it was written to."""
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")
    if not androguard_available():
        pytest.skip("androguard not installed")
    analyzer = Analyzer(settings)
    return analyzer, analyzer.analyze(DEMO_APK)


def _site(offset: int, *, dex_name: str = "classes.dex") -> CallSite:
    """One call site, at a given offset."""
    return CallSite(
        caller=_CALLS_TWICE,
        callee=_TWICE_CALLED,
        kind=InvocationKind.INVOKE,
        dex_name=dex_name,
        instruction_offset=offset,
        provenance=_PROVENANCE,
    )


# -- one method, two calls ---------------------------------------------------


def test_one_method_calling_the_same_target_twice_is_two_call_sites(demo) -> None:
    """Two invoke instructions are two places in the bytecode."""
    analyzer, result = demo

    sites = [
        site
        for site in analyzer.store.list_callees(result.project.id, _CALLS_TWICE)
        if site.callee == _TWICE_CALLED
    ]

    assert len(sites) == 2, "the demo app calls StringBuilder.append twice"
    assert {site.instruction_offset for site in sites} == {10, 18}
    for site in sites:
        assert site.dex_name == "classes.dex"
        assert site.provenance, "a call site has to say where it was read from"


def test_the_same_two_calls_make_one_edge(demo) -> None:
    """The relationship between two methods is one thing, not two."""
    analyzer, result = demo

    edges = [
        edge
        for edge in derive_edges(analyzer.store.list_callees(result.project.id, _CALLS_TWICE))
        if edge.callee == _TWICE_CALLED
    ]

    assert len(edges) == 1
    assert edges[0].caller == _CALLS_TWICE
    assert edges[0].callee == _TWICE_CALLED
    assert edges[0].site_count == 2, "the edge knows how many places it comes from"


def test_the_index_holds_one_row_per_call_site(demo) -> None:
    """The table is keyed, so the same site cannot be written twice."""
    analyzer, result = demo
    project_id = result.project.id

    with analyzer.store.transaction() as connection:
        columns = list(connection.execute("PRAGMA table_info(call_sites)"))
        rows = connection.execute(
            "SELECT caller, callee, dex_name, instruction_offset "
            "FROM call_sites WHERE project_id = ?",
            (project_id,),
        ).fetchall()

    # The table has a primary key, and it carries the position: the old one
    # had neither, so the same edge could be written twice and nothing would
    # say so.
    assert any(column["pk"] for column in columns)
    keys = {
        (row["caller"], row["callee"], row["dex_name"], row["instruction_offset"]) for row in rows
    }
    assert len(rows) == len(keys), "the same call site is in the table twice"

    # The rows are the sites, not the relationships: the method that calls
    # the same target twice contributes two of them.
    twice = [
        row for row in rows if row["caller"] == _CALLS_TWICE and row["callee"] == _TWICE_CALLED
    ]
    assert len(twice) == 2


def test_the_project_counts_the_sites_and_the_edges_apart(demo) -> None:
    """The two numbers are both there, and neither stands in for the other.

    The index holds the call sites, so the number of rows in it is the number
    of them. The edges are what those sites add up to, and there are fewer of
    them: the demo app calls StringBuilder.append twice from one method, and
    that is two sites and one edge.
    """
    _, result = demo

    assert result.project.reference_count == 23, "the indexed call sites"
    assert result.project.call_edge_count == 21, "the relationships between two methods"


# -- the two kinds of duplication --------------------------------------------


def test_a_method_duplicated_across_two_dex_files_is_one_edge() -> None:
    """The same call read from two dex files is one relationship.

    A method defined in two DEX files has two copies of its body, and each
    copy holds its own call sites. They are two places in the bytecode, and
    they are one relationship between two methods.
    """
    sites = [_site(10, dex_name="classes.dex"), _site(10, dex_name="classes2.dex")]

    edges = derive_edges(sites)

    assert len(edges) == 1
    assert edges[0].site_count == 2


def test_the_edges_are_derived_from_the_call_sites() -> None:
    """The edge is what the sites add up to, never the other way round.

    A caller that derived the sites from the edges would lose the second
    call of a method that calls the same target twice, and the citation that
    says where the second one is would have nothing to point at.
    """
    sites = [_site(10), _site(18)]

    edges = derive_edges(sites)

    assert len(edges) == 1
    assert edges[0].site_count == len(sites)
    assert len(sites) == 2, "the sites are the ones that were handed in"


def test_the_two_units_survive_a_round_trip_through_the_store(
    settings: Settings,
) -> None:
    """What is written is what is read back.

    A site that lost its position on the way into the database would be a
    site the index cannot tell apart from another one at the same place, and
    the count would be right for the wrong reason.
    """
    from dexatlas.core.storage import Store

    store = Store.open(settings.database_path)
    project_id = Project.new_id("c" * 64)
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256="c" * 64, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
        ),
        None,
        manifest=None,
    )
    store.save_symbols(project_id, [], [], [], [_site(10), _site(18)], [], [])

    read_back = store.list_callees(project_id, _CALLS_TWICE)

    assert len(read_back) == 2
    assert {site.instruction_offset for site in read_back} == {10, 18}
    assert all(site.dex_name == "classes.dex" for site in read_back)


def test_a_call_site_survives_the_worker_boundary() -> None:
    """The offset has to come back with the site.

    The DEX is parsed in another process, so the site is encoded and decoded
    on the way. A field that did not survive that trip would leave the index
    with a call and no place, which is the state the index was rebuilt to
    stop being in.
    """
    from dexatlas.tools.androguard.isolation import (
        WorkerResult,
        decode_result,
        encode_result,
    )

    encoded = encode_result(
        WorkerResult(
            classes=[], methods=[], fields=[], references=[_site(10), _site(18)], strings=[]
        )
    )

    decoded = decode_result(encoded)

    assert [site.instruction_offset for site in decoded.references] == [10, 18]
    assert all(site.dex_name == "classes.dex" for site in decoded.references)


def test_the_callees_of_a_method_are_the_methods_it_calls(demo) -> None:
    """The other direction is the other direction.

    The two questions have the same shape and opposite answers, and a store
    that answers both with the same query answers one of them wrongly. A
    reader who asked what a method calls and was told who calls it has been
    told something true about the wrong thing.
    """
    analyzer, result = demo

    sites = analyzer.store.list_callees(result.project.id, _CALLS_TWICE)

    assert sites, "the demo app's Crypto.sign calls StringBuilder.append"
    for site in sites:
        assert site.caller == _CALLS_TWICE
    assert _TWICE_CALLED in {site.callee for site in sites}


def test_the_callers_of_a_method_are_the_methods_that_call_it(demo) -> None:
    """The other half of the pair."""
    analyzer, result = demo

    sites = analyzer.store.get_method_references(result.project.id, _TWICE_CALLED)

    assert sites, "the demo app's Crypto.sign calls StringBuilder.append"
    for site in sites:
        assert site.callee == _TWICE_CALLED
    assert _CALLS_TWICE in {site.caller for site in sites}
