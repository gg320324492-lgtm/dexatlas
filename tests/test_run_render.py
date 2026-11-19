"""``dexatlas runs`` and ``dexatlas render``: reading one run back.

The CLI never had a way to look at one particular run: a new analysis
replaced the project's published one, and the previous run's evidence was
gone from the command line the moment the next run finished (M10 reader
rehearsal, finding #9 — C8). These tests hold the new commands to their
contract:

* ``runs`` lists a project's attempts and shows one run's own record;
* ``render`` writes a completed, still-published run's reports, evidence
  package and record to a directory, reading the workspace and nothing else;
* the exit codes are the documented ones, borrowed and not re-invented: a
  wrong request (no such project or run, an output that is not empty) is 2,
  an empty answer (a project with no runs) is 1, and a render that fails is 3;
* a run that is no longer the published one does not render — its snapshot
  has been replaced, and a report that wore its name while describing a
  newer snapshot would be evidence mislabelled.
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dexatlas.cli.main import EXIT_BAD_REQUEST, EXIT_EMPTY, app
from dexatlas.config.settings import get_settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    EvidenceKind,
    EvidenceLevel,
    Project,
    ProjectStatus,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.runs import AnalysisRun, RunCompleteness, RunStatus
from dexatlas.core.storage import Store
from dexatlas.reports.evidence_package import verify_package

runner = CliRunner()

SHA = "0123456789abcdef" * 4
PROJECT_ID = Project.new_id(SHA)
JAVA = """package com.example.demo;

public class Crypto {
    public static String sign(String key) {
        return key;
    }
}
"""


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")
    monkeypatch.setenv("DEXATLAS_APKTOOL_JAR", "")
    # Rich reflows a table that does not fit the console; pin the width so a
    # 20-character run id is never truncated out of the captured output.
    monkeypatch.setenv("COLUMNS", "200")
    get_settings.cache_clear()
    try:
        yield ws
    finally:
        get_settings.cache_clear()


def _provenance() -> list[Provenance]:
    return [
        Provenance(
            tool="jadx",
            tool_version="1.5.2",
            apk_sha256=SHA,
            locator="jadx:sources/com/example/demo/Crypto.java",
        )
    ]


def _publish_run(
    workspace: Path,
    *,
    run_id: str | None = None,
    status: RunStatus = RunStatus.COMPLETED,
    with_error: bool = False,
) -> AnalysisRun:
    """Publish one run for the project, the way a real analysis ends.

    The seeding stages the snapshot in a database of its own and publishes
    it in one transaction — the two steps the pipeline takes — so the render
    reads a snapshot that was really published, not a half-written one.
    """
    store = Store.open(get_settings().database_path)
    project = Project(
        id=PROJECT_ID,
        apk=ApkMetadata(sha256=SHA, size_bytes=4096, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=1,
        method_count=1,
        reference_count=0,
        evidence_count=1,
        tool_versions={"jadx": "1.5.2", "androguard": "4.1"},
    )
    project_workspace = workspace / "projects" / PROJECT_ID
    source = project_workspace / "jadx" / "sources" / "com" / "example" / "demo"
    source.mkdir(parents=True, exist_ok=True)
    (source / "Crypto.java").write_text(JAVA, encoding="utf-8")

    run = AnalysisRun.start(
        PROJECT_ID,
        SHA,
        tool_versions={"jadx": "1.5.2", "androguard": "4.1"},
        workspace=project_workspace,
    )
    if run_id is not None:
        run.id = run_id

    staged_path = project_workspace / f"staging-{run.id}"
    staged_path.mkdir(parents=True, exist_ok=True)
    staged = Store.open(staged_path / "index.db")
    staged.save_project(project, project_workspace, manifest=None)
    staged.save_symbols(
        PROJECT_ID,
        [
            ClassRef(
                name="com.example.demo.Crypto",
                kind=ClassKind.CLASS,
                access_flags=["public"],
                method_count=1,
                provenance=_provenance(),
            )
        ],
        [],
        [],
        [],
        [],
    )
    builder = EvidenceBuilder(
        project_id=PROJECT_ID,
        tool_versions={"jadx": "1.5.2", "androguard": "4.1"},
        apk_sha256=SHA,
        workspace=project_workspace,
        dex_files=["classes.dex"],
    )
    builder.add(
        kind=EvidenceKind.DECLARATION,
        level=EvidenceLevel.VERIFIED,
        summary="the analysed class was decompiled",
        provenance=_provenance(),
    )
    staged.save_evidence(PROJECT_ID, builder.build())

    run.status = status
    run.completeness = RunCompleteness.PARTIAL if with_error else RunCompleteness.COMPLETE
    if with_error:
        run.errors = [
            ToolError(
                tool="jadx",
                code=ToolErrorCode.NOT_INSTALLED,
                message="jadx is not installed or not on PATH",
            )
        ]
    run.finished_at = run.started_at
    run.duration_seconds = 1.5
    store.save_project(project, project_workspace, manifest=None)
    if status is RunStatus.COMPLETED:
        store.publish_run(project, run, staged_path / "index.db", manifest=None)
    else:
        # A run that did not complete published nothing; its record still
        # exists, which is what `runs --run` reads back.
        store.create_run(run)
    return run


@pytest.fixture
def published_run(workspace: Path) -> AnalysisRun:
    """One completed, published run."""
    return _publish_run(workspace)


# ---------------------------------------------------------------------------
# dexatlas runs
# ---------------------------------------------------------------------------


def test_runs_lists_the_project_runs(published_run: AnalysisRun) -> None:
    result = runner.invoke(app, ["runs", PROJECT_ID])

    assert result.exit_code == 0, result.output
    assert published_run.id in result.stdout
    assert "published" in result.stdout.lower()


def test_runs_on_a_project_without_runs_is_empty(workspace: Path) -> None:
    """A project id that names a project with no runs is an empty answer, not a lie."""
    store = Store.open(get_settings().database_path)
    project = Project(
        id=PROJECT_ID,
        apk=ApkMetadata(sha256=SHA, size_bytes=4096, path=Path("demo.apk")),
        status=ProjectStatus.PENDING,
    )
    store.save_project(project, workspace / "projects" / PROJECT_ID, manifest=None)

    result = runner.invoke(app, ["runs", PROJECT_ID])

    assert result.exit_code == EXIT_EMPTY


def test_runs_of_an_unknown_project_is_a_wrong_request(workspace: Path) -> None:
    result = runner.invoke(app, ["runs", "apk_nope"])

    assert result.exit_code == EXIT_BAD_REQUEST


def test_runs_shows_one_runs_record_with_its_errors(workspace: Path) -> None:
    """A failed run's own record is readable after the fact.

    This is the M10 rehearsal's finding #9: the error was recorded, and now
    a command reads it back instead of leaving it on a stdout nobody kept.
    """
    run = _publish_run(workspace, status=RunStatus.FAILED, with_error=True)
    assert run.errors, "the seeded run carries no error to read back"

    result = runner.invoke(app, ["runs", PROJECT_ID, "--run", run.id])

    assert result.exit_code == 0, result.output
    assert run.id in result.stdout
    assert run.errors[0].code.value in result.output
    assert "published" in result.stdout


def test_runs_rejects_an_unknown_run_id(published_run: AnalysisRun) -> None:
    result = runner.invoke(app, ["runs", PROJECT_ID, "--run", "run_0000000000000000"])

    assert result.exit_code == EXIT_BAD_REQUEST


# ---------------------------------------------------------------------------
# dexatlas render
# ---------------------------------------------------------------------------


def _render(tmp_path: Path, run_id: str) -> Path:
    target = tmp_path / "render"
    result = runner.invoke(app, ["render", PROJECT_ID, run_id, "--output", str(target)])
    assert result.exit_code == 0, result.output
    return target


def test_render_writes_reports_package_and_record(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    target = _render(tmp_path, published_run.id)

    names = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert "run.json" in names
    assert "evidence/evidence-package.zip" in names

    package = zipfile.ZipFile(target / "evidence" / "evidence-package.zip")
    packaged = set(package.namelist())
    assert {
        "reports/report.md",
        "reports/report.json",
        "reports/report.html",
        "manifest.json",
    } <= packaged

    record = json.loads((target / "run.json").read_text(encoding="utf-8"))
    assert record["run_id"] == published_run.id
    assert record["project_id"] == PROJECT_ID
    assert record["apk_sha256"] == SHA
    assert record["status"] == "completed"
    assert record["tool_versions"]["jadx"] == "1.5.2"
    assert record["duration_seconds"] == 1.5

    report = json.loads(package.read("reports/report.json"))
    assert report["run"]["id"] == published_run.id


def test_render_output_names_the_run_it_describes(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    """The rendered markdown names the run, so a reader knows whose report it holds."""
    target = _render(tmp_path, published_run.id)

    markdown = (target / "evidence").exists()
    assert markdown
    with zipfile.ZipFile(target / "evidence" / "evidence-package.zip") as archive:
        report_md = archive.read("reports/report.md").decode("utf-8")
    assert published_run.id in report_md


def test_render_package_verifies_after_the_render(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    """The render's own verification ran; the package a reader picks up passes too."""
    target = _render(tmp_path, published_run.id)

    manifest = verify_package(target / "evidence" / "evidence-package.zip")
    assert manifest["project_id"] == PROJECT_ID
    assert manifest["run_id"] == published_run.id


def test_render_refuses_a_run_that_is_not_published(workspace: Path, tmp_path: Path) -> None:
    """A replaced run's snapshot is gone; rendering it would mislabel a report.

    The project's tables hold the *published* run's rows. A later run that
    replaced it leaves the older run's record readable (``runs --run``), but
    there is no snapshot of its own left to render — and a report that named
    the older run while describing the newer snapshot would be evidence
    wearing the wrong attempt's name.
    """
    first = _publish_run(workspace)
    second = _publish_run(workspace)

    assert first.id != second.id
    target = tmp_path / "render-old"
    result = runner.invoke(app, ["render", PROJECT_ID, first.id, "--output", str(target)])

    assert result.exit_code == EXIT_BAD_REQUEST
    assert not target.exists() or not any(target.iterdir()), (
        "a refused render leaves nothing behind"
    )


def test_render_refuses_a_run_that_published_nothing(workspace: Path, tmp_path: Path) -> None:
    """A failed run has a record but no snapshot; the render says so."""
    run = _publish_run(workspace, status=RunStatus.FAILED, with_error=True)

    target = tmp_path / "render-failed"
    result = runner.invoke(app, ["render", PROJECT_ID, run.id, "--output", str(target)])

    assert result.exit_code == EXIT_BAD_REQUEST
    assert "failed" in result.output.lower()


def test_render_refuses_an_empty_output_directory(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    """A render writes a self-contained directory; it does not mix into one."""
    target = tmp_path / "render"
    target.mkdir()
    (target / "already-here.txt").write_text("not empty", encoding="utf-8")

    result = runner.invoke(app, ["render", PROJECT_ID, published_run.id, "--output", str(target)])

    assert result.exit_code == EXIT_BAD_REQUEST
    assert (target / "already-here.txt").read_text(encoding="utf-8") == "not empty"


def test_render_of_an_unknown_run_is_a_wrong_request(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    target = tmp_path / "render"

    result = runner.invoke(
        app, ["render", PROJECT_ID, "run_0000000000000000", "--output", str(target)]
    )

    assert result.exit_code == EXIT_BAD_REQUEST
    assert not target.exists()


def test_render_of_an_unknown_project_is_a_wrong_request(
    published_run: AnalysisRun, tmp_path: Path
) -> None:
    target = tmp_path / "render"

    result = runner.invoke(app, ["render", "apk_nope", published_run.id, "--output", str(target)])

    assert result.exit_code == EXIT_BAD_REQUEST
    assert not target.exists()


def test_render_is_read_only_over_the_workspace(
    published_run: AnalysisRun, tmp_path: Path, workspace: Path
) -> None:
    """A render reads the workspace and writes only its own output directory.

    The workspace database's mtime is the one a re-analysis would move; a
    render that touched it would be an analysis by side effect.
    """
    database = get_settings().database_path
    before = database.stat().st_mtime_ns

    target = _render(tmp_path, published_run.id)

    assert database.stat().st_mtime_ns == before
    assert target.is_dir()


@pytest.fixture
def render_target(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path / "render"


def test_render_summary_names_what_was_written(published_run: AnalysisRun, tmp_path: Path) -> None:
    target = tmp_path / "render"
    result = runner.invoke(app, ["render", PROJECT_ID, published_run.id, "--output", str(target)])

    assert result.exit_code == 0
    assert published_run.id in result.stdout
    assert "evidence-package.zip" in result.stdout
