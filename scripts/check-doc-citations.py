"""Check every file:line citation in the documentation against the code.

Run it directly to see the drift, or let the test suite run it:

    uv run python scripts/check-doc-citations.py

The report and the provenance document cite specific lines. A citation that has
drifted is a small lie, and there have been enough of them to be worth a tool.

The check is precise rather than heuristic: when a sentence names a symbol and
cites a line range, the symbol's own definition (or its construction) has to fall
inside that range. Naming a class and citing the lines where it is built is a
concrete claim, and it can be checked exactly.
"""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = [
    REPO / "docs" / "analysis-provenance.md",
    REPO / "docs" / "reports" / "phase1-execution-report.md",
]

#: path:line or path:start-end
CITATION = re.compile(r"`([\w./-]+\.(?:py|sh|toml|yml)):(\d+)(?:-(\d+))?`")

#: Identifiers a sentence may name in backticks.
NAMED = re.compile(r"`([A-Z][A-Za-z0-9_]*)`")

#: Where a symbol shows up: its definition, a call that constructs it, or a type
#: annotation that names it. All three are ways the code mentions a symbol.
DEFINED = re.compile(r"^\s*(?:class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
CONSTRUCTED = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\(")
MENTIONED = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")

#: Words that are capitalised but are not symbols.
NOT_SYMBOLS = {"The", "This", "A", "An", "In", "It", "And", "But", "For", "When", "If"}


def resolve(rel: str) -> pathlib.Path | None:
    for candidate in (
        REPO / rel,
        REPO / "src" / "dexatlas" / rel,
        REPO / "scripts" / rel,
        REPO / "tests" / rel,
        REPO / "examples" / rel,
    ):
        if candidate.is_file():
            return candidate
    # The documents sometimes abbreviate a path to a bare file name. Find it by
    # name when it is unambiguous, so those citations can be checked too.
    name = rel.rsplit("/", 1)[-1]
    matches = [
        path
        for path in REPO.rglob(name)
        if path.is_file()
        and not set(path.relative_to(REPO).parts)
        & {".git", ".venv", "build", ".claude", "node_modules"}
    ]
    return matches[0] if len(matches) == 1 else None


def symbol_lines(path: pathlib.Path, symbol: str) -> list[int]:
    """Lines where the symbol is named."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = set()
    for match in MENTIONED.finditer(text):
        if match.group(1) == symbol:
            lines.add(text[: match.start()].count("\n") + 1)
    return sorted(lines)


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


def main() -> int:
    use_utf8_output()
    checked = 0
    drifted: list[str] = []
    unknown: list[str] = []

    for doc in DOCS:
        if not doc.is_file():
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for match in CITATION.finditer(line):
                rel, start_s, end_s = match.group(1), match.group(2), match.group(3)
                start, end = int(start_s), int(end_s or start_s)
                target = resolve(rel)
                if target is None:
                    unknown.append(f"{doc.name}:{number}  {rel} (not found)")
                    continue
                checked += 1

                names = [
                    n
                    for n in NAMED.findall(line)
                    if n not in NOT_SYMBOLS and not n.endswith(("Error", "Ref"))
                ]
                for name in names:
                    where = symbol_lines(target, name)
                    if not where:
                        continue  # the symbol is not in this file; nothing to check
                    if not any(start <= w <= end for w in where):
                        nearest = min(where, key=lambda w: abs(w - start))
                        drifted.append(
                            f"{doc.name}:{number}  {rel}:{start}-{end}  "
                            f"`{name}` is at line {nearest}  |  {line.strip()[:100]}"
                        )

    print(f"citations checked: {checked}")
    print(f"unresolved paths: {len(unknown)}")
    for line in unknown:
        print(f"  {line}")
    print(f"drifted: {len(drifted)}")
    for line in drifted:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
