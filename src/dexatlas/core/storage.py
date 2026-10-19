"""SQLite-backed project storage and full-text symbol search.

SQLite FTS5 is the primary retrieval channel. Code search, exact symbol resolution and
cross-references answer most questions precisely; semantic retrieval is a Phase 2
supplement, never a prerequisite.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
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
    StringConstant,
    ToolError,
    canonical_descriptor,
    canonical_method_id,
)

SCHEMA_VERSION = 1

#: Tables cleared when a project is re-analysed. Content-addressed project ids mean a
#: re-analysis replaces rather than accumulates.
_SYMBOL_TABLES = ("classes", "methods", "fields", "xrefs", "strings", "search_index")

_SCHEMA = """
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
    manifest         TEXT,
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

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    kind UNINDEXED,
    qualified_name UNINDEXED,
    project_id UNINDEXED,
    body,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""

_PROJECT_UPSERT = """
INSERT INTO projects (
    id, apk_sha256, apk_path, apk_size_bytes, created_at, status,
    tool_versions, errors, class_count, method_count,
    reference_count, evidence_count, manifest, workspace
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    apk_path      = excluded.apk_path,
    status        = excluded.status,
    tool_versions = excluded.tool_versions,
    errors        = excluded.errors,
    class_count   = excluded.class_count,
    method_count  = excluded.method_count,
    reference_count = excluded.reference_count,
    evidence_count  = excluded.evidence_count,
    manifest      = excluded.manifest,
    workspace     = excluded.workspace
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


class Store:
    """Project and symbol persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @classmethod
    def open(cls, path: Path) -> Self:
        path.parent.mkdir(parents=True, exist_ok=True)
        store = cls(path)
        with store.transaction() as connection:
            connection.executescript(_SCHEMA)
            connection.execute("DELETE FROM schema_info")
            connection.execute("INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,))
        return store

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
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
        self, project: Project, workspace: Path, manifest: ManifestInfo | None
    ) -> None:
        with self.transaction() as connection:
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
                    manifest.model_dump_json() if manifest else None,
                    str(workspace),
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
            for table in _SYMBOL_TABLES:
                connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
        return cursor.rowcount > 0

    # -- symbols -----------------------------------------------------------

    def save_symbols(
        self,
        project_id: str,
        classes: Iterable[ClassRef],
        methods: Iterable[MethodRef],
        fields: Iterable[FieldRef],
        references: Iterable[MethodReference],
        strings: Iterable[StringConstant],
    ) -> None:
        """Replace a project's symbol tables. Callers re-analyse, so this is idempotent.

        Descriptors and method ids are stored in their canonical spelling. The models
        already normalise them, but the database is the durable contract: an id
        written here has to be the id the lookup below matches, whatever the caller
        handed in.
        """
        with self.transaction() as connection:
            for table in _SYMBOL_TABLES:
                connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))

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
                        c.method_count,
                        c.field_count,
                        _dump_provenance(c),
                    )
                    for c in classes
                ],
            )
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
                    for m in methods
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
                    for f in fields
                ],
            )
            connection.executemany(
                "INSERT INTO xrefs VALUES (?,?,?,?,?)",
                [
                    (
                        project_id,
                        canonical_method_id(r.caller),
                        canonical_method_id(r.callee),
                        r.kind,
                        _dump_provenance(r),
                    )
                    for r in references
                ],
            )
            connection.executemany(
                "INSERT INTO strings VALUES (?,?,?,?,?)",
                [
                    (project_id, s.value, s.class_name, s.method_name, _dump_provenance(s))
                    for s in strings
                ],
            )
            connection.executemany(
                "INSERT INTO search_index (kind, qualified_name, project_id, body) VALUES (?,?,?,?)",
                _search_rows(project_id, classes, methods, fields, strings),
            )

    def list_classes(self, project_id: str, *, prefix: str | None = None) -> list[ClassRef]:
        query = "SELECT * FROM classes WHERE project_id = ?"
        params: list[Any] = [project_id]
        if prefix:
            query += " AND name LIKE ? ESCAPE '\\'"
            params.append(prefix.replace("\\", "\\\\").replace("%", "\\%") + "%")
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
        items = list(evidence)
        with self.transaction() as connection:
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


def _dump_provenance(item: Any) -> str:
    return json.dumps([p.model_dump(mode="json") for p in item.provenance])


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
    for constant in strings:
        rows.append(("string", constant.value[:200], project_id, constant.value))
    return rows


__all__ = ["SCHEMA_VERSION", "Store", "parse_method_id"]
