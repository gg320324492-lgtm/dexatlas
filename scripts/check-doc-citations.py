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

What it does not check
----------------------

A citation that only points at a location — "this logic lives in
``core/pipeline.py:296``" — cannot say whether the code there is still the
code that was meant. There is nothing in the sentence to check the lines
against. Those citations get the *where* check and nothing more.

A citation that names a symbol is checked for that symbol being *named* in
the lines, not for the lines being where the symbol is *defined*: a document
that cites the place a class is used is not caught by pointing at another
place it is used.

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
from dataclasses import dataclass

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
    REPO / "docs" / "reports" / "ci-temp-redirect-fix.md",
    REPO / "docs" / "reports" / "m10-round3-fixes.md",
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


@dataclass(frozen=True)
class Clause:
    """One piece of a sentence, with the citations and the symbols it holds."""

    document: pathlib.Path
    line: int
    citations: tuple[Citation, ...]
    #: For every citation, the names it claims to locate.
    claims: tuple[tuple[str, ...], ...]


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
        return tuple(f for f in self.findings if f.kind not in {"unresolved", "ambiguous"})


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
        name = NAME.match(match.group(1))
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
    """Every citation of a text, with the file and the range each one names.

    Two forms are read. A full citation names its file: ``core/pipeline.py:296``.
    A bare one names only a line: ``:143``. The bare form is the same file as
    the citation before it — that is how the release appendix cites one file
    in several places — and it is the same file only as long as both sit in
    the same block of the text.
    """
    ends = block_ends(text)
    resolved: list[Resolved] = []
    previous: Resolved | None = None
    for match in SPAN.finditer(text):
        inner = match.group(1)
        citation = CITATION.match(inner)
        if citation is not None:
            start = int(citation.group(2))
            previous = Resolved(match, citation.group(1), start, int(citation.group(3) or start))
            resolved.append(previous)
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
            previous = Resolved(previous.match, previous.rel, previous.start, end)
            resolved[-1] = previous
            continue
        previous = Resolved(match, previous.rel, start, end)
        resolved.append(previous)
    return resolved


def document_clauses(document: pathlib.Path, tree: Tree = WORKING_COPY) -> list[Clause]:
    """Every clause of a document, with its citations and the symbols it names."""
    text = document.read_text(encoding="utf-8")
    resolved = resolve_citations(text)
    found: list[Clause] = []
    for start, end in clauses(text):
        clause = text[start:end]
        names = span_names(clause)
        brackets = bracket_ranges(clause)
        inside = [item for item in resolved if start <= item.match.start() < end]
        if not inside:
            continue
        citations: list[Citation] = []
        citation_spans: list[tuple[int, int]] = []
        for item in inside:
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
            )
        )
    return found


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


def check_clause(clause: Clause) -> list[Finding]:
    """The findings of one clause."""
    findings: list[Finding] = []
    for citation in clause.citations:
        findings.extend(check_citation(citation))

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
    return Report(
        citations=citations,
        named=named,
        road_sign=citations - named,
        findings=tuple(findings),
        trees=tuple((label, counts[label][0], counts[label][1]) for label in sorted(counts)),
        subject=subject_digest(documents, trees),
    )


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    report = check_documents(DOCS)

    print(f"citations: {report.citations}")
    print(f"  naming a symbol: {report.named}")
    print(f"  pointing only at a location: {report.road_sign}")
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
    if report.findings:
        print(f"\n{len(report.findings)} citation(s) no longer say what they say.")
        return 1
    print("\nEvery citation still says what it says.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
