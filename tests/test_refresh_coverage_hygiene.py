"""The refresh measures one tree, and says so.

The coverage data file is where an interrupted measurement leaves its
numbers behind: a run that is stopped before pytest-cov erases the file
leaves a partial record of whatever it had covered, and the next
measurement adds itself to that record. The refresh must clear the file
before it measures, because a measurement that starts from somebody else's
numbers describes a tree that no longer exists.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SCRIPT = REPO_ROOT / "scripts" / "refresh-report-figures.py"


def _figure_script() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("dexatlas_report_figures_hygiene", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_refresh_discards_stale_coverage_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A leftover .coverage must not reach the measurement.

    The file is written before the refresh runs — the record of a run that
    was interrupted — and the measurement must start from nothing, so the
    script deletes it before asking the suite to run.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_minimal_report(), encoding="utf-8")

    stale = REPO_ROOT / ".coverage"
    stale.write_bytes(b"stale data from an interrupted run")
    seen_at_measure_time: list[bool] = []

    def measure_code_tests() -> Any:
        seen_at_measure_time.append(stale.exists())
        return script.Outcome(
            counts={"passed": 1, "failed": 0, "skipped": 0, "xfailed": 0, "deselected": 0},
            failures=(),
        )

    def measure_report_checks(candidate: str, report_path: Path) -> Any:
        return script.Outcome(counts={"passed": 2, "failed": 0, "skipped": 0, "xfailed": 0})

    def measure_status_checks(
        report_candidate: str, status_candidate: str, report_path: Path, status_path: Path
    ) -> Any:
        return script.Outcome(counts={"passed": 2, "failed": 0, "skipped": 0, "xfailed": 0})

    monkeypatch.setattr(script, "measure_code_tests", measure_code_tests)
    monkeypatch.setattr(script, "measure_report_checks", measure_report_checks)
    monkeypatch.setattr(script, "measure_status_checks", measure_status_checks)
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 1]}, statements=10, missing=1),
    )
    monkeypatch.setattr(script, "collected_tests", lambda marker: (1, 1))
    monkeypatch.setattr(script, "collected_at_tag", lambda tag: None)

    script.main(["--report", str(report)])

    assert seen_at_measure_time == [False], (
        "the measurement ran while a stale .coverage was still present"
    )
    assert not stale.exists()


def test_the_refresh_starts_from_a_clean_file_even_after_a_crash(tmp_path: Path) -> None:
    """The erase has to survive a run that never got as far as pytest-cov's.

    pytest-cov erases the file when a run *starts*, so a run that is
    interrupted before that — a crash during collection, a Ctrl-C — leaves
    the file behind. The refresh's own erase does not depend on the run
    getting anywhere: it happens before the suite is started at all.
    """
    script = _figure_script()
    stale = REPO_ROOT / ".coverage"
    stale.write_bytes(b"partial record of an interrupted run")
    try:
        script.discard_stale_coverage()
        assert not stale.exists()
    finally:
        if stale.exists():
            stale.unlink()


def test_the_measurement_tells_its_processes_which_data_file_to_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The measurement's numbers must land in a file of its own.

    ``.coverage`` belongs to the whole checkout: a ``pytest --cov`` that does
    not ask to append replaces it wholesale. A measurement that reads that
    file can therefore read another run's numbers -- the doc tests' coverage
    instead of the suite's -- and publish them as the project's own. The
    measurement names its own file, and every process it starts is told to
    write there.
    """
    script = _figure_script()
    captured: dict[str, Any] = {}

    def fake_measure_tests(args: list[str], env: dict[str, str] | None = None, **_: Any) -> Any:
        captured["env"] = env
        return script.Outcome(
            counts={"passed": 1, "failed": 0, "skipped": 0, "xfailed": 0, "deselected": 0},
            failures=(),
        )

    monkeypatch.setattr(script, "measure_tests", fake_measure_tests)
    monkeypatch.setattr(script, "run", lambda *args, **kwargs: None)

    script.measure_code_tests()

    env = captured["env"]
    assert env is not None, "the measurement ran its suite without an environment"
    assert "COVERAGE_FILE" in env, "the measurement did not say where to write its coverage"
    assert Path(env["COVERAGE_FILE"]) != REPO_ROOT / ".coverage", (
        "the measurement wrote to the file every process in the checkout shares"
    )
    assert Path(env["COVERAGE_FILE"]).exists() or Path(env["COVERAGE_FILE"]).parent.exists()


def test_a_concurrent_coverage_run_cannot_replace_the_measurement_data() -> None:
    """The shared file is not the measurement's file.

    What a concurrent ``pytest --cov`` does to ``.coverage`` is replace it.
    The measurement's data file lives elsewhere, so that replacement cannot
    reach the numbers the report is about to publish.
    """
    script = _figure_script()
    data_file = script.measurement_data_file("a-concurrent-run")
    try:
        data_file.write_bytes(b"the suite's coverage")

        shared = REPO_ROOT / ".coverage"
        shared.write_bytes(b"the doc tests' coverage")
        try:
            assert data_file.read_bytes() == b"the suite's coverage", (
                "a concurrent coverage run replaced the measurement's data"
            )
        finally:
            shared.unlink(missing_ok=True)
    finally:
        shutil.rmtree(data_file.parent, ignore_errors=True)


def test_a_second_measurement_in_the_same_checkout_is_refused(tmp_path: Path) -> None:
    """Two measurements would fight over the report.

    Whichever finished last would write the numbers the other one measured.
    The slot is an operating-system lock, so it is released when the process
    holding it ends, and a measurement that finds it taken must say so
    rather than race.
    """
    script = _figure_script()
    lock = tmp_path / "measure.lock"

    first = script.try_measurement_slot(lock)
    assert first is not None, "the first measurement could not take the slot"
    try:
        assert script.try_measurement_slot(lock) is None, (
            "a second measurement was allowed to take a slot that was already taken"
        )
    finally:
        first.close()

    again = script.try_measurement_slot(lock)
    assert again is not None, "the slot was not released when its holder ended"
    again.close()


def test_the_slot_guards_the_checkout_report_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run pointed at another document does not fight over this one.

    The slot exists so that two measurements do not write the same report.
    A run that writes a copy somewhere else -- the test suite refreshes
    copies of the report -- leaves the checkout's report alone, so the slot
    must not refuse it.
    """
    script = _figure_script()
    monkeypatch.setattr(script, "MEASUREMENT_LOCK", tmp_path / "measure.lock")

    def measure_code_tests() -> Any:
        return script.Outcome(
            counts={"passed": 1, "failed": 0, "skipped": 0, "xfailed": 0, "deselected": 0},
            failures=(),
        )

    def measure_report_checks(candidate: str, report_path: Path) -> Any:
        return script.Outcome(counts={"passed": 2, "failed": 0, "skipped": 0, "xfailed": 0})

    def measure_status_checks(
        report_candidate: str, status_candidate: str, report_path: Path, status_path: Path
    ) -> Any:
        return script.Outcome(counts={"passed": 2, "failed": 0, "skipped": 0, "xfailed": 0})

    monkeypatch.setattr(script, "measure_code_tests", measure_code_tests)
    monkeypatch.setattr(script, "measure_report_checks", measure_report_checks)
    monkeypatch.setattr(script, "measure_status_checks", measure_status_checks)
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 1]}, statements=10, missing=1),
    )
    monkeypatch.setattr(script, "collected_tests", lambda marker: (1, 1))
    monkeypatch.setattr(script, "collected_at_tag", lambda tag: None)

    copy = tmp_path / "a-copy-of-the-report.md"
    copy.write_text(_minimal_report(), encoding="utf-8")

    slot = script.try_measurement_slot()
    assert slot is not None
    try:
        script.main(["--report", str(copy)])
        refused = capsys.readouterr().out
        assert "already running in this checkout" not in refused, (
            "a run that writes another document was refused by the checkout's slot"
        )

        script.main([])
        refused = capsys.readouterr().out
        assert "already running in this checkout" in refused, (
            "a second run that would write the checkout's report was not refused"
        )
    finally:
        slot.close()


def _minimal_report() -> str:
    """A report with the figures and the record the refresh script owns."""
    record = {
        "schema": 4,
        "code": {"api_endpoints": 1, "cli_commands": 1, "sample_apks": 1},
        "coverage": {"files": {"cli/main.py": [10, 1]}, "missing": 1, "statements": 10},
        "source_fingerprint": "sha256:stale",
        "suite": {
            "passed": 1,
            "skipped": 0,
            "xfailed": 0,
            "failed": 0,
            "xpassed": 0,
            "skipped_tests": [],
            "xfailed_tests": [],
        },
        "tests": {"fast": 1, "slow": 0, "total": 1},
    }
    import json

    return (
        "# A report\n\n"
        "Tests: <!--fig:tests.total-->1<!--/fig--> "
        "<!--fig:tests.fast-->1<!--/fig--> <!--fig:tests.slow-->0<!--/fig-->\n"
        "Coverage: <!--fig:coverage.pct-->90.0%<!--/fig--> "
        "<!--fig:coverage.covered-->9<!--/fig--> "
        "<!--fig:coverage.total-->10<!--/fig-->\n"
        "<!--fig:coverage.weak_modules-->\n| 模块 | 覆盖率 | 未覆盖行 / 总行数 |\n"
        "|------|--------|------------------|\n"
        "| `cli/main.py` | 90.0% | 1 / 10 |\n<!--/fig-->\n"
        "<!--report-figures:" + json.dumps(record) + "-->\n"
    )
