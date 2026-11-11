"""The workbench transport.

The workbench sits on the MCP tools' plain-Python functions, so the point of
these tests is that it exposes them unchanged: the list, the status and the
cross-reference the browser gets are the same shapes the MCP server answers
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
from dexatlas.core.calls import CallSite
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
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
from dexatlas.mcp.schemas import DEFAULT_LIMIT
from dexatlas.mcp.tools import references as reference_tools
from dexatlas.mcp.tools import symbols as symbol_tools
from dexatlas.workbench.app import create_app

FAKE_SHA256 = "ab" * 32

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
    analyzer.store.save_project(
        Project(
            id=pid,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectState.COMPLETED,
            tool_versions={"androguard": "4.1.4", "jadx": None, "apktool": None},
            class_count=3,
            method_count=12,
            reference_count=30,
            call_edge_count=21,
            evidence_count=4,
        ),
        analyzer.settings.workspace / "projects" / pid,
        manifest=None,
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
    assert Path(data["workspace"]) == tmp_path / "workspace"


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
    assert summary["class_count"] == 3
    assert summary["method_count"] == 12
    assert summary["call_site_count"] == 30
    assert summary["call_edge_count"] == 21
    assert summary["evidence_count"] == 4
    # A backend that did not take part is named, not silently absent.
    assert summary["missing_backends"] == ["apktool", "jadx"]
    assert summary["truncated"] is False


def test_project_status_carries_the_mcp_contract_shape(client: TestClient, project_id: str) -> None:
    data = client.get(f"/api/projects/{project_id}").json()
    assert data["project"]["id"] == project_id
    assert data["completeness"]["complete"] is False
    assert data["completeness"]["missing_backends"] == ["apktool", "jadx"]
    assert data["completeness"]["errors"] == []
    # A workspace with no recorded runs answers honestly about that too.
    assert data["published_run"] is None
    assert data["runs"] == []


def test_a_project_with_recorded_errors_names_them(client: TestClient, project_id: str) -> None:
    analyzer: Analyzer = client.app.state.analyzer
    project = analyzer.store.get_project(project_id)
    assert project is not None
    project.errors = [
        ToolError(tool="jadx", code=ToolErrorCode.NOT_INSTALLED, message="jadx could not start")
    ]
    analyzer.store.save_project(
        project, analyzer.settings.workspace / "projects" / project_id, manifest=None
    )

    data = client.get(f"/api/projects/{project_id}").json()
    assert data["completeness"]["errors"] == ["jadx: jadx could not start"]
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
