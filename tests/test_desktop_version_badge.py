"""Regression tests for desktop version display.

The sidebar used to hardcode ``v1.0.2`` while ``/api/health`` reported the
real version (Q2 end-to-end walkthrough, P1). The backend health response is
the single authoritative source; the UI must not hardcode a version number.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_LAYOUT = ROOT / "desktop" / "src" / "components" / "AppLayout.tsx"
SETTINGS_PAGE = ROOT / "desktop" / "src" / "pages" / "SettingsPage.tsx"

VERSION_LITERAL = re.compile(r"\bv\d+\.\d+\.\d+\b")


def test_desktop_sidebar_does_not_hardcode_a_version() -> None:
    """The sidebar must not contain a hardcoded version number."""

    source = APP_LAYOUT.read_text(encoding="utf-8")
    assert not VERSION_LITERAL.search(source), (
        "AppLayout.tsx hardcodes a version; read it from /api/health instead, "
        "as the settings page already does"
    )


def test_desktop_settings_reads_the_version_from_health() -> None:
    """The settings page version must come from the health response."""

    source = SETTINGS_PAGE.read_text(encoding="utf-8")
    assert "health.version" in source
