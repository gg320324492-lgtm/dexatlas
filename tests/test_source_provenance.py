"""Where a source came from, said by the source itself.

The Smali fallback returns bytecode when the decompiler could not reconstruct
a method. A bare string cannot say so: a caller reading it as Java is reading
Dalvik assembly as if it were Java. The document that carries the text carries
the provenance with it, and this file holds that contract down.

The workspaces here are written by the test rather than produced by an
analysis, so the expectations do not depend on which backends the machine
happens to have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.models import ApkMetadata, Project, ProjectStatus, SourceKind
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.storage import Store
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend

FAKE_SHA256 = "b" * 64

CLASS_NAME = "com.example.demo.Crypto"

JAVA_SOURCE = """package com.example.demo;

public class Crypto {
    public static String sign(String a, String b) {
        return a + b;
    }
}
"""

SMALI_SOURCE = """.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;
.source "Crypto.java"


# direct methods
.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    const-string v0, "a"

    return-object v0
.end method
"""


@pytest.fixture
def workspace_with_sources(tmp_path: Path) -> tuple[Path, str]:
    """A workspace holding both representations of one class, and its project row."""
    workspace, project_id = _workspace(tmp_path)
    _write_sources(workspace, project_id, java=True, smali=True)
    return workspace, project_id


@pytest.fixture
def workspace_with_smali_only(tmp_path: Path) -> tuple[Path, str]:
    """A workspace holding the bytecode but none of the decompiled Java.

    This is the case the fallback exists for: the decompiler ran and did
    not manage this class, so the only source left is the bytecode. The
    project records that both backends took part — the fallback is about
    what a backend produced, not about whether it is installed.
    """
    workspace, project_id = _workspace(tmp_path)
    _write_sources(workspace, project_id, java=False, smali=True)
    return workspace, project_id


def _workspace(tmp_path: Path) -> tuple[Path, str]:
    """A workspace with a project row that says both backends took part."""
    workspace = tmp_path / "workspace"
    project_id = Project.new_id(FAKE_SHA256)
    project_dir = workspace / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    store = Store.open(workspace / "dexatlas.db")
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            tool_versions={"jadx": "1.5.2", "apktool": "2.11.1"},
        ),
        project_dir,
        manifest=None,
    )
    return workspace, project_id


def _write_sources(workspace: Path, project_id: str, *, java: bool, smali: bool) -> None:
    """Put the requested representations in the workspace."""
    project_dir = workspace / "projects" / project_id
    if java:
        path = project_dir / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(JAVA_SOURCE, encoding="utf-8")
    if smali:
        path = project_dir / "apktool" / "smali" / "com" / "example" / "demo" / "Crypto.smali"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SMALI_SOURCE, encoding="utf-8")


@pytest.fixture(autouse=True)
def apktool_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the disassembler answer, without running it.

    The source files are already in the workspace; nothing shells out. The
    backend is patched rather than installed so that the test says which
    backend answers instead of depending on what the machine happens to have —
    a suite that only passes where Apktool is installed is a suite that only
    passes on the author's machine.
    """
    monkeypatch.setattr(ApktoolBackend, "resolve", lambda self: Path("apktool-stub"))


@pytest.fixture
def jadx_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the decompiler answer, without running it."""
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("jadx-stub"))


@pytest.fixture
def jadx_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The configuration the Smali fallback exists for."""
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: None)


# -- the document ------------------------------------------------------------


def test_the_java_source_names_the_decompiler(
    workspace_with_sources: tuple[Path, str], jadx_available: None
) -> None:
    workspace, project_id = workspace_with_sources
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    assert document.kind is SourceKind.JAVA
    assert document.text == JAVA_SOURCE
    assert len(document.provenance) == 1
    assert document.provenance[0].tool == "jadx"
    assert document.provenance[0].locator == "jadx:sources/com/example/demo/Crypto.java"


def test_the_smali_fallback_names_the_disassembler(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    """The case that made this necessary: the caller cannot tell from the text
    that this is bytecode."""
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    assert document.kind is SourceKind.SMALI
    assert ".method" in document.text
    assert document.provenance[0].tool == "apktool"
    assert document.tool == "apktool"
    assert document.provenance[0].locator == "apktool:smali/com/example/demo/Crypto.smali"


def test_the_version_is_the_one_the_analysis_recorded(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    """The file on disk was written by the tool that ran then.

    A decompiler upgraded since would otherwise be credited with it, so the
    version is the one the analysis recorded rather than the one installed now.
    """
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    assert document.provenance[0].tool_version == "2.11.1"


def test_the_locator_names_a_place_inside_the_output_tree(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    """A locator that names the machine is worth nothing on another machine."""
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    locator = document.provenance[0].locator
    assert locator.startswith("apktool:")
    assert ":" not in locator[len("apktool:") :]
    assert str(workspace) not in locator


def test_a_method_document_names_its_method(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign")

    assert document is not None
    assert document.kind is SourceKind.SMALI
    assert document.provenance[0].locator == ("apktool:smali/com/example/demo/Crypto.smali#sign")


def test_a_java_method_document_names_its_method(
    workspace_with_sources: tuple[Path, str], jadx_available: None
) -> None:
    workspace, project_id = workspace_with_sources
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign")

    assert document is not None
    assert document.kind is SourceKind.JAVA
    assert document.provenance[0].locator == "jadx:sources/com/example/demo/Crypto.java#sign"


def test_the_old_methods_still_return_text(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    """The existing contract, kept: a caller that only wants the text still
    gets a string, and the text is the same one the document carries."""
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    source = analyzer.class_source(project_id, CLASS_NAME)
    method = analyzer.method_source(project_id, CLASS_NAME, "sign")

    assert isinstance(source, str)
    assert isinstance(method, str)
    assert source == analyzer.class_source_document(project_id, CLASS_NAME).text
    assert method == analyzer.method_source_document(project_id, CLASS_NAME, "sign").text


def test_a_missing_class_has_no_document(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_smali_only
    analyzer = Analyzer(Settings(workspace=workspace))

    assert analyzer.class_source_document(project_id, "com.example.Missing") is None
    assert analyzer.class_source(project_id, "com.example.Missing") is None


# -- which backend's output a source is ---------------------------------------


def test_the_source_is_read_even_when_the_backend_is_no_longer_installed(
    workspace_with_sources: tuple[Path, str], jadx_unavailable: None
) -> None:
    """The question is about the analysis, not about the machine.

    Reading a source file is a matter of reading a file. The workspace holds
    JADX's output whether or not JADX is still installed here, and the
    analysis that wrote it recorded that JADX took part. So the Java is
    still the answer — and asking the machine instead would quietly serve
    the Smali that the decompiler was the fallback for.
    """
    workspace, project_id = workspace_with_sources
    analyzer = Analyzer(Settings(workspace=workspace))

    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    assert document.kind is SourceKind.JAVA
    assert document.text == JAVA_SOURCE


def test_the_output_of_a_backend_that_did_not_run_is_not_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale output tree is not this analysis's output.

    The workspace here holds JADX's Java, but the project records that JADX
    did not take part in the analysis that produced it — so the Java is
    left over from something else, and serving it would attribute one
    analysis's bytes to another.
    """
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("jadx-stub"))
    monkeypatch.setattr(ApktoolBackend, "resolve", lambda self: Path("apktool-stub"))

    workspace = tmp_path / "workspace"
    project_id = Project.new_id(FAKE_SHA256)
    project_dir = workspace / "projects" / project_id

    java = project_dir / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    smali = project_dir / "apktool" / "smali" / "com" / "example" / "demo" / "Crypto.smali"
    smali.parent.mkdir(parents=True)
    smali.write_text(SMALI_SOURCE, encoding="utf-8")

    store = Store.open(workspace / "dexatlas.db")
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            tool_versions={"jadx": None, "apktool": "2.11.1"},
        ),
        project_dir,
        manifest=None,
    )

    analyzer = Analyzer(Settings(workspace=workspace))
    document = analyzer.class_source_document(project_id, CLASS_NAME)

    assert document is not None
    assert document.kind is SourceKind.SMALI
    assert document.provenance[0].tool == "apktool"


# -- the CLI -----------------------------------------------------------------


def _run_cli(*args: str):
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    return CliRunner().invoke(cli, list(args))


def test_the_cli_prints_the_provenance_beside_the_source(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None, monkeypatch
) -> None:
    """stdout stays exactly the source; the provenance goes to stderr.

    A command whose output is piped into a file should put the file in it and
    nothing else.
    """
    workspace, project_id = workspace_with_smali_only
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, CLASS_NAME)
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert result.stdout.strip() == SMALI_SOURCE.strip()
    assert "apktool:smali/com/example/demo/Crypto.smali" in result.stderr


def test_the_cli_can_print_the_document_as_json(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None, monkeypatch
) -> None:
    workspace, project_id = workspace_with_smali_only
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, CLASS_NAME, "--format", "json")
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "smali"
    assert payload["class_name"] == CLASS_NAME
    assert payload["provenance"][0]["tool"] == "apktool"
    assert payload["provenance"][0]["locator"] == "apktool:smali/com/example/demo/Crypto.smali"
    assert payload["text"].strip() == SMALI_SOURCE.strip()


# -- the API -----------------------------------------------------------------


def _client_for(workspace: Path) -> TestClient:
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_the_api_says_which_representation_the_source_is(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_smali_only

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}/classes/{CLASS_NAME}/source")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.text.strip() == SMALI_SOURCE.strip()
    assert response.headers["X-DexAtlas-Source-Kind"] == "smali"
    assert response.headers["X-DexAtlas-Source-Tool"] == "apktool"
    assert response.headers["X-DexAtlas-Source-Locator"] == (
        "apktool:smali/com/example/demo/Crypto.smali"
    )
    assert response.headers["X-DexAtlas-Source-Tool-Version"] == "2.11.1"


def test_the_api_returns_the_document_as_json(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_smali_only

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/classes/{CLASS_NAME}/source", params={"format": "json"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "smali"
    assert body["provenance"][0]["locator"] == "apktool:smali/com/example/demo/Crypto.smali"
    assert body["text"].strip() == SMALI_SOURCE.strip()


def test_the_api_method_source_says_which_representation_it_is(
    workspace_with_smali_only: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_smali_only

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}/methods/{CLASS_NAME}/sign")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["X-DexAtlas-Source-Kind"] == "smali"
    assert response.headers["X-DexAtlas-Source-Locator"] == (
        "apktool:smali/com/example/demo/Crypto.smali#sign"
    )
