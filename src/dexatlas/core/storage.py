"""SQLite-backed project storage and full-text symbol search.

SQLite FTS5 is the primary retrieval channel. Code search, exact symbol resolution and
cross-references answer most questions precisely; semantic retrieval is a Phase 2
supplement, never a prerequisite.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    FieldRef,
    ManifestInfo,
    MethodRef,
    MethodReference,
    Project,
    ProjectStatus,
    ResourceKind,
    ResourceString,
    StringConstant,
    ToolError,
    canonical_descriptor,
    canonical_method_id,
)
from dexatlas.core.runs import AnalysisRun, RunCompleteness, RunStatus

SCHEMA_VERSION = 4

#: The tables that hold a project's published snapshot.
#:
#: Everything a reader sees about a project's symbols and its evidence lives
#: here, and it is replaced as a whole when a run publishes: one run's
#: symbols are never beside another's evidence.
#:
#: The evidence table belongs in this list for the same reason the symbol
#: tables do: it is written afresh by every analysis, and a table that is
#: not cleared keeps the rows of the earlier run. The ids are assigned in
#: sequence, so a record left behind keeps an id that the new run has already
#: given to a different record — and the database ends up holding rows that
#: the report does not mention, which is the opposite of what an evidence
#: table is for.
_PROJECT_TABLES = (
    "classes",
    "methods",
    "fields",
    "xrefs",
    "strings",
    "resources",
    "search_index",
    "evidence",
)


@dataclass(frozen=True, slots=True)
class SymbolCounts:
    """How many rows each symbol table holds for one project.

    These are measured after the write, not predicted from the lists that were
    handed in. The tables collapse duplicate keys — a class defined in two dex
    files is one row — so a count taken from the input is a number the database
    cannot produce, and a report built on it disagrees with every query run
    against it.
    """

    classes: int
    methods: int
    fields: int
    references: int
    resources: int = 0


_RESOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS resources (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    value      TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'string',
    quantity   TEXT NOT NULL DEFAULT '',
    qualifier  TEXT,
    position   INTEGER NOT NULL DEFAULT 0,
    file       TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, file, name, kind, quantity, position)
);
"""

#: The whole schema. The resource table is spliced in rather than written out
#: twice: the migration below has to recreate it with the same statement.
_SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
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
    resource_count   INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL,
    manifest         TEXT,
    workspace        TEXT,
    published_run_id TEXT
);

-- One row per analysis attempt. The run id says nothing about the APK: two
-- analyses of the same bytes are two runs, and the project id -- a content
-- hash -- cannot tell them apart.
--
-- The row is the run's own record of what happened: which tools took part and
-- at which versions, how the execution ended, and how much of what the run
-- set out to read it actually read. The project's row carries the *published*
-- snapshot's figures; this carries the attempt's.
CREATE TABLE IF NOT EXISTS analysis_runs (
    id               TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    apk_sha256       TEXT NOT NULL,
    status           TEXT NOT NULL,
    completeness     TEXT NOT NULL DEFAULT 'complete',
    tool_versions    TEXT NOT NULL DEFAULT '{}',
    errors           TEXT NOT NULL DEFAULT '[]',
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    duration_seconds REAL,
    workspace        TEXT
);

CREATE TABLE IF NOT EXISTS classes (
    project_id   TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL,
    superclass   TEXT,
    interfaces   TEXT NOT NULL DEFAULT '[]',
    access_flags TEXT NOT NULL DEFAULT '[]',
    method_count INTEGER NOT NULL DEFAULT 0,
    field_count  INTEGER NOT NULL DEFAULT 0,
    provenance   TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, name)
);

CREATE TABLE IF NOT EXISTS methods (
    project_id   TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    class_name   TEXT NOT NULL,
    name         TEXT NOT NULL,
    descriptor   TEXT NOT NULL,
    access_flags TEXT NOT NULL DEFAULT '[]',
    signature    TEXT,
    decompiled   INTEGER NOT NULL DEFAULT 0,
    provenance   TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, class_name, name, descriptor)
);

CREATE TABLE IF NOT EXISTS fields (
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    class_name      TEXT NOT NULL,
    name            TEXT NOT NULL,
    descriptor      TEXT NOT NULL,
    access_flags    TEXT NOT NULL DEFAULT '[]',
    constant_value  TEXT,
    provenance      TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, class_name, name, descriptor)
);

CREATE TABLE IF NOT EXISTS xrefs (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    caller     TEXT NOT NULL,
    callee     TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'invoke',
    provenance TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS strings (
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    value       TEXT NOT NULL,
    class_name  TEXT,
    method_name TEXT,
    provenance  TEXT NOT NULL DEFAULT '[]'
);

"""
    + _RESOURCES_TABLE
    + """
CREATE TABLE IF NOT EXISTS evidence (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    id         TEXT NOT NULL,
    kind       TEXT NOT NULL,
    level      TEXT NOT NULL,
    summary    TEXT NOT NULL,
    detail     TEXT NOT NULL DEFAULT '{}',
    provenance TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, id)
);

CREATE INDEX IF NOT EXISTS idx_classes_project ON classes(project_id);
CREATE INDEX IF NOT EXISTS idx_methods_class   ON methods(project_id, class_name);
CREATE INDEX IF NOT EXISTS idx_refs_caller     ON xrefs(project_id, caller);
-- The lookup compares the *canonical* form of a callee, so the index is on that
-- form. A workspace indexed before descriptors were canonicalised holds the
-- spaced spelling, and it still has to be found — without this index the
-- comparison would be a scan of every cross-reference in the project.
CREATE INDEX IF NOT EXISTS idx_refs_callee_canonical
    ON xrefs(project_id, REPLACE(callee, ' ', ''));
CREATE INDEX IF NOT EXISTS idx_strings_project ON strings(project_id);
CREATE INDEX IF NOT EXISTS idx_resources_project ON resources(project_id);
CREATE INDEX IF NOT EXISTS idx_resources_name ON resources(project_id, name);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    kind UNINDEXED,
    qualified_name UNINDEXED,
    project_id UNINDEXED,
    body,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""
)

#: The tables the schema declares.
#:
#: Read out of the schema itself rather than written out here, so that a table
#: added to the schema is one this list already knows about. If the pattern
#: ever stops matching, the list is empty and the comparison below degrades to
#: the schema version alone — which is the condition that decides an upgrade,
#: so a new table still reaches an existing workspace when the version moves.
_SCHEMA_TABLES = frozenset(re.findall(r"CREATE (?:VIRTUAL )?TABLE IF NOT EXISTS (\w+)", _SCHEMA))

_PROJECT_UPSERT = """
INSERT INTO projects (
    id, apk_sha256, apk_path, apk_size_bytes, created_at, status,
    tool_versions, errors, class_count, method_count,
    reference_count, evidence_count, resource_count, duration_seconds,
    manifest, workspace
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    apk_path      = excluded.apk_path,
    status        = excluded.status,
    tool_versions = excluded.tool_versions,
    errors        = excluded.errors,
    class_count   = excluded.class_count,
    method_count  = excluded.method_count,
    reference_count = excluded.reference_count,
    evidence_count  = excluded.evidence_count,
    resource_count  = excluded.resource_count,
    duration_seconds = excluded.duration_seconds,
    manifest      = excluded.manifest,
    -- The workspace is the pointer to the published run's directory, so a
    -- write that does not name one leaves the pointer where it is. A run
    -- that has not published yet must not move it: the reader of the
    -- workspace would follow it into a directory that was never published.
    workspace     = COALESCE(excluded.workspace, projects.workspace)
"""

_RUN_UPSERT = """
INSERT INTO analysis_runs (
    id, project_id, apk_sha256, status, completeness, tool_versions, errors,
    started_at, finished_at, duration_seconds, workspace
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    status           = excluded.status,
    completeness     = excluded.completeness,
    tool_versions    = excluded.tool_versions,
    errors           = excluded.errors,
    finished_at      = excluded.finished_at,
    duration_seconds = excluded.duration_seconds,
    workspace        = excluded.workspace
"""


def parse_method_id(method_id: str) -> tuple[str, str, str]:
    """Split ``com.foo.Bar.baz(Ljava/lang/String;)V`` into ``(class, name, descriptor)``.

    The descriptor begins at the first ``(``, so the class boundary is the last ``.``
    before it. Returns ``("", "", "")`` for input that is not a qualified method id.
    """
    open_paren = method_id.find("(")
    if open_paren == -1:
        return "", "", ""
    class_name, _, name = method_id[:open_paren].rpartition(".")
    if not class_name:
        return "", "", ""
    return class_name, name, method_id[open_paren:]


def _escape_like(value: str) -> str:
    """Escape ``value`` so SQLite's LIKE treats it as a literal.

    SQLite's LIKE has two wildcards: ``%`` matches any run of characters and ``_``
    matches any single one. A literal underscore is legal in a package name, so a
    prefix filter that leaves it unescaped returns classes whose names merely look
    like the prefix. The backslash is the LIKE escape character and is escaped
    first: escaping it later would double-escape the escapes this function
    introduces for the two wildcards.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _migrate(connection: sqlite3.Connection) -> None:
    """Bring an older workspace up to the current schema.

    ``CREATE TABLE IF NOT EXISTS`` does not change a table that already exists,
    so a workspace written before a column was added keeps the old shape and
    every write that names the new column fails. The column is added here
    instead: an existing row reads as zero, which is the truth about it — a
    workspace analysed before the resource table was read holds no resources.

    Two kinds of change live here, and only one of them is additive.

    A *column* is added in place, and the rows keep their values. A column
    that could not be added without rewriting the table would mean the old
    rows had to be migrated, and that is a different job.

    A *table* is rebuilt, and its rows do not survive the rebuild. The
    resource table's key changed when ``<string-array>`` entries were given a
    position, and under the old key one item of an array overwrites the next;
    SQLite cannot change a primary key in place, so the table is dropped and
    created empty. Losing the rows is affordable because the table is a cache
    of an analysis rather than a source of truth: the next analysis fills it
    again. These two changes are the whole of what this function does — the
    schema version is recorded by the caller.

    A column that holds a *measurement* is added without a default, and the
    rows that were already there read as nothing rather than as zero. The
    analysis time is a measurement of one run; a workspace written before the
    measurement was stored never took one, and zero is a number that run
    never reported.
    """
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
    if "resource_count" not in columns:
        connection.execute(
            "ALTER TABLE projects ADD COLUMN resource_count INTEGER NOT NULL DEFAULT 0"
        )
    if "duration_seconds" not in columns:
        connection.execute("ALTER TABLE projects ADD COLUMN duration_seconds REAL")
    if "published_run_id" not in columns:
        # The pointer to the run whose snapshot is published. A workspace
        # written before runs existed has no run to point at, and its rows
        # are the published snapshot of an analysis nobody recorded -- so the
        # pointer reads as nothing rather than as a run that never happened.
        connection.execute("ALTER TABLE projects ADD COLUMN published_run_id TEXT")

    resource_columns = {row["name"] for row in connection.execute("PRAGMA table_info(resources)")}
    if resource_columns and "position" not in resource_columns:
        # A workspace written by an earlier build of the resource table has no
        # position, and its key lets one item of a ``<string-array>`` overwrite
        # the next. The table is a cache of the analysis rather than a source
        # of truth — the next analysis fills it again — so it is dropped and
        # created empty rather than migrated row by row.
        connection.execute("DROP TABLE resources")
        connection.execute(_RESOURCES_TABLE)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    """The tables the database holds."""
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def _journal_mode(connection: sqlite3.Connection) -> str:
    """The journal mode the database is in.

    Reading it does not write; changing it does. That difference is the
    whole of this function's reason to exist: the mode used to be set on
    every connection, which made every read of the database a write, and
    SQLite allows one writer at a time.
    """
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower() if row else ""


def _recorded_version(connection: sqlite3.Connection, tables: set[str]) -> int | None:
    """The schema version the database records, or ``None`` if it records none.

    A database that has never been written has no ``schema_info`` table, and one
    whose table is empty records no version. Both mean the same thing: this
    workspace has no schema yet.
    """
    if "schema_info" not in tables:
        return None
    row = connection.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
    return int(row[0]) if row is not None else None


class Store:
    """Project and symbol persistence."""

    def __init__(self, path: Path, connection: sqlite3.Connection | None = None) -> None:
        self._path = path
        self._connection = connection
        """The connection a read view holds, or ``None`` for an ordinary store.

        A store with a connection is a *view*: it reads through a
        transaction somebody else opened, and it neither opens transactions
        of its own nor commits.
        """

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open the workspace database, creating or upgrading it if it needs it.

        Opening a workspace that is already at the current schema version reads
        the database and writes nothing. That matters more than it sounds:
        SQLite allows one writer at a time, so a write taken on every open
        makes every other writer — including the analysis that is running —
        wait for it, and the wait ends in ``database is locked`` once the
        timeout runs out. A liveness probe that opens the workspace on every
        request is enough to lock a busy deployment out of its own database.

        A workspace that records a different version is upgraded: the schema is
        written out, the migration runs, and the new version is recorded. So is
        a workspace whose tables are missing, whatever version it claims.

        The recorded version is therefore what says the schema has changed, and
        a change to the schema has to come with a change to the version — an
        existing workspace is only rewritten when the version moves.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        store = cls(path)
        with store.transaction() as connection:
            tables = _table_names(connection)
            version = _recorded_version(connection, tables)

            # The journal mode is a property of the database, and setting it
            # is a write -- so it is set here, once, and only when the
            # database is not in it already. Reading the mode does not write;
            # changing it does, and it cannot be changed from inside a
            # transaction, so it happens before the schema is written.
            if _journal_mode(connection) != "wal":
                connection.execute("PRAGMA journal_mode = WAL")

            if version != SCHEMA_VERSION or not _SCHEMA_TABLES.issubset(tables):
                # The workspace does not hold this schema: it is new, it was
                # written by an older build, or a table is missing from it.
                # The statements are idempotent, so writing them over a
                # workspace that already has most of them changes nothing.
                connection.executescript(_SCHEMA)

            # The migration is never skipped. It writes only when it has a
            # change to make, and it needs the tables to be there to look at.
            _migrate(connection)

            if version != SCHEMA_VERSION:
                # The recorded version is what the next open compares against,
                # so it is written when it is wrong and left alone when it is
                # right. Writing it when it is right is what used to make
                # every open a write.
                connection.execute("DELETE FROM schema_info")
                connection.execute(
                    "INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,)
                )
        return store

    @contextmanager
    def reading(self) -> Iterator[Store]:
        """A read-only view of the workspace: one connection, one transaction.

        Every read through the view sees the same snapshot of the database.
        That is what stops a request that reads the symbols and then the
        evidence from seeing one run's symbols beside another's evidence: a
        publish that lands in between is invisible to a transaction that has
        already started reading.

        The view is for reading. It holds no write lock, it never commits,
        and it is closed when the block ends.
        """
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        # A deferred transaction: the snapshot is taken at the first read and
        # held until the transaction ends.
        connection.execute("BEGIN")
        try:
            yield Store(self._path, connection)
        finally:
            connection.rollback()
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """A connection to the workspace database, in a transaction.

        Only *connection* properties are set here. The journal mode is a
        property of the database rather than of the connection, and setting
        it is a write -- so it is set once, where the database is created or
        upgraded, and not on every connection. Setting it here made every
        read a write, and SQLite allows one writer at a time: a liveness
        probe that opened the workspace could lock the analysis out of its
        own database, and could be locked out itself.

        A read view already holds a transaction, so it reads through that
        one: opening a second would end the snapshot the view exists to
        hold.
        """
        if self._connection is not None:
            yield self._connection
            return
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # -- projects ----------------------------------------------------------

    def save_project(
        self, project: Project, workspace: Path | None, manifest: ManifestInfo | None
    ) -> None:
        """Record the project's own row.

        ``workspace`` is the pointer to the published run's directory. It is
        optional because a run that has not published yet has no directory to
        point at — and must not move the pointer to one it is about to
        write into.
        """
        with self.transaction() as connection:
            _save_project(connection, project, workspace, manifest)

    def begin_run(self, project: Project) -> None:
        """Record that a run has started on a project.

        Only the project's identity and its status are written. The counts,
        the manifest, the tool versions, the errors and the duration belong
        to the *published* snapshot: a run that has not published yet has
        nothing to say about them, and writing zeroes over a complete
        snapshot would leave the project describing nothing while its
        tables hold an analysis.

        A project that has never been analysed is created whole, because
        there is no snapshot of its own to preserve.
        """
        project.status = ProjectStatus.RUNNING
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project.id,)
            ).fetchone()
            if row is None:
                _save_project(connection, project, None, None)
                return
            connection.execute(
                "UPDATE projects SET status = ?, apk_path = ?, apk_size_bytes = ? WHERE id = ?",
                (
                    ProjectStatus.RUNNING.value,
                    str(project.apk.path),
                    project.apk.size_bytes,
                    project.id,
                ),
            )

    def set_project_state(
        self, project_id: str, status: ProjectStatus, errors: list[ToolError]
    ) -> None:
        """Record the project's status and errors, and nothing else.

        The counts, the manifest and the workspace belong to the *published*
        snapshot. A run that failed published nothing, so writing the
        project's whole record here would replace the published run's
        figures with zeroes and point the workspace at a directory that was
        never published — which is the opposite of leaving the previous
        complete run intact.
        """
        with self.transaction() as connection:
            connection.execute(
                "UPDATE projects SET status = ?, errors = ? WHERE id = ?",
                (
                    status.value,
                    json.dumps([e.model_dump(mode="json") for e in errors]),
                    project_id,
                ),
            )

    def get_project(self, project_id: str) -> Project | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return _row_to_project(row) if row else None

    def find_project_by_hash(self, sha256: str) -> Project | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE apk_sha256 = ?", (sha256,)
            ).fetchone()
        return _row_to_project(row) if row else None

    def list_projects(self) -> list[Project]:
        with self.transaction() as connection:
            rows = connection.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [_row_to_project(row) for row in rows]

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE projects SET status = ? WHERE id = ?", (status.value, project_id)
            )

    def get_manifest(self, project_id: str) -> ManifestInfo | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT manifest FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if not row or not row["manifest"]:
            return None
        return ManifestInfo.model_validate_json(row["manifest"])

    def get_workspace(self, project_id: str) -> Path | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT workspace FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return Path(row["workspace"]) if row and row["workspace"] else None

    def delete_project(self, project_id: str) -> bool:
        with self.transaction() as connection:
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            for table in _PROJECT_TABLES:
                connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
        return cursor.rowcount > 0

    # -- runs --------------------------------------------------------------

    def create_run(self, run: AnalysisRun) -> None:
        """Record a run that has been created."""
        with self.transaction() as connection:
            _save_run(connection, run)

    def update_run(self, run: AnalysisRun) -> None:
        """Record what became of a run."""
        with self.transaction() as connection:
            _save_run(connection, run)

    def get_run(self, run_id: str) -> AnalysisRun | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return _row_to_run(row) if row else None

    def list_runs(self, project_id: str) -> list[AnalysisRun]:
        """Every run of a project, newest first."""
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM analysis_runs WHERE project_id = ? ORDER BY started_at DESC, id DESC",
                (project_id,),
            ).fetchall()
        return [_row_to_run(row) for row in rows]

    def get_published_run_id(self, project_id: str) -> str | None:
        """The run whose snapshot is published, when there is one.

        ``None`` for a workspace written before runs existed: its rows are
        the published snapshot of an analysis that was never recorded, so
        there is no run to name.
        """
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT published_run_id FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if not row or not row["published_run_id"]:
            return None
        return str(row["published_run_id"])

    def get_published_run(self, project_id: str) -> AnalysisRun | None:
        """The run whose snapshot is published, and its record."""
        run_id = self.get_published_run_id(project_id)
        return self.get_run(run_id) if run_id else None

    def publish_run(
        self,
        project: Project,
        run: AnalysisRun,
        staged: Path,
        manifest: ManifestInfo | None,
    ) -> None:
        """Publish a staged run as the project's snapshot.

        One transaction: the symbol tables, the evidence, the project's own
        row, the pointer to the run and the run's own row. A reader sees the
        previous run's snapshot or this one — never a mixture, and never this
        run's symbols beside the previous run's evidence.

        The staged results live in a database of their own, which is why they
        can be written at leisure and published in one go: a run that dies
        half way through leaves the published snapshot exactly as it was.
        """
        with self.transaction() as connection:
            _copy_staged_symbols(connection, project.id, staged)
            _save_project(connection, project, run.workspace, manifest)
            connection.execute(
                "UPDATE projects SET published_run_id = ? WHERE id = ?", (run.id, project.id)
            )
            _save_run(connection, run)

    # -- symbols -----------------------------------------------------------

    def save_symbols(
        self,
        project_id: str,
        classes: Iterable[ClassRef],
        methods: Iterable[MethodRef],
        fields: Iterable[FieldRef],
        references: Iterable[MethodReference],
        strings: Iterable[StringConstant],
        resources: Iterable[ResourceString] = (),
    ) -> SymbolCounts:
        """Replace a project's symbol tables. Callers re-analyse, so this is idempotent.

        The project's evidence is cleared here too, in the same transaction as
        the symbols: the analysis that follows writes a fresh set of it, and a
        reader of the database must never find the records of an earlier run
        beside the symbols of this one.

        Descriptors and method ids are stored in their canonical spelling. The models
        already normalise them, but the database is the durable contract: an id
        written here has to be the id the lookup below matches, whatever the caller
        handed in.

        The class row's ``method_count`` and ``field_count`` are counted from the
        rows this method writes, not taken from the class views it is handed. A
        backend reads one dex file, so a class split across two dex files is seen
        partly by each of them, and no view of it is the class's total. The rows
        are: the count in the class row is the number of rows a query returns.

        Returns the number of rows each table ended up holding. The count is the
        one a query returns, which is the only count a report may state: the
        symbol tables key on the symbol, so two dex files that define the same
        method are one row, and a count taken from the input list would be
        higher than anything the database can show.
        """
        # The lists are read twice: once for the tables, once for the search
        # index. Materialising them here keeps a caller that passes a generator
        # from filling the tables and leaving the search index empty.
        class_list = list(classes)
        method_list = list(methods)
        field_list = list(fields)
        reference_list = list(references)
        string_list = list(strings)
        resource_list = list(resources)

        with self.transaction() as connection:
            for table in _PROJECT_TABLES:
                connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))

            # The methods and the fields go in first: the class row's counts are
            # measured from them.
            connection.executemany(
                "INSERT OR REPLACE INTO methods VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        project_id,
                        m.class_name,
                        m.name,
                        canonical_descriptor(m.descriptor),
                        json.dumps(m.access_flags),
                        m.signature,
                        int(m.decompiled),
                        _dump_provenance(m),
                    )
                    for m in method_list
                ],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO fields VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        project_id,
                        f.class_name,
                        f.name,
                        canonical_descriptor(f.descriptor),
                        json.dumps(f.access_flags),
                        f.constant_value,
                        _dump_provenance(f),
                    )
                    for f in field_list
                ],
            )
            method_counts = _counts_by_class(connection, "methods", project_id)
            field_counts = _counts_by_class(connection, "fields", project_id)
            connection.executemany(
                "INSERT OR REPLACE INTO classes VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        project_id,
                        c.name,
                        c.kind.value,
                        c.superclass,
                        json.dumps(c.interfaces),
                        json.dumps(c.access_flags),
                        method_counts.get(c.name, 0),
                        field_counts.get(c.name, 0),
                        _dump_provenance(c),
                    )
                    for c in class_list
                ],
            )
            connection.executemany(
                "INSERT INTO xrefs VALUES (?,?,?,?,?)",
                [
                    (
                        project_id,
                        canonical_method_id(r.caller),
                        canonical_method_id(r.callee),
                        r.kind.value,
                        _dump_provenance(r),
                    )
                    for r in reference_list
                ],
            )
            connection.executemany(
                "INSERT INTO strings VALUES (?,?,?,?,?)",
                [
                    (project_id, s.value, s.class_name, s.method_name, _dump_provenance(s))
                    for s in string_list
                ],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        project_id,
                        r.name,
                        r.value,
                        r.kind.value,
                        r.quantity or "",
                        r.qualifier,
                        r.position,
                        r.file,
                        _dump_provenance(r),
                    )
                    for r in resource_list
                ],
            )
            connection.executemany(
                "INSERT INTO search_index (kind, qualified_name, project_id, body) VALUES (?,?,?,?)",
                _search_rows(
                    project_id, class_list, method_list, field_list, string_list, resource_list
                ),
            )

            return SymbolCounts(
                classes=_count_rows(connection, "classes", project_id),
                methods=_count_rows(connection, "methods", project_id),
                fields=_count_rows(connection, "fields", project_id),
                references=_count_rows(connection, "xrefs", project_id),
                resources=_count_rows(connection, "resources", project_id),
            )

    def list_classes(self, project_id: str, *, prefix: str | None = None) -> list[ClassRef]:
        query = "SELECT * FROM classes WHERE project_id = ?"
        params: list[Any] = [project_id]
        if prefix:
            query += " AND name LIKE ? ESCAPE '\\'"
            params.append(_escape_like(prefix) + "%")
        query += " ORDER BY name"
        with self.transaction() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_class(row) for row in rows]

    def get_class(self, project_id: str, class_name: str) -> ClassRef | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM classes WHERE project_id = ? AND name = ?",
                (project_id, class_name),
            ).fetchone()
        return _row_to_class(row) if row else None

    def list_methods(self, project_id: str, class_name: str | None = None) -> list[MethodRef]:
        query = "SELECT * FROM methods WHERE project_id = ?"
        params: list[Any] = [project_id]
        if class_name:
            query += " AND class_name = ?"
            params.append(class_name)
        query += " ORDER BY class_name, name"
        with self.transaction() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_method(row) for row in rows]

    def get_method_references(self, project_id: str, method_id: str) -> list[MethodReference]:
        """Callers of ``method_id``, formatted ``com.foo.Bar.baz(Ljava/lang/String;)V``.

        The comparison is on the canonical form of both sides: the id is
        canonicalised here, and the stored callee is canonicalised by the index. So a
        workspace indexed by an earlier version of DexAtlas — which stored the
        descriptor with Androguard's human-readable spacing — resolves just like a
        current one.
        """
        class_name, _, _ = parse_method_id(method_id)
        if not class_name:
            return []
        canonical = canonical_method_id(method_id)
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM xrefs WHERE project_id = ? AND REPLACE(callee, ' ', '') = ?",
                (project_id, canonical),
            ).fetchall()
        return [_row_to_reference(row) for row in rows]

    def list_resources(self, project_id: str, *, name: str | None = None) -> list[ResourceString]:
        """The resource strings indexed for a project.

        ``name`` selects one resource by its exact name. The answer to "where is
        ``app_name`` defined?" is several rows when the APK ships several
        languages, and every one of them is a different declaration.
        """
        query = "SELECT * FROM resources WHERE project_id = ?"
        params: list[Any] = [project_id]
        if name:
            query += " AND name = ?"
            params.append(name)
        query += " ORDER BY file, name, kind, quantity"
        with self.transaction() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_resource(row) for row in rows]

    def search(self, project_id: str, keyword: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Full-text search across indexed symbols.

        The term is wrapped as an FTS phrase with quotes doubled, so FTS operators in
        user input are matched literally rather than interpreted as query syntax.
        """
        phrase = '"' + keyword.replace('"', '""') + '"'
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT kind,
                       qualified_name,
                       snippet(search_index, 3, '', '', ' … ', 12) AS excerpt
                FROM search_index
                WHERE search_index MATCH ? AND project_id = ?
                LIMIT ?
                """,
                (phrase, project_id, limit),
            ).fetchall()
        return [
            {
                "kind": row["kind"],
                "name": _canonical_search_name(row["kind"], row["qualified_name"]),
                "excerpt": row["excerpt"],
            }
            for row in rows
        ]

    # -- evidence ----------------------------------------------------------

    def save_evidence(self, project_id: str, evidence: Iterable[Evidence]) -> int:
        """Replace a project's evidence. Callers re-analyse, so this is idempotent.

        The rows of the earlier run are removed first. The evidence ids are
        assigned in sequence, so a record left behind keeps an id that this
        run has already given to a different record — and a report that cites
        ``E-0007`` would send a reader to the wrong row. The table and the
        report have to hold the same records, or the ids in one do not mean
        what the ids in the other mean.

        The project's own evidence is cleared a second time by
        :meth:`save_symbols`, in the same transaction that clears the symbol
        tables: a query that ran between the two writes would otherwise see
        the new symbols beside the old evidence, which is worse than seeing
        neither.
        """
        items = list(evidence)
        with self.transaction() as connection:
            connection.execute("DELETE FROM evidence WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        project_id,
                        e.id,
                        e.kind.value,
                        e.level.value,
                        e.summary,
                        json.dumps(e.detail),
                        _dump_provenance(e),
                    )
                    for e in items
                ],
            )
        return len(items)

    def list_evidence(self, project_id: str) -> list[Evidence]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [_row_to_evidence(row) for row in rows]


# ---------------------------------------------------------------------------
# Row mapping
# ---------------------------------------------------------------------------


def _save_project(
    connection: sqlite3.Connection,
    project: Project,
    workspace: Path | None,
    manifest: ManifestInfo | None,
) -> None:
    """Write a project's own row, on a connection somebody else owns."""
    connection.execute(
        _PROJECT_UPSERT,
        (
            project.id,
            project.apk.sha256,
            str(project.apk.path),
            project.apk.size_bytes,
            project.created_at.isoformat(),
            project.status.value,
            json.dumps(project.tool_versions),
            json.dumps([e.model_dump(mode="json") for e in project.errors]),
            project.class_count,
            project.method_count,
            project.reference_count,
            project.evidence_count,
            project.resource_count,
            project.duration_seconds,
            manifest.model_dump_json() if manifest else None,
            str(workspace) if workspace else None,
        ),
    )


def _save_run(connection: sqlite3.Connection, run: AnalysisRun) -> None:
    """Write a run's own row, on a connection somebody else owns."""
    connection.execute(
        _RUN_UPSERT,
        (
            run.id,
            run.project_id,
            run.apk_sha256,
            run.status.value,
            run.completeness.value,
            json.dumps(run.tool_versions),
            json.dumps([e.model_dump(mode="json") for e in run.errors]),
            run.started_at.isoformat(),
            run.finished_at.isoformat() if run.finished_at else None,
            run.duration_seconds,
            str(run.workspace) if run.workspace else None,
        ),
    )


def _copy_staged_symbols(connection: sqlite3.Connection, project_id: str, staged: Path) -> None:
    """Replace a project's published rows with a staged run's rows.

    The staged database holds the same schema as this one — that is what
    makes the copy possible without a table of column names — so the rows
    come across in the order both schemas declare them.

    The destination's columns are the ones named in the insert, so a schema
    that has grown a column since the staged database was written still
    works: the new column takes its default rather than failing the copy.
    """
    source = sqlite3.connect(staged)
    try:
        for table in _PROJECT_TABLES:
            columns = [
                str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            rows = source.execute(
                f"SELECT * FROM {table} WHERE project_id = ?", (project_id,)
            ).fetchall()
            connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
            if not rows:
                continue
            placeholders = ", ".join("?" * len(columns))
            connection.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                [tuple(row) for row in rows],
            )
    finally:
        source.close()


def _dump_provenance(item: Any) -> str:
    return json.dumps([p.model_dump(mode="json") for p in item.provenance])


def _count_rows(connection: sqlite3.Connection, table: str, project_id: str) -> int:
    """How many rows a symbol table holds for one project.

    The table is the only authority on how many symbols were stored: the
    primary keys collapse duplicates, and a count taken from the list that was
    written is a count of something the database never held.
    """
    row = connection.execute(
        f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)
    ).fetchone()
    return int(row[0]) if row else 0


def _counts_by_class(connection: sqlite3.Connection, table: str, project_id: str) -> dict[str, int]:
    """How many rows of ``table`` each class owns.

    This is what a class row's ``method_count`` and ``field_count`` hold. A
    backend that read one dex file saw part of a class that was split across
    two, so its count was part of the class; the rows are the class.
    """
    rows = connection.execute(
        f"SELECT class_name, COUNT(*) FROM {table} WHERE project_id = ? GROUP BY class_name",
        (project_id,),
    ).fetchall()
    return {row["class_name"]: int(row[1]) for row in rows}


def _canonical_search_name(kind: str, name: str) -> str:
    """Canonicalise a search hit's name.

    The indexed name of a method is its id, so it has to be spelled the same way as
    the one the method table prints — otherwise a search result and the method it
    names would look like two different methods. A workspace indexed before
    descriptors were canonicalised holds the spaced spelling here.
    """
    if kind == "method":
        return canonical_method_id(name)
    return name


def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        apk=ApkMetadata(
            sha256=row["apk_sha256"],
            size_bytes=row["apk_size_bytes"],
            path=Path(row["apk_path"]),
        ),
        status=ProjectStatus(row["status"]),
        tool_versions=json.loads(row["tool_versions"]),
        errors=[ToolError.model_validate(e) for e in json.loads(row["errors"])],
        class_count=row["class_count"],
        method_count=row["method_count"],
        reference_count=row["reference_count"],
        evidence_count=row["evidence_count"],
        resource_count=row["resource_count"],
        duration_seconds=row["duration_seconds"],
    )


def _row_to_run(row: sqlite3.Row) -> AnalysisRun:
    return AnalysisRun(
        id=row["id"],
        project_id=row["project_id"],
        apk_sha256=row["apk_sha256"],
        status=RunStatus(row["status"]),
        completeness=RunCompleteness(row["completeness"]),
        tool_versions=json.loads(row["tool_versions"]),
        errors=[ToolError.model_validate(e) for e in json.loads(row["errors"])],
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        duration_seconds=row["duration_seconds"],
        workspace=Path(row["workspace"]) if row["workspace"] else None,
    )


def _row_to_class(row: sqlite3.Row) -> ClassRef:
    return ClassRef(
        name=row["name"],
        kind=ClassKind(row["kind"]),
        superclass=row["superclass"],
        interfaces=json.loads(row["interfaces"]),
        access_flags=json.loads(row["access_flags"]),
        method_count=row["method_count"],
        field_count=row["field_count"],
        provenance=json.loads(row["provenance"]),
    )


def _row_to_method(row: sqlite3.Row) -> MethodRef:
    return MethodRef(
        class_name=row["class_name"],
        name=row["name"],
        descriptor=row["descriptor"],
        access_flags=json.loads(row["access_flags"]),
        signature=row["signature"],
        decompiled=bool(row["decompiled"]),
        provenance=json.loads(row["provenance"]),
    )


def _row_to_reference(row: sqlite3.Row) -> MethodReference:
    return MethodReference(
        caller=row["caller"],
        callee=row["callee"],
        kind=row["kind"],
        provenance=json.loads(row["provenance"]),
    )


def _row_to_resource(row: sqlite3.Row) -> ResourceString:
    return ResourceString(
        name=row["name"],
        value=row["value"],
        kind=ResourceKind(row["kind"]),
        quantity=row["quantity"] or None,
        qualifier=row["qualifier"],
        position=row["position"],
        file=row["file"],
        provenance=json.loads(row["provenance"]),
    )


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence(
        id=row["id"],
        kind=EvidenceKind(row["kind"]),
        level=EvidenceLevel(row["level"]),
        summary=row["summary"],
        detail=json.loads(row["detail"]),
        provenance=json.loads(row["provenance"]),
    )


def _search_rows(
    project_id: str,
    classes: Iterable[ClassRef],
    methods: Iterable[MethodRef],
    fields: Iterable[FieldRef],
    strings: Iterable[StringConstant],
    resources: Iterable[ResourceString] = (),
) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for cls in classes:
        body = f"{cls.name} {cls.superclass or ''} {' '.join(cls.interfaces)} {' '.join(cls.access_flags)}"
        rows.append(("class", cls.name, project_id, body))
    for method in methods:
        body = (
            f"{method.class_name} {method.name} {method.descriptor} {' '.join(method.access_flags)}"
        )
        rows.append(("method", method.qualified_name, project_id, body))
    for field in fields:
        body = f"{field.class_name} {field.name} {field.descriptor} {' '.join(field.access_flags)}"
        rows.append(("field", field.qualified_name, project_id, body))
    # A string constant is one symbol, however many methods use it, so it is
    # indexed once. The use sites live in the strings table; the search index
    # answers "is this text in the APK", and it answers it once.
    indexed: set[str] = set()
    for constant in strings:
        if constant.value in indexed:
            continue
        indexed.add(constant.value)
        rows.append(("string", constant.value[:200], project_id, constant.value))
    # A resource string is a declaration site, not a use site: the same text in
    # two languages is two declarations, and both are indexed. The name goes in
    # with the value so that a search for either finds the row.
    for resource in resources:
        rows.append(
            ("resource", resource.qualified_name, project_id, f"{resource.name} {resource.value}")
        )
    return rows


__all__ = ["SCHEMA_VERSION", "Store", "SymbolCounts", "parse_method_id"]
