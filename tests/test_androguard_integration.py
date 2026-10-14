"""Androguard integration against a real APK.

Marked ``slow``: these parse real DEX bytecode with the ``androguard`` extra installed.
They exist because the library's API is not what its older documentation implies —
``get_dex()`` takes no filename in 4.x, ``get_dex_names()`` returns a filter, and the
xref cache was removed entirely. Every one of those broke the first version of this
adapter, and none would be caught by a mocked test.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ClassKind, MethodReference
from dexatlas.tools.androguard.adapter import AndroguardBackend, androguard_available

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not androguard_available(), reason="androguard not installed"),
]

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "apk"
FIXTURE_APK = "a" * 64


@pytest.fixture
def backend(settings) -> AndroguardBackend:
    return AndroguardBackend(settings)


@pytest.fixture(scope="module")
def analysis() -> dict[str, Any]:
    """Extract the fixture APK once per module and share the result.

    Androguard builds a large object graph per parse and the resulting models keep it
    alive. Re-parsing the same 175 KB APK in each of ten tests exhausts memory and kills
    the pytest process outright — with no traceback, which reads as a crash rather than
    as the leak it is.
    """
    fixture = FIXTURE_DIR / "TestActivity.apk"
    if not fixture.is_file():
        pytest.skip("fixture not present; run scripts/fetch-fixtures.sh")

    workspace = Path(tempfile.mkdtemp(prefix="dexatlas-it-"))
    extracted = AndroguardBackend(Settings(workspace=workspace)).extract(fixture, FIXTURE_APK)
    classes, methods, fields, references, strings, error = extracted
    return {
        "classes": classes,
        "methods": methods,
        "fields": fields,
        "references": references,
        "strings": strings,
        "error": error,
    }


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a fixture into ``tmp_path`` and return the new path.

    These APKs come from androguard's own test data (Apache-2.0). They are not committed
    here — fetch them with ``scripts/fetch-fixtures.sh`` — because a repository should
    not carry binaries that a `git clone` cannot explain.
    """
    candidate = FIXTURE_DIR / name
    if not candidate.is_file():
        pytest.skip(f"fixture {name} not present; run scripts/fetch-fixtures.sh")
    target = tmp_path / name
    target.write_bytes(candidate.read_bytes())
    return target


# -- extraction -------------------------------------------------------------


def test_extract_indexes_symbols(analysis: dict[str, Any]) -> None:
    assert analysis["error"] is None, f"extraction failed: {analysis['error']}"
    assert len(analysis["classes"]) > 100
    assert len(analysis["methods"]) > 100
    assert len(analysis["fields"]) > 0
    assert len(analysis["references"]) > 0
    assert len(analysis["strings"]) > 0


def test_classes_use_dotted_names(analysis: dict[str, Any]) -> None:
    names = [cls.name for cls in analysis["classes"]]

    assert all("/" not in name and ";" not in name for name in names)
    assert any(name.startswith("tests.androguard") for name in names)


def test_superclasses_are_recorded(analysis: dict[str, Any]) -> None:
    activity = next(cls for cls in analysis["classes"] if cls.name.endswith("TestActivity"))

    assert activity.superclass == "android.app.Activity"
    assert activity.kind == ClassKind.CLASS


# -- cross-references -------------------------------------------------------


def test_cross_references_resolve_to_real_calls(analysis: dict[str, Any]) -> None:
    """The xref index is built by walking bytecode, so a wrong operand offset shows up
    here as calls that name nothing."""
    references = analysis["references"]

    assert references
    assert all(isinstance(ref, MethodReference) for ref in references)
    for reference in references:
        assert "->" not in reference.callee
        assert "." in reference.callee
        assert "(" in reference.callee


def test_constructors_are_cross_referenced(analysis: dict[str, Any]) -> None:
    # Nearly every object construction calls Object.<init>; its absence means the
    # invoke-opcode detection is wrong.
    assert any(ref.callee.startswith("java.lang.Object.<init>") for ref in analysis["references"])


def test_every_reference_carries_provenance(analysis: dict[str, Any]) -> None:
    for reference in analysis["references"][:50]:
        assert reference.provenance
        assert reference.provenance[0].tool == "androguard"
        assert reference.provenance[0].apk_sha256 == FIXTURE_APK


def test_reference_targets_match_the_symbol_index(analysis: dict[str, Any]) -> None:
    """A call target must be spelled exactly like a method id elsewhere in DexAtlas.

    Androguard renders a call target for human reading, with argument descriptors
    space-separated: ``sign(Ljava/lang/String; Ljava/lang/String;)``. Storing that
    verbatim yields a descriptor that never equals the one ``get_descriptor()`` returns,
    so the whole cross-reference index becomes unfindable while still looking healthy.

    Not every target is expected to be declared in this APK — a call to
    ``MyActivity.getApplicationContext()`` names an inherited method — so this asserts
    the property that actually breaks: no id carries whitespace, and the ids that *are*
    declared are found by exactly that spelling.
    """
    references = analysis["references"]
    assert references

    for reference in references:
        assert " " not in reference.callee, (
            f"call target carries whitespace and cannot match a stored descriptor: "
            f"{reference.callee!r}"
        )
        assert "->" not in reference.callee

    known = {method.qualified_name for method in analysis["methods"]}
    own = {r.callee for r in references if r.callee.startswith("tests.androguard.")}
    assert own, "expected cross-references into the fixture's own package"

    # At least some targets must be declared methods that `xrefs` can actually find.
    assert own & known, "no call target resolved against the symbol index"


def test_callers_are_findable_under_the_stored_descriptor(analysis: dict[str, Any]) -> None:
    """A caller id must round-trip through the method-id parser used for lookup."""
    from dexatlas.core.storage import parse_method_id

    for reference in analysis["references"][:50]:
        parsed = parse_method_id(reference.callee)
        assert parsed[0], f"callee id is not parseable: {reference.callee!r}"
        assert parsed[1], f"callee id has no method name: {reference.callee!r}"
        assert parsed[2].startswith("("), f"callee id has no descriptor: {reference.callee!r}"


# -- limits and hostile input -----------------------------------------------


def test_method_limit_truncates_without_crashing(
    backend: AndroguardBackend, tmp_path: Path
) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    classes, methods, *_ = backend.extract(apk, FIXTURE_APK, method_limit=10)

    assert len(methods) <= 10
    assert classes


def test_string_limit_is_respected(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    _, _, _, _, strings, _ = backend.extract(apk, FIXTURE_APK, string_limit=5)

    assert len(strings) <= 5


def test_a_non_apk_is_reported_not_raised(backend: AndroguardBackend, tmp_path: Path) -> None:
    path = tmp_path / "not.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "no android markers here")

    classes, methods, _fields, _refs, _strings, error = backend.extract(path, FIXTURE_APK)

    assert error is not None
    assert classes == []
    assert methods == []


def test_a_missing_file_is_reported_not_raised(backend: AndroguardBackend, tmp_path: Path) -> None:
    *_, error = backend.extract(tmp_path / "does-not-exist.apk", FIXTURE_APK)

    assert error is not None
    assert error.code.value in {"parse_error", "unsupported", "not_installed"}


# -- reference normalisation (no backend needed) -----------------------------


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (
            "Ljava/io/PrintStream;->println(Ljava/lang/String;)V",
            "java.io.PrintStream.println(Ljava/lang/String;)V",
        ),
        (
            "Lcom/example/demo/Crypto;->sign(Ljava/lang/String; Ljava/lang/String;)"
            "Ljava/lang/String;",
            "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
        ),
        (
            "Landroid/util/Log;->i(Ljava/lang/String; Ljava/lang/String;)I",
            "android.util.Log.i(Ljava/lang/String;Ljava/lang/String;)I",
        ),
        ("Ljava/lang/Object;-><init>()V", "java.lang.Object.<init>()V"),
        (
            "Lcom/Foo;->baz([I Ljava/lang/String;)V",
            "com.Foo.baz([ILjava/lang/String;)V",
        ),
    ],
)
def test_dalvik_reference_is_normalised(reference: str, expected: str) -> None:
    from dexatlas.tools.androguard.adapter import _parse_dalvik_reference

    assert _parse_dalvik_reference(reference) == expected


@pytest.mark.parametrize("reference", ["", "garbage", "Lcom/Foo;->bar", "Lcom/Foo;->baz("])
def test_unparseable_reference_returns_none(reference: str) -> None:
    from dexatlas.tools.androguard.adapter import _parse_dalvik_reference

    assert _parse_dalvik_reference(reference) is None


def test_normalised_reference_equals_the_symbol_index_spelling() -> None:
    """The two id spaces must be identical, or cross-references cannot be looked up."""
    from dexatlas.core.storage import parse_method_id
    from dexatlas.tools.androguard.adapter import _parse_dalvik_reference

    qualified = _parse_dalvik_reference(
        "Lcom/example/demo/Crypto;->sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
    )
    assert qualified is not None

    class_name, name, descriptor = parse_method_id(qualified)
    assert class_name == "com.example.demo.Crypto"
    assert name == "sign"
    # A JVM descriptor has no spaces anywhere.
    assert " " not in qualified
    assert descriptor == "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
