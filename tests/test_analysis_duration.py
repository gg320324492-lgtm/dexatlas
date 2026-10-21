"""How long the analysis took is a measurement, and it is kept.

The REST API exports a report by rebuilding the analysis out of the
workspace. The rebuild did not set the duration, and the workspace had no
column to read it from, so every report exported over the API said
"Analysis time 0.0s" — for an analysis that had taken seconds. The number was
not a measurement of anything: it was the default of a field that was never
filled in, printed as if it were one.

The measurement now lives on the project, in the database, and both reports
state the number that was stored. A workspace written before the
measurement was stored holds none, and says that the time is unknown rather
than claiming a run took no time at all.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.models import ClassKind, ClassRef, Provenance
from dexatlas.core.pipeline import AnalysisResult, Analyzer
from dexatlas.core.storage import Store
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

#: How long the stand-in DEX reader takes, so that the measurement is one a
#: report can show: a run that takes a thousandth of a second is printed as
#: "0.0s", which is the very thing this is about.
_DURATION = 0.15

#: The row of the report's metric table that states the time.
_TIME_ROW = re.compile(r"^\| Analysis time \| (.+) \|$", re.MULTILINE)

#: The projects table as an earlier build wrote it: no duration column.
_OLD_PROJECTS = """
CREATE TABLE projects (
    id               TEXT PRIMARY KEY,
    apk_sha256       TEXT NOT NULL UNIQUE,
    apk_path         TEXT NOT NULL,
    apk_size_bytes   INTEGER NOT NULL,
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL,
    tool_versions    TEXT NOT NULL DEFAULT '{}',
    errors           TEXT NOT NULL DEFAULT '[]',
    class_count      INTEGER NOT NULL DEFAULT 0,
    method_count     INTEGER NOT NULL DEFAULT 0,
    reference_count  INTEGER NOT NULL DEFAULT 0,
    evidence_count   INTEGER NOT NULL DEFAULT 0,
    resource_count   INTEGER NOT NULL DEFAULT 0,
    manifest         TEXT,
    workspace        TEXT
)
"""


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """A client wired to an isolated workspace."""
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _slow_reader(monkeypatch: pytest.MonkeyPatch, analyzer: Analyzer) -> None:
    """A DEX reader that takes long enough for the measurement to be visible."""

    def extract(*args: object, **kwargs: object):
        time.sleep(_DURATION)
        return (
            [
                ClassRef(
                    name="com.example.C0",
                    kind=ClassKind.CLASS,
                    provenance=[
                        Provenance(
                            tool="androguard",
                            tool_version="4.1.4",
                            apk_sha256="a" * 64,
                            locator="classes.dex",
                        )
                    ],
                )
            ],
            [],
            [],
            [],
            [],
            None,
        )

    monkeypatch.setattr(analyzer._androguard, "extract", extract)


def _analysis_time(report: str) -> str:
    """The value the report's metric table states for the analysis time."""
    match = _TIME_ROW.search(report)
    assert match is not None, "the report states no analysis time"
    return match.group(1)


# -- the two exports state the same number ----------------------------------


def test_the_api_export_and_the_cli_export_state_the_same_time(
    client: TestClient, settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One measurement, stated in two places.

    The CLI exports the report it built; the API rebuilds the analysis out of
    the workspace and exports that. They are the same document, and they used
    to state different numbers for the same run.
    """
    analyzer = Analyzer(settings)
    _slow_reader(monkeypatch, analyzer)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    response = client.get(f"/projects/{result.project.id}/report", params={"format": "markdown"})
    assert response.status_code == 200

    cli_report = render_markdown(result)
    api_report = response.text

    assert _analysis_time(cli_report) == _analysis_time(api_report)
    assert _analysis_time(cli_report) != "unknown"


def test_the_time_the_report_states_is_not_zero(
    client: TestClient, settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The number has to be a measurement, and "0.0s" is not one.

    Zero is what a field that was never filled in prints as, and a report
    that states it is claiming a run that took no time.
    """
    analyzer = Analyzer(settings)
    _slow_reader(monkeypatch, analyzer)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    response = client.get(f"/projects/{result.project.id}/report", params={"format": "markdown"})

    assert _analysis_time(response.text) != "0.0s"
    assert _analysis_time(response.text) != "0s"
    assert float(_analysis_time(response.text).rstrip("s")) > 0


def test_the_json_export_states_the_same_time(
    client: TestClient, settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The JSON report is the same document in another form."""
    analyzer = Analyzer(settings)
    _slow_reader(monkeypatch, analyzer)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    response = client.get(f"/projects/{result.project.id}/report", params={"format": "json"})
    assert response.status_code == 200

    summary = response.json()["summary"]
    assert summary["duration_seconds"] == round(result.project.duration_seconds, 2)
    assert summary["duration_seconds"] > 0
    assert build_json_report(result)["summary"]["duration_seconds"] == summary["duration_seconds"]


# -- the measurement is stored ---------------------------------------------


def test_the_measurement_is_stored_with_the_project(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The number has to be in the database, or the rebuild has nothing to read."""
    analyzer = Analyzer(settings)
    _slow_reader(monkeypatch, analyzer)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    stored = analyzer.store.get_project(result.project.id)
    assert stored is not None
    assert stored.duration_seconds is not None
    assert stored.duration_seconds == result.project.duration_seconds
    assert stored.duration_seconds > 0

    with analyzer.store.transaction() as connection:
        row = connection.execute(
            "SELECT duration_seconds FROM projects WHERE id = ?", (result.project.id,)
        ).fetchone()
    assert row is not None
    assert row["duration_seconds"] == stored.duration_seconds


# -- a workspace written before the measurement was stored -------------------


def test_an_older_workspace_is_given_the_column_and_holds_no_measurement(
    tmp_path: Path,
) -> None:
    """An old row holds no measurement, and reads as none.

    The column is added in place, so the rows keep their values — and the
    rows that were written before the measurement was stored never had one.
    """
    path = tmp_path / "dexatlas.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_info (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_info (version) VALUES (2)")
        connection.execute(_OLD_PROJECTS)
        connection.execute(
            "INSERT INTO projects (id, apk_sha256, apk_path, apk_size_bytes, created_at, status)"
            " VALUES ('apk_0123456789abcdef', ?, 'demo.apk', 10, '2020-01-01T00:00:00+00:00',"
            " 'completed')",
            ("a" * 64,),
        )

    store = Store.open(path)

    with store.transaction() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
    assert "duration_seconds" in columns

    project = store.get_project("apk_0123456789abcdef")
    assert project is not None
    assert project.duration_seconds is None


def test_a_report_for_an_older_workspace_says_the_time_is_unknown(tmp_path: Path) -> None:
    """ "0.0s" would be a measurement nobody took."""
    path = tmp_path / "dexatlas.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_info (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_info (version) VALUES (2)")
        connection.execute(_OLD_PROJECTS)
        connection.execute(
            "INSERT INTO projects (id, apk_sha256, apk_path, apk_size_bytes, created_at, status)"
            " VALUES ('apk_0123456789abcdef', ?, 'demo.apk', 10, '2020-01-01T00:00:00+00:00',"
            " 'completed')",
            ("a" * 64,),
        )

    store = Store.open(path)
    project = store.get_project("apk_0123456789abcdef")
    assert project is not None
    result = AnalysisResult(project=project, manifest=None, evidence=[])

    report = render_markdown(result)

    assert _analysis_time(report) == "unknown"
    assert "| Analysis time | 0.0s |" not in report
    assert build_json_report(result)["summary"]["duration_seconds"] is None
