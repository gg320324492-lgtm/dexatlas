"""The minimal evidence package: an export a client can carry away and check.

Phase 3 M7, red first. The package is explicit — nothing leaves the workspace
unless ``dexatlas export`` asked for it — and everything in it is verified
against the run it claims to come from. The client's APK, the full sources and
strings the analysis did not use do not go in; what is missing is named as
missing rather than implied to be present.
"""

from __future__ import annotations

import hashlib
import json
import shutil
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
    ManifestComponent,
    ManifestInfo,
    Project,
    ProjectStatus,
    Provenance,
)
from dexatlas.core.storage import Store
from dexatlas.reports.evidence_package import (
    PACKAGE_SCHEMA_VERSION,
    EvidencePackageError,
    verify_citations,
    verify_package,
)

runner = CliRunner()

SHA = "0123456789abcdef" * 4
PROJECT_ID = Project.new_id(SHA)
HOSTILE_SUMMARY = "<script>alert('xss')</script> in Crypto.sign"
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
    get_settings.cache_clear()
    try:
        yield ws
    finally:
        get_settings.cache_clear()


@pytest.fixture
def project_id(workspace: Path) -> str:
    """A completed project with one source file and one evidence record."""
    from dexatlas.core.evidence import EvidenceBuilder
    from dexatlas.core.models import ClassKind, EvidenceKind, EvidenceLevel
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
    manifest = ManifestInfo(
        package="com.example.demo",
        version_code="42",
        version_name="1.4.2",
        components=[
            ManifestComponent(kind="activity", name="com.example.demo.MainActivity", exported=True)
        ],
    )
    project_workspace = workspace / "projects" / PROJECT_ID
    source = project_workspace / "jadx" / "sources" / "com" / "example" / "demo"
    source.mkdir(parents=True)
    (source / "Crypto.java").write_text(JAVA, encoding="utf-8")

    provenance = [
        Provenance(
            tool="jadx",
            tool_version="1.5.2",
            apk_sha256=SHA,
            locator="jadx:sources/com/example/demo/Crypto.java",
        ),
        Provenance(
            tool="androguard",
            tool_version="4.1",
            apk_sha256=SHA,
            locator="androguard:classes.dex#com.example.demo.Crypto",
        ),
    ]

    # Stage the run's snapshot in a database of its own, then publish it —
    # the same two steps a real analysis takes, so the export reads the
    # published snapshot and not a half-written one.
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
                provenance=provenance,
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
        summary=f"exported activity com.example.demo.MainActivity; {HOSTILE_SUMMARY}",
        provenance=provenance,
    )
    # The coverage observation a real analysis always writes: its provenance
    # names the decompiler's whole output tree (``jadx:sources``), not one
    # file — the same record the pipeline's ``_record_decompilation`` adds.
    builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="jadx produced real Java for 1 of 1 methods in 1 of 1 classes",
        provenance=[
            Provenance(
                tool="jadx",
                tool_version="1.5.2",
                apk_sha256=SHA,
                locator="jadx:sources",
            )
        ],
    )
    staged.save_evidence(PROJECT_ID, builder.build())

    run.status = RunStatus.COMPLETED
    run.completeness = RunCompleteness.COMPLETE
    run.finished_at = run.started_at
    run.duration_seconds = 1.5
    store.save_project(project, project_workspace, manifest=None)
    store.publish_run(project, run, staged_path / "index.db", manifest)
    return PROJECT_ID


def _export(project_id: str, target: Path, *extra: str) -> int:
    result = runner.invoke(app, ["export", project_id, "--output", str(target), *extra])
    return result.exit_code


# -- the package itself ------------------------------------------------------


def test_build_writes_a_zip_with_manifest_and_reports(project_id: str, tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    package = zipfile.ZipFile(target)
    names = set(package.namelist())
    assert "manifest.json" in names
    assert "reports/report.json" in names
    assert "reports/report.md" in names
    assert "reports/report.html" in names
    assert any(name.startswith("sources/") for name in names)

    manifest = json.loads(package.read("manifest.json"))
    assert manifest["schema_version"] == PACKAGE_SCHEMA_VERSION
    assert manifest["project_id"] == project_id
    assert manifest["apk_sha256"] == SHA
    assert manifest["run_id"]
    assert manifest["tool_versions"]["jadx"] == "1.5.2"
    assert manifest["package_generated_at"]
    # The manifest is a checklist: every file it lists is in the archive, and
    # every file in the archive (but the manifest itself) is listed.
    files = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    assert "manifest.json" not in files
    for path, sha in files.items():
        assert path in names, f"{path} is listed but not packaged"
        assert hashlib.sha256(package.read(path)).hexdigest() == sha
    for name in names - {"manifest.json"}:
        assert name in files, f"{name} is packaged but not listed"


def test_no_local_paths_inside_the_package(project_id: str, tmp_path: Path) -> None:
    """The package locates everything relatively: no machine path travels in it."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    package = zipfile.ZipFile(target)
    manifest = package.read("manifest.json").decode("utf-8")
    assert str(tmp_path) not in manifest
    for name in package.namelist():
        assert "\\" not in name, f"{name} carries a Windows separator"
        assert not name.startswith(("/", "C:", "G:")), f"{name} is an absolute path"
    for report_name in ("reports/report.json", "reports/report.md"):
        text = package.read(report_name).decode("utf-8")
        assert str(tmp_path) not in text, f"{report_name} leaks the workspace path"


def test_the_clients_apk_and_the_whole_source_tree_stay_out(
    project_id: str, tmp_path: Path
) -> None:
    """The package is evidence, not a copy of the analysis: only cited fragments ship."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    package = zipfile.ZipFile(target)
    names = package.namelist()
    assert not any(name.endswith(".apk") for name in names)
    # Only the source a locator names is packaged, and it is not under the
    # decompiler's tree name — the package's tree is the package's own.
    sources = [name for name in names if name.startswith("sources/")]
    assert sources == ["sources/com/example/demo/Crypto.java"]

    manifest = json.loads(package.read("manifest.json"))
    assert manifest["not_included"] == {
        "apk": "the analysed APK is not packaged; identify it by its SHA-256",
        "full_sources": "only the source fragments the evidence cites are packaged",
        "unrelated_strings": "string constants that no evidence record cites are not packaged",
    }


def test_hostile_text_travels_as_data_never_as_markup(project_id: str, tmp_path: Path) -> None:
    """Sample text is content, and content is escaped wherever it is rendered."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    package = zipfile.ZipFile(target)
    html = package.read("reports/report.html").decode("utf-8")
    assert "<script>" not in html
    # The text travels as data: escaped in the HTML, still readable, never markup.
    assert "alert" in html  # the text is readable, just inert
    assert HOSTILE_SUMMARY not in html


def test_verification_passes_on_a_fresh_package(project_id: str, tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    manifest = verify_package(target)
    assert manifest["apk_sha256"] == SHA


# -- what a reader can do with it ---------------------------------------------


def test_key_citations_resolve_after_the_package_moves(project_id: str, tmp_path: Path) -> None:
    """Copy the package elsewhere; every packaged citation still resolves."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    elsewhere = tmp_path / "moved" / "client-copy.zip"
    elsewhere.parent.mkdir(parents=True)
    shutil.copy2(target, elsewhere)
    assert elsewhere != target

    manifest = verify_package(elsewhere)
    report = verify_citations(elsewhere, manifest)
    assert report["citations_resolved"] is True
    assert report["citations_unresolved"] == []


def test_a_bare_tree_citation_does_not_count_as_unresolved(project_id: str, tmp_path: Path) -> None:
    """The coverage observation cites the whole JADX tree, not a file.

    ``jadx:sources`` names where the decompiler's output lives; the package
    states that the full tree is deliberately absent. It is a citation that
    resolves by construction, like a DEX locator — not a missing file. The
    real pipeline always writes this record, so a package from a real
    analysis must still verify as fully resolved.
    """
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    manifest = verify_package(target)
    report = verify_citations(target, manifest)
    assert report["citations_unresolved"] == []
    assert report["citations_resolved"] is True


def test_a_bare_tree_citation_is_unresolved_without_the_exception(
    project_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red guard: without the bare-tree rule, ``jadx:sources`` reads as unresolved.

    The exception is not cosmetic — this test re-runs the check with the rule
    removed and shows the citation land in ``citations_unresolved``, which is
    exactly the false failure the real rehearsal hit.
    """
    from dexatlas.reports import evidence_package as module

    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    manifest = verify_package(target)
    monkeypatch.setattr(module, "_BARE_TREE_LOCATORS", frozenset())
    report = module.verify_citations(target, manifest)
    assert "jadx:sources" in report["citations_unresolved"]
    assert report["citations_resolved"] is False


def test_a_tampered_file_is_refused(project_id: str, tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0

    package = zipfile.ZipFile(target)
    payload = {name: package.read(name) for name in package.namelist()}
    payload["reports/report.md"] = payload["reports/report.md"] + b"tampered\n"
    package.close()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rewritten:
        for name, data in payload.items():
            rewritten.writestr(name, data)

    with pytest.raises(EvidencePackageError, match="sha256"):
        verify_package(target)


def test_a_traversal_entry_name_is_refused(project_id: str, tmp_path: Path) -> None:
    """An archive whose names climb out of the package is not a package."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0
    package = zipfile.ZipFile(target)
    payload = {name: package.read(name) for name in package.namelist()}
    package.close()

    # Build the attack by hand: the exporter never writes this, so the check
    # has to hold for a package somebody else made and renamed.
    payload["manifest.json"] = json.dumps(
        {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "project_id": project_id,
            "apk_sha256": SHA,
            "run_id": "run_deadbeefdeadbeef",
            "package_generated_at": "2026-11-15T00:00:00+00:00",
            "tool_versions": {},
            "files": [
                {
                    "path": "../escape.txt",
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                    "bytes": 1,
                    "role": "evidence_source",
                }
            ],
            "not_included": {},
        }
    ).encode("utf-8")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rewritten:
        for name, data in payload.items():
            rewritten.writestr(name, data)

    with pytest.raises(EvidencePackageError, match=r"traversal|relative|disagree"):
        verify_package(target)


def test_a_package_bound_to_another_project_is_refused(project_id: str, tmp_path: Path) -> None:
    """A package whose hash does not match the project it names is rejected."""
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0
    package = zipfile.ZipFile(target)
    payload = {name: package.read(name) for name in package.namelist()}
    package.close()

    manifest = json.loads(payload["manifest.json"])
    manifest["apk_sha256"] = "f" * 64  # a different sample's hash
    payload["manifest.json"] = json.dumps(manifest).encode("utf-8")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rewritten:
        for name, data in payload.items():
            rewritten.writestr(name, data)

    with pytest.raises(EvidencePackageError, match=r"bound|sha256|project"):
        verify_package(target)


def test_export_refuses_an_unknown_project(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["export", "apk_nosuchproject", "--output", str(tmp_path / "x.zip")]
    )
    assert result.exit_code == 2


def test_export_declares_the_shared_schema(project_id: str, tmp_path: Path) -> None:
    """The manifest's schema version is a number a reader can check against."""
    assert isinstance(PACKAGE_SCHEMA_VERSION, int)
    target = tmp_path / "pkg" / "evidence.zip"
    assert _export(project_id, target) == 0
    manifest = json.loads(zipfile.ZipFile(target).read("manifest.json"))
    assert manifest["schema_version"] == PACKAGE_SCHEMA_VERSION


# -- the store a fixture touched ----------------------------------------------


def test_a_class_reference_survives_the_round_trip(project_id: str) -> None:
    """The evidence the package cites is the evidence the store holds."""
    store = Store.open(get_settings().database_path)
    assert store.get_project(project_id) is not None
    classes = store.list_classes(project_id)
    assert [c.name for c in classes] == ["com.example.demo.Crypto"]
    assert classes[0].kind is ClassKind.CLASS
