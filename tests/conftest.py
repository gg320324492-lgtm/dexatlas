"""Shared fixtures.

Every fixture here is built from scratch in-process: a few bytes of a zip with Android
markers in it. No third-party APK ever enters this repository or its test suite.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend

#: A minimal but real AndroidManifest. Not valid on a device — it is here to exercise
#: manifest parsing, not to be installed.
MINIMAL_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
          package="com.example.demo"
          android:versionCode="42"
          android:versionName="1.4.2">
    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <application android:label="Demo">
        <activity android:name="com.example.demo.MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <activity android:name="com.example.demo.SettingsActivity" android:exported="false" />
        <service android:name="com.example.demo.SyncService" android:exported="true" />
        <receiver android:name="com.example.demo.BootReceiver" />
        <provider android:name="com.example.demo.DataProvider"
                  android:authorities="com.example.demo.provider" />
    </application>
</manifest>
"""

MINIMAL_DEX = b"dex\n035\x00" + b"\x00" * 64


def build_apk(
    path: Path,
    *,
    manifest: str = MINIMAL_MANIFEST,
    dex_count: int = 1,
    extra: dict[str, bytes] | None = None,
) -> Path:
    """Write a zip that passes APK validation.

    The DEX payload is a stub header, not real bytecode: ingestion must identify and
    hash the archive without needing to parse the DEX itself.
    """
    entries: dict[str, bytes] = {
        "AndroidManifest.xml": manifest.encode("utf-8"),
        "resources.arsc": b"\x02\x00\x0c\x00",
        "META-INF/CERT.RSA": b"0\x82",
    }
    for index in range(dex_count):
        # Matches the platform convention: classes.dex, classes2.dex, classes3.dex…
        name = "classes.dex" if index == 0 else f"classes{index + 1}.dex"
        entries[name] = MINIMAL_DEX
    if extra:
        entries.update(extra)

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return path


@pytest.fixture
def minimal_apk(tmp_path: Path) -> Path:
    return build_apk(tmp_path / "minimal.apk")


@pytest.fixture
def not_an_apk(tmp_path: Path) -> Path:
    path = tmp_path / "notes.txt"
    path.write_text("this is not an archive", encoding="utf-8")
    return path


@pytest.fixture
def zip_without_android_markers(tmp_path: Path) -> Path:
    path = tmp_path / "archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", "just a zip")
    return path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    path = tmp_path / "empty.apk"
    path.touch()
    return path


@pytest.fixture
def settings(tmp_path: Path):
    from dexatlas.config.settings import Settings

    return Settings(workspace=tmp_path / "workspace")


@pytest.fixture
def apktool(settings) -> ApktoolBackend:
    """An ApktoolBackend on a test workspace, for parsing already-decoded output.

    No APK is decoded here — these tests exercise the parser against manifests written
    to disk, so they need no installed tool.
    """
    return ApktoolBackend(settings)


@pytest.fixture
def jadx(settings) -> JadxBackend:
    """A JadxBackend used only for its pure source-parsing helpers."""
    return JadxBackend(settings)


@pytest.fixture
def store(tmp_path: Path):
    from dexatlas.core.storage import Store

    return Store.open(tmp_path / "test.db")
