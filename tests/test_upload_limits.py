"""What the API refuses, and when.

An upload arrives over a network and an APK arrives inside an archive, and
both are untrusted sizes. The old API read the whole upload into memory,
wrote it out, and only then decided whether it was an APK — and the
validation read every entry of the archive to check its checksums, so a
four-megabyte zip could ask the machine for four gigabytes.

These tests attack the real endpoints with real bodies.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core import ingest
from tests.conftest import MINIMAL_DEX, MINIMAL_MANIFEST, build_apk

#: The payload the zip bomb carries. Sixty-four megabytes of zeroes is a few
#: kilobytes on disk and a thousand-fold expansion.
BOMB_PAYLOAD_BYTES = 64 * 1024 * 1024


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def client(workspace: Path) -> Iterator[TestClient]:
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    get_settings.cache_clear()

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _bomb_apk(path: Path, payload_bytes: int = BOMB_PAYLOAD_BYTES) -> Path:
    """A ZIP whose contents expand far beyond the file on disk."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo("assets/bomb.bin", date_time=(2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        chunk = b"\0" * (1024 * 1024)
        with archive.open(info, "w") as entry:
            for _ in range(payload_bytes // len(chunk)):
                entry.write(chunk)
        archive.writestr("AndroidManifest.xml", MINIMAL_MANIFEST)
        archive.writestr("classes.dex", MINIMAL_DEX)
    return path


def _uploads(workspace: Path) -> list[Path]:
    uploads = workspace / "uploads"
    return sorted(uploads.iterdir()) if uploads.is_dir() else []


def test_an_upload_over_the_limit_is_refused(client: TestClient, workspace: Path) -> None:
    """The limit is the limit, and the bytes over it are never written.

    The threshold is lowered here so the test does not have to send a quarter
    of a gigabyte to reach it; everything else — the request, the copy, the
    refusal — is the real thing.
    """
    limit = 1024
    original = ingest.MAX_APK_BYTES
    ingest.MAX_APK_BYTES = limit
    try:
        response = client.post(
            "/analyze",
            files={"file": ("big.apk", b"x" * (limit * 4), "application/octet-stream")},
        )
    finally:
        ingest.MAX_APK_BYTES = original

    assert response.status_code == 413
    assert str(limit) in response.json()["detail"]
    assert _uploads(workspace) == [], "the refused upload was left on disk"


def test_an_upload_that_declares_no_length_is_refused_while_it_streams(
    client: TestClient, workspace: Path
) -> None:
    """A chunked upload declares no length, so the copy itself has to count.

    This is the backstop behind the declared-length check: the request is
    refused while it streams, so the bytes over the limit are never written.
    """
    limit = 1024
    original = ingest.MAX_APK_BYTES
    ingest.MAX_APK_BYTES = limit
    boundary = "----dexatlas-test-boundary"
    payload = b"y" * (limit * 4)

    def body():
        yield (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="big.apk"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        yield payload
        yield f"\r\n--{boundary}--\r\n".encode()

    try:
        response = client.post(
            "/analyze",
            content=body(),
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        )
    finally:
        ingest.MAX_APK_BYTES = original

    assert response.status_code == 413
    assert _uploads(workspace) == [], "the refused upload was left on disk"


def test_a_zip_bomb_is_refused(client: TestClient, workspace: Path) -> None:
    """Four megabytes on disk can ask for four gigabytes out.

    The sizes are read from the archive's central directory, so the refusal
    costs nothing and nothing is expanded to reach it.
    """
    bomb = _bomb_apk(workspace / "bomb.apk")
    assert bomb.stat().st_size < 1024 * 1024, "the bomb is not small enough to be one"

    response = client.post(
        "/analyze",
        files={"file": ("bomb.apk", bomb.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 422
    assert "expands" in response.json()["detail"]
    assert _uploads(workspace) == [], "the refused archive was left on disk"


def test_an_archive_that_declares_too_much_is_refused(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The absolute ceiling is enforced as well as the ratio.

    The threshold is lowered so the test does not have to build a two-gigabyte
    archive to reach it.
    """
    limit = 1024 * 1024
    monkeypatch.setattr(ingest, "MAX_APK_UNCOMPRESSED_BYTES", limit)
    apk = build_apk(workspace / "fat.apk", extra={"assets/fat.bin": b"\0" * (limit * 4)})

    response = client.post(
        "/analyze",
        files={"file": ("fat.apk", apk.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 422
    assert "declares" in response.json()["detail"]
    assert _uploads(workspace) == [], "the refused archive was left on disk"


def test_a_normal_apk_is_still_accepted(client: TestClient, workspace: Path) -> None:
    """The limits must not stop the ordinary case."""
    apk = build_apk(workspace / "demo.apk")

    response = client.post(
        "/analyze",
        files={"file": ("demo.apk", apk.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 202
    assert response.json()["project_id"].startswith("apk_")


@pytest.mark.slow
def test_the_apk_is_inspected_once(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading an archive is not free, and doing it twice is twice the cost.

    The API inspects the upload to find its hash and to look for an earlier
    analysis of the same file. The analysis then inspects it again — which is
    how one upload came to be expanded twice before it was even analysed.
    """
    api_module = import_module("dexatlas.api.app")
    pipeline_module = import_module("dexatlas.core.pipeline")

    calls: list[str] = []
    original_api = api_module.inspect_apk
    original_pipeline = pipeline_module.inspect_apk

    def counting_api(path: Path):
        calls.append("api")
        return original_api(path)

    def counting_pipeline(path: Path):
        calls.append("pipeline")
        return original_pipeline(path)

    monkeypatch.setattr(api_module, "inspect_apk", counting_api)
    monkeypatch.setattr(pipeline_module, "inspect_apk", counting_pipeline)

    apk = build_apk(workspace / "demo.apk")
    response = client.post(
        "/analyze",
        files={"file": ("demo.apk", apk.read_bytes(), "application/vnd.android.package-archive")},
    )

    assert response.status_code == 202
    assert calls == ["api"], f"the archive was read more than once: {calls}"
