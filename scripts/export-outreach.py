#!/usr/bin/env python3
"""Render the outward materials to the plain text that gets sent.

    uv run --no-sync python scripts/export-outreach.py
    uv run --no-sync python scripts/export-outreach.py --check

The problem this closes
-----------------------
The materials under ``docs/outreach/`` are sent to other platforms: pasted
into a form, attached to a proposal, mailed to a client.  Their numbers --
the test count, the coverage -- used to be copied in by hand, and a
hand-copied number is the most perishable thing in this project: between
2026-11-27 and 2026-11-28 it was re-copied three times (1887, 1915, 1931),
each time by a person who had to remember that four files and six places
held a number that the measurement had already moved past.

The numbers are generated now.  ``scripts/refresh-report-figures.py`` writes
them into the materials between ``<!--fig:...-->`` markers, out of the same
measurement that writes the execution report -- so the number in a proposal
and the number in the report are one fact rather than two copies of it.

**But a marker is not something you can paste into a form.**  ``<!--fig:
tests.total.grouped-->1,938<!--/fig-->`` is 46 characters of markup around
a number that is 5 characters long, and pasting it into a proposal form
would put the markup in front of a client.  So the material in the
repository is a *source*, and what gets sent is what this script renders
out of it.

The two are different things, and the repository is where the source
belongs: a source is edited, reviewed and diffed; a rendered copy is not
edited, and its content is decided by the current measurement, so it is not
versioned either.  It is written to ``.scratch/outreach-export/``.

What is exported, and what is not
---------------------------------
Three of the files are outward material.  ``publish-review.md`` is not: it
says so in its own header -- it is the internal checking record, and the
numbers it states are the same generated ones, so it is written by the
measurement like the rest, but there is nothing to send.

``--check`` is the gate: it renders the materials and compares the result
with the sources, and fails when a marker is left in what would be sent, or
when a source holds a marker whose value the report does not carry.  A
source that drifts from the report is the failure this project cares about,
and it is caught here rather than by whoever remembers to run the refresh.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent

#: ``<!--fig:key-->value<!--/fig-->`` -- the same syntax the measurement writes
#: and the release-number gate reads.  One syntax for the whole project: a
#: second one here would be a second thing to keep right.
FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)

#: The materials that are sent to somebody.  ``publish-review.md`` is not in
#: this list on purpose: its own header says it is an internal record, it is
#: not attached to a proposal and it does not go out with one.
EXPORTED = (
    "cover-letter-templates.md",
    "project-brief.md",
    "scope-backend-automation.md",
)

#: Where the rendered copies are written.  ``.scratch/`` is gitignored: the
#: rendered copy is decided by the current measurement, and it changes every
#: time the measurement does.
EXPORT_ROOT = REPO_ROOT / ".scratch" / "outreach-export"

#: The report that holds the measured figures.  It is the authority: the
#: materials and the report are written from the same measurement, and this
#: script renders the materials from the report, so a number that the report
#: does not carry cannot be sent.
REPORT = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"


def measurement_script() -> ModuleType | None:
    """The measurement script, loaded as a module.

    How a file is read out of a tree is one rule and it lives in the script
    that owns it.  The rule this script asks for -- how a count is spelled in
    prose -- is the measurement script's, because the measurement script
    writes that spelling into the materials themselves.  A second copy of it
    here would be a second answer to the same question, and the second one
    is the one that drifts.

    The module has to be in ``sys.modules`` before it runs: a module whose
    annotations resolve through itself fails to import otherwise.
    """
    script = REPO_ROOT / "scripts" / "refresh-report-figures.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("dexatlas_refresh_figures", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # A rule that cannot be asked is a fallback, not a failure: the
        # grouping rule below is the same one the measurement script holds,
        # and a script that cannot be loaded means this one has to carry it.
        return None
    return module


def report_figures() -> dict[str, str]:
    """The figures the execution report records.

    They are read out of the report rather than written down here.  A list of
    expected values in this file would be a second copy of the truth -- the
    same mistake the materials used to make, one level down.
    """
    if not REPORT.is_file():
        return {}
    return dict(FIGURE.findall(REPORT.read_text(encoding="utf-8")))


#: The keys whose value the report carries in a different spelling.
#:
#: The report writes its counts in a table cell (``1938``); the outward
#: materials are prose, and a person writing a count in a sentence writes
#: ``1,938``.  Both spellings are one number, and both are derived from the
#: one measurement: the report's value is the measurement, and the grouped
#: spelling is that value written the way a person writes it.  Deriving the
#: second from the first -- here, rather than by copying either one -- is
#: what keeps them one fact.
GROUPED = {
    "tests.total.grouped": "tests.total",
    "tests.fast.grouped": "tests.fast",
    "tests.slow.grouped": "tests.slow",
    "coverage.covered.grouped": "coverage.covered",
    "coverage.total.grouped": "coverage.total",
}


def grouped(value: str) -> str:
    """A count as a person writes it: ``1,938``.

    The value is a whole number of lines or tests.  A value that is not one
    -- a percentage, say -- is returned as it is: adding a separator to it
    would make a number nobody wrote.

    The rule belongs to the measurement script, which writes the same
    spelling into the materials themselves, so it is asked there rather than
    written out again here.  Two copies of one rule are two answers to one
    question, and the second one is the one that drifts.
    """
    measurement = measurement_script()
    if measurement is not None:
        return str(measurement.grouped(value))
    stripped = value.replace(",", "")
    if not stripped.isdigit():
        return value
    return f"{int(stripped):,}"


def figure_number(value: str) -> float | None:
    """A number a figure holds, read the way the figure writes it.

    The figures are counts ("1,938") and percentages ("93.4%").  A number
    that cannot be read is read as nothing, so the two spellings of one
    number -- "1,938" and "1938" -- are one number here too.
    """
    text = value.strip().rstrip("%").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def outward_figures() -> dict[str, str]:
    """Every figure the outward materials may carry.

    The report's own figures, plus the grouped spelling of the counts, taken
    from the report's figures rather than measured again.
    """
    values = dict(report_figures())
    for key, source in GROUPED.items():
        if source in values:
            values[key] = grouped(values[source])
    return values


def render(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Render the markers of a text to their values.

    Returns the rendered text and the keys that were left unfilled.  A key
    the report does not carry is left in place as the marker it is: a
    placeholder nobody can fill is better than a number nobody can trace,
    and the caller reports it rather than sending it.
    """
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            unknown.append(key)
            return match.group(0)
        return values[key]

    return FIGURE.sub(replace, text), unknown


def exported_sources() -> list[Path]:
    """The materials that are sent, and that this script renders."""
    directory = REPO_ROOT / "docs" / "outreach"
    found = [directory / name for name in EXPORTED]
    return [path for path in found if path.is_file()]


def export(values: dict[str, str]) -> list[tuple[Path, str, list[str]]]:
    """Render every material, and say which keys each one left unfilled."""
    rendered: list[tuple[Path, str, list[str]]] = []
    for path in exported_sources():
        text = path.read_text(encoding="utf-8")
        output, unknown = render(text, values)
        rendered.append((path, output, unknown))
    return rendered


def write_exports(rendered: list[tuple[Path, str, list[str]]]) -> list[Path]:
    """Write the rendered materials, and say where they went."""
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path, output, _unknown in rendered:
        target = EXPORT_ROOT / path.name
        target.write_text(output, encoding="utf-8", newline="\n")
        written.append(target)
    return written


def residue(text: str) -> list[str]:
    """The markers a rendered text still carries.

    A rendered text that still holds a marker is a text with markup in it,
    and markup in a proposal is a bug with a client's name on it.
    """
    return [match.group(1) for match in FIGURE.finditer(text)]


def check(values: dict[str, str]) -> list[str]:
    """The problems that must keep the export from being sent.

    Two kinds, and both are failures of the same promise: what is sent
    carries no markup, and every number in it is a number the measurement
    stands behind.
    """
    problems: list[str] = []
    for path, output, unknown in export(values):
        for key in sorted(set(unknown)):
            problems.append(
                f"{path.relative_to(REPO_ROOT).as_posix()}: the marker {key} is not "
                "a figure the report carries, so it cannot be rendered"
            )
        for key in residue(output):
            problems.append(
                f"{path.relative_to(REPO_ROOT).as_posix()}: the marker {key} is "
                "still in the rendered text"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    """Render the materials, or check that they could be rendered."""
    parser = argparse.ArgumentParser(
        description="Render the outward materials to the plain text that gets sent."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check that every material renders, and that nothing is left marked",
    )
    args = parser.parse_args(argv)

    values = outward_figures()
    if not values:
        print(
            f"the report {REPORT.relative_to(REPO_ROOT).as_posix()} carries no figures, "
            "so there is nothing to render the materials from"
        )
        return 1

    if args.check:
        problems = check(values)
        if problems:
            for problem in problems:
                print(f"FAIL {problem}")
            print(f"\n{len(problems)} problem(s) in the outward materials.")
            return 1
        rendered = export(values)
        print(f"PASS {len(rendered)} outward material(s) render, and none is left marked.")
        return 0

    rendered = export(values)
    written = write_exports(rendered)
    for path, output, unknown in rendered:
        name = path.relative_to(REPO_ROOT).as_posix()
        left = sorted(set(unknown))
        note = f" ({len(left)} marker(s) not filled: {', '.join(left)})" if left else ""
        print(f"{name} -> {len(output)} characters{note}")
    print()
    for target in written:
        print(f"  {target.relative_to(REPO_ROOT).as_posix()}")
    print(f"Written to {EXPORT_ROOT.relative_to(REPO_ROOT).as_posix()}/")
    print("That is the text to send. The files in the repository are the source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
