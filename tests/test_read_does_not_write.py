"""A read of the database must not write to it.

The journal mode used to be set on every connection. The journal mode is a
property of the *database* rather than of the connection, and setting it is
a write -- so every read of the workspace database was a write, and SQLite
allows one writer at a time. The consequence was not theoretical: two
concurrent requests produced

    sqlite3.OperationalError: database is locked
      File "src/dexatlas/core/storage.py", line 375, in transaction
        connection.execute("PRAGMA journal_mode = WAL")

with that line at the top of the stack, and the second request answered
with a 500.

The tests here do not race anything. A read is a read, and the question --
"did this read change the database?" -- has an answer that does not depend
on timing.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import pytest

from dexatlas.core.storage import Store


def _journal_mode(path: Path) -> str:
    """The journal mode of the database at a path, read without changing it."""
    connection = sqlite3.connect(path)
    try:
        row = connection.execute("PRAGMA journal_mode").fetchone()
        return str(row[0]).lower() if row else ""
    finally:
        connection.close()


def _modified_at(path: Path) -> float:
    """When the database file was last written."""
    return os.stat(path).st_mtime


def test_a_read_does_not_change_the_database(tmp_path: Path) -> None:
    """Reading the database leaves it exactly as it was."""
    store = Store.open(tmp_path / "dexatlas.db")
    store.save_project(
        _project(),
        tmp_path / "workspace",
        manifest=None,
    )

    database = tmp_path / "dexatlas.db"
    before = _modified_at(database)
    content_before = database.read_bytes()

    # A read, through the same path a request takes.
    store.list_projects()
    store.get_project("apk_" + "a" * 16)

    assert _modified_at(database) == before, "a read changed the database file"
    assert database.read_bytes() == content_before


def test_a_read_does_not_set_the_journal_mode(tmp_path: Path) -> None:
    """A read does not put the database into WAL mode.

    Setting the journal mode is a write, and it cannot be done from inside
    a transaction -- so a connection that sets it takes a lock that a read
    has no business taking. On a database that is already in WAL mode the
    statement happens to do nothing; on one that is not, it changes the
    file. A read must not depend on which of those two it finds.

    The mode is put back to ``delete`` here, so the read has something to
    change -- and a read that leaves it alone is the claim being checked.
    """
    database = tmp_path / "dexatlas.db"
    store = Store.open(database)

    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.commit()
    connection.close()
    assert _journal_mode(database) == "delete"

    store.list_projects()

    assert _journal_mode(database) == "delete", "a read put the database into WAL mode"


def test_the_journal_mode_is_set_once_and_not_on_every_connection(tmp_path: Path) -> None:
    """The mode is a property of the database, so it is set when it changes.

    A database that is already in WAL mode is not put into it again: the
    statement that does it is a write, and a write on every connection is
    what this change removed.
    """
    database = tmp_path / "dexatlas.db"
    Store.open(database)
    assert _journal_mode(database) == "wal", "the database was not put into WAL mode"

    before = _modified_at(database)
    Store.open(database)

    assert _modified_at(database) == before, "opening the workspace wrote to it again"


def test_a_database_created_without_wal_is_put_into_wal(tmp_path: Path) -> None:
    """A workspace that was not in WAL mode is moved into it.

    The mode is set when it differs, not only when the schema is written --
    a workspace created by an older build, or by another tool, has to end
    up in the same mode as a new one.
    """
    database = tmp_path / "dexatlas.db"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("CREATE TABLE placeholder (id INTEGER)")
    connection.commit()
    connection.close()
    assert _journal_mode(database) != "wal"

    Store.open(database)

    assert _journal_mode(database) == "wal"


def test_two_reads_do_not_lock_each_other_out(tmp_path: Path) -> None:
    """A reader does not take the lock a writer needs.

    SQLite allows one writer at a time. A read that is really a write
    takes that writer's place, so a second writer waits for it -- and the
    wait ends in ``database is locked`` once the timeout runs out. The
    first writer here holds the lock the whole time; the reads have to go
    through anyway.
    """
    database = tmp_path / "dexatlas.db"
    store = Store.open(database)

    holder = sqlite3.connect(database, timeout=1)
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("CREATE TABLE held (id INTEGER)")

        # The reads must not wait for the writer's lock.
        started = time.monotonic()
        store.list_projects()
        elapsed = time.monotonic() - started

        assert elapsed < 1.0, f"a read waited {elapsed:.2f}s for the write lock"
    finally:
        holder.rollback()
        holder.close()


def _project():
    """A project to store, so the database is not empty."""
    from dexatlas.core.models import ApkMetadata, Project

    return Project.create(
        ApkMetadata(sha256="a" * 64, size_bytes=16, path=Path("/tmp/example.apk"))
    )


@pytest.mark.parametrize("name", ["dexatlas.db"])
def test_the_store_opens_a_workspace_that_does_not_exist_yet(tmp_path: Path, name: str) -> None:
    """Opening a workspace that is not there creates it, in WAL mode."""
    database = tmp_path / name

    Store.open(database)

    assert database.is_file()
    assert _journal_mode(database) == "wal"
