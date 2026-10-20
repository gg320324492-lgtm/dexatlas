"""The documentation's citations have to keep up with the code.

Both the execution report and the provenance document cite specific lines of
specific files, and so does the large-APK benchmark. A citation that has drifted
is a small lie, and this project has collected enough of them: the
cross-reference fix was described with the reason backwards, a version was
quoted in the wrong shape, and a test name belonged to a different test.

The check is exact rather than heuristic. When a sentence names a symbol and
cites a line range, the symbol's own definition — or the call that constructs
it — has to fall inside that range. Naming a class and citing the lines where it
is built is a concrete claim, and it can be checked.

The logic lives in ``scripts/check-doc-citations.py`` so it can also be run by
hand when a document is edited.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-doc-citations.py"


def _checker():
    """Load the checker as a module, the way the test suite loads the figure script."""
    spec = importlib.util.spec_from_file_location("dexatlas_doc_citations", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_citation_checker_exists() -> None:
    assert SCRIPT.is_file(), "scripts/check-doc-citations.py is missing"


def test_every_citation_in_the_documents_resolves_to_a_file() -> None:
    """A citation to a file that does not exist cannot be checked, and is wrong."""
    checker = _checker()

    unresolved = []
    for doc in checker.DOCS:
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for match in checker.CITATION.finditer(line):
                rel = match.group(1)
                if checker.resolve(rel) is None:
                    unresolved.append(f"{doc.name}:{number}  {rel}")

    assert not unresolved, "citations to files that do not exist:\n" + "\n".join(unresolved)


def test_every_cited_symbol_is_inside_the_cited_range() -> None:
    """The cited lines have to contain the symbol the sentence names.

    This is the check that would have caught the citations that drifted when the
    code around them changed.

    A couple of lines of slack: a cited range often ends on the line before the
    construction it leads to, and that is the same claim, not a different one.
    """
    checker = _checker()
    slack = 2

    drifted: list[str] = []
    for doc in checker.DOCS:
        if not doc.is_file():
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            matches = list(checker.CITATION.finditer(line))
            for match in matches:
                rel, start_s, end_s = match.group(1), match.group(2), match.group(3)
                target = checker.resolve(rel)
                if target is None:
                    continue
                start, end = int(start_s), int(end_s or start_s)
                # A line with several citations names its symbols for all of them, and
                # there is no way to tell which belongs where. Those lines are checked
                # by hand.
                if len(matches) > 1:
                    continue
                for name in checker.NAMED.findall(line):
                    if name in checker.NOT_SYMBOLS:
                        continue
                    where = checker.symbol_lines(target, name)
                    if not where:
                        continue  # the symbol is not in this file; nothing to check
                    if not any(start - slack <= w <= end + slack for w in where):
                        nearest = min(where, key=lambda w: abs(w - start))
                        drifted.append(
                            f"{doc.name}:{number}  {rel}:{start}-{end}  "
                            f"`{name}` is at line {nearest}"
                        )

    assert not drifted, "citations that no longer contain what they name:\n" + "\n".join(drifted)
