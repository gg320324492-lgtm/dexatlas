"""APK ingestion — validation, hashing and archive inspection.

Runs before any backend does, using only the standard library. If this rejects a file,
no backend needs to be trusted with it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from dexatlas.core.models import ApkMetadata, sha256_file

#: Directories that mark a ZIP as an Android application package rather than any ZIP.
_ANDROID_MARKERS = ("AndroidManifest.xml", "classes.dex", "resources.arsc")

_NATIVE_LIB_SUFFIXES = (".so",)


class ApkValidationError(ValueError):
    """The file is not something we are willing to hand to an analysis backend."""


def validate_apk(path: Path) -> None:
    """Raise :class:`ApkValidationError` unless ``path`` looks like an Android package."""
    if not path.is_file():
        raise ApkValidationError(f"{path} is not a file")

    if path.stat().st_size == 0:
        raise ApkValidationError(f"{path} is empty")

    if not zipfile.is_zipfile(path):
        raise ApkValidationError(f"{path} is not a ZIP archive; APKs are ZIP archives")

    try:
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken is not None:
                raise ApkValidationError(f"{path} has a corrupt entry: {broken}")

            names = set(archive.namelist())
            if not any(marker in names for marker in _ANDROID_MARKERS):
                raise ApkValidationError(
                    f"{path} contains no AndroidManifest.xml, classes.dex or resources.arsc; "
                    "it does not look like an Android application package"
                )
    except zipfile.BadZipFile as exc:
        raise ApkValidationError(f"{path} is not a readable ZIP archive: {exc}") from exc


def inspect_apk(path: Path) -> ApkMetadata:
    """Hash and characterize an APK without invoking any external backend."""
    validate_apk(path)

    digest = sha256_file(path)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        dex_files = sorted(n for n in names if n.endswith(".dex") and "/" not in n)
        native_libraries = sorted(
            n for n in names if n.startswith("lib/") and n.endswith(_NATIVE_LIB_SUFFIXES)
        )
        has_certificate = any(
            n.startswith("META-INF/") and n.upper().endswith((".RSA", ".DSA", ".EC", ".SF"))
            for n in names
        )
        metadata = ApkMetadata(
            sha256=digest,
            size_bytes=path.stat().st_size,
            path=path,
            zip_entries=len(names),
            dex_files=dex_files,
            native_libraries=native_libraries,
            has_signed_certificate=has_certificate,
        )

    metadata.path = path.resolve()
    return metadata


__all__ = ["ApkValidationError", "inspect_apk", "validate_apk"]
