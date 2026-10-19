"""Backend discovery and platform handling.

The jadx distribution ships one launcher per platform and the bare ``jadx`` name in
``bin/`` is the shell script. Pointing at it from Windows produces "not a valid Win32
application", and that failure is invisible until an analysis is run — so resolution is
tested directly.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from dexatlas.core.models import ToolErrorCode
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend


def _write_launcher(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\necho jadx 1.5.2\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


# -- jadx -------------------------------------------------------------------


def test_jadx_finds_a_shell_launcher_when_it_is_the_only_one(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    launcher = _write_launcher(tmp_path / "bin" / "jadx")
    jadx._settings.jadx_path = str(launcher)

    assert jadx.resolve() == launcher


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher preference")
def test_jadx_prefers_a_windows_launcher(jadx: JadxBackend, tmp_path: Path) -> None:
    """Pointing at the shell script on Windows must resolve to the .bat beside it."""
    bin_dir = tmp_path / "bin"
    shell_script = _write_launcher(bin_dir / "jadx")
    batch = bin_dir / "jadx.bat"
    batch.write_text("@echo off\r\necho jadx 1.5.2\r\n", encoding="utf-8")

    jadx._settings.jadx_path = str(shell_script)

    assert jadx.resolve() == batch


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher preference")
def test_jadx_falls_back_when_no_windows_launcher_exists(jadx: JadxBackend, tmp_path: Path) -> None:
    shell_script = _write_launcher(tmp_path / "bin" / "jadx")
    jadx._settings.jadx_path = str(shell_script)

    # Nothing better exists; return what we have rather than pretending it is absent.
    assert jadx.resolve() == shell_script


def test_jadx_reports_missing_when_nothing_is_configured(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    jadx._settings.jadx_path = ""

    assert jadx.resolve() is None
    assert jadx.available() is False


def test_jadx_missing_error_explains_how_to_configure(jadx: JadxBackend) -> None:
    error = jadx.missing_error()

    assert error.code == ToolErrorCode.NOT_INSTALLED
    assert "DEXATLAS_JADX_PATH" in (error.detail or "")


# -- apktool ----------------------------------------------------------------


def test_apktool_prefers_an_explicit_jar(apktool: ApktoolBackend, tmp_path: Path) -> None:
    jar = tmp_path / "apktool.jar"
    jar.write_bytes(b"PK\x03\x04")
    apktool._settings.apktool_jar = str(jar)

    assert apktool.resolve() == jar
    assert apktool._argv("--version")[0:3] == ["java", "-jar", str(jar)]


def test_apktool_uses_a_launcher_script_directly(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """A non-jar launcher is invoked directly rather than through java -jar."""
    script = tmp_path / "apktool"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    apktool._settings.apktool_jar = str(script)

    assert apktool._argv("d", "app.apk") == [str(script), "d", "app.apk"]


def test_apktool_argv_is_empty_when_missing(
    apktool: ApktoolBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    apktool._settings.apktool_jar = ""

    assert apktool.resolve() is None
    assert apktool._argv("d") == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "settings.py documents that an empty path disables the backend, but which_or_none "
        "falls back to a PATH lookup, so an empty string does not disable anything. Found "
        "while writing the Smali fallback integration test, which could not otherwise make "
        "JADX unavailable. Not fixed here: it is outside FIX-001. See the execution report."
    ),
)
def test_an_empty_path_disables_the_backend(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An empty configured path is documented to mean "do not use this backend"."""
    # Named jadx.bat so that `shutil.which` finds it on every platform the
    # resolution code looks for.
    _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    jadx._settings.jadx_path = ""

    assert jadx.resolve() is None


def test_apktool_decode_without_the_tool_is_a_value_not_an_exception(
    apktool: ApktoolBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", "")
    apktool._settings.apktool_jar = ""

    outcome = apktool.decode(tmp_path / "app.apk", tmp_path / "out")

    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.NOT_INSTALLED


# -- registry ---------------------------------------------------------------


def test_registry_separates_available_from_missing(settings, monkeypatch) -> None:
    from dexatlas.tools.registry import BackendRegistry

    monkeypatch.setenv("PATH", "")
    registry = BackendRegistry(settings)

    available = {b.name for b in registry.available()}
    missing = {b.name for b in registry.missing()}
    assert available.isdisjoint(missing)
    assert available | missing == {"jadx", "apktool", "androguard"}


def test_registry_rejects_an_unknown_backend(settings) -> None:
    from dexatlas.tools.registry import BackendRegistry

    with pytest.raises(KeyError, match="unknown backend"):
        BackendRegistry(settings).get("nonesuch")
