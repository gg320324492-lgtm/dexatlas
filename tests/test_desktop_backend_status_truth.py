"""The backend status card must be able to tell two apart that look alike.

The card on the analysis page answers one question per backend: what
happened to it in *this* analysis.  Two of the facts it needs come from
the backend and are easy to confuse:

* the run's ``tool_versions`` says which versions the run **recorded** --
  and a recorded version may be ``null``;
* ``GET /api/backends`` says which backends are **installed on this
  machine**.

A ``null`` version means one of two things -- "not probed yet" or "not
installed" -- and the run's record cannot tell them apart.  Measured on
the packaged executable on 2026-11-27, both were said wrong: an analysis
in progress called three installed backends "not installed", and a
finished analysis on a machine without jadx/apktool kept calling them
"version being probed" long after the probing was over.

The mapping itself is unit-tested by the desktop's own door
(``desktop/src/stages.test.ts``, vitest); what this file pins down is the
**wiring** -- that the page actually hands the machine's list to the
mapping, so the two facts cannot drift apart again.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PAGE = ROOT / "desktop" / "src" / "pages" / "Analysis.tsx"
STAGES_MODULE = ROOT / "desktop" / "src" / "stages.js"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def test_the_page_asks_the_machine_which_backends_are_missing() -> None:
    """The machine's list is what separates "not probed" from "not installed"."""
    source = _source(ANALYSIS_PAGE)

    assert "getBackends()" in source, (
        "the analysis page does not read GET /api/backends, so it cannot tell "
        "a backend that is missing from one whose version is not probed yet"
    )


def test_the_page_hands_the_machine_s_list_to_the_mapping() -> None:
    """The list has to reach ``deriveBackends``; reading it is not enough."""
    source = _source(ANALYSIS_PAGE)

    assert re.search(r"deriveBackends\(\s*latestRun\s*,\s*machineBackends\s*\)", source), (
        "the analysis page does not hand the machine's backend list to deriveBackends"
    )
    assert "setMachineBackends" in source, (
        "the machine's backend list is never stored, so it cannot be handed over"
    )


def test_the_mapping_reads_the_missing_list() -> None:
    """The mapping has to use the list, not only the run's record."""
    source = _source(STAGES_MODULE)

    assert re.search(r"machine\s*&&\s*machine\.missing", source), (
        "deriveBackends does not read the missing list, so a missing backend "
        "still reads as one that is being probed"
    )


def test_the_card_says_where_each_claim_comes_from() -> None:
    """A reader who lands on the card can see which fact each line rests on."""
    source = _source(ANALYSIS_PAGE)

    assert "/api/backends" in source, "the card does not name the machine's list"
    assert "tool_versions" in source, "the card does not name the run's record"
