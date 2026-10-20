"""The liveness probe must not need the database.

``/health`` answers two questions: is this process alive, and which analysis
backends can this deployment use. Both are facts about the machine, so neither
needs the workspace database.

It matters more than tidiness. SQLite allows one writer at a time, so a probe
that opened the workspace took the write lock on every request — which is
enough to lock the analysis that is running out of the workspace it is
analysing into, and to be locked out itself once the timeout ran out. A
service that answers "am I alive?" must not be able to take the service down.

These tests ask for the probe by behaviour: what it leaves behind, and what it
does while somebody else holds the database.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas import __version__
from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.storage import Store

#: How many probes are sent at once when they are sent at once.
_CONCURRENT_PROBES = 24


@contextmanager
def _client(settings: Settings) -> Iterator[TestClient]:
    """A client bound to these settings.

    Server errors are returned rather than raised, so a probe that fails the
    way this defect makes it fail — with a 500 — is something a test can make
    an assertion about.
    """
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@contextmanager
def _write_lock_held(path: Path) -> Iterator[None]:
    """Hold the database's single write lock while the block runs.

    SQLite allows one writer at a time. A connection that has begun an
    immediate transaction holds that lock until it commits or rolls back, and
    every other writer waits for it and gives up with ``database is locked``
    once its timeout runs out. A reader is not affected: in WAL mode it sees
    the last committed state.
    """
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE schema_info SET version = version")
        yield
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def workspace_settings(tmp_path: Path) -> Settings:
    """Settings for a workspace that exists and holds a database."""
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    Store.open(settings.database_path)
    return settings


# -- the probe does not need the database ------------------------------------


def test_health_answers_when_the_database_cannot_exist(tmp_path: Path) -> None:
    """The probe answers even when there is nowhere to put a database.

    The workspace is a file, so no database can be created inside it: an open
    that wanted one would fail, and the probe would answer 500.
    """
    workspace = tmp_path / "workspace"
    workspace.write_text("this is a file, not a directory", encoding="utf-8")

    with _client(Settings(workspace=workspace)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_leaves_no_database_behind(tmp_path: Path) -> None:
    """The probe does not create the workspace's database."""
    workspace = tmp_path / "workspace"

    with _client(Settings(workspace=workspace)) as client:
        assert client.get("/health").status_code == 200

    assert not (workspace / "dexatlas.db").exists()


def test_backends_leaves_no_database_behind(tmp_path: Path) -> None:
    """The backend listing does not create the workspace's database either."""
    workspace = tmp_path / "workspace"

    with _client(Settings(workspace=workspace)) as client:
        assert client.get("/backends").status_code == 200

    assert not (workspace / "dexatlas.db").exists()


def test_health_answers_while_the_database_is_locked(workspace_settings: Settings) -> None:
    """The probe answers while the database's one writer is busy.

    This is the failure this defect produced: the probe opened the workspace,
    the open wrote, the write waited for the writer that held the lock, and
    the probe answered 500 with "database is locked" once the timeout ran out.
    """
    with (
        _write_lock_held(workspace_settings.database_path),
        _client(workspace_settings) as client,
    ):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_concurrent_health_probes_all_answer(workspace_settings: Settings) -> None:
    """No probe fails when the probes overlap."""
    with _client(workspace_settings) as client, ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: client.get("/health"), range(_CONCURRENT_PROBES)))

    assert [response.status_code for response in responses] == [200] * _CONCURRENT_PROBES


def test_concurrent_health_probes_all_answer_while_the_database_is_locked(
    workspace_settings: Settings,
) -> None:
    """No probe fails when the probes overlap and the database is busy.

    The writer holds the lock for the whole run, so every probe that tried to
    write would wait for the whole timeout and answer 500. Probes that only
    read are not kept out by the lock.
    """
    with (
        _write_lock_held(workspace_settings.database_path),
        _client(workspace_settings) as client,
        ThreadPoolExecutor(max_workers=8) as pool,
    ):
        responses = list(pool.map(lambda _: client.get("/health"), range(_CONCURRENT_PROBES)))

    assert [response.status_code for response in responses] == [200] * _CONCURRENT_PROBES


# -- the probe still answers the question it is there to answer --------------


def test_health_reports_the_version_and_the_backends(workspace_settings: Settings) -> None:
    """The probe still says which backends this deployment can use."""
    with _client(workspace_settings) as client:
        body = client.get("/health").json()

    assert body["version"] == __version__
    assert set(body["backends"]) == {"jadx", "apktool", "androguard"}
