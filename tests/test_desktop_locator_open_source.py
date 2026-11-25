"""Regression test: the evidence drawer's "open source" button must not be dead.

The Q2 end-to-end walkthrough (P3) found that the drawer's source button did
nothing at all for a locator that is not a place inside a file: for
``apk-reader:zip-entries`` -- a fact about the APK package itself -- clicking
it neither navigated nor said anything. The user clicked and nothing happened.

The fix: a locator with no single-file landing point leaves the button
disabled and says why, in words a reader can see (a package-level source has
no single file to point at). A locator that does name a file keeps behaving
the way it did.

The desktop front-end has no test framework (``desktop/package.json`` carries
only dev/build/preview/tauri), so this checks the sources under ``desktop/src``
directly -- the same approach as ``tests/test_desktop_version_badge.py``. What
is asserted is what the code must say, not what a browser would draw.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCATORS = ROOT / "desktop" / "src" / "locators.ts"
PROJECT_DETAIL = ROOT / "desktop" / "src" / "pages" / "ProjectDetail.tsx"
BACKEND_LOCATORS = ROOT / "src" / "dexatlas" / "core" / "locators.py"

#: The label the drawer must show for a package-level locator.
PACKAGE_LABEL = "包级来源"
#: The reason it must give: there is no single file to point at.
NO_SINGLE_FILE = "没有单文件落点"
#: The button the walkthrough found dead.
OPEN_SOURCE_LABEL = "打开来源"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def _window(source: str, marker: str, span: int = 700, before: int = 0) -> str:
    """The text around a marker, so a branch can be inspected without parsing TS."""
    index = source.find(marker)
    assert index != -1, f"the source does not contain {marker!r}"
    start = max(0, index - before)
    return source[start : index + span]


def _note(branch: str) -> str:
    """The wording a branch hands back to the reader."""
    match = re.search(r'note:\s*\n?\s*"([^"]+)"', branch)
    assert match, f"the branch has no wording for the reader: {branch[:200]!r}"
    return match.group(1)


def _button_props(source: str, label: str, span: int = 1200) -> str:
    """The props of a button whose JSX label is ``label``.

    The label is looked for as a JSX text node, so that a mention of it in a
    comment is not mistaken for the button itself.
    """
    match = re.search(rf">\s*{re.escape(label)}\s*<", source)
    assert match, f"the drawer has no button labelled {label!r}"
    start = max(0, match.start() - span)
    return source[start : match.start()]


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


def test_package_level_locator_has_no_single_file_landing_point() -> None:
    """A locator about the APK package itself points at no file to open."""
    source = _source(LOCATORS)

    branch = _window(source, "if (tool === APK_READER)")
    assert "openable: false" in branch, "a package-level locator must not be openable"

    wording = _note(branch)
    assert wording.startswith(PACKAGE_LABEL), (
        "a package-level locator must be named as one: " + wording
    )
    assert NO_SINGLE_FILE in wording, "the wording must say there is no file to point at"


def test_dex_locator_has_no_single_file_landing_point() -> None:
    """A locator inside the APK's bytecode points at no file to open either."""
    source = _source(LOCATORS)

    branch = _window(source, "if (tool === DEX_BACKEND)")
    assert "openable: false" in branch, "a dex-internal locator must not be openable"
    assert NO_SINGLE_FILE in _note(branch), "the wording must say there is no file to point at"


def test_backend_failure_locator_has_no_single_file_landing_point() -> None:
    """A locator that names a backend failure points at no file to open."""
    source = _source(LOCATORS)

    branch = _window(source, "place.startsWith(ERROR_PREFIX)")
    assert "openable: false" in branch, "a failed backend's locator must not be openable"


def test_file_level_locator_stays_openable() -> None:
    """A locator into a backend's output tree still names a file to open."""
    source = _source(LOCATORS)

    branch = _window(source, 'target: "file"', span=200)
    assert "openable: true" in branch, "a file inside the output tree stays openable"


def test_open_source_button_is_disabled_without_a_file_landing_point() -> None:
    """The button must be disabled rather than clickable-and-dead."""
    source = _source(PROJECT_DETAIL)

    assert "openSourceState(" in source, "the drawer must derive the button state from the locator"

    button = _button_props(source, OPEN_SOURCE_LABEL)
    assert re.search(r"disabled=\{[^}]*openSource[^}]*\}", button), (
        "the source button must be disabled when the locator has no file landing point"
    )


def test_the_reason_is_readable_in_the_drawer_not_only_in_a_tooltip() -> None:
    """A disabled button must still tell the reader why, in visible text."""
    source = _source(PROJECT_DETAIL)

    assert re.search(r"\{openSource\.note\s*&&", source), (
        "the explanation must be rendered when there is one"
    )
    hint = _window(source, 'className="da-ev-drawer__hint"', span=400)
    assert "openSource.note" in hint, "the explanation must be rendered as text"
    assert 'id="da-ev-open-source-hint"' in hint, (
        "the explanation needs an id of its own so that aria-describedby can point at it"
    )


def test_file_level_locator_keeps_its_click_behaviour() -> None:
    """The working path must not change: clicking still surfaces the locator."""
    source = _source(PROJECT_DETAIL)

    button = _button_props(source, OPEN_SOURCE_LABEL)
    assert "onClick" in button, "the source button must still do something when it is enabled"
    assert "displayLocator(selected.provenance)" in button, (
        "the click must still surface where the source is"
    )


def test_the_backend_answer_wins_once_it_has_been_asked() -> None:
    """The backend's answer about a locator outranks the front-end's guess."""
    source = _source(LOCATORS)

    assert "if (!resolution.resolved)" in source, (
        "a locator the backend could not resolve must not stay openable"
    )
    assert "if (!resolution.kind)" in source, (
        "a locator that resolves to a symbol rather than a file must not stay openable"
    )


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
