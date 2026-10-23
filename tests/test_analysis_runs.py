"""Analysis runs: the identity of one analysis, and what a reader can see.

The project id is a content hash, so the same APK always maps to the same
project -- and a re-analysis used to overwrite the previous one *in place*.
The Phase 1 review found the same shape of problem twice (the ``evidence``
table not being cleared, and the upload being overwritten) and fixed both
by hand. A run identifier fixes the class of it.

What these tests hold in place:

- A reader never sees one run's symbols beside another's evidence.
- A re-analysis that fails, or that finds nothing, leaves the published
  snapshot exactly as it was.
- Every run has an identity of its own, and writes into a directory of its
  own, so two analyses of one APK cannot overwrite each other's output.
- A workspace written before runs existed still opens, and still holds what
  it held.

The tests drive the analysis through its own seams -- the DEX reader is
patched and the two external backends are left out -- so none of them needs
a decompiler, and none of them is skipped when one is not installed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.ingest import inspect_apk
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    Project,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import AnalysisFailed, Analyzer
from dexatlas.core.runs import AnalysisRun, RunCompleteness, RunStatus
from dexatlas.core.storage import SCHEMA_VERSION, Store
from dexatlas.tools.androguard.adapter import AndroguardBackend


def _classes(*names: str) -> list[ClassRef]:
    return [ClassRef(name=name, kind=ClassKind.CLASS) for name in names]


def _patch_dex_reader(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make the DEX reader report these classes, and nothing else.

    The DEX reader is the backend that owns the symbol index, so patching
    it is how a test says what the APK holds without needing an APK whose
    bytecode a real reader would accept.
    """

    def extract(self: AndroguardBackend, apk: Path, apk_sha256: str, **kwargs: object):
        return (_classes(*names), [], [], [], [], None)

    monkeypatch.setattr(AndroguardBackend, "extract", extract)


def _analyse(analyzer: Analyzer, apk: Path) -> object:
    """Analyse an APK with the two external backends left out.

    The DEX reader is patched, so the run has symbols; there is no
    manifest and no decompiled Java, and the run completes on the symbols
    alone.
    """
    return analyzer.analyze(apk, include_apktool=False, include_jadx=False)


def _published_symbols(analyzer: Analyzer, project_id: str) -> list[str]:
    return [c.name for c in analyzer.store.list_classes(project_id)]


def _published_evidence(analyzer: Analyzer, project_id: str) -> list[str]:
    return [e.summary for e in analyzer.store.list_evidence(project_id)]


# ---------------------------------------------------------------------------
# The run's identity
# ---------------------------------------------------------------------------


def test_two_analyses_of_one_apk_are_two_runs(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run id says nothing about the APK.

    The project id is the APK's content hash, so it cannot tell two
    analyses of the same bytes apart. A run id that was derived from the
    APK would have the same problem, and the whole mechanism would be
    worth nothing: the reader would still be unable to say which attempt
    produced the symbols in front of them.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    first = _analyse(analyzer, minimal_apk)
    second = _analyse(analyzer, minimal_apk)

    assert first.run is not None
    assert second.run is not None
    assert first.run.id != second.run.id
    assert first.run.id != first.project.id
    assert first.run.id != first.run.apk_sha256
    assert first.run.apk_sha256 == second.run.apk_sha256

    runs = analyzer.store.list_runs(first.project.id)
    assert {run.id for run in runs} == {first.run.id, second.run.id}


def test_a_run_records_the_tools_the_sha_and_how_it_ended(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The facts that belong to an attempt, recorded on the attempt.

    The tool versions are the run's, not the project's: the same APK
    analysed twice, with a decompiler upgraded in between, is two runs
    with two sets of versions, and only the run can tell them apart.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    result = _analyse(analyzer, minimal_apk)
    assert result.run is not None

    stored = analyzer.store.get_run(result.run.id)
    assert stored is not None
    assert stored.status is RunStatus.COMPLETED
    assert stored.completeness is RunCompleteness.COMPLETE
    assert stored.apk_sha256 == result.project.apk.sha256
    assert stored.project_id == result.project.id
    assert stored.tool_versions == result.project.tool_versions
    assert stored.finished_at is not None
    assert stored.duration_seconds is not None


def test_a_run_that_hit_an_error_is_partial(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run with a gap in it says so.

    A backend that fails does not make the run's other findings untrue --
    but it does make the result incomplete, and a reader who is not told
    that reads a partial index as a whole one.
    """
    analyzer = Analyzer(settings)

    def extract(self: AndroguardBackend, apk: Path, apk_sha256: str, **kwargs: object):
        error = ToolError(
            tool="androguard",
            code=ToolErrorCode.PARSE_ERROR,
            message="the DEX file could not be read",
        )
        return (_classes("com.fake.One"), [], [], [], [], error)

    monkeypatch.setattr(AndroguardBackend, "extract", extract)

    result = _analyse(analyzer, minimal_apk)
    assert result.run is not None
    assert result.run.completeness is RunCompleteness.PARTIAL
    assert result.run.errors


# ---------------------------------------------------------------------------
# What a reader can see
# ---------------------------------------------------------------------------


def test_a_reader_never_sees_one_runs_symbols_beside_anothers_evidence(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The symbols and the evidence in front of a reader are one run's.

    This is the defect the run identifier exists to remove. The symbols
    and the evidence were written in two separate transactions, so a
    reader that looked between them saw the *new* run's symbols beside the
    *old* run's evidence -- two runs' results, presented as one.

    The test watches the workspace at the moment the evidence is written,
    which is where the two used to come apart. What it sees has to be one
    run's symbols and one run's evidence, and never a mixture.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    _analyse(analyzer, minimal_apk)

    observed: list[tuple[list[str], list[str]]] = []
    original = Store.save_evidence

    def spy(self: Store, project_id: str, evidence: list[Evidence]) -> int:
        # What a reader of the workspace sees at this moment.
        observed.append(
            (
                [c.name for c in analyzer.store.list_classes(project_id)],
                [e.summary for e in analyzer.store.list_evidence(project_id)],
            )
        )
        return original(self, project_id, evidence)

    monkeypatch.setattr(Store, "save_evidence", spy)
    _patch_dex_reader(monkeypatch, "com.fake.Second")
    _analyse(analyzer, minimal_apk)

    assert observed, "the analysis never wrote its evidence"
    for classes, evidence in observed:
        named = {name for name in classes if any(name in summary for summary in evidence)}
        assert named == set(classes), (
            "the symbols and the evidence are from different runs: "
            f"the symbols are {classes}, the evidence is {evidence}"
        )


def test_a_failed_re_analysis_leaves_the_published_snapshot_alone(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An interrupted run leaves the previous complete run intact.

    The run that fails publishes nothing. What was published before it --
    the symbols, the evidence, the counts and the workspace pointer --
    is still there, and it is still the run that published it.

    Before this, the symbols were written before the evidence, and the
    failure happened between them: the previous run's evidence was gone
    and the new run's symbols were in its place. The reader was left with
    a snapshot that no run had ever produced.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    first = _analyse(analyzer, minimal_apk)
    project_id = first.project.id

    before_classes = _published_symbols(analyzer, project_id)
    before_evidence = _published_evidence(analyzer, project_id)
    before_counts = (first.project.class_count, first.project.evidence_count)

    def boom(self: Store, project_id: str, evidence: list[Evidence]) -> int:
        raise RuntimeError("the evidence could not be written")

    monkeypatch.setattr(Store, "save_evidence", boom)
    _patch_dex_reader(monkeypatch, "com.fake.Second")

    with pytest.raises(AnalysisFailed):
        _analyse(analyzer, minimal_apk)

    # What a reader sees: the published snapshot, whole and unchanged.
    assert _published_symbols(analyzer, project_id) == before_classes
    assert _published_evidence(analyzer, project_id) == before_evidence

    stored = analyzer.store.get_project(project_id)
    assert stored is not None
    assert (stored.class_count, stored.evidence_count) == before_counts
    # The failure is still visible: the project says the last attempt failed.
    assert stored.status.value == "failed"
    assert any(error.code is ToolErrorCode.ANALYSIS_FAILED for error in stored.errors)


def test_a_failed_re_analysis_leaves_the_published_run_published(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The snapshot that is left behind is still the run that published it.

    The pointer names a run, and a run that failed does not become the
    published one: the project keeps pointing at the run whose results it
    still holds.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    first = _analyse(analyzer, minimal_apk)
    project_id = first.project.id
    published = analyzer.store.get_published_run_id(project_id)
    assert published is not None

    def boom(self: Store, project_id: str, evidence: list[Evidence]) -> int:
        raise RuntimeError("the evidence could not be written")

    monkeypatch.setattr(Store, "save_evidence", boom)
    _patch_dex_reader(monkeypatch, "com.fake.Second")

    with pytest.raises(AnalysisFailed):
        _analyse(analyzer, minimal_apk)

    assert analyzer.store.get_published_run_id(project_id) == published
    failed = analyzer.store.list_runs(project_id)[0]
    assert failed.status is RunStatus.FAILED
    assert failed.id != published


def test_a_run_that_finds_nothing_does_not_replace_the_published_snapshot(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run with nothing to publish does not publish.

    The analysis found no classes and no manifest. It has no result, and
    a result it does not have is not one it may put in place of the one
    the project already holds.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    first = _analyse(analyzer, minimal_apk)
    project_id = first.project.id

    before_classes = _published_symbols(analyzer, project_id)
    before_evidence = _published_evidence(analyzer, project_id)

    _patch_dex_reader(monkeypatch)
    result = _analyse(analyzer, minimal_apk)

    assert not result.succeeded
    assert _published_symbols(analyzer, project_id) == before_classes
    assert _published_evidence(analyzer, project_id) == before_evidence


def test_a_run_that_finds_nothing_leaves_the_published_run_published(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run with nothing to publish does not become the published one."""
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    first = _analyse(analyzer, minimal_apk)
    project_id = first.project.id
    published = analyzer.store.get_published_run_id(project_id)
    assert published is not None

    _patch_dex_reader(monkeypatch)
    _analyse(analyzer, minimal_apk)

    assert analyzer.store.get_published_run_id(project_id) == published


def test_a_re_analysis_replaces_the_snapshot_as_a_whole(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A published re-analysis is the new run's, entirely.

    The old run's symbols are not left behind beside the new run's, and
    the new run's are not published beside the old run's evidence.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.First")
    _analyse(analyzer, minimal_apk)

    _patch_dex_reader(monkeypatch, "com.fake.Second")
    second = _analyse(analyzer, minimal_apk)
    project_id = second.project.id

    assert _published_symbols(analyzer, project_id) == ["com.fake.Second"]
    evidence = _published_evidence(analyzer, project_id)
    assert evidence
    assert all("com.fake.Second" in summary for summary in evidence)
    assert not any("com.fake.First" in summary for summary in evidence)
    assert analyzer.store.get_published_run_id(project_id) == second.run.id


# ---------------------------------------------------------------------------
# One writer per run
# ---------------------------------------------------------------------------


def test_each_run_writes_into_a_directory_of_its_own(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two analyses of one APK do not share an output directory.

    The output directories were handed to the external tools as *their*
    output directories, so two analyses of the same APK wrote over each
    other, and a request for source could read a half-written ``.java``.

    Each run now writes into ``projects/<id>/runs/<run-id>/``, and the
    project's workspace column names the run that is published.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    first = _analyse(analyzer, minimal_apk)
    second = _analyse(analyzer, minimal_apk)

    assert first.workspace is not None
    assert second.workspace is not None
    assert first.workspace != second.workspace
    assert first.run is not None
    assert second.run is not None
    assert first.workspace.name == first.run.id
    assert second.workspace.name == second.run.id
    assert first.workspace.parent == second.workspace.parent
    assert first.workspace.parent.name == "runs"


def test_the_workspace_pointer_names_the_published_run(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pointer a reader follows is the published run's directory.

    The pointer is read once per request and then holds still, so a
    request cannot read the source of one run and the symbols of another.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")
    first = _analyse(analyzer, minimal_apk)
    second = _analyse(analyzer, minimal_apk)

    pointer = analyzer.store.get_workspace(first.project.id)
    assert pointer == second.workspace
    assert pointer is not None
    assert pointer.name == second.run.id  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# The store: staging, publishing, and the schema
# ---------------------------------------------------------------------------


def test_staged_results_are_invisible_until_the_run_publishes_them(tmp_path: Path) -> None:
    """A run's results are staged separately, and published in one go.

    The staged database holds the run's symbols and evidence. Until the
    run publishes them, a reader of the workspace sees nothing of them --
    which is what makes an interrupted run harmless.
    """
    store = Store.open(tmp_path / "workspace.db")
    project = Project.create(ApkMetadata(sha256="a" * 64, size_bytes=10, path=tmp_path / "a.apk"))
    store.save_project(project, None, None)

    staged_path = tmp_path / "run" / "index.db"
    staged = Store.open(staged_path)
    staged.save_project(project, tmp_path / "run", None)
    staged.save_symbols(project.id, _classes("com.fake.One"), [], [], [], [], [])
    staged.save_evidence(
        project.id,
        [
            Evidence(
                id="E-0001",
                kind=EvidenceKind.OBSERVATION,
                level=EvidenceLevel.VERIFIED,
                summary="a fact",
            )
        ],
    )

    assert store.list_classes(project.id) == []
    assert store.list_evidence(project.id) == []

    run = AnalysisRun.start(project.id, project.apk.sha256, workspace=tmp_path / "run")
    run.status = RunStatus.COMPLETED
    store.publish_run(project, run, staged_path, None)

    assert [c.name for c in store.list_classes(project.id)] == ["com.fake.One"]
    assert len(store.list_evidence(project.id)) == 1
    assert store.get_published_run_id(project.id) == run.id
    assert store.get_workspace(project.id) == tmp_path / "run"


def test_a_workspace_written_before_runs_existed_still_opens(tmp_path: Path) -> None:
    """A legacy workspace keeps what it kept.

    The migration adds what the new schema needs and changes nothing
    else: the symbols, the evidence and the project's own row are still
    there, and the pointer to the published run is empty -- because the
    analysis that wrote those rows was never recorded as a run.
    """
    path = tmp_path / "workspace.db"
    store = Store.open(path)
    project = Project.create(ApkMetadata(sha256="b" * 64, size_bytes=10, path=tmp_path / "b.apk"))
    store.save_project(project, tmp_path / "ws", None)
    store.save_symbols(project.id, _classes("com.fake.Legacy"), [], [], [], [], [])

    _downgrade_to_schema_3(path)

    reopened = Store.open(path)
    assert reopened.get_project(project.id) is not None
    assert [c.name for c in reopened.list_classes(project.id)] == ["com.fake.Legacy"]
    assert reopened.get_published_run_id(project.id) is None
    assert reopened.list_runs(project.id) == []
    assert reopened.get_workspace(project.id) == tmp_path / "ws"


def test_a_legacy_workspace_is_analysed_again_and_published(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first run after the migration publishes, and the pointer names it.

    The workspace had no run to point at. The next analysis makes one, and
    the pointer moves to it.
    """
    project = Project.create(inspect_apk(minimal_apk))
    legacy = Store.open(settings.database_path)
    legacy.save_project(project, None, None)
    _downgrade_to_schema_3(settings.database_path)

    # The analyzer opens the workspace for itself, so it is built after the
    # downgrade: it has to run the migration to see the new schema at all.
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    result = _analyse(analyzer, minimal_apk)

    assert result.run is not None
    assert analyzer.store.get_published_run_id(project.id) == result.run.id
    assert _published_symbols(analyzer, project.id) == ["com.fake.One"]


def _downgrade_to_schema_3(path: Path) -> None:
    """Make a workspace look like one written before runs existed.

    The schema of the two versions differs in exactly two places: the run
    table is not there, and the published-run pointer is not a column of
    the project. Putting the database back into that shape is what a
    workspace written by the previous version looks like.
    """
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE analysis_runs")
        connection.execute("ALTER TABLE projects DROP COLUMN published_run_id")
        connection.execute("DELETE FROM schema_info")
        connection.execute("INSERT INTO schema_info (version) VALUES (3)")
        connection.commit()
    finally:
        connection.close()
    assert SCHEMA_VERSION == 4
