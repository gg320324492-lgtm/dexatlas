"""The numbers the measurement writes, and the run that cannot count.

Two things are tested here.

The first is the hard insurance. pytest prints its counts in one line, and a
run that does not have that line has not said how many tests passed. Reading
the counts as zero would publish a number that describes a suite that ran
nothing -- which is a fact, and a false one. So the run stops instead, and
says what it measured and what it did not; a fact that was not measured is
not a fact of zero.

The second is the mechanism the numbers travel on. A document that carries a
generated figure is written from the one measurement, so the number in the
page and the number in the report are one fact rather than two copies of it,
and a page that states a number does not have to be remembered when the
number changes: the marker is the whole of the registration.

The suite that checks these is the suite the measurement runs, so the checks
themselves change what the report says -- the report's own self-checks are
measured apart from the code tests, and this file is one of them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SCRIPT = REPO_ROOT / "scripts" / "refresh-report-figures.py"


def _figure_script() -> Any:
    """The refresh script, loaded as a module for direct inspection."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("dexatlas_figures_auto_write", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# -- the hard insurance -------------------------------------------------


def test_a_run_whose_summary_line_cannot_be_read_is_not_read_as_zero() -> None:
    """A run that cannot be counted stops; it does not report zero.

    The counts were read out of the whole output when no summary line could
    be found, and a run whose output says nothing about how many tests
    passed comes out of that as zero passed, zero failed, zero skipped. Zero
    is a measurement -- "the suite ran nothing" -- and a run that could not
    read the line measured nothing of the kind.

    This is not a hypothetical: on the v1.0.0 tag the measurement job read a
    self-check run of thirteen tests, one of which had failed, as a run of
    zero tests. The numbers did not add up to the tree, the job went red,
    and the message it printed named a wrong cause.
    """
    script = _figure_script()

    with pytest.raises(script.SummaryUnreadable):
        script.outcome_counts("ERROR: interrupted: collection was cancelled\n")


def test_a_run_that_prints_its_summary_line_is_still_counted() -> None:
    """The insurance does not stop the runs that can be counted."""
    script = _figure_script()

    counts = script.outcome_counts(
        "================ 1 failed, 12 passed, 1682 deselected in 12.11s ================\n"
    )

    assert counts["passed"] == 12, counts
    assert counts["failed"] == 1, counts
    assert counts["deselected"] == 1682, counts


def test_the_error_reaches_the_run_and_not_only_the_reader_of_the_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run that cannot be counted stops the measurement, not just the parse.

    The measurement is a chain: the run, the parser, the report. A parser
    that shrugged and returned zero would let the chain carry a number that
    describes nothing, and the report would be written from it.
    """
    script = _figure_script()

    def fake_run(*args: str, **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(args), returncode=0, stdout="the run said nothing\n", stderr=""
        )

    monkeypatch.setattr(script, "run", fake_run)

    with pytest.raises(script.SummaryUnreadable):
        script.measure_tests(["-k", "nothing"])


def test_the_run_says_what_it_measured_and_what_it_did_not(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run that stops says which of its facts it established.

    A measurement that could not be taken is not a measurement of zero, and a
    reader who is told "zero" goes looking for a broken suite instead of a
    broken reader. So the run names the facts it established and the facts
    it did not, and says that nothing was written: a report that still
    describes the tree it was measured on is worth more than a report that
    describes a run that never happened.
    """
    script = _figure_script()
    ledger = script.Ledger()
    ledger.expect("the fingerprint of the tree")
    ledger.expect("the tests the suite collects")
    ledger.expect("the coverage of the tree")
    ledger.note("the fingerprint of the tree", "sha256:abc")

    code = script.abort(script.SummaryUnreadable("the suite", "boom\n"), ledger)

    out = capsys.readouterr().out
    assert code == 1
    assert "the fingerprint of the tree: sha256:abc" in out, out
    assert "What this run measured:" in out, out
    assert "What this run did not measure:" in out, out
    assert "the tests the suite collects" in out, out
    assert "the coverage of the tree" in out, out
    assert "Nothing was written" in out, out


# -- the mechanism the numbers travel on ---------------------------------


def test_a_figure_inside_a_code_block_is_an_illustration_and_not_a_figure() -> None:
    """A page that shows what a marker looks like is not carrying a number.

    The page that teaches the reader what ``<!--fig:...-->`` is shows the
    marker inside a code block, and the glossary says the same thing in a
    sentence. Neither is a number for the script to fill in, and rewriting
    one would turn an illustration into a measurement nobody asked for.
    """
    script = _figure_script()

    assert script.live_figures("```text\n<!--fig:tests.total-->1712<!--/fig-->\n```\n") == []
    assert script.live_figures("the `<!--fig:tests.total-->1712<!--/fig-->` marker") == []
    assert script.live_figures("<!--fig:tests.total-->1712<!--/fig-->") == ["tests.total"]


def test_a_document_that_carries_a_figure_is_written_from_the_measurement(
    tmp_path: Path,
) -> None:
    """Adding a marker to a page is all it takes to have the number written.

    The document is found by its marker -- there is no list of pages to add
    it to -- and the measured number is written into it, so a page that
    states a number does not have to be remembered when the number changes.
    """
    script = _figure_script()
    page = tmp_path / "page.md"
    page.write_text("The suite has <!--fig:tests.total-->1<!--/fig--> tests.\n", encoding="utf-8")

    assert script.documents_with_figures(tmp_path) == [page]

    refreshed = script.write_figures(page, {"tests.total": "1712"})
    assert refreshed == "The suite has <!--fig:tests.total-->1712<!--/fig--> tests.\n"


def test_a_figure_the_measurement_cannot_fill_stops_the_refresh(tmp_path: Path) -> None:
    """A number behind a marker nobody can fill in is a number written by hand.

    The script stops instead of guessing, because a guessed number is a
    number that looks measured and is not: the reader has no way to tell it
    from the ones that are.
    """
    script = _figure_script()
    page = tmp_path / "page.md"
    page.write_text("<!--fig:suite.measured-->1<!--/fig-->\n", encoding="utf-8")

    with pytest.raises(SystemExit) as stopped:
        script.write_figures(page, {"tests.total": "1712"})

    assert "suite.measured" in str(stopped.value)


def test_every_generated_number_in_the_repository_is_written_by_the_measurement() -> None:
    """No number hides behind a marker that nothing writes.

    A marker in a document the script does not write is a number written by
    hand: it says "1712" because somebody typed it, and it stays that way
    until somebody notices. The script writes every document that carries a
    marker, so the only way such a number can exist is in a document it must
    not write -- a release note, a historical record -- and that is an error
    rather than a policy.
    """
    script = _figure_script()

    for path in script.markdown_documents(REPO_ROOT):
        text = path.read_text(encoding="utf-8")
        figures = script.live_figures(text)
        if not figures:
            continue
        assert not script.excluded_from_writing(path), (
            f"{path.name} carries generated figures ({', '.join(sorted(set(figures)))}), "
            "but it is a document the measurement must not write: the number behind "
            "the marker would be written by hand."
        )


def test_the_documents_the_measurement_writes_are_the_ones_that_carry_figures() -> None:
    """The report and the status page are written because they carry figures.

    They are the two pages that state the measurement today, and the script
    finds the pages by their markers rather than by a list, so this is a
    statement about what the mechanism covers rather than about a list that
    has to be kept up to date by hand.
    """
    script = _figure_script()

    found = script.documents_with_figures(REPO_ROOT)

    assert script.REPORT_PATH in found, found
    assert script.STATUS_PATH in found, found
