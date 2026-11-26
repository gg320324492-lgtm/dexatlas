"""The card heading must not be squeezed into a column of single characters.

The analysis page's left column is 280px wide, and its card header holds
three things side by side: the title, the subtitle, and a badge. The badge
-- "stage progress: backend stage events + frontend mapping" -- is a long
sentence that refuses to wrap, so it takes most of the column, and the
title is what gives way. The title has no ``flex`` of its own while the
actions beside it have ``flex-shrink: 0``, so "阶段进度" ended up with
about 20px to write in: one character per line.

This was seen in the packaged executable on 2026-11-27. The fix gives the
heading the room the actions leave it, and lets a long action wrap inside
itself.

Layout has no unit test to speak of, so what these tests pin down is the
**rules themselves**: the two declarations that keep the layout sane are
read out of the stylesheets and held in place here, the same way
``test_desktop_keyboard_accessibility.py`` reads the focus-ring rules out
of a stylesheet and holds them in place.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_CSS = ROOT / "desktop" / "src" / "components" / "Card.css"
ANALYSIS_CSS = ROOT / "desktop" / "src" / "pages" / "Analysis.css"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def _rule(css: str, selector: str) -> str:
    """The body of the first rule for a selector."""
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}", css)
    assert match, f"{selector} has no rule"
    return match.group("body")


def test_the_card_heading_takes_the_room_the_actions_do_not_need() -> None:
    """The heading grows; the actions do not squeeze it.

    ``.da-card__actions`` does not shrink (``flex-shrink: 0``), so without
    ``flex`` on the heading the heading is what gives way -- and a title
    squeezed to a few pixels stacks its characters one per line.
    """
    css = _source(CARD_CSS)

    heading = _rule(css, ".da-card__heading")
    assert re.search(r"flex:\s*1", heading), (
        "the card heading does not take the room the actions leave it, so a "
        "long action squeezes the title into a column of single characters"
    )

    actions = _rule(css, ".da-card__actions")
    assert "flex-shrink: 0" not in actions, (
        "the card actions refuse to shrink, so they take the heading's width instead of giving way"
    )


def test_the_stage_badge_may_wrap_in_a_narrow_column() -> None:
    """The badge wraps inside itself rather than pushing the title away.

    It says which source the stage grid is drawn from; a narrow column
    cannot hold it on one line, and a wrapped badge is honest where a
    squeezed title is not.
    """
    css = _source(ANALYSIS_CSS)

    badge = _rule(css, ".da-mock-badge")
    assert "white-space: nowrap" not in badge, (
        "the stage badge refuses to wrap, so it takes the column's width from the title beside it"
    )
    assert re.search(r"min-width:\s*0", badge), (
        "the stage badge needs a bound of its own to wrap inside"
    )
