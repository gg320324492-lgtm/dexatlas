"""What a reader sees while an analysis is still running.

The desktop application reads the project's runs to answer "which backends
took part in this analysis". That answer comes from the run's
``tool_versions``. It is set on the run the moment the backends are
probed -- but it was only **written down** when the run's row was next
saved, and the next save happened at the first stage transition after the
probe.

The gap was visible. Between the run's row being created and the first
stage transition after the probe, the row on disk still carried the empty
map it was created with. A reader that asked "which backends are
installed" in that window was told the machine had none of them -- on a
machine where all three were installed and working. The same answer came
back correct once the analysis moved past that window, because the next
stage transition saved the row again with the versions on it. That is the
worst shape for this kind of defect: the answer depends on when you ask.

These tests hold in place:

- The run's ``tool_versions`` are on disk while the analysis is still
  running, not only after it has moved past the first stage transition.
- The versions on the run are the ones the backends report.
- A run that is cancelled still carries them.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ClassKind, ClassRef, Project
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import AnalysisCancelled, CancellationToken, RunStatus
from dexatlas.tools.androguard.adapter import AndroguardBackend


def _patch_dex_reader(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """Give the run some symbols without needing a real DEX reader."""

    def extract(self: AndroguardBackend, apk: Path, apk_sha256: str, **kwargs: object):
        return (
            [
                ClassRef(
                    name=name,
                    kind=ClassKind.CLASS,
                    apk_path="classes.dex",
                    method_count=1,
                    field_count=0,
                )
            ],
            [],
            [],
            [],
            [],
            None,
        )

    monkeypatch.setattr(AndroguardBackend, "extract", extract)


def _metadata(apk: Path):
    """The metadata the pipeline itself would compute for this APK.

    The project id is a hash of the APK's own bytes, so a made-up sha
    would name a project that does not exist.
    """
    from dexatlas.core.ingest import inspect_apk

    return inspect_apk(apk)


class _PausedAnalysis:
    """An analysis that stops at a named point, so a reader can look.

    The pause is what makes this test about a *running* analysis rather
    than a finished one. ``where`` says which point to stop at:

    - ``"probe"`` -- inside the version probe, before the versions are
      known. This is the window where the run's row used to say nothing
      at all about the backends.
    - ``"stage"`` -- after the probe, before the first stage transition.
      This is the window where the row used to say nothing, because the
      next save was the stage transition itself.
    """

    def __init__(self, where: str = "stage") -> None:
        self.where = where
        self.reached = threading.Event()
        self.resume = threading.Event()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        paused = self
        from dexatlas.core.evidence import EvidenceBuilder
        from dexatlas.tools.registry import BackendRegistry

        if paused.where == "probe":
            original = BackendRegistry.versions

            def versions(self: BackendRegistry) -> dict[str, str | None]:
                paused.reached.set()
                assert paused.resume.wait(timeout=30), "the test never released the probe"
                return original(self)

            monkeypatch.setattr(BackendRegistry, "versions", versions)
            return

        original_add = EvidenceBuilder.add_dex_files

        def add_dex_files(self: EvidenceBuilder) -> None:
            paused.reached.set()
            assert paused.resume.wait(timeout=30), "the test never released the analysis"
            original_add(self)

        monkeypatch.setattr(EvidenceBuilder, "add_dex_files", add_dex_files)


def test_the_run_carries_the_backend_versions_while_the_analysis_runs(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reader polling a running analysis must see the versions.

    The versions are probed once, at the start of the run, and the run's
    row is written at that point too. So a reader that asks "which
    backends are installed" during the analysis gets the same answer it
    gets after the analysis ends.
    """
    analyzer = Analyzer(settings)
    paused = _PausedAnalysis()
    paused.install(monkeypatch)

    failure: list[BaseException] = []

    def run() -> None:
        try:
            analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
        except BaseException as exc:  # the test reports whatever came out
            failure.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    assert paused.reached.wait(timeout=30), "the analysis never reached the pause"

    # This is the reader's view: the run is on disk, and it is still
    # running. What does it say about the backends?
    project_id = Project.create(_metadata(minimal_apk)).id
    runs = analyzer.store.list_runs(project_id)
    assert len(runs) == 1
    stored = runs[0]
    assert stored.status is RunStatus.RUNNING

    paused.resume.set()
    worker.join(timeout=30)
    assert not failure, failure

    assert stored.tool_versions.get("androguard") is not None, (
        "the running run's row carries no backend versions, so a reader "
        "polling a running analysis is told the machine has no backends"
    )


def test_the_run_names_the_backends_before_their_versions_are_probed(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The names are known before the versions are.

    Probing a backend's version means running it, and that takes long
    enough to be a window a reader can land in. A reader who lands there
    must be told "this backend is taking part, its version is not known
    yet", not "this backend is not installed" -- the second one is a lie
    about the machine, and it is what the desktop application said.
    """
    analyzer = Analyzer(settings)
    paused = _PausedAnalysis(where="probe")
    paused.install(monkeypatch)

    failure: list[BaseException] = []

    def run() -> None:
        try:
            analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
        except BaseException as exc:  # the test reports whatever came out
            failure.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    assert paused.reached.wait(timeout=30), "the analysis never reached the probe"

    project_id = Project.create(_metadata(minimal_apk)).id
    runs = analyzer.store.list_runs(project_id)
    assert len(runs) == 1
    stored = runs[0]
    assert stored.status is RunStatus.RUNNING

    # The names are there; the versions are not known yet.
    assert "androguard" in stored.tool_versions, (
        "the run's row names no backends while the probe is running, so a "
        "reader polling a running analysis is told the machine has none"
    )
    assert stored.tool_versions["androguard"] is None

    paused.resume.set()
    worker.join(timeout=30)
    assert not failure, failure

    # And once the probe is done, the versions are on the row.
    after = analyzer.store.list_runs(project_id)[0]
    assert after.tool_versions.get("androguard") is not None


def test_the_versions_on_the_run_are_the_ones_the_backends_report(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the run says is what the backends say.

    The run's versions are not a guess and not a copy of the project's
    published snapshot: they are the versions probed for this run.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    result = analyzer.analyze(minimal_apk, include_apktool=False, include_jadx=False)
    assert result.run is not None

    stored = analyzer.store.get_run(result.run.id)
    assert stored is not None
    assert stored.tool_versions == result.project.tool_versions
    assert stored.tool_versions.get("androguard") is not None


def test_a_cancelled_run_still_carries_the_versions(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cancellation does not erase what the machine has installed.

    The versions are a fact about the machine, not about the outcome.
    """
    analyzer = Analyzer(settings)
    _patch_dex_reader(monkeypatch, "com.fake.One")

    token = CancellationToken()
    token.cancel()

    with pytest.raises(AnalysisCancelled):
        analyzer.analyze(
            minimal_apk,
            include_apktool=False,
            include_jadx=False,
            cancellation=token,
        )

    project_id = Project.create(_metadata(minimal_apk)).id
    runs = analyzer.store.list_runs(project_id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.CANCELLED
    assert runs[0].tool_versions.get("androguard") is not None
