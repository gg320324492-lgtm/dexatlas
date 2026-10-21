"""The documentation's citations have to keep up with the code.

The provenance document and the large-APK benchmark cite specific lines of
specific files. A citation that has drifted is a small lie, and this project
has collected enough of them: the cross-reference fix was described with the
reason backwards, a version was quoted in the wrong shape, and a test name
belonged to a different test.

The check is exact rather than heuristic. When a sentence names a symbol and
cites a line range, the symbol has to be inside that range — a symbol the
file defines has to be defined there, or the range has to be inside the body
it opens. Naming a class and citing the lines where it is built is a concrete
claim, and it can be checked.

The logic lives in ``scripts/check-doc-citations.py`` so it can also be run by
hand when a document is edited. These tests call that script's ``main()``
rather than repeating its rules: a checker that is written twice is two
checkers, and only one of them is ever fixed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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


def test_every_citation_in_the_documents_still_says_what_it_says(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The documents are checked by the script, and the script passes.

    The exit code is the checker's answer. A checker that always answers 0 is
    a gate that never opens, so this asserts the code as well as the output.
    """
    checker = _checker()

    code = checker.main()
    written = capsys.readouterr().out

    assert code == 0, f"the citation checker found drift:\n{written}"
    assert "drifted: 0" in written


def test_the_checker_reaches_every_citation_the_documents_hold() -> None:
    """No citation is skipped.

    The first version of this checker only looked at the citations whose line
    named a capitalised symbol — 18 of the 94. Every citation is checked now:
    the file has to exist and the lines have to be inside it, and the ones
    that name a symbol are checked against it.
    """
    checker = _checker()
    report = checker.check_documents(checker.DOCS)

    counted = 0
    for document in checker.DOCS:
        if not document.is_file():
            continue
        text = document.read_text(encoding="utf-8")
        counted += sum(
            1 for span in checker.SPAN.finditer(text) if checker.CITATION.match(span.group(1))
        )

    assert counted > 0
    assert report.citations == counted, "the checker did not look at every citation"


def test_the_checker_checks_more_than_the_citations_that_name_a_class() -> None:
    """The symbol check cannot collapse back to the handful it used to reach.

    The names it follows are not only the ones that start with a capital:
    ``add_exported_components`` and ``ManifestComponent.exported`` are symbols
    too, and a citation that names one of them is checked against it.
    """
    checker = _checker()
    report = checker.check_documents(checker.DOCS)

    assert report.named * 2 >= report.citations, (
        "only a minority of the citations carry a symbol to check: "
        f"{report.named} of {report.citations}"
    )


def test_a_citation_that_has_drifted_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The check has teeth: a citation that no longer holds is a failure.

    This is the whole point of the exit code. A checker that answered 0
    whatever it found would pass this test suite with its checks deleted.
    """
    checker = _checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The `Provenance` class is built at `src/dexatlas/core/models.py:2-3`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    written = capsys.readouterr().out
    assert "drifted: 1" in written
    assert "Provenance" in written


def test_a_citation_to_a_file_that_does_not_exist_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A citation to a file that is not there cannot be checked, and is wrong."""
    checker = _checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The logic lives at `src/dexatlas/core/no_such_file.py:1-2`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    written = capsys.readouterr().out
    assert "unresolved paths: 1" in written


def test_a_citation_past_the_end_of_the_file_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lines a citation names have to be inside the file it names."""
    checker = _checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The `Provenance` class is built at `src/dexatlas/core/models.py:89-9000`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    written = capsys.readouterr().out
    assert "out of range" in written


def test_a_citation_to_a_file_that_does_not_hold_the_symbol_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A citation that names a symbol has to name a file that holds it.

    The old checker skipped the citation when the symbol was nowhere in the
    file, so pointing a citation at the wrong file was invisible.
    """
    checker = _checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The `Provenance` class is built at `src/dexatlas/reports/markdown.py:89-121`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    written = capsys.readouterr().out
    assert "Provenance" in written


def test_a_citation_that_names_a_lowercase_symbol_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The names that are checked are not only the ones that start with a capital."""
    checker = _checker()
    document = tmp_path / "doc.md"
    # The range is computed rather than written down: this test is about the
    # rule that a cited range has to hold the symbol it names, and a range
    # typed into the test would fail for a different reason every time the
    # method moved -- which is not what the test is about.
    source = REPO_ROOT / "src" / "dexatlas" / "core" / "evidence.py"
    line = checker.definition_line(source, "add_exported_components")
    assert line is not None, "the method this test cites is not in the file"
    document.write_text(
        f"The `add_exported_components` method is at "
        f"`src/dexatlas/core/evidence.py:{line}-{line}`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0

    document.write_text(
        "The `add_exported_components` method is at `src/dexatlas/core/evidence.py:2-3`\n",
        encoding="utf-8",
    )

    assert checker.main() == 1


def test_a_backend_name_in_prose_is_not_code_the_citation_has_to_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The name of a tool is a word a sentence uses, not code a citation points at.

    A table row that lists the backends and cites the line that fills the
    ``tool`` field was reported as drift: the file the citation names happens
    to mention one of them in a docstring, and the checker took the mention
    for the claim. The row says which backends exist; the citation says who
    fills the field. Both are true, and the citation is the one that is
    checked.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    document.write_text(
        "| `tool` | `str` | the backend name (`jadx` / `apktool` / `androguard`) "
        "| `src/dexatlas/tools/base.py:258` |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0


def test_a_citation_that_only_points_at_a_location_is_still_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A citation with no symbol in its sentence is checked for existing.

    There is nothing in the sentence to check the lines against, so the lines
    are only checked for being inside the file — and the file has to be there.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    document.write_text(
        "The logic lives at `src/dexatlas/core/no_such_file.py:1-2`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1


def _line_of(path: Path, text: str) -> int:
    """The line a piece of code is on, read out of the file itself."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if text in line:
            return number
    raise AssertionError(f"{text!r} is not in {path}")


def test_every_citation_on_a_line_that_cites_several_places_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A line that points at several places is checked in each of them.

    The old checker skipped the lines that held more than one citation, on
    the grounds that there was no way to tell which name belonged where. The
    names are told apart now, so the line is checked in every one of them.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    # The ranges are computed rather than written down: this test is about the
    # rule that a line citing several places is checked in each of them, and a
    # range typed into the test would fail for a different reason every time
    # the pipeline moved.
    source = REPO_ROOT / "src" / "dexatlas" / "core" / "pipeline.py"
    apktool = _line_of(source, "if include_apktool:")
    androguard = _line_of(source, "if include_androguard:")
    document.write_text(
        f"The stages run in order (`core/pipeline.py:{apktool}-{apktool}` with "
        f"`include_apktool` and `core/pipeline.py:{androguard}-{androguard}` with "
        f"`include_androguard`).\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0

    document.write_text(
        f"The stages run in order (`core/pipeline.py:{apktool}-{apktool}` with "
        f"`include_apktool` and `core/pipeline.py:2-3` with `include_androguard`).\n",
        encoding="utf-8",
    )

    assert checker.main() == 1


def test_a_symbol_one_line_outside_the_range_is_a_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The range has to hold the symbol. There is no room for "close enough".

    A line of slack let the range beside it satisfy the check, which is how
    the pipeline's three backend stages went unchecked: each one answered for
    the next.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    document.write_text(
        "The `Provenance` class is at `src/dexatlas/core/models.py:86-88`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1


def test_a_class_is_checked_where_it_is_defined_not_merely_where_it_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Naming a class in a line is not the same as pointing at its definition.

    ``Provenance`` is named in the field of another model, a long way from
    the class itself. A citation that points at the field is a citation to
    the wrong lines, and the check has to say so.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    document.write_text(
        "The `Provenance` class is at `src/dexatlas/core/models.py:126-126`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1


def test_the_exit_code_is_the_same_on_any_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A checker that answers differently on another machine is worse than none.

    The exit code is the checker's answer, and it must not depend on what the
    console can encode.
    """
    checker = _checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The `Provenance` class is built at `src/dexatlas/core/models.py:2-3` 🔴\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    with_utf8 = checker.main()
    capsys.readouterr()

    import io

    stream = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)
    with_gbk = checker.main()
    stream.flush()
    written = stream.buffer.getvalue().decode("utf-8")

    assert with_gbk == with_utf8
    assert with_utf8 == 1
    assert "🔴" in written
    assert "Traceback" not in written
