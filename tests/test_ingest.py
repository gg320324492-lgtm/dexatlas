"""APK ingestion."""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.ingest import ApkValidationError, inspect_apk, validate_apk
from dexatlas.core.models import sha256_file
from tests.conftest import MINIMAL_MANIFEST, build_apk


def test_accepts_a_minimal_apk(minimal_apk: Path) -> None:
    validate_apk(minimal_apk)


def test_rejects_a_non_archive(not_an_apk: Path) -> None:
    with pytest.raises(ApkValidationError, match="not a ZIP archive"):
        validate_apk(not_an_apk)


def test_rejects_a_zip_without_android_markers(zip_without_android_markers: Path) -> None:
    with pytest.raises(ApkValidationError, match="does not look like an Android"):
        validate_apk(zip_without_android_markers)


def test_rejects_an_empty_file(empty_file: Path) -> None:
    with pytest.raises(ApkValidationError, match="empty"):
        validate_apk(empty_file)


def test_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ApkValidationError, match="not a file"):
        validate_apk(tmp_path / "nope.apk")


def test_inspect_reports_hash_size_and_dex_files(minimal_apk: Path) -> None:
    metadata = inspect_apk(minimal_apk)

    assert len(metadata.sha256) == 64
    assert metadata.size_bytes > 0
    assert metadata.dex_files == ["classes.dex"]
    assert metadata.zip_entries == 4
    assert metadata.has_signed_certificate is True


def test_inspect_lists_multi_dex(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "multi.apk", dex_count=3)

    metadata = inspect_apk(apk)

    assert metadata.dex_files == ["classes.dex", "classes2.dex", "classes3.dex"]


def test_inspect_lists_native_libraries(tmp_path: Path) -> None:
    apk = build_apk(
        tmp_path / "native.apk",
        extra={"lib/arm64-v8a/libfoo.so": b"\x7fELF", "lib/armeabi-v7a/libbar.so": b"\x7fELF"},
    )

    metadata = inspect_apk(apk)

    assert metadata.native_libraries == [
        "lib/arm64-v8a/libfoo.so",
        "lib/armeabi-v7a/libbar.so",
    ]


def test_inspect_resolves_to_an_absolute_path(minimal_apk: Path) -> None:
    metadata = inspect_apk(minimal_apk)

    assert metadata.path.is_absolute()


def test_hash_is_content_addressed_and_stable(tmp_path: Path) -> None:
    """Two APKs with identical contents must produce the same project id."""
    first = build_apk(tmp_path / "a.apk", manifest=MINIMAL_MANIFEST)
    second = build_apk(tmp_path / "b.apk", manifest=MINIMAL_MANIFEST)

    assert inspect_apk(first).sha256 == inspect_apk(second).sha256


def test_generated_fixtures_are_byte_reproducible(tmp_path: Path) -> None:
    """The fixture builder must not embed the wall-clock time.

    ``ZipFile.writestr`` stamps the current time into each entry, so archives built from
    identical content in different seconds differ. Any test comparing their hashes then
    fails intermittently — which is exactly what happened before this was pinned.
    """
    first = build_apk(tmp_path / "one.apk")
    second = build_apk(tmp_path / "two.apk")

    assert first.read_bytes() == second.read_bytes()
    assert sha256_file(first) == sha256_file(second)
