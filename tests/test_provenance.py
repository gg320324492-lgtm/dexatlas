"""Provenance: where it points, and which build of what it names.

A locator is a pointer. A pointer that only resolves on the machine that wrote
it is not a pointer — it is a note about somebody's disk. So every locator here
names a place *inside an artefact the reader can name too*: the APK itself, or
the output tree a backend wrote. Never an absolute path.

The rule is one rule for every backend: the locator starts with the tool that
produced it, and the rest is relative to the artefact that tool names. A reader
should not have to learn a different convention per backend.

The other half of a provenance record is the version of the tool that produced
it. A record that names a tool without a version cannot be reproduced, and
cannot be told apart from a record where the version was simply never filled
in — so the version is on every record, including the ones that record a
failure.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ApkMetadata,
    ManifestComponent,
    ManifestInfo,
    Project,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer, _record_decompilation
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import ToolOutcome
from dexatlas.tools.jadx.adapter import JadxBackend

APKTOOL_VERSION = "2.11.1"
JADX_VERSION = "1.5.2"

DEMO_JAVA = """package com.example.demo;

public class Crypto {
    public static String sign(String a, String b) {
        return a + b;
    }
}
"""

#: A locator names a path when the path after the tool prefix starts at a root
#: or at a drive letter. Both spellings of a Windows root count, because the
#: machines that produce these locators are not all the same machine.
_ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")


def _is_absolute(locator: str) -> bool:
    """Whether a locator names a path on one particular machine."""
    return bool(_ABSOLUTE_PATH.match(locator.split(":", 1)[-1]))


# -- a single backend --------------------------------------------------------


def _write_jadx_output(tmp_path: Path) -> Path:
    """A JADX output tree, laid out the way JADX lays it out."""
    source = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    source.mkdir(parents=True, exist_ok=True)
    (source / "Crypto.java").write_text(DEMO_JAVA, encoding="utf-8")
    return tmp_path / "jadx"


def test_a_jadx_class_locator_points_inside_the_output_tree(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    """The locator is relative to the directory JADX wrote into.

    An absolute path would name the machine that ran the analysis rather than
    the analysis, and a reader on another machine cannot follow it.
    """
    output = _write_jadx_output(tmp_path)

    classes, error = jadx.extract(
        "a" * 64, output, ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)
    )

    assert error is None
    assert classes[0].provenance[0].locator == "jadx:sources/com/example/demo/Crypto.java"


def test_the_decompilation_coverage_record_points_at_the_sources_tree(tmp_path: Path) -> None:
    """The coverage record is about a whole tree of files, so it names the tree."""
    from dexatlas.core.evidence import EvidenceBuilder

    apk = ApkMetadata(sha256="a" * 64, size_bytes=1, path=Path("demo.apk"))
    project = Project(id="apk_test", apk=apk, tool_versions={"jadx": JADX_VERSION})
    builder = EvidenceBuilder(
        project_id=project.id,
        apk_sha256=apk.sha256,
        tool_versions=project.tool_versions,
    )
    output_dir = tmp_path / "jadx"
    (output_dir / "sources").mkdir(parents=True)

    _record_decompilation(
        builder,
        project=project,
        classes=[],
        methods=[],
        status={"com.example.demo.Crypto": _decompiled_class()},
        output_dir=output_dir,
    )

    assert builder.items[0].provenance[0].locator == "jadx:sources"


def _decompiled_class():
    from dexatlas.tools.jadx.adapter import ClassDecompilation

    return ClassDecompilation(decompiled=frozenset({"sign"}))


# -- locators written by an earlier version ---------------------------------


def test_a_legacy_absolute_jadx_locator_reads_as_a_relative_one() -> None:
    """A workspace analysed before the fix still produces a portable locator.

    The old locator was the absolute path of the file on the machine that ran
    the analysis. Only the tail after the project directory is a fact about the
    analysis; the rest was a fact about the machine.
    """
    legacy = (
        "jadx:C:/Users/admin/AppData/Local/Temp/ws/projects/apk_80a8fe0e81204c9f"
        "/jadx/sources/com/example/demo/Crypto.java"
    )

    provenance = Provenance(
        tool="jadx", tool_version=JADX_VERSION, apk_sha256="a" * 64, locator=legacy
    )

    assert provenance.locator == "jadx:sources/com/example/demo/Crypto.java"


def test_a_legacy_posix_locator_reads_as_a_relative_one() -> None:
    legacy = (
        "jadx:/home/ci/ws/projects/apk_80a8fe0e81204c9f/jadx/sources/com/example/demo/Crypto.java"
    )

    provenance = Provenance(
        tool="jadx", tool_version=JADX_VERSION, apk_sha256="a" * 64, locator=legacy
    )

    assert provenance.locator == "jadx:sources/com/example/demo/Crypto.java"


def test_a_current_locator_is_left_alone() -> None:
    provenance = Provenance(
        tool="jadx",
        tool_version=JADX_VERSION,
        apk_sha256="a" * 64,
        locator="jadx:sources/com/example/demo/Crypto.java",
    )

    assert provenance.locator == "jadx:sources/com/example/demo/Crypto.java"


def test_a_locator_from_another_backend_is_left_alone() -> None:
    locator = "androguard:classes.dex#com.example.demo.Crypto"

    provenance = Provenance(
        tool="androguard", tool_version="4.1.4", apk_sha256="a" * 64, locator=locator
    )

    assert provenance.locator == locator


# -- the whole pipeline ------------------------------------------------------


def _install_fake_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the three backends.

    The pipeline is then driven end to end — manifest, decompilation, evidence —
    with no external tool installed, so the locators it writes can be checked on
    any machine.
    """

    def apktool_resolve(self) -> Path:
        return Path("/fake/apktool.jar")

    def apktool_version(self) -> str | None:
        return APKTOOL_VERSION

    def apktool_decode(self, apk: Path, output_dir: Path) -> ToolOutcome:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "AndroidManifest.xml").write_text("<manifest/>", encoding="utf-8")
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    def apktool_read_manifest(self, output_dir: Path):
        return (
            ManifestInfo(
                package="com.example.demo",
                version_name="1.0",
                components=[
                    ManifestComponent(
                        kind="activity", name="com.example.demo.MainActivity", exported=True
                    )
                ],
            ),
            None,
        )

    def jadx_resolve(self) -> Path:
        return Path("/fake/jadx.bat")

    def jadx_version(self) -> str | None:
        return JADX_VERSION

    def jadx_decompile(
        self, apk: Path, output_dir: Path, *, timeout: int | None = None
    ) -> ToolOutcome:
        source = output_dir / "sources" / "com" / "example" / "demo"
        source.mkdir(parents=True, exist_ok=True)
        (source / "Crypto.java").write_text(DEMO_JAVA, encoding="utf-8")
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    def androguard_extract(self, apk: Path, apk_sha256: str, **kwargs):
        return [], [], [], [], [], None

    monkeypatch.setattr(ApktoolBackend, "resolve", apktool_resolve)
    monkeypatch.setattr(ApktoolBackend, "version", apktool_version)
    monkeypatch.setattr(ApktoolBackend, "decode", apktool_decode)
    monkeypatch.setattr(ApktoolBackend, "read_manifest", apktool_read_manifest)
    monkeypatch.setattr(JadxBackend, "resolve", jadx_resolve)
    monkeypatch.setattr(JadxBackend, "version", jadx_version)
    monkeypatch.setattr(JadxBackend, "decompile", jadx_decompile)
    monkeypatch.setattr(
        "dexatlas.tools.androguard.adapter.AndroguardBackend.extract", androguard_extract
    )


def _analyse(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, apk: Path):
    _install_fake_backends(monkeypatch)
    analyzer = Analyzer(Settings(workspace=tmp_path / "workspace"))
    return analyzer, analyzer.analyze(apk)


def test_an_analysis_writes_no_machine_specific_locator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_apk: Path
) -> None:
    """No locator may name a path on the machine that produced it.

    This is the whole defect: the report is read on another machine, and an
    absolute path there points at nothing.
    """
    result = _analyse(monkeypatch, tmp_path, minimal_apk)[1]

    locators = [p.locator for evidence in result.evidence for p in evidence.provenance]
    assert locators, "the analysis recorded no evidence at all"
    for locator in locators:
        assert not _is_absolute(locator), f"{locator!r} names a path on this machine"


def test_every_locator_names_the_tool_that_produced_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_apk: Path
) -> None:
    """One convention for every backend: the tool, then the place.

    A reader should not have to learn a different rule per backend to follow a
    pointer back to the code.
    """
    result = _analyse(monkeypatch, tmp_path, minimal_apk)[1]

    for evidence in result.evidence:
        for provenance in evidence.provenance:
            assert provenance.locator.startswith(f"{provenance.tool}:"), (
                f"{provenance.tool} wrote {provenance.locator!r}, which does not name it"
            )


def test_the_jadx_locator_names_the_file_inside_the_output_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_apk: Path
) -> None:
    analyzer, result = _analyse(monkeypatch, tmp_path, minimal_apk)

    locators = {p.locator for evidence in result.evidence for p in evidence.provenance}
    assert "jadx:sources" in locators
    assert "apktool:AndroidManifest.xml#/application" in locators

    # The class index is where a decompiled file is named: the evidence table
    # holds conclusions, and this file is the source one of them came from.
    classes = analyzer.store.list_classes(result.project.id)
    class_locators = {p.locator for cls in classes for p in cls.provenance}
    assert "jadx:sources/com/example/demo/Crypto.java" in class_locators


# -- the version of the tool that produced the evidence ----------------------


def test_the_exported_components_evidence_carries_the_apktool_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_apk: Path
) -> None:
    """The version has to reach the evidence, not stop at the project record.

    The project knows which tools took part in the analysis. The evidence is
    what a reader follows, so the version has to be on the evidence too — and
    the manifest evidence beside it already carries one.
    """
    result = _analyse(monkeypatch, tmp_path, minimal_apk)[1]

    exported = [item for item in result.evidence if "exported" in item.summary]
    assert exported, "the analysis recorded no exported-component evidence"
    assert exported[0].provenance[0].tool_version == APKTOOL_VERSION


def test_a_failed_backend_is_evidence_and_carries_the_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_apk: Path
) -> None:
    """A failure is evidence, so it names the build of the tool that failed."""
    from dexatlas.core.models import ToolError, ToolErrorCode

    def failing_decompile(
        self, apk: Path, output_dir: Path, *, timeout: int | None = None
    ) -> ToolOutcome:
        return ToolOutcome(
            returncode=1,
            stdout="",
            stderr="boom",
            duration_seconds=0.0,
            error=ToolError(
                tool="jadx",
                code=ToolErrorCode.EXIT_NONZERO,
                message="jadx exited with code 1",
            ),
        )

    _install_fake_backends(monkeypatch)
    monkeypatch.setattr(JadxBackend, "decompile", failing_decompile)
    analyzer = Analyzer(Settings(workspace=tmp_path / "workspace"))

    result = analyzer.analyze(minimal_apk)

    failures = [item for item in result.evidence if "did not complete" in item.summary]
    assert failures, "the failed backend produced no evidence"
    assert failures[0].provenance[0].tool_version == JADX_VERSION
