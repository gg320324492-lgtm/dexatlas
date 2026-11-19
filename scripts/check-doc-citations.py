"""Check every file:line citation in the documentation against the code.

Run it directly to see the drift, or let the test suite run it:

    uv run python scripts/check-doc-citations.py

The provenance document and the large-APK benchmark cite specific lines. A
citation that has drifted is a small lie, and there have been enough of them
to be worth a tool.

What a citation claims
-----------------------

A citation makes two claims, and the check follows both of them.

*Where* — the file it names has to exist, the lines it names have to be
inside that file, and those lines have to hold code. Every citation is
checked for this, whatever the sentence around it says.

*What* — when the sentence around it also names a symbol, the symbol has to
be in that file and inside the lines it names. A symbol the file defines has
to be defined in the lines, or the lines have to be inside the body it opens;
a symbol the file only mentions has to be mentioned in the lines. Naming a
class and citing the lines where it is built is a concrete claim, and it can
be checked exactly.

*Which value* — when the sentence around it states a number, the lines it
names have to carry that number. "1694 passed" cited at
``phase1-execution-report.md:879`` is a claim about the line 879, and a line
that says "1710 passed" does not say it. The check names both numbers when
they differ, so the fix is a number and not a hunt.

A number is only compared when the sentence says enough for the comparison
to mean something: a count with the word it counts ("1694 passed"), a
percentage ("93.3%") or a fingerprint ("sha256:18f3ab15…"). A bare number is
not one — a table row numbered ``1`` and a status code ``404`` are labels.
A number that is a limit ("≥16/20"), a section ("§3"), a quotation, or
part of a version ("2.11.1") is not one either.

The value findings are reported and they do not fail the check yet. A number
in a document is a snapshot of a measurement, and every measurement writes
new numbers: the outward texts are refreshed by hand after it, and that
refresh is the release session's work. What the checker owes it is the two
numbers side by side — the one the sentence says and the one the line holds.

What it does not check
----------------------

A citation that only points at a location — "this logic lives in
``core/pipeline.py:296``" — cannot say whether the code there is still the
code that was meant. There is nothing in the sentence to check the lines
against. Those citations get the *where* check and nothing more, unless the
document declares what the location holds.

A citation that names a symbol is checked for that symbol being *named* in
the lines, not for the lines being where the symbol is *defined*: a document
that cites the place a class is used is not caught by pointing at another
place it is used.

What a declaration says
-----------------------

A citation that only points at a location can declare what that location
holds, in the citation itself::

    `src/dexatlas/cli/main.py:289-291` `anchor: def version(`

The declaration is a piece of the source that has to be inside the cited
range. The range points at a place; the declaration says what is there. A
range that has drifted to somewhere else no longer holds the declared
fragment, and the citation is reported.

The declaration names no line and no number, so it does not go stale the way
a line number does. It is checked against the source, not against the
document, so a measurement that rewrites a figure cannot invalidate it, and
the only thing that can move it is the code it quotes.

The declaration is checked the way the strongest reading allows. An anchor
that is a bare name — ``version`` — is checked the way a named symbol is
checked: the file has to define it in the range, or the range has to be
inside the body it opens. Any other anchor is a fragment of the source —
``def version(``, ``@app.get("/projects"`` — and has to appear in the range
verbatim, whitespace aside.
A citation that names a symbol is not compared with a value as well: a
number in the same sentence then counts what the symbol holds — "28 checks
in ``_rest_requests()``" — rather than being written on the cited line.

Which tree a citation is about
------------------------------

A citation is a claim about *a* tree. Most documents describe the tree they
are checked out in, and for them the working copy is the right tree. Some do
not: the release body says in its own header that its line numbers refer to
the v1.0.0 release tree, and the tag is not the working copy. A checker that
reads every citation out of the working copy cannot honour that: it checks
that the line is still there, not that the line is the one the document meant.
The two trees have drifted apart since the tag, so the same number means two
different things in them, and a document can mix them without anybody noticing.

So the checker is told which tree each document describes, reads that
document's citations out of that tree, and says so in its summary. The
declaration is checked too: the tree has to be in this checkout, and the
document has to quote the fingerprint of that tree's measurement. A registry
that has drifted away from the documents it names is a finding, not a silent
pass.

The summary says how many citations each kind of check reached, so the number
of citations that carry a real check is never a guess. The exit code is the
answer: 0 when every citation holds, 1 when one has drifted. A checker that
always says 0 is a gate that never opens.
"""

from __future__ import annotations

import ast
import functools
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, replace

REPO = pathlib.Path(__file__).resolve().parent.parent


def release_documents(root: pathlib.Path) -> list[pathlib.Path]:
    """The release notes and the release body, wherever the tree has them.

    The suffixes are compared explicitly: a glob pattern matches
    case-insensitively on Windows and case-sensitively on Linux, so a
    ``V1.0.0.MD`` written in upper case would be checked on one platform and
    never read on the other.
    """
    releases = root / "docs" / "releases"
    reports = root / "docs" / "reports"
    return [
        *(
            sorted(path for path in releases.iterdir() if path.suffix == ".md")
            if releases.is_dir()
            else []
        ),
        *(
            sorted(
                path
                for path in reports.iterdir()
                if path.suffix == ".md" and path.name.endswith("-github-release-body.md")
            )
            if reports.is_dir()
            else []
        ),
    ]


#: The documents whose citations are checked.
#:
#: Every document that states a ``file:line`` belongs here. A citation in a
#: document nobody checks is a citation nobody has to keep true, and the
#: release notes and the release body carry the appendix that says where each
#: number of a release came from: those line numbers drifted for a long time
#: because the documents were not on this list.
DOCS: list[pathlib.Path] = [
    REPO / "docs" / "analysis-provenance.md",
    REPO / "docs" / "architecture" / "public-contracts.md",
    REPO / "docs" / "reports" / "phase1-execution-report.md",
    REPO / "docs" / "benchmarks" / "large-apk.md",
    # The howto for the social preview card states, for every figure on the
    # card, the file and the line it was read from. Two of those citations
    # were wrong for a long time, because the document was not on this list:
    # a citation nobody checks is a citation nobody has to keep true.
    REPO / "docs" / "reports" / "social-preview-howto.md",
    # The review reports of the November 2026 round. Each one declares, where
    # it states its basis, the commit its line numbers are anchored to, and
    # this is the round whose reports drifted for days precisely because they
    # were not on this list: a citation nobody checks is a citation nobody has
    # to keep true.
    REPO / "docs" / "reports" / "outreach-first-read.md",
    REPO / "docs" / "reports" / "readme-image-consistency.md",
    REPO / "docs" / "reports" / "case-studies-client-read.md",
    REPO / "docs" / "reports" / "round-two-fresh-read.md",
    REPO / "docs" / "reports" / "stale-number-scan-2.md",
    REPO / "docs" / "reports" / "denominator-and-tree-pass.md",
    REPO / "docs" / "reports" / "local-vs-ci-gates.md",
    REPO / "docs" / "reports" / "english-reader-review-2.md",
    # The evidence package's isolation report: it quotes the line numbers of
    # the packager, of the pipeline that produced the workspace it checked and
    # of the paths module. A citation nobody checks is a citation nobody has
    # to keep true.
    REPO / "docs" / "reports" / "evidence-package-isolation.md",
    # The three rehearsal reports of the release week. Each one quotes the
    # line numbers of the tree it rehearsed against -- the invitation, the
    # container image and the post-release procedure -- so their citations
    # have to keep being true.
    REPO / "docs" / "reports" / "invitation-reader-rehearsal.md",
    REPO / "docs" / "reports" / "docker-examples-gap.md",
    REPO / "docs" / "reports" / "post-release-rehearsal.md",
    # The landing of the Docker sample change: it quotes the CLI's count line,
    # the JSON report's summary keys, the sample's pinned numbers and the CI
    # step that checks them, so all of those have to keep being true.
    REPO / "docs" / "reports" / "docker-image-samples.md",
    # The wording of the "the backend did not finish" evidence record: it
    # quotes the evidence module and the pipeline that writes the record, so
    # the line numbers it names have to keep being true.
    REPO / "docs" / "reports" / "evidence-incomplete-backend-wording.md",
    # The outward-number parity report: it quotes the lines of the four
    # outward texts it compared and of the checker it wrote.
    REPO / "docs" / "reports" / "outward-number-parity.md",
    # The candidate that carries the manifest's fourth key forward to v1.1.0:
    # it quotes the packager, the contract table and the three places that
    # pin the manifest's shape.
    REPO / "docs" / "reports" / "v1.1.0-candidate-c10-manifest.md",
    # The reports of the batch that followed the release: the second reader
    # rehearsal of the invitation, the build time C6's criterion (a) asks for,
    # the gates' own regression tests, and the landing of the auto-write
    # mechanism. Each one quotes line numbers of the tree it was written
    # against, so their citations have to keep being true.
    REPO / "docs" / "reports" / "m10-reader-rehearsal-2nd.md",
    REPO / "docs" / "reports" / "c6-build-time-from-ci.md",
    REPO / "docs" / "reports" / "gate-self-checks.md",
    REPO / "docs" / "reports" / "figures-auto-write-landing.md",
    # The reports of the batch that fixed the materials the second reader
    # rehearsal found, and the note that closes M8-4 in the history.
    REPO / "docs" / "reports" / "m10-material-fixes.md",
    REPO / "docs" / "reports" / "m8-4-note-and-c17.md",
    # The reports of the batch that aligned the candidates with reality,
    # rehearsed the materials for the third time, and built the method
    # for telling local gates and CI gates apart.
    REPO / "docs" / "reports" / "c5-c6-status-alignment.md",
    REPO / "docs" / "reports" / "m10-reader-rehearsal-3rd.md",
    REPO / "docs" / "reports" / "platform-gate-inventory.md",
    # The report of the batch that fixed the CI job that was missing its
    # temporary-directory redirect, and the one that closed the gaps the
    # third reader rehearsal found in the M10 materials.
    # The reports of the batch that let the citations declare what they
    # claim, and the read-only audit of the hand-written numbers the
    # mechanism does not cover.
    # The report of the batch that taught the checker to compare the values a
    # citation states with the values on the lines it names.
    REPO / "docs" / "reports" / "citation-value-comparison.md",
    REPO / "docs" / "reports" / "citation-anchor-declarations.md",
    REPO / "docs" / "reports" / "handwritten-numbers-audit.md",
    REPO / "docs" / "reports" / "card-travels-with-the-measurement.md",
    REPO / "docs" / "reports" / "ci-temp-redirect-fix.md",
    REPO / "docs" / "reports" / "m10-round3-fixes.md",
    REPO / "docs" / "reports" / "declarations-outward.md",
    # The report of the batch that gave the unguarded hand-written
    # numbers their gates (or an explicit reason not to).
    REPO / "docs" / "reports" / "unguarded-numbers-gates.md",
    # The report of the batch that turned the prose numbers into markers,
    # so adding a test no longer means hand-editing any number.
    REPO / "docs" / "reports" / "prose-to-markers.md",
    # The report of the batch that closed C17: the last hand-written
    # measurement numbers (the collect summaries, the document count, the
    # test-file table's rows, the card's sidecar) are written or audited by
    # the mechanism.
    REPO / "docs" / "reports" / "c17-markers-everywhere.md",
    # The report of the fourth reader rehearsal: the one that proved the
    # five material fixes had never reached the tagged tree, and that the
    # F2 fallback really falls back when both ports are taken.
    REPO / "docs" / "reports" / "m10-reader-rehearsal-4th.md",
    *sorted((REPO / "docs" / "releases").glob("*.md")),
    *sorted((REPO / "docs" / "reports").glob("*-github-release-body.md")),
]

#: The trees some documents describe, and the ref each one names.
#:
#: A document that quotes line numbers has to say which tree those numbers are
#: in, and this is where the checker learns it. The value is a git ref: the
#: tree the document's citations are read out of.
#:
#: The release body is the one document that says so out loud -- its appendix
#: header reads "Line numbers refer to the v1.0.0 release tree". Without this
#: registry the checker read that document's citations out of the working
#: copy, so it checked the release tree's numbers against a tree that had
#: moved on since the release, and it had no way to say so.
TREE_DOCUMENTS: dict[str, str] = {
    "docs/reports/v1.0.0-github-release-body.md": "v1.0.0",
    # The November 2026 review reports. The ref is the commit each report
    # names where it declares its basis; the report has to quote that tree's
    # measurement fingerprint, and the citations are read out of that tree.
    "docs/reports/outreach-first-read.md": "48a56b5",
    "docs/reports/readme-image-consistency.md": "3ef6676",
    "docs/reports/case-studies-client-read.md": "9e1aa61",
    "docs/reports/round-two-fresh-read.md": "ec52527",
    "docs/reports/stale-number-scan-2.md": "9e1aa61",
    "docs/reports/denominator-and-tree-pass.md": "d43369b",
    "docs/reports/local-vs-ci-gates.md": "9e1aa61",
    "docs/reports/english-reader-review-2.md": "2c456e0",
}

#: The document that carries a tree's measurement record. The record holds the
#: fingerprint of the tree the measurement was taken on, and that fingerprint
#: is what ties a document to the tree it says it describes.
RECORD_DOCUMENT = "docs/reports/phase1-execution-report.md"

#: The measurement record inside that document.
RECORD = re.compile(r"<!--report-figures:(.*?)-->", re.DOTALL)

#: A source fingerprint a document quotes. The documents abbreviate it, and
#: not always by the same amount: one release body quotes ``sha256:4e72ac49…``
#: and another quotes ``sha256:787282…``. Six hex characters is the shortest
#: abbreviation the documents use, so that is what is recognised -- a shorter
#: match would fit half the fingerprints by accident.
FINGERPRINT = re.compile(r"sha256:([0-9a-f]{6,})", re.IGNORECASE)


def git_output(*args: str) -> str | None:
    """What a git command says, or None when git cannot answer.

    ``None`` means "this repository does not have that", not "the answer was
    empty": a tree that is not in this checkout is a finding, and a finding
    that reads like an empty answer would be missed.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


class Tree:
    """One tree a document's citations can be read against.

    The working copy is a tree; a tagged release is another. A citation says
    "line N of this file", and which file that is depends on the tree the
    sentence is about.
    """

    def __init__(self, ref: str | None = None) -> None:
        self.ref = ref

    @property
    def is_working_copy(self) -> bool:
        return self.ref is None

    @property
    def label(self) -> str:
        """How this tree is named in the checker's report."""
        return "the working copy" if self.ref is None else f"the {self.ref} tree"

    def exists(self) -> bool:
        """Whether this tree is in this checkout."""
        if self.ref is None:
            return True
        return git_output("rev-parse", "--verify", "--quiet", f"{self.ref}^{{commit}}") is not None

    def lines(self, path: pathlib.Path) -> tuple[str, ...] | None:
        """The lines of a file, as this tree has them.

        None means the tree does not have the file at all, which is a different
        answer from a file with no lines in it.
        """
        if self.ref is None:
            return file_lines(path)
        try:
            relative = path.relative_to(REPO).as_posix()
        except ValueError:
            return None
        return tree_file_lines(self.ref, relative)

    def text(self, relative: str) -> str | None:
        """The content of a file of this tree, named by its path in the repo."""
        if self.ref is None:
            path = REPO / relative
            return path.read_text(encoding="utf-8") if path.is_file() else None
        content = git_output("show", f"{self.ref}:{relative}")
        return content


@functools.cache
def tree_file_lines(ref: str, relative: str) -> tuple[str, ...] | None:
    """The lines of a file in a tagged tree, read once."""
    content = git_output("show", f"{ref}:{relative}")
    if content is None:
        return None
    return tuple(content.splitlines())


#: The tree a document describes when it says nothing about one.
WORKING_COPY = Tree()

#: A backticked span of the documentation.
SPAN = re.compile(r"`([^`\n]+)`")

#: path:line or path:start-end — the whole backticked span has to be a citation.
#:
#: Markdown is a target like any other: a document that says "the number is
#: at ``docs/status.md:37``" has made a claim about a line of a file, and
#: the claim is exactly as checkable as one about a line of Python.
CITATION = re.compile(r"^([\w./-]+\.(?:py|sh|toml|yml|md)):(\d+)(?:-(\d+))?$")

#: A bare line number: ``:143``. The file it belongs to is the one the same
#: block of the text named before it — "``core/pipeline.py:296``, ``:143``"
#: is the same file twice.
BARE_LINE = re.compile(r"^:(\d+)(?:-(\d+))?$")

#: The dashes that join two citations into one range.
DASHES = "-–—"  # noqa: RUF001

#: A declaration of what a citation's range holds: ``anchor: def version(``.
#:
#: A citation that only points at a location has nothing to check the lines
#: against. The declaration gives it something: a piece of the source that
#: has to be inside the range. It names no line and no number, so it does
#: not go stale when the code moves or when a measurement rewrites a
#: figure; the line number does, and the declaration is what says whether
#: the line number still points at the right thing.
DECLARATION = re.compile(r"^anchor:\s*(\S.*?)\s*$")

#: An anchor that is a bare name: ``version``. A name is checked the way a
#: named symbol is checked — defined in the range, or the range inside the
#: body it opens. Any other anchor is a fragment of the source and has to
#: appear in the range verbatim.
ANCHOR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: The documents in which every citation has to say what it points at.
#:
#: A citation that names a symbol says what it points at on its own. A
#: citation that only points at a location says nothing, and the checker can
#: only ask whether the location holds something. In these documents it
#: asks more: the citation has to carry a declaration, and a citation that
#: does not is reported as declaring nothing.
DECLARING_DOCUMENTS: frozenset[str] = frozenset(
    {
        "docs/architecture/public-contracts.md",
    }
)

#: A backticked span that names a symbol: ``ApkMetadata``, ``ManifestComponent.kind``,
#: ``read_resources()``, ``Project.tool_versions``, ``DEFAULT_METHOD_LIMIT = 200_000``.
#: A span that is a sentence, a path or a value is not a name.
NAME = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    r"(?:\(\))?"
    r"(?::\s*[A-Za-z_][A-Za-z0-9_\[\], |]*(?:\s*\|\s*None)?)?"
    r"(?:\s*=\s*\S+)?$"
)

#: How far a symbol may sit from the range a sentence cites. Zero: a cited
#: range has to hold the symbol. A line of slack let the range beside it in
#: the same file satisfy the check, which is how the pipeline's three backend
#: stages went unchecked — each one answered for the next.
SLACK = 0

#: Brackets, Chinese and English. A comma inside them does not end a clause.
OPEN_BRACKETS = "（([{"  # noqa: RUF001
CLOSE_BRACKETS = "）)]}"  # noqa: RUF001

#: Characters that end a sentence, Chinese and English.
SENTENCE_ENDS = "。！？；!?;"  # noqa: RUF001

#: Characters that end a clause inside a sentence.
CLAUSE_ENDS = "，,：:—–→⇒"  # noqa: RUF001

#: Words that are capitalised or in backticks but are not symbols: the names
#: of the tools, of the project, and the type names of Python.
#:
#: The backend names are here in lower case too, and deliberately so. They are
#: the *values* the ``tool`` field holds — a document that writes them says
#: which backends exist, not that the cited lines mention them. The docstring
#: of :func:`is_symbolic` says as much: ``jadx`` and ``apktool`` are words a
#: sentence uses, not code a citation points at. Without the lower-case
#: spellings, a table row that lists the backends and cites the line that
#: fills the field was reported as drift, because the file the citation
#: names happens to mention one of them in a docstring.
NOT_SYMBOLS = {
    "The",
    "This",
    "A",
    "An",
    "In",
    "It",
    "And",
    "But",
    "For",
    "When",
    "If",
    "None",
    "True",
    "False",
    "Any",
    "Optional",
    "str",
    "int",
    "bool",
    "float",
    "bytes",
    "list",
    "dict",
    "set",
    "tuple",
    "object",
    "DexAtlas",
    "JADX",
    "Jadx",
    "jadx",
    "Apktool",
    "apktool",
    "Androguard",
    "androguard",
    "Java",
    "Smali",
    "Kotlin",
    "Android",
    "Gradle",
    "Python",
    "JSON",
    "YAML",
    "TOML",
}

#: Directories that are never part of a citation's target.
#: The project's local state: the backends, the helper scripts, the temporary
#: files and the packages uv has fetched. A citation that resolved to a copy
#: of a file in there would be a citation to the wrong tree. ``fixtures`` is
#: fetched, not committed: a bare name that resolved to a downloaded sample
#: would make the verdict depend on what the machine happens to have fetched.
#: The caches and ``dist`` are the tools' own outputs, never citation targets.
SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "build",
    ".claude",
    ".scratch",
    "node_modules",
    "fixtures",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


@dataclass(frozen=True)
class Citation:
    """One ``file:line`` reference in a document."""

    document: pathlib.Path
    line: int
    rel: str
    start: int
    end: int
    target: pathlib.Path | None
    ambiguous: bool
    text: str
    #: The tree the document describes. The cited lines are read out of it,
    #: not out of the working copy, when the document says which tree it means.
    tree: Tree = WORKING_COPY
    #: What the cited range is declared to hold. Empty when the citation
    #: declares nothing.
    anchors: tuple[str, ...] = ()

    @property
    def where(self) -> str:
        return f"{self.document.name}:{self.line}  {self.rel}:{self.start}-{self.end}"

    def lines(self) -> tuple[str, ...] | None:
        """The lines of the file this citation names, in the tree it describes."""
        if self.target is None:
            return None
        return self.tree.lines(self.target)


@dataclass(frozen=True)
class Resolved:
    """One citation span, with the file and the range it names.

    A span may name its file (``core/pipeline.py:296``) or only a line
    (``:296``). The second form is read against the file the same block of
    the text named before it, so the file is filled in here.
    """

    match: re.Match[str]
    rel: str
    start: int
    end: int
    #: The declarations that belong to this citation.
    anchors: tuple[str, ...] = ()


@dataclass(frozen=True)
class Declaration:
    """A declaration that names no citation.

    It says what some range holds, and there is no range: the declaration
    sits where no citation can be bound to it. It is reported rather than
    ignored, because a declaration nobody reads is a claim nobody checks.
    """

    line: int
    text: str


@dataclass(frozen=True)
class Clause:
    """One piece of a sentence, with the citations and the symbols it holds."""

    document: pathlib.Path
    line: int
    citations: tuple[Citation, ...]
    #: For every citation, the names it claims to locate.
    claims: tuple[tuple[str, ...], ...]
    #: For every citation, the values the sentence states about it.
    values: tuple[tuple[StatedValue, ...], ...] = ()


@dataclass(frozen=True)
class Finding:
    """A citation that no longer says what the document says it says."""

    where: str
    kind: str
    detail: str
    text: str = ""

    def render(self) -> str:
        rendered = f"{self.where}  {self.kind}: {self.detail}"
        return f"{rendered}  |  {self.text}" if self.text else rendered


@dataclass(frozen=True)
class Report:
    """The result of checking a set of documents."""

    citations: int
    named: int
    road_sign: int
    findings: tuple[Finding, ...]
    #: The citations that declare what their range holds.
    declared: int = 0
    #: How many citations had a value of their own compared against the
    #: lines they name.
    valued: int = 0
    #: For every tree a document was read against: its name, how many
    #: documents it described and how many citations it answered for.
    trees: tuple[tuple[str, int, int], ...] = ()
    #: A digest of what the check was about: the documents it read and the
    #: trees it resolved them against.
    subject: str = ""

    @property
    def unresolved(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind in {"unresolved", "ambiguous"})

    @property
    def drifted(self) -> tuple[Finding, ...]:
        """The citations whose symbol is no longer where the document says it is."""
        return tuple(
            f for f in self.findings if f.kind not in {"unresolved", "ambiguous", "value drifted"}
        )

    @property
    def value_findings(self) -> tuple[Finding, ...]:
        """The citations whose value is no longer on the line they name.

        These are reported and they do not fail the check yet. A number in
        a document is a snapshot of a measurement, and a measurement writes
        new numbers every time it runs: the outward texts are refreshed by
        hand after it, and the refresh is the release session's work, not
        the checker's. Reporting the two numbers — the one the sentence
        says and the one the line holds — is what makes the refresh
        possible.
        """
        return tuple(f for f in self.findings if f.kind == "value drifted")


@functools.cache
def _files_by_name() -> dict[str, list[pathlib.Path]]:
    """Every file in the repository, indexed by its bare name.

    The index is built once and kept: a citation is looked up by name, and
    looking one up by walking the tree again is what made this checker take
    minutes over ninety citations. The directories the checker never reads
    are not walked into at all, which is the other half of the time.

    The names are folded to lower case, because the tree it used to walk was
    matched that way on Windows and on macOS: a citation that says
    ``models.py`` finds ``Models.py`` there, and it should find it here too.
    """
    index: dict[str, list[pathlib.Path]] = {}
    for root, directories, files in os.walk(REPO):
        directories[:] = [name for name in directories if name not in SKIP_DIRECTORIES]
        for name in files:
            path = pathlib.Path(root) / name
            index.setdefault(name.lower(), []).append(path)
    return index


def _exists_by_path(root: pathlib.Path, rel: str) -> pathlib.Path | None:
    """The file a relative path names, matched component by component.

    The file system on Windows answers ``is_file()`` for any spelling of a
    name, so a citation that said ``SRC/CORE/MODELS.PY`` found
    ``src/core/models.py`` and passed on Windows, while a Linux checker
    reported it. The names are matched against each directory's real
    entries, which is what a file system does on a case-sensitive platform,
    so a wrong-case citation fails the same way everywhere.
    """
    current = root
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return None
        if part not in names:
            return None
        current = current / part
    return current if current.is_file() else None


def candidates(rel: str) -> list[pathlib.Path]:
    """Every file in the repository a citation could mean.

    The documents sometimes abbreviate a path to a bare file name. Those are
    found by name, and only when the name is unambiguous — a citation that
    could mean two files is a finding, not a guess.

    A path with directories in it is matched component by component, not by
    asking a file system whose case rules differ per platform: a citation
    whose path is spelled wrong has to fail the same way everywhere. Only a
    bare file name falls back to the folded index, which is the one place a
    case-insensitive match is the point.
    """
    for root in (
        REPO,
        REPO / "src" / "dexatlas",
        REPO / "scripts",
        REPO / "tests",
        REPO / "examples",
    ):
        found = _exists_by_path(root, rel)
        if found is not None:
            return [found]
    name = rel.rsplit("/", 1)[-1]
    if name != rel:
        # A path that went unresolved is a miss, not a bare name: falling
        # back to the folded index would find whatever file happens to have
        # that name, and the citation's directories were part of what it
        # claimed.
        return []
    return list(_files_by_name().get(name.lower(), []))


@functools.cache
def file_lines(path: pathlib.Path) -> tuple[str, ...]:
    """The lines of a file, read once."""
    return tuple(path.read_text(encoding="utf-8", errors="replace").splitlines())


def symbol_lines(lines: tuple[str, ...], symbol: str) -> list[int]:
    """The lines of a file that name a symbol.

    The symbol is matched as a whole word, so ``kind`` does not match
    ``kinds``.
    """
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    return [number for number, line in enumerate(lines, 1) if pattern.search(line)]


def use_utf8_output() -> None:
    """Make the output independent of the console's encoding.

    A drifted citation is reported with the line it drifted in, and that line
    may hold a character the console cannot encode — the execution report
    marks its findings with 🔴. A console that cannot write it (GBK, cp1252)
    would kill the script halfway through its report, and the exit code it
    managed to give would be the one a crash gives. The report has to finish
    on every machine, so the output is UTF-8 and a character that cannot be
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


def fenced_regions(text: str) -> list[tuple[int, int]]:
    """The fenced code blocks of a text.

    A fenced block is sample output, not prose. Its brackets are unbalanced
    often enough — a table of Java signatures, a JSON dump — that reading them
    as the depth of the surrounding sentence would swallow the rest of the
    document.
    """
    regions: list[tuple[int, int]] = []
    offset = 0
    opening: int | None = None
    for line in text.split("\n"):
        start = offset
        offset += len(line) + 1
        if not line.lstrip().startswith("```"):
            continue
        if opening is None:
            opening = start
        else:
            regions.append((opening, offset))
            opening = None
    return regions


def bracket_ranges(text: str) -> list[tuple[int, int]]:
    """The bracket pairs of a text, as (start, end) offsets."""
    spans = [match.span() for match in SPAN.finditer(text)]
    stack: list[int] = []
    found: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        if spans and index == spans[0][0]:
            index = spans[0][1]
            spans.pop(0)
            continue
        char = text[index]
        if char in OPEN_BRACKETS:
            stack.append(index)
        elif char in CLOSE_BRACKETS and stack:
            found.append((stack.pop(), index + 1))
        index += 1
    return found


def clauses(text: str) -> list[tuple[int, int]]:
    """The clauses of a text: the pieces of a sentence that can hold one claim.

    A clause ends at a full stop, a semicolon, a colon, a dash, an arrow, or
    a comma that is not inside brackets. Text in backticks is never a
    boundary — a citation ``core/pipeline.py:296`` contains both a colon and
    a dot.
    """
    spans = [match.span() for match in SPAN.finditer(text)]
    spans.extend(fenced_regions(text))
    spans.sort()
    boundaries: list[int] = []
    depth = 0
    index = 0
    while index < len(text):
        if spans and index == spans[0][0]:
            index = spans[0][1]
            spans.pop(0)
            continue
        char = text[index]
        if char in OPEN_BRACKETS:
            depth += 1
        elif char in CLOSE_BRACKETS:
            depth = max(0, depth - 1)
        elif char in SENTENCE_ENDS:
            # A full stop ends the sentence whatever brackets are open: an
            # unbalanced bracket must not swallow the rest of the document.
            depth = 0
            boundaries.append(index + 1)
        elif depth == 0 and ends_clause(text, index):
            boundaries.append(index + 1)
        index += 1

    # A table row is a row of its own: the cells around it have nothing to do
    # with the symbols the row names.
    boundaries.extend(table_row_ends(text))

    pieces: list[tuple[int, int]] = []
    start = 0
    for end in sorted(set(boundaries)):
        if end <= start:
            continue
        pieces.append((start, end))
        start = end
    if start < len(text):
        pieces.append((start, len(text)))
    return pieces


def ends_clause(text: str, index: int) -> bool:
    """Whether the character at an index ends a clause.

    A comma between two digits is a thousands separator, not a boundary:
    ``200,000`` is one number.
    """
    char = text[index]
    if char == ",":
        before = text[index - 1] if index else ""
        after = text[index + 1] if index + 1 < len(text) else ""
        return not (before.isdigit() and after.isdigit())
    if char == ".":
        return index + 1 == len(text) or text[index + 1].isspace()
    return char in CLAUSE_ENDS


def table_row_ends(text: str) -> list[int]:
    """The offset just past every table row of a text."""
    ends: list[int] = []
    offset = 0
    for line in text.split("\n"):
        offset += len(line) + 1
        if line.lstrip().startswith("|"):
            ends.append(offset)
    return ends


def span_names(text: str) -> list[tuple[str, int, int]]:
    """The symbols a text names, with where in the text it names them.

    A qualified name carries its class, so ``StringConstant`` is not checked
    again when the text also names ``StringConstant.class_name``: the
    qualified name says where the class is, and it is the one that was cited.
    """
    found: list[tuple[str, int, int]] = []
    for match in SPAN.finditer(text):
        inner = match.group(1)
        if DECLARATION.match(inner):
            # A declaration is a claim of its own, not a name the prose
            # mentions: it is checked against the source, not inferred from
            # the sentence around it.
            continue
        name = NAME.match(inner)
        if name is None:
            continue
        symbol = name.group(1)
        if symbol in NOT_SYMBOLS:
            continue
        found.append((symbol, match.start(), match.end()))
    return [
        entry for entry in found if not any(other[0].startswith(entry[0] + ".") for other in found)
    ]


def is_symbolic(name: str) -> bool:
    """Whether a name looks like a symbol rather than a word or a value.

    ``ApkMetadata`` and ``add_exported_components`` are symbols. ``jadx`` and
    ``apktool`` are the names of tools — words the sentence uses, not code
    the citation points at.
    """
    return any(character.isupper() for character in name) or "_" in name


def definition_line(lines: tuple[str, ...], symbol: str, is_python: bool) -> int | None:
    """The line where a class or a function is defined."""
    if is_python:
        try:
            tree = ast.parse("\n".join(lines))
        except SyntaxError:
            tree = None
        if tree is not None:
            definitions = [
                node.lineno
                for node in ast.walk(tree)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == symbol
            ]
            if definitions:
                return min(definitions)
    for number, line in enumerate(lines, 1):
        if re.match(rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(symbol)}\b", line):
            return number
    return None


def definition_span(lines: tuple[str, ...], symbol: str, is_python: bool) -> tuple[int, int] | None:
    """The lines of a function's definition and of the body it opens.

    A citation that names a function may point at the function's definition
    or at code inside it — "the counting at ``storage.py:520-526``" is
    inside ``save_symbols`` even though the ``def`` is a hundred lines up.
    """
    if is_python:
        try:
            tree = ast.parse("\n".join(lines))
        except SyntaxError:
            tree = None
        if tree is not None:
            spans = [
                (node.lineno, node.end_lineno or node.lineno)
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
            ]
            if spans:
                return min(spans)
    pattern = re.compile(rf"^\s*(?:async\s+)?def\s+{re.escape(symbol)}\b")
    for number, line in enumerate(lines, 1):
        if not pattern.match(line):
            continue
        indent = len(line) - len(line.lstrip())
        end = len(lines)
        for later, text in enumerate(lines[number:], number + 1):
            if not text.strip():
                continue
            if len(text) - len(text.lstrip()) <= indent:
                end = later - 1
                break
        return number, end
    return None


def symbol_is_in_range(
    lines: tuple[str, ...], name: str, start: int, end: int, is_python: bool
) -> bool | None:
    """Whether a symbol is inside a cited range.

    A symbol the file defines has to be defined in the range, or the range has
    to be inside the body it opens. A symbol the file only mentions has to be
    mentioned in the range.

    None means the file does not name the symbol at all, so there is nothing
    to compare against.
    """
    defined = definition_line(lines, name, is_python)
    if defined is not None:
        if start - SLACK <= defined <= end + SLACK:
            return True
        body = definition_span(lines, name, is_python)
        return bool(body is not None and body[0] - SLACK <= start and end <= body[1] + SLACK)
    where = symbol_lines(lines, name)
    if not where:
        return None
    return any(start - SLACK <= line <= end + SLACK for line in where)


def block_ends(text: str) -> list[int]:
    """The offsets at which a block of a text ends.

    A table row is a block of its own, and so is a paragraph. A bare
    ``:143`` names a line of the file the *same block* named before it: a
    number that referred to a file named in the previous row would be a
    number nobody could check.
    """
    ends = set(table_row_ends(text))
    for match in re.finditer(r"\n[ \t]*\n", text):
        ends.add(match.end())
    return sorted(ends)


def joins_range(previous: re.Match[str], match: re.Match[str]) -> bool:
    """Whether two spans are joined by a dash into one range.

    ``file:37`` joined to ``:44`` by a dash is one range of lines;
    ``file:37``, ``:44`` is two citations of the same file. The difference is
    the dash, and nothing else may sit between the two spans.
    """
    between = previous.string[previous.end() : match.start()].strip()
    return bool(between) and set(between) <= set(DASHES)


def resolve_citations(text: str) -> list[Resolved]:
    """Every citation of a text, with the file and the range each one names."""
    return _resolve(text)[0]


def _resolve(text: str) -> tuple[list[Resolved], list[Declaration]]:
    """Every citation of a text, and the declarations that name no citation.

    Two forms are read. A full citation names its file: ``core/pipeline.py:296``.
    A bare one names only a line: ``:143``. The bare form is the same file as
    the citation before it — that is how the release appendix cites one file
    in several places — and it is the same file only as long as both sit in
    the same block of the text.

    A declaration — ``anchor: def version(`` — is bound to the citation
    before it, the way a bare line number is, and only as long as no block
    boundary lies between them. A declaration that names no citation is
    returned as an orphan: it says something about nothing, and a reader who
    believes it is checking the code is not.
    """
    ends = block_ends(text)
    resolved: list[Resolved] = []
    orphans: list[Declaration] = []
    previous: Resolved | None = None
    for match in SPAN.finditer(text):
        inner = match.group(1)
        citation = CITATION.match(inner)
        if citation is not None:
            start = int(citation.group(2))
            previous = Resolved(match, citation.group(1), start, int(citation.group(3) or start))
            resolved.append(previous)
            continue
        declaration = DECLARATION.match(inner)
        if declaration is not None:
            line = text[: match.start()].count("\n") + 1
            if previous is None:
                orphans.append(Declaration(line, declaration.group(1)))
                continue
            if any(previous.match.start() < end <= match.start() for end in ends):
                # A block boundary lies between them: the declaration would
                # belong to a citation in another block, and reading it as
                # this one's would check the wrong lines.
                orphans.append(Declaration(line, declaration.group(1)))
                continue
            previous = replace(previous, anchors=(*previous.anchors, declaration.group(1)))
            resolved[-1] = previous
            continue
        bare = BARE_LINE.match(inner)
        if bare is None or previous is None:
            continue
        if any(previous.match.start() < end <= match.start() for end in ends):
            # A block boundary lies between them: the bare line number has no
            # file of its own, and guessing one would check the wrong file.
            continue
        start = int(bare.group(1))
        end = int(bare.group(2) or start)
        if joins_range(previous.match, match):
            previous = replace(previous, end=end)
            resolved[-1] = previous
            continue
        previous = Resolved(match, previous.rel, start, end)
        resolved.append(previous)
    return resolved, orphans


def document_clauses(document: pathlib.Path, tree: Tree = WORKING_COPY) -> list[Clause]:
    """Every clause of a document, with its citations and the symbols it names."""
    text = document.read_text(encoding="utf-8")
    resolved = resolve_citations(text)
    ignored = ignored_regions(text, resolved)
    clause_ranges = list(clauses(text))
    owned = stated_values_by_citation(text, resolved, ignored, clause_ranges, tree)
    found: list[Clause] = []
    for start, end in clause_ranges:
        clause = text[start:end]
        names = span_names(clause)
        brackets = bracket_ranges(clause)
        inside_ = [item for item in resolved if start <= item.match.start() < end]
        if not inside_:
            continue
        citations: list[Citation] = []
        citation_spans: list[tuple[int, int]] = []
        for item in inside_:
            options = candidates(item.rel)
            citations.append(
                Citation(
                    document=document,
                    line=text[: item.match.start()].count("\n") + 1,
                    rel=item.rel,
                    start=item.start,
                    end=item.end,
                    target=options[0] if len(options) == 1 else None,
                    ambiguous=len(options) > 1,
                    text=clause.strip()[:100],
                    tree=tree,
                    anchors=item.anchors,
                )
            )
            citation_spans.append((item.match.start() - start, item.match.end() - start))
        claims = [claimed_names(brackets, span, names, citation_spans) for span in citation_spans]
        found.append(
            Clause(
                document=document,
                line=text[:start].count("\n") + 1,
                citations=tuple(citations),
                claims=tuple(claims),
                values=tuple(owned.get(item.match.start(), ()) for item in inside_),
            )
        )
    return found


def ignored_regions(text: str, resolved: list[Resolved]) -> list[tuple[int, int]]:
    """The parts of a document whose numbers are not claims.

    A citation names a line, not a value. A fenced block is sample output.
    A heading names a section, and the number in it is the section's number.
    """
    regions = [(item.match.start(), item.match.end()) for item in resolved]
    regions.extend(fenced_regions(text))
    regions.extend(match.span() for match in re.finditer(r"(?m)^#{1,6}[ \t].*$", text))
    return regions


def unit_of(text: str, start: int, clause_ranges: list[tuple[int, int]]) -> tuple[int, int]:
    """The extent of the unit a citation sits in.

    A citation in a table row belongs to the whole row: a row is one
    statement, and a comma in one cell does not end it. A citation in a
    sentence belongs to its clause.
    """
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    if text[line_start:line_end].lstrip().startswith("|"):
        return line_start, line_end
    for clause_start, clause_end in clause_ranges:
        if clause_start <= start < clause_end:
            return clause_start, clause_end
    return start, start


def stated_values_by_citation(
    text: str,
    resolved: list[Resolved],
    ignored: list[tuple[int, int]],
    clause_ranges: list[tuple[int, int]],
    tree: Tree = WORKING_COPY,
) -> dict[int, tuple[StatedValue, ...]]:
    """The values every citation owns.

    A table row is read cell by cell. The number a row states in one cell
    is the claim of the citation in the cell beside it — a provenance
    table says "this number came from there". A number in the *same* cell
    as a citation is that citation's own claim. A number in a cell that
    has no citation beside it belongs to no citation at all.

    A sentence that is not a table row is read by proximity: the number
    is the claim of the citation it was written next to.
    """
    grouped: dict[tuple[int, int], list[Resolved]] = {}
    for item in resolved:
        grouped.setdefault(unit_of(text, item.match.start(), clause_ranges), []).append(item)
    owned: dict[int, tuple[StatedValue, ...]] = {}
    for (unit_start, unit_end), items in grouped.items():
        unit = text[unit_start:unit_end]
        if names_another_tree(unit, tree.ref):
            # The unit quotes another tree: its numbers are not a claim
            # about the tree this document is read against.
            continue
        blanked = list(unit)
        for region_start, region_end in ignored:
            for index in range(
                max(0, region_start - unit_start), min(len(blanked), region_end - unit_start)
            ):
                blanked[index] = " "
        # The measurement's markers are markup: a number between two of them
        # is still the number that goes with the word next to it. They are
        # replaced by spaces, so that every offset in the text stays where it
        # was.
        for match in FIGURES.finditer(unit):
            for index in range(match.start(), match.end()):
                blanked[index] = " "
        stated = stated_values("".join(blanked))
        if not stated:
            continue
        spans = [(item.match.start() - unit_start, item.match.end() - unit_start) for item in items]
        cells = table_cells(unit) if unit.lstrip().startswith("|") else []
        for index, item in enumerate(items):
            values = values_for_citation(stated, cells, spans, index)
            if values:
                owned[item.match.start()] = tuple(values)
    return owned


def table_cells(row: str) -> list[tuple[int, int]]:
    """The cells of a table row, with where each of them starts and ends.

    A ``|`` inside a backticked span does not separate two cells: the
    release appendix writes a whole table row inside a quotation.
    """
    spans = [match.span() for match in SPAN.finditer(row)]
    cells: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(row):
        if spans and index == spans[0][0]:
            index = spans[0][1]
            spans.pop(0)
            continue
        if row[index] == "|":
            cells.append((start, index))
            start = index + 1
        index += 1
    cells.append((start, len(row)))
    return cells


def values_for_citation(
    stated: list[tuple[int, StatedValue]],
    cells: list[tuple[int, int]],
    citation_spans: list[tuple[int, int]],
    index: int,
) -> list[StatedValue]:
    """The values that belong to one citation."""
    start = citation_spans[index][0]
    if not cells:
        best: list[StatedValue] = []
        for position, value in stated:
            distances = [
                min(abs(position - other_start), abs(position - other_end))
                for other_start, other_end in citation_spans
            ]
            if distances[index] == min(distances):
                best.append(value)
        return best
    cell = next(
        (
            number
            for number, (cell_start, cell_end) in enumerate(cells)
            if cell_start <= start < cell_end
        ),
        None,
    )
    if cell is None:
        return []
    here = [value for position, value in stated if cells[cell][0] <= position < cells[cell][1]]
    if here:
        return here
    if cell == 0:
        return []
    # The cell beside it is the claim; only the first citation of the cell
    # is the source the claim is about.
    left = cells[cell - 1]
    if any(
        other < index and cells[cell][0] <= citation_spans[other][0] < cells[cell][1]
        for other in range(len(citation_spans))
    ):
        return []
    return [value for position, value in stated if left[0] <= position < left[1]]


def claimed_names(
    brackets: list[tuple[int, int]],
    citation: tuple[int, int],
    names: list[tuple[str, int, int]],
    citation_spans: list[tuple[int, int]],
) -> tuple[str, ...]:
    """The symbols a citation claims to locate.

    A citation inside brackets is about what those brackets hold — "the
    ``normalize_locator()`` at ``core/models.py:68-86``" — or about the
    symbol that sits right in front of them — "``_DECOMPILE_FAILED_RE``
    (``tools/jadx/adapter.py:42-47``)". The symbols further away are the
    subject of the sentence, not what the lines point at.
    """
    inside = [
        (start, end) for start, end in brackets if start <= citation[0] and citation[1] <= end
    ]
    if not inside:
        return tuple(symbol for symbol, _, _ in names)
    narrowest = min(inside, key=lambda pair: pair[1] - pair[0])
    pool = [entry for entry in names if narrowest[0] <= entry[1] and entry[2] <= narrowest[1]]
    if pool:
        return tuple(symbol for symbol, _, _ in pool)
    # Nothing inside the brackets: the symbol in front of them may be the
    # one they are about.
    before = [entry for entry in names if entry[2] <= narrowest[0]]
    if before:
        nearest = before[-1]
        if not any(nearest[2] <= span[0] < narrowest[0] for span in citation_spans):
            return (nearest[0],)
    return tuple(symbol for symbol, _, _ in names)


def holds_content(line: str) -> bool:
    """Whether a line holds something a citation can point at.

    A blank line holds nothing. A comment holds a sentence, and a citation
    can be about what a comment says: the release appendix points at the
    header of ``scripts/fetch-fixtures.sh`` for the claim that the script
    fetches two fixtures, and that line is a comment.
    """
    return bool(line.strip())


#: A number: ``1694``, ``1,182,356``, ``93.3``.
#:
#: The thousands separator has to be followed by three digits, or the
#: separator is a comma between two numbers and belongs to neither.
NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"

#: A percentage: ``93.3%``.
PERCENT = re.compile(rf"(?<![\w.])({NUMBER})\s*%")

#: A count and the word it counts: ``1694 passed``, ``7136 / 7650 lines``.
#:
#: The word is what makes the number a *value* rather than a label: a table
#: that says ``| 1 |`` counts its rows, it does not state a measurement, and
#: a contract table that says ``200 / 404`` states status codes, not a number
#: that a line of the source is supposed to carry. A number without a word
#: behind it is therefore not compared.
COUNT = re.compile(rf"(?<![\w.-])({NUMBER})((?:\s*/\s*{NUMBER})*)\s+([A-Za-z][A-Za-z0-9_-]+)")

#: A number word and the word it counts: ``Two third-party integration fixtures``.
WORD_COUNT = re.compile(
    r"(?<![\w])(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    r"\s+([A-Za-z][A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

#: A fingerprint: ``sha256:18f3ab15…``.
#:
#: Eight hex characters at least, and at least one of them a digit: a word
#: made of the letters ``a``-``f`` is not a digest.
DIGEST = re.compile(r"(?<![\w.])((?:sha256:)?[0-9a-f]{8,})(?![\w.])", re.IGNORECASE)

#: A quotation: ``「two live runs」``, ``"ten jobs"``.
#:
#: A number inside one is what somebody else said. A document that quotes
#: the number it is talking about is not making a claim about its own
#: citation.
QUOTED = re.compile(r"「[^」]*」|\"[^\"\n]*\"|'[^'\n]*'")

#: The number words, and the number each of them states.
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

#: How many values a claim may state and still be a claim about a number.
#:
#: A provenance row states what a line holds: "1694 passed + 0 xfailed +
#: 1 skipped". A sentence that states five numbers is telling a story, and
#: the checker cannot know which of them the cited line is about. Such a
#: claim is not compared — a false report is worse than a missed one.
MAX_CLAIMED_VALUES = 4

#: A tree a clause names: a tag like ``v1.0.0`` or a commit like ``75976e0``.
#:
#: A fingerprint is not a tree, and a run of seven digits is a number.
NAMED_TREE = re.compile(r"(?<![\w.-])(?<!sha256:)(v\d+\.\d+\.\d+|[0-9a-f]{7,40})(?![\w.])")

#: The Chinese measure words a count is written with: ``两个``, ``三次``, ``五行``.
#:
#: A numeral that is not followed by one of these is not a count: ``一方``
#: in "first-party code" is not the number one.
CHINESE_MEASURES = "个次条行项份张轮天秒篇台块组批件套名位只本页章节回遍趟种款"

#: The Chinese numerals a count may be written in, and the number each of
#: them states. The documents are bilingual: a Chinese report states a count
#: as ``两个`` and an English release body states the same count as ``Two``.
CHINESE_NUMERALS = {
    "零": 0,
    "一": 1,
    "两": 2,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

#: The words that may sit between a number and the word it counts.
#:
#: They are not units: "400,000 and the amended limit" states a number and
#: then continues the sentence, and reading "and" as the word the number
#: counts would compare a limit against a conjunction.
NOT_UNITS = {
    "all",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "between",
    "but",
    "by",
    "each",
    "every",
    "for",
    "from",
    "had",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "least",
    "less",
    "more",
    "most",
    "no",
    "not",
    "of",
    "on",
    "or",
    "other",
    "our",
    "out",
    "over",
    "own",
    "per",
    "same",
    "since",
    "so",
    "such",
    "than",
    "that",
    "the",
    "their",
    "then",
    "this",
    "to",
    "too",
    "under",
    "until",
    "via",
    "very",
    "was",
    "were",
    "when",
    "while",
    "which",
    "who",
    "with",
    "within",
    "without",
}

#: The characters that say a number is a limit rather than a measurement:
#: ``≥16/20`` is the acceptance bar, not the number the run produced.
COMPARISON = "≥≤><≤≥"

#: The characters that say a number belongs to something else: ``§3`` is a
#: section, ``= 75%`` is the number the sentence itself worked out.
BELONGS_TO = "§=第"

#: The characters that may sit between a number and the word it counts.
THOUSANDS = re.compile(r"(?<=\d),(?=\d)")


#: The markers the measurement script writes a number between.
#:
#: The execution report holds its numbers between them: ``1710`` is written
#: ``<!--fig:suite.passed-->1710<!--/fig-->``. The markers are markup, not
#: content, and a number that sits between two of them is still the number
#: that sits next to the word it counts.
FIGURES = re.compile(r"<!--/?fig(?::[^>]*)?-->")


def strip_figures(text: str) -> str:
    """The text with the measurement's figure markers taken out."""
    return FIGURES.sub(" ", text)


@dataclass(frozen=True)
class StatedValue:
    """One value the sentence around a citation states."""

    #: The value as the sentence writes it: ``1694``, ``93.3%``, ``Two``.
    text: str
    #: The value as a number: ``1694``, ``93.3``, ``2``.
    number: str
    #: The word the number is measured in: ``passed``, ``tests``, ``lines``.
    unit: str
    #: Whether the value is a fingerprint rather than a count.
    digest: bool = False

    @property
    def kind(self) -> str:
        """What kind of claim the value makes."""
        if self.digest:
            return "digest"
        if self.unit == "%":
            return "percent"
        return "count"


def is_limit(text: str, position: int) -> bool:
    """Whether the number at a position is a limit rather than a measurement.

    ``≥16/20`` is the bar a run has to clear; it is not a number any line
    is supposed to carry. A limit is the one number in a sentence that is
    true whatever the run produced.
    """
    before = text[:position].rstrip()
    return bool(before) and before[-1] in COMPARISON


def belongs_to_something_else(text: str, position: int) -> bool:
    """Whether the number at a position belongs to something else.

    ``§3`` names a section, ``第 3 节`` names a section in Chinese, and
    ``= 75%`` is the number the sentence itself worked out. None of them
    is a number that a cited line has to carry.
    """
    before = text[:position].rstrip()
    if not before:
        return False
    return before[-1] in BELONGS_TO


def quoted_spans(text: str) -> list[tuple[int, int]]:
    """The backticked spans of a text."""
    return [match.span() for match in SPAN.finditer(text)]


def inside(span: int, spans: list[tuple[int, int]]) -> bool:
    """Whether an offset lies inside one of the spans."""
    return any(start <= span < end for start, end in spans)


def stated_values(text: str) -> list[tuple[int, StatedValue]]:
    """The values a text states, with where in the text it states them.

    Only values that a line of the source could carry are returned: a
    percentage, a count with the word it counts, and a fingerprint. A bare
    number is not one — a table row numbered ``1`` and a status code
    ``404`` are labels, and comparing them would report drift where
    there is none.

    A number inside a backticked span is a quotation or a piece of code,
    not a claim: a document that quotes what another document says is not
    making a claim about its own citation. A fingerprint is the one
    exception — it is a value in its own right, not a quotation.
    """
    found: list[tuple[int, StatedValue]] = []
    quoted = quoted_spans(text)
    quotations = [match.span() for match in QUOTED.finditer(text)]
    for match in PERCENT.finditer(text):
        if is_limit(text, match.start()) or belongs_to_something_else(text, match.start()):
            continue
        if inside(match.start(), quoted) or inside(match.start(), quotations):
            continue
        found.append((match.start(), StatedValue(match.group(0).strip(), match.group(1), "%")))
    for match in COUNT.finditer(text):
        if is_limit(text, match.start()) or belongs_to_something_else(text, match.start()):
            continue
        if inside(match.start(), quoted) or inside(match.start(), quotations):
            continue
        unit = match.group(3)
        if len(unit) < 2 or unit.lower() in NOT_UNITS:
            # ``120 s`` is a duration and ``120 files`` is a count, but a
            # single letter is as likely to be a stray initial as a unit.
            continue
        numbers = re.findall(NUMBER, match.group(1) + match.group(2))
        offset = match.start(1)
        for number in numbers:
            found.append(
                (
                    offset,
                    StatedValue(f"{number} {unit}", THOUSANDS.sub("", number), unit),
                )
            )
            offset += len(number)
    for match in WORD_COUNT.finditer(text):
        if is_limit(text, match.start()) or belongs_to_something_else(text, match.start()):
            continue
        if inside(match.start(), quoted) or inside(match.start(), quotations):
            continue
        unit = match.group(2)
        if len(unit) < 2 or unit.lower() in NOT_UNITS:
            continue
        number = NUMBER_WORDS[match.group(1).lower()]
        found.append((match.start(), StatedValue(match.group(0), str(number), unit)))
    for match in DIGEST.finditer(text):
        digest = match.group(1)
        if not any(character.isdigit() for character in digest):
            continue
        found.append((match.start(), StatedValue(digest, digest, "", True)))
    return found


def bare_numbers(text: str) -> list[str]:
    """The numbers a text carries, with the thousands separators removed."""
    return re.findall(NUMBER, THOUSANDS.sub("", text))


def number_word(number: str) -> str | None:
    """The English word a number is written as, if there is one."""
    for word, value in NUMBER_WORDS.items():
        if str(value) == number:
            return word
    return None


def range_kinds(text: str) -> set[str]:
    """The kinds of value a range of lines carries.

    A count, a percentage and a fingerprint are three different claims,
    and a line that states none of them cannot contradict one.
    """
    kinds: set[str] = set()
    if bare_numbers(text):
        kinds.add("count")
    if PERCENT.search(text):
        kinds.add("percent")
    for match in DIGEST.finditer(text):
        if any(character.isdigit() for character in match.group(1)):
            kinds.add("digest")
            break
    return kinds


def anchored_number(text: str, unit: str) -> str | None:
    """The number a text states for a word.

    The word may sit before the number (``"failed": 1``) or after it
    (``1694 passed``), and the two orders are both common in the documents
    that carry these numbers.
    """
    text = strip_figures(text)
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(unit)}(?![A-Za-z0-9_])")
    for match in pattern.finditer(text):
        after = re.match(rf"[\"'`\]\*]*\s*[:=]?\s*({NUMBER})", text[match.end() :])
        if after:
            return THOUSANDS.sub("", after.group(1))
        before = re.search(rf"({NUMBER})\s*[:=]?\s*[\"'`\]\*]*\s*$", text[: match.start()])
        if before:
            return THOUSANDS.sub("", before.group(1))
    return None


def value_present(value: StatedValue, target: str) -> bool:
    """Whether a line of the source carries the value a sentence states.

    The word the number is measured in decides it. A line that carries the
    word and a *different* number is not the line the sentence means: that
    is the drift this check exists for. A line that does not carry the word
    at all is compared by the number alone, because the word may be written
    in the other language.
    """
    target = strip_figures(target)
    if value.digest:
        return value.number.lower() in target.lower()
    if value.unit and value.unit != "%":
        stated = anchored_number(target, value.unit)
        if stated is not None:
            return stated == value.number
    numbers = bare_numbers(target)
    if value.number in numbers:
        return True
    if chinese_number_present(value.number, target):
        return True
    word = number_word(value.number)
    if word is None:
        return False
    return bool(re.search(rf"(?<![A-Za-z0-9_]){word}(?![A-Za-z0-9_])", target, re.IGNORECASE))


def chinese_number_present(number: str, target: str) -> bool:
    """Whether a Chinese numeral states the number a sentence states.

    The numeral has to be a count: it has to be followed by the measure
    word Chinese counts are written with. ``两个`` is two, ``一方`` in
    "first-party code" is not a number at all.
    """
    if not number.isdigit():
        return False
    for character, value in CHINESE_NUMERALS.items():
        if str(value) != number:
            continue
        if re.search(rf"(?<![0-9.]){character}[{CHINESE_MEASURES}]", target):
            return True
    return False


def value_lines(lines: tuple[str, ...], value: StatedValue) -> list[int]:
    """The lines of a file that carry a value."""
    found = []
    for number, line in enumerate(lines, 1):
        if value_present(value, line):
            found.append(number)
    return found


def carries_the_way(value: StatedValue, line: str) -> bool:
    """Whether a line carries a value the way the sentence writes it.

    A line that carries the word the number goes with is the line the
    sentence means: "1710 passed" is the suite result. A line that carries
    only the digits is not — a number that appears in five places points at
    none of them.
    """
    if value.digest:
        return value.number.lower() in line.lower()
    if value.unit and value.unit != "%":
        stated = anchored_number(line, value.unit)
        if stated is not None:
            return stated == value.number
    return False


def carries_the_count(value: StatedValue, line: str) -> bool:
    """Whether a line writes a count as a count rather than as digits.

    Chinese writes a count with a measure word -- ``9 个文件`` -- and so
    does the number in a sentence that counts things: "Two third-party
    integration fixtures" is two, and the line that says ``两个`` says it
    too. A line that carries the digits alone does not: a number that
    appears in five places points at none of them.
    """
    if value.digest:
        return False
    if chinese_number_present(value.number, line):
        return True
    word = number_word(value.number)
    if word is not None and re.search(
        rf"(?<![A-Za-z0-9_]){word}(?![A-Za-z0-9_])", line, re.IGNORECASE
    ):
        return True
    return bool(re.search(rf"(?<![0-9.]){re.escape(value.number)}\s*[{CHINESE_MEASURES}]", line))


def nearest_value_line(lines: tuple[str, ...], value: StatedValue, cited: int) -> int | None:
    """The line of a file that carries a value, the closest one to a citation.

    The check on a symbol reports the line it is at, so that the fix is a
    line number. The line has to carry the value the way the sentence
    writes it: a line that carries only the digits does not say which of
    them the sentence means.
    """
    for carries in (carries_the_way, carries_the_count):
        found = [number for number, line in enumerate(lines, 1) if carries(value, line)]
        if found:
            return min(found, key=lambda line: abs(line - cited))
    return None


def check_citation(citation: Citation) -> list[Finding]:
    """The findings of one citation's location.

    The lines are read out of the tree the document describes. For most
    documents that tree is the working copy; for the ones that say they are
    about a release, it is that release's tree, and a line number that only
    means something in the working copy is not a line of that release.
    """
    if citation.target is None:
        kind = "ambiguous" if citation.ambiguous else "unresolved"
        detail = "the name could mean several files" if citation.ambiguous else "no such file"
        return [Finding(citation.where, kind, detail, citation.text)]

    lines = citation.lines()
    if lines is None:
        return [
            Finding(
                citation.where,
                "not in the tree",
                f"{citation.tree.label} has no such file",
                citation.text,
            )
        ]
    if citation.start < 1 or citation.end < citation.start or citation.end > len(lines):
        return [
            Finding(
                citation.where,
                "out of range",
                f"the file has {len(lines)} lines in {citation.tree.label}",
                citation.text,
            )
        ]
    if not any(holds_content(line) for line in lines[citation.start - 1 : citation.end]):
        return [
            Finding(citation.where, "points at nothing", "the range holds nothing", citation.text)
        ]
    return []


def check_anchor(citation: Citation) -> list[Finding]:
    """Whether the cited range still holds what the citation declares.

    A declaration is a claim about the content of the range, and it is
    checked against the source rather than against the sentence around it.
    An anchor that is a bare name is checked the way a named symbol is
    checked; any other anchor is a fragment of the source and has to be in
    the range verbatim.

    The finding says what the declaration claims and where the claim holds,
    so that a reader can see the drift without reading the file.
    """
    if not citation.anchors:
        return []
    lines = citation.lines()
    if lines is None:
        # The location check has already reported that the file is not there.
        return []
    findings: list[Finding] = []
    for anchor in citation.anchors:
        if ANCHOR_NAME.match(anchor):
            findings.extend(check_anchor_name(citation, lines, anchor))
        else:
            findings.extend(check_anchor_fragment(citation, lines, anchor))
    return findings


def check_anchor_name(citation: Citation, lines: tuple[str, ...], anchor: str) -> list[Finding]:
    """Whether a bare-name anchor is inside the cited range.

    A name is checked the way a named symbol is checked: the file has to
    define it in the range, or the range has to be inside the body it
    opens. A name the file does not mention at all cannot be in the range
    either.
    """
    is_python = citation.target is not None and citation.target.suffix == ".py"
    verdict = symbol_is_in_range(lines, anchor, citation.start, citation.end, is_python)
    if verdict is True:
        return []
    if verdict is None:
        return [
            Finding(
                citation.where,
                "anchor missing",
                f"the anchor `{anchor}` is not in the file at all",
                citation.text,
            )
        ]
    defined = definition_line(lines, anchor, is_python)
    if defined is not None:
        detail = f"the anchor `{anchor}` is at line {defined}"
    else:
        where = symbol_lines(lines, anchor)
        detail = f"the anchor `{anchor}` is not in the range"
        if where:
            detail = f"the anchor `{anchor}` is at line {min(where)}"
    return [Finding(citation.where, "anchor missing", detail, citation.text)]


def check_anchor_fragment(citation: Citation, lines: tuple[str, ...], anchor: str) -> list[Finding]:
    """Whether a fragment of the source is inside the cited range.

    Whitespace is normalised on both sides: the anchor quotes a piece of
    code, and re-indenting the code does not change what it says.
    """
    quoted = " ".join(anchor.split())
    where = [number for number, line in enumerate(lines, 1) if quoted in " ".join(line.split())]
    if any(citation.start <= number <= citation.end for number in where):
        return []
    detail = f"the anchor `{anchor}` is not in the range"
    if where:
        detail = f"the anchor `{anchor}` is at line {min(where)}"
    return [Finding(citation.where, "anchor missing", detail, citation.text)]


def check_declaration_of_content(clause: Clause) -> list[Finding]:
    """Whether a citation that says nothing about its lines says so out loud.

    In a document that declares what its citations point at, a citation
    that names no symbol and carries no declaration is a citation that says
    nothing: the checker can ask whether the range holds something, but not
    whether it holds what the document meant. It is reported, so that the
    silence is a decision and not an oversight.
    """
    if relative_path(clause.document) not in DECLARING_DOCUMENTS:
        return []
    findings: list[Finding] = []
    for citation, names in zip(clause.citations, clause.claims, strict=True):
        if citation.anchors or is_compared(citation, names):
            continue
        findings.append(
            Finding(
                citation.where,
                "declares nothing",
                "the citation names no symbol and declares no anchor",
                citation.text,
            )
        )
    return findings


def document_orphan_declarations(document: pathlib.Path) -> list[Finding]:
    """The declarations of a document that name no citation.

    A declaration says what a range holds. Without a range it says nothing,
    and a reader who takes it for a check is not getting one.
    """
    text = document.read_text(encoding="utf-8")
    orphans = _resolve(text)[1]
    return [
        Finding(
            f"{document.name}:{orphan.line}",
            "orphaned declaration",
            f"the declaration `{orphan.text}` names no citation",
        )
        for orphan in orphans
    ]


def check_values(citation: Citation, values: tuple[StatedValue, ...]) -> list[Finding]:
    """The findings of one citation's values.

    A sentence that states a number and cites the line it was read from
    makes a claim that can be checked exactly: the line has to carry the
    number. When it carries a different one, the citation has drifted, and
    the two numbers are both named so that the fix is obvious.

    Three verdicts, in the order they are decided:

    * the cited line carries the number — the claim holds;
    * the cited line carries the same word and a different number — the
      claim is contradicted, and the two numbers are reported;
    * the cited line carries no number at all — the claim points at a
      line that does not hold it.
    """
    if not values:
        return []
    lines = citation.lines()
    if lines is None:
        return []
    if len(values) > MAX_CLAIMED_VALUES:
        # A claim that states this many numbers is prose.
        return []
    target = "\n".join(lines[citation.start - 1 : citation.end])
    kinds = range_kinds(target)
    present = [value for value in values if value_present(value, target)]
    findings: list[Finding] = []
    for value in values:
        if value in present:
            continue
        stated = anchored_number(target, value.unit) if value.unit not in {"", "%"} else None
        if stated is not None:
            detail = (
                f"the sentence says `{value.text}`, the cited line says `{stated} {value.unit}`"
            )
        elif kinds and value.kind not in kinds:
            # The range states values, but none of this kind: it is not
            # making a different claim about this number.
            continue
        elif present:
            # The range carries other values of this claim: it is the
            # place those came from, and this number is about elsewhere.
            continue
        else:
            detail = f"the sentence says `{value.text}`, the cited line does not carry it"
        elsewhere = nearest_value_line(lines, value, citation.start)
        if elsewhere is not None:
            detail += f"; the file says it at line {elsewhere}"
        findings.append(Finding(citation.where, "value drifted", detail, citation.text))
    return findings


def names_another_tree(text: str, ref: str | None) -> bool:
    """Whether a clause is about a tree other than the one it is read against.

    A review document quotes a release tree and says so; the checker reads
    that document's citations out of the tree the document declares, and a
    number quoted from another tree is not a claim about this one.
    """
    if ref is None:
        return False
    for match in NAMED_TREE.finditer(text):
        named = match.group(1)
        if not any(character.isalpha() for character in named):
            # A run of digits is a number, not a tree.
            continue
        if named == ref or ref.startswith(named) or named.startswith(ref):
            continue
        return True
    return False


def check_clause(clause: Clause) -> list[Finding]:
    """The findings of one clause."""
    findings: list[Finding] = []
    for citation in clause.citations:
        findings.extend(check_citation(citation))
        findings.extend(check_anchor(citation))
    findings.extend(check_declaration_of_content(clause))

    located: set[str] = set()
    missing: dict[str, Citation] = {}
    for citation, names in zip(clause.citations, clause.claims, strict=True):
        if citation.target is None:
            continue
        lines = citation.lines()
        if lines is None:
            continue
        for name in names:
            anchor = name.rsplit(".", 1)[-1]
            if symbol_is_in_range(
                lines, anchor, citation.start, citation.end, citation.target.suffix == ".py"
            ):
                located.add(name)
            else:
                missing.setdefault(name, citation)

    for name, citation in missing.items():
        if name in located:
            continue
        lines = citation.lines()
        if lines is None:
            continue
        anchor = name.rsplit(".", 1)[-1]
        where = symbol_lines(lines, anchor)
        if where:
            nearest = min(where, key=lambda line: abs(line - citation.start))
            findings.append(
                Finding(citation.where, "drifted", f"`{name}` is at line {nearest}", citation.text)
            )
        elif is_symbolic(name):
            findings.append(
                Finding(
                    citation.where,
                    "drifted",
                    f"`{name}` is not in the file at all",
                    citation.text,
                )
            )
    for citation, names, values in zip(clause.citations, clause.claims, clause.values, strict=True):
        if is_compared(citation, names):
            # The citation already has a check of its own: the sentence
            # names a symbol, and the number in it counts what that symbol
            # holds rather than being written on the cited line.
            continue
        if names_another_tree(citation.text, citation.tree.ref):
            continue
        findings.extend(check_values(citation, values))
    return findings


def is_compared(citation: Citation, names: tuple[str, ...]) -> bool:
    """Whether a symbol is compared against the cited lines.

    A name is compared when it looks like a symbol — then its absence from
    the file is a finding — or when the file names it — then the lines have
    to hold it. A word the file does not name is prose, and prose is not
    compared against anything.
    """
    if citation.target is None:
        return False
    lines = citation.lines()
    if lines is None:
        return False
    for name in names:
        anchor = name.rsplit(".", 1)[-1]
        if is_symbolic(name) or symbol_lines(lines, anchor):
            return True
    return False


def relative_path(document: pathlib.Path) -> str:
    """A document's path in the repository, as the repository spells it."""
    try:
        return document.relative_to(REPO).as_posix()
    except ValueError:
        return document.name


def tree_of(document: pathlib.Path) -> Tree:
    """The tree a document describes."""
    ref = TREE_DOCUMENTS.get(relative_path(document))
    return Tree(ref) if ref is not None else WORKING_COPY


def tree_fingerprint(tree: Tree) -> str | None:
    """The source fingerprint of the tree a measurement was taken on.

    The measurement record of a tree holds it, and the record is in the tree,
    so the fingerprint of a tree is read out of that tree.
    """
    text = tree.text(RECORD_DOCUMENT)
    if text is None:
        return None
    match = RECORD.search(text)
    if match is None:
        return None
    try:
        record = json.loads(match.group(1))
    except json.JSONDecodeError:
        # ``json`` has no ``JSONError``: the name this used to catch does not
        # exist, so the except clause itself raised ``AttributeError`` -- and a
        # record that is not valid JSON took the checker down instead of being
        # reported as unreadable.
        return None
    value = record.get("source_fingerprint")
    return value if isinstance(value, str) else None


def check_declaration(document: pathlib.Path, tree: Tree) -> list[Finding]:
    """Whether a document really is about the tree it says it is about.

    Two things have to hold: the tree has to be in this checkout, and the
    document has to quote the fingerprint of that tree's measurement. The
    second one is what ties the two together -- a document that names a tree
    nobody can check against is a document whose line numbers mean nothing.
    """
    where = f"{document.name}  declaration"
    if not tree.exists():
        return [
            Finding(
                where,
                "no such tree",
                f"the {tree.ref} tree is not in this checkout (fetch the tags: git fetch --tags)",
                "",
            )
        ]
    expected = tree_fingerprint(tree)
    if expected is None:
        return [
            Finding(
                where,
                "unverified tree",
                f"the {tree.ref} tree has no measurement record to compare a fingerprint with",
                "",
            )
        ]
    quoted = sorted(set(FINGERPRINT.findall(document.read_text(encoding="utf-8"))))
    if not quoted:
        return [
            Finding(
                where,
                "unverified tree",
                f"the document quotes no fingerprint, so it cannot be tied to the {tree.ref} tree",
                "",
            )
        ]
    prefix = expected.removeprefix("sha256:").lower()
    if not any(prefix.startswith(part.lower()) for part in quoted):
        return [
            Finding(
                where,
                "wrong tree",
                f"the document quotes sha256:{', sha256:'.join(quoted)} "
                f"but the {tree.ref} tree's fingerprint is sha256:{prefix}",
                "",
            )
        ]
    return []


def subject_digest(documents: list[pathlib.Path], trees: dict[str, Tree]) -> str:
    """A digest of what the check was about.

    The documents it read and the trees it resolved them against. It is not a
    staleness rule -- the checker reads its subject on every run, so nothing it
    says can go stale -- but it makes "this verdict was about this subject" a
    statement that can be compared, rather than an assumption.
    """
    digest = hashlib.sha256()
    for document in sorted(documents):
        if not document.is_file():
            continue
        digest.update(relative_path(document).encode("utf-8"))
        digest.update(b"\0")
        # The bytes are normalised to LF first: git checks the documents out
        # with CRLF on Windows and LF on Linux, and a digest of the raw bytes
        # would make the same document two subjects -- one per platform.
        content = document.read_bytes().replace(b"\r\n", b"\n")
        digest.update(hashlib.sha256(content).hexdigest().encode("utf-8"))
        digest.update(b"\0")
    for label, tree in sorted(trees.items()):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update((tree_fingerprint(tree) or "").encode("utf-8"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def check_documents(documents: list[pathlib.Path]) -> Report:
    """Check every citation in every document."""
    clauses_found: list[Clause] = []
    findings: list[Finding] = []
    trees: dict[str, Tree] = {}
    counts: dict[str, list[int]] = {}

    for document in documents:
        if not document.is_file():
            continue
        tree = tree_of(document)
        trees[tree.label] = tree
        found = document_clauses(document, tree)
        clauses_found.extend(found)
        findings.extend(document_orphan_declarations(document))
        entry = counts.setdefault(tree.label, [0, 0])
        entry[0] += 1
        entry[1] += sum(len(clause.citations) for clause in found)
        if not tree.is_working_copy:
            findings.extend(check_declaration(document, tree))

    for clause in clauses_found:
        findings.extend(check_clause(clause))

    citations = sum(len(clause.citations) for clause in clauses_found)
    named = sum(
        1
        for clause in clauses_found
        for citation, names in zip(clause.citations, clause.claims, strict=True)
        if is_compared(citation, names)
    )
    declared = sum(
        1 for clause in clauses_found for citation in clause.citations if citation.anchors
    )
    valued = sum(
        1
        for clause in clauses_found
        for citation, values in zip(clause.citations, clause.values, strict=True)
        if values and citation.target is not None
    )
    return Report(
        citations=citations,
        named=named,
        road_sign=citations - named - valued,
        declared=declared,
        findings=tuple(findings),
        valued=valued,
        trees=tuple((label, counts[label][0], counts[label][1]) for label in sorted(counts)),
        subject=subject_digest(documents, trees),
    )


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    report = check_documents(DOCS)

    print(f"citations: {report.citations}")
    print(f"  naming a symbol: {report.named}")
    print(f"  comparing a value: {report.valued}")
    print(f"  pointing only at a location: {report.road_sign}")
    print(f"  declaring what they point at: {report.declared}")
    print("trees:")
    for label, documents, citations in report.trees:
        print(f"  {label}: {documents} document(s), {citations} citation(s)")
    print(f"subject: {report.subject}")
    print(f"unresolved paths: {len(report.unresolved)}")
    for finding in report.unresolved:
        print(f"  {finding.render()}")
    print(f"drifted: {len(report.drifted)}")
    for finding in report.drifted:
        print(f"  {finding.render()}")
    print(f"values not matching: {len(report.value_findings)}")
    for finding in report.value_findings:
        print(f"  {finding.render()}")
    if report.drifted or report.unresolved:
        print(
            f"\n{len(report.drifted) + len(report.unresolved)} citation(s) no longer say what they say."
        )
        return 1
    if report.value_findings:
        print(
            f"\n{len(report.value_findings)} citation(s) name a value the cited line does "
            "not carry. They are reported, not counted as drift."
        )
    print("\nEvery citation still says what it says.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
