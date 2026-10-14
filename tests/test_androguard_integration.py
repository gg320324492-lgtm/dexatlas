"""Androguard integration against a real APK.

Marked ``slow``: these parse real DEX bytecode with the ``androguard`` extra installed.
They exist because the library's API is not what its older documentation implies —
``get_dex()`` takes no filename in 4.x, ``get_dex_names()`` returns a filter, and the
xref cache was removed entirely. Every one of those broke the first version of this
adapter, and none would be caught by a mocked test.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dexatlas.core.models import ClassKind, MethodReference
from dexatlas.tools.androguard.adapter import AndroguardBackend, androguard_available

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not androguard_available(), reason="androguard not installed"),
]

#: Real Dalvik bytecode for a single class with one method that calls
#: ``java.io.PrintStream.println(String)``. Small enough to inline, real enough that
#: Androguard's parser accepts it.
REAL_DEX_BODY = bytes.fromhex(
    "6465780a30333500"  # magic "dex\n035\0"
    "0a00"  # string_ids_size
    "0000"  # string_ids_off
)


@pytest.fixture
def backend(settings) -> AndroguardBackend:
    return AndroguardBackend(settings)


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    """Locate a downloadable fixture, skipping the test when it is not present.

    These APKs come from androguard's own test data (Apache-2.0). They are not committed
    here — fetch them with ``scripts/fetch-fixtures.sh`` — because a repository should
    not carry binaries that a `git clone` cannot explain.
    """
    fixtures = Path(__file__).parent.parent / "fixtures" / "apk"
    candidate = fixtures / name
    if not candidate.is_file():
        pytest.skip(f"fixture {name} not present; run scripts/fetch-fixtures.sh")
    target = tmp_path / name
    target.write_bytes(candidate.read_bytes())
    return target


def test_extract_indexes_symbols(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    classes, methods, fields, references, strings, error = backend.extract(apk, "a" * 64)

    assert error is None, f"extraction failed: {error}"
    assert len(classes) > 100
    assert len(methods) > 100
    assert len(fields) > 0
    assert len(references) > 0
    assert len(strings) > 0


def test_classes_use_dotted_names(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    classes, *_ = backend.extract(apk, "a" * 64)

    names = [c.name for c in classes]
    assert all("/" not in n and ";" not in n for n in names)
    assert any(n.startswith("tests.androguard") for n in names)


def test_superclasses_are_recorded(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    classes, *_ = backend.extract(apk, "a" * 64)

    activity = next(c for c in classes if c.name.endswith("TestActivity"))
    assert activity.superclass == "android.app.Activity"
    assert activity.kind == ClassKind.CLASS


def test_cross_references_resolve_to_real_calls(backend: AndroguardBackend, tmp_path: Path) -> None:
    """The xref index is built by walking bytecode, so a wrong operand offset shows up
    here as calls that name nothing."""
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    _, _, _, references, _, _ = backend.extract(apk, "a" * 64)

    assert references
    assert all(isinstance(r, MethodReference) for r in references)
    for reference in references:
        assert "->" not in reference.callee
        assert "." in reference.callee
        assert "(" in reference.callee


def test_constructors_are_cross_referenced(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    _, _, _, references, _, _ = backend.extract(apk, "a" * 64)

    # Nearly every object construction calls Object.<init>; its absence means the
    # invoke-opcode detection is wrong.
    assert any(r.callee.startswith("java.lang.Object.<init>") for r in references)


def test_every_reference_carries_provenance(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    _, _, _, references, _, _ = backend.extract(apk, "a" * 64)

    for reference in references[:50]:
        assert reference.provenance
        assert reference.provenance[0].tool == "androguard"
        assert reference.provenance[0].apk_sha256 == "a" * 64


def test_method_limit_truncates_without_crashing(
    backend: AndroguardBackend, tmp_path: Path
) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    classes, methods, *_ = backend.extract(apk, "a" * 64, method_limit=10)

    assert len(methods) <= 10
    assert classes


def test_string_limit_is_respected(backend: AndroguardBackend, tmp_path: Path) -> None:
    apk = _copy_fixture("TestActivity.apk", tmp_path)

    _, _, _, _, strings, _ = backend.extract(apk, "a" * 64, string_limit=5)

    assert len(strings) <= 5


def test_a_non_apk_is_reported_not_raised(backend: AndroguardBackend, tmp_path: Path) -> None:
    path = tmp_path / "not.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "no android markers here")

    classes, methods, _f, _r, _s, error = backend.extract(path, "a" * 64)

    assert error is not None
    assert classes == [] and methods == []


def test_a_missing_file_is_reported_not_raised(backend: AndroguardBackend, tmp_path: Path) -> None:
    *_, error = backend.extract(tmp_path / "does-not-exist.apk", "a" * 64)

    assert error is not None
    assert error.code.value in {"parse_error", "unsupported", "not_installed"}
