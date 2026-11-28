"""The numbers the outward materials carry, and the text that gets sent.

The materials under ``docs/outreach/`` are pasted into forms and attached to
proposals.  Their numbers used to be copied in by hand, and a hand-copied
number is the most perishable thing in this project: between 2026-11-27 and
2026-11-28 it was re-copied three times -- 1887, 1915, 1931 -- each time by
a person who had to remember that four files and six places held a number
the measurement had already moved past.

The numbers are generated now.  ``scripts/refresh-report-figures.py`` writes
them between ``<!--fig:...-->`` markers, out of the same measurement that
writes the execution report, and ``scripts/export-outreach.py`` renders the
markers to the plain text that is sent.

Three things are tested here, and each of them is the failure that would
make the mechanism a decoration:

* the **materials carry markers** rather than hand-written numbers, so a
  re-measurement moves them without anybody remembering;
* the **export carries no markup**, because markup in a proposal is a bug
  with a client's name on it;
* the **gate still sees them** -- a number inside a marker is not a claim
  the text makes, it is a claim the *measurement* makes, and a gate that
  ignores it has stopped guarding.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

OUTREACH = REPO_ROOT / "docs" / "outreach"

#: The materials that are sent to somebody.
OUTWARD = (
    "cover-letter-templates.md",
    "project-brief.md",
    "scope-backend-automation.md",
)

#: The internal record.  It is not sent, so it is not exported, but it
#: carries the same numbers and it is written by the same measurement.
INTERNAL = "publish-review.md"

#: ``<!--fig:key-->value<!--/fig-->``.
FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)


def _script(name: str) -> ModuleType:
    """A script under ``scripts/``, loaded as a module."""
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"dexatlas_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _version_claims() -> ModuleType:
    return _script("check-version-claims.py")


def _export() -> ModuleType:
    return _script("export-outreach.py")


def _text(name: str) -> str:
    return (OUTREACH / name).read_text(encoding="utf-8")


def _report_figures() -> dict[str, str]:
    """The figures the execution report holds.

    They are read out of the report rather than written down here: the report
    is what the measurement writes, and a number copied into this file would
    be a second copy of the truth -- the very mistake this mechanism exists
    to end.
    """
    report = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
    return dict(FIGURE.findall(report.read_text(encoding="utf-8")))


def _section(text: str, name: str) -> str | None:
    """One section of a document, by its heading.

    The rule is the one ``publish-review.md`` §5 records: a ``## `` heading
    opens a section; it runs to the next one, or to a line that is only
    ``---``; the heading itself is not part of it.
    """
    out: str | None = None
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current and out is not None:
                break
            if line[3:].strip().startswith(name):
                out = line[3:].strip()
                current = []
                continue
            current = []
            continue
        if line.strip() == "---":
            if out is not None:
                break
            continue
        if out is not None:
            current.append(line)
    if out is None:
        return None
    return "\n".join(current).strip("\n")


def _plain(text: str) -> str:
    """A text without its Markdown syntax.

    The cleaning rule is the one ``publish-review.md`` §5 records, so the
    length this returns is the length a form receives.
    """
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(-|\d+\.)\s+", "    ", line)
        line = re.sub(r"^>\s?", "", line)
        line = re.sub(r"^#+\s*", "", line)
        lines.append(line.rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


# -- the materials carry generated figures -------------------------------


@pytest.mark.parametrize("name", (*OUTWARD, INTERNAL))
def test_the_materials_carry_generated_figures(name: str) -> None:
    """A number in a material is between markers, not written by hand.

    A hand-written number is a number nobody has to remember to move, and
    this one was moved three times in two days.  The marker is what makes
    the re-measurement reach the material on its own.
    """
    figures = dict(FIGURE.findall(_text(name)))

    assert "tests.total.grouped" in figures, f"{name} states no test count"
    assert "coverage.pct" in figures, f"{name} states no coverage"


@pytest.mark.parametrize("name", OUTWARD)
def test_a_material_states_no_hand_written_test_count(name: str) -> None:
    """The number that is written by hand is the number the gate finds.

    The gate reads the numbers a text states outside its markers, and the
    materials' numbers are all inside their markers -- so a number written
    by hand among them would be the one number that nothing checks.

    The internal record is not checked here: it is a record of what earlier
    rounds found, and the numbers in it are the numbers *of those rounds*.
    It is not sent, and a history that had to be re-measured would stop
    being a history.
    """
    text = _text(name)
    # The markers are blanked out first: what is left is what a person wrote.
    spoken = FIGURE.sub(lambda match: " " * len(match.group(0)), text)

    stated = re.findall(r"(?<![\d,])(\d[\d,]*)\s+(?:[A-Za-z]+\s+){0,2}?tests\b", spoken)

    assert not stated, f"{name} states a test count by hand: {stated}"


def test_the_materials_carry_only_keys_the_measurement_writes() -> None:
    """Every key a material carries is one the measurement knows.

    The measurement **refuses** a figure it cannot fill in, and it says so
    by stopping the whole refresh.  A material is therefore read by the
    writer on every refresh, and a key nobody carries would hold the
    refresh up.

    This test says that about the keys, not about their values.  The
    values are the measurement's business: the measurement writes the
    materials *after* it has run the suite, so a test that demanded the
    materials already agree with the report would demand the refresh of
    something the refresh itself produces -- and the refresh would never
    finish.  That agreement is the gate's job
    (``check-version-claims.py``'s ``check_outward_figures``), which runs
    on a tree that is not being measured.
    """
    script = _script("refresh-report-figures.py")
    report = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
    record = script.read_record(report.read_text(encoding="utf-8"))
    values = script.render_figures(record)

    for name in (*OUTWARD, INTERNAL):
        for key, _value in FIGURE.findall(_text(name)):
            assert key in values, (
                f"{name} carries the marker {key}, and the measurement does not know "
                "how to fill it in -- that stops the whole refresh"
            )


# -- the export carries no markup ----------------------------------------


@pytest.mark.parametrize("name", OUTWARD)
def test_the_exported_text_carries_no_marker(name: str) -> None:
    """What is sent has no markup in it.

    A marker pasted into a form is visible markup in front of a client, and
    the file that is sent is the exported one, not the source.
    """
    export = _export()
    values = export.outward_figures()
    output, unknown = export.render(_text(name), values)

    assert not unknown, f"{name}: {unknown} could not be filled"
    assert "<!--fig:" not in output, f"{name}: the exported text still carries a marker"
    assert not export.residue(output), f"{name}: {export.residue(output)} left in the export"


@pytest.mark.parametrize("name", OUTWARD)
def test_the_exported_text_states_the_measured_number(name: str) -> None:
    """The export carries the number the report holds.

    Rendering the markers is not enough: the rendered text has to say the
    number the measurement measured, in the spelling a person writes.
    """
    export = _export()
    values = export.outward_figures()
    output, _unknown = export.render(_text(name), values)
    report = _report_figures()

    assert values["tests.total.grouped"] in output
    assert values["coverage.pct"] in output
    assert export.figure_number(values["tests.total.grouped"]) == export.figure_number(
        report["tests.total"]
    )


def test_the_internal_record_is_not_exported() -> None:
    """The internal record is not sent, so it is not exported.

    Its own header says it is a checking record and not an attachment.
    Exporting it would put the internal path, the commit and the draft
    status in front of a client.
    """
    export = _export()

    assert INTERNAL not in export.EXPORTED
    assert "publish-review.md" not in {path.name for path in export.exported_sources()}


def test_the_export_is_written_outside_the_repository() -> None:
    """The rendered copy is not versioned.

    Its content is decided by the current measurement, and it changes every
    time the measurement does.  A rendered copy in the repository would be a
    second copy of a number -- the thing this mechanism exists to end.
    """
    export = _export()

    assert ".scratch" in export.EXPORT_ROOT.parts
    assert not export.EXPORT_ROOT.is_relative_to(REPO_ROOT / "docs")


# -- the gate still sees them --------------------------------------------


def test_the_gate_reports_a_figure_that_drifted_from_the_report() -> None:
    """A number written by hand inside a marker is found.

    The gate ignores the numbers inside markers, because a generated number
    is not a claim the text makes.  That is right for a number the
    measurement wrote, and it is how a hand-written number inside a marker
    would go unnoticed -- so the figures are checked as well.
    """
    checker = _version_claims()
    export = _export()
    figures = _report_figures()
    values = export.outward_figures()
    # A number that is not the measured one, derived rather than written
    # down: a fixed "9,999" would stop being a drift the day the suite
    # reached 9,999, and the test would pass for the wrong reason.
    wrong_total = int(values["tests.total"]) + 1
    wrong_coverage = float(values["coverage.pct"].rstrip("%")) + 1.0
    drifted = "docs/outreach/project-brief.md"
    text = (
        f"<!--fig:tests.total.grouped-->{wrong_total:,}<!--/fig--> automated tests, "
        f"<!--fig:coverage.pct-->{wrong_coverage:.1f}%<!--/fig--> coverage\n"
    )

    findings = checker.check_outward_figures(drifted, text, figures, "1.2.0")

    kinds = {finding.kind for finding in findings}
    assert "outward-figure" in kinds, findings
    assert len(findings) == 2, findings


def test_the_gate_does_not_report_a_figure_that_agrees_with_the_report() -> None:
    """A figure that agrees is not a finding.

    The values are read out of the report rather than written down here.
    A number copied into this file would be a second copy of the truth --
    the same mistake the materials used to make, one level down, and it
    would go stale exactly like the one it replaced.
    """
    checker = _version_claims()
    export = _export()
    figures = _report_figures()
    values = export.outward_figures()
    text = (
        f"<!--fig:tests.total.grouped-->{values['tests.total.grouped']}<!--/fig--> "
        f"automated tests, <!--fig:coverage.pct-->{values['coverage.pct']}<!--/fig--> "
        "coverage\n"
    )

    findings = checker.check_outward_figures(
        "docs/outreach/project-brief.md", text, figures, "1.2.0"
    )

    assert not findings, findings


def test_the_gate_reports_a_figure_it_cannot_compare() -> None:
    """A figure the gate has no answer for is a finding.

    A number nobody checks is a number nobody can trust, and a figure the
    gate does not know about is exactly that.
    """
    checker = _version_claims()
    figures = _report_figures()
    text = "<!--fig:tests.invented-->1<!--/fig--> tests\n"

    findings = checker.check_outward_figures(
        "docs/outreach/project-brief.md", text, figures, "1.2.0"
    )

    assert [finding.kind for finding in findings] == ["outward-figure-unknown"], findings


def test_a_percentage_is_compared_as_a_percentage() -> None:
    """A drifted coverage is found.

    ``plain_number`` reads "1,938" and returns nothing for "93.4%" -- so
    two percentages would both read as nothing, and would compare equal.
    That is how a coverage could drift by half a point without the gate
    noticing.
    """
    checker = _version_claims()

    assert checker.figure_number("93.4%") == 93.4
    assert checker.figure_number("1,938") == 1938
    assert checker.figure_number("1,938") == checker.figure_number("1938")
    assert checker.figure_number("93.4%") != checker.figure_number("95.0%")


def test_the_gate_still_checks_the_numbers_written_by_hand() -> None:
    """The gate did not lose the check it already had.

    The materials' numbers are all inside markers now, so the part of the
    gate that reads a number a text states has nothing left to read there.
    The figures check replaces that work; this test says the other half --
    the counts the materials state in the review table's own spelling -- is
    still read.

    The counts are read out of the report rather than written down here: a
    number copied into this file would be a second copy of the truth, and
    it would go stale exactly like the one it replaced.
    """
    checker = _version_claims()
    export = _export()
    figures = _report_figures()
    values = export.outward_figures()
    total = values["tests.total.grouped"]
    fast = values["tests.fast.grouped"]
    slow = values["tests.slow.grouped"]

    findings = checker.check_outward_counts(
        "docs/outreach/publish-review.md",
        f"| 测试总数 | {total}（{fast} 快 + {slow} 集成） |\n",  # noqa: RUF001
        figures,
        11,
        3,
        "1.2.0",
        [],
    )

    assert not findings, findings

    drifted = checker.check_outward_counts(
        "docs/outreach/publish-review.md",
        f"| 测试总数 | {int(values['tests.total']) + 1:,}（{fast} 快 + {slow} 集成） |\n",  # noqa: RUF001
        figures,
        11,
        3,
        "1.2.0",
        [],
    )

    assert drifted, drifted


# -- the measurement writes the materials --------------------------------


def test_the_measurement_writes_the_outward_materials() -> None:
    """The materials are written by the measurement, not excluded from it.

    They used to be excluded: the reason was that they are sent out, and a
    marker in a text that is pasted into a form is visible markup.  The
    export answers that, and without this the numbers would go back to being
    copied by hand.
    """
    script = _script("refresh-report-figures.py")

    for name in (*OUTWARD, INTERNAL):
        path = OUTREACH / name
        assert not script.excluded_from_writing(path), f"{name} is excluded from the measurement"


def test_the_measurement_writes_the_grouped_spelling_of_a_count() -> None:
    """The prose spelling of a count is generated too.

    The report writes ``1938`` in a table cell; a person writing a count in
    a sentence writes ``1,938``.  Both are one number, and the second is
    derived from the first rather than copied.
    """
    script = _script("refresh-report-figures.py")

    assert script.grouped(1938) == "1,938"
    assert script.grouped("1938") == "1,938"
    assert script.grouped("93.4%") == "93.4%", "a percentage is not a count"


def test_no_material_writes_a_literal_marker_as_an_example() -> None:
    """A marker written as an example must not be one the writer chokes on.

    The measurement refuses a figure it cannot fill, and it says so by
    stopping the whole refresh -- a document that shows the reader what a
    marker looks like can therefore hold the refresh up, if the key it
    shows is one nobody carries.  A literal ``<!--fig:...-->`` is exactly
    that: a key that is not a key.

    The materials are read by the writer on every refresh, so this is
    pinned here rather than left to whoever writes the next example.
    """
    script = _script("refresh-report-figures.py")
    report = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
    record = script.read_record(report.read_text(encoding="utf-8"))
    values = script.render_figures(record)

    for name in (*OUTWARD, INTERNAL):
        text = _text(name)
        for key, _value in FIGURE.findall(text):
            assert key in values, (
                f"{name} carries the marker {key}, and the measurement does not know "
                "how to fill it in -- that stops the whole refresh"
            )


def test_the_exported_material_still_fits_the_platform_limits() -> None:
    """The exported text must still fit the field it goes into.

    This is the check that caught a regression this round: a paragraph of
    usage notes was added to the head of three outward materials, and it
    pushed one of them from 4,941 characters to 5,381 -- over the 5,000
    character limit of the field it was going into, by 381 characters.

    The limits are the platform's, not this project's, and the counting
    method is the one ``publish-review.md`` §5 records: a section is
    measured, not the whole file -- ``cover-letter-templates.md`` is two
    letters, and each one is pasted into its own field.

    What is checked here is the fact that matters: **the exported text
    fits the field it goes into.**  The measured lengths in the table are
    the measurement's business; the limit is the platform's.
    """
    export = _export()
    values = export.outward_figures()

    # The piece of each material that is pasted into a field, and the limit
    # of that field.  A section is what gets pasted into the platform's
    # field; the whole file is what gets attached.
    limits = {
        ("cover-letter-templates.md", "Template 1"): 2500,
        ("cover-letter-templates.md", "Template 2"): 2500,
        ("scope-backend-automation.md", "What I offer"): 5000,
    }

    for (name, section), limit in limits.items():
        output, _unknown = export.render(_text(name), values)
        body = _section(output, section)
        assert body is not None, f"{name} has no section {section}"
        length = len(_plain(body).strip("\n"))
        assert length <= limit, (
            f"{name} §{section} is {length} characters once exported, and the "
            f"field it goes into takes {limit}. It is on the line -- cut "
            "something, or take the length back out of the material itself."
        )


def test_the_exported_material_still_fits_as_an_attachment() -> None:
    """The whole exported file must still fit the field it is attached to.

    This is the check that caught a regression this round: a paragraph of
    usage notes was added to the head of three outward materials, and it
    pushed one of them from 4,941 characters to 5,381 -- over the 5,000
    character limit, by 381 characters.

    The note was added at the *head*, so a check that only measured the
    ``What I offer`` section would not have seen it.  A material is pasted
    into a field *or* attached whole, and the whole one has to fit too.
    """
    export = _export()
    values = export.outward_figures()

    limits = {
        "scope-backend-automation.md": 5000,
    }

    for name, limit in limits.items():
        output, _unknown = export.render(_text(name), values)
        length = len(_plain(output).strip("\n"))
        assert length <= limit, (
            f"{name} is {length} characters once exported, and the field it is "
            f"attached to takes {limit}."
        )
