"""The offline HTML report: one presentation of the shared analysis model.

Phase 3 M7, red first. The renderer reads the same ``AnalysisResult`` the
Markdown and JSON renderers read — it adds no fact and recomputes none — and
it must never let text that came from the analysed APK run as markup in the
reader's browser.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from dexatlas.core.models import (
    ApkMetadata,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    ManifestComponent,
    ManifestInfo,
    Project,
    ProjectStatus,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.core.runs import AnalysisRun, RunCompleteness, RunStatus
from dexatlas.reports.html_report import render_html
from dexatlas.reports.markdown import render_markdown
from dexatlas.reports.summary import summary_metrics

HOSTILE_SCRIPT = "<script>alert('xss')</script>"
HOSTILE_IMG = "<img src=x onerror=alert(1)>"


class _Audit(HTMLParser):
    """Collects the tags, event handlers and URLs a document actually has."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.event_attributes: list[str] = []
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag.lower())
        for name, value in attrs:
            lowered = name.lower()
            if lowered.startswith("on") and value is not None:
                self.event_attributes.append(lowered)
            if lowered in {"src", "href"} and value is not None:
                self.urls.append(value)


def _project() -> Project:
    project = Project.create(ApkMetadata(sha256="c" * 64, size_bytes=2048, path=Path("demo.apk")))
    project.status = ProjectStatus.COMPLETED
    project.class_count = 1200
    project.method_count = 9400
    project.reference_count = 31000
    project.call_edge_count = 28000
    project.evidence_count = 2
    project.resource_count = 45
    project.duration_seconds = 3.5
    project.tool_versions = {"jadx": "1.5.2", "apktool": "2.11.1", "androguard": None}
    return project


def _verified(summary: str) -> Evidence:
    return Evidence(
        id="E-0001",
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary=summary,
        provenance=[
            Provenance(
                tool="androguard",
                tool_version="4.1",
                apk_sha256="c" * 64,
                locator="androguard:classes.dex#com.example.demo.Crypto",
            )
        ],
    )


def _result(
    evidence: list[Evidence] | None = None,
    manifest: ManifestInfo | None = None,
    errors: list[ToolError] | None = None,
    run: AnalysisRun | None = None,
    latest_attempt_status: ProjectStatus | None = None,
) -> AnalysisResult:
    project = _project()
    project.errors = errors or []
    return AnalysisResult(
        project=project,
        manifest=manifest,
        evidence=evidence if evidence is not None else [_verified("ok")],
        duration_seconds=3.5,
        run=run,
        latest_attempt_status=latest_attempt_status,
    )


def test_the_html_report_prints_the_same_facts_as_the_markdown_report() -> None:
    """One analysis, three renderings, one set of numbers."""
    result = _result()
    page = render_html(result)
    markdown = render_markdown(result)

    assert result.project.id in page
    assert result.project.apk.sha256 in page
    for _name, value in summary_metrics(result):
        assert value in page, f"{value!r} missing from the HTML report"
        assert value in markdown, f"{value!r} missing from the Markdown report"


def test_sample_text_never_becomes_markup() -> None:
    """A hostile summary, component name or tool version renders as text."""
    evidence = [
        _verified(f"string constant {HOSTILE_SCRIPT} found in Crypto.sign"),
        Evidence(
            id="E-0002",
            kind=EvidenceKind.CODE_LOCATED,
            level=EvidenceLevel.VERIFIED,
            summary=f"component {HOSTILE_IMG} is exported",
            provenance=[
                Provenance(
                    tool="jadx",
                    tool_version="1.5.2",
                    apk_sha256="c" * 64,
                    locator="jadx:sources/com/example/demo/Crypto.java",
                )
            ],
        ),
    ]
    manifest = ManifestInfo(
        package="com.example.demo",
        components=[ManifestComponent(kind="activity", name=HOSTILE_IMG, exported=True)],
    )
    project = _project()
    project.tool_versions = {"jadx": HOSTILE_SCRIPT}
    result = AnalysisResult(
        project=project, manifest=manifest, evidence=evidence, duration_seconds=3.5
    )

    page = render_html(result)
    audit = _Audit()
    audit.feed(page)

    assert "script" not in audit.tags, "sample text ran as a <script> element"
    assert "img" not in audit.tags, "sample text ran as an <img> element"
    assert not audit.event_attributes, "sample text installed an event handler"
    # The text survives as text — escaped, readable, inert. The escaped form
    # is what a reader sees; the raw form is what must never appear.
    assert "&lt;script&gt;" in page
    assert "&lt;img" in page
    assert HOSTILE_SCRIPT not in page
    assert HOSTILE_IMG not in page


def test_the_page_is_self_contained_and_offline() -> None:
    """No scripts, no fetched resources: the file renders with no network."""
    page = render_html(_result())
    audit = _Audit()
    audit.feed(page)

    assert not set(audit.tags) & {"script", "iframe", "object", "embed", "link", "img"}
    assert not audit.urls, f"the page fetches something: {audit.urls}"


def test_the_evidence_table_is_capped_like_the_markdown_one() -> None:
    """Two hundred rows shown, the rest named — the same cap as Markdown."""
    evidence = [
        Evidence(
            id=f"E-{index:04d}",
            kind=EvidenceKind.OBSERVATION,
            level=EvidenceLevel.VERIFIED,
            summary=f"record {index}",
            provenance=[],
        )
        for index in range(1, 251)
    ]
    page = render_html(_result(evidence=evidence))

    assert "50 further evidence records omitted" in page
    assert "E-0200" in page
    assert "E-0201" not in page


def test_the_page_names_the_run_and_a_later_attempt() -> None:
    run = AnalysisRun.start("apk_" + "c" * 16, "c" * 64, tool_versions={"jadx": "1.5.2"})
    run.status = RunStatus.COMPLETED
    run.completeness = RunCompleteness.COMPLETE

    page = render_html(_result(run=run, latest_attempt_status=ProjectStatus.FAILED))

    assert run.id in page
    assert "later attempt" in page.lower()
    assert "failed" in page.lower()


def test_backend_errors_are_visible() -> None:
    error = ToolError(tool="jadx", code=ToolErrorCode.TIMEOUT, message="decompilation timed out")

    page = render_html(_result(errors=[error]))

    assert "jadx" in page
    assert "timeout" in page
    assert "timed out" in page


@pytest.mark.slow
def test_analyze_writes_the_html_report(
    tmp_path: Path, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``dexatlas analyze --html`` writes the offline page beside the others."""
    from dexatlas.cli.main import app
    from dexatlas.config.settings import get_settings

    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")
    monkeypatch.setenv("DEXATLAS_APKTOOL_JAR", "")
    get_settings.cache_clear()
    try:
        from typer.testing import CliRunner

        html_out = tmp_path / "out" / "report.html"
        result = CliRunner().invoke(app, ["analyze", str(minimal_apk), "--html", str(html_out)])

        assert result.exit_code in (0, 1)
        assert html_out.exists()
        page = html_out.read_text(encoding="utf-8")
        assert "<html" in page
        assert "DexAtlas" in page
    finally:
        get_settings.cache_clear()
