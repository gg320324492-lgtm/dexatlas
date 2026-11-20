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
    # The code run asks the collector how many tests the ignored file holds;
    # a collector that is not running answers "none" rather than crashing on
    # a command that never ran.
    monkeypatch.setattr(script, "collected_page_checks", lambda: 0)

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


# -- the measurement gate ---------------------------------------------------
#
# A measurement is complete when it accounted for every test the tree
# collects, when nothing failed, and when the machine has everything the
# report names as the basis of its coverage numbers. It is not complete
# because it skipped the same tests the recorded measurement skipped: that
# says which machine the run was on, not whether the tree was measured.
#
# The tests below keep that true. They run on every platform: the skips
# they describe are the ones a platform makes, and a test that only failed
# on one of them would not be a test.


def _gate_record(total: int = 4, passed: int = 4, skipped: int = 0) -> dict[str, Any]:
    """The record of a measurement taken where nothing skipped.

    It carries the table audit the way the measuring script writes one: the
    refresh states the audit even when it states nothing was wrong, and a
    record without the key would make every ``--check`` below look stale
    against a report the script had really written.
    """
    return {
        "schema": 4,
        "code": {"api_endpoints": 1, "cli_commands": 1, "sample_apks": 1},
        "coverage": {"files": {"cli/main.py": [10, 1]}, "missing": 1, "statements": 10},
        "history": {},
        "source_fingerprint": "sha256:recorded",
        "suite": {
            "passed": passed,
            "skipped": skipped,
            "xfailed": 0,
            "failed": 0,
            "xpassed": 0,
            "skipped_tests": [],
            "xfailed_tests": [],
        },
        "table": {"missing_rows": [], "stale_rows": []},
        "tests": {"fast": total - 1, "slow": 1, "total": total},
    }


def _gate_report(script: Any, record: dict[str, Any]) -> str:
    """A report that states the figures of the record, the way the script writes them."""
    values = script.render_figures(record)
    return (
        "# A report\n\n"
        f"Tests: <!--fig:tests.total-->{values['tests.total']}<!--/fig--> "
        f"<!--fig:tests.fast-->{values['tests.fast']}<!--/fig--> "
        f"<!--fig:tests.slow-->{values['tests.slow']}<!--/fig-->\n"
        f"Passed: <!--fig:suite.passed-->{values['suite.passed']}<!--/fig--> "
        f"<!--fig:suite.skipped-->{values['suite.skipped']}<!--/fig--> "
        f"<!--fig:suite.xfailed-->{values['suite.xfailed']}<!--/fig-->\n"
        f"Coverage: <!--fig:coverage.pct-->{values['coverage.pct']}<!--/fig--> "
        f"<!--fig:coverage.covered-->{values['coverage.covered']}<!--/fig--> "
        f"<!--fig:coverage.total-->{values['coverage.total']}<!--/fig-->\n"
        "<!--fig:coverage.weak_modules-->" + values["coverage.weak_modules"] + "<!--/fig-->\n"
        "<!--report-figures:" + script.render_record(record) + "-->\n"
    )


def _stub_measurement(
    script: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    total: int,
    passed: int,
    skipped: int,
    prerequisites: list[str] | None = None,
    self_check_failures: tuple[str, ...] = (),
) -> None:
    """Stub the measurement: the suite ran, and some of its tests sat out.

    ``deselected`` counts the report's own self-checks: the code run leaves
    them out and measures them on their own, so they are the tests that make
    the tree bigger than the code run.
    """
    deselected = total - passed - skipped
    monkeypatch.setattr(
        script,
        "measure_code_tests",
        lambda: script.Outcome(
            counts={
                "passed": passed,
                "failed": 0,
                "skipped": skipped,
                "xfailed": 0,
                "xpassed": 0,
                "error": 0,
                "deselected": deselected,
            },
            failures=(),
            skipped=tuple(f"tests/test_platform.py::test_{n}" for n in range(skipped)),
        ),
    )
    monkeypatch.setattr(
        script,
        "measure_report_checks",
        lambda candidate, report_path: script.Outcome(
            counts={"passed": deselected, "failed": 0, "skipped": 0, "xfailed": 0},
            failures=self_check_failures,
        ),
    )
    monkeypatch.setattr(
        script,
        "measure_status_checks",
        lambda *args: script.Outcome(counts={"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}),
    )
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 1]}, statements=10, missing=1),
    )
    # The script checks that the coverage run and the tree name the same
    # modules, so the tree is the one the stubbed coverage measured.
    monkeypatch.setattr(script, "source_statements", lambda: {"cli/main.py": 10})
    monkeypatch.setattr(
        script,
        "collected_tests",
        lambda marker: (1, total) if marker == "slow" else (total - 1, total),
    )
    monkeypatch.setattr(script, "collected_at_tag", lambda tag: None)
    monkeypatch.setattr(script, "missing_prerequisites", lambda: prerequisites or [])
    monkeypatch.setattr(script, "source_fingerprint", lambda: "sha256:recorded")
    monkeypatch.setattr(
        script,
        "code_facts",
        lambda: {"api_endpoints": 1, "cli_commands": 1, "sample_apks": 1},
    )


def test_a_measurement_that_skipped_the_platform_tests_is_not_thrown_away(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tests a platform makes skip are not a reason to discard the run.

    The Windows-only tests skip on Linux by design, so a Linux run skips
    tests a Windows run did not. That says which machine the run was on, not
    whether the tree was measured -- and the run that judged it by the
    identities of the skipped tests threw the measurement away, kept the
    recorded figures and reported success. The figures of a tree that was
    measured are the ones this run measured.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_measurement(script, monkeypatch, total=4, passed=2, skipped=1)

    script.main(["--report", str(report)])

    written = script.read_record(report.read_text(encoding="utf-8"))
    assert written["suite"]["skipped"] == 1, (
        "the run threw the measurement away and kept the recorded one: the report's "
        "figures are not the ones this tree measured"
    )
    assert written["suite"]["skipped_tests"] == ["tests/test_platform.py::test_0"]
    assert written["suite"]["passed"] == 3


def test_a_run_that_could_not_measure_the_tree_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gate that cannot fail is not a gate.

    A run that could not measure the tree kept the recorded figures and
    reported success, so the CI job that asks whether the report's figures
    describe the tagged tree was green because it never looked. A run that
    measured nothing has to say so with its exit code.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_measurement(
        script,
        monkeypatch,
        total=4,
        passed=2,
        skipped=1,
        prerequisites=["JADX (bash scripts/install-backends.sh)"],
    )

    code = script.main(["--report", str(report), "--check"])

    assert code != 0, (
        "a run that could not measure the tree reported success: the measurement gate cannot fail"
    )


def _stub_runs_around_the_real_code_run(
    script: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    total: int,
    passed: int,
    skipped: int,
    ignored: int,
) -> None:
    """Stub the runs *around* the real ``measure_code_tests``.

    The code run's summary line carries the tests it ran and the tests the
    ``-k`` deselected; the page self-checks it ``--ignore``s never reach it.
    ``ignored`` is what pytest's collector says the ignored file holds. The
    real ``measure_code_tests`` has to add that count back itself: the
    accounting below compares its outcome against ``total``.
    """
    monkeypatch.setattr(
        script,
        "measure_tests",
        lambda args, env=None, **_: script.Outcome(
            counts={
                "passed": passed,
                "failed": 0,
                "skipped": skipped,
                "xfailed": 0,
                "xpassed": 0,
                "error": 0,
                "deselected": 0,
            },
            failures=(),
        ),
    )
    monkeypatch.setattr(script, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(script, "collected_page_checks", lambda: ignored)
    # The self-check rounds add the tests the code run left out back into
    # the suite, the way the real page-check round does for the ignored
    # file's tests.
    monkeypatch.setattr(
        script,
        "measure_report_checks",
        lambda candidate, report_path: script.Outcome(
            counts={"passed": ignored, "failed": 0, "skipped": 0, "xfailed": 0},
            failures=(),
        ),
    )
    monkeypatch.setattr(
        script,
        "measure_status_checks",
        lambda *args: script.Outcome(counts={"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}),
    )
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 1]}, statements=10, missing=1),
    )
    # The script checks that the coverage run and the tree name the same
    # modules, so the tree is the one the stubbed coverage measured.
    monkeypatch.setattr(script, "source_statements", lambda: {"cli/main.py": 10})
    monkeypatch.setattr(
        script,
        "collected_tests",
        lambda marker: (1, total) if marker == "slow" else (total - 1, total),
    )
    monkeypatch.setattr(script, "collected_at_tag", lambda tag: None)
    monkeypatch.setattr(script, "missing_prerequisites", lambda: [])
    monkeypatch.setattr(script, "source_fingerprint", lambda: "sha256:recorded")
    monkeypatch.setattr(
        script,
        "code_facts",
        lambda: {"api_endpoints": 1, "cli_commands": 1, "sample_apks": 1},
    )


def test_the_tests_the_code_run_ignores_are_still_accounted_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A test the code run set aside with ``--ignore`` did not vanish.

    The how-to-verify pages' self-checks are left out of the code run with
    ``--ignore`` on their file, so pytest never collects them and its
    summary line carries none of them. The accounting that compared the run
    against the tree the collector found read their absence as tests that
    went unmeasured, threw the measurement away and refused to write the
    figures -- on a tree the run had, in fact, measured, because those very
    checks are measured on their own and added up with the rest.

    The run has to add the count of the ignored file back before it asks
    whether the tree was measured.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_runs_around_the_real_code_run(
        script, monkeypatch, total=4, passed=2, skipped=1, ignored=1
    )

    code = script.main(["--report", str(report)])

    assert code == 0, (
        "the run threw the measurement away: the tests the code run ignored were "
        "not added back to the accounting, and the gate read a measured tree as "
        "an unmeasured one"
    )
    written = script.read_record(report.read_text(encoding="utf-8"))
    assert written["suite"]["passed"] == 3, written["suite"]
    assert written["tests"]["total"] == 4


def test_the_accounting_cannot_count_an_ignored_file_that_no_longer_has_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ignored count comes from the collector, not from a constant.

    A count typed into the script would survive the file it describes: a
    file whose tests are all gone would still add its old count to the
    accounting, and the gate would accept a measurement of a smaller tree.
    The count is asked of pytest's collector, the same collector the tree
    count comes from, so the two cannot drift.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_runs_around_the_real_code_run(
        script, monkeypatch, total=4, passed=2, skipped=1, ignored=0
    )

    code = script.main(["--report", str(report)])

    assert code != 0, (
        "a run that ignored tests it did not count reported success: the accounting "
        "must read the ignored count from the collector, not from a constant"
    )


def test_the_check_measures_the_reports_own_self_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The self-checks are part of the measurement, not a formality.

    The run that judged the measurement by the identities of the skipped
    tests never measured the report's own self-checks, so a report whose
    figures disagree with its own record passed. A run that measured the
    tree has to measure those too.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_measurement(
        script,
        monkeypatch,
        total=4,
        passed=2,
        skipped=1,
        self_check_failures=("tests/test_docs.py::test_execution_report_numbers",),
    )

    code = script.main(["--report", str(report), "--check"])

    assert code != 0, "the report's own self-checks failed and the run reported success"


def test_a_coverage_figure_no_measurement_produces_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check compares the numbers with the measurement, not with the record.

    Two measurements of one tree on one machine are comparable, so the
    coverage they measured has to be the coverage the report states.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_measurement(script, monkeypatch, total=4, passed=3, skipped=0)
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 5]}, statements=10, missing=5),
    )

    code = script.main(["--report", str(report), "--check"])

    assert code != 0, "a coverage figure that no measurement of this tree produces was accepted"


def test_the_check_does_not_compare_the_coverage_of_two_different_machines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two measurements that left different tests unexercised are two numbers.

    The Windows-only tests skip on Linux and nowhere else, so a Linux run
    and the Windows record describe different code: the coverage of the one
    is the coverage of the code the other did not run. Comparing them would
    be comparing a Windows number with a Linux number, so the check says so
    instead of failing on it. The figures that describe the tree are
    compared either way.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_gate_report(script, _gate_record()), encoding="utf-8")
    _stub_measurement(script, monkeypatch, total=4, passed=2, skipped=1)
    monkeypatch.setattr(
        script,
        "read_coverage",
        lambda: script.Coverage(files={"cli/main.py": [10, 5]}, statements=10, missing=5),
    )

    code = script.main(["--report", str(report), "--check"])

    out = capsys.readouterr().out
    assert code == 0, (
        "the check compared the coverage of two measurements that exercised different code:\n" + out
    )
    assert "were not compared" in out


def test_a_run_whose_summary_line_follows_a_failure_is_still_counted() -> None:
    """A run with a failure in it has its counts read.

    pytest prints the failed test's assertion in the short summary, and that
    line contains an ``==``. A reader that lets its match cross a line starts
    there, runs on into the next line and swallows the ``=`` rules that open
    the summary line: the last match is then the tail of that summary with
    nothing in it, and a run that passed twelve tests and failed one comes
    out as zero passed and zero failed.

    The summary line is only preceded by an ``assert`` line when something
    failed, which is why this stayed hidden: locally every self-check passed,
    on the runner one failed, and only there did the run print the line that
    broke the reader. The output below is the runner's, trimmed to the part
    that matters.
    """
    script = _figure_script()
    output = (
        "=========================== short test summary info ============================\n"
        "FAILED tests/test_docs.py::test_execution_report_suite_figures_add_up_to_the_tests"
        "_that_exist - AssertionError: the report says 1681 passed, 1 skipped, 0 xfailed, "
        "0 failed and 0 xpassed, which is 1682\n"
        "assert 1682 == 1695\n"
        "================ 1 failed, 12 passed, 1682 deselected in 12.11s ================\n"
    )

    counts = script.outcome_counts(output)

    assert counts["passed"] == 12, counts
    assert counts["failed"] == 1, counts
    assert counts["deselected"] == 1682, counts


def test_a_failure_whose_id_carries_a_parameter_is_still_listed() -> None:
    """A parametrized test's id has a space in it, and it is still listed.

    pytest writes the parameters into the id: ``test_x[not slow-docs/a.md]``.
    A reader that stops at the first blank drops that failure from the list,
    so a run with eight failures was reported as having six -- and the reader
    was left looking for two problems that were not in the run at all.
    """
    script = _figure_script()
    output = (
        "=========================== short test summary info ============================\n"
        "FAILED tests/test_how_to_verify.py::test_the_expected_output_of_the_collect_command"
        "_is_what_the_suite_prints[not slow-docs/how-to-verify.md] - AssertionError: the "
        "page's expected output is not what the suite prints\n"
        "FAILED tests/test_docs.py::test_execution_report_exists - AssertionError: nope\n"
    )

    failures = script.failed_tests(output)

    assert len(failures) == 2, failures
    assert "not slow-docs/how-to-verify.md" in failures[0], failures
    assert "test_execution_report_exists" in failures[1], failures
