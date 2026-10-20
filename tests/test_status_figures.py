"""The status page's numbers are measured, not written by hand.

The status page is the first thing a reader looks at, so its numbers are the
ones that have to be right — and they were the ones nobody checked. They were
typed into the page and left there, and they went stale the moment a test was
added.

They are now written by ``scripts/refresh-report-figures.py``, between the same
markers the execution report uses, and the page's numbers are the report's
numbers: one measurement, stated in two places, rather than two copies of it.
These checks are what keeps the two apart, and what notices a number somebody
typed into the page by hand.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "refresh-report-figures.py"

#: The documents the refresh points at a candidate copy of, so that a check
#: never sees a page that is half-refreshed.
STATUS = Path(os.environ.get("DEXATLAS_STATUS_PATH", REPO_ROOT / "docs" / "status.md"))
REPORT = Path(
    os.environ.get(
        "DEXATLAS_REPORT_PATH",
        REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md",
    )
)

#: The figures the status page states. The page is a summary; it does not
#: repeat the report's whole set of numbers.
STATUS_FIGURES = ("tests.total", "tests.fast", "tests.slow", "coverage.pct")


def _figure_script() -> ModuleType:
    """Load the script that writes the figures; the tests read its rules."""
    spec = importlib.util.spec_from_file_location("dexatlas_report_figures", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its dataclasses
    # resolve their annotations through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _figures(path: Path) -> dict[str, str]:
    """Every figure a document states, with the value it states it as."""
    script = _figure_script()
    return dict(script.FIGURE.findall(path.read_text(encoding="utf-8")))


def test_status_page_states_the_figures_it_owes() -> None:
    """A figure that quietly disappears is as wrong as one that is wrong."""
    stated = _figures(STATUS)
    missing = [key for key in STATUS_FIGURES if key not in stated]
    assert not missing, "the status page no longer states: " + ", ".join(missing)


def test_status_page_figures_match_the_report() -> None:
    """The page and the report state one measurement, not two copies of it.

    The report holds the measurement, and the page is a summary of it. A
    number typed into the page alone would be a number nothing stands behind,
    and the two documents would say different things about the same tree.
    """
    report = _figures(REPORT)
    status = _figures(STATUS)
    wrong = {
        key: (value, report.get(key)) for key, value in status.items() if report.get(key) != value
    }
    assert not wrong, (
        "the status page and the report state the same figure differently: "
        + "; ".join(
            f"{key}: page {page}, report {report_value}"
            for key, (page, report_value) in wrong.items()
        )
    )


def test_status_page_states_each_figure_one_way() -> None:
    """The same figure must not appear twice with two different values."""
    script = _figure_script()
    stated: dict[str, list[str]] = {}
    for key, value in script.FIGURE.findall(STATUS.read_text(encoding="utf-8")):
        stated.setdefault(key, []).append(value)
    inconsistent = {key: values for key, values in stated.items() if len(set(values)) > 1}
    assert not inconsistent, (
        "the status page states the same figure in two different ways: "
        + "; ".join(f"{key}: {values}" for key, values in sorted(inconsistent.items()))
    )
