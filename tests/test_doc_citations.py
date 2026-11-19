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
import re
import subprocess
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
        counted += len(checker.resolve_citations(text))

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

    # The November 2026 review reports are mostly audit tables: their
    # citations point at a place ("this row's number is at ``status.md:26``")
    # rather than at a symbol, so the symbol share of the whole drops. A fifth
    # still says the check reaches far beyond the handful of class citations
    # it used to be limited to.
    assert report.named * 5 >= report.citations, (
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
    line = checker.definition_line(checker.file_lines(source), "add_exported_components", True)
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

    # The line is found rather than written down: the file it points into is
    # rewritten from time to time, and a test that names a line goes red for
    # a change that was not about it.
    source = (REPO_ROOT / "src" / "dexatlas" / "tools" / "base.py").read_text(encoding="utf-8")
    line = next(
        number
        for number, text in enumerate(source.splitlines(), start=1)
        if text.strip() == "tool=self.name,"
    )
    document.write_text(
        "| `tool` | `str` | the backend name (`jadx` / `apktool` / `androguard`) "
        f"| `src/dexatlas/tools/base.py:{line}` |\n",
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


def test_the_release_documents_are_checked() -> None:
    """The release notes and the release body are on the checker's list.

    The release body carries the appendix that says where every number of a
    release came from. Those line numbers drifted for a long time — nobody
    was checking them, because the document was not on this list.
    """
    checker = _checker()
    names = {document.name for document in checker.DOCS}

    assert "v1.0.0-github-release-body.md" in names, "the release body is not checked"
    assert "v1.0.0.md" in names, "the release notes are not checked"


def test_a_drifted_citation_in_the_release_body_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A line number in the release appendix that no longer holds is drift.

    The appendix is a table of "number in the body | source". Corrupting one
    of its line numbers has to turn the check red: a table of claims that
    nothing checks is a table of guesses.
    """
    checker = _checker()
    body = REPO_ROOT / "docs" / "reports" / "v1.0.0-github-release-body.md"
    text = body.read_text(encoding="utf-8")
    corrupted = text.replace("docs/status.md:37", "docs/status.md:3737", 1)
    assert corrupted != text, "the release body does not cite docs/status.md:37"

    document = tmp_path / "body.md"
    document.write_text(corrupted, encoding="utf-8")
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    written = capsys.readouterr().out
    assert "docs/status.md:3737" in written, "the corrupted line number was not the finding"


def _a_word_on_one_line_only(lines: list[str]) -> tuple[str, int]:
    """A word that one line of a text holds and no other line does.

    The word has to look like a symbol — a capital or an underscore in it —
    because that is what the checker compares a citation against.
    """
    words: dict[str, list[int]] = {}
    for number, line in enumerate(lines, start=1):
        for word in set(re.findall(r"[A-Z][A-Za-z0-9_]{3,}", line)):
            words.setdefault(word, []).append(number)
    for word, numbers in sorted(words.items()):
        if len(numbers) == 1:
            return word, numbers[0]
    raise AssertionError("no word appears on exactly one line")


def _a_name_mentioned_on_one_line_only(lines: list[str]) -> tuple[str, int]:
    """A name one line of a Python file mentions and no other line does.

    The name must not be one the file defines: a defined name is checked
    against its own definition, not against the line that mentions it.
    """
    defined: set[str] = set()
    mentioned: dict[str, list[int]] = {}
    for number, line in enumerate(lines, start=1):
        if re.match(r"^\s*(?:async\s+)?(?:def|class)\s", line):
            defined.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line))
            continue
        for name in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+", line)):
            mentioned.setdefault(name, []).append(number)
    for name, numbers in sorted(mentioned.items()):
        if len(numbers) == 1 and name not in defined:
            return name, numbers[0]
    raise AssertionError("no name appears on exactly one line")


def test_a_bare_line_number_is_read_as_a_line_of_the_file_named_before_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``:44`` after ``file:37`` is the line 44 of the same file.

    The release appendix writes its sources that way, and the checker used to
    read only the first half of the pair: it checked the line 37 of the file
    and never looked at the 38 to 44 the sentence pointed at. A citation that
    names a symbol on the second line of the range was therefore reported as
    drift, when it was in fact right.
    """
    checker = _checker()
    source = REPO_ROOT / "scripts" / "verify-public-contracts.py"
    name, number = _a_name_mentioned_on_one_line_only(
        source.read_text(encoding="utf-8").splitlines()
    )

    document = tmp_path / "doc.md"
    document.write_text(
        f"The `{name}` is at `scripts/verify-public-contracts.py:{number - 1}`–`:{number}`\n",  # noqa: RUF001
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    report = checker.check_documents([document])
    assert report.citations == 1, "the range was not read as one citation"
    assert checker.main() == 0, capsys.readouterr().out


def test_a_citation_into_a_markdown_file_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``file:line`` into a Markdown file is a citation like any other.

    The release appendix cites documents: the number it points at is in a
    Markdown file, and the checker used to read no extension but the code
    ones.
    """
    checker = _checker()
    status = REPO_ROOT / "docs" / "status.md"
    word, number = _a_word_on_one_line_only(status.read_text(encoding="utf-8").splitlines())

    document = tmp_path / "doc.md"
    document.write_text(f"The `{word}` is at `docs/status.md:{number}`\n", encoding="utf-8")
    monkeypatch.setattr(checker, "DOCS", [document])

    report = checker.check_documents([document])
    assert report.citations == 1, "the citation into the Markdown file was not read"


def test_a_bare_line_number_without_a_file_is_not_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``:44`` with no file named before it is not a citation.

    A number whose file was never named cannot be checked, and guessing the
    file would check the wrong one.
    """
    checker = _checker()
    document = tmp_path / "doc.md"
    document.write_text("The line is at `:44`\n", encoding="utf-8")
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0


def test_a_citation_to_a_comment_is_not_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A comment holds a sentence, and a citation can be about that sentence.

    The release appendix points at the header of ``scripts/fetch-fixtures.sh``
    for the claim that the script fetches two fixtures, and that line is a
    comment. The checker used to call every comment "nothing".
    """
    checker = _checker()
    source = REPO_ROOT / "scripts" / "fetch-fixtures.sh"
    line = next(
        number
        for number, text in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1)
        if "Two fixtures were fetched here" in text
    )

    document = tmp_path / "doc.md"
    document.write_text(
        f"Two fixtures are fetched by `scripts/fetch-fixtures.sh:{line}`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0


# -- which tree a citation is about -----------------------------------------


def _git(repository: Path, *args: str) -> None:
    """Run a git command in a repository the test has made."""
    subprocess.run(["git", *args], cwd=repository, check=True, capture_output=True)


#: The fingerprint the made-up repository's measurement carries.
FAKE_FINGERPRINT = "ab" * 32


def _repository_with_two_trees(tmp_path: Path) -> Path:
    """A repository whose working copy has moved on from the tree it tags.

    The file the document cites loses the line the citation names after the
    tag, so the citation holds in the tagged tree and not in the working copy.
    That is the case a checker cannot tell apart if it reads every citation
    out of the working copy: the number means one thing in one tree and
    another thing in the other.
    """
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q", "-b", "main")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Test")

    record = repository / "docs" / "reports"
    record.mkdir(parents=True)
    (record / "phase1-execution-report.md").write_text(
        '<!--report-figures:{"source_fingerprint": "sha256:' + FAKE_FINGERPRINT + '"}-->\n',
        encoding="utf-8",
    )
    (repository / "file.py").write_text(
        "\n".join(f"line {number}" for number in range(1, 11)) + "\n", encoding="utf-8"
    )
    (repository / "doc.md").write_text(
        f"The logic lives in `file.py:8`.\n\nThis document describes the tree "
        f"`sha256:{FAKE_FINGERPRINT}`.\n",
        encoding="utf-8",
    )
    _git(repository, "add", "-A")
    _git(repository, "commit", "-qm", "the release")
    _git(repository, "tag", "v1")

    # The working copy moves on: the cited line is gone from it.
    (repository / "file.py").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    _git(repository, "commit", "-qam", "the tree moved on")
    return repository


def _checker_for(repository: Path, monkeypatch: pytest.MonkeyPatch, tree: str | None):
    """The checker, pointed at the made-up repository."""
    checker = _checker()
    monkeypatch.setattr(checker, "REPO", repository)
    checker._files_by_name.cache_clear()
    monkeypatch.setattr(checker, "TREE_DOCUMENTS", {"doc.md": tree} if tree else {}, raising=False)
    return checker


def test_a_citation_is_read_out_of_the_tree_its_document_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A document says which tree its line numbers are in, and it is honoured.

    The citation points at line 8 of a file that had ten lines in the tagged
    tree and three in the working copy. Read out of the tagged tree it holds;
    read out of the working copy it is out of range. A checker that cannot
    tell the two apart has no way to say which of the two it did.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"

    checker = _checker_for(repository, monkeypatch, "v1")
    report = checker.check_documents([document])
    assert not report.findings, [finding.render() for finding in report.findings]

    # The same citation, read out of the tree the document does not name.
    checker = _checker_for(repository, monkeypatch, None)
    report = checker.check_documents([document])
    assert [finding.kind for finding in report.findings] == ["out of range"]


def test_a_document_that_quotes_another_tree_s_fingerprint_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The declaration is checked, not taken on trust.

    A document that names a tree it does not quote the fingerprint of is a
    document whose line numbers cannot be tied to anything, and the registry
    entry that says so is a claim nobody has checked.

    The fingerprint is quoted the way the documents quote it: abbreviated.
    One release body abbreviates it to eight hex characters and another to
    six, so a checker that only recognises the longer form calls a document
    that *does* name a fingerprint a document that quotes none -- a finding
    that is about the checker's own vocabulary rather than about the
    document.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "The logic lives in `file.py:8`.\n\nThis document describes the tree `sha256:cdcdcd…`.\n",
        encoding="utf-8",
    )

    checker = _checker_for(repository, monkeypatch, "v1")
    report = checker.check_documents([document])

    kinds = [finding.kind for finding in report.findings]
    assert "wrong tree" in kinds, [finding.render() for finding in report.findings]


def test_a_tree_that_is_not_in_the_checkout_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared tree that is not here cannot be checked, and says so.

    A checker that quietly fell back to the working copy would pass a document
    whose line numbers mean nothing in the tree it names.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"

    checker = _checker_for(repository, monkeypatch, "v9")
    report = checker.check_documents([document])

    kinds = [finding.kind for finding in report.findings]
    assert "no such tree" in kinds, [finding.render() for finding in report.findings]


def test_the_release_body_is_read_out_of_the_release_tree() -> None:
    """The release body says its line numbers refer to the v1.0.0 tree.

    It is the one document in the repository that describes a tree other than
    the one it is read from, and the checker has to say which tree it read
    each citation out of.
    """
    checker = _checker()
    report = checker.check_documents(checker.DOCS)

    trees = {label: citations for label, _documents, citations in report.trees}
    assert trees.get("the v1.0.0 tree"), (
        f"the release body was not read out of the release tree: {report.trees}"
    )
    # The value findings are a separate class: they say what a number in the
    # document states against the number the line holds, and the release
    # body's appendix has some of those. What this test is about is the
    # tree, and a citation that drifted or could not be resolved would say
    # that the tree was read wrong.
    assert not report.drifted, [finding.render() for finding in report.drifted]
    assert not report.unresolved, [finding.render() for finding in report.unresolved]


def test_every_document_that_declares_a_tree_is_one_the_checker_reads() -> None:
    """A declaration nobody checks is a declaration nobody has to keep true."""
    checker = _checker()
    read = {checker.relative_path(document) for document in checker.DOCS if document.is_file()}

    for relative in checker.TREE_DOCUMENTS:
        assert relative in read, f"{relative} declares a tree but the checker never reads it"


def test_the_subject_digest_follows_the_documents_it_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The digest is of what the check was about.

    It is what makes "this verdict was about this subject" a statement that
    can be compared: a document that changes has to change the digest, and a
    check that changed nothing has to leave it alone.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"

    checker = _checker_for(repository, monkeypatch, "v1")
    before = checker.subject_digest([document], {"the v1 tree": checker.Tree("v1")})
    assert before == checker.subject_digest([document], {"the v1 tree": checker.Tree("v1")})

    document.write_text(
        document.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8"
    )
    after = checker.subject_digest([document], {"the v1 tree": checker.Tree("v1")})
    assert after != before


def test_the_round_reports_are_read_out_of_the_trees_they_declare() -> None:
    """The review reports of the November 2026 round declare their anchor tree.

    Each one states, where it sets out its basis, the commit its line numbers
    are anchored to and that tree's measurement fingerprint. The checker has
    to read every one of them out of the tree it declares: read out of the
    working copy, a report's citations fail in both directions at once -- the
    reports drift when the working copy moves, and the drift cannot be told
    from the report's own mistakes.
    """
    checker = _checker()
    names = (
        "outreach-first-read.md",
        "readme-image-consistency.md",
        "case-studies-client-read.md",
        "round-two-fresh-read.md",
        "stale-number-scan-2.md",
        "denominator-and-tree-pass.md",
        "local-vs-ci-gates.md",
        "english-reader-review-2.md",
    )
    documents = [checker.REPO / "docs" / "reports" / name for name in names]
    report = checker.check_documents(documents)

    trees = {label for label, _documents, _citations in report.trees}
    for ref in ("2c456e0", "3ef6676", "48a56b5", "9e1aa61", "d43369b", "ec52527"):
        assert f"the {ref} tree" in trees, (
            f"the {ref} tree was not among the trees the check read against: {sorted(trees)}"
        )
    assert not report.findings, [finding.render() for finding in report.findings]


def test_a_report_citing_another_tree_without_a_declaration_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report whose line numbers are another tree's, and which says nothing
    about that, is checked against the working copy -- and fails there.

    The November round found dozens of citations that were true when written
    and false a commit later, in documents that never said which tree they
    were about. This is the shape of that failure: the checker cannot honour
    a declaration that is not there, so the citation has to hold in the tree
    it is read from or be reported.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"
    # Line 8 held the code in the tagged tree; the working copy has moved on.
    # The report declares no tree, so the citation is read out of the working
    # copy -- where it is out of range.
    document.write_text("The logic lives in `file.py:8`.\n", encoding="utf-8")

    checker = _checker_for(repository, monkeypatch, None)
    report = checker.check_documents([document])
    assert [finding.kind for finding in report.findings] == ["out of range"], [
        finding.render() for finding in report.findings
    ]

    # The same report, now declaring the tree it is about, is read out of it,
    # and the citation holds.
    document.write_text(
        "The logic lives in `file.py:8`.\n\n"
        f"This document describes the tree `sha256:{FAKE_FINGERPRINT}`.\n",
        encoding="utf-8",
    )
    checker = _checker_for(repository, monkeypatch, "v1")
    report = checker.check_documents([document])
    assert not report.findings, [finding.render() for finding in report.findings]


def test_a_report_whose_declaration_quotes_another_tree_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declaration that quotes the wrong tree's fingerprint is a finding.

    The declaration is what ties a report to the tree it describes. A report
    that quotes some other tree's fingerprint has declared a tree it is not
    about, and every line number in it is unverifiable.
    """
    repository = _repository_with_two_trees(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "The logic lives in `file.py:8`.\n\n"
        f"This document describes the tree `sha256:{'cd' * 32}`.\n",
        encoding="utf-8",
    )

    checker = _checker_for(repository, monkeypatch, "v1")
    report = checker.check_documents([document])

    kinds = [finding.kind for finding in report.findings]
    assert "wrong tree" in kinds, [finding.render() for finding in report.findings]


def test_a_tree_whose_measurement_record_is_broken_is_read_as_unreadable() -> None:
    """A record that is not valid JSON must not take the checker down.

    ``tree_fingerprint`` reads the measurement record of a tree, and a record
    that is not valid JSON has to be reported as unreadable. The name it used
    to catch -- ``json.JSONError`` -- does not exist in the ``json`` module,
    so the except clause itself raised ``AttributeError`` and a broken record
    crashed the checker instead of being read as unreadable.
    """
    checker = _checker()

    class BrokenTree:
        """A tree whose measurement record is not valid JSON."""

        def text(self, relative: str) -> str | None:
            return '<!--report-figures:{"source_fingerprint": -->\n'

    assert checker.tree_fingerprint(BrokenTree()) is None


#: The report the release body quotes, as the v1.0.0 tree holds it.
#:
#: The three lines a claim points at are the ones the release body's
#: appendix names, and the three numbers it quotes sit two lines further
#: down: the suite result, the source fingerprint and the fixture count.
REPORT_LINES = [
    "uv sync --extra dev --extra analysis --extra demo",
    "bash scripts/install-backends.sh    # JADX / Apktool",
    "bash scripts/fetch-fixtures.sh      # 两个第三方集成样本",
    "",
    "uv run pytest          # 收集 1712 个：1563 快 + 149 集成",  # noqa: RUF001
    "uv run pytest --cov=dexatlas --cov-report=term",
    "                      # 一方代码覆盖率 93.3%（7157/7671 行）",  # noqa: RUF001
    "                      # 完整环境下的结果：1710 passed + 0 xfailed，1 skipped",  # noqa: RUF001
    "",
    "  },",
    '  "schema": 4,',
    '  "source_fingerprint": "sha256:18f3ab15b40b156110b7e57722427c468290691f31e2be9cd2b3646c74b5b525",',
]


def _repository_with_a_report(tmp_path: Path) -> Path:
    """A repository whose report holds the numbers a document quotes.

    The document is the release body's appendix: a table of "number |
    source", and the source lines it names do not hold the numbers. The
    numbers are two lines further down, which is what the v1.0.0 release
    tree looks like.
    """
    repository = tmp_path / "report-repo"
    repository.mkdir()
    _git(repository, "init", "-q", "-b", "main")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Test")

    record = repository / "docs"
    record.mkdir(parents=True)
    (record / "report.md").write_text("\n".join(REPORT_LINES) + "\n", encoding="utf-8")
    scripts = repository / "scripts"
    scripts.mkdir()
    (scripts / "fetch-fixtures.sh").write_text(
        "\n".join(f"line {number}" for number in range(1, 12))
        + "\n# Only what a test actually reads. Two fixtures were fetched here.\n",
        encoding="utf-8",
    )
    (repository / "doc.md").write_text(
        "| Number in the body | Source |\n"
        "|---|---|\n"
        "| 1694 passed + 0 xfailed + 1 skipped | `docs/report.md:6` |\n"
        "| Source fingerprint `sha256:18f3ab15…` | `docs/report.md:10` |\n"
        "| Two third-party integration fixtures, fetched by "
        "`scripts/fetch-fixtures.sh`, never committed | `docs/report.md:1` |\n",
        encoding="utf-8",
    )
    _git(repository, "add", "-A")
    _git(repository, "commit", "-qm", "the release")
    _git(repository, "tag", "v1")
    return repository


def _value_findings(report) -> list:
    """The findings of the value check."""
    return [finding for finding in report.findings if finding.kind == "value drifted"]


def test_a_value_the_sentence_states_is_compared_with_the_line_it_cites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A number in the sentence is a claim about the cited line.

    The three rows are the ones the v1.0.0 release body's appendix carries
    and the release body got wrong: the suite result, the source fingerprint
    and the fixture count each sit two lines below the line the appendix
    names. The checker has to say so, and to say where the number is.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    checker = _checker_for(repository, monkeypatch, None)

    report = checker.check_documents([document])

    findings = _value_findings(report)
    assert findings, "the value in the sentence was not compared with the cited line"
    details = "\n".join(finding.detail for finding in findings)
    assert "1694 passed" in details
    assert "sha256:18f3ab15" in details
    assert "Two third-party" in details
    # The number is not on the cited line, and the checker says where it is.
    assert "line 8" in details
    assert "line 12" in details
    assert "line 3" in details


def test_a_value_the_cited_line_holds_is_not_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same three rows, pointed at the lines that hold the numbers.

    A check that reports everything is not a check. The rows here are the
    appendix written correctly, and the checker has to stay quiet.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "| Number in the body | Source |\n"
        "|---|---|\n"
        "| 1710 passed + 0 xfailed + 1 skipped | `docs/report.md:8` |\n"
        "| Source fingerprint `sha256:18f3ab15…` | `docs/report.md:12` |\n"
        "| Two third-party integration fixtures, fetched by "
        "`scripts/fetch-fixtures.sh`, never committed | `docs/report.md:3` |\n",
        encoding="utf-8",
    )
    checker = _checker_for(repository, monkeypatch, None)

    report = checker.check_documents([document])

    assert not _value_findings(report), "the value was reported where it holds"


def test_a_claim_that_states_no_value_is_not_compared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentence that only says where the thing lives cannot be checked.

    There is nothing in the sentence to check the line against, so the
    citation gets the location check and nothing more.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    document.write_text("The reproduction steps live in `docs/report.md:6`.\n", encoding="utf-8")
    checker = _checker_for(repository, monkeypatch, None)

    report = checker.check_documents([document])

    assert not _value_findings(report)


def test_a_number_that_is_not_a_measurement_is_not_compared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The numbers a sentence uses for other things are not claims.

    A row numbered ``1``, a status code, a limit, a version and a
    quotation are all numbers, and none of them is a measurement the cited
    line is supposed to carry.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "| # | claim | source |\n"
        "|---|---|---|\n"
        "| 1 | `docs/report.md:6` | a row number |\n"
        "| 2 | 200 / 404 (`docs/report.md:6`) | status codes |\n"
        "| 3 | at least 16/20 per round (`docs/report.md:6`) | a limit |\n"
        "| 4 | version 2.11.1 (`docs/report.md:6`) | a version |\n"
        "| 5 | 「1710 passed」 (`docs/report.md:6`) | a quotation |\n",
        encoding="utf-8",
    )
    checker = _checker_for(repository, monkeypatch, None)

    report = checker.check_documents([document])

    assert not _value_findings(report), "a number that is not a measurement was compared"


def test_a_citation_that_names_a_symbol_is_not_compared_with_a_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A number beside a symbol counts what the symbol holds.

    "28 checks in ``_rest_requests()``" is a claim about the function, and
    the checker already compares the function against the cited lines. The
    number is not a number the line has to carry.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "The 1710 checks are in `fetch_fixtures()` (`docs/report.md:6`).\n",
        encoding="utf-8",
    )
    checker = _checker_for(repository, monkeypatch, None)

    report = checker.check_documents([document])

    assert not _value_findings(report), "a number beside a symbol was compared"


def test_the_value_is_read_out_of_the_tree_the_document_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The number is compared with the tree the document is about.

    The release body says its line numbers refer to the release tree, so
    the number is read out of that tree and not out of the working copy.
    A checker that read the working copy would report a drift where the
    document is right.
    """
    repository = _repository_with_a_report(tmp_path)
    document = repository / "doc.md"
    document.write_text(
        "| Number in the body | Source |\n"
        "|---|---|\n"
        "| 1710 passed + 0 xfailed + 1 skipped | `docs/report.md:8` |\n"
        "| Source fingerprint `sha256:18f3ab15…` | `docs/report.md:12` |\n",
        encoding="utf-8",
    )
    _git(repository, "add", "-A")
    _git(repository, "commit", "-qm", "the rows")
    _git(repository, "tag", "-f", "v2")
    # The working copy moves on and the numbers change with it.
    (repository / "docs" / "report.md").write_text(
        "\n".join("the working copy moved on" for _ in range(12)) + "\n", encoding="utf-8"
    )
    _git(repository, "commit", "-qam", "the tree moved on")

    checker = _checker_for(repository, monkeypatch, "v2")
    report = checker.check_documents([document])
    assert not _value_findings(report), "the number was read out of the working copy"

    checker = _checker_for(repository, monkeypatch, None)
    report = checker.check_documents([document])
    assert _value_findings(report), "the number was not compared with the working copy"


def test_the_value_findings_are_reported_and_do_not_fail_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The value findings are printed, and the exit code is still the answer.

    A number in a document is a snapshot of a measurement, and a
    measurement writes new numbers every time it runs. The outward texts
    are refreshed by hand after it, and that refresh is the release
    session's work. What the checker owes it is the two numbers side by
    side; the exit code still belongs to the citations that name a symbol.
    """
    repository = _repository_with_a_report(tmp_path)
    checker = _checker_for(repository, monkeypatch, None)
    monkeypatch.setattr(checker, "DOCS", [repository / "doc.md"])

    code = checker.main()
    written = capsys.readouterr().out

    assert "values not matching:" in written
    assert "1694 passed" in written
    assert code == 0, f"the value findings failed the check:\n{written}"
