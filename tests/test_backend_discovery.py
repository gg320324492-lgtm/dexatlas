"""Backend discovery and platform handling.

The jadx distribution ships one launcher per platform and the bare ``jadx`` name in
``bin/`` is the shell script. Pointing at it from Windows produces "not a valid Win32
application", and that failure is invisible until an analysis is run — so resolution is
tested directly.

A configured path is a statement of intent, and it has three states that are not
interchangeable: unset means "find the tool on PATH", a path means "use this one", and
an empty string means "do not use this backend at all" — the last of which has to hold
even when the tool happens to be installed.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

from dexatlas.core.models import ToolErrorCode
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import which_or_none
from dexatlas.tools.jadx.adapter import JadxBackend


def _write_launcher(path: Path, label: str = "jadx 1.5.2") -> Path:
    """Write an executable stand-in for a backend launcher."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho {label}\n", encoding="utf-8")
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


# -- disabling a backend through configuration ---------------------------------


def test_an_empty_path_disables_the_backend(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An empty configured path is documented to mean "do not use this backend".

    The tool is installed and on ``PATH`` on purpose: the point of the empty string is
    that it holds against what happens to be discoverable, so a test without a
    discoverable jadx would pass even if the empty string were silently ignored.
    """
    # Named jadx.bat so that `shutil.which` finds it on every platform the
    # resolution code looks for.
    _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    jadx._settings.jadx_path = ""

    assert jadx.resolve() is None
    assert jadx.available() is False


def test_an_empty_path_disables_apktool(
    apktool: ApktoolBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The rule is the shared resolver's, not one backend's — apktool obeys it too."""
    # Named apktool.bat because that is what `shutil.which` looks for on Windows:
    # it only tries the PATHEXT extensions, never the bare name.
    _write_launcher(tmp_path / "bin" / "apktool.bat", label="Apktool 2.10.0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    apktool._settings.apktool_jar = ""

    assert apktool.resolve() is None
    assert apktool._argv("d") == []


def test_an_unset_path_still_searches_path(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``None`` means "not configured", which is the opposite of "disabled"."""
    launcher = _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    jadx._settings.jadx_path = None

    assert jadx.resolve() == launcher


def test_an_empty_path_wins_over_a_configured_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An explicit "no" is not outvoted by another candidate for the same backend."""
    _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    # which_or_none is shared, so the conflict is checked on it directly.
    assert which_or_none([str(tmp_path / "bin" / "jadx.bat"), ""]) is None


def test_a_configured_path_outranks_path_lookup(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pinned location is preferred over whatever is installed."""
    pinned = _write_launcher(tmp_path / "pinned" / "jadx.bat", label="jadx 9.9.9")
    _write_launcher(tmp_path / "bin" / "jadx.bat", label="jadx 1.5.2")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    jadx._settings.jadx_path = str(pinned)

    assert jadx.resolve() == pinned


def test_a_missing_configured_path_falls_back_to_path_lookup(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A stale pin must not take the backend offline.

    This is the behaviour that made the original Smali-fallback test pass on a
    developer machine and fail in CI: pointing ``jadx_path`` at something that does
    not exist looks like disabling JADX, but it is not — the installed tool is still
    found. Kept deliberately, because the alternative turns a mistyped path into a
    silently missing backend, and pinned so a future change has to say why.
    """
    launcher = _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    jadx._settings.jadx_path = str(tmp_path / "no-such-dir" / "jadx")

    assert jadx.resolve() == launcher


def test_a_missing_configured_path_is_reported_when_nothing_replaces_it(
    jadx: JadxBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nothing on PATH either: the stale pin is why nothing was found, so say so."""
    monkeypatch.setenv("PATH", "")
    jadx._settings.jadx_path = str(tmp_path / "no-such-dir" / "jadx")

    assert jadx.resolve() is None
    assert jadx.missing_error().code == ToolErrorCode.NOT_INSTALLED


def test_a_disabled_backend_fails_closed(
    apktool: ApktoolBackend, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Disabling a backend degrades the run to a recorded error, never a crash."""
    _write_launcher(tmp_path / "bin" / "apktool.bat", label="Apktool 2.10.0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    apktool._settings.apktool_jar = ""

    outcome = apktool.decode(tmp_path / "app.apk", tmp_path / "out")

    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.NOT_INSTALLED
    assert not (tmp_path / "out").exists()


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


# -- the shared resolver ----------------------------------------------------


def test_which_or_none_treats_an_empty_candidate_as_a_disable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The disable rule belongs to the resolver, so it holds for every caller."""
    _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    assert which_or_none([""], names=("jadx", "jadx.bat")) is None


def test_which_or_none_reports_a_stale_pin_instead_of_replacing_it_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Falling back to PATH is allowed; doing it silently is not."""
    launcher = _write_launcher(tmp_path / "bin" / "jadx.bat")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    stale = tmp_path / "no-such-dir" / "jadx"

    with caplog.at_level("WARNING", logger="dexatlas.tools.base"):
        assert which_or_none([str(stale)], names=("jadx", "jadx.bat")) == launcher

    assert any(str(stale) in record.getMessage() for record in caplog.records)


def test_an_empty_environment_variable_reaches_the_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``DEXATLAS_JADX_PATH=`` has to arrive as an empty string, not as unset.

    If the configuration layer swallowed it, the disable signal would be lost before
    the resolver ever saw it and the backend would come back from ``PATH``.
    """
    from dexatlas.config.settings import Settings

    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")

    assert Settings(workspace=tmp_path / "workspace").jadx_path == ""


def test_every_backend_reports_a_bare_version_number(settings) -> None:
    """The version column has to read the same way for every backend.

    JADX and Apktool print their own version, so they report a bare number.
    Androguard used to prefix its name, which made one entry in a list of versions
    read differently from the rest — and a reader comparing "4.1.4" with
    "androguard 4.1.4" has to know which is which.
    """
    from dexatlas.tools.androguard.adapter import AndroguardBackend, androguard_available

    reported = {
        "jadx": JadxBackend(settings).version(),
        "apktool": ApktoolBackend(settings).version(),
    }
    if androguard_available():
        reported["androguard"] = AndroguardBackend(settings).version()

    for name, value in reported.items():
        if value is None:
            continue  # not installed here; nothing to compare
        assert not value.startswith(name), f"{name} reports {value!r}, not a bare version"
        assert re.match(r"^\d", value), f"{name} reports {value!r}, which is not a version"
