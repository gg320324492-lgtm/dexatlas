"""The refresh measures one tree, and says so.

The coverage data file is where an interrupted measurement leaves its
numbers behind: a run that is stopped before pytest-cov erases the file
leaves a partial record of whatever it had covered, and the next
measurement adds itself to that record. The refresh must clear the file
before it measures, because a measurement that starts from somebody else's
numbers describes a tree that no longer exists.
"""

from __future__ import annotations

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
