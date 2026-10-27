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

The summary says how many citations each kind of check reached, so the number
of citations that carry a real check is never a guess. The exit code is the
answer: 0 when every citation holds, 1 when one has drifted. A checker that
always says 0 is a gate that never opens.
"""

from __future__ import annotations

import ast
import functools
import pathlib
import re
import sys
from dataclasses import dataclass

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = [
    REPO / "docs" / "analysis-provenance.md",
    REPO / "docs" / "reports" / "phase1-execution-report.md",
    REPO / "docs" / "benchmarks" / "large-apk.md",
]

#: A backticked span of the documentation.
SPAN = re.compile(r"`([^`\n]+)`")

#: path:line or path:start-end — the whole backticked span has to be a citation.
CITATION = re.compile(r"^([\w./-]+\.(?:py|sh|toml|yml)):(\d+)(?:-(\d+))?$")

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
#: of a file in there would be a citation to the wrong tree.
SKIP_DIRECTORIES = {".git", ".venv", "build", ".claude", ".scratch", "node_modules"}


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

    @property
    def where(self) -> str:
        return f"{self.document.name}:{self.line}  {self.rel}:{self.start}-{self.end}"


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

    @property
    def unresolved(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind in {"unresolved", "ambiguous"})

    @property
    def drifted(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind not in {"unresolved", "ambiguous"})


def candidates(rel: str) -> list[pathlib.Path]:
    """Every file in the repository a citation could mean.

    The documents sometimes abbreviate a path to a bare file name. Those are
    found by name, and only when the name is unambiguous — a citation that
    could mean two files is a finding, not a guess.
    """
    for candidate in (
        REPO / rel,
        REPO / "src" / "dexatlas" / rel,
        REPO / "scripts" / rel,
        REPO / "tests" / rel,
        REPO / "examples" / rel,
    ):
        if candidate.is_file():
            return [candidate]
    name = rel.rsplit("/", 1)[-1]
    return [
        path
        for path in REPO.rglob(name)
        if path.is_file() and not set(path.relative_to(REPO).parts) & SKIP_DIRECTORIES
    ]


@functools.cache
def file_lines(path: pathlib.Path) -> tuple[str, ...]:
    """The lines of a file, read once."""
    return tuple(path.read_text(encoding="utf-8", errors="replace").splitlines())


def symbol_lines(path: pathlib.Path, symbol: str) -> list[int]:
    """The lines of a file that name a symbol.

    The symbol is matched as a whole word, so ``kind`` does not match
    ``kinds``.
    """
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    return [number for number, line in enumerate(file_lines(path), 1) if pattern.search(line)]


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


def definition_line(path: pathlib.Path, symbol: str) -> int | None:
    """The line where a class or a function is defined."""
    if path.suffix == ".py":
        try:
            tree = ast.parse("\n".join(file_lines(path)))
        except SyntaxError:
            tree = None
        if tree is not None:
            lines = [
                node.lineno
                for node in ast.walk(tree)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == symbol
            ]
            if lines:
                return min(lines)
    for number, line in enumerate(file_lines(path), 1):
        if re.match(rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(symbol)}\b", line):
            return number
    return None


def definition_span(path: pathlib.Path, symbol: str) -> tuple[int, int] | None:
    """The lines of a function's definition and of the body it opens.

    A citation that names a function may point at the function's definition
    or at code inside it — "the counting at ``storage.py:520-526``" is
    inside ``save_symbols`` even though the ``def`` is a hundred lines up.
    """
    if path.suffix == ".py":
        try:
            tree = ast.parse("\n".join(file_lines(path)))
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
    lines = file_lines(path)
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


def symbol_is_in_range(target: pathlib.Path, name: str, start: int, end: int) -> bool | None:
    """Whether a symbol is inside a cited range.

    A symbol the file defines has to be defined in the range, or the range has
    to be inside the body it opens. A symbol the file only mentions has to be
    mentioned in the range.

    None means the file does not name the symbol at all, so there is nothing
    to compare against.
    """
    defined = definition_line(target, name)
    if defined is not None:
        if start - SLACK <= defined <= end + SLACK:
            return True
        body = definition_span(target, name)
        return bool(body is not None and body[0] - SLACK <= start and end <= body[1] + SLACK)
    where = symbol_lines(target, name)
    if not where:
        return None
    return any(start - SLACK <= line <= end + SLACK for line in where)


def document_clauses(document: pathlib.Path) -> list[Clause]:
    """Every clause of a document, with its citations and the symbols it names."""
    text = document.read_text(encoding="utf-8")
    found: list[Clause] = []
    for start, end in clauses(text):
        clause = text[start:end]
        names = span_names(clause)
        spans = list(SPAN.finditer(clause))
        brackets = bracket_ranges(clause)
        found_spans = [
            (match, citation)
            for match, citation in ((m, CITATION.match(m.group(1))) for m in spans)
            if citation is not None
        ]
        if not found_spans:
            continue
        citations: list[Citation] = []
        for match, citation in found_spans:
            rel, start_s, end_s = citation.group(1), citation.group(2), citation.group(3)
            options = candidates(rel)
            citations.append(
                Citation(
                    document=document,
                    line=text[: start + match.start()].count("\n") + 1,
                    rel=rel,
                    start=int(start_s),
                    end=int(end_s or start_s),
                    target=options[0] if len(options) == 1 else None,
                    ambiguous=len(options) > 1,
                    text=clause.strip()[:100],
                )
            )
        citation_spans = [match.span() for match, _ in found_spans]
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


def check_citation(citation: Citation) -> list[Finding]:
    """The findings of one citation's location."""
    if citation.target is None:
        kind = "ambiguous" if citation.ambiguous else "unresolved"
        detail = "the name could mean several files" if citation.ambiguous else "no such file"
        return [Finding(citation.where, kind, detail, citation.text)]

    lines = file_lines(citation.target)
    if citation.start < 1 or citation.end < citation.start or citation.end > len(lines):
        return [
            Finding(
                citation.where,
                "out of range",
                f"the file has {len(lines)} lines",
                citation.text,
            )
        ]
    if not any(
        line.strip() and not line.strip().startswith("#")
        for line in lines[citation.start - 1 : citation.end]
    ):
        return [
            Finding(citation.where, "points at nothing", "the range holds no code", citation.text)
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
        for name in names:
            anchor = name.rsplit(".", 1)[-1]
            if symbol_is_in_range(citation.target, anchor, citation.start, citation.end):
                located.add(name)
            else:
                missing.setdefault(name, citation)

    for name, citation in missing.items():
        if name in located:
            continue
        if citation.target is None:
            continue
        anchor = name.rsplit(".", 1)[-1]
        where = symbol_lines(citation.target, anchor)
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
    for name in names:
        anchor = name.rsplit(".", 1)[-1]
        if is_symbolic(name) or symbol_lines(citation.target, anchor):
            return True
    return False


def check_documents(documents: list[pathlib.Path]) -> Report:
    """Check every citation in every document."""
    clauses_found: list[Clause] = []
    for document in documents:
        if document.is_file():
            clauses_found.extend(document_clauses(document))

    findings: list[Finding] = []
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
    )


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    report = check_documents(DOCS)

    print(f"citations: {report.citations}")
    print(f"  naming a symbol: {report.named}")
    print(f"  pointing only at a location: {report.road_sign}")
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
