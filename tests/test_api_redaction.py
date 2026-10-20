"""What the API publishes about the server it runs on.

DexAtlas promises — in `docs/architecture/README.md` — that the API redacts
server paths from error messages, and that extracted artefacts stay under the
project workspace. The first promise was kept in one place and broken in
everywhere else: a project's `apk_path` was the server's own absolute path,
and so was the path in the JSON report.

These tests hold that promise down.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.models import ApkMetadata, Project, ToolError, ToolErrorCode
from dexatlas.core.storage import Store
from dexatlas.tools.apktool.adapter import ApktoolBackend


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def client(workspace: Path) -> Iterator[TestClient]:
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    get_settings.cache_clear()

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _store(workspace: Path) -> Store:
    return Store.open(workspace / "dexatlas.db")


def _project_with_an_apk(workspace: Path, errors: list[ToolError] | None = None) -> str:
    """A project whose APK lives at an absolute path inside the workspace."""
    apk = workspace / "uploads" / "demo.apk"
    apk.parent.mkdir(parents=True, exist_ok=True)
    apk.write_bytes(b"not really an apk")

    project = Project.create(ApkMetadata(sha256="e" * 64, size_bytes=16, path=apk.resolve()))
    project.errors = errors or []
    _store(workspace).save_project(project, workspace / "projects" / project.id, manifest=None)
    return project.id


def test_the_project_response_names_the_file_and_not_the_path(
    client: TestClient, workspace: Path
) -> None:
    """`apk_path` is a public field, so it is a promise about every caller.

    The path it used to carry was the server's own: a username, a temporary
    directory, the shape of the workspace. None of that describes the
    analysis, and all of it describes the machine.
    """
    project_id = _project_with_an_apk(workspace)

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    apk_path = response.json()["apk_path"]
    assert apk_path == "demo.apk"
    assert "/" not in apk_path and "\\" not in apk_path
    assert str(workspace) not in apk_path


def test_the_project_listing_names_the_file_and_not_the_path(
    client: TestClient, workspace: Path
) -> None:
    project_id = _project_with_an_apk(workspace)

    body = client.get("/projects").json()

    assert [project["id"] for project in body] == [project_id]
    assert body[0]["apk_path"] == "demo.apk"


def test_the_json_report_names_the_file_and_not_the_path(
    client: TestClient, workspace: Path
) -> None:
    """A report is written to a file, diffed and pasted into issues.

    The server's filesystem layout is not part of the analysis, and it does
    not belong in something that is shared.
    """
    project_id = _project_with_an_apk(workspace)

    response = client.get(f"/projects/{project_id}/report", params={"format": "json"})

    assert response.status_code == 200
    path = response.json()["project"]["apk"]["path"]
    assert path == "demo.apk"
    assert str(workspace) not in response.text


def test_an_error_detail_does_not_name_the_workspace(client: TestClient, workspace: Path) -> None:
    """A backend's error can quote the path it was handed, and that path is
    the server's. The workspace root is the part that names the machine; what
    is left of the path is a place inside the analysis, and that is worth
    keeping."""
    detail = f"could not read {workspace / 'projects' / 'apk_1' / 'jadx'}"
    project_id = _project_with_an_apk(
        workspace,
        errors=[
            ToolError(
                tool="jadx",
                code=ToolErrorCode.EXIT_NONZERO,
                message="jadx exited with code 1",
                detail=detail,
            )
        ],
    )

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    error = response.json()["errors"][0]
    assert str(workspace) not in error["detail"]
    assert "<workspace>" in error["detail"]
    # The place inside the analysis is still there.
    assert "projects" in error["detail"]


def test_a_broken_manifest_names_the_file_and_not_the_path(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """The manifest error carried the absolute path of the decoded file.

    The resource reader in the same module already named the file relative
    to the output tree; the manifest reader did not, and the difference was
    the difference between a report and a disclosure.
    """
    output = tmp_path / "apktool"
    output.mkdir()
    (output / "AndroidManifest.xml").write_text("<manifest><unclosed>", encoding="utf-8")

    manifest, error = apktool.read_manifest(output)

    assert manifest is None
    assert error is not None
    assert error.code is ToolErrorCode.PARSE_ERROR
    assert error.detail == "AndroidManifest.xml"
    assert str(output) not in (error.detail or "")
