"""The docstrings have to say what the code does.

A docstring that names a thing the code does not have is worse than no docstring:
a reader takes it as a promise, looks for the thing that is missing, and finds a
sentence instead of an artefact. The four checked here were each found to be
describing something the code did not do.

The checks are made against the code rather than against a copy of it. The
backends that produce class definitions are found by reading the adapters, and
the backend that parses in-process is found by reading whether it ever calls the
base class's subprocess runner. A check that repeated the truth would only be as
good as the day it was written.

The behaviour behind the claims is checked here too — the merge itself is
exercised in ``test_evidence.py``, and the ingestion budget and the schema
migration are exercised below.
"""

from __future__ import annotations

import ast
import inspect
import re
import sqlite3
import textwrap
import zipfile
from pathlib import Path

import pytest

from dexatlas.core import ingest, storage
from dexatlas.core.ingest import ApkValidationError, validate_apk
from dexatlas.core.pipeline import Analyzer, _merge_classes
from dexatlas.core.storage import _migrate
from dexatlas.tools import base
from dexatlas.tools.androguard.adapter import AndroguardBackend
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import Backend
from dexatlas.tools.jadx.adapter import JadxBackend

REPO_ROOT = Path(__file__).parent.parent

#: The backends, in the order the pipeline runs them.
BACKENDS: tuple[type[Backend], ...] = (JadxBackend, ApktoolBackend, AndroguardBackend)

#: A sentence ends at a full stop, a question mark or an exclamation mark.
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    """The sentences of a text."""
    return [piece.strip() for piece in SENTENCE.split(text) if piece.strip()]


def _builds_class_refs(backend: type[Backend]) -> bool:
    """Whether an adapter constructs a ``ClassRef``."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(backend)))
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ClassRef"
        for node in ast.walk(tree)
    )


def _class_producers() -> set[str]:
    """The backends whose adapter builds a class definition."""
    return {backend.name for backend in BACKENDS if _builds_class_refs(backend)}


def _calls_the_subprocess_runner(backend: type[Backend]) -> bool:
    """Whether an adapter runs a tool through the base class's subprocess runner."""
    return "self.run(" in inspect.getsource(backend)


# -- the class index --------------------------------------------------------


def test_only_androguard_and_jadx_build_class_definitions() -> None:
    """The class index has two sources, and Apktool is not one of them.

    Apktool reads the manifest, the resource table and the disassembled
    bytecode. It builds no class definitions at all, and the merge docstring
    used to say that it knew a class the way Androguard did.
    """
    assert _class_producers() == {"androguard", "jadx"}


def test_the_merge_docstring_names_every_backend_that_builds_classes() -> None:
    """The docstring is a map of where the class rows come from.

    A reader who follows it to a backend that builds none finds nothing, and
    concludes the index is empty there.
    """
    doc = (_merge_classes.__doc__ or "").lower()

    missing = sorted(name for name in _class_producers() if name not in doc)
    assert not missing, f"the merge docstring does not name {missing}"


def test_the_merge_docstring_does_not_credit_a_backend_that_builds_no_classes() -> None:
    """A backend that builds no classes may not be credited with producing them.

    The sentence has to say that the backend contributes none, in the same
    breath as it names it — otherwise a reader stops at the name.
    """
    doc = _merge_classes.__doc__ or ""
    producers = _class_producers()

    problems: list[str] = []
    for sentence in _sentences(doc):
        lowered = sentence.lower()
        for backend in BACKENDS:
            if backend.name in producers or backend.name not in lowered:
                continue
            if not any(marker in lowered for marker in ("no class", "not", "never")):
                problems.append(f"{backend.name}: {sentence}")

    assert not problems, (
        "the merge docstring credits a backend that builds no classes:\n" + "\n".join(problems)
    )


def test_the_apktool_step_cannot_contribute_a_class() -> None:
    """The pipeline's Apktool step returns no classes, and cannot.

    It used to return a list of classes that was always empty, which is what
    made the docstring's claim look true: the shape of the code said Apktool
    had classes to give.
    """
    annotation = str(inspect.signature(Analyzer._run_apktool).return_annotation)

    assert "ClassRef" not in annotation


# -- the backend interface --------------------------------------------------


def test_one_backend_parses_in_process_and_the_engines_do_not() -> None:
    """Androguard is a library, so there is nothing to shell out to.

    The base class's runner is what puts the engines in a process of their
    own; a backend that never calls it parses the input where it stands.
    """
    in_process = {backend.name for backend in BACKENDS if not _calls_the_subprocess_runner(backend)}

    assert in_process == {"androguard"}


def test_the_backend_interface_names_the_backend_that_parses_in_process() -> None:
    """The base class has to name the exception to its own rule.

    The module docstring said that backends are subprocess wrappers and never
    links, and the Androguard adapter said the opposite two files away. The
    adapter was right.
    """
    doc = (base.__doc__ or "").lower()
    in_process = {backend.name for backend in BACKENDS if not _calls_the_subprocess_runner(backend)}

    missing = sorted(name for name in in_process if name not in doc)
    assert not missing, f"the backend interface does not name {missing} as the in-process one"
    assert "in-process" in doc


def test_the_backend_interface_does_not_say_every_backend_is_a_subprocess() -> None:
    """The two phrases that made the claim false are gone.

    The claim was not wrong in every particular — the engines really are
    subprocesses — but it was stated as a universal, and one backend is not
    one.
    """
    doc = (base.__doc__ or "").lower()

    assert "subprocess wrappers" not in doc
    assert "never links" not in doc


def test_the_backend_interface_says_why_the_in_process_exception_is_safe() -> None:
    """The exception is only safe because a failure inside it is recorded.

    A library that raised inside our process would end the run. The adapter
    wraps every step, so what raises becomes a ``ToolError`` and the run
    carries on.
    """
    doc = (base.__doc__ or "").lower()

    assert "toolerror" in doc
    assert "wrapped" in doc


# -- the schema migration ---------------------------------------------------

#: The resource table as an earlier build wrote it: no position, and a key that
#: lets one item of a ``<string-array>`` overwrite the next.
OLD_RESOURCES_TABLE = """
CREATE TABLE resources (
    project_id TEXT NOT NULL,
    name       TEXT NOT NULL,
    value      TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'string',
    quantity   TEXT NOT NULL DEFAULT '',
    qualifier  TEXT,
    file       TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, file, name, kind, quantity)
);
"""

#: The projects table as an earlier build wrote it: no resource count.
OLD_PROJECTS_TABLE = """
CREATE TABLE projects (
    id         TEXT PRIMARY KEY,
    apk_sha256 TEXT NOT NULL
);
"""


def test_the_migration_docstring_accounts_for_the_table_it_drops() -> None:
    """The docstring has to describe what the function does, not a part of it.

    It said "Additive only" and then dropped a table sixteen lines later. A
    column is added in place; a table whose key changed cannot be, and the
    docstring has to say which is which.
    """
    source = inspect.getsource(_migrate)
    doc = (_migrate.__doc__ or "").lower()

    if "DROP TABLE" in source:
        assert "additive only" not in doc
        assert "dropped" in doc or "rebuilt" in doc
    assert "column" in doc


def test_the_migration_adds_a_column_without_losing_the_rows() -> None:
    """The column is added in place, and the rows keep their values."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(OLD_PROJECTS_TABLE)
    connection.execute("INSERT INTO projects (id, apk_sha256) VALUES ('p', 'a')")
    connection.commit()

    _migrate(connection)

    columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
    assert "resource_count" in columns
    rows = connection.execute("SELECT id, resource_count FROM projects").fetchall()
    assert [(row["id"], row["resource_count"]) for row in rows] == [("p", 0)]
    connection.close()


def test_the_migration_rebuilds_the_resource_table_and_its_rows_are_lost() -> None:
    """The old key let one item of a string array overwrite the next.

    SQLite cannot change a primary key in place, so the table is dropped and
    created empty. The rows do not survive, and the table is a cache of an
    analysis rather than a source of truth: the next analysis fills it again.
    """
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(OLD_PROJECTS_TABLE)
    connection.execute(OLD_RESOURCES_TABLE)
    connection.execute(
        "INSERT INTO resources (project_id, name, value, file) VALUES ('p', 'a', '1', 'f')"
    )
    connection.commit()

    _migrate(connection)

    columns = {row["name"] for row in connection.execute("PRAGMA table_info(resources)")}
    assert "position" in columns
    count = connection.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    assert count == 0
    connection.close()


def test_the_migration_leaves_a_current_workspace_alone() -> None:
    """A workspace that already has the current schema keeps its rows."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(storage._SCHEMA)
    connection.execute(
        "INSERT INTO resources (project_id, name, value, file) VALUES ('p', 'a', '1', 'f')"
    )
    connection.commit()

    _migrate(connection)

    count = connection.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    assert count == 1
    connection.close()


# -- the ingestion budget ---------------------------------------------------


def test_the_ingestion_docstring_accounts_for_the_bytes_it_reads() -> None:
    """The module says the archive is inspected without decompressing it.

    It is — for the sizes, which come out of the central directory. The
    checksums are verified by reading the entries, and that read is bounded by
    a budget the docstring has to name. The phrase that said the opposite has
    to go with it: the archive *is* decompressed, up to the budget.
    """
    source = inspect.getsource(ingest)
    doc = ingest.__doc__ or ""

    if "entry.read(" in source:
        assert "MAX_VERIFIED_BYTES" in doc
        assert "checksum" in doc.lower()
    assert "rather than by decompressing it" not in doc


def _write_a_corrupt_apk(path: Path) -> Path:
    """Write an APK whose last entry does not match its checksum.

    The corruption is in the stored bytes, so the archive still lists every
    entry and still passes the checks that read the central directory.
    """
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("AndroidManifest.xml", b"<manifest/>")
        archive.writestr("classes.dex", b"dex\n035\x00")
        archive.writestr("resources.arsc", b"\x02\x00\x0c\x00")
        archive.writestr("zzz-last.bin", b"CORRUPT-ME-PLEASE")

    data = bytearray(path.read_bytes())
    index = data.find(b"CORRUPT-ME-PLEASE")
    assert index != -1, "the fixture did not write the entry it corrupts"
    data[index] = ord("X")
    path.write_bytes(bytes(data))
    return path


def test_a_corrupt_entry_is_reported_while_the_budget_lasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Within the budget the entries are read, and a bad one is found."""
    monkeypatch.setattr(ingest, "MAX_VERIFIED_BYTES", 1024 * 1024)
    apk = _write_a_corrupt_apk(tmp_path / "corrupt.apk")

    with pytest.raises(ApkValidationError, match="corrupt entry"):
        validate_apk(apk)


def test_a_corrupt_entry_past_the_budget_is_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Past the budget the archive is accepted on the strength of its structure.

    The budget is a promise about how much is read, and a promise has to be
    kept: the entries past it are never decompressed, so a corruption in one
    of them is not noticed.
    """
    monkeypatch.setattr(ingest, "MAX_VERIFIED_BYTES", 1)
    apk = _write_a_corrupt_apk(tmp_path / "corrupt.apk")

    validate_apk(apk)


# -- the README's examples --------------------------------------------------


def _readme() -> str:
    """The README, as a reader gets it."""
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _readme_method_ids() -> list[str]:
    """The method ids the README's xrefs examples quote."""
    return re.findall(r"dexatlas xrefs\s+\S+\s+\"([^\"]+)\"", _readme())


def _demo_method_ids() -> set[str]:
    """The method ids the bundled demo application's smali defines.

    The smali is the source the demo APK was built from, so an id read out of
    it is an id the index holds.
    """
    root = REPO_ROOT / "examples" / "demo-app" / "smali"
    ids: set[str] = set()
    for path in root.rglob("*.smali"):
        class_name = ".".join(path.relative_to(root).with_suffix("").parts)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith(".method"):
                continue
            declaration = line.split()[-1]
            name = declaration.split("(")[0]
            ids.add(f"{class_name}.{name}{declaration[len(name) :]}")
    return ids


def test_the_readme_quotes_a_method_id_the_demo_app_defines() -> None:
    """The xrefs example has to name a method that exists.

    The example named a class that is not in the repository, so a reader who
    copied it got nothing back — and a method id that finds nothing looks
    exactly like a method that has no callers.
    """
    ids = _readme_method_ids()
    assert ids, "the README has no xrefs example to check"

    known = _demo_method_ids()
    unknown = [method_id for method_id in ids if method_id not in known]
    assert not unknown, f"the README quotes method ids the demo app does not define: {unknown}"


def test_the_readme_quotes_a_method_id_with_its_return_type() -> None:
    """An id without a return type is not the id the index holds.

    The descriptor the index stores carries the return type as well as the
    argument types, so an id that stops at the closing parenthesis names no
    method at all.
    """
    for method_id in _readme_method_ids():
        assert ")" in method_id, f"{method_id} has no argument list"
        assert method_id.split(")", 1)[1], f"{method_id} has no return type"
