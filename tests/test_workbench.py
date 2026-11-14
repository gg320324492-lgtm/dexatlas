"""The workbench transport.

The workbench sits on the MCP tools' plain-Python functions, so the point of
these tests is that it exposes them unchanged: the list, the status, the
symbol search, the source, the evidence, the locator resolutions and the
cross-references the browser gets are the same shapes the MCP server answers
with, an unknown project is the contract's ``unknown_project`` error as a 404,
and the front end is served when it is built and says how to build it when it
is not.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.config.settings import Settings
from dexatlas.core import ingest
from dexatlas.core.calls import CallSite
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    InvocationKind,
    MethodRef,
    MethodReference,
    Project,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.models import ProjectStatus as ProjectState
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.schemas import DATA_NOTICE, DEFAULT_LIMIT
from dexatlas.mcp.tools import references as reference_tools
from dexatlas.mcp.tools import symbols as symbol_tools
from dexatlas.workbench.app import create_app
from tests.conftest import build_apk

FAKE_SHA256 = "ab" * 32
CLASS_NAME = "com.example.demo.Crypto"
METHOD_NAME = "sign"
DESCRIPTOR = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
JAVA_SOURCE = """package com.example.demo;

public final class Crypto {
    public static String sign(String first, String second) {
        return first + second;
    }
}
"""

FOCAL_METHOD = "com.example.demo.Crypto.sign([B)[B"
FIRST_CALLER = "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"
SECOND_CALLER = "com.example.demo.MainActivity.onResume()V"
THIRD_CALLER = "com.example.demo.NetworkClient.send(Ljava/lang/String;)Ljava/lang/String;"
FIRST_CALLEE = "java.security.MessageDigest.digest([B)[B"
SECOND_CALLEE = "android.util.Base64.encodeToString([B)Ljava/lang/String;"
THIRD_CALLEE = "java.util.Arrays.copyOf([BI)[B"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A client wired to an isolated workspace, so tests never touch a real project DB."""
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    with TestClient(create_app(analyzer)) as test_client:
        yield test_client


@pytest.fixture
def project_id(client: TestClient) -> str:
    """One analysed project, written straight into the store."""
    analyzer: Analyzer = client.app.state.analyzer
    pid = Project.new_id(FAKE_SHA256)
    workspace = analyzer.settings.workspace / "projects" / pid
    analyzer.store.save_project(
        Project(
            id=pid,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectState.COMPLETED,
            tool_versions={"androguard": "4.1.4", "jadx": "1.5.2", "apktool": None},
            class_count=1,
            method_count=1,
            reference_count=0,
            call_edge_count=0,
            evidence_count=1,
        ),
        workspace,
        manifest=None,
    )
    # The index and one source file are enough to exercise the whole chain:
    # no external backend runs, and every answer still comes out of a real
    # store row or a real file inside the analysis's own workspace.
    locator = f"androguard:classes.dex#{CLASS_NAME}"
    provenance = [
        Provenance(tool="androguard", tool_version="4.1.4", apk_sha256=FAKE_SHA256, locator=locator)
    ]
    analyzer.store.save_symbols(
        pid,
        [ClassRef(name=CLASS_NAME, kind=ClassKind.CLASS, provenance=provenance)],
        [
            MethodRef(
                class_name=CLASS_NAME,
                name=METHOD_NAME,
                descriptor=DESCRIPTOR,
                provenance=provenance,
            )
        ],
        [],
        [],
        [],
    )
    java = workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")
    analyzer.store.save_evidence(
        pid,
        [
            Evidence(
                id="E-0001",
                kind=EvidenceKind.CROSS_REFERENCE,
                level=EvidenceLevel.VERIFIED,
                summary=f"{CLASS_NAME}.{METHOD_NAME} is called from 1 caller",
                detail={"callers": [f"{CLASS_NAME}.caller()V"], "call_site_count": 1},
                provenance=provenance,
            )
        ],
    )
    return pid


@pytest.fixture
def called_project_id(client: TestClient, project_id: str) -> str:
    """The project, plus the symbols and the call sites a cross-reference needs.

    Written through :meth:`Store.save_symbols`, the same write the analysis
    performs, so the ids in the database are the ids the tools look up — the
    canonical spelling, the canonicalisation rules included. Handing the store
    a spaced descriptor here would test the store, not the screen.
    """
    analyzer: Analyzer = client.app.state.analyzer
    provenance = [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256=FAKE_SHA256,
            locator=f"androguard:classes.dex#{FOCAL_METHOD}",
        )
    ]
    called_classes = {
        "com.example.demo.Crypto": ClassRef(
            name="com.example.demo.Crypto",
            kind=ClassKind.CLASS,
            access_flags=["public"],
            provenance=provenance,
        ),
        "com.example.demo.MainActivity": ClassRef(
            name="com.example.demo.MainActivity",
            kind=ClassKind.CLASS,
            superclass="android.app.Activity",
            access_flags=["public"],
            provenance=provenance,
        ),
        "com.example.demo.NetworkClient": ClassRef(
            name="com.example.demo.NetworkClient",
            kind=ClassKind.CLASS,
            access_flags=["public"],
            provenance=provenance,
        ),
    }
    called_methods = [
        MethodRef(
            class_name="com.example.demo.Crypto",
            name="sign",
            descriptor="([B)[B",
            access_flags=["public"],
            provenance=provenance,
        ),
        MethodRef(
            class_name="com.example.demo.MainActivity",
            name="onCreate",
            descriptor="(Landroid/os/Bundle;)V",
            access_flags=["public"],
            provenance=provenance,
        ),
        MethodRef(
            class_name="com.example.demo.MainActivity",
            name="onResume",
            descriptor="()V",
            access_flags=["public"],
            provenance=provenance,
        ),
        MethodRef(
            class_name="com.example.demo.NetworkClient",
            name="send",
            descriptor="(Ljava/lang/String;)Ljava/lang/String;",
            access_flags=["public"],
            provenance=provenance,
        ),
    ]
    # Who calls `Crypto.sign`. Two calls from one caller at two instructions,
    # which is the case the two counts are kept apart for: two call sites and
    # one edge between those two methods.
    inbound = [
        CallSite(
            caller=FIRST_CALLER,
            callee=FOCAL_METHOD,
            kind=InvocationKind.VIRTUAL,
            dex_name="classes.dex",
            instruction_offset=40,
            provenance=provenance,
        ),
        CallSite(
            caller=FIRST_CALLER,
            callee=FOCAL_METHOD,
            kind=InvocationKind.VIRTUAL,
            dex_name="classes.dex",
            instruction_offset=58,
            provenance=provenance,
        ),
        CallSite(
            caller=SECOND_CALLER,
            callee=FOCAL_METHOD,
            kind=InvocationKind.STATIC,
            dex_name="classes.dex",
            instruction_offset=8,
            provenance=provenance,
        ),
    ]
    # What `Crypto.sign` calls, including a call it makes twice: the same
    # target by the same opcode at two instructions, which is two call sites
    # and one edge. The offsets are what keep them two rows — the call-site
    # table keys on the instruction the call sits at.
    outbound = [
        CallSite(
            caller=FOCAL_METHOD,
            callee=FIRST_CALLEE,
            kind=InvocationKind.VIRTUAL,
            dex_name="classes.dex",
            instruction_offset=12,
            provenance=provenance,
        ),
        CallSite(
            caller=FOCAL_METHOD,
            callee=FIRST_CALLEE,
            kind=InvocationKind.VIRTUAL,
            dex_name="classes.dex",
            instruction_offset=26,
            provenance=provenance,
        ),
        MethodReference(
            caller=FOCAL_METHOD,
            callee=SECOND_CALLEE,
            kind=InvocationKind.STATIC,
            provenance=provenance,
        ),
        MethodReference(
            caller=FOCAL_METHOD,
            callee=THIRD_CALLEE,
            kind=InvocationKind.STATIC,
            provenance=provenance,
        ),
    ]
    analyzer.store.save_symbols(
        project_id,
        list(called_classes.values()),
        called_methods,
        [],
        [*inbound, *outbound],
        [],
    )
    return project_id


# -- the API over the MCP contract -------------------------------------------


def test_health_names_the_workspace_and_the_version(client: TestClient, tmp_path: Path) -> None:
    data = client.get("/api/health").json()
    assert data["version"]
    assert data["workspace"] == "workspace"


def test_health_does_not_leak_the_workspace_path(client: TestClient) -> None:
    """install.md promises the API redacts the server's own directories.

    ``/api/health`` answers with the workspace's directory *name*, so the
    absolute path — which names this machine's directory layout, and which
    the header used to print in full — never crosses the wire. The old
    response carried ``str(workspace)``; this test goes red against it.
    """
    data = client.get("/api/health").json()

    assert data["workspace"] == "workspace"
    # No separator of any kind: a name, not a path on any platform.
    assert "/" not in data["workspace"]
    assert "\\" not in data["workspace"]


def test_empty_workspace_lists_no_projects(client: TestClient) -> None:
    data = client.get("/api/projects").json()
    assert data == {"projects": [], "total": 0, "offset": 0, "limit": DEFAULT_LIMIT}


def test_project_list_limit_is_bounded(client: TestClient) -> None:
    assert client.get("/api/projects", params={"limit": 9999}).status_code == 422


def test_project_list_carries_the_mcp_contract_shape(client: TestClient, project_id: str) -> None:
    data = client.get("/api/projects").json()
    assert data["total"] == 1
    summary = data["projects"][0]
    assert summary["id"] == project_id
    assert summary["apk_name"] == "demo.apk"
    assert summary["status"] == "completed"
    assert summary["class_count"] == 1
    assert summary["method_count"] == 1
    assert summary["call_site_count"] == 0
    assert summary["call_edge_count"] == 0
    assert summary["evidence_count"] == 1
    # A backend that did not take part is named, not silently absent.
    assert summary["missing_backends"] == ["apktool"]
    assert summary["truncated"] is False


def test_project_status_carries_the_mcp_contract_shape(client: TestClient, project_id: str) -> None:
    data = client.get(f"/api/projects/{project_id}").json()
    assert data["project"]["id"] == project_id
    assert data["completeness"]["complete"] is False
    assert data["completeness"]["missing_backends"] == ["apktool"]
    assert data["completeness"]["errors"] == []
    # A workspace with no recorded runs answers honestly about that too.
    assert data["published_run"] is None
    assert data["runs"] == []


def test_a_project_with_recorded_errors_names_them(client: TestClient, project_id: str) -> None:
    analyzer: Analyzer = client.app.state.analyzer
    project = analyzer.store.get_project(project_id)
    assert project is not None
    project.errors = [
        ToolError(
            tool="apktool", code=ToolErrorCode.NOT_INSTALLED, message="apktool could not start"
        )
    ]
    analyzer.store.save_project(
        project, analyzer.settings.workspace / "projects" / project_id, manifest=None
    )

    data = client.get(f"/api/projects/{project_id}").json()
    assert data["completeness"]["errors"] == ["apktool: apktool could not start"]
    assert data["completeness"]["complete"] is False


def test_unknown_project_is_404_with_the_mcp_error_shape(client: TestClient) -> None:
    response = client.get("/api/projects/deadbeef00")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "unknown_project"
    assert "deadbeef00" in data["message"]


def test_project_list_offset_pages_the_workspaces_projects(
    client: TestClient, project_id: str
) -> None:
    assert client.get("/api/projects", params={"offset": 1}).json()["projects"] == []
    assert client.get("/api/projects", params={"offset": 0}).json()["total"] == 1


# -- the second screen: index -> source -> evidence -> the place cited -------


def test_symbol_search_is_the_mcp_answer(client: TestClient, project_id: str) -> None:
    """A phrase in the index comes back as `search_symbols` would answer."""
    response = client.get(f"/api/projects/{project_id}/symbols", params={"q": CLASS_NAME})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["offset"] == 0
    assert data["limit"] == DEFAULT_LIMIT
    assert [entry["kind"] for entry in data["symbols"]] == ["class", "method"]
    assert data["symbols"][0]["name"]["text"] == CLASS_NAME
    assert data["symbols"][0]["name"]["notice"] == DATA_NOTICE
    assert CLASS_NAME in data["symbols"][0]["detail"]["text"]


def test_search_limit_and_offset_are_bounded(client: TestClient, project_id: str) -> None:
    assert (
        client.get(
            f"/api/projects/{project_id}/symbols", params={"q": "sign", "limit": 9999}
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/projects/{project_id}/symbols", params={"q": "sign", "offset": -1}
        ).status_code
        == 422
    )
    data = client.get(
        f"/api/projects/{project_id}/symbols",
        params={"q": CLASS_NAME, "limit": 1, "offset": 1},
    ).json()
    assert [entry["kind"] for entry in data["symbols"]] == ["method"]


def test_class_source_is_the_mcp_answer(client: TestClient, project_id: str) -> None:
    data = client.get(
        f"/api/projects/{project_id}/source/class", params={"class_name": CLASS_NAME}
    ).json()
    assert data["found"] is True
    assert data["kind"] == "java"
    assert "public final class Crypto" in data["text"]["text"]
    assert data["text"]["notice"] == DATA_NOTICE
    assert data["provenance"] == ["jadx:sources/com/example/demo/Crypto.java"]


def test_method_source_is_addressed_by_its_descriptor(client: TestClient, project_id: str) -> None:
    params = {"class_name": CLASS_NAME, "method_name": METHOD_NAME, "descriptor": DESCRIPTOR}
    data = client.get(f"/api/projects/{project_id}/source/method", params=params).json()
    assert data["found"] is True
    assert data["kind"] == "java"
    assert "return first + second" in data["text"]["text"]
    assert data["provenance"] == [
        f"jadx:sources/com/example/demo/Crypto.java#{METHOD_NAME}{DESCRIPTOR}"
    ]
    assert data["candidates"] == []


def test_missing_source_says_why(client: TestClient, project_id: str) -> None:
    data = client.get(
        f"/api/projects/{project_id}/source/class", params={"class_name": "com.example.Absent"}
    ).json()
    assert data["found"] is False
    assert data["text"] is None
    assert "no source" in data["reason"]


def test_evidence_list_is_made_of_the_mcp_get_evidence_answers(
    client: TestClient, project_id: str
) -> None:
    listed = client.get(f"/api/projects/{project_id}/evidence").json()
    one = client.get(f"/api/projects/{project_id}/evidence/E-0001").json()
    assert listed == [one]
    assert one["id"] == "E-0001"
    assert one["kind"] == "cross_reference"
    assert one["level"] == "verified"
    assert one["detail"]["call_site_count"] == 1
    assert one["provenance"] == [f"androguard:classes.dex#{CLASS_NAME}"]


def test_an_unknown_evidence_id_is_the_contract_error(client: TestClient, project_id: str) -> None:
    response = client.get(f"/api/projects/{project_id}/evidence/E-9999")
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_project"


def test_every_second_screen_endpoint_answers_an_unknown_project_as_mcp_does(
    client: TestClient,
) -> None:
    """The MCP tools do not all use the same error for a missing project.

    `search_symbols`, `get_evidence` and `resolve_locator` raise
    `unknown_project`; the two source tools answer `found: false` with a
    reason, because "this analysis holds no source" and "there is no such
    project" are the same branch in them. The workbench does not add a
    status code its tools do not have.
    """
    raising = (
        ("symbols", {"q": "sign"}),
        ("evidence", {}),
        ("evidence/E-0001", {}),
        ("locators/resolve", {"locator": "androguard:classes.dex"}),
    )
    for path, params in raising:
        response = client.get(f"/api/projects/deadbeef00/{path}", params=params)
        assert response.status_code == 404, path
        assert response.json()["code"] == "unknown_project", path

    for path, params in (
        ("source/class", {"class_name": CLASS_NAME}),
        ("source/method", {"class_name": CLASS_NAME, "method_name": METHOD_NAME}),
    ):
        response = client.get(f"/api/projects/deadbeef00/{path}", params=params)
        assert response.status_code == 200, path
        assert response.json()["found"] is False, path
        assert response.json()["reason"], path


def test_a_locator_resolves_into_the_analysis(client: TestClient, project_id: str) -> None:
    record = client.get(f"/api/projects/{project_id}/evidence/E-0001").json()
    locator = record["provenance"][0]
    resolution = client.get(
        f"/api/projects/{project_id}/locators/resolve", params={"locator": locator}
    ).json()
    assert resolution["resolved"] is True
    assert resolution["provenance"] == [locator]
    assert resolution["text"] is None  # a DEX symbol, not a file to show


def test_a_source_locator_resolves_to_the_file_it_names(
    client: TestClient, project_id: str
) -> None:
    source = client.get(
        f"/api/projects/{project_id}/source/class", params={"class_name": CLASS_NAME}
    ).json()
    resolution = client.get(
        f"/api/projects/{project_id}/locators/resolve",
        params={"locator": source["provenance"][0]},
    ).json()
    assert resolution["resolved"] is True
    assert resolution["kind"] == "java"
    assert "public final class Crypto" in resolution["text"]["text"]
    assert resolution["provenance"] == source["provenance"]


def test_a_locator_outside_the_analysis_is_not_silently_resolved(
    client: TestClient, project_id: str
) -> None:
    resolution = client.get(
        f"/api/projects/{project_id}/locators/resolve",
        params={"locator": "jadx:sources/com/example/Absent.java"},
    ).json()
    assert resolution["resolved"] is False
    assert "Absent.java" in resolution["reason"]


# -- the third screen: the calls into and out of one method ------------------
#
# The load-bearing test of this screen is the equality against the tool: the
# workbench adds nothing to `CallerView` and `CalleeView`, and a screen that
# invented a count or renamed a field would be a second contract, which is the
# failure mode the workbench exists to avoid.


def test_callers_endpoint_answers_exactly_what_find_callers_answers(
    client: TestClient, called_project_id: str
) -> None:
    analyzer: Analyzer = client.app.state.analyzer
    expected = reference_tools.find_callers(analyzer, called_project_id, FOCAL_METHOD, limit=50)

    response = client.get(
        f"/api/projects/{called_project_id}/callers", params={"method_id": FOCAL_METHOD}
    )
    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")


def test_callees_endpoint_answers_exactly_what_find_callees_answers(
    client: TestClient, called_project_id: str
) -> None:
    analyzer: Analyzer = client.app.state.analyzer
    expected = reference_tools.find_callees(analyzer, called_project_id, FOCAL_METHOD, limit=50)

    response = client.get(
        f"/api/projects/{called_project_id}/callees", params={"method_id": FOCAL_METHOD}
    )
    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")


def test_callers_names_each_site_with_the_instruction_it_sits_at(
    client: TestClient, called_project_id: str
) -> None:
    data = client.get(
        f"/api/projects/{called_project_id}/callers", params={"method_id": FOCAL_METHOD}
    ).json()
    # Three places in the bytecode call this method, and they make two
    # relationships: the two from MainActivity.onCreate are two sites and one
    # edge, and the screen has to be able to say both numbers.
    assert data["call_site_count"] == 3
    assert data["call_edge_count"] == 2
    assert data["truncated"] is False
    offsets = {site["instruction_offset"] for site in data["call_sites"]}
    assert offsets == {8, 40, 58}
    assert {site["dex_name"] for site in data["call_sites"]} == {"classes.dex"}
    for site in data["call_sites"]:
        assert site["callee"] == FOCAL_METHOD
        # Every site carries the locator a reader can follow back to the bytes.
        assert site["provenance"]


def test_callees_keeps_the_sites_and_the_relationships_apart(
    client: TestClient, called_project_id: str
) -> None:
    data = client.get(
        f"/api/projects/{called_project_id}/callees", params={"method_id": FOCAL_METHOD}
    ).json()
    # Four sites, three callees, three edges: `digest` is called twice, and the
    # deduplicated list says one thing about it while the counts say another.
    assert data["call_site_count"] == 4
    assert data["call_edge_count"] == 3
    # The call sites come back ordered by callee, so the deduplicated list
    # follows that order: a reader who compares this screen against the query
    # the same tool answers sees the same sequence both ways.
    assert [callee["name"]["text"] for callee in data["callees"]] == [
        SECOND_CALLEE,
        FIRST_CALLEE,
        THIRD_CALLEE,
    ]
    kinds = {callee["detail"]["text"] for callee in data["callees"]}
    assert kinds == {"virtual", "static"}
    # A callee is text out of the APK, so it arrives under the untrusted-text
    # notice rather than as a bare string.
    assert all(callee["name"]["notice"] for callee in data["callees"])


def test_a_method_nobody_calls_answers_zero_counts_not_404(
    client: TestClient, called_project_id: str
) -> None:
    """A method with no caller is an answer, not an error.

    ``404`` would turn "the analysis read no call into this method" into "this
    method does not exist", and a reader who believed it would look for a
    method that is there. This is the distinction the MCP tool makes by
    returning zero counts, and the workbench has to inherit it.
    """
    response = client.get(
        f"/api/projects/{called_project_id}/callers",
        params={"method_id": "com.example.demo.Unused.thing()V"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "call_sites": [],
        "call_site_count": 0,
        "call_edge_count": 0,
        "truncated": False,
    }


def test_a_method_that_calls_nothing_says_so(client: TestClient, called_project_id: str) -> None:
    response = client.get(
        f"/api/projects/{called_project_id}/callees",
        params={"method_id": "com.example.demo.Unused.thing()V"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "callees": [],
        "call_site_count": 0,
        "call_edge_count": 0,
        "truncated": False,
    }


def test_a_followed_call_resolves_to_the_same_method_the_edge_named(
    client: TestClient, called_project_id: str
) -> None:
    """Following a caller gives the same answer as asking about it directly.

    The graph is navigable, so this has to hold: the caller a site names is the
    id the callees of that caller were read out of, or the walk would drift off
    the analysis with every click.
    """
    callers = client.get(
        f"/api/projects/{called_project_id}/callers", params={"method_id": FOCAL_METHOD}
    ).json()
    walked = callers["call_sites"][0]["caller"]

    outbound = client.get(
        f"/api/projects/{called_project_id}/callees", params={"method_id": walked}
    ).json()
    assert walked == FIRST_CALLER
    assert {callee["name"]["text"] for callee in outbound["callees"]} == {FOCAL_METHOD}
    assert outbound["call_site_count"] == 2


def test_callers_limit_bounds_the_page_and_says_the_rest_exists(
    client: TestClient, called_project_id: str
) -> None:
    data = client.get(
        f"/api/projects/{called_project_id}/callers",
        params={"method_id": FOCAL_METHOD, "limit": 2},
    ).json()
    assert len(data["call_sites"]) == 2
    # The counts describe the whole answer, not the page: a truncated page is
    # not a smaller total.
    assert data["call_site_count"] == 3
    assert data["truncated"] is True


def test_callers_limit_is_bounded_the_way_the_tools_limit_is(client: TestClient) -> None:
    assert (
        client.get(
            "/api/projects/x/callers", params={"method_id": "a.b()V", "limit": 9999}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/projects/x/callees", params={"method_id": "a.b()V", "limit": 0}
        ).status_code
        == 422
    )


def test_cross_reference_on_an_unknown_project_is_404(
    client: TestClient, called_project_id: str
) -> None:
    for path in ("callers", "callees"):
        response = client.get(
            f"/api/projects/deadbeef00/{path}", params={"method_id": FOCAL_METHOD}
        )
        assert response.status_code == 404, path
        assert response.json()["code"] == "unknown_project"


def test_method_id_is_taken_from_the_index_search_the_screen_offers(
    client: TestClient, called_project_id: str
) -> None:
    """The screen's entry point is the MCP search tool, unchanged.

    A method hit's name is the method's canonical id, and that is the string
    the two cross-reference endpoints take — so the id a reader clicks and the
    id the analysis indexed are one id.
    """
    analyzer: Analyzer = client.app.state.analyzer
    expected = symbol_tools.search_symbols(analyzer, called_project_id, "sign", limit=50, offset=0)

    response = client.get(f"/api/projects/{called_project_id}/symbols", params={"q": "sign"})
    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")

    hits = [symbol for symbol in response.json()["symbols"] if symbol["kind"] == "method"]
    assert [hit["name"]["text"] for hit in hits] == [FOCAL_METHOD]

    # ...and that id is exactly what the cross-reference answers about.
    callers = client.get(
        f"/api/projects/{called_project_id}/callers", params={"method_id": hits[0]["name"]["text"]}
    ).json()
    assert callers["call_site_count"] == 3


# ---------------------------------------------------------------------------
# The report export screen
# ---------------------------------------------------------------------------


def test_report_export_is_the_renderers_own_markdown(client: TestClient, project_id: str) -> None:
    """The workbench exports the analysis report the project already renders.

    The point of the endpoint is that the browser reads the same report the
    CLI writes to disk -- not a second report in a second format. So the
    response is compared against the renderer itself, called the same way
    the export path calls it: the snapshot read back out of the workspace.
    """

    response = client.get(f"/api/projects/{project_id}/report", params={"format": "markdown"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text == _expected_markdown(client, project_id)
    assert "# DexAtlas analysis report" in response.text
    # The one piece of evidence the fixture wrote is in the table.
    assert "E-0001" in response.text


def test_report_export_is_the_renderers_own_json(client: TestClient, project_id: str) -> None:
    """The JSON report is the same document the REST API's export returns.

    ``generated_at`` is the moment the renderer ran, so the two documents
    are compared without it -- everything else has to be identical.
    """

    response = client.get(f"/api/projects/{project_id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    served = response.json()
    expected = _expected_json(client, project_id)
    served.pop("generated_at")
    expected.pop("generated_at")
    assert served == expected
    assert served["schema_version"] == 3


def test_report_export_defaults_to_json(client: TestClient, project_id: str) -> None:
    """No format parameter: the JSON report, as on the REST API.

    ``generated_at`` differs between two renders, so it is dropped here too.
    """
    first = client.get(f"/api/projects/{project_id}/report").json()
    second = client.get(f"/api/projects/{project_id}/report", params={"format": "json"}).json()
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_report_export_of_an_unknown_project_is_the_contract_error(
    client: TestClient,
) -> None:
    """An unknown project is the MCP contract's ``unknown_project``, as a 404."""
    response = client.get("/api/projects/apk_missing/report")
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_project"


def test_report_export_rejects_an_unknown_format(client: TestClient, project_id: str) -> None:
    """A format the reports do not have is refused before anything renders."""
    response = client.get(f"/api/projects/{project_id}/report", params={"format": "pdf"})
    assert response.status_code == 422


def test_report_export_describes_the_published_run(client: TestClient, tmp_path: Path) -> None:
    """A re-analysis that failed leaves the published snapshot as the report.

    The report describes the last run that completed. The project's own row
    says how the latest attempt ended, which is a different thing -- and the
    exported report has to keep saying what the snapshot said, with the
    later attempt named, not silently promoted to the report's status.
    """
    from dexatlas.core.runs import AnalysisRun, RunStatus
    from dexatlas.core.storage import Store

    analyzer: Analyzer = client.app.state.analyzer
    pid = Project.new_id(FAKE_SHA256)
    workspace = analyzer.settings.workspace / "projects" / pid
    project = Project(
        id=pid,
        apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
        status=ProjectState.FAILED,
        tool_versions={"androguard": "4.1.4"},
        duration_seconds=1.5,
    )
    # The project row exists first; the run references it.
    analyzer.store.save_project(project, workspace, manifest=None)
    published = AnalysisRun.start(pid, FAKE_SHA256, workspace=workspace)
    published.status = RunStatus.COMPLETED
    analyzer.store.create_run(published)
    # A staged database of the project's own rows, the way the pipeline
    # publishes: the snapshot the report describes, not the project's row.
    staged = workspace / "staging.db"
    staged_store = Store.open(staged)
    staged_store.save_project(project, workspace, manifest=None)
    staged_store.save_evidence(
        pid,
        [
            Evidence(
                id="E-0001",
                kind=EvidenceKind.OBSERVATION,
                level=EvidenceLevel.VERIFIED,
                summary="the published snapshot's one fact",
            )
        ],
    )
    analyzer.store.publish_run(project, published, staged, None)

    markdown = client.get(f"/api/projects/{pid}/report", params={"format": "markdown"})
    assert markdown.status_code == 200
    assert f"**Run:** `{published.id}`" in markdown.text
    # The snapshot's status, not the latest attempt's.
    assert "**Status:** completed" in markdown.text
    # ...and the later attempt is named where the report is read.
    assert "ended as `failed`" in markdown.text

    json_report = client.get(f"/api/projects/{pid}/report").json()
    assert json_report["run"]["id"] == published.id
    assert json_report["latest_attempt_status"] == "failed"


def _expected_markdown(client: TestClient, project_id: str) -> str:
    """The markdown the renderer itself writes for the stored snapshot."""
    from dexatlas.reports.markdown import render_markdown

    return render_markdown(_stored_result(client, project_id))


def _expected_json(client: TestClient, project_id: str) -> dict:
    from dexatlas.reports.json_report import build_json_report

    return build_json_report(_stored_result(client, project_id))


def _stored_result(client: TestClient, project_id: str):
    """The analysis result as the workspace holds it, for the renderer.

    The same reconstruction the export endpoint performs; spelled out here
    so the tests compare the endpoint's answer against the renderer's own
    output for the same snapshot, not against a hand-written expectation.
    """
    from dexatlas.core.models import ProjectStatus as ProjectState
    from dexatlas.core.pipeline import AnalysisResult

    analyzer: Analyzer = client.app.state.analyzer
    with analyzer.store.reading() as view:
        project = view.get_project(project_id)
        run = view.get_published_run(project_id)
        manifest = view.get_manifest(project_id)
        evidence = view.list_evidence(project_id)
        workspace = view.get_workspace(project_id)

    assert project is not None
    latest_attempt_status = None
    if run is not None:
        known = {status.value for status in ProjectState}
        published_status = (
            ProjectState(run.status.value) if run.status.value in known else ProjectState.FAILED
        )
        latest_attempt_status = project.status if project.status is not published_status else None
        project = project.model_copy(
            update={"status": published_status, "errors": list(run.errors)}
        )
    return AnalysisResult(
        project=project,
        manifest=manifest,
        evidence=evidence,
        workspace=workspace,
        duration_seconds=project.duration_seconds or 0.0,
        run=run,
        latest_attempt_status=latest_attempt_status,
    )


# -- the front end -----------------------------------------------------------


def test_root_without_a_built_front_end_says_so(tmp_path: Path) -> None:
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("dexatlas.workbench.app.WEB_DIST", tmp_path / "dist-absent")
        with TestClient(create_app(analyzer)) as test_client:
            response = test_client.get("/")
    assert response.status_code == 503
    assert response.json()["code"] == "front_end_not_built"


def test_root_serves_the_built_front_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>workbench</body></html>", encoding="utf-8")
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("dexatlas.workbench.app.WEB_DIST", dist)
        with TestClient(create_app(analyzer)) as test_client:
            response = test_client.get("/")
    assert response.status_code == 200
    assert "workbench" in response.text


# ---------------------------------------------------------------------------
# The upload screen
# ---------------------------------------------------------------------------


class _StubAnalyzer:
    """An Analyzer-shaped stand-in: the upload policy is what is under test.

    The endpoint calls the shared policy with a real Analyzer, and only the
    background analysis is replaced -- analysis is the CPU-bound part the
    tests must not run. Everything the policy touches (the workspace, the
    store, the settings) is the real thing, so a stored upload is a real
    file in the workspace this client was built around.
    """

    def __init__(self, analyzer: Analyzer) -> None:
        self.settings = analyzer.settings
        self.store = analyzer.store
        self._analyze_calls: list[Path] = []

    def analyze(self, apk_path: Path, **kwargs: object):
        self._analyze_calls.append(apk_path)
        raise AssertionError("the stub analysis should be replaced per test")


def _upload_client(tmp_path: Path) -> Iterator[tuple[TestClient, _StubAnalyzer]]:
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    real = Analyzer(settings)
    stub = _StubAnalyzer(real)
    with TestClient(create_app(stub)) as test_client:
        yield test_client, stub


def test_upload_stores_and_accepts_an_apk(tmp_path: Path) -> None:
    """A valid APK is stored under the shared policy and queued for analysis."""
    client, _stub = next(_upload_client(tmp_path))
    apk = build_apk(tmp_path / "demo.apk")

    response = client.post(
        "/api/analyze",
        files={"file": ("demo.apk", apk.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["already_analysed"] is False
    assert body["project_id"].startswith("apk_")
    # The stored upload is a real file in the workspace, in the shared
    # hash-addressed layout both transports use.
    stored = list((tmp_path / "workspace" / "uploads").rglob("demo.apk"))
    assert len(stored) == 1
    assert body["apk_sha256"] in str(stored[0])


def test_upload_rejects_a_non_apk_with_the_shared_words(tmp_path: Path) -> None:
    """A file that is not an APK is refused before any analysis is queued."""
    client, _stub = next(_upload_client(tmp_path))

    response = client.post(
        "/api/analyze", files={"file": ("notes.txt", b"not a zip", "text/plain")}
    )

    assert response.status_code == 422


def test_upload_over_the_limit_is_refused_like_the_api(tmp_path: Path) -> None:
    """The workbench's limit is the shared limit, enforced in front of the route."""
    client, _stub = next(_upload_client(tmp_path))
    limit = 1024
    original = ingest.MAX_APK_BYTES
    ingest.MAX_APK_BYTES = limit
    try:
        response = client.post(
            "/api/analyze",
            files={"file": ("big.apk", b"x" * (limit * 4), "application/octet-stream")},
        )
    finally:
        ingest.MAX_APK_BYTES = original

    assert response.status_code == 413
    assert str(limit) in response.json()["detail"]
    uploads = tmp_path / "workspace" / "uploads"
    assert not uploads.exists() or list(uploads.iterdir()) == []


def test_upload_of_an_analysed_apk_answers_the_existing_project(tmp_path: Path) -> None:
    """The same bytes twice: the second upload opens the first analysis."""
    iterator = _upload_client(tmp_path)
    client, stub = next(iterator)
    apk = build_apk(tmp_path / "demo.apk")
    files = {"file": ("demo.apk", apk.read_bytes(), "application/vnd.android.package-archive")}
    first = client.post("/api/analyze", files=files).json()

    # Publish the analysis the way the real background task would, then send
    # the same bytes again.
    project_id = first["project_id"]
    analyzer = Analyzer(stub.settings)
    analyzer.store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=first["apk_sha256"], size_bytes=apk.stat().st_size, path=apk),
            status=ProjectState.COMPLETED,
            tool_versions={},
        ),
        stub.settings.workspace / "projects" / project_id,
        manifest=None,
    )
    second = client.post("/api/analyze", files=files)

    assert second.status_code == 202
    body = second.json()
    assert body["already_analysed"] is True
    assert body["project_id"] == project_id
    assert body["status"] == "completed"


# -- the benchmark screen ----------------------------------------------------
#
# The screen's whole claim is that it serves the M3 comparison's committed
# traces recomputed, not restated. So the tests compare the served metrics
# against `_run_from_document` + `compare` — the derivation the reports were
# written from — and the missing-file case against a checkout that carries
# no measurement.


def test_benchmark_metrics_are_the_harness_own_recomputation(client: TestClient) -> None:
    """The served figures are the harness's recomputation of the committed traces.

    The endpoint does not cache and does not restate: the numbers in the
    response are compared metric-for-metric against the same derivation the
    `docs/benchmarks/` reports were generated by. If the two ever disagree,
    the screen has started telling its own story, and that is the failure
    this test exists to catch.
    """
    import json

    from benchmarks.comparison.run import COMMITTED_TRACES, _run_from_document

    from dexatlas.workbench.benchmarks import REAL_TRACES, SCRIPTED_TRACES

    response = client.get("/api/benchmarks/m3")
    assert response.status_code == 200
    served = response.json()

    kinds = {measurement["kind"]: measurement for measurement in served["measurements"]}
    assert set(kinds) == {"scripted", "real-model"}
    assert kinds["scripted"]["traces_file"] == SCRIPTED_TRACES.name
    assert kinds["real-model"]["traces_file"] == REAL_TRACES.name

    for kind, path in (("scripted", SCRIPTED_TRACES), ("real-model", REAL_TRACES)):
        assert path.is_file(), f"{path} is a committed measurement; the screen may not drop it"
        document = json.loads(path.read_text(encoding="utf-8"))
        run = _run_from_document(document)
        measurement = kinds[kind]
        assert measurement["task_count"] == run.task_count == 92
        assert measurement["budget"] == run.budget
        for config in measurement["configurations"]:
            expected = run.metrics[config["configuration"]]
            assert config["metrics"] == expected
            assert config["provider"] == run.providers[config["configuration"]]
            assert config["model"] == run.models[config["configuration"]]
        # The failure-cause table is the report's own grouping: every failed
        # task appears exactly once, under one cause.
        failed = sum(1 for trace in document["traces"] if not trace["passed"])
        assert sum(cause["tasks"] for cause in measurement["failure_causes"]) == failed

    # The reports under docs/benchmarks/ are generated from the same traces;
    # the screen has to agree with the figures they state.
    assert COMMITTED_TRACES.is_file()


def test_benchmark_screen_carries_the_disclosures(client: TestClient) -> None:
    """The numbers travel with the claims that bound them.

    A rate without its disclosure invites the reading the M3 rules forbid —
    that a scripted number is a model baseline, or that a difference is an
    improvement. The screen answers with both measurements and the
    disclosures in one document, so the browser cannot show one without the
    other.
    """
    response = client.get("/api/benchmarks/m3")
    assert response.status_code == 200
    disclosures = "\n".join(response.json()["disclosures"])
    assert "not a model baseline" in disclosures
    assert "not reproducible" in disclosures
    assert "never claims an improvement" in disclosures


def test_benchmark_screen_with_no_committed_traces(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checkout without the trace files answers with nothing, not with an error.

    The traces are measurement evidence this screen reads, not data it
    needs to function: the rest of the workbench works without them, and so
    does this screen — it reports which measurements it could not find
    instead of pretending one ran.
    """
    from dexatlas.workbench import benchmarks as benchmark_view

    monkeypatch.setattr(benchmark_view, "SCRIPTED_TRACES", Path("no/such/traces.json"))
    monkeypatch.setattr(benchmark_view, "REAL_TRACES", Path("no/such/traces.json"))
    response = client.get("/api/benchmarks/m3")
    assert response.status_code == 200
    body = response.json()
    assert body["measurements"] == []
    assert len(body["disclosures"]) == 3


def test_benchmark_metrics_recomputed_live_not_cached(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two requests read the traces twice: the screen adds no cache.

    The point of the screen is that a number it serves is the number a
    regeneration would derive. That only holds if every request actually
    re-derives — a cache would let the served figures outlive the evidence
    they were computed from.
    """

    calls = {"count": 0}
    original_read_text = Path.read_text

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name.startswith("comparison-"):
            calls["count"] += 1
        return original_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    client.get("/api/benchmarks/m3")
    assert calls["count"] == 2
    client.get("/api/benchmarks/m3")
    assert calls["count"] == 4
