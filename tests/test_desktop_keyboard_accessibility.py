"""Regression test: the desktop shell's keyboard contract.

The Q2 end-to-end walkthrough left the keyboard pass unverified (P4): the
skip link, the focus trap and the focus restore were asserted by reading the
code, not by walking the pages. This file pins down the parts that the walk
found to be broken or unproven:

* the skip link is the first stop of the tab order, and it reveals itself
  when it is focused;
* the region the skip link jumps to shows where the focus went -- the
  ``:focus`` suppression of the outline used to win over the global
  ``:focus-visible`` ring, so the landing point was invisible;
* the focus trap wraps at both ends of the overlay;
* Escape closes the overlay and the focus goes back to the element that
  opened it.

The desktop front-end has no test framework, so this checks the sources under
``desktop/src`` directly, the same way ``tests/test_desktop_version_badge.py``
does. What is asserted is what the code must say, not what a browser draws.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_LAYOUT_TSX = ROOT / "desktop" / "src" / "components" / "AppLayout.tsx"
APP_LAYOUT_CSS = ROOT / "desktop" / "src" / "components" / "AppLayout.css"
DISMISSABLE = ROOT / "desktop" / "src" / "components" / "useDismissable.ts"
DRAWER = ROOT / "desktop" / "src" / "components" / "Drawer.tsx"
DIALOG = ROOT / "desktop" / "src" / "components" / "Dialog.tsx"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def test_the_skip_link_is_the_first_stop_of_the_tab_order() -> None:
    """The skip link comes before the sidebar, so the first Tab reaches it."""
    source = _source(APP_LAYOUT_TSX)

    skip = source.find('className="skip-link"')
    sidebar = source.find('className="sidebar"')
    assert skip != -1, "the layout has no skip link"
    assert sidebar != -1, "the layout has no sidebar"
    assert skip < sidebar, "the skip link must come before the sidebar in the DOM"


def test_the_skip_link_reveals_itself_when_it_is_focused() -> None:
    """Hidden until focused, and then it must be visible and outlined."""
    css = _source(APP_LAYOUT_CSS)

    match = re.search(r"\.skip-link:focus[^{]*\{(?P<body>[^}]*)\}", css)
    assert match, "the skip link has no rule for when it is focused"
    body = match.group("body")
    assert "clip-path: none" in body, "the skip link must stop being clipped when focused"
    assert re.search(r"outline:\s*2px solid", body), "the focused skip link must be outlined"


def test_the_skip_link_target_shows_where_the_focus_went() -> None:
    """The main region must not swallow the focus ring the skip link lands on.

    ``.app-main:focus { outline: none }`` and the global ``:focus-visible``
    ring have the same specificity in that order, so the suppression used to
    win and the landing point was invisible to a keyboard user.
    """
    css = _source(APP_LAYOUT_CSS)

    suppression = css.find(".app-main:focus {")
    visible = css.find(".app-main:focus-visible")
    assert suppression != -1, "the main region's outline suppression is gone"
    assert visible != -1, (
        "the main region needs a :focus-visible rule, or the skip link lands on an invisible focus"
    )
    assert visible > suppression, (
        "the :focus-visible rule must come after the :focus suppression: they "
        "have the same specificity, and the later one wins"
    )

    body = re.search(r"\.app-main:focus-visible\s*\{(?P<body>[^}]*)\}", css)
    assert body, "the :focus-visible rule for the main region is malformed"
    assert re.search(r"outline:\s*2px solid", body.group("body")), (
        "the main region must draw an outline when it is focused from the keyboard"
    )


def test_the_focus_trap_wraps_at_both_ends_of_the_overlay() -> None:
    """Tab at the last stop goes to the first, Shift+Tab at the first to the last."""
    source = _source(DISMISSABLE)

    assert "e.shiftKey" in source, "the focus trap does not handle Shift+Tab"
    assert "lastEl.focus()" in source, "Shift+Tab at the first stop must go to the last"
    assert "firstEl.focus()" in source, "Tab at the last stop must go to the first"
    assert source.count("preventDefault()") >= 2, (
        "the trap must stop the browser's own Tab from leaving the overlay"
    )


def test_escape_closes_the_overlay() -> None:
    """Escape is the way out of an overlay; it must be wired to the close action."""
    source = _source(DISMISSABLE)

    assert '"Escape"' in source, "Escape is not handled by the overlay"
    assert "onEscape?.()" in source, "Escape must call the close action"


def test_the_focus_goes_back_to_the_element_that_opened_the_overlay() -> None:
    """Closing an overlay must not drop the keyboard user at the top of the page."""
    for path in (DRAWER, DIALOG):
        source = _source(path)
        assert "document.activeElement" in source, (
            f"{path.name} does not remember what had the focus"
        )
        assert re.search(r"opener\??\.focus\??\.?\(\)", source), (
            f"{path.name} does not give the focus back"
        )
