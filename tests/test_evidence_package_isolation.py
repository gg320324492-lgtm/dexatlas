"""The evidence package carries the analysis, and nothing else.

The package is what a client takes away, so what is in it has to be the
analysis and nothing else. The packager used to copy any file a citation
named out of the decompiler's output directory, and the directory is not a
boundary: a link inside it that points somewhere else is read like a file of
the analysis, and a file that was put in it by something other than the
decompiler is not the analysis either. Both are ways for the operator's own
working material — a review record, a checklist, a document that has not been
published — to travel out with the package.

These tests are the boundary written down: the analysis's own file ships,
anything else does not, and the citation that named it is reported as
unresolved rather than quietly satisfied.
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dexatlas.cli.main import app
from dexatlas.config.settings import get_settings
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Project,
    ProjectStatus,
    Provenance,
)
from dexatlas.core.storage import Store
from dexatlas.reports.evidence_package import verify_citations

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

#: What an internal review record looks like: an internal judgement about the
#: analysis, and something that was never published.
INTERNAL_RECORD = """# Publish review

Internal judgement: the client has not seen the draft of this report and the
form we submit it through does not accept attachments. Do not send this.
"""

#: The internal record's own text, so a test can look for it in the archive
#: rather than for a file name.
INTERNAL_MARKER = "the form we submit it through does not accept attachments"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")
    monkeypatch.setenv("DEXATLAS_APKTOOL_JAR", "")
    get_settings.cache_clear()
    try:
        yield ws
    finally:
        get_settings.cache_clear()


@pytest.fixture
def internal_record(tmp_path: Path) -> Path:
    """An internal review record, outside the analysis entirely."""
    outside = tmp_path / "operator" / "internal"
    outside.mkdir(parents=True)
    record = outside / "publish-review.md"
    record.write_text(INTERNAL_RECORD, encoding="utf-8")
    return record


def _provenance(locator: str) -> list[Provenance]:
    return [
        Provenance(
            tool="jadx",
            tool_version="1.5.2",
            apk_sha256=SHA,
            locator=locator,
        )
    ]


def _build_project(workspace: Path, extra_records: list[tuple[str, Path | None]]) -> str:
    """A published project whose evidence cites the given places.

    Each entry is the locator the evidence names and, where the citation
    points at something that is not the decompiler's own output, the file the
    locator resolves to inside the decompiler's directory.
    """
    from dexatlas.core.evidence import EvidenceBuilder
    from dexatlas.core.models import EvidenceKind, EvidenceLevel
    from dexatlas.core.runs import AnalysisRun, RunCompleteness, RunStatus

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
    tree = project_workspace / "jadx"
    source = tree / "sources" / "com" / "example" / "demo"
    source.mkdir(parents=True)
    (source / "Crypto.java").write_text(JAVA, encoding="utf-8")

    for _locator, planted in extra_records:
        if planted is None:
            continue
        planted.parent.mkdir(parents=True, exist_ok=True)
        if not planted.exists():
            planted.write_text(INTERNAL_RECORD, encoding="utf-8")

    run = AnalysisRun.start(
        PROJECT_ID,
        SHA,
        tool_versions={"jadx": "1.5.2", "androguard": "4.1"},
        workspace=project_workspace,
    )
    staged_path = project_workspace / "staging"
    staged_path.mkdir(parents=True)
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
                provenance=_provenance("jadx:sources/com/example/demo/Crypto.java"),
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
        provenance=_provenance("jadx:sources/com/example/demo/Crypto.java"),
    )
    for locator, _ in extra_records:
        builder.add(
            kind=EvidenceKind.OBSERVATION,
            level=EvidenceLevel.VERIFIED,
            summary="the analysis read a place outside its own output",
            provenance=_provenance(locator),
        )
    staged.save_evidence(PROJECT_ID, builder.build())

    run.status = RunStatus.COMPLETED
    run.completeness = RunCompleteness.COMPLETE
    run.finished_at = run.started_at
    run.duration_seconds = 1.5
    store.save_project(project, project_workspace, manifest=None)
    store.publish_run(project, run, staged_path / "index.db", manifest=None)
    return PROJECT_ID


def _export(project_id: str, target: Path) -> int:
    return runner.invoke(app, ["export", project_id, "--output", str(target)]).exit_code


def _archive_text(target: Path) -> str:
    """Every byte of the archive, decoded: what a client would read."""
    with zipfile.ZipFile(target) as package:
        return "".join(
            package.read(name).decode("utf-8", errors="replace") for name in package.namelist()
        )


# -- the boundary -------------------------------------------------------------


def test_the_decompiler_output_the_evidence_cites_is_packaged(
    workspace: Path, tmp_path: Path
) -> None:
    """The analysis's own file still ships — the boundary is not a wall."""
    project_id = _build_project(workspace, [])
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    with zipfile.ZipFile(target) as package:
        names = set(package.namelist())
    assert "sources/com/example/demo/Crypto.java" in names


def test_a_record_planted_in_the_decompiler_directory_is_not_packaged(
    workspace: Path, tmp_path: Path
) -> None:
    """A file the decompiler did not write does not travel with the package.

    The decompiler writes two trees, ``sources/`` and ``resources/``. A file
    that sits anywhere else in its output directory was put there by something
    else — an operator's note, a review record, a working document — and it
    is not the analysis, so it does not ship.
    """
    project_id = _build_project(
        workspace,
        [
            (
                "jadx:publish-review.md",
                workspace / "projects" / PROJECT_ID / "jadx" / "publish-review.md",
            )
        ],
    )
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    with zipfile.ZipFile(target) as package:
        names = set(package.namelist())
    assert "sources/publish-review.md" not in names
    assert INTERNAL_MARKER not in _archive_text(target)


def test_a_link_out_of_the_analysis_is_not_packaged(
    workspace: Path, tmp_path: Path, internal_record: Path
) -> None:
    """A link inside the tree that points outside it is not the analysis's file.

    The name says ``sources/`` and the file is there, so everything the
    packager could see said "this is a source of the analysis". It is not:
    it is the operator's own record, and the package is what the client
    takes away.
    """
    link = workspace / "projects" / PROJECT_ID / "jadx" / "sources" / "internal-notes.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(internal_record, link)
    except OSError as exc:  # pragma: no cover - a platform without links
        pytest.skip(f"this platform cannot create a symbolic link: {exc}")

    project_id = _build_project(workspace, [("jadx:sources/internal-notes.md", None)])
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    with zipfile.ZipFile(target) as package:
        names = set(package.namelist())
    assert "sources/internal-notes.md" not in names
    assert INTERNAL_MARKER not in _archive_text(target)


def test_a_refused_citation_is_reported_as_unresolved(workspace: Path, tmp_path: Path) -> None:
    """The citation stays in the evidence, and the package says it is unresolved.

    A file that is not packaged is not a citation that was quietly dropped:
    the reader who follows it finds no file, and ``verify_citations`` counts
    it as unresolved instead of pretending the package carries it.
    """
    project_id = _build_project(
        workspace,
        [
            (
                "jadx:publish-review.md",
                workspace / "projects" / PROJECT_ID / "jadx" / "publish-review.md",
            )
        ],
    )
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    with zipfile.ZipFile(target) as package:
        manifest = json.loads(package.read("manifest.json"))
    result = verify_citations(target, manifest)
    assert "jadx:publish-review.md" in result["citations_unresolved"]


def test_every_file_in_the_package_is_the_analysis_and_nothing_else(
    workspace: Path, tmp_path: Path
) -> None:
    """The archive holds the reports, the manifest, and the analysis's own files.

    This is the whole boundary in one assertion: nothing in the archive is a
    file of the machine that ran the analysis.
    """
    project_id = _build_project(
        workspace,
        [
            (
                "jadx:publish-review.md",
                workspace / "projects" / PROJECT_ID / "jadx" / "publish-review.md",
            )
        ],
    )
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    with zipfile.ZipFile(target) as package:
        names = set(package.namelist())
    allowed = {
        "manifest.json",
        "reports/report.json",
        "reports/report.md",
        "reports/report.html",
        "sources/com/example/demo/Crypto.java",
    }
    assert names == allowed
