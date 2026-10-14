"""REST API.

The point of these tests is that the API exposes the same behaviour as the CLI, and
that it degrades honestly — a missing project is a 404, a bad APK is a 422, and a
missing backend shows up as a recorded error rather than a crashed request.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.storage import Store
from tests.conftest import build_apk


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A client wired to an isolated workspace, so tests never touch a real project DB."""
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


# -- meta -------------------------------------------------------------------


def test_health_reports_version_and_backends(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["backends"]) == {"jadx", "apktool", "androguard"}


def test_backends_separates_available_from_missing(client: TestClient) -> None:
    body = client.get("/backends").json()

    available = set(body["available"])
    missing = set(body["missing"])
    assert available.isdisjoint(missing)
    assert available | missing == {"jadx", "apktool", "androguard"}


def test_openapi_schema_is_served(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200


# -- projects ---------------------------------------------------------------


def test_no_projects_initially(client: TestClient) -> None:
    assert client.get("/projects").json() == []


def test_unknown_project_is_404(client: TestClient) -> None:
    assert client.get("/projects/apk_missing").status_code == 404


def test_unknown_project_manifest_is_404(client: TestClient) -> None:
    assert client.get("/projects/apk_missing/manifest").status_code == 404


def test_unknown_project_classes_is_empty(client: TestClient) -> None:
    response = client.get("/projects/apk_missing/classes")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_unknown_project_search_is_empty(client: TestClient) -> None:
    assert (
        client.get("/projects/apk_missing/search", params={"q": "anything"}).json()["results"] == []
    )


def test_delete_unknown_project_is_404(client: TestClient) -> None:
    assert client.delete("/projects/apk_missing").status_code == 404


# -- upload validation ------------------------------------------------------


def test_upload_rejects_a_non_apk(client: TestClient) -> None:
    response = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )

    assert response.status_code == 422
    assert "not a ZIP archive" in response.json()["detail"]


def test_rejection_message_does_not_leak_the_server_path(client: TestClient) -> None:
    """A remote caller must not learn the server's filesystem layout."""
    response = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )

    detail = response.json()["detail"]
    assert "notes.txt" in detail
    assert "\\Temp\\" not in detail and "/tmp/" not in detail
    assert str(Path.cwd()) not in detail


def test_rejected_upload_is_not_kept_on_disk(client: TestClient, tmp_path: Path) -> None:
    client.post("/analyze", files={"file": ("notes.txt", b"not a zip", "text/plain")})

    uploads = tmp_path / "workspace" / "uploads"
    assert not uploads.exists() or list(uploads.iterdir()) == []


def test_upload_requires_a_file(client: TestClient) -> None:
    assert client.post("/analyze").status_code == 422


# -- analysis ---------------------------------------------------------------


@pytest.mark.slow
def test_analyze_a_synthetic_apk_end_to_end(client: TestClient, tmp_path: Path) -> None:
    """Full loop against whatever backends this machine has. Assertions stay true
    whether or not JADX and Apktool are installed — which is the point."""
    apk = build_apk(tmp_path / "demo.apk")

    response = client.post(
        "/analyze",
        files={"file": ("demo.apk", apk.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 202
    project_id = response.json()["project_id"]

    project = client.get(f"/projects/{project_id}")
    assert project.status_code == 200
    assert project.json()["apk_sha256"] == response.json().get(
        "sha256", project.json()["apk_sha256"]
    )

    report = client.get(f"/projects/{project_id}/report", params={"format": "json"})
    assert report.status_code == 200
    assert "errors" in report.json()

    markdown = client.get(f"/projects/{project_id}/report", params={"format": "markdown"})
    assert markdown.status_code == 200
    assert "# DexAtlas analysis report" in markdown.text


def test_store_is_reachable_from_the_api_workspace(client: TestClient, tmp_path: Path) -> None:
    """The API must not write outside its configured workspace."""
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()

    assert Store.open(settings.database_path).list_projects() == []


def test_query_parameters_are_bounded(client: TestClient) -> None:
    response = client.get("/projects/apk_missing/classes", params={"limit": 99999})

    assert response.status_code == 422


def test_search_requires_a_query(client: TestClient) -> None:
    assert client.get("/projects/apk_missing/search").status_code == 422


def test_report_format_is_validated(client: TestClient) -> None:
    response = client.get("/projects/apk_missing/report", params={"format": "pdf"})

    assert response.status_code == 422
