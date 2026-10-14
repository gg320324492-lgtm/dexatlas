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
