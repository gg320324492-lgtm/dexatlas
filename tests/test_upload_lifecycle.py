"""What happens to an upload, and to an analysis that is still running.

The upload is already safe: it is staged under a random name and then moved
to ``uploads/<sha256>/<client-filename>``, so two uploads cannot overwrite
one another. What was missing is everything that happens to that file
afterwards -- there was no retention policy, no cleanup, and no way to stop
an analysis that was still running.

These tests hold in place:

- An upload is kept for a stated window and removed after it.
- The upload of an analysis that is running is never removed underneath it.
- An analysis that is cancelled publishes nothing, and the snapshot that
  was published before it is left alone.
- The project's runs are readable, and the one that is published is marked.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api import app as fastapi_app
from dexatlas.config.settings import Settings
from dexatlas.core.models import ApkMetadata, ClassKind, ClassRef, Project, ProjectStatus
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import AnalysisCancelled, AnalysisRun, CancellationToken, RunStatus
from dexatlas.core.storage import Store
from dexatlas.tools.androguard.adapter import AndroguardBackend

api_module = sys.modules["dexatlas.api.app"]

#: A hash of nothing in particular, used to name a directory the way an
#: upload's own hash would.
FAKE_HASH = "a" * 64


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


def _store_upload(workspace: Path, name: str = "app.apk") -> Path:
    """Put a file where an upload is stored."""
    directory = workspace / "uploads" / FAKE_HASH
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(b"not really an apk")
    return path


def _age(path: Path, seconds: float) -> None:
    """Make a file look as old as it needs to look."""
    moment = time.time() - seconds
    os.utime(path, (moment, moment))


def _patch_dex_reader(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make the DEX reader report these classes, and nothing else.

    The fixture APK carries a stub DEX header that no reader can parse, so
    without this the analysis finds nothing and publishes nothing -- which
    is a perfectly good run, and not the one these tests are about.
    """

    def extract(self: AndroguardBackend, apk: Path, apk_sha256: str, **kwargs: object):
        return (
            [ClassRef(name=name, kind=ClassKind.CLASS) for name in names],
            [],
            [],
            [],
            [],
            None,
        )

    monkeypatch.setattr(AndroguardBackend, "extract", extract)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def test_an_upload_within_the_window_is_kept(workspace: Path, monkeypatch) -> None:
    """The policy keeps an upload for a stated window.

    The window is a policy of the deployment, not of the analysis: the
    bytes are what the analysis read, and an operator is entitled to look
    at them for a while after the fact.
    """
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "3600")
    stored = _store_upload(workspace)
    _age(stored, 60)

    response = _client().post("/uploads/cleanup")

    assert response.status_code == 200
    assert response.json()["removed"] == 0
    assert stored.exists()


def test_an_upload_past_the_window_is_removed(workspace: Path, monkeypatch) -> None:
    """The sweep removes what the policy has expired.

    Without it the workspace grows for ever: every APK that was ever
    uploaded stays on the disk, and nothing ever says when it may go.
    """
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "3600")
    stored = _store_upload(workspace)
    _age(stored, 7200)

    response = _client().post("/uploads/cleanup")

    assert response.status_code == 200
    assert response.json()["removed"] == 1
    assert not stored.exists()


def test_the_retention_window_is_configurable(workspace: Path, monkeypatch) -> None:
    """A deployment chooses its own window."""
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "60")
    stored = _store_upload(workspace)
    _age(stored, 120)

    assert api_module._upload_retention_seconds() == 60
    assert _client().post("/uploads/cleanup").json()["removed"] == 1
    assert not stored.exists()


def test_a_retention_window_that_cannot_be_read_falls_back_to_the_default(
    monkeypatch,
) -> None:
    """A policy that cannot be read is not one to guess at.

    The window decides whether a file the analysis read is deleted, so a
    mistyped value must not be read as "delete everything now" or as
    "keep everything for ever".
    """
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "not a number")
    assert api_module._upload_retention_seconds() == api_module.UPLOAD_RETENTION_SECONDS

    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "-5")
    assert api_module._upload_retention_seconds() == api_module.UPLOAD_RETENTION_SECONDS


def test_the_upload_of_a_running_analysis_is_not_removed(workspace: Path, monkeypatch) -> None:
    """The sweep never removes the file an analysis is reading.

    A file that disappears under a running analysis is a failure of the
    analysis, and it would look like one: the analysis would report that
    it could not read the APK.
    """
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "0")
    stored = _store_upload(workspace)
    _age(stored, 7200)

    api_module._RUNNING.start("apk_in_use", stored)
    try:
        assert api_module._expire_uploads(Settings(workspace=workspace)) == []
        assert stored.exists()
    finally:
        api_module._RUNNING.finish("apk_in_use")


def test_the_stored_uploads_are_listed_with_their_age(workspace: Path, monkeypatch) -> None:
    """The operator can see what is being kept, and for how long."""
    monkeypatch.setenv(api_module.UPLOAD_RETENTION_ENV, "3600")
    stored = _store_upload(workspace)
    _age(stored, 600)

    response = _client().get("/uploads")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["sha256"] == FAKE_HASH
    assert body[0]["name"] == "app.apk"
    assert body[0]["size_bytes"] > 0
    assert 500 < body[0]["age_seconds"] < 700
    assert 2900 < body[0]["expires_in_seconds"] < 3100


def test_deleting_an_upload_removes_it_now(workspace: Path) -> None:
    """An operator can remove one upload without waiting for the sweep.

    The bytes the analysis read go with it; the project's record of the
    APK -- its hash, its size and its name -- does not.
    """
    stored = _store_upload(workspace)

    response = _client().delete(f"/uploads/{FAKE_HASH}")

    assert response.status_code == 204
    assert not stored.exists()


def test_deleting_an_upload_that_is_not_there_is_a_not_found(workspace: Path) -> None:
    """The endpoint says so rather than pretending it did something."""
    _store_upload(workspace)

    response = _client().delete(f"/uploads/{'b' * 64}")

    assert response.status_code == 404


def test_a_name_that_is_not_a_hash_cannot_name_a_directory(workspace: Path) -> None:
    """The hash comes from the request, and a request does not name directories."""
    stored = _store_upload(workspace)

    response = _client().delete("/uploads/not-a-hash")

    assert response.status_code == 400
    assert stored.exists()


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def test_a_cancelled_analysis_publishes_nothing(
    settings: Settings, minimal_apk: Path, monkeypatch
) -> None:
    """A cancelled run leaves the published snapshot exactly as it was.

    The cancellation is checked before the run publishes, so the snapshot
    that was published before it is still the one the project holds.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")
    result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
    project_id = result.project.id
    published = analyzer.store.get_published_run_id(project_id)
    assert published is not None
    before = [c.name for c in analyzer.store.list_classes(project_id)]

    token = CancellationToken()
    token.cancel()

    with pytest.raises(AnalysisCancelled):
        analyzer.analyze(
            minimal_apk,
            include_apktool=False,
            include_jadx=False,
            cancellation=token,
        )

    assert [c.name for c in analyzer.store.list_classes(project_id)] == before
    assert analyzer.store.get_published_run_id(project_id) == published
    stored = analyzer.store.get_project(project_id)
    assert stored is not None
    assert stored.status is ProjectStatus.FAILED


def test_a_cancelled_run_is_recorded_as_cancelled(
    settings: Settings, minimal_apk: Path, monkeypatch
) -> None:
    """The run's own record says what happened to it.

    The project's status has no value for a cancellation -- it is not a
    failure and it is not a result -- so the run's own record is where
    the distinction is kept.
    """
    analyzer = Analyzer(settings)
    token = CancellationToken()
    token.cancel()

    with pytest.raises(AnalysisCancelled):
        analyzer.analyze(
            minimal_apk,
            include_apktool=False,
            include_jadx=False,
            cancellation=token,
        )

    runs = analyzer.store.list_runs(Project.create(_metadata(minimal_apk)).id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.CANCELLED


def test_the_cancel_endpoint_asks_the_running_analysis_to_stop(workspace: Path) -> None:
    """The endpoint stops the analysis it is asked about.

    The answer is that the request was accepted, not that the analysis has
    stopped: a backend that is half way through reading the APK finishes
    reading it first.
    """
    token = api_module._RUNNING.start("apk_running", workspace / "uploads" / "app.apk")
    try:
        response = _client().post("/projects/apk_running/cancel")

        assert response.status_code == 202
        assert response.json()["status"] == "cancelling"
        assert token.cancelled
    finally:
        api_module._RUNNING.finish("apk_running")


def test_cancelling_an_analysis_that_is_not_running_is_a_not_found(
    workspace: Path,
) -> None:
    """There is nothing to cancel, and the endpoint says so."""
    response = _client().post("/projects/apk_nothing/cancel")

    assert response.status_code == 404


def test_the_background_task_reports_a_cancellation_as_a_cancellation(
    settings: Settings, minimal_apk: Path, monkeypatch, caplog
) -> None:
    """A cancellation is not a failure.

    A log that says "failed" for a run the operator stopped sends the
    reader looking for a fault that is not there.
    """
    analyzer = Analyzer(settings)

    def cancelling(self: Analyzer, apk_path: Path, **kwargs: object):
        raise AnalysisCancelled("the analysis was cancelled")

    monkeypatch.setattr(Analyzer, "analyze", cancelling)

    with caplog.at_level(logging.INFO):
        api_module._run_analysis(analyzer, minimal_apk, _metadata(minimal_apk))

    assert "cancelled" in caplog.text
    assert "failed" not in caplog.text


# ---------------------------------------------------------------------------
# The runs of a project
# ---------------------------------------------------------------------------


def test_the_runs_of_a_project_are_listed_with_the_published_one_marked(
    workspace: Path,
) -> None:
    """A reader can say which run produced the results in front of them."""
    store = Store.open(workspace / "dexatlas.db")
    project = Project.create(_project_metadata())
    store.save_project(project, None, None)

    first = AnalysisRun.start(project.id, project.apk.sha256)
    first.status = RunStatus.COMPLETED
    store.create_run(first)
    second = AnalysisRun.start(project.id, project.apk.sha256)
    second.status = RunStatus.RUNNING
    store.create_run(second)
    store.publish_run(project, first, _empty_staging(workspace), None)

    response = _client().get(f"/projects/{project.id}/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["published_run_id"] == first.id
    published = [run for run in body["runs"] if run["published"]]
    assert len(published) == 1
    assert published[0]["id"] == first.id
    assert published[0]["status"] == "completed"
    assert published[0]["completeness"] == "complete"


def test_a_run_that_is_not_the_projects_is_a_not_found(workspace: Path) -> None:
    """A run id from another project is not this project's run."""
    store = Store.open(workspace / "dexatlas.db")
    project = Project.create(_project_metadata())
    store.save_project(project, None, None)
    other = AnalysisRun.start(project.id, project.apk.sha256)
    store.create_run(other)

    response = _client().get(f"/projects/{project.id}/runs/run_does_not_exist")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _metadata(apk: Path):
    from dexatlas.core.ingest import inspect_apk

    return inspect_apk(apk)


def _project_metadata() -> ApkMetadata:
    """Metadata for an APK that is not on disk.

    The runs of a project are read from the database, so the project only
    has to exist -- there is no file to analyse.
    """
    return ApkMetadata(sha256="d" * 64, size_bytes=10, path=Path("app.apk"))


def _empty_staging(workspace: Path) -> Path:
    """A staged database with nothing in it, ready to be published."""
    staged = workspace / "staging.db"
    store = Store.open(staged)
    project = Project.create(_project_metadata())
    store.save_project(project, None, None)
    store.save_symbols(
        project.id, [ClassRef(name="com.fake.One", kind=ClassKind.CLASS)], [], [], [], [], []
    )
    return staged
