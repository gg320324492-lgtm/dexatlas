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
from dexatlas.core.storage import Store, parse_method_id


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
