"""CLI smoke tests.

Every command is actually executed. Rich markup errors, unencodable glyphs and exit-code
mistakes only surface when a command really runs — a unit test that imports the CLI
misses all of it.
"""

from __future__ import annotations

import hashlib
import inspect
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dexatlas.cli.main import app

runner = CliRunner()

#: A method id as the CLI prints it: qualified name, then the descriptor.
_METHOD_ID = re.compile(r"[A-Za-z0-9_.$<>]+\([^)]*\)[^\s]*")


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


# -- a populated workspace --------------------------------------------------

#: SHA-256 of the seeded APK. Project ids are derived from it, so it is fixed.
SEEDED_SHA256 = "0123456789abcdef" * 4

#: Decompiled Java for the seeded class. The bracketed literal is deliberate: it is
#: the quickest way to notice that the CLI stopped treating source code as text.
SEEDED_JAVA = """package com.example.demo;

public class MainActivity {
    public void onCreate() {
        String label = "[bold]not markup[/bold]";
    }

    public void onResume() {
        onCreate();
    }
}
"""


@pytest.fixture
def seeded_project(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A project with symbols, a manifest and decompiled sources in the store.

    Seeded through the storage layer rather than by running a real analysis: these
    tests are about what the CLI *renders*, and a real run would make the output
    depend on which backends happen to be installed on the machine.

    The console width is pinned too. Rich reflows a table that does not fit, and a
    table that reflows differently on another terminal is a test that fails for
    reasons that have nothing to do with the code under test.
    """
    from dexatlas.config.settings import get_settings
    from dexatlas.core.models import (
        ApkMetadata,
        ClassKind,
        ClassRef,
        ManifestComponent,
        ManifestInfo,
        ManifestPermission,
        MethodRef,
        MethodReference,
        Project,
        ProjectStatus,
        Provenance,
        StringConstant,
    )
    from dexatlas.core.storage import Store

    monkeypatch.setenv("COLUMNS", "200")

    store = Store.open(get_settings().database_path)
    project = Project(
        id=Project.new_id(SEEDED_SHA256),
        apk=ApkMetadata(sha256=SEEDED_SHA256, size_bytes=4096, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=2,
        method_count=2,
        reference_count=1,
    )
    manifest = ManifestInfo(
        package="com.example.demo",
        version_code="42",
        version_name="1.4.2",
        min_sdk="24",
        target_sdk="34",
        permissions=[ManifestPermission(name="android.permission.INTERNET")],
        components=[
            ManifestComponent(kind="activity", name="com.example.demo.MainActivity", exported=True),
            ManifestComponent(kind="service", name="com.example.demo.SyncService", exported=False),
            ManifestComponent(
                kind="receiver",
                name="com.example.demo.BootReceiver",
                exported=True,
                permission="android.permission.RECEIVE_BOOT_COMPLETED",
            ),
        ],
    )

    project_workspace = workspace / "projects" / project.id
    sources = project_workspace / "jadx" / "sources" / "com" / "example" / "demo"
    sources.mkdir(parents=True)
    (sources / "MainActivity.java").write_text(SEEDED_JAVA, encoding="utf-8")
    store.save_project(project, project_workspace, manifest)

    provenance = [
        Provenance(
            tool="jadx",
            apk_sha256=SEEDED_SHA256,
            locator="jadx:sources/com/example/demo/MainActivity.java",
        )
    ]
    classes = [
        ClassRef(
            name="com.example.demo.MainActivity",
            kind=ClassKind.CLASS,
            access_flags=["public"],
            method_count=2,
            provenance=provenance,
        ),
        ClassRef(
            name="com.example.demo.SyncService",
            kind=ClassKind.CLASS,
            access_flags=["public"],
            method_count=1,
            provenance=[
                Provenance(
                    tool="jadx",
                    apk_sha256=SEEDED_SHA256,
                    locator="jadx:sources/com/example/demo/SyncService.java",
                )
            ],
        ),
    ]
    methods = [
        MethodRef(
            class_name="com.example.demo.MainActivity",
            name="onCreate",
            descriptor="(Landroid/os/Bundle;)V",
            access_flags=["public"],
            provenance=provenance,
        ),
        MethodRef(
            class_name="com.example.demo.SyncService",
            name="start",
            descriptor="(Ljava/lang/String;)V",
            access_flags=["public", "static"],
            provenance=classes[1].provenance,
        ),
    ]
    references = [
        MethodReference(
            caller="com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V",
            callee="com.example.demo.SyncService.start(Ljava/lang/String;)V",
            kind="invoke",
            provenance=provenance,
        )
    ]
    # Two string constants that share a token, so a search for it matches both and
    # `--limit` has something to cut.
    strings = [
        StringConstant(value="TOKEN_ALPHA", provenance=provenance),
        StringConstant(value="TOKEN_BETA", provenance=provenance),
    ]
    store.save_symbols(project.id, classes, methods, [], references, strings)
    return project.id


@pytest.fixture
def jadx_available(workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the JADX backend discoverable without running JADX.

    ``JadxBackend.resolve`` only checks that the configured path exists, so a stub
    file is enough: the CLI reads the sources the seed fixture wrote and never shells
    out to anything.

    It depends on ``workspace`` so that the workspace fixture's "no backends" setting
    is applied first and this one overrides it, whatever order the test names them in.
    """
    from dexatlas.config.settings import get_settings

    stub = tmp_path / "tools" / "jadx.bat"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEXATLAS_JADX_PATH", str(stub))
    get_settings.cache_clear()


def _printed_method_id(output: str, marker: str) -> str:
    """The method id the CLI printed on the line that names ``marker``."""
    for line in output.splitlines():
        if marker in line:
            match = _METHOD_ID.search(line)
            assert match, f"no method id on the line naming {marker}: {line!r}"
            return match.group(0)
    raise AssertionError(f"no line naming {marker} in:\n{output}")


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


# -- listing what the store holds -------------------------------------------


def test_projects_lists_an_analysed_project(seeded_project: str) -> None:
    result = _run("projects")

    assert result.exit_code == 0
    assert "Projects (1)" in result.stdout
    assert seeded_project in result.stdout
    assert "demo.apk" in result.stdout
    assert "completed" in result.stdout


def test_classes_lists_the_indexed_classes(seeded_project: str) -> None:
    result = _run("classes", seeded_project)

    assert result.exit_code == 0
    assert "com.example.demo.MainActivity" in result.stdout
    assert "com.example.demo.SyncService" in result.stdout
    # A listing without a source is a claim; the provenance line is what makes it
    # checkable.
    assert "jadx -> jadx:sources/com/example/demo/MainActivity.java" in result.stdout


def test_classes_prefix_filters_the_listing(seeded_project: str) -> None:
    result = _run("classes", seeded_project, "--prefix", "com.example.demo.Sync")

    assert result.exit_code == 0
    assert "com.example.demo.SyncService" in result.stdout
    assert "MainActivity" not in result.stdout


def test_classes_limit_caps_the_listing(seeded_project: str) -> None:
    result = _run("classes", seeded_project, "--limit", "1")

    assert result.exit_code == 0
    assert "com.example.demo.MainActivity" in result.stdout
    assert "com.example.demo.SyncService" not in result.stdout


def test_methods_lists_the_indexed_methods(seeded_project: str) -> None:
    result = _run("methods", seeded_project)

    assert result.exit_code == 0
    assert "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V" in result.stdout
    assert "com.example.demo.SyncService.start(Ljava/lang/String;)V" in result.stdout


def test_methods_filters_by_class(seeded_project: str) -> None:
    result = _run("methods", seeded_project, "--class", "com.example.demo.SyncService")

    assert result.exit_code == 0
    assert "com.example.demo.SyncService.start(Ljava/lang/String;)V" in result.stdout
    assert "onCreate" not in result.stdout


def test_methods_limit_caps_the_listing(seeded_project: str) -> None:
    result = _run("methods", seeded_project, "--limit", "1")

    assert result.exit_code == 0
    assert "onCreate" in result.stdout
    assert "SyncService.start" not in result.stdout


def test_search_finds_an_indexed_symbol(seeded_project: str) -> None:
    result = _run("search", seeded_project, "onCreate")

    assert result.exit_code == 0
    assert "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V" in result.stdout
    assert "method" in result.stdout


def test_search_limit_caps_the_results(seeded_project: str) -> None:
    """Both string constants contain the token ``TOKEN``; only one may be shown."""
    result = _run("search", seeded_project, "TOKEN", "--limit", "1")

    assert result.exit_code == 0
    shown = [name for name in ("TOKEN_ALPHA", "TOKEN_BETA") if name in result.stdout]
    assert len(shown) == 1


def test_manifest_shows_the_recorded_manifest(seeded_project: str) -> None:
    import re

    result = _run("manifest", seeded_project)

    assert result.exit_code == 0
    assert "com.example.demo" in result.stdout
    assert "1.4.2" in result.stdout
    assert "min 24 / target 34" in result.stdout
    assert re.search(r"permissions\s+1", result.stdout)
    assert re.search(r"components\s+3", result.stdout)


def test_manifest_lists_only_the_exported_components(seeded_project: str) -> None:
    """An unexported component is not reachable from outside the app, so listing it
    among the exported ones would overstate the attack surface."""
    result = _run("manifest", seeded_project)

    assert result.exit_code == 0
    assert "Exported components" in result.stdout
    assert "com.example.demo.MainActivity" in result.stdout
    assert "com.example.demo.BootReceiver" in result.stdout
    assert "no permission guard" in result.stdout
    assert "android.permission.RECEIVE_BOOT_COMPLETED" in result.stdout
    assert "com.example.demo.SyncService" not in result.stdout


def test_xrefs_lists_the_callers_of_a_method(seeded_project: str) -> None:
    result = _run(
        "xrefs", seeded_project, "com.example.demo.SyncService.start(Ljava/lang/String;)V"
    )

    assert result.exit_code == 0
    assert "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V" in result.stdout
    assert "com.example.demo.SyncService.start(Ljava/lang/String;)V" in result.stdout


# -- source ------------------------------------------------------------------


def test_source_prints_the_decompiled_class(seeded_project: str, jadx_available: None) -> None:
    result = _run("source", seeded_project, "com.example.demo.MainActivity")

    assert result.exit_code == 0
    assert "public class MainActivity" in result.stdout
    # The source is printed as text, not as Rich markup: a decompiled file is full of
    # square brackets, and interpreting them would corrupt every listing.
    assert "[bold]not markup[/bold]" in result.stdout


def test_source_method_option_prints_one_method(seeded_project: str, jadx_available: None) -> None:
    result = _run("source", seeded_project, "com.example.demo.MainActivity", "--method", "onCreate")

    assert result.exit_code == 0
    assert "onCreate" in result.stdout
    assert "onResume" not in result.stdout


def test_source_of_a_class_that_was_never_decompiled(
    seeded_project: str, jadx_available: None
) -> None:
    """The project exists but the class does not — a different situation from an
    unknown project, and it must not crash the command."""
    result = _run("source", seeded_project, "com.example.demo.Missing")

    assert result.exit_code == 1
    assert "No source for com.example.demo.Missing" in result.output


# -- option combinations and error paths -------------------------------------


def test_backends_reports_missing_backends_without_failing(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing backend is a gap in the analysis, not a failure of the tool.

    The command must still exit 0 and still list every backend: the point of the
    report is that the analyst can see what is and is not available.
    """
    # Nothing on PATH, so the not-installed path is the one under test.
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)

    result = _run("backends")

    assert result.exit_code == 0
    assert "jadx" in result.stdout
    assert "apktool" in result.stdout
    assert "not installed" in result.stdout
    assert "backend(s) unavailable" in result.output


def test_analyze_workspace_option_redirects_the_run(
    workspace: Path, tmp_path: Path, not_an_apk: Path
) -> None:
    """``--workspace`` must move the whole run, database included, to another root.

    The APK is rejected on purpose: what is being checked is which workspace the run
    used, and a rejected APK still got as far as creating one.
    """
    elsewhere = tmp_path / "elsewhere"

    result = _run("analyze", str(not_an_apk), "--workspace", str(elsewhere))

    assert result.exit_code == 2
    assert (elsewhere / "dexatlas.db").exists()
    assert not (workspace / "dexatlas.db").exists()


def test_analyze_rejects_a_zip_that_is_not_an_apk(
    workspace: Path, zip_without_android_markers: Path
) -> None:
    """A plain ZIP is a different rejection from a file that is not a ZIP at all."""
    result = _run("analyze", str(zip_without_android_markers))

    assert result.exit_code == 2
    assert "Not a usable APK" in result.output


def test_analyze_reports_an_analysis_that_produced_nothing(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An analysis that yields no symbols and no manifest has failed.

    The exit code says so, and the message says why — a run that quietly exits 0
    with an empty report reads as success.
    """
    # No backend is installed, so nothing can produce a manifest...
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    # ...and the APK carries no bytecode, so nothing can produce a symbol either.
    apk = tmp_path / "no-bytecode.apk"
    with zipfile.ZipFile(apk, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", "<?xml version='1.0'?><manifest/>")
        archive.writestr("resources.arsc", b"\x02\x00\x0c\x00")

    result = _run("analyze", str(apk))

    assert result.exit_code == 1
    assert "Analysis produced no symbols" in result.output


def test_console_entry_point_invokes_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """``main`` is what the console script and ``python -m`` both end up calling.

    If it stopped invoking the app, the command would exit quietly and print
    nothing at all.
    """
    from dexatlas.cli import main as cli_module

    called: list[str] = []
    monkeypatch.setattr(cli_module, "app", lambda: called.append("app"))

    cli_module.main()

    assert called == ["app"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_the_module_entry_point_runs_a_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """``python -m dexatlas.cli.main version`` must work.

    The ``__main__`` guard is the only thing that makes it work, and nothing else in
    the suite exercises it.
    """
    import runpy

    monkeypatch.setattr(sys, "argv", ["dexatlas", "version"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("dexatlas.cli.main", run_name="__main__")

    assert excinfo.value.code == 0


@pytest.mark.slow
def test_an_id_printed_by_methods_resolves_in_xrefs(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The path a user actually takes: copy the id out of `dexatlas methods`, look it
    up in `dexatlas xrefs`.

    The id is taken from what the command printed, not written out by hand. The
    method table and the cross-reference table once spelled the same method
    differently — the method table spaced the argument descriptors, the
    cross-reference table did not — so the id a user could read was the id that
    could not be looked up.
    """
    from dexatlas.tools.androguard.adapter import androguard_available

    demo = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"
    if not demo.is_file():
        pytest.skip("demo APK missing")
    if not androguard_available():
        pytest.skip("androguard not installed")
    # Rich sizes its table to the terminal, and a narrow one truncates the id with
    # an ellipsis — there would be nothing left to copy.
    monkeypatch.setenv("COLUMNS", "200")

    assert _run("analyze", str(demo)).exit_code == 0
    project_id = f"apk_{hashlib.sha256(demo.read_bytes()).hexdigest()[:16]}"

    methods_out = _run("methods", project_id)
    assert methods_out.exit_code == 0
    sign_id = _printed_method_id(methods_out.stdout, "Crypto.sign")
    assert " " not in sign_id, f"the printed id carries whitespace: {sign_id!r}"

    refs = _run("xrefs", project_id, sign_id)
    assert refs.exit_code == 0, f"no callers for {sign_id!r}: {refs.output}"
    assert "MainActivity.onCreate" in refs.stdout
