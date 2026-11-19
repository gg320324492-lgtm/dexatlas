#!/usr/bin/env python3
"""Draw the GitHub social preview cards, and check that they are still true.

    uv run --no-sync python scripts/make-social-preview.py              # draw both cards
    uv run --no-sync python scripts/make-social-preview.py --check      # the gate

Why this script is in the repository
------------------------------------

The card on the repository's front page quotes the project's measured
numbers: the coverage, the test count, the size of the public-contract
checklist. Nothing held those numbers to the reports they came from. The
drawing script used to live outside the repository, CI did not look at the
image, and the card went stale silently: it named one test count while
the badge named another and the report a third, and no check anywhere
noticed.

A PNG cannot be diffed by a reviewer, and one drawn on Windows has
different bytes from one drawn on Linux, so the gate cannot compare the
image. What it compares is the *numbers*: this script writes down the
figures it drew into ``.github/social-preview.json``, and ``--check``
asserts that those figures still equal the ones in the reports, and that
the hash of the image still matches the hash recorded beside them.
The two languages
-----------------

The English card is ``.github/social-preview.png`` and the Chinese one is
``.github/social-preview.zh-CN.png``. Each card carries the numbers and
the words of its own language: an English reader must be able to read what
``49`` means without switching languages, and the Chinese card must not
carry English labels.

Every number on a card is read from a file that is checked in:

* the coverage and the test counts from the ``<!--fig:...-->`` markers in
  ``docs/reports/phase1-execution-report.md``;
* the size of the public-contract checklist from the ``check()`` call
  sites in ``scripts/verify-public-contracts.py``;
* the number of MCP tools from the ``@server.tool`` registrations in
  ``src/dexatlas/mcp/server.py``;
* the version from ``src/dexatlas/__init__.py`` and the licence from
  ``pyproject.toml``;
* the headline and the one-line positioning sentence from the two
  READMEs.

The labels -- what a number is called on the card -- are this script's own
wording, in two languages, and they are listed in the howto.

Only Pillow is used, and only to draw. ``--check`` needs no fonts, no
Pillow and no image: it compares numbers, so it runs on a Linux CI runner
that has neither a Windows font nor a display.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Where everything comes from
# --------------------------------------------------------------------------

#: The report that holds the measured figures.
REPORT = "docs/reports/phase1-execution-report.md"
#: The contract table, which states the size of the checklist in prose.
CONTRACTS = "docs/architecture/public-contracts.md"
#: The script whose ``check()`` call sites are the checklist.
CONTRACT_SCRIPT = "scripts/verify-public-contracts.py"
#: The MCP server, whose ``@server.tool`` registrations are the tool list.
MCP_SERVER = "src/dexatlas/mcp/server.py"
#: Where the version number is written down.
INIT = "src/dexatlas/__init__.py"
#: Where the licence is written down.
PYPROJECT = "pyproject.toml"
#: The two READMEs the cards take their words from.
README_EN = "README.md"
README_ZH = "README.zh-CN.md"
#: The side-car file: the figures the cards draw, and the images carrying them.
ASIDE = ".github/social-preview.json"
#: The cards.
IMAGE_EN = ".github/social-preview.png"
IMAGE_ZH = ".github/social-preview.zh-CN.png"

#: The functions in the contract script whose ``check()`` calls are counted.
#: The names are structural; the counts are read out of the file, never typed.
CONTRACT_SECTIONS = ("_rest_requests", "mcp_checks", "cli_checks")

#: The badge URLs carry the numbers too, and they are written by hand into
#: the URL -- so they are read and compared here as well.
BADGE_TESTS = re.compile(r"badge/tests-([\d.]+)%20passing")
BADGE_COVERAGE = re.compile(r"badge/coverage-([\d.]+)%25")

#: A ``<!--fig:key-->value<!--/fig-->`` marker in the report.
FIG = re.compile(r"<!--fig:([\w.]+)-->(.*?)<!--/fig-->", re.DOTALL)
#: The machine-readable record the measurement writes into the report.
RECORD = re.compile(r"<!--report-figures:\s*(\{.*?\})\s*-->", re.DOTALL)
#: The sentence in the contract table that states the size of the checklist.
CONTRACT_LINE = re.compile(
    r"检查项清单共\s*(\d+)\s*项[：:]\s*(\d+)\s*REST\s*\+\s*(\d+)\s*MCP\s*\+\s*(\d+)\s*CLI"
)
#: The version in ``src/dexatlas/__init__.py``.
VERSION = re.compile(r"^__version__\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
#: The licence in ``pyproject.toml``.
LICENSE = re.compile(r"^license\s*=\s*\{\s*text\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
#: The status the README declares, English and Chinese.
STATUS_EN = re.compile(r"\*\*Status:\s*([^—*]+?)\s*—")
STATUS_ZH = re.compile(r"\*\*当前状态[：:]\s*([^—*]+?)\s*—")


class PreviewError(Exception):
    """A reason the card cannot be drawn, or cannot be checked."""


# --------------------------------------------------------------------------
# The figures
# --------------------------------------------------------------------------


#: The outcomes a test can have in a measurement. A measurement is complete
#: when every test in the tree has one of them.
SUITE_NAMES = ("passed", "failed", "skipped", "xfailed", "xpassed", "deselected")


@dataclass(frozen=True)
class Facts:
    """Every figure the cards draw, and where each one was read."""

    #: key -> the value as the card writes it.
    figures: dict[str, str]
    #: key -> where the value was read (a file and a marker, never a line
    #: number: a line number is a claim that goes stale on the next edit).
    origins: dict[str, str]
    #: How many tests the measurement sat out. The cards do not draw it, but
    #: a measurement that sat out a test still measured the tree when every
    #: test has an outcome -- ran, sat out with a recorded reason, failed, or
    #: was expected to fail.
    skipped: str = ""
    #: The measurement record's whole suite block: how many passed, failed,
    #: sat out, were expected to fail, and passed unexpectedly.
    suite: dict[str, str] = field(default_factory=dict)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise PreviewError(f"{path}: {error.strerror or error}") from error


def _report_figures(report: str) -> dict[str, str]:
    return {key: value.strip() for key, value in FIG.findall(report)}


def _record(report: str) -> dict[str, Any]:
    match = RECORD.search(report)
    if match is None:
        raise PreviewError(
            "the measurement record was not found in the report "
            "(<!--report-figures:{...}-->); run scripts/refresh-report-figures.py"
        )
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise PreviewError(f"the measurement record is not valid JSON: {error}") from error


def _contract_counts(script: str) -> dict[str, int]:
    """The number of ``check()`` call sites in each section of the contract script.

    The count is read out of the script rather than typed, so a new check
    changes the number on the card instead of drifting away from it.
    """
    try:
        tree = ast.parse(script)
    except SyntaxError as error:
        raise PreviewError(f"the contract script does not parse: {error}") from error
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in CONTRACT_SECTIONS:
            continue
        calls = sum(
            1
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "check"
        )
        counts[node.name] = calls
    missing = [name for name in CONTRACT_SECTIONS if name not in counts]
    if missing:
        raise PreviewError(
            "the contract script has no section(s) named "
            + ", ".join(missing)
            + "; the card counts the check() call sites in "
            + ", ".join(CONTRACT_SECTIONS)
        )
    return counts


def _mcp_tool_count(server: str) -> int:
    """The number of tools the MCP server registers."""
    return len(re.findall(r"^\s*@server\.tool\(", server, re.MULTILINE))


def collect_facts(repo: Path) -> Facts:
    """Read every figure the cards draw out of the files that hold it."""
    report = _read(repo / REPORT)
    figures = _report_figures(report)
    record = _record(report)
    suite = record.get("suite", {})

    required = (
        "tests.total",
        "tests.fast",
        "tests.slow",
        "coverage.pct",
        "coverage.covered",
        "coverage.total",
    )
    missing = [key for key in required if key not in figures]
    if missing:
        raise PreviewError(
            f"{REPORT} has no marker for: {', '.join(missing)}; "
            f"run scripts/refresh-report-figures.py"
        )

    contract_counts = _contract_counts(_read(repo / CONTRACT_SCRIPT))
    rest = contract_counts["_rest_requests"]
    mcp = contract_counts["mcp_checks"]
    cli = contract_counts["cli_checks"]
    tools = _mcp_tool_count(_read(repo / MCP_SERVER))
    version = VERSION.search(_read(repo / INIT))
    if version is None:
        raise PreviewError(f"{INIT}: no __version__ was found")
    licence = LICENSE.search(_read(repo / PYPROJECT))
    if licence is None:
        raise PreviewError(f"{PYPROJECT}: no project licence was found")

    values = {
        "tests.total": figures["tests.total"],
        "tests.fast": figures["tests.fast"],
        "tests.slow": figures["tests.slow"],
        "coverage.pct": figures["coverage.pct"],
        "coverage.covered": figures["coverage.covered"],
        "coverage.total": figures["coverage.total"],
        "suite.passed": str(suite.get("passed", "")),
        "suite.failed": str(suite.get("failed", "")),
        "contract.checks.total": str(rest + mcp + cli),
        "contract.checks.rest": str(rest),
        "contract.checks.mcp": str(mcp),
        "contract.checks.cli": str(cli),
        "mcp.tools": str(tools),
        "version": version.group(1),
        "license": licence.group(1),
    }
    origins = {
        "tests.total": f"{REPORT} (<!--fig:tests.total-->)",
        "tests.fast": f"{REPORT} (<!--fig:tests.fast-->)",
        "tests.slow": f"{REPORT} (<!--fig:tests.slow-->)",
        "coverage.pct": f"{REPORT} (<!--fig:coverage.pct-->)",
        "coverage.covered": f"{REPORT} (<!--fig:coverage.covered-->)",
        "coverage.total": f"{REPORT} (<!--fig:coverage.total-->)",
        "suite.passed": f"{REPORT} (<!--report-figures:...--> suite.passed)",
        "suite.failed": f"{REPORT} (<!--report-figures:...--> suite.failed)",
        "contract.checks.total": f"{CONTRACT_SCRIPT} (check() call sites)",
        "contract.checks.rest": f"{CONTRACT_SCRIPT} (check() call sites in _rest_requests)",
        "contract.checks.mcp": f"{CONTRACT_SCRIPT} (check() call sites in mcp_checks)",
        "contract.checks.cli": f"{CONTRACT_SCRIPT} (check() call sites in cli_checks)",
        "mcp.tools": f"{MCP_SERVER} (@server.tool registrations)",
        "version": f"{INIT} (__version__)",
        "license": f"{PYPROJECT} (project.license)",
    }
    return Facts(
        figures=values,
        origins=origins,
        skipped=str(suite.get("skipped", "")),
        suite={name: str(suite.get(name, "")) for name in SUITE_NAMES},
    )


# --------------------------------------------------------------------------
# The words
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Copy:
    """The words of one card, in one language."""

    language: str
    wordmark: str
    headline: str
    positioning: str
    status: str
    coverage_label: str
    coverage_sub: str
    tests_label: str
    tests_sub: str
    contracts_label: str
    contracts_sub: str
    read_only: str
    footer: str


#: The labels, one pack per language. The numbers inside the braces are
#: filled in from the figures; nothing here is a number.
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "coverage_label": "First-party code coverage",
        "coverage_sub": "{covered}/{total} lines",
        "tests_label": "Tests collected",
        "tests_sub": "{fast} fast + {slow} integration",
        "contracts_label": "Public-contract checklist",
        "contracts_sub": "Static count: {rest} REST + {mcp} MCP + {cli} CLI checks",
        "read_only": "Read-only analysis: {tools} MCP read-only tools, no writes",
        "footer": "{license} · v{version} · {status}",
    },
    "zh-CN": {
        "coverage_label": "一方代码覆盖率",
        "coverage_sub": "{covered}/{total} 行",
        "tests_label": "测试数（收集）",
        "tests_sub": "{fast} 快 + {slow} 集成",
        "contracts_label": "公共契约检查清单",
        "contracts_sub": "静态条数：{rest} REST + {mcp} MCP + {cli} CLI 项检查",
        "read_only": "只读分析：{tools} 个 MCP 只读工具，不写盘",
        "footer": "{license} · v{version} · {status}",
    },
}

#: The README each language's card reads its words from.
README_OF = {"en": README_EN, "zh-CN": README_ZH}


def _readme_words(repo: Path, language: str) -> tuple[str, str, str, str]:
    """The wordmark, the headline, the positioning sentence and the status.

    The wordmark is the README's first heading. The headline is the first
    half of the tagline, up to the dash. The positioning sentence is the
    line under it. All of them are read out of the README, so the card
    cannot show a tagline the README has moved on from.
    """
    text = _read(repo / README_OF[language])
    lines = text.splitlines()
    wordmark = ""
    tagline_index = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not wordmark and stripped.startswith("# "):
            wordmark = stripped[2:].strip()
        if stripped.startswith("**") and stripped.endswith("**") and "—" in stripped:
            tagline_index = index
            break
    if not wordmark:
        raise PreviewError(f"{README_OF[language]}: the title was not found")
    if tagline_index is None:
        raise PreviewError(f"{README_OF[language]}: the tagline was not found")
    headline = lines[tagline_index].strip().strip("*").split("—")[0].strip()
    positioning = ""
    for line in lines[tagline_index + 1 :]:
        if line.strip():
            positioning = line.strip()
            break
    if not positioning:
        raise PreviewError(f"{README_OF[language]}: the positioning sentence was not found")
    status_pattern = STATUS_EN if language == "en" else STATUS_ZH
    status = status_pattern.search(text)
    if status is None:
        raise PreviewError(f"{README_OF[language]}: the status line was not found")
    return wordmark, headline, positioning, status.group(1).strip()


def card_copy(repo: Path, language: str, facts: Facts) -> Copy:
    """The words of one card, with the measured numbers filled in."""
    if language not in LABELS:
        raise PreviewError(f"unknown language: {language}")
    wordmark, headline, positioning, status = _readme_words(repo, language)
    labels = LABELS[language]
    values = {
        "covered": facts.figures["coverage.covered"],
        "total": facts.figures["coverage.total"],
        "fast": facts.figures["tests.fast"],
        "slow": facts.figures["tests.slow"],
        "rest": facts.figures["contract.checks.rest"],
        "mcp": facts.figures["contract.checks.mcp"],
        "cli": facts.figures["contract.checks.cli"],
        "tools": facts.figures["mcp.tools"],
        "version": facts.figures["version"],
        "license": facts.figures["license"],
        "status": status,
    }
    return Copy(
        language=language,
        wordmark=wordmark,
        headline=headline,
        positioning=positioning,
        status=status,
        coverage_label=labels["coverage_label"],
        coverage_sub=labels["coverage_sub"].format(**values),
        tests_label=labels["tests_label"],
        tests_sub=labels["tests_sub"].format(**values),
        contracts_label=labels["contracts_label"],
        contracts_sub=labels["contracts_sub"].format(**values),
        read_only=labels["read_only"].format(**values),
        footer=labels["footer"].format(**values),
    )


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

WIDTH, HEIGHT = 1280, 640
MARGIN = 80

BACKGROUND = (255, 255, 255)
INK = (17, 24, 39)
BODY = (55, 65, 81)
MUTED = (107, 114, 128)
ACCENT = (29, 78, 216)
RULE = (226, 232, 240)
TRACK = (241, 245, 249)

#: The fonts the card is drawn with: Microsoft YaHei, which Windows ships
#: and which carries Latin and Chinese in the same typeface.
FONT_FILES = {"regular": "msyh.ttc", "bold": "msyhbd.ttc"}
#: Where to look for them when the default is not there.
FONT_DIRECTORIES = (Path("C:/Windows/Fonts"),)
#: The environment variable that points at another directory.
FONT_ENV = "DEXATLAS_PREVIEW_FONT_DIR"


@dataclass(frozen=True)
class Fonts:
    """The two faces the card is drawn with."""

    regular: Path
    bold: Path


def resolve_fonts(font_dir: Path | None) -> Fonts:
    """Find the fonts, or say exactly what is missing and where it was looked for.

    The card is drawn with the fonts Windows ships, because Chinese and
    Latin then come out of the same typeface. A machine without them cannot
    draw the card -- and gets told so, with the paths that were searched.
    """
    directories: list[Path] = []
    if font_dir is not None:
        directories.append(font_dir)
    else:
        from_env = os.environ.get(FONT_ENV)
        if from_env:
            directories.append(Path(from_env))
        directories.extend(FONT_DIRECTORIES)
    found: dict[str, Path] = {}
    missing: list[str] = []
    for role, name in FONT_FILES.items():
        for directory in directories:
            candidate = directory / name
            if candidate.is_file():
                found[role] = candidate
                break
        else:
            missing.append(f"{name} ({role})")
    if missing:
        searched = ", ".join(str(directory) for directory in directories)
        raise PreviewError(
            "the social preview card needs a font, and none was found.\n"
            f"  missing: {', '.join(missing)}\n"
            f"  searched: {searched}\n"
            "Point the script at a directory that has them:\n"
            "  --font-dir /path/to/fonts\n"
            f"or set {FONT_ENV}.\n"
            "The card is drawn with Microsoft YaHei, which Windows ships and which "
            "carries Latin and Chinese in one typeface.\n"
            "The check mode (--check) needs no fonts at all: it compares numbers."
        )
    return Fonts(regular=found["regular"], bold=found["bold"])


class Card:
    """A canvas that knows where every line of text went."""

    def __init__(self, fonts: Fonts) -> None:
        from PIL import Image, ImageDraw, ImageFont

        self._image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
        self._draw = ImageDraw.Draw(self._image)
        self._fonts = fonts
        self._image_font = ImageFont
        self.placed: list[tuple[str, tuple[float, float, float, float]]] = []
        self.faults: list[str] = []

    def font(self, role: str, size: int) -> Any:
        path = self._fonts.regular if role == "regular" else self._fonts.bold
        return self._image_font.truetype(str(path), size)

    def place(
        self,
        text: str,
        xy: tuple[int, int],
        role: str,
        size: int,
        color: tuple[int, int, int],
        max_width: int | None = None,
        min_size: int = 12,
    ) -> tuple[float, float, float, float]:
        """Draw one line, shrinking it until it fits, and record where it went.

        A card is 1280 pixels wide and the text on it is written in a
        language whose length is not ours to decide, so the font shrinks
        instead of the text running off the edge. A line that still does
        not fit at the smallest size is a layout fault, and is reported.
        """
        font = self.font(role, size)
        while max_width is not None and size > min_size:
            box = self._draw.textbbox((0, 0), text, font=font)
            if box[2] - box[0] <= max_width:
                break
            size -= 1
            font = self.font(role, size)
        if max_width is not None:
            box = self._draw.textbbox((0, 0), text, font=font)
            if box[2] - box[0] > max_width:
                self.faults.append(
                    f"{text!r} is {box[2] - box[0]:.0f}px wide at {size}px, "
                    f"and its column is {max_width}px wide"
                )
        self._draw.text(xy, text, font=font, fill=color, anchor="la")
        box = self._draw.textbbox(xy, text, font=font, anchor="la")
        self.placed.append((text, box))
        return box

    def rule(self, y: int) -> None:
        self._draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=RULE, width=2)

    def bar(self, x: int, y: int, width: int, height: int, fraction: float) -> None:
        """A progress bar: the coverage is a ratio, and a ratio wants a scale."""
        self._draw.rounded_rectangle([x, y, x + width, y + height], radius=height // 2, fill=TRACK)
        filled = max(height, round(width * fraction))
        self._draw.rounded_rectangle(
            [x, y, x + filled, y + height], radius=height // 2, fill=ACCENT
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._image.save(path, format="PNG", optimize=True)

    def overflow(self) -> list[str]:
        """The lines that ran off the card, and the ones that did not fit."""
        faults = list(self.faults)
        for text, (left, top, right, bottom) in self.placed:
            if left < 0 or top < 0 or right > WIDTH or bottom > HEIGHT:
                faults.append(f"{text!r} at ({left:.0f}, {top:.0f})-({right:.0f}, {bottom:.0f})")
        return faults


def draw_card(copy: Copy, facts: Facts, fonts: Fonts) -> Card:
    """Draw one card.

    The layout gives the coverage its own weight: it is a ratio, it has a
    denominator the reader can check, and it is the number this project
    wants to be remembered by. The two counts sit next to it, smaller, and
    the counts say what they count. The strongest claim on the card -- that
    the analysis is read-only -- is a line of its own, not a footnote.
    """
    card = Card(fonts)
    card.place(copy.wordmark, (MARGIN, 44), "bold", 30, ACCENT)
    card.place(copy.headline, (MARGIN, 92), "bold", 56, INK, max_width=WIDTH - 2 * MARGIN)
    card.place(copy.positioning, (MARGIN, 182), "regular", 22, MUTED, max_width=WIDTH - 2 * MARGIN)
    card.rule(228)
    card.place(copy.read_only, (MARGIN, 248), "regular", 22, BODY, max_width=WIDTH - 2 * MARGIN)

    column = (WIDTH - 2 * MARGIN - 2 * 60) // 3
    left = MARGIN
    middle = MARGIN + column + 60
    right = MARGIN + 2 * (column + 60)

    covered = int(facts.figures["coverage.covered"])
    total = int(facts.figures["coverage.total"])
    fraction = covered / total if total else 0.0

    card.place(facts.figures["coverage.pct"], (left, 320), "bold", 72, INK, max_width=column)
    card.place(facts.figures["tests.total"], (middle, 336), "bold", 52, INK, max_width=column)
    card.place(
        facts.figures["contract.checks.total"], (right, 336), "bold", 52, INK, max_width=column
    )

    card.place(copy.coverage_label, (left, 412), "regular", 22, BODY, max_width=column)
    card.place(copy.tests_label, (middle, 412), "regular", 22, BODY, max_width=column)
    card.place(copy.contracts_label, (right, 412), "regular", 22, BODY, max_width=column)

    card.place(copy.coverage_sub, (left, 444), "regular", 18, MUTED, max_width=column)
    card.place(copy.tests_sub, (middle, 444), "regular", 18, MUTED, max_width=column)
    card.place(copy.contracts_sub, (right, 444), "regular", 18, MUTED, max_width=column)

    card.bar(left, 478, column, 8, fraction)

    card.rule(526)
    card.place(copy.footer, (MARGIN, 552), "regular", 19, MUTED, max_width=WIDTH - 2 * MARGIN)
    return card


# --------------------------------------------------------------------------
# The side-car file
# --------------------------------------------------------------------------


def image_record(path: Path) -> dict[str, Any]:
    """The hash and the size of an image."""
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def aside_path(repo: Path) -> Path:
    return repo / ASIDE


def build_aside(repo: Path, facts: Facts, copies: dict[str, Copy]) -> dict[str, Any]:
    """The record of what the cards say and which images carry it."""
    cards: dict[str, Any] = {}
    for language, copy in copies.items():
        image = IMAGE_EN if language == "en" else IMAGE_ZH
        cards[language] = {
            "headline": copy.headline,
            "positioning": copy.positioning,
            "image": image,
            **image_record(repo / image),
        }
    return {
        "schema": 1,
        "note": (
            "The figures the social preview cards draw, and the images that carry "
            "them. Written by scripts/make-social-preview.py; checked by the same "
            "script's --check mode. The numbers are compared, never the image "
            "bytes: a PNG drawn on one machine has different bytes on another. "
            "The suite block holds every outcome the measuring script accounts "
            "for (its SUITE_NAMES), so a measurement that gains an outcome is a "
            "sidecar that has to be redrawn, not one that passes in silence."
        ),
        "figures": dict(sorted(facts.figures.items())),
        "origins": dict(sorted(facts.origins.items())),
        "suite": dict(sorted(facts.suite.items())),
        "cards": cards,
    }


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------


@dataclass
class Report:
    """What the check found."""

    failures: list[str]
    checks: int

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks += 1
        if ok:
            print(f"  PASS {name}")
        else:
            print(f"  FAIL {name}  {detail}")
            self.failures.append(f"{name}: {detail}" if detail else name)


def check(repo: Path) -> int:
    """Check that the cards still say what the reports say.

    Nothing here draws anything or needs a font: the images are compared
    by the hash recorded beside them, and the numbers are compared to the
    files they were read from.
    """
    print("\n== the card's numbers against the reports ==")
    result = Report(failures=[], checks=0)

    facts = collect_facts(repo)
    copies = {language: card_copy(repo, language, facts) for language in LABELS}

    side_car = aside_path(repo)
    if not side_car.is_file():
        print(f"  FAIL the side-car file  {side_car} does not exist")
        print(
            "\nThe card's numbers are not on record. Draw the cards:\n"
            "  uv run --no-sync python scripts/make-social-preview.py"
        )
        return 1
    try:
        recorded = json.loads(side_car.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"  FAIL the side-car file  {side_car}: {error}")
        return 1

    recorded_figures = recorded.get("figures", {})
    for key, value in facts.figures.items():
        result.check(
            f"figure {key}",
            recorded_figures.get(key) == value,
            f"the card says {recorded_figures.get(key)!r}, the reports say {value!r}",
        )

    # The sidecar is the record of what the cards drew, so it carries the
    # whole measurement the same way the report's record does: the outcomes
    # the run accounted for. A key the measuring script writes but the
    # sidecar does not is a figure the card drew that nobody can check
    # against the record -- the gap this loop closes. It reads the same
    # names as the measuring script's own accounting (``SUITE_NAMES``),
    # rather than a copy of the list: a second list is a second answer.
    recorded_suite = recorded.get("suite", {})
    for name in SUITE_NAMES:
        result.check(
            f"the sidecar records suite.{name}",
            name in recorded_suite,
            f"the sidecar has no suite.{name}; the measurement record has it",
        )

    recorded_origins = recorded.get("origins", {})
    for key, origin in facts.origins.items():
        result.check(
            f"origin {key}",
            recorded_origins.get(key) == origin,
            f"the card says {recorded_origins.get(key)!r}, the source is {origin!r}",
        )

    print("\n== the images that carry the numbers ==")
    recorded_cards = recorded.get("cards", {})
    for language, copy in copies.items():
        image = IMAGE_EN if language == "en" else IMAGE_ZH
        entry = recorded_cards.get(language, {})
        path = repo / image
        if not path.is_file():
            result.check(f"image {image}", False, "the file does not exist")
            continue
        actual = image_record(path)
        result.check(
            f"image {image} is the one the numbers were drawn into",
            entry.get("sha256") == actual["sha256"],
            f"the file hashes {actual['sha256'][:12]}..., the record says "
            f"{str(entry.get('sha256'))[:12]}...; redraw the card",
        )
        result.check(
            f"headline {language}",
            entry.get("headline") == copy.headline,
            f"the card says {entry.get('headline')!r}, the README says {copy.headline!r}",
        )
        result.check(
            f"positioning {language}",
            entry.get("positioning") == copy.positioning,
            f"the card says {entry.get('positioning')!r}, the README says {copy.positioning!r}",
        )

    print("\n== the badges, which carry the same numbers ==")
    for name in (README_EN, README_ZH):
        text = _read(repo / name)
        tests = BADGE_TESTS.search(text)
        coverage = BADGE_COVERAGE.search(text)
        result.check(
            f"{name} carries the test count",
            tests is not None and tests.group(1) == facts.figures["suite.passed"],
            f"the badge says {tests.group(1) if tests else None!r}, "
            f"the report says {facts.figures['suite.passed']!r} passed",
        )
        result.check(
            f"{name} carries the coverage",
            coverage is not None and coverage.group(1) == facts.figures["coverage.pct"].rstrip("%"),
            f"the badge says {coverage.group(1) if coverage else None!r}, "
            f"the report says {facts.figures['coverage.pct']!r}",
        )

    # A measurement is complete when every test in the tree has an outcome:
    # it ran, it was skipped with a recorded reason, it failed, or it was
    # expected to fail. That is the same rule the measuring script applies
    # (see its ``measured_the_tree``), and this check used to apply a
    # stricter one -- "no skips at all" -- which a by-design platform skip
    # (the POSIX launcher test on Windows, where the native one runs
    # instead) turned into a permanent red: the card's numbers were right
    # and the gate said they were not.
    skipped = facts.skipped
    accounted = sum(int(facts.suite.get(name) or 0) for name in SUITE_NAMES)
    total = int(facts.figures.get("tests.total") or 0)
    result.check(
        "the measurement was complete",
        total > 0 and accounted == total,
        f"the tree has {total} tests; the record accounts for {accounted} "
        f"({skipped} skipped, each with a recorded reason); re-run the measurement",
    )

    print("\n== the cards are on the front page ==")
    for name, image in ((README_EN, IMAGE_EN), (README_ZH, IMAGE_ZH)):
        text = _read(repo / name)
        result.check(
            f"{name} shows {image}",
            image in text,
            "the README does not embed the card",
        )

    print("\n== the contract table states the number the card draws ==")
    contracts = _read(repo / CONTRACTS)
    match = CONTRACT_LINE.search(contracts)
    if match is None:
        result.check(
            "the checklist line in the contract table",
            False,
            f"the sentence stating the size of the checklist was not found in {CONTRACTS}",
        )
    else:
        stated = [int(part) for part in match.groups()]
        derived = [
            int(facts.figures["contract.checks.total"]),
            int(facts.figures["contract.checks.rest"]),
            int(facts.figures["contract.checks.mcp"]),
            int(facts.figures["contract.checks.cli"]),
        ]
        result.check(
            "the checklist line in the contract table",
            stated == derived,
            f"the table says {stated}, the script has {derived}",
        )

    print()
    if result.failures:
        print(f"{len(result.failures)} of {result.checks} checks failed.")
        print(
            "The card quotes the numbers the reports hold. If the reports moved, "
            "draw the card again:\n"
            "  uv run --no-sync python scripts/make-social-preview.py"
        )
        return 1
    print(f"All {result.checks} checks passed.")
    return 0


# --------------------------------------------------------------------------
# The command line
# --------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="the repository to draw the cards for (default: the one this script is in)",
    )
    parser.add_argument(
        "--font-dir",
        type=Path,
        default=None,
        help=f"where to find the fonts (default: {FONT_ENV}, then Windows' own)",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh-CN", "both"],
        default="both",
        help="which card to draw (default: both)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check the cards against the reports instead of drawing them",
    )
    return parser.parse_args(argv)


def draw(repo: Path, languages: list[str], font_dir: Path | None) -> int:
    """Draw the cards and write down what they say."""
    facts = collect_facts(repo)
    all_copies = {language: card_copy(repo, language, facts) for language in LABELS}
    fonts = resolve_fonts(font_dir)

    for language in languages:
        copy = all_copies[language]
        image = repo / (IMAGE_EN if language == "en" else IMAGE_ZH)
        card = draw_card(copy, facts, fonts)
        faults = card.overflow()
        for text, (left, top, right, bottom) in card.placed:
            print(f"  {language:5} {text!r} at ({left:.0f}, {top:.0f})-({right:.0f}, {bottom:.0f})")
        if faults:
            print(f"\nThe {language} card does not fit: ", file=sys.stderr)
            for fault in faults:
                print(f"  {fault}", file=sys.stderr)
            return 1
        card.save(image)
        print(f"  wrote {image} ({image_record(image)['bytes']} bytes)")

    side_car = aside_path(repo)
    side_car.parent.mkdir(parents=True, exist_ok=True)
    side_car.write_text(
        json.dumps(
            build_aside(repo, facts, all_copies), ensure_ascii=False, indent=2, sort_keys=False
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {ASIDE}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo_root.resolve()
    try:
        if args.check:
            return check(repo)
        languages = list(LABELS) if args.lang == "both" else [args.lang]
        return draw(repo, languages, args.font_dir)
    except PreviewError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
