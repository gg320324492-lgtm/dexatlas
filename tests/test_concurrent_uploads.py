"""What happens when the same APK is uploaded twice at the same time.

The workbench promises that an APK the workspace already holds is not
analysed again. That promise only held when the uploads arrived one after
the other: the check and the start of the analysis were two separate
moments, and four uploads that arrived together all passed the check
before any of them had written a row. Four analyses of one APK then ran at
once, writing over each other's results.

The registry had the same shape of defect. It was keyed by the project id,
which is the APK's content hash, so two analyses under one project id
shared one key: the analysis that ended first unregistered the one that
was still running, and an analysis that is not registered cannot be
cancelled -- the cancel endpoint answered 409 for an analysis that was
running.

The versions had a third. The backends remember that they have been
probed *before* the probe finishes, so an analysis that arrived in that
window was handed ``None`` -- and the run it published said a backend that
took part was not installed.

These tests hold in place:

- Four concurrent uploads of one APK start exactly one analysis; the other
  three are told the APK is already being analysed, and one run row is
  written.
- One analysis ending does not unregister the one that is still running:
  that one is still cancellable, and its token really is cancelled.
- A backend that took part is never recorded as having no version, even
  when the analysis that found out ran beside another one.
"""

from __future__ import annotations

import os
import stat
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.uploads import run_background_analysis
from dexatlas.config.settings import Settings
from dexatlas.core.models import ApkMetadata, Project
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import AnalysisRun
from dexatlas.workbench.app import create_app
from tests.conftest import build_apk


def _wait_for(predicate: Any, timeout: float = 60.0) -> bool:
    """Wait until the predicate holds. Whether it ever did."""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


class _GatedAnalysis:
    """A stand-in for the analysis, so the other uploads arrive while it runs.

    The stand-in is the slow part of the pipeline; the claim, the check and
    the answer are the production ones, and the threads are real. Nothing
    in the code under test is told that a test is running.
    """

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.released = threading.Event()
        self.calls = 0
        self._lock = threading.Lock()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Put the stand-in in place of the pipeline's analysis."""
        state = self

        def analyze(
            analyzer: Analyzer,
            apk_path: Path,
            *,
            metadata: ApkMetadata | None = None,
            cancellation: Any = None,
            **_: Any,
        ) -> SimpleNamespace:
            with state._lock:
                state.calls += 1
            state.entered.set()
            if not state.released.wait(timeout=60):
                raise AssertionError("the test never released the analysis")
            assert metadata is not None
            # The project's row and the run's own row, the way the pipeline
            # writes them: the test counts the runs to see how many analyses
            # there were.
            project = Project.create(metadata)
            run = AnalysisRun.start(project.id, metadata.sha256)
            analyzer.store.begin_run(project)
            analyzer.store.create_run(run)
            return SimpleNamespace(succeeded=True)

        monkeypatch.setattr(Analyzer, "analyze", analyze)


def test_four_concurrent_uploads_of_one_apk_start_one_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One APK, four uploads at once, one analysis.

    The three uploads that lost the race are answered while the analysis is
    still running. That window is where the defect lived: the check that
    decided "nobody is analysing this APK" and the start of the analysis
    were two separate moments, and every upload that arrived in between
    passed the check.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    gate = _GatedAnalysis()
    gate.install(monkeypatch)

    payload = build_apk(tmp_path / "demo.apk").read_bytes()
    answers: list[dict[str, Any]] = []
    answered = threading.Condition()

    with TestClient(create_app(analyzer)) as client:

        def upload() -> None:
            response = client.post(
                "/api/analyze",
                files={"file": ("demo.apk", payload, "application/octet-stream")},
            )
            with answered:
                answers.append(response.json())
                answered.notify_all()

        threads = [threading.Thread(target=upload) for _ in range(4)]
        for thread in threads:
            thread.start()
        try:
            assert gate.entered.wait(timeout=60), "no analysis started"
            # The three that lost the claim answer while the winner is still
            # running; the winner answers when its analysis is done.
            assert _wait_for(lambda: len(answers) == 3), (
                f"only {len(answers)} of the four uploads answered while the "
                "analysis was running: the uploads that must find the analysis "
                "already running are waiting for an analysis of their own"
            )
        finally:
            gate.released.set()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive(), "an upload never answered"

    assert len(answers) == 4
    started = [answer for answer in answers if not answer["already_analysed"]]
    deduped = [answer for answer in answers if answer["already_analysed"]]
    assert len(started) == 1, "more than one upload started an analysis"
    assert len(deduped) == 3
    assert gate.calls == 1, "the APK was analysed more than once"
    # Every upload is pointed at the same project: the analysis that runs
    # is the one the browser has to watch.
    assert {answer["project_id"] for answer in answers} == {started[0]["project_id"]}
    assert started[0]["status"] == "pending"
    assert all(answer["status"] == "running" for answer in deduped)
    # One run row: one analysis, one attempt.
    assert len(analyzer.store.list_runs(started[0]["project_id"])) == 1


def test_an_analysis_that_ends_does_not_unregister_the_one_that_is_still_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One analysis ending must not unregister the one beside it.

    The project id is the first sixteen digits of the APK's hash, so two
    analyses under one project id are two different APKs whose hashes share
    those digits. The registry has to hold them apart: the one that ends
    first must not unregister the one that is still running, or that one
    cannot be cancelled any more -- and the cancel endpoint answered 409
    for an analysis that was running.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    apk = build_apk(tmp_path / "demo.apk")

    # Two hashes that share their first sixteen digits, and so share the
    # project id the analyses are registered under.
    first_hash = "ab" * 8 + "00" * 24
    second_hash = "ab" * 8 + "11" * 24
    project_id = Project.new_id(first_hash)
    assert project_id == Project.new_id(second_hash)

    gates = {first_hash: threading.Event(), second_hash: threading.Event()}
    tokens: dict[str, Any] = {}
    entered = threading.Semaphore(0)

    def analyze(
        analyzer: Analyzer,
        apk_path: Path,
        *,
        metadata: ApkMetadata | None = None,
        cancellation: Any = None,
        **_: Any,
    ) -> SimpleNamespace:
        assert metadata is not None
        tokens[metadata.sha256] = cancellation
        entered.release()
        if not gates[metadata.sha256].wait(timeout=60):
            raise AssertionError("the test never released the analysis")
        return SimpleNamespace(succeeded=True)

    monkeypatch.setattr(Analyzer, "analyze", analyze)
    metadatas = [
        ApkMetadata(sha256=first_hash, size_bytes=apk.stat().st_size, path=apk),
        ApkMetadata(sha256=second_hash, size_bytes=apk.stat().st_size, path=apk),
    ]

    with TestClient(create_app(analyzer)) as client:
        threads = [
            threading.Thread(target=run_background_analysis, args=(analyzer, apk, metadata))
            for metadata in metadatas
        ]
        for thread in threads:
            thread.start()
        assert entered.acquire(timeout=60), "the first analysis never started"
        assert entered.acquire(timeout=60), "the second analysis never started"

        # The first analysis ends while the second one is still running.
        gates[first_hash].set()
        threads[0].join(timeout=60)
        assert not threads[0].is_alive()

        response = client.post(f"/api/projects/{project_id}/cancel")

        assert response.status_code == 202, (
            f"the running analysis could not be cancelled: {response.text}"
        )
        assert response.json() == {"project_id": project_id, "status": "cancelling"}
        assert tokens[second_hash].cancelled

        gates[second_hash].set()
        threads[1].join(timeout=60)
        assert not threads[1].is_alive()


def _slow_jadx_launcher(directory: Path) -> Path:
    """A stand-in for the jadx launcher whose version probe takes a while.

    The probe is what the race is about: a backend remembers that it has
    been probed before the probe finishes, so the probe has to be slow
    enough for another analysis to arrive in the middle of it.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = directory / "jadx.bat"
        launcher.write_text(
            "@echo off\r\n"
            'echo %* | findstr /C:"--version" > nul\r\n'
            "if not errorlevel 1 ping -n 3 127.0.0.1 > nul\r\n"
            "echo jadx 1.5.2\r\n",
            encoding="utf-8",
        )
    else:
        launcher = directory / "jadx"
        launcher.write_text(
            '#!/bin/sh\ncase "$*" in\n  *--version*) sleep 2 ;;\nesac\necho "jadx 1.5.2"\n',
            encoding="utf-8",
        )
        launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    return launcher


def test_a_backend_that_took_part_is_never_recorded_without_a_version(
    tmp_path: Path,
) -> None:
    """The versions are probed once, and everybody reads the same answer.

    Two analyses run at the same time, so one of them arrives while the
    other is still probing. The backends remember that they have been
    probed before the probe finishes, so the second one used to be handed
    ``None`` -- and the run it published said a backend that took part was
    not installed.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    settings.jadx_path = str(_slow_jadx_launcher(tmp_path / "bin"))
    analyzer = Analyzer(settings)

    apks = [
        build_apk(tmp_path / "one.apk"),
        build_apk(tmp_path / "two.apk", extra={"META-INF/OTHER.RSA": b"other"}),
    ]
    results: list[Any] = []
    failures: list[BaseException] = []

    def analyse(apk: Path) -> None:
        try:
            results.append(analyzer.analyze(apk))
        except BaseException as exc:  # pragma: no cover - reported below
            failures.append(exc)

    threads = [threading.Thread(target=analyse, args=(apk,)) for apk in apks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=300)
        assert not thread.is_alive(), "an analysis did not finish"

    assert not failures, f"an analysis failed: {failures[0]}"
    assert len(results) == 2
    for result in results:
        assert result.run is not None
        versions = result.run.tool_versions
        assert versions["jadx"] == "jadx 1.5.2", (
            "a backend that took part was recorded as having no version"
        )
