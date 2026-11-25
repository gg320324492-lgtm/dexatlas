"""The front end mirrors the back end's locator vocabulary -- across languages.

The desktop classifies a locator by its tool prefix (``jadx:`` / ``apktool:`` /
``apk-reader:`` / ``androguard:`` / ``error/``).  Those prefixes belong to the
back end: ``src/dexatlas/core/locators.py`` is what decides what a locator
means.  If the two lists drift apart, the front end classifies a locator the
back end does not recognise -- and the 「打开来源」 button ends up wrong about a
file that is really there.

This is the one thing about the desktop's locator handling that a JavaScript
test cannot do: it reads the *Python* source of the back end.  Everything else
about the classification -- which locators have no single-file landing point,
which ones do, what the button does with the back end's answer -- is unit
tested in ``desktop/src/locators.test.ts`` (vitest).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCATORS = ROOT / "desktop" / "src" / "locators.ts"
BACKEND_LOCATORS = ROOT / "src" / "dexatlas" / "core" / "locators.py"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def _backend_constant(source: str, name: str) -> str:
    match = re.search(rf'^{name} = "([^"]+)"', source, re.MULTILINE)
    assert match, f"core/locators.py does not define {name}"
    return match.group(1)


def _frontend_constant(source: str, name: str) -> str:
    match = re.search(rf'export const {name} = "([^"]+)"', source)
    assert match, f"desktop/src/locators.ts does not define {name}"
    return match.group(1)


def _backend_output_backends(source: str) -> list[str]:
    match = re.search(r"OUTPUT_BACKENDS: dict\[str, str\] = \{(?P<body>[^}]*)\}", source)
    assert match, "core/locators.py does not define OUTPUT_BACKENDS"
    return re.findall(r'"([^"]+)"\s*:', match.group("body"))


def _frontend_output_backends(source: str) -> list[str]:
    match = re.search(
        r"export const OUTPUT_BACKENDS: readonly string\[\] = \[(?P<body>[^\]]*)\]", source
    )
    assert match, "desktop/src/locators.ts does not define OUTPUT_BACKENDS"
    return re.findall(r'"([^"]+)"', match.group("body"))


def test_the_frontend_locator_vocabulary_matches_the_backend() -> None:
    """The front-end mirrors the back-end's tool vocabulary; it must not drift."""
    backend = _source(BACKEND_LOCATORS)
    frontend = _source(LOCATORS)

    assert _backend_constant(backend, "APK_READER") == _frontend_constant(frontend, "APK_READER")
    assert _backend_constant(backend, "DEX_BACKEND") == _frontend_constant(frontend, "DEX_BACKEND")
    assert _backend_constant(backend, "ERROR_PREFIX") == _frontend_constant(
        frontend, "ERROR_PREFIX"
    )
    assert _backend_output_backends(backend) == _frontend_output_backends(frontend)
