"""Run stage facts (Phase 5 W2): the pipeline's progression, made readable.

The analysis page's stage timeline used to be approximated by the front end,
because the runs contract said only how a run *ended*. These tests hold the
new, additive part of the contract in place:

- A completed run records the pipeline's stages, in the order the pipeline
  reaches them, with monotonically non-decreasing timestamps.
- The same facts survive a round trip through the workspace database.
- The stages are visible on the two read paths the transports expose: the
  REST API's ``RunResponse`` and the workbench's ``RunSummary``.
- The instrumentation changes nothing about the analysis itself: the same
  APK, analysed with stage recording on or off, yields the same project row.

The DEX reader is patched and the two external backends are left out, so
none of these tests needs a decompiler installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.config.settings import Settings
from dexatlas.core.models import ProjectStatus
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import RunStage
from dexatlas.core.storage import SCHEMA_VERSION, Store
from dexatlas.tools.androguard.adapter import AndroguardBackend
from tests.test_analysis_runs import _patch_dex_reader

#: The stages a full run goes through, in pipeline order.
PIPELINE_ORDER = [
    RunStage.INSPECT,
    RunStage.PARSE_APKTOOL,
    RunStage.INDEX_ANDROGUARD,
    RunStage.DECOMPILE_JADX,
    RunStage.PUBLISH,
]


def _stages_of(run) -> list[str]:
    return [event.stage.value for event in run.stages]


def _timestamps_of(run) -> list[str]:
    moments: list[str] = []
    for event in run.stages:
        moments.append(event.started_at.isoformat())
        if event.finished_at is not None:
            moments.append(event.finished_at.isoformat())
    return moments


# ---------------------------------------------------------------------------
# The run model and its persistence
# ---------------------------------------------------------------------------


def test_a_completed_run_records_the_pipeline_stages_in_order(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A finished run says which stages the pipeline went through, in order."""
    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")
    analyzer = Analyzer(settings)

    result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)

    run = result.run
    assert run is not None
    assert _stages_of(run) == [
        "inspect",
        "index-androguard",
        "publish",
    ], "a run without the two external backends skips exactly their stages"
    for event in run.stages:
        assert event.finished_at is not None, "a completed run left no stage open"
        assert event.finished_at >= event.started_at
    assert _timestamps_of(run) == sorted(_timestamps_of(run)), "timestamps are monotonic"


def test_a_completed_run_with_every_backend_records_five_stages(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With all backends enabled the run carries all five stages, in order.

    The two external backends are patched at the adapter seam — the same
    objects the pipeline calls — so the run walks the full pipeline without
    either tool being installed.
    """
    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")

    from dexatlas.tools.apktool.adapter import ApktoolBackend
    from dexatlas.tools.base import ToolOutcome
    from dexatlas.tools.jadx.adapter import JadxBackend

    def decode(self, apk, output_dir):
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    def read_manifest(self, output_dir):
        return None, None

    def read_resources(self, output_dir, sha):
        return [], []

    def decompile(self, apk, output_dir, *, timeout=None):
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    monkeypatch.setattr(ApktoolBackend, "decode", decode)
    monkeypatch.setattr(ApktoolBackend, "read_manifest", read_manifest)
    monkeypatch.setattr(ApktoolBackend, "read_resources", read_resources)
    monkeypatch.setattr(JadxBackend, "decompile", decompile)

    analyzer = Analyzer(settings)
    result = analyzer.analyze(minimal_apk)

    run = result.run
    assert run is not None
    assert _stages_of(run) == [stage.value for stage in PIPELINE_ORDER]
    assert _timestamps_of(run) == sorted(_timestamps_of(run))


def test_stage_facts_survive_the_database(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run's stages are read back from the workspace unchanged."""
    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")
    analyzer = Analyzer(settings)
    result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
    run = result.run
    assert run is not None

    stored = analyzer.store.get_run(run.id)

    assert stored is not None
    assert _stages_of(stored) == _stages_of(run)
    assert _timestamps_of(stored) == _timestamps_of(run)


def test_a_workspace_before_stages_still_opens(tmp_path: Path) -> None:
    """A database written before the stages column existed still reads.

    The column is added by migration, and a row from the older schema reads
    as "no stage facts" — an empty list, not an error.
    """
    db = tmp_path / "legacy.db"
    Store.open(db)
    assert SCHEMA_VERSION >= 8

    import sqlite3

    connection = sqlite3.connect(db)
    try:
        connection.execute(
            "UPDATE analysis_runs SET stages = '[]' WHERE id = (SELECT id FROM analysis_runs LIMIT 1)"
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(analysis_runs)")}
        assert "stages" in columns
    finally:
        connection.close()

    reopened = Store.open(db)
    assert reopened.list_runs("no-such-project") == []


def test_a_stage_cannot_be_recorded_twice() -> None:
    """Re-entering a stage keeps the original event, in place and order."""
    from dexatlas.core.runs import AnalysisRun

    run = AnalysisRun.start("p1", "ab" * 32)
    run.record_stage_start(RunStage.INSPECT)
    run.record_stage_end(RunStage.INSPECT)
    first = list(run.stages)

    run.record_stage_start(RunStage.INSPECT)
    run.record_stage_end(RunStage.INSPECT)

    assert run.stages == first


def test_a_stage_end_without_a_start_still_reads_in_sequence() -> None:
    """An end recorded before a start fabricates the start it implies."""
    from dexatlas.core.runs import AnalysisRun

    run = AnalysisRun.start("p1", "ab" * 32)
    run.record_stage_end(RunStage.INSPECT)

    assert len(run.stages) == 1
    assert run.stages[0].stage is RunStage.INSPECT
    assert run.stages[0].started_at is not None


# ---------------------------------------------------------------------------
# The instrumentation changes nothing about the analysis
# ---------------------------------------------------------------------------


def test_stage_recording_does_not_change_the_analysis(
    tmp_path: Path, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same APK, analysed with and without stage writes, agrees.

    The comparison runs the pipeline twice against two isolated workspaces:
    once as the pipeline is, and once with every stage write short-circuited.
    The published project rows — the reader-visible result — must be equal.
    """
    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")

    def _analyse(workspace: Path) -> dict[str, object]:
        settings = Settings(workspace=workspace / "workspace")
        analyzer = Analyzer(settings)
        result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
        project = result.project
        assert project.status is ProjectStatus.COMPLETED
        return {
            "id": project.id,
            "status": project.status.value,
            "class_count": project.class_count,
            "method_count": project.method_count,
            "reference_count": project.reference_count,
            "call_edge_count": project.call_edge_count,
            "evidence_count": project.evidence_count,
            "resource_count": project.resource_count,
            "errors": [(e.tool, e.code.value, e.message) for e in project.errors],
            "classes": sorted(c.name for c in analyzer.store.list_classes(project.id)),
            "evidence": sorted(e.summary for e in analyzer.store.list_evidence(project.id)),
        }

    with_stages = _analyse(tmp_path / "with")
    monkeypatch.setattr(
        Analyzer, "_stage", lambda self, run, stage, *, end=False: None, raising=True
    )
    without_stages = _analyse(tmp_path / "without")

    assert with_stages == without_stages


def test_an_instrumented_failure_still_leaves_a_failed_project(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backend that raises mid-run leaves the failure record intact.

    The stage bookkeeping wraps the backend call, so the test also proves
    the wrapper neither swallows nor rewrites the exception path.
    """
    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")

    def extract(self, apk, sha, **kwargs):
        raise RuntimeError("the DEX reader exploded")

    monkeypatch.setattr(AndroguardBackend, "extract", extract)

    analyzer = Analyzer(settings)
    from dexatlas.core.pipeline import AnalysisFailed

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)

    project = analyzer.store.get_project(_project_id(minimal_apk))
    assert project is not None
    assert project.status is ProjectStatus.FAILED
    assert any("RuntimeError" in e.message for e in project.errors)


def _project_id(apk: Path) -> str:
    from dexatlas.core.ingest import inspect_apk
    from dexatlas.core.models import Project

    return Project.new_id(inspect_apk(apk).sha256)


# ---------------------------------------------------------------------------
# The two transports read the same facts
# ---------------------------------------------------------------------------


def test_the_rest_api_run_stages_endpoint_carries_stages(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /projects/{pid}/runs/{rid}/stages returns the stages.

    The run detail's own shape keeps the contract's original field set —
    the stage facts are this endpoint's, not the run row's.
    """
    from dexatlas.api.app import app
    from dexatlas.config.settings import get_settings

    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        analyzer = Analyzer(settings)
        result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
        run = result.run
        assert run is not None
        with TestClient(app) as client:
            detail = client.get(f"/projects/{project_id_of(result)}/runs/{run.id}")
            response = client.get(f"/projects/{project_id_of(result)}/runs/{run.id}/stages")
        assert detail.status_code == 200
        assert "stages" not in detail.json(), "the run detail keeps its original shape"
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project_id_of(result)
        assert body["run_id"] == run.id
        assert body["run_status"] == run.status.value
        assert [stage["stage"] for stage in body["stages"]] == _stages_of(run)
        for stage in body["stages"]:
            assert stage["finished_at"] is not None
        assert body["stages"][0]["started_at"] <= body["stages"][-1]["finished_at"]
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_the_workbench_run_stages_endpoint_carries_stages(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /api/projects/{pid}/runs/{rid}/stages returns the same stage facts."""
    from dexatlas.workbench.app import create_app

    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")
    settings.ensure_workspace()
    analyzer = Analyzer(settings)
    result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
    run = result.run
    assert run is not None

    app = create_app(analyzer)
    with TestClient(app) as client:
        detail = client.get(f"/api/projects/{project_id_of(result)}/runs/{run.id}")
        response = client.get(f"/api/projects/{project_id_of(result)}/runs/{run.id}/stages")
    assert detail.status_code == 200
    assert "stages" not in detail.json(), "the run detail keeps its original shape"
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run.id
    assert body["run_status"] == run.status.value
    assert [stage["stage"] for stage in body["stages"]] == _stages_of(run)
    assert all(stage["finished_at"] for stage in body["stages"])


def test_the_stages_endpoint_of_an_unknown_run_is_404(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown run, or another project's run, is the contract's 404."""
    from dexatlas.api.app import app
    from dexatlas.config.settings import get_settings

    _patch_dex_reader(monkeypatch, "com.example.demo.Crypto")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        analyzer = Analyzer(settings)
        result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
        pid = project_id_of(result)
        with TestClient(app) as client:
            assert client.get(f"/projects/{pid}/runs/run_missing/stages").status_code == 404
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def project_id_of(result) -> str:
    return result.project.id
