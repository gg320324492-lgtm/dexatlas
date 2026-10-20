"""APK ingestion — validation, hashing and archive inspection.

Runs before any backend does, using only the standard library. If this rejects a file,
no backend needs to be trusted with it.

The archive is inspected through its *central directory* — the table of contents a ZIP
carries — for the sizes it declares. Nothing is expanded to read them, so an archive
that is a bomb is refused before a single byte of it is decompressed, and reading the
sizes costs nothing where expanding the contents to look at them costs whatever the
archive asks for.

Reading the contents is a different matter. Verifying an entry's checksum means
decompressing it, so that step does read the archive — up to a budget of
``MAX_VERIFIED_BYTES`` of decompressed data, across every entry. Past the budget the
archive is accepted on the strength of its structure alone: the entries beyond it are
not decompressed, so a corruption in one of them is not noticed.
"""

from __future__ import annotations

import zipfile
import zlib
from pathlib import Path
from typing import BinaryIO

from dexatlas.core.models import ApkMetadata, sha256_file

#: Directories that mark a ZIP as an Android application package rather than any ZIP.
_ANDROID_MARKERS = ("AndroidManifest.xml", "classes.dex", "resources.arsc")

_NATIVE_LIB_SUFFIXES = (".so",)

#: How much of an archive is read at a time.
_CHUNK_SIZE = 1024 * 1024

#: The largest APK DexAtlas will analyse, in bytes.
#:
#: 256 MiB is above the 200 MB ceiling Google Play puts on an APK, so every APK
#: that can be distributed is analysable, and it is the point at which an upload
#: stops being an inconvenience and starts being a disk-space problem.
MAX_APK_BYTES = 256 * 1024 * 1024

#: The name an upload is shown under when the client did not give one.
DEFAULT_UPLOAD_NAME = "upload.apk"

#: The longest a name shown to a reader may be, in bytes.
#:
#: A file name cannot be longer than this on any filesystem DexAtlas runs on, so
#: a name that is longer cannot name anything — and a name that is shown is a
#: name somebody may try to use.
MAX_NAME_BYTES = 255

#: The largest total uncompressed size an APK's contents may declare.
#:
#: A real APK expands by a factor of two or three, so 2 GiB — eight times that — is
#: more than any real package needs, and it is the ceiling on what a hostile
#: archive can make the backends write into the workspace.
MAX_APK_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024

#: The largest ratio of uncompressed size to compressed size an APK may have.
#:
#: A real APK holds code and media and expands by a factor of two or three. A
#: hundred is far past anything real and far below the thousand-fold expansion of
#: a bomb, so this check and the one above catch different archives.
MAX_APK_EXPANSION_RATIO = 100

#: How much of an archive is read to verify the checksums of its entries.
#:
#: Reading an entry is what verifies its checksum, and the size of an archive is
#: not known until it has been read, so this is a budget rather than a complete
#: check. It is above the size of every archive an ordinary analysis sees. An
#: archive whose contents are larger than this is read only in part: the entries
#: past the budget are not decompressed, so a corruption in one of them is not
#: noticed.
#:
#: The budget is its own. It bounds what ingestion reads out of the APK; the cap
#: on a backend's output bounds a different thing — what a tool writes back. One
#: is not a share of the other, and reaching one does not raise the other.
MAX_VERIFIED_BYTES = 256 * 1024 * 1024


class ApkValidationError(ValueError):
    """The file is not something we are willing to hand to an analysis backend."""


class UploadTooLarge(ValueError):
    """The upload is larger than the limit."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"the upload is larger than {limit} bytes")
        self.limit = limit


def save_upload(source: BinaryIO, target: Path, *, limit: int | None = None) -> int:
    """Stream an upload to disk, refusing it if it grows past the limit.

    The bytes are counted as they arrive, so an upload over the limit is refused
    while it streams: it is never held in memory in one piece, and it is never
    written in full. The partial file is removed before the refusal, so a
    rejected upload leaves nothing behind.

    ``limit`` defaults to :data:`MAX_APK_BYTES`, read when the upload starts
    rather than when this function was defined, so that the limit a
    deployment applies is the limit that is enforced.

    Returns the number of bytes written.
    """
    if limit is None:
        limit = MAX_APK_BYTES
    written = 0
    try:
        with target.open("wb") as handle:
            while chunk := source.read(_CHUNK_SIZE):
                written += len(chunk)
                if written > limit:
                    raise UploadTooLarge(limit)
                handle.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return written


def validate_apk(path: Path) -> None:
    """Raise :class:`ApkValidationError` unless ``path`` looks like an Android package."""
    if not path.is_file():
        raise ApkValidationError(f"{path} is not a file")

    size = path.stat().st_size
    if size == 0:
        raise ApkValidationError(f"{path} is empty")

    if size > MAX_APK_BYTES:
        raise ApkValidationError(
            f"{path} is {size} bytes; an APK may not be larger than {MAX_APK_BYTES} bytes"
        )

    if not zipfile.is_zipfile(path):
        raise ApkValidationError(f"{path} is not a ZIP archive; APKs are ZIP archives")

    try:
        with zipfile.ZipFile(path) as archive:
            _check_declared_size(path, archive)
            names = set(archive.namelist())
            if not any(marker in names for marker in _ANDROID_MARKERS):
                raise ApkValidationError(
                    f"{path} contains no AndroidManifest.xml, classes.dex or resources.arsc; "
                    "it does not look like an Android application package"
                )
            _verify_entries(path, archive)
    except zipfile.BadZipFile as exc:
        raise ApkValidationError(f"{path} is not a readable ZIP archive: {exc}") from exc


def _check_declared_size(path: Path, archive: zipfile.ZipFile) -> None:
    """Refuse an archive whose contents declare more than the limits allow.

    The sizes come from the archive's central directory, so nothing is expanded
    to read them: a bomb is refused before a single byte of it is decompressed.
    """
    entries = archive.infolist()
    uncompressed = sum(info.file_size for info in entries)
    if uncompressed > MAX_APK_UNCOMPRESSED_BYTES:
        raise ApkValidationError(
            f"{path} declares {uncompressed} bytes of contents; an APK may not expand "
            f"beyond {MAX_APK_UNCOMPRESSED_BYTES} bytes"
        )

    compressed = sum(info.compress_size for info in entries)
    ratio = uncompressed / max(compressed, 1)
    if ratio > MAX_APK_EXPANSION_RATIO:
        raise ApkValidationError(
            f"{path} expands {ratio:.0f}-fold; an APK may not expand beyond "
            f"{MAX_APK_EXPANSION_RATIO}-fold"
        )


def _verify_entries(path: Path, archive: zipfile.ZipFile) -> None:
    """Read the archive's entries to check their checksums, up to a budget.

    Reading an entry is what verifies its checksum. The budget stops the read
    from becoming the thing the limits above exist to prevent; past it the
    archive is accepted on the strength of its structure.
    """
    read = 0
    for info in archive.infolist():
        if read >= MAX_VERIFIED_BYTES:
            return
        try:
            with archive.open(info) as entry:
                while chunk := entry.read(_CHUNK_SIZE):
                    read += len(chunk)
                    if read >= MAX_VERIFIED_BYTES:
                        return
        except (zipfile.BadZipFile, zlib.error, EOFError, OSError) as exc:
            raise ApkValidationError(f"{path} has a corrupt entry: {info.filename}") from exc


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


__all__ = [
    "MAX_APK_BYTES",
    "MAX_APK_EXPANSION_RATIO",
    "MAX_APK_UNCOMPRESSED_BYTES",
    "ApkValidationError",
    "UploadTooLarge",
    "inspect_apk",
    "save_upload",
    "validate_apk",
]
