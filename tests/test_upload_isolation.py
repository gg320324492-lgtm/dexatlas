"""Two uploads that carry the same name must not be able to write over
one another.

The name of the uploaded file was the client's to choose, so two different
APKs uploaded under the same name landed on the same path -- and the
analysis of the first one reads that path in the background. It therefore
read the *second* APK's bytes, and the project it produced said it held
the first APK's classes.

That is the worst kind of wrong: the project's hash was the first APK's,
its identifier was the first APK's, and every provenance record named the
first APK's hash -- and the classes in its symbol table belonged to the
second one. Nothing a reader could check contradicted the record; the
record was simply about a different file than the one it described.

The file is now stored under its own hash, so two uploads share a path
only when they are the same bytes.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import time
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.background import BackgroundTasks
from starlette.datastructures import UploadFile

from dexatlas.api import app as fastapi_app
from dexatlas.config.settings import Settings
from dexatlas.core.pipeline import Analyzer

api_module = sys.modules["dexatlas.api.app"]

REPO_ROOT = Path(__file__).parent.parent
DEMO = REPO_ROOT / "examples" / "demo-app" / "demo.apk"
STRINGS = REPO_ROOT / "examples" / "strings-app" / "strings.apk"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace of its own, with the API pointed at it."""
    path = tmp_path / "workspace"
    path.mkdir()
    settings = Settings(workspace=path)
    fastapi_app.dependency_overrides[api_module.get_settings] = lambda: settings
    yield path
    fastapi_app.dependency_overrides.clear()


def _client() -> TestClient:
    return TestClient(fastapi_app)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _projects(workspace: Path) -> dict[str, list[str]]:
    """Each project id, and the class names its symbol table holds."""
    database = next(workspace.rglob("*.db"))
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    projects: dict[str, list[str]] = {}
    for row in connection.execute("SELECT id FROM projects"):
        projects[row["id"]] = [
            other["name"]
            for other in connection.execute(
                "SELECT name FROM classes WHERE project_id = ?", (row["id"],)
            )
        ]
    connection.close()
    return projects


def test_two_uploads_of_the_same_name_get_different_paths(workspace: Path) -> None:
    """The path of an upload is not the client's to choose."""
    client = _client()

    first = client.post(
        "/analyze", files={"file": ("app.apk", DEMO.read_bytes(), "application/octet-stream")}
    )
    second = client.post(
        "/analyze",
        files={"file": ("app.apk", STRINGS.read_bytes(), "application/octet-stream")},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["project_id"] != second.json()["project_id"]

    stored = sorted((workspace / "uploads").rglob("*.apk"))
    assert len(stored) == 2, "the two uploads share a path"


def test_the_file_an_analysis_reads_is_the_file_it_was_about(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bytes at the path the analysis reads are the ones it was given.

    This is the defect stated as an invariant, and it is checked without
    racing anything: the analysis is told the hash of the file it was
    handed, and the hash of the file at that path is read at the moment
    the analysis starts. When the two uploads shared a path, the second
    one replaced the bytes between the first one's inspection and its
    analysis, and the two hashes stopped agreeing.

    Reading the path at the moment the analysis starts is what makes it
    deterministic: the question is not "did the other upload arrive in
    time" but "are the bytes at that path the ones this project names".
    """
    client = _client()
    seen: list[tuple[str, str]] = []

    original = Analyzer.analyze

    def recording(self: Analyzer, apk_path: Path, *, metadata: object = None, **kwargs: object):
        # The hash of the file at the path, read now, and the hash the
        # analysis was told about.
        on_disk = _sha256(apk_path)
        assert metadata is not None
        seen.append((on_disk, getattr(metadata, "sha256", "")))
        return original(self, apk_path, metadata=metadata, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Analyzer, "analyze", recording)

    client.post(
        "/analyze", files={"file": ("app.apk", DEMO.read_bytes(), "application/octet-stream")}
    )
    client.post(
        "/analyze",
        files={"file": ("app.apk", STRINGS.read_bytes(), "application/octet-stream")},
    )

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and len(seen) < 2:
        time.sleep(0.1)

    assert len(seen) == 2, f"the analyses did not both start: {seen}"
    for on_disk, claimed in seen:
        assert on_disk == claimed, (
            "the file the analysis read is not the file the project names: "
            f"the path holds {on_disk[:12]}, the project says {claimed[:12]}"
        )


def test_an_analysis_cannot_read_the_bytes_of_another_upload(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect, in an order that does not depend on timing.

    The test client runs a background task before it returns the response,
    so two uploads through it never overlap -- which is why the defect
    survived every test written against the endpoint. The order is arranged
    here instead: the first upload's analysis is held until the second
    upload has arrived.

    That is the order a real deployment produces. The analysis is in the
    background, the second upload is not waiting for it, and the file the
    first analysis reads is the path the second upload wrote.
    """
    settings = Settings(workspace=workspace)
    analyzer = Analyzer(settings)

    # The first upload. Its background task is collected, not run.
    first = BackgroundTasks()
    api_module.analyze(
        first,
        analyzer,
        settings,
        UploadFile(file=BytesIO(DEMO.read_bytes()), filename="app.apk"),
    )
    assert len(first.tasks) == 1

    # The second upload, under the same name, before the first analysis runs.
    second = BackgroundTasks()
    api_module.analyze(
        second,
        analyzer,
        settings,
        UploadFile(file=BytesIO(STRINGS.read_bytes()), filename="app.apk"),
    )
    assert len(second.tasks) == 1

    # Now the first analysis runs -- and the second upload has been here.
    for task in first.tasks:
        task.func(*task.args, **task.kwargs)

    projects = _projects(workspace)
    demo_project = next(
        (
            pid
            for pid, classes in projects.items()
            if any("com.example.demo." in c for c in classes)
        ),
        None,
    )
    assert demo_project is not None, f"the demo APK's classes are in no project: {projects}"

    classes = projects[demo_project]
    assert not any("com.example.strings." in name for name in classes), (
        f"the project that names the demo APK holds the other APK's classes: {classes}"
    )


def test_the_name_a_reader_sees_is_the_name_the_client_gave(workspace: Path) -> None:
    """The stored file is named by its hash; the report names what it was called.

    The name on disk is for the machine, and the name in the report is for
    the reader. A reader who is handed a hash where a file name belongs
    learns nothing, so the client's name is kept as the name of the file
    inside the hash-named directory.
    """
    client = _client()

    response = client.post(
        "/analyze", files={"file": ("demo.apk", DEMO.read_bytes(), "application/octet-stream")}
    )
    assert response.status_code == 202
    project_id = response.json()["project_id"]

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        projects = _projects(workspace)
        if projects.get(project_id):
            break
        time.sleep(0.2)

    stored = sorted((workspace / "uploads").rglob("demo.apk"))
    assert stored, "the upload was not stored under the name the client gave"

    shown = client.get(f"/projects/{project_id}").json()
    assert shown["apk_path"] == "demo.apk"
