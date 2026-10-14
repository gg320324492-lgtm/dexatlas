"""CLI smoke tests.

Every command is actually executed. Rich markup errors, unencodable glyphs and exit-code
mistakes only surface when a command really runs — a unit test that imports the CLI
misses all of it.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dexatlas.cli.main import app

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI at an isolated workspace so no test touches a real project DB."""
    from dexatlas.config.settings import get_settings

    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")
    monkeypatch.setenv("DEXATLAS_APKTOOL_JAR", "")
    # Settings is lru_cached, so a changed environment alone would be ignored and one
    # test would see another's projects.
    get_settings.cache_clear()
    try:
        yield ws
    finally:
        get_settings.cache_clear()


def _run(*args: str):
    return runner.invoke(app, list(args))


# -- meta -------------------------------------------------------------------


def test_version_prints() -> None:
    result = _run("version")

    assert result.exit_code == 0
    assert "dexatlas" in result.stdout


def test_backends_runs() -> None:
    result = _run("backends")

    assert result.exit_code == 0
    assert "jadx" in result.stdout
    assert "apktool" in result.stdout
    assert "androguard" in result.stdout


def test_help_does_not_crash() -> None:
    assert _run("--help").exit_code == 0


def test_no_console_call_has_unpaired_markup() -> None:
    """A stray closing tag raises ``MarkupError`` at print time.

    Rich raises only when the line actually executes, so these five bugs shipped a CLI
    that crashed on ordinary commands. Scan every output string instead.
    """
    import re

    from dexatlas.cli import main as cli_module

    tag = re.compile(r"\[/?[a-z][a-z0-9 _#=.,]*\]", re.IGNORECASE)
    problems: list[str] = []

    for name in dir(cli_module):
        func = getattr(cli_module, name)
        if not callable(func) or not hasattr(func, "__doc__"):
            continue
        source = getattr(func, "__wrapped__", func)
        try:
            lines = inspect.getsource(source).splitlines()
        except (OSError, TypeError):
            continue

        for lineno, line in enumerate(lines, 1):
            if "print(" not in line and "add_row(" not in line:
                continue
            stack: list[str] = []
            for match in tag.finditer(line):
                found = match.group(0)
                if found.startswith("[/"):
                    if not stack:
                        problems.append(f"{name}:{lineno} stray {found}")
                        break
                    stack.pop()
                else:
                    stack.append(found)

    assert not problems, "unpaired Rich markup:\n" + "\n".join(problems)


# -- empty workspace --------------------------------------------------------


def test_projects_on_empty_workspace(workspace: Path) -> None:
    result = _run("projects")

    assert result.exit_code == 0
    assert "No projects yet" in result.stdout


def test_classes_on_empty_workspace(workspace: Path) -> None:
    result = _run("classes", "apk_nope")

    assert result.exit_code == 1


def test_manifest_on_unknown_project(workspace: Path) -> None:
    result = _run("manifest", "apk_nope")

    assert result.exit_code == 1


def test_search_on_unknown_project(workspace: Path) -> None:
    result = _run("search", "apk_nope", "anything")

    assert result.exit_code == 1


def test_source_on_unknown_project(workspace: Path) -> None:
    result = _run("source", "apk_nope", "com.example.Missing")

    assert result.exit_code == 1


def test_xrefs_on_unknown_project(workspace: Path) -> None:
    result = _run("xrefs", "apk_nope", "com.example.Missing.m()V")

    assert result.exit_code == 1


def test_methods_on_unknown_project(workspace: Path) -> None:
    result = _run("methods", "apk_nope")

    assert result.exit_code == 1


# -- analysis ---------------------------------------------------------------


def test_analyze_rejects_a_non_apk(workspace: Path, not_an_apk: Path) -> None:
    result = _run("analyze", str(not_an_apk))

    assert result.exit_code == 2
    assert "Not a usable APK" in result.output


def test_analyze_rejects_a_missing_file(workspace: Path) -> None:
    result = _run("analyze", str(workspace / "does-not-exist.apk"))

    assert result.exit_code == 2


@pytest.mark.slow
def test_analyze_writes_both_report_formats(
    workspace: Path, tmp_path: Path, minimal_apk: Path
) -> None:
    markdown = tmp_path / "out" / "report.md"
    json_out = tmp_path / "out" / "report.json"

    result = _run("analyze", str(minimal_apk), "-o", str(markdown), "--json", str(json_out))

    assert result.exit_code in (0, 1)
    assert markdown.exists()
    assert json_out.exists()
    assert "# DexAtlas analysis report" in markdown.read_text(encoding="utf-8")


@pytest.mark.slow
def test_the_two_interfaces_share_one_workspace(workspace: Path, minimal_apk: Path) -> None:
    """A project analysed through the CLI is visible to a fresh Analyzer, which is the
    concrete form of "CLI and REST API use the same analysis core"."""
    from dexatlas.config.settings import get_settings
    from dexatlas.core.pipeline import Analyzer

    get_settings.cache_clear()
    _run("analyze", str(minimal_apk))
    get_settings.cache_clear()

    projects = Analyzer().store.list_projects()
    assert len(projects) == 1
