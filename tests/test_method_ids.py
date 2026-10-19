"""Method ids must have exactly one spelling across every table.

DexAtlas stores a method's identity in two places: the ``methods`` table, as its
descriptor, and the ``xrefs`` table, as the caller and the callee. When those two
spell a method differently, an id copied out of one table can never be looked up in
the other — and the failure is silent, because an index that finds nothing looks
exactly like an index that had nothing to find.

These tests pin the one spelling DexAtlas uses: the canonical JVM descriptor, with
its argument types packed together and no separator whitespace. That is the form the
DEX format itself uses, so it is the form an external tool expects too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.models import (
    ApkMetadata,
    FieldRef,
    MethodRef,
    MethodReference,
    Project,
    canonical_descriptor,
    canonical_method_id,
)
from dexatlas.core.storage import Store

#: The two-argument method from the demo app. This is where the two spellings
#: differ: a space after the first argument separator.
SPACED_DESCRIPTOR = "(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
CANONICAL_DESCRIPTOR = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"

SPACED_ID = f"com.example.demo.Crypto.sign{SPACED_DESCRIPTOR}"
CANONICAL_ID = f"com.example.demo.Crypto.sign{CANONICAL_DESCRIPTOR}"

CALLER = "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"


def _project() -> Project:
    return Project.create(ApkMetadata(sha256="a" * 64, size_bytes=1024, path=Path("demo.apk")))


# -- the canonical form -----------------------------------------------------


@pytest.mark.parametrize(
    ("descriptor", "expected"),
    [
        (SPACED_DESCRIPTOR, CANONICAL_DESCRIPTOR),
        (CANONICAL_DESCRIPTOR, CANONICAL_DESCRIPTOR),
        ("(Ljava/lang/String;)V", "(Ljava/lang/String;)V"),
        ("()V", "()V"),
        ("([B)[B", "([B)[B"),
        ("(I Ljava/lang/String;)V", "(ILjava/lang/String;)V"),
        # A field descriptor has no argument list at all.
        ("Ljava/lang/String;", "Ljava/lang/String;"),
        # Nothing to canonicalise.
        ("", ""),
        ("not a descriptor", "not a descriptor"),
    ],
)
def test_canonical_descriptor(descriptor: str, expected: str) -> None:
    assert canonical_descriptor(descriptor) == expected


def test_canonical_descriptor_is_idempotent() -> None:
    once = canonical_descriptor(SPACED_DESCRIPTOR)
    assert canonical_descriptor(once) == once


@pytest.mark.parametrize(
    ("method_id", "expected"),
    [
        (SPACED_ID, CANONICAL_ID),
        (CANONICAL_ID, CANONICAL_ID),
        (
            "com.example.demo.Crypto.sign(Ljava/lang/String;)V",
            "com.example.demo.Crypto.sign(Ljava/lang/String;)V",
        ),
        # A constructor and a call without arguments.
        ("com.example.demo.MainActivity.<init>()V", "com.example.demo.MainActivity.<init>()V"),
        # Not a method id at all: left alone rather than mangled.
        ("com.example.demo.Crypto", "com.example.demo.Crypto"),
        ("", ""),
    ],
)
def test_canonical_method_id(method_id: str, expected: str) -> None:
    assert canonical_method_id(method_id) == expected


# -- the models -------------------------------------------------------------


def test_a_method_ref_canonicalises_its_descriptor() -> None:
    method = MethodRef(
        class_name="com.example.demo.Crypto",
        name="sign",
        descriptor=SPACED_DESCRIPTOR,
    )

    assert method.descriptor == CANONICAL_DESCRIPTOR
    assert method.qualified_name == CANONICAL_ID
    assert " " not in method.qualified_name


def test_a_field_ref_canonicalises_its_descriptor() -> None:
    field = FieldRef(
        class_name="com.example.demo.Crypto",
        name="KEY",
        descriptor="Ljava/lang/String;",
    )

    assert field.descriptor == "Ljava/lang/String;"


def test_a_method_reference_canonicalises_both_of_its_ends() -> None:
    reference = MethodReference(caller=CALLER, callee=SPACED_ID)

    assert reference.callee == CANONICAL_ID
    assert reference.caller == CALLER


# -- the storage layer ------------------------------------------------------


def test_the_stored_descriptor_is_canonical(store: Store, tmp_path: Path) -> None:
    """The database is the durable contract, so it normalises on write.

    The model is built with ``model_construct``, which skips validation: this
    asserts the storage layer's own normalisation, not the model's.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    method = MethodRef.model_construct(
        class_name="com.example.demo.Crypto",
        name="sign",
        descriptor=SPACED_DESCRIPTOR,
    )

    store.save_symbols(project.id, [], [method], [], [], [])

    with store.transaction() as connection:
        row = connection.execute(
            "SELECT descriptor FROM methods WHERE project_id = ?", (project.id,)
        ).fetchone()
    assert row is not None
    assert row["descriptor"] == CANONICAL_DESCRIPTOR


def test_the_stored_xref_ids_are_canonical(store: Store, tmp_path: Path) -> None:
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    reference = MethodReference.model_construct(caller=CALLER, callee=SPACED_ID)

    store.save_symbols(project.id, [], [], [], [reference], [])

    with store.transaction() as connection:
        row = connection.execute(
            "SELECT caller, callee FROM xrefs WHERE project_id = ?", (project.id,)
        ).fetchone()
    assert row is not None
    assert row["callee"] == CANONICAL_ID
    assert row["caller"] == CALLER


@pytest.mark.parametrize("stored_callee", [CANONICAL_ID, SPACED_ID])
def test_a_workspace_indexed_before_canonicalisation_still_resolves(
    store: Store, tmp_path: Path, stored_callee: str
) -> None:
    """A workspace written by an older DexAtlas must keep working.

    Before descriptors were canonicalised, the method table stored the spaced
    spelling while the cross-reference table stored the compact one, so the two
    never matched. The oldest version stored the spaced spelling on both sides.
    Those workspaces are still on disk, so a lookup has to accept the id as the
    user has it and the id as it is stored.
    """
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO methods VALUES (?,?,?,?,?,?,?,?)",
            (
                project.id,
                "com.example.demo.Crypto",
                "sign",
                SPACED_DESCRIPTOR,
                "[]",
                None,
                0,
                "[]",
            ),
        )
        connection.execute(
            "INSERT INTO xrefs VALUES (?,?,?,?,?)",
            (project.id, CALLER, stored_callee, "invoke", "[]"),
        )

    # The id as the old `dexatlas methods` printed it.
    assert store.get_method_references(project.id, SPACED_ID)
    # And the canonical id.
    assert store.get_method_references(project.id, CANONICAL_ID)


def test_a_lookup_is_unaffected_by_the_spelling_of_the_stored_callee(
    store: Store, tmp_path: Path
) -> None:
    """Both spellings of the same call are found by the same lookup, and both come
    back in the canonical spelling."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    with store.transaction() as connection:
        for callee in (CANONICAL_ID, SPACED_ID):
            connection.execute(
                "INSERT INTO xrefs VALUES (?,?,?,?,?)",
                (project.id, CALLER, callee, "invoke", "[]"),
            )

    found = store.get_method_references(project.id, CANONICAL_ID)

    assert len(found) == 2
    assert {ref.callee for ref in found} == {CANONICAL_ID}


def test_an_old_workspace_prints_canonical_method_ids(store: Store, tmp_path: Path) -> None:
    """The method table of an old workspace is read back in the canonical spelling,
    so the id the user copies out of it is the id that resolves."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO methods VALUES (?,?,?,?,?,?,?,?)",
            (
                project.id,
                "com.example.demo.Crypto",
                "sign",
                SPACED_DESCRIPTOR,
                "[]",
                None,
                0,
                "[]",
            ),
        )

    methods = store.list_methods(project.id)

    assert [m.qualified_name for m in methods] == [CANONICAL_ID]


def test_a_search_hit_names_a_method_the_way_the_method_table_does(
    store: Store, tmp_path: Path
) -> None:
    """A search result and the method it names must not look like two methods."""
    project = _project()
    store.save_project(project, tmp_path, manifest=None)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO search_index (kind, qualified_name, project_id, body) VALUES (?,?,?,?)",
            ("method", SPACED_ID, project.id, "com.example.demo.Crypto sign"),
        )

    results = store.search(project.id, "sign")

    assert [row["name"] for row in results] == [CANONICAL_ID]
