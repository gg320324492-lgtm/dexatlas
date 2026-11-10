"""Re-derive the citation line numbers after the source tree moved.

A citation in the documentation says "this line of this file". When the code
moves, that sentence is a small lie, and the checker in
``scripts/check-doc-citations.py`` is what notices.

Most of the sentences that carry a citation name the thing they point at —
"the ``Project.new_id()`` at ``models.py:812-814``". The checker already
knows how to find a symbol's definition, so the number can be read off the
code instead of guessed at: the citation is moved onto where the symbol it
names now lives.

The script is **idempotent**. It moves a citation only when the checker says
the symbol it names is no longer inside the cited range, so running it twice
over the same document changes nothing the second time. That matters: the
earlier version of this script carried the old numbers across by diffing two
trees, which meant a second run over an already-mapped document moved every
number twice. A citation that points at a place rather than at a named symbol
has nothing to look up, so it is left alone and the checker reports it — a
number is not worth guessing at.

    uv run --no-sync python scripts/remap-citations.py            # the three documents
    uv run --no-sync python scripts/remap-citations.py docs/x.md  # one of them

Then run the checker, which is the authority on what a citation has to say:

    uv run --no-sync python scripts/check-doc-citations.py
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: The documents the citation checker reads. The remapper works on the same
#: ones, because a citation in a document the checker never reads is a
#: citation nobody checks.
DOCUMENTS = (
    REPO / "docs" / "analysis-provenance.md",
    REPO / "docs" / "reports" / "phase1-execution-report.md",
    REPO / "docs" / "benchmarks" / "large-apk.md",
)

CITATION = re.compile(r"`([\w./-]+\.(?:py|sh|toml|yml)):(\d+)(?:-(\d+))?`")

#: The directories the citation checker does not look in. The remapper has to
#: find the same file the checker found, or it leaves the citation alone and
#: the drift survives.
SKIP_DIRECTORIES = {".git", ".venv", "build", ".claude", ".scratch", "node_modules"}


def _checker():
    """The citation checker, loaded as a module.

    The rules about what a citation means live in one place, and a second
    copy of them would be a second set of rules.
    """
    script = REPO / "scripts" / "check-doc-citations.py"
    spec = importlib.util.spec_from_file_location("dexatlas_doc_citations", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mentions(checker, target: Path, symbol: str) -> list[int]:
    """Where a name is used in a file that does not define it.

    An import is not a use: the line that brings a name in is not the place
    the name is used, and a range that started there would point at the
    import rather than at the code. The name is matched as a whole word, so
    ``kind`` does not match ``kinds``.
    """
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    out: list[int] = []
    for number, line in enumerate(checker.file_lines(target), 1):
        if re.match(r"\s*(?:from|import)\s", line):
            continue
        if pattern.search(line):
            out.append(number)
    return out


def _anchors(checker, document: Path) -> dict[tuple[str, int, int], tuple[int, int]]:
    """Where the symbols each drifted citation names are now.

    The key is the citation's file and its line range; the value is the range
    the citation has to hold to keep saying what it says.

    Every symbol the citation names is placed, not only the ones that drifted:
    a citation that says "``class_source_document`` / ``method_source_document``"
    has to keep holding both of them, and a range that moved onto the first
    and left the second behind says something narrower than it used to.
    """
    anchors: dict[tuple[str, int, int], tuple[int, int]] = {}
    for clause in checker.document_clauses(document):
        for citation, names in zip(clause.citations, clause.claims, strict=True):
            if citation.target is None or not names:
                continue
            lines = checker.file_lines(citation.target)
            positions: list[int] = []
            drifted = False
            for name in names:
                anchor = name.rsplit(".", 1)[-1]
                if checker.symbol_is_in_range(
                    citation.target, anchor, citation.start, citation.end
                ):
                    # The symbol is where the citation says it is. It still has
                    # to be placed, because the new range has to keep holding
                    # it -- but it does not make the citation a drifted one.
                    positions.extend(_where(checker, citation.target, anchor, citation))
                    continue
                where = _where(checker, citation.target, anchor, citation)
                if not where:
                    continue
                positions.extend(where)
                drifted = True
            if not drifted or not positions:
                continue
            length = citation.end - citation.start
            start = min(positions)
            end = start + length
            if end > len(lines):
                continue
            if not all(start <= line <= end for line in positions):
                # The symbols sit further apart than the range is long, so no
                # range of the same shape holds all of them. The checker says
                # so, and a person decides.
                continue
            anchors[(citation.rel, citation.start, citation.end)] = (start, end)
    return anchors


def _where(checker, target: Path, symbol: str, citation) -> list[int]:
    """Where a symbol is, in a file that may only mention it.

    A file that defines the symbol has one place for it. A file that only
    mentions it -- a table name in a SQL string, an imported class, an
    enumeration member -- has the places it is used, and the range has to
    hold the run of them. When the symbol is already inside the cited range,
    only the mentions inside it count: the ones outside it are places the
    name appears in other code, and dragging them into the new range would
    make it point at something else.
    """
    line = checker.definition_line(target, symbol)
    if line is not None:
        return [line]
    mentions = _mentions(checker, target, symbol)
    inside = [where for where in mentions if citation.start <= where <= citation.end]
    return inside or mentions


def _rewrite(checker, document: Path) -> int:
    """Move every drifted citation onto where its symbol is."""
    anchors = _anchors(checker, document)
    if not anchors:
        return 0
    text = document.read_text(encoding="utf-8")
    moved = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal moved
        rel, start_s, end_s = match.group(1), match.group(2), match.group(3)
        start, end = int(start_s), int(end_s or start_s)
        anchor = anchors.get((rel, start, end))
        if anchor is None:
            return match.group(0)
        new_start, new_end = anchor
        if (new_start, new_end) == (start, end):
            return match.group(0)
        moved += 1
        if new_start == new_end:
            return f"`{rel}:{new_start}`"
        return f"`{rel}:{new_start}-{new_end}`"

    document.write_text(CITATION.sub(replace, text), encoding="utf-8")
    return moved


def _uncommitted(document: Path) -> bool:
    """Whether the document has changes that are not committed yet.

    The script rewrites numbers, so running it over a document that already
    carries uncommitted edits means the edits and the rewritten numbers are
    mixed together in one diff. It still works — the numbers are right either
    way — but the diff is harder to read than it needs to be, so it is said
    out loud rather than left to be discovered.
    """
    relative = document.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    return result.returncode != 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "documents",
        nargs="*",
        type=Path,
        help="the documents to re-derive; the default is the ones the checker reads",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="say only how many citations moved",
    )
    arguments = parser.parse_args(argv)

    documents = arguments.documents or list(DOCUMENTS)
    checker = _checker()
    for document in documents:
        if not document.is_file():
            print(f"{document}: not there")
            continue
        if _uncommitted(document) and not arguments.quiet:
            print(f"{document.name}: it has uncommitted changes; the diff will mix them")
        moved = _rewrite(checker, document)
        print(f"{document.name}: {moved} citation(s) moved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
