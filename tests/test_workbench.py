"""The workbench transport.

The workbench sits on the MCP tools' plain-Python functions, so the point of
these tests is that it exposes them unchanged: the list, the status, the
symbol search, the source, the evidence and the locator resolutions the
browser gets are the same shapes the MCP server answers with, an unknown
project is the contract's ``unknown_project`` error as a 404, and the front
end is served when it is built and says how to build it when it is not.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    MethodRef,
    Project,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.models import ProjectStatus as ProjectState
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.schemas import DATA_NOTICE, DEFAULT_LIMIT
from dexatlas.workbench.app import create_app

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
