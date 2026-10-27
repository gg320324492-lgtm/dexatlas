"""Project storage, symbol index and search."""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    FieldRef,
    MethodRef,
    MethodReference,
    Project,
    Provenance,
    StringConstant,
)
from dexatlas.core.storage import Store, _escape_like, parse_method_id


def _project(name: str = "demo.apk") -> Project:
    return Project.create(ApkMetadata(sha256="a" * 64, size_bytes=1024, path=Path(name)))


def _provenance(tool: str = "androguard") -> list[Provenance]:
    return [
        Provenance(
            tool=tool,
            tool_version="1.0",
            apk_sha256="a" * 64,
            locator=f"{tool}:com/example/Demo#run",
        )
    ]


def _symbol_set() -> tuple[
    list[ClassRef], list[MethodRef], list[FieldRef], list[MethodReference], list[StringConstant]
]:
    classes = [
        ClassRef(
            name="com.example.demo.NetworkClient",
            kind=ClassKind.CLASS,
            superclass="java.lang.Object",
            method_count=2,
            provenance=_provenance(),
        ),
        ClassRef(name="com.example.demo.Crypto", kind=ClassKind.CLASS, provenance=_provenance()),
    ]
    methods = [
        MethodRef(
            class_name="com.example.demo.NetworkClient",
            name="send",
            descriptor="(Ljava/lang/String;)V",
            provenance=_provenance(),
        ),
        MethodRef(
            class_name="com.example.demo.Crypto",
            name="encrypt",
            descriptor="([B)[B",
            provenance=_provenance(),
        ),
    ]
    fields = [
        FieldRef(
            class_name="com.example.demo.Crypto",
            name="KEY",
            descriptor="Ljava/lang/String;",
            constant_value="aes-key",
            provenance=_provenance(),
        )
    ]
    references = [
        MethodReference(
            caller="com.example.demo.NetworkClient.send(Ljava/lang/String;)V",
            callee="com.example.demo.Crypto.encrypt([B)[B",
            provenance=_provenance(),
        )
    ]
    strings = [
        StringConstant(value="https://api.example.com/v1", provenance=_provenance()),
    ]
    return classes, methods, fields, references, strings


# -- method id parsing ------------------------------------------------------


@pytest.mark.parametrize(
    ("method_id", "expected"),
    [
        (
            "com.example.demo.Crypto.encrypt([B)[B",
            ("com.example.demo.Crypto", "encrypt", "([B)[B"),
        ),
        (
            "com.example.Foo.bar(Ljava/lang/String;)V",
            ("com.example.Foo", "bar", "(Ljava/lang/String;)V"),
        ),
        ("com.example.Foo.baz()V", ("com.example.Foo", "baz", "()V")),
        ("<init>", ("", "", "")),
        ("noDescriptor", ("", "", "")),
        ("", ("", "", "")),
    ],
)
def test_parse_method_id(method_id: str, expected: tuple[str, str, str]) -> None:
    assert parse_method_id(method_id) == expected


# -- projects ---------------------------------------------------------------


def test_save_and_load_project(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path / "ws", manifest=None)

    loaded = store.get_project(project.id)

    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.apk.sha256 == project.apk.sha256
    assert loaded.apk.size_bytes == 1024


def test_project_ids_are_content_addressed() -> None:
    first = _project("a.apk")
    second = _project("b.apk")

    assert first.id == second.id


def test_unknown_project_is_none(store: Store) -> None:
    assert store.get_project("apk_nope") is None


def test_list_projects(store: Store, tmp_path: Path) -> None:
    store.save_project(_project(), tmp_path, manifest=None)

    assert len(store.list_projects()) == 1


def test_find_by_hash(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)

    found = store.find_project_by_hash("a" * 64)

    assert found is not None
    assert found.id == project.id


def test_delete_project_removes_symbols(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.delete_project(project.id) is True
    assert store.get_project(project.id) is None
    assert store.list_classes(project.id) == []


# -- symbols ----------------------------------------------------------------


#: The two-argument method from the demo app, spelled the way Androguard
#: renders it: a space after every argument separator. The canonical spelling
#: packs the arguments together.
SPACED_DESCRIPTOR = "(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
CANONICAL_DESCRIPTOR = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"

SPACED_CALLER = (
    "com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
)
CANONICAL_CALLER = (
    "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
)


def test_the_stored_field_descriptor_is_canonical(store: Store, tmp_path: Path) -> None:
    """The database is the durable contract, so it normalises on write.

    The field table is the one place a descriptor is stored on its own rather
    than as part of a method id, so it is the one place a spaced descriptor
    could survive into the database. A descriptor that reaches the table in
    two spellings makes a lookup that finds nothing look exactly like a
    lookup that had nothing to find.

    The model is built with ``model_construct``, which skips validation: this
    asserts the storage layer's own normalisation, not the model's.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    field = FieldRef.model_construct(
        class_name="com.example.demo.Crypto",
        name="KEY",
        descriptor=SPACED_DESCRIPTOR,
    )

    store.save_symbols(project.id, [], [], [field], [], [])

    with store.transaction() as connection:
        row = connection.execute(
            "SELECT descriptor FROM fields WHERE project_id = ?", (project.id,)
        ).fetchone()
    assert row is not None
    assert row["descriptor"] == CANONICAL_DESCRIPTOR


def test_the_stored_xref_caller_is_canonical(store: Store, tmp_path: Path) -> None:
    """The caller's id is normalised on write too, not only the callee's.

    A cross-reference has two ends and both of them are method ids. The
    callee was checked and the caller was not, so a spaced caller could reach
    the table: the edge would then name a method the method table spells
    differently, and a query for that method would find nothing.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    reference = MethodReference.model_construct(caller=SPACED_CALLER, callee=CANONICAL_CALLER)

    store.save_symbols(project.id, [], [], [], [reference], [])

    with store.transaction() as connection:
        row = connection.execute(
            "SELECT caller, callee FROM call_sites WHERE project_id = ?", (project.id,)
        ).fetchone()
    assert row is not None
    assert row["caller"] == CANONICAL_CALLER
    assert row["callee"] == CANONICAL_CALLER


def test_save_and_read_classes(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields, references, strings = _symbol_set()
    store.save_symbols(project.id, classes, methods, fields, references, strings)

    loaded = store.list_classes(project.id)

    assert [c.name for c in loaded] == ["com.example.demo.Crypto", "com.example.demo.NetworkClient"]
    assert loaded[0].provenance[0].tool == "androguard"


def test_filter_classes_by_prefix(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields, references, strings = _symbol_set()
    store.save_symbols(project.id, classes, methods, fields, references, strings)

    filtered = store.list_classes(project.id, prefix="com.example.demo.Network")

    assert [c.name for c in filtered] == ["com.example.demo.NetworkClient"]


def test_prefix_filter_escapes_wildcards(store: Store, tmp_path: Path) -> None:
    """A ``%`` in the prefix must be a literal, not a match-everything wildcard."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.list_classes(project.id, prefix="%") == []


# -- prefix filtering: every LIKE wildcard must be a literal ----------------

#: Names that differ only in the character a LIKE wildcard would consume. SQLite's
#: LIKE has two wildcards: ``%`` matches any run of characters and ``_`` matches any
#: single one. ``com.example.com_ex`` and ``com.example.comXex`` are different
#: classes, so a prefix filter on the first must never return the second.
_LIKE_TRICKY_NAMES = [
    "com.example.com_ex.Alpha",
    "com.example.comXex.Alpha",
    "com.example.per%cent.Beta",
    "com.example.perXcent.Beta",
    "com.example.back\\slash.Gamma",
    "com.example.backXslash.Gamma",
    "com.example.plain.Delta",
]


def _seed_like_tricky_classes(store: Store, tmp_path: Path) -> str:
    """Load a project whose class names probe every LIKE wildcard."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes = [
        ClassRef(name=name, kind=ClassKind.CLASS, provenance=_provenance())
        for name in _LIKE_TRICKY_NAMES
    ]
    store.save_symbols(project.id, classes, [], [], [], [])
    return project.id


def test_prefix_filter_treats_underscore_as_a_literal(store: Store, tmp_path: Path) -> None:
    """``_`` matches any single character in a LIKE pattern, so it must be escaped.

    ``com.example.comXex.Alpha`` is a different class from ``com.example.com_ex.Alpha``
    and must not be returned by a filter on the latter.
    """
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.com_ex")]

    assert names == ["com.example.com_ex.Alpha"]


def test_prefix_filter_treats_underscore_at_the_end_as_a_literal(
    store: Store, tmp_path: Path
) -> None:
    """A trailing underscore is the case a wildcard swallows most convincingly."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.com_")]

    assert names == ["com.example.com_ex.Alpha"]


def test_prefix_filter_treats_percent_as_a_literal(store: Store, tmp_path: Path) -> None:
    """A ``%`` in a prefix is a literal percent sign, not a wildcard."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.per%cent")]

    assert names == ["com.example.per%cent.Beta"]


def test_prefix_filter_treats_backslash_as_a_literal(store: Store, tmp_path: Path) -> None:
    """A backslash is the LIKE escape character and must be escaped first."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.back\\slash")]

    assert names == ["com.example.back\\slash.Gamma"]


def test_prefix_filter_of_only_wildcards_matches_nothing(store: Store, tmp_path: Path) -> None:
    """A prefix made entirely of wildcards must not match every class."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    for prefix in ("%", "_", "%_", "_%_", "%\\%"):
        assert store.list_classes(project_id, prefix=prefix) == [], prefix


def test_prefix_filter_still_matches_longer_names(store: Store, tmp_path: Path) -> None:
    """The trailing ``%`` belongs to the filter and must keep working."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.")]

    assert names == sorted(_LIKE_TRICKY_NAMES)


def test_prefix_filter_matches_the_exact_name_too(store: Store, tmp_path: Path) -> None:
    """A prefix that is a whole class name still matches that class."""
    project_id = _seed_like_tricky_classes(store, tmp_path)

    names = [c.name for c in store.list_classes(project_id, prefix="com.example.plain.Delta")]

    assert names == ["com.example.plain.Delta"]


def test_escape_like_escapes_every_like_wildcard() -> None:
    """SQLite's LIKE has two wildcards; both have to be neutralised."""
    assert _escape_like("a%b") == "a\\%b"
    assert _escape_like("a_b") == "a\\_b"
    assert _escape_like("a\\b") == "a\\\\b"


def test_escape_like_escapes_the_backslash_before_the_wildcards() -> None:
    """Escaping the wildcards first would double-escape the escape character."""
    assert _escape_like("\\%") == "\\\\\\%"


def test_list_methods_class_filter_is_an_exact_match(store: Store, tmp_path: Path) -> None:
    """``list_methods`` filters with ``=``, not ``LIKE``, so no wildcard applies.

    This pins the audit result that ``list_classes`` holds the only LIKE in the
    storage layer.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.list_methods(project.id, "com.example.demo") == []
    crypto_methods = store.list_methods(project.id, "com.example.demo.Crypto")
    assert [m.qualified_name for m in crypto_methods] == ["com.example.demo.Crypto.encrypt([B)[B"]


def test_search_has_no_like_wildcards(store: Store, tmp_path: Path) -> None:
    """``search`` goes through FTS5, which knows no ``%`` or ``_`` wildcards."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.search(project.id, "%") == []
    assert store.search(project.id, "_") == []


def test_resaving_replaces_rather_than_accumulates(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())
    store.save_symbols(project.id, *_symbol_set())

    assert len(store.list_classes(project.id)) == 2


def test_list_methods_by_class(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    methods = store.list_methods(project.id, "com.example.demo.Crypto")

    assert [m.qualified_name for m in methods] == ["com.example.demo.Crypto.encrypt([B)[B"]


def test_method_references_resolve_the_callee(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    refs = store.get_method_references(project.id, "com.example.demo.Crypto.encrypt([B)[B")

    assert len(refs) == 1
    assert refs[0].caller.startswith("com.example.demo.NetworkClient.send")


def test_method_references_for_unknown_method_is_empty(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.get_method_references(project.id, "com.nope.Missing.m()V") == []
    assert store.get_method_references(project.id, "malformed") == []


# -- the counts a report may state ------------------------------------------


def _row_count(store: Store, table: str, project_id: str) -> int:
    with store.transaction() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)
        ).fetchone()
    return int(row[0])


def test_save_symbols_reports_the_rows_it_stored(store: Store, tmp_path: Path) -> None:
    """The number a report states must be the number a query returns.

    The counts are measured from the tables, because the tables collapse
    duplicate keys: the number of symbols that went in is not the number of
    rows that are there afterwards.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields, references, strings = _symbol_set()

    counts = store.save_symbols(project.id, classes, methods, fields, references, strings)

    assert counts.classes == len(store.list_classes(project.id))
    assert counts.methods == len(store.list_methods(project.id))
    assert counts.fields == _row_count(store, "fields", project.id)
    assert counts.references == _row_count(store, "call_sites", project.id)
    # The edges are what the call sites say about each other, and they are a
    # different number: two calls from one method to one target are two sites
    # and one edge.
    assert counts.call_edges == len({(r.caller, r.callee, r.kind) for r in references})


def test_a_symbol_defined_twice_is_stored_once(store: Store, tmp_path: Path) -> None:
    """Two dex files that define the same method give one row, not two.

    The method table keys on the method id, so the second definition replaces
    the first. The count has to say one: the report used to state the number
    of symbols that went in, which was a number the table could not produce.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields, references, strings = _symbol_set()
    # The same method, indexed twice — as a class defined in two dex files is.
    methods = [*methods, methods[0].model_copy(deep=True)]

    counts = store.save_symbols(project.id, classes, methods, fields, references, strings)

    assert len(methods) == 3
    assert counts.methods == 2
    assert len(store.list_methods(project.id)) == 2


# -- the counts a class row holds -------------------------------------------


def _split_class_symbols() -> tuple[list[ClassRef], list[MethodRef], list[FieldRef]]:
    """A class split across two dex files, as a multi-dex APK splits one.

    Each dex file defines part of the class, so each backend view of it says
    one method and one field — while the class has two of each. The views are
    what the backends produce; the class is what the index has to report.
    """
    classes = [
        ClassRef(
            name="com.example.demo.Shared",
            method_count=1,
            field_count=1,
            provenance=_provenance(),
        ),
        ClassRef(
            name="com.example.demo.Shared",
            method_count=1,
            field_count=1,
            provenance=_provenance(),
        ),
    ]
    methods = [
        MethodRef(
            class_name="com.example.demo.Shared",
            name="first",
            descriptor="()V",
            provenance=_provenance(),
        ),
        MethodRef(
            class_name="com.example.demo.Shared",
            name="second",
            descriptor="()V",
            provenance=_provenance(),
        ),
    ]
    fields = [
        FieldRef(
            class_name="com.example.demo.Shared",
            name="A",
            descriptor="I",
            provenance=_provenance(),
        ),
        FieldRef(
            class_name="com.example.demo.Shared",
            name="B",
            descriptor="I",
            provenance=_provenance(),
        ),
    ]
    return classes, methods, fields


def test_a_class_split_across_two_dexes_counts_the_rows_it_owns(
    store: Store, tmp_path: Path
) -> None:
    """The class row must hold the class's real method count.

    It used to hold the larger of the counts the backends reported, and a
    backend that reads one dex file sees only that dex file's share of a
    class. A class split across two dex files was counted once and stored
    twice: the number in the row and the number a query returns disagreed.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields = _split_class_symbols()

    store.save_symbols(project.id, classes, methods, fields, [], [])

    stored = store.get_class(project.id, "com.example.demo.Shared")
    assert stored is not None
    assert stored.method_count == 2
    assert stored.method_count == len(store.list_methods(project.id, "com.example.demo.Shared"))


def test_a_class_split_across_two_dexes_counts_the_fields_it_owns(
    store: Store, tmp_path: Path
) -> None:
    """The field count is the same two numbers, and has to be the real one."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields = _split_class_symbols()

    store.save_symbols(project.id, classes, methods, fields, [], [])

    stored = store.get_class(project.id, "com.example.demo.Shared")
    assert stored is not None
    assert stored.field_count == 2


def test_the_class_row_counts_the_rows_and_not_the_view(store: Store, tmp_path: Path) -> None:
    """Whatever a backend says about a class, the row holds the rows.

    A view is what one backend saw. The row is the index's own count, and it
    has to be the number a query against the method table returns — the
    property the report's numbers rest on.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields = _split_class_symbols()
    # A backend that miscounts. The index does not have to believe it.
    classes = [cls.model_copy(update={"method_count": 99, "field_count": 99}) for cls in classes]

    store.save_symbols(project.id, classes, methods, fields, [], [])

    stored = store.get_class(project.id, "com.example.demo.Shared")
    assert stored is not None
    assert stored.method_count == 2
    assert stored.field_count == 2


def test_a_class_with_no_methods_counts_zero(store: Store, tmp_path: Path) -> None:
    """A class nothing was indexed for has no methods, and says so."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes = [ClassRef(name="com.example.demo.Empty", method_count=3, provenance=_provenance())]

    store.save_symbols(project.id, classes, [], [], [], [])

    stored = store.get_class(project.id, "com.example.demo.Empty")
    assert stored is not None
    assert stored.method_count == 0
    assert stored.field_count == 0


def test_a_generator_of_symbols_still_fills_the_search_index(store: Store, tmp_path: Path) -> None:
    """The search index reads the same symbols the tables do.

    They used to be read from the caller's iterables twice, so a caller that
    passed a generator filled the tables and left the search index empty.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    classes, methods, fields, references, strings = _symbol_set()

    store.save_symbols(
        project.id,
        (c for c in classes),
        (m for m in methods),
        (f for f in fields),
        (r for r in references),
        (s for s in strings),
    )

    assert store.search(project.id, "NetworkClient")


# -- search -----------------------------------------------------------------


def test_search_finds_classes_and_their_methods(store: Store, tmp_path: Path) -> None:
    """A class-name term legitimately matches both the class and its methods."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    results = store.search(project.id, "NetworkClient")

    names = {r["name"] for r in results}
    assert "com.example.demo.NetworkClient" in names
    assert "com.example.demo.NetworkClient.send(Ljava/lang/String;)V" in names
    assert {r["kind"] for r in results} == {"class", "method"}


def test_search_finds_string_constants(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    results = store.search(project.id, "api.example.com")

    assert results
    assert results[0]["kind"] == "string"


def test_search_is_scoped_to_one_project(store: Store, tmp_path: Path) -> None:
    first = _project()
    second = Project.create(ApkMetadata(sha256="b" * 64, size_bytes=1, path=Path("other.apk")))
    store.save_project(first, tmp_path, manifest=None)
    store.save_project(second, tmp_path, manifest=None)
    store.save_symbols(first.id, *_symbol_set())

    assert store.search(second.id, "NetworkClient") == []


def test_search_treats_fts_operators_as_literal_text(store: Store, tmp_path: Path) -> None:
    """User input must never be interpreted as FTS5 query syntax."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    for hostile in ('"', "NEAR(", "a OR", "*", "^start", "col:val"):
        results = store.search(project.id, hostile)
        assert isinstance(results, list)


def test_search_with_no_match_is_empty(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    store.save_symbols(project.id, *_symbol_set())

    assert store.search(project.id, "zzzznotpresent") == []


# -- evidence ---------------------------------------------------------------


def test_evidence_roundtrip_preserves_provenance(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    evidence = Evidence(
        id="E-0001",
        kind=EvidenceKind.CROSS_REFERENCE,
        level=EvidenceLevel.VERIFIED,
        summary="send calls encrypt",
        provenance=_provenance(),
    )

    assert store.save_evidence(project.id, [evidence]) == 1

    loaded = store.list_evidence(project.id)
    assert len(loaded) == 1
    assert loaded[0].id == "E-0001"
    assert loaded[0].level == EvidenceLevel.VERIFIED
    assert loaded[0].provenance[0].tool == "androguard"
    assert loaded[0].provenance[0].locator.endswith("#run")


def test_saving_evidence_again_replaces_the_earlier_records(store: Store, tmp_path: Path) -> None:
    """A re-analysis replaces the evidence of the earlier run rather than adding to it.

    The ids are assigned in sequence, so a record left behind by an earlier run
    keeps an id that the new run has already given to a different record. A
    report that cites ``E-0007`` would then send a reader to the wrong row —
    and the table would hold records the report does not mention, which is the
    opposite of what an evidence table is for.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)

    first = [
        Evidence(
            id=f"E-{index:04d}",
            kind=EvidenceKind.OBSERVATION,
            level=EvidenceLevel.VERIFIED,
            summary=f"observation {index}",
            provenance=_provenance(),
        )
        for index in range(1, 4)
    ]
    store.save_evidence(project.id, first)

    second = [
        Evidence(
            id="E-0001",
            kind=EvidenceKind.OBSERVATION,
            level=EvidenceLevel.VERIFIED,
            summary="the only observation of this run",
            provenance=_provenance(),
        )
    ]
    store.save_evidence(project.id, second)

    loaded = store.list_evidence(project.id)
    assert len(loaded) == 1, "the records of the earlier run were kept"
    assert loaded[0].summary == "the only observation of this run"
