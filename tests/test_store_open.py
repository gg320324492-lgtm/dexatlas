"""What opening a workspace does to the database.

SQLite allows one writer at a time. An open that writes therefore makes every
other writer wait for it, and the wait ends in ``database is locked`` once the
timeout runs out. So an open that writes when it had no reason to can stop the
server from using the workspace it is running against.

These tests pin the two halves of that: the cases where an open really does
have to write — a new workspace, an older one, a table that went missing — and
the case where it must not, which is an open of a workspace that is already
right.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dexatlas.core.storage import SCHEMA_VERSION, Store

#: A time no clock reports: 2001-09-09. A file stamped with it can be told
#: apart from one that was written, whatever the filesystem's clock resolution.
_MARKER_TIME = 1_000_000_000
_MARKER_MTIME_NS = _MARKER_TIME * 1_000_000_000

#: The ``projects`` table as it was before the resource count was added to it.
#: A workspace written by that build has no resource count column and no
#: resource table, and the migration is what brings it up to date.
_V1_PROJECTS = """
CREATE TABLE projects (
    id               TEXT PRIMARY KEY,
    apk_sha256       TEXT NOT NULL UNIQUE,
    apk_path         TEXT NOT NULL,
    apk_size_bytes   INTEGER NOT NULL,
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL,
    tool_versions    TEXT NOT NULL DEFAULT '{}',
    errors           TEXT NOT NULL DEFAULT '[]',
    class_count      INTEGER NOT NULL DEFAULT 0,
    method_count     INTEGER NOT NULL DEFAULT 0,
    reference_count  INTEGER NOT NULL DEFAULT 0,
    evidence_count   INTEGER NOT NULL DEFAULT 0,
    manifest         TEXT,
    workspace        TEXT
)
"""


@contextmanager
def _writing(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection that writes to the database, and is closed afterwards."""
    connection = sqlite3.connect(path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


@contextmanager
def _reading(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection that reads from the database, and is closed afterwards."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _write_lock_held(path: Path) -> Iterator[None]:
    """Hold the database's single write lock while the block runs.

    SQLite allows one writer at a time, and a connection that has begun an
    immediate transaction holds that lock until it commits or rolls back.
    Every other writer waits for it, and gives up with ``database is locked``
    once its timeout runs out — which is exactly what happens to an open that
    writes while another writer is busy. An open that only reads is not
    affected: in WAL mode a reader sees the last committed state.
    """
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE schema_info SET version = version")
        yield
    finally:
        connection.rollback()
        connection.close()


def _tables(path: Path) -> set[str]:
    with _reading(path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def _version(path: Path) -> tuple[int, ...]:
    with _reading(path) as connection:
        row = connection.execute("SELECT version FROM schema_info").fetchone()
    return tuple(row) if row is not None else ()


def _version_rows(path: Path) -> list[int]:
    with _reading(path) as connection:
        rows = connection.execute("SELECT version FROM schema_info").fetchall()
    return [row[0] for row in rows]


# -- the opens that have to write -------------------------------------------


def test_a_new_workspace_is_created(tmp_path: Path) -> None:
    """The first open creates the directory, the file, the tables and the version."""
    path = tmp_path / "workspace" / "dexatlas.db"

    Store.open(path)

    assert path.exists()
    assert {"projects", "classes", "methods", "fields", "xrefs", "strings", "resources"} <= _tables(
        path
    )
    assert _version(path) == (SCHEMA_VERSION,)


def test_an_older_workspace_is_upgraded(tmp_path: Path) -> None:
    """A workspace written by an older build is brought up to the current schema."""
    path = tmp_path / "dexatlas.db"
    with _writing(path) as connection:
        connection.execute("CREATE TABLE schema_info (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_info (version) VALUES (1)")
        connection.execute(_V1_PROJECTS)

    Store.open(path)

    assert _version(path) == (SCHEMA_VERSION,)
    assert "resources" in _tables(path)


def test_the_migration_still_runs_on_an_older_workspace(tmp_path: Path) -> None:
    """The column an older build did not have is added, rather than skipped."""
    path = tmp_path / "dexatlas.db"
    with _writing(path) as connection:
        connection.execute("CREATE TABLE schema_info (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_info (version) VALUES (1)")
        connection.execute(_V1_PROJECTS)

    Store.open(path)

    with _reading(path) as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
    assert "resource_count" in columns


def test_a_missing_table_is_created(tmp_path: Path) -> None:
    """A workspace that lost a table gets it back, whatever version it records."""
    path = tmp_path / "dexatlas.db"
    Store.open(path)
    with _writing(path) as connection:
        connection.execute("DROP TABLE resources")

    Store.open(path)

    assert "resources" in _tables(path)


# -- the open that must not write -------------------------------------------


def test_reopening_a_current_workspace_writes_nothing(tmp_path: Path) -> None:
    """A workspace that is already right is left exactly as it was found.

    The file is stamped with a time no clock reports first, so a write cannot
    hide behind the filesystem's clock resolution — and the content cannot
    hide it either, because rewriting the version row writes the same bytes
    back. The timestamp is what shows the write happened.
    """
    path = tmp_path / "dexatlas.db"
    Store.open(path)
    os.utime(path, (_MARKER_TIME, _MARKER_TIME))

    Store.open(path)

    assert os.stat(path).st_mtime_ns == _MARKER_MTIME_NS


def test_reopening_a_current_workspace_does_not_need_the_write_lock(tmp_path: Path) -> None:
    """An open that only reads is not shut out by the writer holding the lock."""
    path = tmp_path / "dexatlas.db"
    Store.open(path)

    with _write_lock_held(path):
        # Raises "database is locked" if the open writes.
        Store.open(path)


def test_reopening_a_current_workspace_does_not_rewrite_the_version_table(tmp_path: Path) -> None:
    """The rows of the version table are left exactly as they were found.

    A second row is put in the table to make a rewrite visible: an open that
    cleared the table and wrote the version back would drop it. The row
    records the current version, so which of the two rows an open reads first
    does not change what it decides to do.
    """
    path = tmp_path / "dexatlas.db"
    Store.open(path)
    with _writing(path) as connection:
        connection.execute("INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,))

    Store.open(path)

    assert _version_rows(path) == [SCHEMA_VERSION, SCHEMA_VERSION]
