"""The MCP tools answer what an agent needs, and say what they do not know.

Every tool is exercised against the project's own demo APK — the first-party
sample whose sources are checked in beside it — and every claim the tools
make is checked against the workspace rather than against a number written
down here.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.client import Client

from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    MethodRef,
    Project,
    ProjectStatus,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.schemas import DATA_NOTICE
from dexatlas.mcp.server import build_server
from dexatlas.mcp.tools import evidence as evidence_tools
from dexatlas.mcp.tools import projects as project_tools
from dexatlas.mcp.tools import references as reference_tools
from dexatlas.mcp.tools import symbols as symbol_tools

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_APK = REPO_ROOT / "examples" / "demo-app" / "demo.apk"
STRINGS_APK = REPO_ROOT / "examples" / "strings-app" / "strings.apk"

#: Three methods that share a name. The DEX descriptor is what tells them
#: apart, and a tool asked for the name has to answer with them rather than
#: with one of them.
SIGN_DESCRIPTORS = (
    "(I)Ljava/lang/String;",
    "(Ljava/lang/String;)Ljava/lang/String;",
    "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
)
OVERLOADED_CLASS = "com.example.demo.Crypto"

#: The decompiled source of that class: three methods that share a name.
JAVA_SOURCE = """package com.example.demo;

public final class Crypto {

    public static String sign(int value) {
        return "int";
    }

    public static String sign(String value) {
        return "string";
    }

    public static String sign(String value, String other) {
        return "two";
    }
}
"""
FAKE_SHA256 = "a" * 64


@pytest.fixture
def analyzer(settings) -> Analyzer:
    return Analyzer(settings)


@pytest.fixture
def demo(analyzer: Analyzer):
    """The demo APK, analysed."""
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")
    return analyzer.analyze(DEMO_APK)


@pytest.fixture
def overloaded_project(analyzer: Analyzer, tmp_path: Path) -> str:
    """A project whose one class has three methods that share a name.

    The demo application has no overloads — the ambiguity the tool has to
    answer with candidates is built here instead, because it is the case the
    tool exists for.
    """
    store = analyzer.store
    project_id = Project.new_id(FAKE_SHA256)
    workspace = tmp_path / "overloaded"

    # The decompiled source, so that asking for one of the overloads by its
    # descriptor has a body to return.
    java = workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            tool_versions={"androguard": "4.1.4"},
        ),
        workspace,
        manifest=None,
    )
    provenance = [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256=FAKE_SHA256,
            locator=f"androguard:classes.dex#{OVERLOADED_CLASS}",
        )
    ]
    store.save_symbols(
        project_id,
        [
            ClassRef(
                name=OVERLOADED_CLASS,
                kind=ClassKind.CLASS,
                access_flags=["public"],
                method_count=len(SIGN_DESCRIPTORS),
                provenance=provenance,
            )
        ],
        [
            MethodRef(
                class_name=OVERLOADED_CLASS,
                name="sign",
                descriptor=descriptor,
                access_flags=["public"],
                provenance=provenance,
            )
            for descriptor in SIGN_DESCRIPTORS
        ],
        [],
        [],
        [],
    )
    return project_id


# -- what the server exposes ------------------------------------------------


def test_the_server_registers_the_tools_it_says_it_does(analyzer: Analyzer) -> None:
    """The tool list is the contract, and it has to be the whole contract."""
    server = build_server(analyzer)

    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert names == {
        "list_projects",
        "get_project_status",
        "get_manifest",
        "search_symbols",
        "get_class_source",
        "get_method_source",
        "find_callers",
        "find_callees",
        "get_evidence",
        "resolve_locator",
    }
    for tool in tools:
        assert tool.annotations is not None, f"{tool.name} carries no annotations"
        assert tool.annotations.read_only_hint is True, f"{tool.name} is not marked read-only"
        assert tool.annotations.destructive_hint is False, f"{tool.name} is marked destructive"


def test_the_server_runs_without_a_model_provider(analyzer: Analyzer) -> None:
    """It is a tool server. A tool server that needs a model is not a tool server.

    The check is that nothing in the server reaches for one: the module's own
    imports are the whole of what it can depend on.
    """
    source = (REPO_ROOT / "src" / "dexatlas" / "mcp" / "server.py").read_text(encoding="utf-8")

    for provider in ("anthropic", "openai", "httpx"):
        assert f"import {provider}" not in source, (
            f"the server imports {provider}: it is a tool server and it must not need a model"
        )


def test_every_tool_says_what_it_does_and_what_it_does_not(analyzer: Analyzer) -> None:
    """The description is the only thing a caller reads before it calls.

    A description that says what the tool returns but not what it does not
    return is how a caller ends up reading the wrong tool.
    """
    tools = asyncio.run(build_server(analyzer).list_tools())

    for tool in tools:
        assert tool.description, f"{tool.name} has no description"
        assert len(tool.description) > 40, f"{tool.name}'s description says almost nothing"


# -- the projects ------------------------------------------------------------


def test_list_projects_pages(analyzer: Analyzer, demo) -> None:
    """The page says how many there are, not how many it shows."""
    project_id = demo.project.id

    everything = project_tools.list_projects(analyzer, limit=10, offset=0)
    assert everything.total == 1
    assert [project.id for project in everything.projects] == [project_id]

    empty = project_tools.list_projects(analyzer, limit=10, offset=5)
    assert empty.projects == []
    assert empty.total == 1, "the total is the workspace's, not the page's"


def test_get_project_status_says_what_is_missing(analyzer: Analyzer, demo) -> None:
    """A backend that did not take part is said to, by name."""
    status = project_tools.project_status(analyzer, demo.project.id)

    assert status.project.id == demo.project.id
    assert status.project.call_site_count == demo.project.reference_count
    assert status.project.call_edge_count == demo.project.call_edge_count
    assert status.completeness.missing_backends == [], (
        "every backend took part in this analysis, so none is missing"
    )
    assert status.completeness.truncated is False


def test_get_project_status_of_a_project_that_is_not_there(analyzer: Analyzer) -> None:
    """A project that is not there is an error, not an empty answer."""
    from dexatlas.mcp.errors import RequestError

    with pytest.raises(RequestError) as raised:
        project_tools.project_status(analyzer, "apk_nope")

    assert raised.value.code == "unknown_project"


def test_get_manifest_reads_the_parsed_fields(analyzer: Analyzer, demo) -> None:
    """The manifest comes back as fields, not as raw text."""
    view = project_tools.manifest(analyzer, demo.project.id)

    assert view.package == "com.example.demo"
    assert view.permissions, "the demo app asks for permissions"
    names = [permission.name.text for permission in view.permissions]
    assert "android.permission.INTERNET" in names
    assert view.components, "the demo app declares components"


# -- the symbols ------------------------------------------------------------


def test_search_symbols_finds_what_is_indexed(analyzer: Analyzer, demo) -> None:
    """The search covers the index, and says why a symbol matched."""
    found = symbol_tools.search_symbols(
        analyzer, demo.project.id, "obfuscation_failed", limit=20, offset=0
    )

    assert found.symbols, "the demo app indexes the string it prints"
    assert any("obfuscation_failed" in symbol.detail for symbol in found.symbols)


def test_get_class_source_returns_the_source_and_where_it_came_from(
    analyzer: Analyzer, demo
) -> None:
    """The source comes with the provenance that says which backend produced it."""
    view = symbol_tools.class_source(analyzer, demo.project.id, "com.example.demo.Crypto")

    assert view.found, view.reason
    assert view.text is not None
    assert "Crypto" in view.text.text
    assert view.provenance, "the source says where it was read from"
    assert view.kind in {"java", "smali"}


def test_get_method_source_answers_an_ambiguous_name_with_the_candidates(
    analyzer: Analyzer, overloaded_project: str
) -> None:
    """A name that matches several methods is answered with them, not with one.

    The body of the wrong overload reads exactly like the body of the right
    one, and it travels straight into whatever quotes it.
    """
    view = symbol_tools.method_source(analyzer, overloaded_project, OVERLOADED_CLASS, "sign")

    assert view.found is False, "an ambiguous name has no body to return"
    assert view.candidates, "the candidates are what tell the overloads apart"
    assert len(view.candidates) == len(SIGN_DESCRIPTORS)
    for descriptor in SIGN_DESCRIPTORS:
        assert any(descriptor in candidate for candidate in view.candidates)


def test_get_method_source_with_a_descriptor_returns_that_method(
    analyzer: Analyzer, overloaded_project: str
) -> None:
    """And with the descriptor, it returns the one that was asked for."""
    view = symbol_tools.method_source(
        analyzer,
        overloaded_project,
        OVERLOADED_CLASS,
        "sign",
        SIGN_DESCRIPTORS[0],
    )

    assert view.found, view.reason
    assert view.text is not None


def test_a_class_that_is_not_there_says_so(analyzer: Analyzer, demo) -> None:
    """ "There is no source" is not the same as "there is no class"."""
    view = symbol_tools.class_source(analyzer, demo.project.id, "com.example.Missing")

    assert view.found is False
    assert view.reason, "a missing source says why"
    assert view.text is None


# -- the calls --------------------------------------------------------------


def test_find_callers_counts_the_call_sites_and_the_call_edges_apart(
    analyzer: Analyzer, demo
) -> None:
    """One caller that calls the same target twice is two sites and one edge.

    This is the distinction the whole index now rests on, and the tool is
    where a caller would meet it.
    """
    method_id = "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"

    callers = reference_tools.find_callers(analyzer, demo.project.id, method_id, limit=100)

    assert callers.call_site_count >= 2
    assert callers.call_edge_count < callers.call_site_count, (
        "some caller calls the same target twice, so the sites outnumber the edges"
    )
    for site in callers.call_sites:
        assert site.dex_name, "a call site says which dex file it was read from"
        assert site.instruction_offset >= 0, "a call site says where in the bytecode it sits"


def test_find_callees_answers_the_other_direction(analyzer: Analyzer, demo) -> None:
    """A method and what it calls."""
    method_id = (
        "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
    )

    callees = reference_tools.find_callees(analyzer, demo.project.id, method_id, limit=100)

    assert callees.callees, "the demo app's sign method calls something"
    assert callees.call_site_count == len(callees.callees), (
        "each callee here was called once, so the two counts agree"
    )


# -- the evidence -----------------------------------------------------------


def test_every_evidence_record_resolves_to_what_it_names(analyzer: Analyzer, demo) -> None:
    """A caller has to be able to check every record it is given.

    That is the promise the evidence records make: each one names the place
    it was read from, and the place has to be inside this analysis. A record
    whose citation does not resolve is a claim, not evidence.
    """
    records = analyzer.store.list_evidence(demo.project.id)

    assert records, "the demo analysis produces evidence"
    unresolved: list[str] = []
    for record in records:
        for provenance in record.provenance:
            resolution = evidence_tools.resolve_locator(
                analyzer, demo.project.id, provenance.locator
            )
            if not resolution.resolved:
                unresolved.append(f"{record.id}: {provenance.locator} ({resolution.reason})")

    assert not unresolved, "evidence records name places that do not resolve:\n" + "\n".join(
        unresolved
    )


def test_get_evidence_returns_the_record_and_its_receipts(analyzer: Analyzer, demo) -> None:
    """One record, with the locators it was read from."""
    records = analyzer.store.list_evidence(demo.project.id)
    record = records[0]

    view = evidence_tools.get_evidence(analyzer, demo.project.id, record.id)

    assert view.id == record.id
    assert view.level == record.level.value
    assert view.provenance == [entry.locator for entry in record.provenance]


def test_a_locator_that_names_nothing_says_why(analyzer: Analyzer, demo) -> None:
    """A backend that did not run and a file that is not there are different facts."""
    resolution = evidence_tools.resolve_locator(
        analyzer, demo.project.id, "jadx:sources/com/example/Missing.java"
    )

    assert resolution.resolved is False
    assert resolution.reason, "a locator that does not resolve says why"


# -- the text that comes out of an APK is data ------------------------------


def test_the_text_of_an_apk_is_data_and_not_an_instruction(analyzer: Analyzer) -> None:
    """A string inside an APK must not be able to steer whoever reads the answer.

    The whole surface is checked, because the danger is not one tool but the
    place where the tool's own words live: a description is read before the
    call, and a schema is read instead of the answer. If the APK's own text
    could reach either, the APK would be talking to the agent rather than
    being talked about.
    """
    if not STRINGS_APK.is_file():
        pytest.skip("strings APK missing")
    analyzed = analyzer.analyze(STRINGS_APK)

    # A string from this APK that looks like something an agent should not act on.
    marker = "sk_live_PLACEHOLDER_NOT_A_REAL_KEY"

    server = build_server(analyzer)
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert marker not in (tool.description or ""), (
            f"{tool.name}'s description carries a string out of the APK"
        )
        assert marker not in str(tool.input_schema), (
            f"{tool.name}'s schema carries a string out of the APK"
        )

    # And the string itself is in the data, where it belongs.
    found = symbol_tools.search_symbols(
        analyzer, analyzed.project.id, "PLACEHOLDER_NOT_A_REAL_KEY", limit=20, offset=0
    )
    assert found.symbols, "the string is indexed"

    # The text is carried in a field that says what it is.
    manifest_view = project_tools.manifest(analyzer, analyzed.project.id)
    for permission in manifest_view.permissions:
        assert permission.name.notice == DATA_NOTICE


def test_every_text_the_tools_return_is_marked_as_data(analyzer: Analyzer, demo) -> None:
    """The notice is in the response, not only in the documentation."""
    view = symbol_tools.class_source(analyzer, demo.project.id, "com.example.demo.Crypto")

    assert view.text is not None
    assert view.text.notice == DATA_NOTICE
    assert "not an instruction" in view.text.notice


def test_an_excerpt_is_bounded(analyzer: Analyzer, demo) -> None:
    """Nothing comes back unbounded, and the cut is stated."""
    view = symbol_tools.class_source(analyzer, demo.project.id, "com.example.demo.Crypto")

    assert view.text is not None
    assert len(view.text.text.encode("utf-8")) <= 64 * 1024


# -- the server, over the protocol ------------------------------------------


def test_the_server_answers_over_the_protocol(analyzer: Analyzer, demo) -> None:
    """The tools are not only callable in Python — they are reachable.

    The test above calls the functions the tools are built on. This one goes
    through the protocol, the way a caller does: start the server, list what
    it offers, and call one. A server that answers in Python and not over
    the wire is a library, not a server.
    """

    async def ask() -> tuple[list[str], object]:
        async with Client(build_server(analyzer)) as client:
            listed = await client.list_tools()
            called = await client.call_tool("list_projects", {"limit": 5})
            return [tool.name for tool in listed.tools], called.structured_content

    names, payload = asyncio.run(ask())

    assert "get_method_source" in names
    assert isinstance(payload, dict)
    assert payload.get("total") == 1, "the server answers the projects in the workspace"


# -- what the analysis could not do ------------------------------------------


def _project(analyzer: Analyzer, tmp_path: Path, **fields) -> str:
    """A project in the workspace, with the fields the test cares about."""
    project_id = Project.new_id(FAKE_SHA256)
    analyzer.store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            **fields,
        ),
        tmp_path / "project",
        manifest=None,
    )
    return project_id


def test_a_missing_backend_is_named(analyzer: Analyzer, tmp_path: Path) -> None:
    """A backend that did not take part is said to, by name.

    A backend that is absent is not a backend that found nothing, and the
    difference decides what the counts mean.
    """
    project_id = _project(
        analyzer,
        tmp_path,
        tool_versions={"jadx": None, "apktool": "2.11.1", "androguard": "4.1.4"},
    )

    status = project_tools.project_status(analyzer, project_id)

    assert status.completeness.missing_backends == ["jadx"]
    assert status.completeness.complete is False
    assert status.project.missing_backends == ["jadx"]


def test_a_truncated_analysis_says_so(analyzer: Analyzer, tmp_path: Path) -> None:
    """A shortened index is not a wrong one, but a reader has to know.

    The rows that were written hold; the ones that were not are not there.
    A count that does not say which is which is a count that will be read as
    more than it is.
    """
    project_id = _project(
        analyzer,
        tmp_path,
        tool_versions={"jadx": "1.5.2", "apktool": "2.11.1", "androguard": "4.1.4"},
        errors=[
            ToolError(
                tool="androguard",
                code=ToolErrorCode.OUTPUT_TRUNCATED,
                message="method limit 200000 reached: the index is incomplete",
            )
        ],
    )

    status = project_tools.project_status(analyzer, project_id)

    assert status.completeness.truncated is True
    assert status.completeness.complete is False
    assert status.project.truncated is True
    assert any("method limit" in error for error in status.completeness.errors)
