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
QUOTED = re.compile(r"「[^」]*」|『[^』]*』|“[^”]*”|‘[^’]*’|\"[^\"\n]*\"")  # noqa: RUF001

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
    versions = frozenset(tag.lstrip("v") for tag in tags if tag.startswith("v"))
    newest_tag = max(versions, key=version_key) if versions else None

    package = PACKAGE_VERSION.search(
        (REPO / "src" / "dexatlas" / "__init__.py").read_text(encoding="utf-8")
    )
    package_version = package.group("value") if package else ""

    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
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
    return QUOTED.sub(lambda match: blank(match.group(0)), masked)


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


def is_project_version(match: re.Match[str], facts: Facts) -> bool:
    """Whether a version token is a version of *this* project.

    A token with the ``v`` prefix is one: the project writes its own versions
    that way. A bare number is one only when it is a version the repository
    knows about. A bare number that is neither is a tool's version — Apktool
    2.11.1, JADX 1.5.2 — and reading it as a release of this project would be
    a false report.
    """
    raw = match.group("raw")
    if raw.startswith("v"):
        return True
    name = raw.lstrip("v")
    return name in facts.versions or name == facts.pending


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
        if clause[0] <= match.start() < clause[1] and is_project_version(match, facts)
    ]
    if inside:
        return inside
    nearby = [
        match
        for match in versions
        if is_project_version(match, facts) and gap_between(match, predicate) <= BIND_LIMIT
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
            name = raw.lstrip("v")
            if name in facts.versions or name == facts.pending:
                continue
            if not raw.startswith("v"):
                continue  # a bare number is a tool's version until proven otherwise
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


def main(argv: list[str] | None = None) -> int:
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
    for name, text in documents:
        findings.extend(check_text(name, text, facts))

    base: str | None = None
    known: set[tuple[str, str, str, str]] = set()
    if args.base is not None:
        base = automatic_base() if args.base == "auto" else args.base
        if base is None or not git_succeeds("rev-parse", "--verify", f"{base}^{{commit}}"):
            print(f"could not resolve the base commit {args.base!r}", file=sys.stderr)
            return 2
        for name, text in documents_at(base):
            for finding in check_text(name, text, facts):
                known.add(finding.key)

    print("facts:")
    print(f"  tags: {', '.join(facts.tags) or '(none)'}")
    print(f"  package version: {facts.package_version}")
    print(f"  changelog: {', '.join(facts.changelog_versions) or '(none)'}")
    print(f"  newest release: v{facts.newest_release or '(none)'}")
    print(f"documents read: {len(documents)}")

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
