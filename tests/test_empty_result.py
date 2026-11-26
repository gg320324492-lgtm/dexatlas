"""An analysis that finishes without reading anything is recorded as a failure.

The pipeline could reach the end of a run having read nothing: not one class
declaration and not one manifest. It knew -- the project status it computed
was ``failed``, and the run's own status was ``failed`` -- but it wrote
neither of them down. The only write that publishes a run's results is the
one that publishes them, and a run that publishes nothing published no
status either: the project row kept saying ``running``, and so did the run
row.

A row that says ``running`` is a run that is still going. The workbench
reads those rows, so an analysis that had finished was shown as an analysis
in progress -- and stayed that way until the server was restarted and the
orphan sweep guessed at what had happened, in words that said the opposite
of the truth.

These tests read the rows in the database, because the rows are what the API
and the workbench read. The model the pipeline held in memory is not what a
reader ever sees.

The sample is the project's own demo application, with its DEX, its manifest
and its resource table made unreadable. It is written to a temporary
directory, which this project keeps inside its own ``.scratch``: no
third-party APK enters this repository, and none is needed here.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dexatlas.api.uploads import run_background_analysis
from dexatlas.config.settings import Settings
from dexatlas.core.ingest import inspect_apk
from dexatlas.core.models import Project, ProjectStatus
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import RunStatus

EXAMPLES = Path(__file__).parent.parent / "examples"
DEMO_APK = EXAMPLES / "demo-app" / "demo.apk"

#: Bytes that are not what the reader they are handed expects.
NOT_READABLE = b"these bytes are not what the reader expects" * 8

#: The parts of an APK that every backend reads. Damaged together, they
#: leave a run with nothing at all to show: no class, no manifest.
READ_BY_EVERY_BACKEND = ("classes.dex", "AndroidManifest.xml", "resources.arsc")


def _damage(source: Path, target: Path) -> Path:
    """A copy of ``source`` that no backend can read anything out of.

    The archive around the damaged parts is copied byte for byte, and the
    copy is written with the zip's own checksums recomputed, so it is still
    a readable archive: the file is damaged, not malformed, and it gets past
    the ingestion checks the way a damaged APK does.
    """
    with (
        zipfile.ZipFile(source) as archive,
        zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out,
    ):
        for info in archive.infolist():
            payload = archive.read(info.filename)
            if info.filename in READ_BY_EVERY_BACKEND:
                payload = NOT_READABLE
            out.writestr(info, payload)
    return target


@pytest.fixture
def unreadable_apk(tmp_path: Path) -> Path:
    """The demo application, damaged in every part a backend reads."""
    return _damage(DEMO_APK, tmp_path / "unreadable-demo.apk")


# -- the failure reaches the database ----------------------------------------


def test_an_analysis_that_read_nothing_is_recorded_as_failed(
    settings: Settings, unreadable_apk: Path
) -> None:
    """The rows said ``running``, and a reader took that as "still going".

    The pipeline knew: the status it computed was ``failed``, and the run's
    own status was ``failed``. It wrote neither down, so the rows a later
    reader consults still described an analysis in progress -- one that had
    finished minutes ago and found nothing.
    """
    analyzer = Analyzer(settings)

    result = analyzer.analyze(unreadable_apk)

    # The pipeline itself saw the failure.
    assert result.project.status is ProjectStatus.FAILED
    assert result.succeeded is False

    # The database is what the API and the workbench read.
    project = analyzer.store.get_project(result.project.id)
    assert project is not None
    assert project.status is ProjectStatus.FAILED
    assert project.status is not ProjectStatus.RUNNING

    runs = analyzer.store.list_runs(result.project.id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.FAILED
    assert runs[0].status is not RunStatus.RUNNING
    assert runs[0].finished_at is not None


def test_the_failure_says_why_the_analysis_found_nothing(
    settings: Settings, unreadable_apk: Path
) -> None:
    """A failure with no reason is a failure nobody can act on.

    The reason the workbench shows is the project's own errors. An empty
    list there means the interface says the analysis failed and cannot say
    what happened -- which is the state this defect left behind.
    """
    analyzer = Analyzer(settings)

    result = analyzer.analyze(unreadable_apk)

    project = analyzer.store.get_project(result.project.id)
    assert project is not None
    reasons = [f"{error.tool}: {error.message}" for error in project.errors]
    assert any("read nothing" in reason for reason in reasons), reasons

    run = analyzer.store.list_runs(result.project.id)[0]
    run_reasons = [f"{error.tool}: {error.message}" for error in run.errors]
    assert any("read nothing" in reason for reason in run_reasons), run_reasons


def test_a_run_that_read_nothing_publishes_nothing(
    settings: Settings, unreadable_apk: Path
) -> None:
    """Publishing an empty result would replace a good snapshot with zeroes.

    The failure is recorded; the result is not published. Those are two
    different facts, and only the first one is true of a run that read
    nothing.
    """
    analyzer = Analyzer(settings)

    result = analyzer.analyze(unreadable_apk)

    assert analyzer.store.get_published_run_id(result.project.id) is None


def test_a_failed_attempt_leaves_the_published_snapshot_alone(settings: Settings) -> None:
    """A project that published a snapshot keeps it.

    The second attempt reached the end of the analysis having read nothing,
    and published nothing -- so the snapshot the first attempt published
    still describes the project: the counts, the manifest and the workspace
    pointer are still the ones it wrote.
    """
    analyzer = Analyzer(settings)

    good = analyzer.analyze(DEMO_APK)
    assert good.succeeded
    published_id = analyzer.store.get_published_run_id(good.project.id)
    assert published_id is not None
    before = analyzer.store.get_project(good.project.id)
    assert before is not None
    manifest_before = analyzer.store.get_manifest(good.project.id)
    workspace_before = analyzer.store.get_workspace(good.project.id)
    assert workspace_before is not None

    # No backend runs, so the analysis reaches its end having read nothing:
    # no class and no manifest. It is the same empty result a run of
    # damaged bytes produces, on the same project.
    analyzer.analyze(
        DEMO_APK,
        include_jadx=False,
        include_apktool=False,
        include_androguard=False,
    )

    after = analyzer.store.get_project(good.project.id)
    assert after is not None
    assert after.status is ProjectStatus.FAILED
    assert after.class_count == before.class_count
    assert after.method_count == before.method_count
    assert after.evidence_count == before.evidence_count
    assert analyzer.store.get_workspace(good.project.id) == workspace_before
    assert analyzer.store.get_manifest(good.project.id) == manifest_before
    assert analyzer.store.get_published_run_id(good.project.id) == published_id


# -- the background task reads the same rows ---------------------------------


def test_the_background_analysis_records_the_failure_too(
    settings: Settings, unreadable_apk: Path
) -> None:
    """The workbench analyses in the background, and it reads the same rows.

    The background task is the same pipeline, so the failure it finds has to
    reach the database the same way. Otherwise the interface waits for an
    analysis that has already ended, which is the defect this file is about.
    """
    analyzer = Analyzer(settings)
    apk = inspect_apk(unreadable_apk)

    run_background_analysis(analyzer, unreadable_apk, apk)

    project = analyzer.store.get_project(Project.new_id(apk.sha256))
    assert project is not None
    assert project.status is ProjectStatus.FAILED
    reasons = [f"{error.tool}: {error.message}" for error in project.errors]
    assert any("read nothing" in reason for reason in reasons), reasons
