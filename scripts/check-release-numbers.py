#!/usr/bin/env python3
"""Check that the release numbers the outward-facing texts state agree.

    uv run --no-sync python scripts/check-release-numbers.py
    uv run --no-sync python scripts/check-release-numbers.py --strict
    uv run --no-sync python scripts/check-release-numbers.py --offline

The execution report is the authority for the numbers of a release:
``scripts/refresh-report-figures.py`` writes them into
``docs/reports/phase1-execution-report.md`` between ``<!--fig:...-->`` markers,
out of a complete measurement. Five documents repeat them by hand:

* ``docs/how-to-verify.md``,
* ``docs/how-to-verify.zh-CN.md``,
* ``docs/releases/<tag>.md``,
* ``docs/reports/<tag>-github-release-body.md``,
* the release body published on GitHub for the tag.

Nobody compared them. A number that drifted in one copy left the other three
saying something else, and the release went out with both. This script reads
the authority, reads what each of the texts says, and compares them.

It reads the numbers; it does not carry them. A hand-written list of expected
values would be a second copy of the truth -- the same mistake the four
documents make, one level down.

Which tree a number is about
-----------------------------
There are two comparisons here, and they are about two different trees.

* The **working copy**: the pages that describe the tree you are standing on
  -- ``docs/how-to-verify.md`` and ``docs/how-to-verify.zh-CN.md`` -- against
  the execution report in this checkout.
* The **published release**: the documents of a release that shipped -- the
  release notes, the release body in the repository, and the release body
  published on GitHub -- against the execution report **in the tagged tree**,
  the tree that release actually shipped. It is read with
  ``git show <tag>:<path>``, the way the citation checker reads a file out of
  a tree.

They have to be two comparisons, because they are two different claims. The
working copy's report is re-measured as soon as the next version starts, and
a report measured after the next version began says nothing about the
release that shipped before it. Comparing the release notes of v1.0.0
against that measurement would go red for a reason that has nothing to do
with the release -- and a gate that goes red for the wrong reason is a gate
that gets turned off.

What a document asserts
-----------------------
A number in a fenced code block, or in an inline code span, is a quotation:
the output of a command, or a sample of what a generated marker looks like.
The measurement script already draws that line -- it does not write a figure
that sits inside a code block -- and this script draws it with the same two
patterns, so that a number illustrated in a document is never read as a
number asserted by it.

What it prints
--------------
For every segment, for every source and every number: what the report of
that segment's tree says, what the source says, where in the source it says
it, and whether the two agree. A number a source does not state is reported
as "not written": a document that leaves a number out is not a document
that states it wrongly, and the difference is visible here rather than
hidden behind a green exit code.

The exit codes
--------------
* 0 -- every number that is written agrees with the report of its own tree.
* 1 -- a number disagrees, or one text says two things about it.
* 2 -- the published release body, or the tagged tree it is compared
  against, could not be read, so the second comparison is incomplete. That
  is not "the numbers agree": the published body was not checked.
  ``--offline`` skips it on purpose, and says so.

``--strict`` also fails when a text does not state a number at all.
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The figures the execution report is the authority for. The first seven are
#: the batch the release claims; the last two are the line counts behind the
#: coverage percentage.
BATCH = (
    "tests.total",
    "tests.fast",
    "tests.slow",
    "suite.passed",
    "suite.skipped",
    "suite.xfailed",
    "coverage.pct",
)
DETAIL = ("coverage.covered", "coverage.total")
FAMILIES = BATCH + DETAIL

#: The pages that describe the tree the reader is standing on. They are
#: compared against the working copy's report, because they are about the
#: working copy.
VERIFY_DOCUMENTS = (
    "docs/how-to-verify.md",
    "docs/how-to-verify.zh-CN.md",
)

#: The document that records the measurement of a tree. In the working copy it
#: is the authority for the working copy's texts; in the tagged tree it is the
#: authority for the published release body.
REPORT_DOCUMENT = "docs/reports/phase1-execution-report.md"

#: Markdown noise around a number: emphasis, code spans, spaces.
_MARKDOWN = r"[*`_\t ]*"

#: ``**1695**(**1546** 快 + **149** 集成)`` and its English and prose forms.
#: The fullwidth punctuation is written as escapes: ``ruff``'s RUF001 reads
#: it as ASCII punctuation, and this batch may not add a per-file ignore
#: (``pyproject.toml`` is outside the change it is allowed to make).
_TRIPLE = re.compile(
    rf"(?P<total>\d[\d,]*){_MARKDOWN}"
    rf"(?:(?:[A-Za-z]+\s+){{0,2}}?tests|个测试)?{_MARKDOWN}[(\uff08]"
    rf"{_MARKDOWN}(?P<fast>\d[\d,]*){_MARKDOWN}(?:快|fast){_MARKDOWN}[+,\uff0c]{_MARKDOWN}"
    rf"(?P<slow>\d[\d,]*){_MARKDOWN}(?:集成|集|integration){_MARKDOWN}[)\uff09]",
    re.IGNORECASE,
)

#: A test count a text states on its own: "1,695 tests", "1695 个测试". The
#: count may carry an adjective, the way the outward materials write it.
_TEST_COUNT = re.compile(
    r"(?P<total>\d[\d,]*)\s+(?:[A-Za-z]+\s+){0,2}?tests\b"
    r"|(?P<total_cn>\d[\d,]*)\s*个测试"
)

#: ``1546/1695 tests collected`` -- the same fast/integration split, written
#: as the output of a command a reader is told to run.
_COLLECT = re.compile(
    rf"(?P<n>\d[\d,]*){_MARKDOWN}/{_MARKDOWN}(?P<total>\d[\d,]*)"
    rf"{_MARKDOWN}tests collected",
    re.IGNORECASE,
)

#: One number of a suite summary: ``1694 passed``, ``0 xfailed``, ``1 skipped``.
_ATOM = re.compile(
    rf"(?<![\d,.])(?P<n>\d[\d,]*){_MARKDOWN}(?P<kind>passed|xfailed|skipped|failed|errors?)\b",
    re.IGNORECASE,
)

#: A coverage percentage, named by the word that introduces it. "coverage is
#: 93.3%" and "93.3% coverage" both count.
_COVERAGE_PCT = re.compile(
    r"(?:(?<![\w.])coverage|覆盖率)[^%\n|]{0,30}?(?P<pct>\d+(?:\.\d+)?)%"
    r"|(?P<pct_before>\d+(?:\.\d+)?)\s*%[^%\n|]{0,20}?(?:(?<![\w.])coverage|覆盖率)",
    re.IGNORECASE,
)

#: The line counts behind the percentage: ``7136 / 7650 lines``.
_COVERAGE_LINES = re.compile(
    rf"(?P<covered>\d[\d,]*){_MARKDOWN}/{_MARKDOWN}(?P<total>\d[\d,]*)"
    rf"{_MARKDOWN}(?:lines|行)"
)

#: A generated figure, copied into a document: ``<!--fig:tests.total-->1695<!--/fig-->``.
#: The value may not contain a ``<``, so an unclosed reference -- the way a
#: document names a figure instead of quoting it -- is not read as a value.
_FIG = re.compile(r"<!--fig:(?P<key>[A-Za-z0-9_./-]+)-->(?P<value>[^<]*)<!--/fig-->")

#: The heading that starts the appendix of the release body file. Everything
#: from there on is the provenance table, not the published text.
_APPENDIX = re.compile(r"^##\s+Appendix", re.MULTILINE)

#: A line that starts a list item or a heading.
_ITEM = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|#{1,6}\s)")

#: How far apart two atoms may sit and still be one summary.
_GAP = 24

#: Characters that end a sentence: two atoms on either side of one are two
#: summaries.
_SENTENCE_ENDS = "\u3002\uff01\uff1f\uff1b!?;"

#: The words that say "this summary is the complete-environment run" -- the
#: measurement the release claims.
_COMPLETE = re.compile(
    r"完整环境|完整测量|full environment|complete measurement"
    r"|(?:取|拉)了[^。\n]{0,4}第三方样本"
    r"|fetched[^.\n]{0,60}(?:fixtures|samples)",
    re.IGNORECASE,
)

#: The words that say "this summary is another environment" -- the run
#: without the third-party fixtures. It is a true number, about another
#: environment, and it is not the one the release claims.
_OTHER_ENVIRONMENT = re.compile(
    r"没[^。\n]{0,8}?(?:取|拉)[^。\n]{0,4}?第三方样本"
    r"|not fetched"
    r"|without the (?:third-party )?(?:fixtures|samples)",
    re.IGNORECASE,
)

#: The family a suite summary's number belongs to.
_SUMMARY_FAMILY = {
    "passed": "suite.passed",
    "skipped": "suite.skipped",
    "xfailed": "suite.xfailed",
}


@dataclass(frozen=True)
class Claim:
    """One number a text states, and where it states it."""

    family: str
    value: str
    line: int
    text: str


@dataclass(frozen=True)
class Source:
    """A text that claims numbers, and where the text came from."""

    name: str
    text: str


@dataclass(frozen=True)
class Finding:
    """A number that is wrong, or that a text does not state."""

    source: str
    family: str
    kind: str
    expected: str
    found: str
    line: int
    detail: str
    segment: str = ""


@dataclass(frozen=True)
class Segment:
    """One comparison: a set of texts and the numbers of one tree.

    The name is what the report calls the comparison, so that a finding can
    say which comparison it belongs to: "the working copy" and "the
    published release" are two different claims about two different trees,
    and a reader has to be able to tell them apart.
    """

    name: str
    authority_label: str
    authority: dict[str, str]
    sources: tuple[Source, ...]


def normalize(raw: str) -> str:
    """``1,695`` and ``1695`` are the same number; ``93.3%`` is ``93.3``."""
    return raw.replace(",", "").replace("%", "").strip()


def same(left: str, right: str) -> bool:
    """Whether two written numbers are the same number."""
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return left == right


def line_of(text: str, offset: int) -> int:
    """The 1-based line an offset sits on."""
    return text.count("\n", 0, offset) + 1


def block_of(text: str, offset: int) -> str:
    """The text unit that holds a claim: a table row, a list item, or a paragraph.

    The unit is what tells one summary from another. A table row is a row; a
    list item is the item and the lines that continue it; a paragraph is the
    paragraph.
    """
    lines = text.split("\n")
    index = line_of(text, offset) - 1
    if lines[index].lstrip().startswith("|"):
        return lines[index]
    start = index
    back = index - 1
    while back >= 0:
        line = lines[back]
        if not line.strip():
            break
        if _ITEM.match(line):
            # The line above starts an item. It belongs to this claim only
            # when the claim continues that item -- a continuation line is
            # indented, a new paragraph is not.
            if lines[back + 1][:1].isspace():
                start = back
            break
        back -= 1
    return "\n".join(lines[start : index + 1])


@dataclass(frozen=True)
class _Atom:
    """One number of a suite summary."""

    kind: str
    value: str
    start: int
    end: int


def summaries(text: str) -> Iterator[list[_Atom]]:
    """The atoms of the suite summaries, grouped into the summaries they form."""
    group: list[_Atom] = []
    previous: _Atom | None = None
    for match in _ATOM.finditer(text):
        atom = _Atom(match["kind"].lower(), normalize(match["n"]), match.start(), match.end())
        if previous is not None:
            gap = text[previous.end : atom.start]
            if len(gap) > _GAP or any(end in gap for end in _SENTENCE_ENDS):
                yield group
                group = []
        group.append(atom)
        previous = atom
    if group:
        yield group


def extract(source: Source, authority: dict[str, str]) -> tuple[dict[str, list[Claim]], list[str]]:
    """Every number the text states, by family.

    The second return value holds the summaries that are about another
    environment: they are true numbers, and they are not the ones the release
    claims.
    """
    text = source.text
    code_blocks, inline_code = quoted_spans(text)
    quotations = code_blocks + inline_code
    claims: dict[str, list[Claim]] = defaultdict(list)
    others: list[str] = []

    def add(family: str, value: str, offset: int, shown: str, *, marker: bool = False) -> None:
        spans = quotations if marker else code_blocks
        if any(start <= offset < end for start, end in spans):
            # A code block is a quotation: the output of a command, or a
            # sample of what a checker prints. It is not a claim about the
            # current tree.
            #
            # A *marker* in an inline code span is one too: it shows the
            # reader what a marker looks like, and the measurement script
            # will not write a number into it either.
            #
            # A number the page states in a sentence is a claim, though --
            # the project's own pages write their summary that way, and a
            # rule that read half a table cell would read the page wrongly.
            return
        line = line_of(text, offset)
        claim = Claim(family, normalize(value), line, shown.strip())
        if not any(
            seen.family == claim.family and seen.value == claim.value and seen.line == claim.line
            for seen in claims[family]
        ):
            claims[family].append(claim)

    for match in _TRIPLE.finditer(text):
        add("tests.total", match["total"], match.start(), match.group(0))
        add("tests.fast", match["fast"], match.start(), match.group(0))
        add("tests.slow", match["slow"], match.start(), match.group(0))

    for match in _TEST_COUNT.finditer(text):
        total = match["total"] or match["total_cn"]
        add("tests.total", total, match.start(), match.group(0))

    for match in _COLLECT.finditer(text):
        total = normalize(match["total"])
        numerator = normalize(match["n"])
        if not same(total, authority.get("tests.total", total)):
            add("tests.total", total, match.start(), match.group(0))
        if same(numerator, authority.get("tests.fast", "")):
            add("tests.fast", numerator, match.start(), match.group(0))
        elif same(numerator, authority.get("tests.slow", "")):
            add("tests.slow", numerator, match.start(), match.group(0))
        else:
            # The numerator is neither the fast count nor the integration
            # count, so it is not one of the two any more.
            add("tests.split", numerator, match.start(), match.group(0))

    for group in summaries(text):
        block = block_of(text, group[0].start)
        if _OTHER_ENVIRONMENT.search(block) and not _COMPLETE.search(block):
            others.append(
                f"line {line_of(text, group[0].start)}: "
                + ", ".join(f"{atom.value} {atom.kind}" for atom in group)
            )
            continue
        for atom in group:
            family = _SUMMARY_FAMILY.get(atom.kind)
            if family:
                add(family, atom.value, atom.start, f"{atom.value} {atom.kind}")

    for match in _COVERAGE_PCT.finditer(text):
        pct = match["pct"] or match["pct_before"]
        add("coverage.pct", pct, match.start(), match.group(0))

    for match in _COVERAGE_LINES.finditer(text):
        add("coverage.covered", match["covered"], match.start(), match.group(0))
        add("coverage.total", match["total"], match.start(), match.group(0))

    for match in _FIG.finditer(text):
        key = match["key"]
        if key in FAMILIES:
            # A generated figure. It is a claim like any other -- unless it
            # sits in a code block or an inline code span, where it shows
            # the reader what a marker looks like, and there it is an
            # illustration.
            add(key, match["value"], match.start(), match.group(0), marker=True)

    return dict(claims), others


def figures_in(text: str) -> dict[str, str]:
    """The figures a report records."""
    figures: dict[str, str] = {}
    for match in _FIG.finditer(text):
        figures.setdefault(match["key"], normalize(match["value"]))
    return figures


def read_authority() -> dict[str, str]:
    """The figures the working copy's execution report records."""
    path = REPO_ROOT / REPORT_DOCUMENT
    return figures_in(path.read_text(encoding="utf-8"))


@functools.cache
def citation_checker():
    """The citation checker, loaded as a module.

    How a file is read out of a tree is one rule, and it lives in the
    citation checker: a ``Tree`` reads a file with ``git show`` and tells
    "this tree does not have that file" apart from "the file is empty". A
    second copy of that here would be a second answer to the same question,
    and the two answers would drift.
    """
    script = Path(__file__).resolve().parent / "check-doc-citations.py"
    spec = importlib.util.spec_from_file_location("dexatlas_doc_citations", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@functools.cache
def measurement_script():
    """The measurement script, loaded as a module.

    What a document *asserts* is one rule, and the measurement script has
    already drawn that line: a marker inside a code block shows the reader
    what a marker looks like, and a marker inside inline code says the same
    thing in a sentence. Neither is a number to fill in. The same two
    patterns decide here what they decide there -- a second copy of the
    rule would be a second answer, and the two answers would drift.
    """
    script = Path(__file__).resolve().parent / "refresh-report-figures.py"
    spec = importlib.util.spec_from_file_location("dexatlas_refresh_figures", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def quoted_spans(text: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """The spans of a text that are quotations: code blocks, and inline code.

    The measurement script already draws this line, and the same two
    patterns draw it here: a fenced code block shows the reader the output
    of a command, and an inline code span says the same thing in a
    sentence. A second copy of the rule would be a second answer to the
    same question, and the two answers would drift.
    """
    ruler = measurement_script()
    code_blocks = [match.span() for match in ruler.CODE_BLOCK.finditer(text)]
    inline_code = [match.span() for match in ruler.INLINE_CODE.finditer(text)]
    return code_blocks, inline_code


def tagged_report(tag: str) -> tuple[str | None, str]:
    """The execution report as the tagged tree has it.

    The report of the tree the release shipped is the authority for the
    release body published for it. Reading it out of the working copy would
    compare a release with a measurement that was taken later, on a
    different tree.
    """
    tree = citation_checker().Tree(tag)
    if not tree.exists():
        return None, f"the {tag} tag is not in this checkout"
    text = tree.text(REPORT_DOCUMENT)
    if text is None:
        return None, f"the {tag} tree has no {REPORT_DOCUMENT}"
    return text, ""


def published_body(tag: str, repo: str = "") -> tuple[str | None, str]:
    """The release body published on GitHub, or the reason it is not readable."""
    gh = shutil.which("gh")
    if gh is None:
        return None, "gh is not installed"
    command = [gh, "release", "view", tag, "--json", "body"]
    if repo:
        command += ["--repo", repo]
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return None, f"gh could not be run: {exc}"
    if done.returncode != 0:
        return None, f"gh release view {tag} exited {done.returncode}: {done.stderr.strip()}"
    try:
        payload = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        return None, f"gh did not return JSON: {exc}"
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
        return None, "the published release has no body"
    return body.replace("\r\n", "\n"), ""


def release_body_portion(text: str) -> str:
    """The part of the release body file that is published: the file without
    its appendix, which is the provenance table and not the release text."""
    match = _APPENDIX.search(text)
    return text[: match.start()] if match else text


def compare(
    source: Source,
    claims: dict[str, list[Claim]],
    authority: dict[str, str],
    segment: str = "",
) -> list[Finding]:
    """What the source says against what the report says."""
    findings: list[Finding] = []
    for family in FAMILIES:
        expected = authority.get(family)
        if expected is None:
            continue
        found = claims.get(family, [])
        if not found:
            if family in DETAIL and "coverage.pct" not in claims:
                # The coverage is not stated at all; saying again that its
                # line counts are missing says nothing new.
                continue
            findings.append(Finding(source.name, family, "missing", expected, "", 0, "", segment))
            continue
        for claim in found:
            if not same(claim.value, expected):
                findings.append(
                    Finding(
                        source.name,
                        family,
                        "mismatch",
                        expected,
                        claim.value,
                        claim.line,
                        claim.text,
                        segment,
                    )
                )
    fast = authority.get("tests.fast", "?")
    slow = authority.get("tests.slow", "?")
    for claim in claims.get("tests.split", []):
        findings.append(
            Finding(
                source.name,
                "tests.fast / tests.slow",
                "mismatch",
                f"{fast} or {slow}",
                claim.value,
                claim.line,
                claim.text,
                segment,
            )
        )
    return findings


def compare_texts(
    left: Source,
    left_claims: dict[str, list[Claim]],
    right: Source,
    right_claims: dict[str, list[Claim]],
) -> list[Finding]:
    """One text against another, number by number."""
    findings: list[Finding] = []
    for family in FAMILIES:
        left_values = {claim.value for claim in left_claims.get(family, [])}
        right_values = {claim.value for claim in right_claims.get(family, [])}
        if not left_values or not right_values:
            continue
        for value in sorted(left_values - right_values):
            line = next(claim.line for claim in left_claims.get(family, []) if claim.value == value)
            findings.append(
                Finding(
                    left.name,
                    family,
                    "mismatch",
                    ", ".join(sorted(right_values)),
                    value,
                    line,
                    "",
                )
            )
    return findings


def render_source(
    source: Source,
    claims: dict[str, list[Claim]],
    authority: dict[str, str],
    findings: list[Finding],
    others: list[str],
) -> list[str]:
    """What one source says, number by number."""
    lines = [f"=== {source.name} ==="]
    for family in FAMILIES:
        expected = authority.get(family, "?")
        found = claims.get(family, [])
        broken = [f for f in findings if f.family == family]
        if not found:
            if family in DETAIL and "coverage.pct" not in claims:
                continue
            lines.append(f"  {family:<16} {'--':<10} {'--':<12} not written (report: {expected})")
            continue
        values = sorted({claim.value for claim in found})
        where = ", ".join(str(claim.line) for claim in found)
        shown = values[0] if len(values) == 1 else " / ".join(values)
        if broken:
            verdict = f"MISMATCH (report: {expected})"
        elif len(values) > 1:
            verdict = "CONFLICT"
        else:
            verdict = "ok"
        lines.append(f"  {family:<16} {shown:<10} {where:<12} {verdict}")
    for claim in claims.get("tests.split", []):
        lines.append(
            f"  {'tests.split':<16} {claim.value:<10} {claim.line!s:<12} "
            f"MISMATCH (report: {authority.get('tests.fast', '?')} or {authority.get('tests.slow', '?')})"
        )
    for other in others:
        lines.append(f"  note: another environment's summary, not compared -- {other}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare the release numbers across the outward texts."
    )
    parser.add_argument("--tag", default="v1.0.0", help="the release to compare (default: v1.0.0)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail when a text does not state a number at all",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the published release body, and say so",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="the GitHub repository to read the release from (default: the one the checkout names)",
    )
    args = parser.parse_args(argv)

    print("dexatlas outward-number parity")
    print(f"tag: {args.tag}")

    findings: list[Finding] = []
    incomplete = ""

    # ---- the working copy: the pages that describe this tree -------------
    authority = read_authority()

    sources: list[Source] = []
    for relative in VERIFY_DOCUMENTS:
        path = REPO_ROOT / relative
        if not path.is_file():
            print(f"missing document: {relative}", file=sys.stderr)
            continue
        sources.append(Source(relative, path.read_text(encoding="utf-8")))

    segments: list[Segment] = [
        Segment(
            name="the working copy",
            authority_label=f"{REPORT_DOCUMENT} (the working copy)",
            authority=authority,
            sources=tuple(sources),
        )
    ]

    # ---- the published release: its documents against the tree it shipped
    #
    # The release notes and the release body say what the release measured.
    # That release is frozen -- its tag is not cut again -- so their numbers
    # belong to the tree that tag points at, and to nothing measured since.
    # The page that says "the tree you are standing on has N tests" is a
    # different thing: it describes the working copy, and it is compared
    # against the working copy's report.
    published: Source | None = None
    body_source: Source | None = None
    tagged_text, tagged_reason = tagged_report(args.tag)
    if tagged_text is None:
        incomplete = f"the {args.tag} tree could not be read: {tagged_reason}"
        print(f"the {args.tag} tree: NOT READ -- {tagged_reason}")
    else:
        print(f"the {args.tag} tree: read")
        published_sources: list[Source] = []

        notes_relative = f"docs/releases/{args.tag}.md"
        notes_path = REPO_ROOT / notes_relative
        if notes_path.is_file():
            published_sources.append(Source(notes_relative, notes_path.read_text(encoding="utf-8")))
        else:
            print(f"missing document: {notes_relative}", file=sys.stderr)

        body_relative = f"docs/reports/{args.tag}-github-release-body.md"
        body_path = REPO_ROOT / body_relative
        if body_path.is_file():
            body_source = Source(
                body_relative, release_body_portion(body_path.read_text(encoding="utf-8"))
            )
            published_sources.append(body_source)
        else:
            print(f"missing document: {body_relative}", file=sys.stderr)

        if args.offline:
            print("published release body: not checked (--offline)")
        else:
            body, reason = published_body(args.tag, args.repo)
            if body is None:
                incomplete = f"the published release body could not be read: {reason}"
                print(f"published release body: NOT READ -- {reason}")
            else:
                published = Source(f"GitHub release {args.tag} (published body)", body)
                published_sources.append(published)
                print("published release body: read")

        segments.append(
            Segment(
                name=f"the published release {args.tag}",
                authority_label=f"{REPORT_DOCUMENT} (the {args.tag} tree)",
                authority=figures_in(tagged_text),
                sources=tuple(published_sources),
            )
        )

    for segment in segments:
        print()
        print(f"=== segment: {segment.name} ===")
        print(f"authority: {segment.authority_label}")
        missing_authority = [family for family in FAMILIES if family not in segment.authority]
        if missing_authority:
            print(
                "  the report records no "
                + ", ".join(missing_authority)
                + "; those numbers are not compared",
                file=sys.stderr,
            )
        for family in FAMILIES:
            print(f"  {family:<16} {segment.authority.get(family, '--')}")
        for source in segment.sources:
            claims, others = extract(source, segment.authority)
            source_findings = compare(source, claims, segment.authority, segment.name)
            findings.extend(source_findings)
            print()
            for line in render_source(source, claims, segment.authority, source_findings, others):
                print(line)

    if published is not None and body_source is not None:
        # The two texts are read against the same numbers -- the numbers of
        # the tree they shipped with -- so that the difference between them
        # is a difference between the two texts and not a difference between
        # the two trees they are read against.
        tagged_authority = segments[-1].authority
        published_claims, _ = extract(published, tagged_authority)
        body_claims, _ = extract(body_source, tagged_authority)
        drift = compare_texts(published, published_claims, body_source, body_claims)
        if drift:
            print()
            print(f"=== the published body against {body_relative} ===")
            for finding in drift:
                print(
                    f"  {finding.family:<16} published {finding.found} / "
                    f"in the repository {finding.expected}"
                )

    mismatches = [f for f in findings if f.kind == "mismatch"]
    missing = [f for f in findings if f.kind == "missing"]

    print()
    print("summary")
    for segment in segments:
        segment_mismatches = [f for f in mismatches if f.segment == segment.name]
        segment_missing = [f for f in missing if f.segment == segment.name]
        print(f"  segment {segment.name}: {len(segment.sources)} source(s)")
        print(f"    mismatches: {len(segment_mismatches)}")
        print(f"    not written: {len(segment_missing)}")
    if mismatches:
        print()
        print("mismatches")
        for segment in segments:
            segment_mismatches = [f for f in mismatches if f.segment == segment.name]
            if not segment_mismatches:
                continue
            print(f"  {segment.name}")
            for finding in segment_mismatches:
                print(f"    {finding.source}  {finding.family}")
                print(f"      report: {finding.expected}")
                print(f"      this text: {finding.found}  (line {finding.line})")
    if missing:
        print()
        print("not written")
        for segment in segments:
            segment_missing = [f for f in missing if f.segment == segment.name]
            if not segment_missing:
                continue
            print(f"  {segment.name}")
            for finding in segment_missing:
                print(f"    {finding.source}  {finding.family}  (report: {finding.expected})")

    if incomplete:
        print()
        print(incomplete)
        return 2
    if mismatches:
        return 1
    if missing and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
