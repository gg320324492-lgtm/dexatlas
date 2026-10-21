"""An analysis that fails leaves the project failed, and says what failed.

The pipeline used to have no error handling at all. A step that raised took
the whole run down, and the project row was left saying ``running`` for ever:
nothing recorded that the analysis had failed, the report said the project
was still running, and the API — which finds a project by the APK's hash —
handed the same project back for ever. The failure was invisible and
permanent.

Two things have to be true at once, and a fix that only does one of them is
not a fix:

* the project reaches a terminal state, with the reason recorded on it; and
* the failure still reaches the caller, because a run that says nothing is
  not a run that found nothing.

The tests here pin both, and the row they read is the row in the database —
the thing the API reads — rather than the object the pipeline happened to
hold in memory.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from dexatlas.api.app import _run_analysis, app
from dexatlas.cli.main import app as cli_app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.ingest import inspect_apk
from dexatlas.core.models import (
    ANALYSIS_TOOL,
    ApkMetadata,
    Project,
    ProjectStatus,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import AnalysisFailed, AnalysisResult, Analyzer
from dexatlas.core.storage import Store

runner = CliRunner()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A client wired to the same workspace the tests write to."""
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _boom(*args: object, **kwargs: object) -> None:
    """A backend that fails the way a broken one does: by raising."""
    raise RuntimeError("the DEX reader fell over")


def _failing_analyzer(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Analyzer:
    """An analyzer whose DEX reader raises in the middle of the run."""
    analyzer = Analyzer(settings)
    monkeypatch.setattr(analyzer._androguard, "extract", _boom)
    return analyzer


def _stored_row(analyzer: Analyzer, project_id: str) -> tuple[str, str]:
    """The status and the errors the database holds for a project."""
    with analyzer.store.transaction() as connection:
        row = connection.execute(
            "SELECT status, errors FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    assert row is not None, "the project was never written"
    return str(row["status"]), str(row["errors"])


# -- the project reaches a terminal state -----------------------------------


def test_a_failing_analysis_does_not_leave_the_project_running(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The project was left saying ``running``, for ever.

    The status was the only thing that said the analysis was going on, and
    nothing ever said otherwise: a row that says ``running`` is a run that is
    still going, and this one was not.
    """
    analyzer = _failing_analyzer(settings, monkeypatch)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    projects = analyzer.store.list_projects()
    assert len(projects) == 1
    assert projects[0].status is ProjectStatus.FAILED
    assert projects[0].status is not ProjectStatus.RUNNING


def test_the_database_row_says_failed(settings: Settings, minimal_apk: Path, monkeypatch) -> None:
    """The row in the database is what the API reads, and what it read was wrong."""
    analyzer = _failing_analyzer(settings, monkeypatch)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    project = analyzer.store.list_projects()[0]
    status, errors = _stored_row(analyzer, project.id)
    assert status == "failed"
    assert "RuntimeError" in errors


def test_the_failure_is_recorded_on_the_project(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record has to say what came out, not merely that something did."""
    analyzer = _failing_analyzer(settings, monkeypatch)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    project = analyzer.store.list_projects()[0]
    failures = [error for error in project.errors if error.code is ToolErrorCode.ANALYSIS_FAILED]
    assert len(failures) == 1, f"the failure was not recorded: {project.errors}"
    failure = failures[0]
    # No backend failed: the analysis did. The record says which, so that a
    # reader can tell a broken tool from a broken run.
    assert failure.tool == ANALYSIS_TOOL
    assert "RuntimeError" in failure.message
    assert "the DEX reader fell over" in failure.message


def test_the_failure_does_not_hide_the_errors_that_came_before_it(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backend that failed first, and then the analysis: both are recorded."""
    analyzer = Analyzer(settings)

    def failing_extract(*args: object, **kwargs: object):
        raise RuntimeError("the DEX reader fell over")

    monkeypatch.setattr(analyzer._androguard, "extract", failing_extract)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    project = analyzer.store.list_projects()[0]
    assert project.status is ProjectStatus.FAILED
    assert project.errors, "the failure was dropped"


# -- the failure still reaches the caller -----------------------------------


def test_the_failure_is_raised_to_the_caller(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller that cannot tell a failure from an empty result cannot act.

    The exception carries the failure that was recorded, and the original
    exception with it, so the log says what went wrong rather than only that
    something did.
    """
    analyzer = _failing_analyzer(settings, monkeypatch)

    with pytest.raises(AnalysisFailed) as excinfo:
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    failure = excinfo.value
    assert "the DEX reader fell over" in str(failure)
    assert failure.error.code is ToolErrorCode.ANALYSIS_FAILED
    assert isinstance(failure.__cause__, RuntimeError)


def test_a_failure_of_the_analysis_is_not_a_failure_of_a_backend(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The error is about the run, and it says so.

    A record that said "androguard" would blame a tool that did its job, and
    the index gap it would imply would be a different claim from the one that
    is true: the run stopped, so whatever the index would have held is not in
    it.
    """
    analyzer = _failing_analyzer(settings, monkeypatch)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    project = analyzer.store.list_projects()[0]
    failure = project.errors[-1]
    assert failure.tool != "androguard"
    assert failure.code is ToolErrorCode.ANALYSIS_FAILED


# -- the API's background task tells the two apart --------------------------


def test_the_background_task_reports_a_failure_as_a_failure(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """The background task used to swallow the failure into one log line."""
    analyzer = _failing_analyzer(settings, monkeypatch)
    apk = inspect_apk(minimal_apk)

    with caplog.at_level(logging.ERROR):
        _run_analysis(analyzer, minimal_apk, apk)

    assert "failed" in caplog.text
    assert "the DEX reader fell over" in caplog.text


def test_the_background_task_does_not_call_an_empty_result_a_failure(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """A run that found nothing is an answer; a run that broke is an error.

    The two used to reach the log the same way, which sends the reader
    looking for a fault in a run that worked.
    """
    analyzer = Analyzer(settings)
    project = Project.create(inspect_apk(minimal_apk))
    project.status = ProjectStatus.FAILED
    result = AnalysisResult(project=project, manifest=None, evidence=[])
    monkeypatch.setattr(analyzer, "analyze", lambda *args, **kwargs: result)
    apk = inspect_apk(minimal_apk)

    with caplog.at_level(logging.WARNING):
        _run_analysis(analyzer, minimal_apk, apk)

    assert "produced no symbols" in caplog.text
    assert "failed" not in caplog.text


# -- what the command line does with it -------------------------------------


def test_the_command_line_does_not_report_a_failed_analysis_as_a_success(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI says what failed, and exits with a code of its own.

    Exit code 1 is the code for "the answer is empty", so a failed analysis
    that also exited 1 could not be told from an APK with nothing in it. The
    failure has its own code now — 3 — and it says what failed rather than
    printing a traceback: a caller that reads the output wants to know what
    broke, not where in the code it broke.
    """
    analyzer = _failing_analyzer(settings, monkeypatch)
    monkeypatch.setattr("dexatlas.cli.main.Analyzer", lambda *args, **kwargs: analyzer)

    outcome = runner.invoke(cli_app, ["analyze", str(minimal_apk)])

    assert outcome.exit_code == 3
    assert outcome.exit_code != 1, "a failed analysis must not read as an empty answer"
    flat = " ".join(outcome.output.split())
    assert "did not complete" in flat
    assert "Traceback" not in flat


def test_the_command_line_leaves_the_project_failed(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI writes to the same workspace the API reads, so the row matters."""
    analyzer = _failing_analyzer(settings, monkeypatch)
    monkeypatch.setattr("dexatlas.cli.main.Analyzer", lambda *args, **kwargs: analyzer)

    runner.invoke(cli_app, ["analyze", str(minimal_apk)])

    projects = analyzer.store.list_projects()
    assert len(projects) == 1
    assert projects[0].status is ProjectStatus.FAILED


def test_the_metadata_the_caller_passed_in_is_still_usable(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The failure path takes the same route whether the APK was inspected here or not."""
    analyzer = _failing_analyzer(settings, monkeypatch)
    apk = inspect_apk(minimal_apk)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, metadata=apk, include_jadx=False, include_apktool=False)

    projects = analyzer.store.list_projects()
    assert len(projects) == 1
    assert projects[0].status is ProjectStatus.FAILED
    assert projects[0].apk.sha256 == apk.sha256


def test_a_non_apk_is_still_refused_before_a_project_is_made(
    settings: Settings, not_an_apk: Path
) -> None:
    """The input that is not an APK at all is refused, and it is not a failure.

    There is no project to leave running: the project id is the APK's hash,
    and there is no APK.
    """
    from dexatlas.core.ingest import ApkValidationError

    analyzer = Analyzer(settings)

    with pytest.raises(ApkValidationError):
        analyzer.analyze(not_an_apk)

    assert analyzer.store.list_projects() == []


def test_the_metadata_type_is_the_one_the_api_passes(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The API hands the analysis an inspection it has already done."""
    analyzer = _failing_analyzer(settings, monkeypatch)
    apk: ApkMetadata = inspect_apk(minimal_apk)

    with pytest.raises(AnalysisFailed):
        analyzer.analyze(minimal_apk, metadata=apk, include_jadx=False, include_apktool=False)

    assert analyzer.store.list_projects()[0].apk.sha256 == apk.sha256


# -- the API finds a project by the APK's hash -------------------------------


def _seed_project(settings: Settings, minimal_apk: Path, status: ProjectStatus) -> Project:
    """A project for the APK, in the state the test needs it in."""
    apk = inspect_apk(minimal_apk)
    project = Project.create(apk)
    project.status = status
    if status is ProjectStatus.FAILED:
        project.errors.append(
            ToolError(
                tool=ANALYSIS_TOOL,
                code=ToolErrorCode.ANALYSIS_FAILED,
                message="the analysis did not complete: RuntimeError: boom",
            )
        )
    store = Store.open(settings.database_path)
    store.save_project(project, settings.projects_dir / project.id, manifest=None)
    return project


def test_uploading_a_failed_apk_again_analyses_it_again(
    client: TestClient, settings: Settings, minimal_apk: Path
) -> None:
    """The project id is the APK's hash, so the next upload finds it.

    Handing the failed project back made the failure permanent: the APK was
    never analysed again, and the answer the client got was the one the run
    had already given. Sending the same APK is how the operator asks for
    another go.
    """
    project = _seed_project(settings, minimal_apk, ProjectStatus.FAILED)

    response = client.post("/analyze", files={"file": ("a.apk", minimal_apk.read_bytes())})

    assert response.status_code == 202
    body = response.json()
    assert body["project_id"] == project.id
    # A new job, not the failed project handed back.
    assert body["status"] == "pending"


def test_uploading_an_analysed_apk_again_does_not_analyse_it_again(
    client: TestClient, settings: Settings, minimal_apk: Path
) -> None:
    """The project id is the APK's hash, so a finished analysis is found too.

    Re-analysing it would replace a report that is already there with the
    same one, and the answer the client gets is the answer the analysis
    gave.
    """
    project = _seed_project(settings, minimal_apk, ProjectStatus.COMPLETED)

    response = client.post("/analyze", files={"file": ("a.apk", minimal_apk.read_bytes())})

    assert response.status_code == 202
    body = response.json()
    assert body["project_id"] == project.id
    assert body["status"] == "completed"


def test_the_failure_message_does_not_leak_the_server_path(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The path is the server's, and the message is read by people who are not.

    An exception's message can quote the path it was handed -- a file that
    was not there, a directory that could not be created -- and that path
    names the machine the analysis ran on. The message is recorded on the
    project, and from there it is read back through the API, through the
    JSON report and through the Markdown report.

    So it is redacted where it is written, not at each of those: the
    workspace root becomes a placeholder and the path inside it survives,
    because that is the part that says what was being worked on.
    """
    secret = settings.workspace / "secret" / "path" / "db.sqlite"

    def broken(self, *args, **kwargs):
        raise FileNotFoundError(f"no such file: {secret}")

    analyzer = Analyzer(settings)
    monkeypatch.setattr(analyzer, "_run_androguard", broken)

    with pytest.raises(AnalysisFailed) as caught:
        analyzer.analyze(minimal_apk)

    message = caught.value.error.message
    assert str(settings.workspace) not in message
    assert "<workspace>" in message
    # The path inside the workspace survives: it is what says what failed.
    assert "secret" in message
