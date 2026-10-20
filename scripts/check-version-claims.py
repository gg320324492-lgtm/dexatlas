#!/usr/bin/env python3
"""Check the documentation's version claims against the repository itself.

    uv run python scripts/check-version-claims.py
    uv run python scripts/check-version-claims.py --base main

``scripts/check-doc-citations.py`` proves that a ``file:line`` citation still
points at what it names. It cannot prove that a sentence like "the newest tag
is v0.1.2" is true, because a version is not a line number.

This script proves that one, from facts the repository can be asked for:

* the tags — ``git tag``,
* the version in ``src/dexatlas/__init__.py``,
* ``CHANGELOG.md``.

Nothing here is a list of expected values written by hand. A hand-written list
would be a second copy of the truth, and this project has a documented history
of a checklist being rewritten into something easier to tick: a list written by
hand can be rewritten the same way, and nothing would notice. So the expected
values are read, not declared.

What is checked
---------------

* "v0.1.3 has been released" / "v0.1.3 has not been released" — against the tags.
* "the newest version is v0.1.2" — against the newest tag.
* "the v0.1.4 release" — a version that is neither a tag nor the release
  being prepared is a release that does not exist.

Statements and quotations
-------------------------

A document that quotes another document is not making a claim about the
present. The repository's convention is that a backtick means literal text,
and quotation marks around a phrase mean "this is what the other document
says". The second is honoured here: a version inside a quotation is not read
as a claim about the project now. The status page quotes a closed issue's
checklist — "``v0.1.0`` release: Not started" — and that is a true statement
about a piece of history, not a claim that v0.1.0 has not shipped.

The second thing that keeps false positives out is that a version is only read
as a *project* version when it says so: it carries the ``v`` prefix, or it is
one of the project's own versions. The documents also contain Apktool 2.11.1,
JADX 1.5.2, Androguard 4.1.4, OpenJDK 21.0.12.1 and a planned v0.5.0. None of
those is a release of this project, and a checker that reported them would be
worse than no checker.

What is *not* checked
---------------------

A version mentioned with no release context at all. "The samples are under
3 KB" and "Apktool 2.11.1" are not claims about releases, and the checker has
no business guessing at them.

Known findings and new ones
---------------------------

The repository's documents currently contain statements that were true when
they were written and are not true now — that is ordinary drift, and a tool
that could only say "there are problems" would be ignored. So the script can
compare against another commit:

    uv run python scripts/check-version-claims.py --base main

The findings that the base commit already had are reported as *known*; only
the ones this tree adds are failures. "Already fixed" is then a fact about
the repository rather than a list of exceptions in the script: once the fix
lands, the base no longer has the finding, and the finding disappears from
the report by itself.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import unquote

REPO = pathlib.Path(__file__).resolve().parent.parent

#: Markdown that is *history* rather than a statement about the project now.
#: The project does not rewrite a closed issue's checklist — docs/status.md
#: says so — so a claim inside one is not a claim about the present, and
#: flagging it would ask for a change the project has decided against.
HISTORY = (".github/issues/",)

#: A version number: three numeric parts, optionally prefixed with "v".
#: The lookaround keeps ``21.0.12.1`` (a JDK version) from being read as a
#: version of this project, and lets a version end a sentence.
VERSION = re.compile(r"(?<![A-Za-z0-9_.])(?P<raw>v?\d+\.\d+\.\d+)(?![A-Za-z0-9_])(?!\.\d)")

#: The version in ``src/dexatlas/__init__.py``.
PACKAGE_VERSION = re.compile(r"^__version__\s*=\s*[\"'](?P<value>[^\"']+)[\"']", re.MULTILINE)

#: A released version in ``CHANGELOG.md``: "## [0.1.3] — 2026-10-20".
CHANGELOG_ENTRY = re.compile(r"^##\s*\[(?P<value>\d+\.\d+\.\d+)\]", re.MULTILINE)

#: The link from ``[Unreleased]`` to the last release it follows.
UNRELEASED_LINK = re.compile(
    r"^\[Unreleased\]:\s*\S*compare/(?P<value>v?\d+\.\d+\.\d+)", re.MULTILINE
)

#: ``<!--fig:key-->value<!--/fig-->`` — the figures the refresh script writes
#: into the execution report. They are measurements, so a hand-written number
#: that disagrees with one of them is a number that was copied and went stale.
FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)

#: The report that holds the measured figures of a release.
REPORT_AT_TAG = "docs/reports/phase1-execution-report.md"

#: The release notes of a release.
RELEASE_NOTES = "docs/releases/{tag}.md"

#: One section of the changelog: "## [0.1.3] — 2026-10-20" and what follows it.
CHANGELOG_SECTION = re.compile(
    r"^## \[(?P<version>\d+\.\d+\.\d+)\][^\n]*\n(?P<body>.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)

#: A coverage percentage a text states. "coverage is 93.9%" and "93.9%
#: coverage" both count; a percentage that belongs to a module, or to the
#: version before this one, does not — it is not attached to the word.
COVERAGE_STATED = re.compile(
    r"(?:coverage|覆盖率)[^%\n]{0,40}?(?P<after>\d+(?:\.\d+)?)\s*%"
    r"|(?P<before>\d+(?:\.\d+)?)\s*%[^%\n]{0,20}?(?:coverage|覆盖率)"
)

#: A percentage a text states, with or without a word attached to it:
#: "93.9%" and "93.9 %" are the same number.
PERCENTAGE = re.compile(r"(?<![\d.])(?P<number>\d+(?:\.\d+)?)\s*%")

#: A test count a text states: "444 tests (347 fast, 97 integration)".
TESTS_STATED = re.compile(
    r"(?P<total>\d+)\s+tests\b"
    r"(?:\s*\(\s*(?P<fast>\d+)\s+fast\s*,\s*(?P<slow>\d+)\s+(?:integration|slow)\s*\))?"
)

#: A number that belongs to the version before this one: "up from 89.2%",
#: "the previous release had 89.2% coverage". The marker may stand before
#: the number or after it, and it refers to the nearest percentage.
#:
#: "up from" is on its own: it always introduces the number that follows
#: it, so it never says anything about a number it stands behind.
PREVIOUS_UP_FROM = re.compile(r"up\s+from", re.IGNORECASE)

#: A marker that says the nearest number belongs to an earlier release:
#: "previously", "the previous release", "上一版".
PREVIOUS_VERSION = re.compile(
    r"previously|previous|prior|last\s+(?:release|version)|上一(?:版|个版本|版本)|以前",
    re.IGNORECASE,
)

#: "before" and "earlier" are words about time as well, so they only count
#: when they sit right next to the number.
PREVIOUS_VERSION_NEAR = re.compile(r"before|earlier|之前", re.IGNORECASE)

#: How far a previous-version marker may be from the number it speaks about.
#: "the previous release had 89.2% coverage" puts thirteen characters
#: between them, so the window has to be wider than a word.
PREVIOUS_WINDOW = 60
PREVIOUS_WINDOW_NEAR = 12

#: What may not lie between a previous-version marker and the number it
#: speaks about: another stated figure (that one is the previous number),
#: the end of a sentence, or a conjunction (which starts a claim of its
#: own).
BREAKS = re.compile(
    r"\d+(?:\.\d+)?\s*%|\d+\s+tests\b|[;；。！!？?]|\.(?=\s|$)|\band\b|\bbut\b|而|但"  # noqa: RUF001
)

#: The same, for a marker that follows the number: a clause boundary
#: breaks it too, because "94.0% coverage, up from 89.2%" introduces a
#: second number and the marker is about that one.
BREAKS_FORWARD = re.compile(BREAKS.pattern + r"|[,，、:：]")  # noqa: RUF001

#: A badge that states a number:
#: "https://img.shields.io/badge/tests-275%20passing-brightgreen.svg".
#: The label and the number are picked out of the URL rather than matched
#: against one form of it: the URL is percent-encoded, and a badge that says
#: "coverage-89%25" says 89%, not "89%25".
BADGE = re.compile(
    r"img\.shields\.io/badge/(?P<label>[A-Za-z][A-Za-z0-9+._-]*?)"
    r"-(?P<number>\d+(?:\.\d+)?)(?P<rest>[^/\"'\s]*?)\.svg"
)

#: The badges that state a number of this project. The numbers a badge may
#: state are gathered per label, so the caller decides what would answer it.
BADGES = ("tests", "test", "coverage")

#: The rest of a badge's URL says what its number is about: "%20passing" for a
#: count of tests, "%25" for a coverage. A badge whose text says something else
#: — "failing", "remaining" — is not a count of anything, and is left alone.
BADGE_TEXT = {"tests": ("passing",), "test": ("passing",), "coverage": ("%",)}

#: How far a badge may be from the measured number. A badge states a whole
#: percentage, and 89.2% is written "89%" on it.
BADGE_TOLERANCE = 0.5

#: Words that say a release has happened.
RELEASED = re.compile(
    r"已发布|已经发布|已发行|已上线|已推送|正式发布|发布了|发布"
    r"|\breleased\b|\bpublished\b|\bshipped\b|\bis out\b|\bwent out\b"
)

#: Words that say a release has *not* happened.
NOT_RELEASED = re.compile(
    r"尚未发布|还没有发布|还未发布|没有发布|还没发布|未发布|待发布|等待发布"
    r"|\bunreleased\b|\bnot\s+(?:yet\s+)?(?:released|published|shipped)\b|\bpending\s+release\b"
)

#: "the newest tag is v0.1.2". The noun decides what the claim is about: the
#: newest *tag* is a fact about git, the newest *version* is a fact about the
#: release, and the two differ while a release is being prepared.
#:
#: The fullwidth punctuation in this file is on purpose — it is what the
#: documents are written with — so ruff's "ambiguous character" rule is
#: silenced on the lines that have to name it.
LATEST = re.compile(
    r"(?:最新|最近的|当前|现行)\s*(?:的\s*)?(?P<noun>tag|标签|版本|version|release|发布)\s*"
    r"(?:是|为|＝|=|:|：)\s*"  # noqa: RUF001
    r"|(?:latest|most recent|current|newest)\s+(?P<noun2>tag|version|release)\s+"
    r"(?:is|was|are|were|=|:)\s*"
)

#: "the newest is v0.1.2", "最新的是 v0.1.2" — the same claim without the
#: noun. Without a noun there is no way to tell a claim about the newest
#: *tag* from a claim about the newest *release*, so the claim is only
#: wrong when the number is wrong under both readings.
LATEST_NOUN = re.compile(
    r"(?:最新|最近的|当前|现行)\s*(?:的\s*)?(?:是|为|＝|=|:|：)\s*"  # noqa: RUF001
    r"|(?:latest|most recent|current|newest)\s+(?:is|was|are|were)\s*"
)

#: A version that stands where a release is named: "the v0.1.4 release",
#: "版本 v0.1.4".
RELEASE_NOUN = re.compile(
    r"(?:release|Release|版本|版本号)\s*[:：]?\s*(?P<first>v?\d+\.\d+\.\d+)"  # noqa: RUF001
    r"|(?P<second>v?\d+\.\d+\.\d+)\s*(?:的\s*)?(?:release|Release|版本|版本号)"
)

#: Connectors that turn a version into the point the work is measured from:
#: "the fixes after v0.1.2". The claim is then about the work since that
#: release, and it is only true while that release is the last one.
SINCE_AFTER = re.compile(r"\s*(?:之后|以后|以来|起)")
SINCE_BEFORE = re.compile(r"(?:after|since|following|post-)\s+$", re.IGNORECASE)

#: Quotation marks. A phrase inside them is what another document said.
#: These are the marks this repository uses: 「」 in the Chinese documents,
#: and the curly marks in the English ones.
QUOTED = re.compile(r"「[^」]*」|『[^』]*』|“[^”]*”|‘[^’]*’")  # noqa: RUF001

#: An ASCII-quoted phrase. This repository does not use the ASCII double
#: quote as a quotation mark — the convention is 「」 and the backtick — so
#: an ASCII-quoted phrase is prose, and a claim inside one is a claim. The
#: one exception is an example: see EXAMPLE.
ASCII_QUOTED = re.compile(r"\"[^\"\n]*\"")

#: What introduces an example: a sentence like "the newest tag is v0.1.2".
#: An example is not a claim about the project, and the repository's own
#: changelog quotes the checker's own subject this way.
EXAMPLE = re.compile(
    r"(?:like|such as|for\s+example|e\.g\.|例如|比如)[,，]?\s*$",  # noqa: RUF001
    re.IGNORECASE,
)

#: A fenced code block. Its content is a listing, not a statement.
CODE_FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

#: What separates one clause of a sentence from the next. A claim binds to
#: the versions in its own clause; a table row stays one clause, because a
#: pipe is not a clause boundary.
CLAUSE = re.compile(r"[：:，,；;。！!？?、]")  # noqa: RUF001

#: How far a version may be from a predicate and still be the one it speaks
#: about. The status page puts a predicate and its version in one line with
#: a few words between them; anything further away is a different sentence.
BIND_LIMIT = 40


@dataclass(frozen=True)
class Facts:
    """What the repository says about its own releases."""

    tags: tuple[str, ...]
    versions: frozenset[str]
    newest_tag: str | None
    package_version: str
    changelog_versions: tuple[str, ...]
    changelog_newest: str | None
    unreleased_link: str | None

    @property
    def pending(self) -> str | None:
        """The release being prepared: in the changelog, not tagged yet."""
        if self.changelog_newest is None:
            return None
        if self.changelog_newest in self.versions:
            return None
        return self.changelog_newest

    @property
    def newest_release(self) -> str | None:
        """The newest version that has been released, or is being prepared."""
        known = list(self.versions)
        if self.pending is not None:
            known.append(self.pending)
        return max(known, key=version_key) if known else None

    @property
    def series(self) -> frozenset[tuple[str, str]]:
        """The major.minor pairs this project's own releases live in.

        "0.1" for a project whose releases are 0.1.0, 0.1.1 and so on. A
        bare number in one of those series is a version of this project even
        when the repository has never heard of it — "0.1.4 has been
        released" is a claim about this project whatever the tags say — while
        a bare number in no series of this project belongs to a tool:
        Apktool 2.11.1, JADX 1.5.2, Androguard 4.1.4.
        """
        known = set(self.versions)
        if self.pending is not None:
            known.add(self.pending)
        pairs = {series_of(version) for version in known}
        return frozenset(pair for pair in pairs if pair is not None)


@dataclass(frozen=True)
class Finding:
    """One claim that the repository's own facts contradict."""

    path: str
    line: int
    kind: str
    version: str
    message: str
    excerpt: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        """What makes two findings the same finding.

        The line number is not part of it: a line that moves is still the same
        claim, and a check that treated a moved line as a new one would
        report the same old problem again on every edit above it.
        """
        return (self.path, self.kind, self.version, self.excerpt)

    def render(self) -> str:
        return f"{self.path}:{self.line}  {self.kind}  {self.message}\n      {self.excerpt}"


def version_key(version: str) -> tuple[int, int, int]:
    """A comparable form of "0.1.3".

    A version that is not three numbers is not a version, and sorts below
    every version that is — it must never win a comparison by accident.
    """
    parts = version.lstrip("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return (-1, -1, -1)
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def base_version(version: str) -> str:
    """The release a version belongs to: "0.1.4.dev1" is a development build
    of 0.1.4."""
    return version.split(".dev", 1)[0]


def series_of(version: str) -> tuple[str, str] | None:
    """The major.minor pair a version belongs to: ("0", "1") for "0.1.4".

    ``None`` for anything that is not three numbers, because a version
    without a series cannot be placed in one.
    """
    parts = version.lstrip("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return (parts[0], parts[1])


def git(*args: str) -> str:
    """Run a git command in the repository and return its output.

    The output is decoded as UTF-8 whatever the machine's locale is: a
    document in this repository is UTF-8, and reading it as something else
    would fail on a machine whose default encoding is not UTF-8.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def git_succeeds(*args: str) -> bool:
    """Whether a git command works. Used for the optional lookups."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


def git_optional(*args: str) -> str | None:
    """The output of a git command, or None when the command does not work."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def facts_of(tags: tuple[str, ...], package: str, changelog: str) -> Facts:
    """The facts a set of tags, a package version and a changelog describe."""
    versions = frozenset(tag.lstrip("v") for tag in tags if tag.startswith("v"))
    newest_tag = max(versions, key=version_key) if versions else None

    package_match = PACKAGE_VERSION.search(package)
    package_version = package_match.group("value") if package_match else ""

    changelog_versions = tuple(CHANGELOG_ENTRY.findall(changelog))
    changelog_newest = max(changelog_versions, key=version_key) if changelog_versions else None

    link = UNRELEASED_LINK.search(changelog)
    unreleased_link = link.group("value").lstrip("v") if link else None

    return Facts(
        tags=tags,
        versions=versions,
        newest_tag=newest_tag,
        package_version=package_version,
        changelog_versions=changelog_versions,
        changelog_newest=changelog_newest,
        unreleased_link=unreleased_link,
    )


def read_facts() -> Facts:
    """Ask the repository what its releases are."""
    tags = tuple(sorted(git("tag", "--list").split()))
    if not tags:
        # A clone without tags cannot answer any of the questions this script
        # asks. Reporting "nothing is wrong" from such a clone would be the
        # worst kind of answer: a green check that checked nothing.
        raise SystemExit(
            "this clone has no tags, so the release state cannot be checked.\n"
            "Fetch them and try again:\n"
            "  git fetch --tags\n"
            "(in CI: check out with fetch-depth: 0)"
        )
    package = (REPO / "src" / "dexatlas" / "__init__.py").read_text(encoding="utf-8")
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    return facts_of(tags, package, changelog)


def read_facts_at(ref: str) -> Facts:
    """What the repository said about its releases at another commit.

    The base commit's *own* facts, not this tree's. The base's documents are
    read against what the base believed: a claim that this commit made false
    — by releasing a new version, say — is not drift the base already had,
    and reading the base against this tree's facts would say that it was.

    The tags are the ones the base can reach, so a tag this commit pushed is
    not among them, and the package version and the changelog are the ones
    that commit carried.
    """
    tags = tuple(sorted(git("tag", "--merged", ref).split()))
    if not tags:
        # A base that predates the project's first release has no tags of
        # its own. Reading it as "nothing has ever been released" would make
        # every release claim in its documents a finding, and exempt far
        # more than it should.
        tags = tuple(sorted(git("tag", "--list").split()))
    package = git_optional("show", f"{ref}:src/dexatlas/__init__.py") or ""
    changelog = git_optional("show", f"{ref}:CHANGELOG.md") or ""
    return facts_of(tags, package, changelog)


def check_facts(facts: Facts) -> list[Finding]:
    """Check the repository's own three sources against each other.

    These need no document and no prose: the tags, the package version and
    the changelog each say what the releases are, and they have to agree.
    """
    findings: list[Finding] = []

    def add(path: str, kind: str, version: str, message: str) -> None:
        findings.append(
            Finding(
                path=path,
                line=0,
                kind=kind,
                version=version,
                message=message,
                excerpt=message,
            )
        )

    for tag in sorted(facts.versions, key=version_key):
        if tag not in facts.changelog_versions:
            add(
                "CHANGELOG.md",
                "fact-changelog-missing",
                tag,
                f"there is a tag v{tag} but CHANGELOG.md has no [{tag}] section",
            )

    for version in sorted(set(facts.changelog_versions) - set(facts.versions), key=version_key):
        if version == facts.changelog_newest:
            continue  # the release being prepared is not tagged yet
        add(
            "CHANGELOG.md",
            "fact-changelog-untagged",
            version,
            f"CHANGELOG.md records [{version}] but there is no v{version} tag",
        )

    package = base_version(facts.package_version)
    if facts.newest_tag is not None and version_key(package) < version_key(facts.newest_tag):
        add(
            "src/dexatlas/__init__.py",
            "fact-package-behind",
            package,
            f"the package says {facts.package_version} but v{facts.newest_tag} has been released",
        )
    elif facts.changelog_newest is not None and version_key(package) < version_key(
        facts.changelog_newest
    ):
        add(
            "src/dexatlas/__init__.py",
            "fact-package-behind",
            package,
            f"the package says {facts.package_version} but CHANGELOG.md records "
            f"[{facts.changelog_newest}]",
        )

    if (
        facts.unreleased_link is not None
        and facts.newest_tag is not None
        and version_key(facts.unreleased_link) < version_key(facts.newest_tag)
    ):
        add(
            "CHANGELOG.md",
            "fact-changelog-link-behind",
            facts.unreleased_link,
            f"CHANGELOG.md's [Unreleased] link starts at v{facts.unreleased_link} "
            f"but v{facts.newest_tag} has been released",
        )

    return findings


def blank(text: str) -> str:
    """Replace text with spaces, keeping its length and its line breaks."""
    return "".join("\n" if char == "\n" else " " for char in text)


def mask(text: str) -> str:
    """Blank out the parts of a document that are not the document's own words.

    Quotations and code listings are somebody else's text. Blanking them
    keeps their length, so a line number still points at the right line.
    """
    masked = CODE_FENCE.sub(lambda match: blank(match.group(0)), text)
    masked = QUOTED.sub(lambda match: blank(match.group(0)), masked)
    return mask_examples(masked)


def mask_examples(text: str) -> str:
    """Blank the ASCII-quoted phrases that are examples.

    An ASCII double quote is not one of this repository's quotation marks,
    so an ASCII-quoted phrase is prose and a claim inside it is checked like
    any other. An example is the exception: a sentence like "the newest tag
    is v0.1.2" is not a claim about the project, and the repository's own
    changelog quotes the checker's subject that way.
    """

    def blank_if_example(match: re.Match[str]) -> str:
        before = text[max(0, match.start() - 40) : match.start()]
        if EXAMPLE.search(before):
            return blank(match.group(0))
        return match.group(0)

    return ASCII_QUOTED.sub(blank_if_example, text)


def clause_of(text: str, position: int) -> tuple[int, int]:
    """The span of the clause a position belongs to."""
    start = 0
    end = len(text)
    for match in CLAUSE.finditer(text):
        if match.end() <= position:
            start = match.end()
        elif match.start() > position:
            end = match.start()
            break
    return start, end


def collapse(text: str) -> str:
    """A line, with its whitespace folded, for use as an identity."""
    return " ".join(text.split())


def is_project_version(raw: str, facts: Facts) -> bool:
    """Whether a version token is a version of *this* project.

    A token with the ``v`` prefix is one: the project writes its own versions
    that way. A bare number is one when the repository knows it, and one when
    it belongs to the series this project's releases live in: "0.1.4" is a
    version of this project even before it is tagged, and "0.1.4 has been
    released" is a claim about this project whatever the tags say. A bare
    number in no series of this project is a tool's version — Apktool 2.11.1,
    JADX 1.5.2 — and reading it as a release of this project would be a
    false report.
    """
    if raw.startswith("v"):
        return True
    name = raw.lstrip("v")
    if name in facts.versions or name == facts.pending:
        return True
    pair = series_of(name)
    return pair is not None and pair in facts.series


def gap_between(first: re.Match[str], second: re.Match[str]) -> int:
    """How many characters lie between two spans."""
    if first.end() <= second.start():
        return second.start() - first.end()
    if second.end() <= first.start():
        return first.start() - second.end()
    return 0


def versions_for(
    versions: list[re.Match[str]], predicate: re.Match[str], clause: tuple[int, int], facts: Facts
) -> list[re.Match[str]]:
    """The versions a predicate is about.

    A predicate speaks about the versions in its own clause. When the clause
    has none, it falls back to the nearest version in the same line, within
    a short distance — which is how "these fixes have not been released:
    the newest tag is v0.1.2" ends up bound to v0.1.2.
    """
    inside = [
        match
        for match in versions
        if clause[0] <= match.start() < clause[1] and is_project_version(match.group("raw"), facts)
    ]
    if inside:
        return inside
    nearby = [
        match
        for match in versions
        if is_project_version(match.group("raw"), facts)
        and gap_between(match, predicate) <= BIND_LIMIT
    ]
    if not nearby:
        return []
    closest = min(gap_between(match, predicate) for match in nearby)
    return [match for match in nearby if gap_between(match, predicate) == closest]


def is_since_anchor(version: re.Match[str], text: str) -> bool:
    """Whether a version is the point the work is measured from.

    "the fixes after v0.1.2" measures from v0.1.2, and that claim is only
    true while v0.1.2 is the last release.
    """
    if SINCE_AFTER.match(text, version.end()):
        return True
    return bool(SINCE_BEFORE.search(text, max(0, version.start() - 12), version.start()))


def check_text(path: str, text: str, facts: Facts) -> list[Finding]:
    """Every claim in one document that the repository's facts contradict."""
    findings: list[Finding] = []
    masked = mask(text)
    original_lines = text.splitlines()
    masked_lines = masked.splitlines()

    for number, line in enumerate(masked_lines, 1):
        if not line.strip():
            continue
        original = original_lines[number - 1] if number - 1 < len(original_lines) else line
        excerpt = collapse(original)[:160]
        versions = list(VERSION.finditer(line))
        if not versions:
            continue
        claimed: list[tuple[str, str, str]] = []

        # -- "the newest tag / version is X" -----------------------------
        for match in LATEST.finditer(line):
            found = VERSION.search(line, match.end())
            if not found:
                continue
            if not is_project_version(found.group("raw"), facts):
                continue
            version = found.group("raw").lstrip("v")
            noun = match.group("noun") or match.group("noun2") or ""
            target = facts.newest_tag if noun in {"tag", "标签"} else facts.newest_release
            if target is None or version == target:
                continue
            claimed.append(
                (
                    "latest",
                    version,
                    f"it says the newest {noun or 'version'} is v{version}, "
                    f"but the newest is v{target}",
                )
            )

        # -- "the newest is X" — no noun, so no way to tell a tag from a
        #    release. It is only wrong when the number is wrong under both
        #    readings.
        for match in LATEST_NOUN.finditer(line):
            found = VERSION.search(line, match.end())
            if not found:
                continue
            if not is_project_version(found.group("raw"), facts):
                continue
            version = found.group("raw").lstrip("v")
            targets = {target for target in (facts.newest_tag, facts.newest_release) if target}
            if not targets or version in targets:
                continue
            newest = max(targets, key=version_key)
            claimed.append(
                (
                    "latest",
                    version,
                    f"it says the newest version is v{version}, but the newest is v{newest}",
                )
            )

        # -- "X has been released" / "X has not been released" ------------
        not_released = list(NOT_RELEASED.finditer(line))
        spoken = line
        for match in not_released:
            spoken = spoken[: match.start()] + blank(match.group(0)) + spoken[match.end() :]
        released = list(RELEASED.finditer(spoken))

        for match in released:
            clause = clause_of(line, match.start())
            for version in versions_for(versions, match, clause, facts):
                name = version.group("raw").lstrip("v")
                if name in facts.versions or name == facts.pending:
                    continue
                claimed.append(
                    (
                        "released",
                        name,
                        f"it says v{name} has been released, but there is no v{name} tag",
                    )
                )

        for match in not_released:
            clause = clause_of(line, match.start())
            for version in versions_for(versions, match, clause, facts):
                name = version.group("raw").lstrip("v")
                if name not in facts.versions or name == facts.pending:
                    continue
                if is_since_anchor(version, line):
                    if facts.newest_tag is None or version_key(name) >= version_key(
                        facts.newest_tag
                    ):
                        continue
                    claimed.append(
                        (
                            "stale-anchor",
                            name,
                            f"it says the work after v{name} has not been released, "
                            f"but the newest release is v{facts.newest_tag}",
                        )
                    )
                    continue
                claimed.append(
                    (
                        "unreleased",
                        name,
                        f"it says v{name} has not been released, but v{name} is a tag",
                    )
                )

        # -- a release that does not exist -------------------------------
        for match in RELEASE_NOUN.finditer(line):
            raw = match.group("first") or match.group("second")
            if not raw:
                continue
            if not is_project_version(raw, facts):
                continue  # a bare number in no series of this project is a tool's
            name = raw.lstrip("v")
            if name in facts.versions or name == facts.pending:
                continue
            claimed.append(
                (
                    "unknown-version",
                    name,
                    f"it names the v{name} release, but there is no v{name} tag",
                )
            )

        for kind, version, message in claimed:
            findings.append(
                Finding(
                    path=path,
                    line=number,
                    kind=kind,
                    version=version,
                    message=message,
                    excerpt=excerpt,
                )
            )

    return findings


def measured_figures(tag: str) -> dict[str, str]:
    """The figures the execution report of a release carries.

    An empty result means the release predates the generated figures, or that
    it has no report: there is nothing measured to compare with, and nothing
    is claimed.
    """
    report = git_optional("show", f"{tag}:{REPORT_AT_TAG}")
    if report is None:
        return {}
    return dict(FIGURE.findall(report))


def release_documents(
    tag: str, version: str, by_path: dict[str, str]
) -> list[tuple[str, str, int]]:
    """The documents that state a release's numbers, with their line offsets.

    The offset is the number of lines before the text starts, so that a
    finding in the changelog's section points at the line in the changelog.
    """
    documents: list[tuple[str, str, int]] = []

    notes = RELEASE_NOTES.format(tag=tag)
    if notes in by_path:
        documents.append((notes, by_path[notes], 0))

    changelog = by_path.get("CHANGELOG.md", "")
    for match in CHANGELOG_SECTION.finditer(changelog):
        if match.group("version") != version:
            continue
        offset = changelog[: match.start("body")].count("\n")
        documents.append(("CHANGELOG.md", match.group("body"), offset))
    return documents


def percentage(value: str) -> float | None:
    """A percentage as a number: "94.0%" and "94" are the same number."""
    try:
        return float(value.rstrip("%"))
    except ValueError:
        return None


@dataclass(frozen=True)
class Percentage:
    """A percentage a document states."""

    value: str
    start: int
    end: int
    labelled: bool
    """Whether the word "coverage" is attached to it."""


def stated_percentages(line: str) -> list[Percentage]:
    """The percentages a line states.

    A percentage the word "coverage" is attached to is a coverage claim
    whatever else the line says. One with no word attached to it is a number
    that may or may not be a coverage, and the caller decides.
    """
    found: list[Percentage] = []
    starts: dict[int, str] = {}
    for match in COVERAGE_STATED.finditer(line):
        value = match.group("after") or match.group("before")
        if value is None:
            continue
        start = match.start("after") if match.group("after") else match.start("before")
        starts[start] = value
        found.append(Percentage(value=value, start=start, end=start + len(value), labelled=True))
    for match in PERCENTAGE.finditer(line):
        if match.start() in starts:
            continue
        value = match.group("number")
        found.append(
            Percentage(
                value=value, start=match.start(), end=match.start() + len(value), labelled=False
            )
        )
    found.sort(key=lambda item: item.start)
    return found


def belongs_to_previous_version(
    line: str, start: int, end: int, *, backward_only: bool = False
) -> bool:
    """Whether a number is a number from an earlier release.

    "up from 89.2%" and "the previous release had 89.2% coverage" both state
    what the version before this one measured, and neither number is this
    release's own coverage. The marker may stand before the number or after
    it; what may not lie between them is another stated figure, the end of a
    sentence, or a conjunction.

    A marker behind the number and a marker in front of it are not judged
    the same way. A marker in front qualifies the number it introduces — a
    comma may sit inside the noun phrase between them ("the previous
    release, 89.2%"). A marker behind qualifies the number it follows only
    when no clause boundary lies between them: "94.0% coverage, up from
    89.2%" introduces a second number, and the marker is about that one.
    """
    for pattern, window, behind in (
        (PREVIOUS_UP_FROM, PREVIOUS_WINDOW, False),
        (PREVIOUS_VERSION, PREVIOUS_WINDOW, True),
        (PREVIOUS_VERSION_NEAR, PREVIOUS_WINDOW_NEAR, True),
    ):
        for match in pattern.finditer(line):
            if match.end() <= start:
                gap = line[match.end() : start]
                distance = start - match.end()
                broken = BREAKS.search(gap)
            elif behind and not backward_only and match.start() >= end:
                gap = line[end : match.start()]
                distance = match.start() - end
                broken = BREAKS_FORWARD.search(gap)
            else:
                continue
            if distance > window or broken:
                continue
            return True
    return False


def check_stated_numbers(
    path: str, text: str, offset: int, expected: dict[str, str], version: str
) -> list[Finding]:
    """The numbers a release document states, against the numbers measured.

    ``expected`` holds the figures the release is measured by: the number of
    tests the report measured at that release, and the coverage the report of
    that release measured. A figure that is missing from it was never
    measured, and nothing is claimed about it.

    A percentage the word "coverage" is attached to is a coverage claim. A
    percentage with no word attached to it is one only when the document
    states no other percentage: a document with several of them is stating
    several different things — the coverage of this release, of the one
    before it, of a module — and the checker cannot tell which is which. A
    percentage that belongs to an earlier release is not a claim about this
    one and is not checked against it.
    """
    findings: list[Finding] = []
    measured = expected.get("coverage.pct")
    lines = text.splitlines()
    # A number between the markers is generated, not written by hand.
    spoken_lines = [FIGURE.sub(lambda match: " " * len(match.group(0)), line) for line in lines]
    stated = [stated_percentages(line) for line in spoken_lines]
    labelled = any(item.labelled for items in stated for item in items)
    only_one = sum(len(items) for items in stated) == 1
    bare_is_coverage = not labelled and only_one

    for number, line in enumerate(lines, 1):
        spoken = spoken_lines[number - 1]
        excerpt = collapse(line)[:160]

        for item in stated[number - 1]:
            if not item.labelled and not bare_is_coverage:
                continue
            if measured is None:
                continue
            if belongs_to_previous_version(spoken, item.start, item.end):
                continue
            if percentage(item.value) == percentage(measured):
                continue
            findings.append(
                Finding(
                    path=path,
                    line=offset + number,
                    kind="release-coverage",
                    version=version,
                    message=(
                        f"it says the coverage is {item.value}%, "
                        f"the measured coverage is {measured}"
                    ),
                    excerpt=excerpt,
                )
            )

        for match in TESTS_STATED.finditer(spoken):
            total = match.group("total")
            fast = match.group("fast")
            slow = match.group("slow")
            if belongs_to_previous_version(
                spoken, match.start("total"), match.end("total"), backward_only=True
            ):
                continue
            measured_tests = expected.get("tests.total")
            if measured_tests is not None and total != measured_tests:
                findings.append(
                    Finding(
                        path=path,
                        line=offset + number,
                        kind="release-tests",
                        version=version,
                        message=(
                            f"it says the release had {total} tests, "
                            f"the measured number is {measured_tests}"
                        ),
                        excerpt=excerpt,
                    )
                )
            if fast is not None and slow is not None and int(fast) + int(slow) != int(total):
                findings.append(
                    Finding(
                        path=path,
                        line=offset + number,
                        kind="release-tests",
                        version=version,
                        message=(
                            f"it says {fast} fast and {slow} integration, "
                            f"which is not the {total} tests it states"
                        ),
                        excerpt=excerpt,
                    )
                )
    return findings


def badge_figures(facts: Facts, report_figures: dict[str, str]) -> dict[str, list[str]]:
    """The numbers a badge may state: the tree as it is now, and the last release.

    A badge that says how many tests the project has is right when it names
    the tree as it is now, and right when it names the release the project
    last shipped. The badge that shipped with v0.1.2 named neither: it said
    275, and the project had 444.
    """
    newest = facts.newest_tag
    released = measured_figures(f"v{newest}") if newest else {}
    return {
        "tests": [report_figures.get("tests.total"), released.get("tests.total")],
        "test": [report_figures.get("tests.total"), released.get("tests.total")],
        "coverage": [report_figures.get("coverage.pct"), released.get("coverage.pct")],
    }


def check_release_numbers(
    facts: Facts, documents: list[tuple[str, str]], notes: list[str] | None = None
) -> list[Finding]:
    """The numbers the release documents state, against the numbers measured.

    Three comparisons, each between two measurements:

    * The **test count** a release document states is the number the report
      measured at that release — the report's ``history.<tag>.tests``, taken
      from an archive of the tag. It describes history, so it does not go
      stale as the code grows.
    * The **coverage** a release document states is the coverage the report of
      that release measured. A release whose report predates the generated
      figures has nothing to compare with: it is skipped, and the skip is
      said out loud.
    * The **badge** in the readme is compared with the current tree's figures,
      because a badge is a claim about the project as it is now.

    The release documents are read as they are now — that is the text a
    reader sees — and the measurements come from the release they describe.
    """
    findings: list[Finding] = []
    by_path = dict(documents)
    report_figures = dict(FIGURE.findall(by_path.get(REPORT_AT_TAG, "")))
    tags = sorted(
        (tag for tag in facts.tags if tag.startswith("v")),
        key=lambda tag: version_key(tag.lstrip("v")),
    )
    for tag in tags:
        version = tag.lstrip("v")
        measured = measured_figures(tag)
        expected = {
            "tests.total": report_figures.get(f"history.{tag}.tests"),
            "coverage.pct": measured.get("coverage.pct"),
        }
        if expected["coverage.pct"] is None and notes is not None:
            notes.append(
                f"{tag}: the report of that release has no measured coverage, "
                f"so only its test count is checked"
            )
        for path, text, offset in release_documents(tag, version, by_path):
            findings.extend(check_stated_numbers(path, text, offset, expected, version))
    return findings


def check_badges(path: str, text: str, figures: dict[str, list[str]]) -> list[Finding]:
    """The numbers the badges state, against the numbers that were measured.

    A badge is the first thing a reader sees, and it looks as if a service
    had generated it. A hand-written number in a URL drifts the moment the
    code changes, and the drift is invisible: nothing about the URL says when
    it was written. The URL cannot hold the report's markers, so the badge is
    compared with the report's figures instead.

    ``figures`` maps a badge's label to the numbers that would answer it: the
    tree as it is now, and the release it last shipped. A badge that states
    one of them is not wrong. The badge that shipped with v0.1.2 was never
    moved on, and it told readers the project had 275 tests when it had 444.
    """
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in BADGE.finditer(line):
            label = match.group("label").lower()
            if label not in BADGES:
                continue
            rest = unquote(match.group("rest"))
            if not any(word in rest for word in BADGE_TEXT[label]):
                continue
            measured = [value for value in figures.get(label, []) if value]
            if not measured:
                continue
            value = percentage(match.group("number"))
            if value is None:
                continue
            numbers = [percentage(item) for item in measured]
            if any(item is not None and abs(value - item) <= BADGE_TOLERANCE for item in numbers):
                continue
            findings.append(
                Finding(
                    path=path,
                    line=number,
                    kind="badge",
                    version=label,
                    message=(
                        f"the {label} badge says {match.group('number')}, "
                        f"the measured numbers are {', '.join(measured)}"
                    ),
                    excerpt=collapse(line)[:160],
                )
            )
    return findings


def documents_in_tree() -> list[tuple[str, str]]:
    """The markdown files of the working tree, with their text."""
    documents: list[tuple[str, str]] = []
    for name in git("ls-files", "*.md").splitlines():
        name = name.strip()
        if not name or name.startswith(HISTORY):
            continue
        path = REPO / name
        if not path.is_file():
            continue
        documents.append((name, path.read_text(encoding="utf-8", errors="replace")))
    return documents


def documents_at(ref: str) -> list[tuple[str, str]]:
    """The markdown files of another commit, with their text."""
    documents: list[tuple[str, str]] = []
    for name in git("ls-tree", "-r", "--name-only", ref).splitlines():
        name = name.strip()
        if not name.endswith(".md") or name.startswith(HISTORY):
            continue
        documents.append((name, git("show", f"{ref}:{name}")))
    return documents


def automatic_base() -> str | None:
    """The commit to compare against when the caller does not name one.

    On a branch, the point the branch left the mainline. On the mainline
    itself, the commit before this one. ``None`` means there is nothing to
    compare against, and every finding counts as a new one.
    """
    if git_succeeds("rev-parse", "--verify", "origin/main"):
        head = git("rev-parse", "HEAD").strip()
        main = git("rev-parse", "origin/main").strip()
        if head != main and git_succeeds("merge-base", "HEAD", "origin/main"):
            return git("merge-base", "HEAD", "origin/main").strip()
    if git_succeeds("rev-parse", "--verify", "HEAD^"):
        return git("rev-parse", "--verify", "HEAD^").strip()
    return None


def use_utf8_output() -> None:
    """Make the output independent of the console's encoding.

    A finding quotes the line it is about, and that line may hold an emoji —
    the execution report marks its findings with 🔴. A console that cannot
    encode it (GBK, cp1252) would kill the script halfway through its report,
    and the exit code it managed to give would be the one a crash gives: 1,
    the same as the one a real finding gives. The report has to finish on
    every machine, so the output is UTF-8 and a character that cannot be
    written is replaced rather than raised.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            continue


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    parser = argparse.ArgumentParser(
        description="Check the documentation's version claims against the repository."
    )
    parser.add_argument(
        "--base",
        default=None,
        help=(
            "compare against this commit: only the findings this tree adds are "
            "failures. 'auto' picks the merge base with origin/main, or the "
            "previous commit on the mainline."
        ),
    )
    args = parser.parse_args(argv)

    facts = read_facts()
    findings = check_facts(facts)

    documents = documents_in_tree()
    notes: list[str] = []
    findings.extend(check_release_numbers(facts, documents, notes))
    report_figures = dict(FIGURE.findall(dict(documents).get(REPORT_AT_TAG, "")))
    badges = badge_figures(facts, report_figures)
    for name, text in documents:
        findings.extend(check_badges(name, text, badges))
        findings.extend(check_text(name, text, facts))

    base: str | None = None
    known: set[tuple[str, str, str, str]] = set()
    if args.base is not None:
        base = automatic_base() if args.base == "auto" else args.base
        if base is None or not git_succeeds("rev-parse", "--verify", f"{base}^{{commit}}"):
            print(f"could not resolve the base commit {args.base!r}", file=sys.stderr)
            return 2
        # The base's own facts. The base's documents are read against what
        # the base believed, so that a claim this commit made false — by
        # releasing a version, say — is a new finding rather than drift the
        # base already had. Reading the base against this tree's facts would
        # have said the opposite, and the check would have passed.
        base_facts = read_facts_at(base)
        base_documents = documents_at(base)
        base_figures = dict(FIGURE.findall(dict(base_documents).get(REPORT_AT_TAG, "")))
        base_badges = badge_figures(base_facts, base_figures)
        for finding in check_release_numbers(base_facts, base_documents):
            known.add(finding.key)
        for name, text in base_documents:
            for finding in check_badges(name, text, base_badges):
                known.add(finding.key)
            for finding in check_text(name, text, base_facts):
                known.add(finding.key)

    print("facts:")
    print(f"  tags: {', '.join(facts.tags) or '(none)'}")
    print(f"  package version: {facts.package_version}")
    print(f"  changelog: {', '.join(facts.changelog_versions) or '(none)'}")
    print(f"  newest release: v{facts.newest_release or '(none)'}")
    print(f"documents read: {len(documents)}")
    for note in notes:
        print(f"  skipped: {note}")

    if base is None:
        failures = findings
        print(f"findings: {len(findings)}")
    else:
        failures = [finding for finding in findings if finding.key not in known]
        print(f"findings: {len(findings)} ({len(findings) - len(failures)} already in {base[:8]})")
    for finding in findings:
        print(f"  {finding.render()}")

    if failures:
        print(f"\n{len(failures)} version claim(s) contradict the repository.")
        return 1
    print("\nEvery version claim matches the repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
