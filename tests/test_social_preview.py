"""The social preview card cannot drift away from the reports it quotes.

The card on the repository's front page used to have no machine-checkable
link to the reports it quoted. The script that drew it was not in the
repository, CI did not look at the image, and the card went stale
silently: it said 1612 tests while the badge said 1631 and the report
said 1632, and nothing noticed.

The script is in the repository now (``scripts/make-social-preview.py``),
it writes down the figures it drew (``.github/social-preview.json``), and
``--check`` asserts that those figures still equal the ones in the reports.
These tests are that gate's own tests: they take the tree apart in a
temporary copy and check that the gate says so.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "make-social-preview.py"

#: Everything the script reads or writes. A temporary copy needs all of it,
#: and nothing else.
TREE = (
    "scripts/make-social-preview.py",
    "scripts/verify-public-contracts.py",
    "docs/reports/phase1-execution-report.md",
    "docs/architecture/public-contracts.md",
    "src/dexatlas/mcp/server.py",
    "src/dexatlas/__init__.py",
    "pyproject.toml",
    "README.md",
    "README.zh-CN.md",
    ".github/social-preview.json",
    ".github/social-preview.png",
    ".github/social-preview.zh-CN.png",
)


def _script() -> ModuleType:
    """The drawing script; the tests read its rules, not a copy of them."""
    spec = importlib.util.spec_from_file_location("dexatlas_social_preview", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _copy_tree(destination: Path) -> Path:
    """A copy of the tree the check reads."""
    for name in TREE:
        source = REPO_ROOT / name
        assert source.is_file(), f"{name} is missing from the repository"
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def _check(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the gate against a tree and return what it said."""
    return subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "make-social-preview.py"),
            "--check",
            "--repo-root",
            str(root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_the_card_script_is_in_the_repository() -> None:
    """The script that draws the card is a file in the repository.

    It used to live outside it, which is the whole reason the card could
    go stale: nothing held the numbers on it to the numbers in the reports.
    """
    assert SCRIPT.is_file(), "scripts/make-social-preview.py is missing"
    assert "make-social-preview.py" in (
        REPO_ROOT / "docs" / "reports" / "social-preview-howto.md"
    ).read_text(encoding="utf-8"), "the howto does not say how to run the script"


def test_the_card_script_holds_no_measured_number() -> None:
    """The numbers on the card are read out of the files, never typed in.

    A number written into the script is a number that goes stale the next
    time the measurement moves. The figures the script knows about are
    therefore read out of the tree, and the test says so by looking for
    them in the source.
    """
    script = _script()
    facts = script.collect_facts(REPO_ROOT)
    source = SCRIPT.read_text(encoding="utf-8")
    for key in ("tests.total", "tests.fast", "tests.slow", "coverage.covered", "coverage.total"):
        value = facts.figures[key]
        assert value not in source, f"{key} ({value}) is written into the script"


def test_the_cards_are_current(tmp_path: Path) -> None:
    """The cards in the repository say what the reports say.

    This is the gate itself, run against the tree as it stands.
    """
    result = _check(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_check_fails_when_the_report_moves(tmp_path: Path) -> None:
    """A measurement that moved must make the gate say so.

    This is the failure that happened: the report's test count moved and
    the card did not. The gate has to notice that, and it has to name the
    figure that moved.
    """
    root = _copy_tree(tmp_path)
    report = root / "docs" / "reports" / "phase1-execution-report.md"
    text = report.read_text(encoding="utf-8")
    total = _script().collect_facts(REPO_ROOT).figures["tests.total"]
    before = f"<!--fig:tests.total-->{total}<!--/fig-->"
    assert before in text
    report.write_text(
        text.replace(before, "<!--fig:tests.total-->1999<!--/fig-->"),
        encoding="utf-8",
    )

    result = _check(root)
    assert result.returncode != 0, "the gate passed a tree whose report had moved"
    assert "tests.total" in result.stdout, "the gate did not name the figure that moved"


def test_the_check_fails_when_the_card_is_not_the_one_that_was_drawn(
    tmp_path: Path,
) -> None:
    """A card that was edited by hand must make the gate say so.

    The numbers on the card are on record beside it. If the image is not
    the one those numbers were drawn into, the card is a picture of
    something else -- and the gate is the only thing that can tell.
    """
    root = _copy_tree(tmp_path)
    image = root / ".github" / "social-preview.png"
    image.write_bytes(image.read_bytes() + b"\x00")

    result = _check(root)
    assert result.returncode != 0, "the gate passed a card that was edited by hand"
    assert "social-preview.png" in result.stdout, "the gate did not name the card"


def test_the_check_fails_when_the_tagline_moves(tmp_path: Path) -> None:
    """A card whose words are no longer the README's words must be redrawn.

    The numbers are not the only thing on the card: the headline and the
    one-line positioning sentence are read out of the READMEs, and a card
    that kept the old ones would be quoting a project that has moved on.
    """
    root = _copy_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "**From APK to Evidence" in text
    readme.write_text(
        text.replace("**From APK to Evidence", "**From APK to Proof"), encoding="utf-8"
    )

    result = _check(root)
    assert result.returncode != 0, "the gate passed a card with a tagline the README moved on from"
    assert "headline" in result.stdout, "the gate did not name the headline that moved"


def test_the_check_fails_when_a_badge_drifts(tmp_path: Path) -> None:
    """A badge that was typed by hand must make the gate say so.

    The badge is a URL, so its number is written by hand into it, and a
    hand-written number drifts -- that is how the card and the badge came
    to disagree about the same number.
    """
    root = _copy_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    passed = _script().collect_facts(REPO_ROOT).figures["suite.passed"]
    before = f"badge/tests-{passed}%20passing"
    assert before in text
    readme.write_text(text.replace(before, "badge/tests-1600%20passing"), encoding="utf-8")

    result = _check(root)
    assert result.returncode != 0, "the gate passed a badge that had drifted"


def test_both_cards_exist_and_are_the_project_s_own() -> None:
    """The English and the Chinese card are both there, and they differ.

    The English card hangs on the English front page and the Chinese card
    on the Chinese one. A card that carries the other language's labels
    is the mistake this pair exists to prevent.
    """
    script = _script()
    english = REPO_ROOT / script.IMAGE_EN
    chinese = REPO_ROOT / script.IMAGE_ZH
    assert english.is_file(), f"{script.IMAGE_EN} is missing"
    assert chinese.is_file(), f"{script.IMAGE_ZH} is missing"
    assert english.read_bytes() != chinese.read_bytes(), "the two cards are the same file"


def test_the_cards_are_on_both_front_pages() -> None:
    """Each README shows the card in its own language."""
    script = _script()
    english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    assert script.IMAGE_EN in english, "the English README does not show the English card"
    assert script.IMAGE_ZH in chinese, "the Chinese README does not show the Chinese card"
    assert script.IMAGE_ZH not in english, "the English README shows the Chinese card"


def test_the_side_car_file_holds_the_figures_the_cards_draw() -> None:
    """The side-car file is the record the gate compares against.

    It is written by the drawing script, so it must hold the same figures
    the script reads out of the tree -- and it must say where each one
    came from, because a number without a source is the thing this whole
    gate exists to prevent.
    """
    script = _script()
    facts = script.collect_facts(REPO_ROOT)
    recorded = json.loads((REPO_ROOT / script.ASIDE).read_text(encoding="utf-8"))
    assert recorded["figures"] == dict(sorted(facts.figures.items()))
    for key, origin in facts.origins.items():
        assert recorded["origins"][key] == origin
        assert origin, f"{key} has no origin"
