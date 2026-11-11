"""The workbench transport.

The workbench sits on the MCP tools' plain-Python functions, so the point of
these tests is that it exposes them unchanged: the list and the status the
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
    Project,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.models import ProjectStatus as ProjectState
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.schemas import DEFAULT_LIMIT
from dexatlas.workbench.app import create_app

FAKE_SHA256 = "ab" * 32


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
