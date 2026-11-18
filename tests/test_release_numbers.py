"""The outward texts have to agree with the numbers of the tree they describe.

The execution report is the authority for the numbers of a release, and four
documents repeat them by hand. The check that they agree lives in
``scripts/check-release-numbers.py``, so that it can also be run by hand when
one of them is edited. These tests call that script's ``main()`` rather than
repeating its rules: a checker that is written twice is two checkers, and
only one of them is ever fixed.

There are two comparisons, and they are about two different trees.

* The **working copy**: the four texts in this checkout, against the report
  in this checkout.
* The **published release**: the release body published on GitHub, against
  the report **in the tagged tree** -- the tree the release actually
  shipped.

The second one is the one that is easy to get wrong. The working copy's
report is re-measured as soon as the next version starts, and a report that
says "200 tests" says nothing about the release that shipped "100". A gate
that compared the published body of v1.0.0 against a measurement taken after
v1.1.0 began would go red for a reason that has nothing to do with the
release, and a gate that goes red for the wrong reason is a gate that gets
turned off.

The repository these tests build has both trees in it: a tag whose report
records the numbers the release shipped with, and a working copy that was
measured again afterwards.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-release-numbers.py"

#: The report the release shipped with, in the tagged tree.
TAG_FIGURES = {
    "tests.total": "100",
    "tests.fast": "90",
    "tests.slow": "10",
    "suite.passed": "98",
    "suite.skipped": "2",
    "suite.xfailed": "0",
    "coverage.pct": "91.0%",
    "coverage.covered": "900",
    "coverage.total": "1000",
}

#: The report of the working copy, measured again for the next version.
WORKING_FIGURES = {
    "tests.total": "200",
    "tests.fast": "180",
    "tests.slow": "20",
    "suite.passed": "198",
    "suite.skipped": "2",
    "suite.xfailed": "0",
    "coverage.pct": "92.0%",
    "coverage.covered": "920",
    "coverage.total": "1000",
}

#: The numbers the outward texts state, read out of a figure set.
TAG_NUMBERS = {
    "total": "100",
    "fast": "90",
    "slow": "10",
    "passed": "98",
    "skipped": "2",
    "coverage": "91.0%",
    "covered": "900",
    "lines": "1000",
}

WORKING_NUMBERS = {
    "total": "200",
    "fast": "180",
    "slow": "20",
    "passed": "198",
    "skipped": "2",
    "coverage": "92.0%",
    "covered": "920",
    "lines": "1000",
}


def _checker():
    """Load the checker as a module, the way the suite loads the other gates."""
    spec = importlib.util.spec_from_file_location("dexatlas_release_numbers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repository: Path, message: str) -> None:
    _git(
        repository,
        "-c",
        "user.name=DexAtlas Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        message,
    )


def _report(figures: dict[str, str]) -> str:
    """A report that records the figures, the way the generated one does."""
    lines = ["# Phase 1 execution report", ""]
    for key, value in figures.items():
        lines.append(f"<!--fig:{key}-->{value}<!--/fig-->")
    return "\n".join(lines) + "\n"


def _text(numbers: dict[str, str]) -> str:
    """An outward text that states the numbers the way the real ones do."""
    return (
        "# The release\n"
        "\n"
        f"The suite has {numbers['total']} tests "
        f"({numbers['fast']} fast + {numbers['slow']} integration).\n"
        "\n"
        "| run | result |\n"
        "|---|---|\n"
        f"| the whole suite | {numbers['passed']} passed, {numbers['skipped']} skipped |\n"
        "\n"
        f"The coverage is {numbers['coverage']} "
        f"({numbers['covered']} / {numbers['lines']} lines).\n"
    )


def _text_cn(numbers: dict[str, str]) -> str:
    """The same text, in Chinese.

    The fullwidth parentheses are written as escapes: ``ruff``'s RUF001 reads
    them as ASCII punctuation, and the checker under test matches the
    fullwidth ones.
    """
    return (
        "# 这个版本\n"
        "\n"
        f"当前这棵树上应当是 {numbers['total']}"
        f"\uff08{numbers['fast']} 快 + {numbers['slow']} 集成\uff09。\n"
        "\n"
        "| 跑的是什么 | 结果 |\n"
        "|---|---|\n"
        f"| 整个套件 | {numbers['passed']} passed, {numbers['skipped']} skipped |\n"
        "\n"
        f"覆盖率是 {numbers['coverage']}"
        f"\uff08{numbers['covered']} / {numbers['lines']} 行\uff09。\n"
    )


def _page(numbers: dict[str, str], illustrated: dict[str, str]) -> str:
    """A how-to page: the numbers in prose, and two illustrations of a marker.

    The illustrations are what the pages that teach the reader what a
    generated marker looks like carry: one in a fenced code block, one in an
    inline code span. Their numbers are not the numbers of this tree -- the
    pages keep the marker they were written with -- and they are not claims.
    """
    return (
        _text(numbers)
        + "\n"
        + "## Which numbers are generated\n"
        + "\n"
        + "They look like this in the source file:\n"
        + "\n"
        + "```text\n"
        + f"<!--fig:tests.total-->{illustrated['total']}<!--/fig-->\n"
        + "```\n"
        + "\n"
        + f"And inline: `<!--fig:tests.total-->{illustrated['total']}<!--/fig-->`.\n"
    )


def _page_cn(numbers: dict[str, str], illustrated: dict[str, str]) -> str:
    """The same page, in Chinese."""
    return (
        _text_cn(numbers)
        + "\n"
        + "## 哪些数是生成物\n"
        + "\n"
        + "在源文件里长这样\uff1a\n"
        + "\n"
        + "```text\n"
        + f"<!--fig:tests.total-->{illustrated['total']}<!--/fig-->\n"
        + "```\n"
        + "\n"
        + f"行内的是\uff1a`<!--fig:tests.total-->{illustrated['total']}<!--/fig-->`。\n"
    )


def _body(numbers: dict[str, str]) -> str:
    """The source of a release body: the text, and the appendix that is not published."""
    return (
        _text(numbers) + "\n" + "## Appendix\n"
        "\n"
        "| number | where it came from |\n"
        "|---|---|\n"
        "| the suite | the measurement |\n"
    )


def _repository(tmp_path: Path) -> Path:
    """A checkout with two trees: the tag that shipped, and a copy measured later."""
    repository = tmp_path / "repository"
    repository.mkdir()

    _write(
        repository / "docs" / "reports" / "phase1-execution-report.md",
        _report(TAG_FIGURES),
    )
    _write(repository / "docs" / "how-to-verify.md", _page(TAG_NUMBERS, TAG_NUMBERS))
    _write(repository / "docs" / "how-to-verify.zh-CN.md", _page_cn(TAG_NUMBERS, TAG_NUMBERS))
    _write(repository / "docs" / "releases" / "v1.0.0.md", _text(TAG_NUMBERS))
    _write(
        repository / "docs" / "reports" / "v1.0.0-github-release-body.md",
        _body(TAG_NUMBERS),
    )
    _git(repository, "init", "-q")
    _git(repository, "add", "-A")
    _commit(repository, "the v1.0.0 release")
    _git(repository, "tag", "v1.0.0")

    # The working copy is measured again, for the next version.
    #
    # The pages that describe the tree you are standing on are re-synced --
    # they are about the working copy. The documents of the release that
    # shipped are not: that release is frozen, its tag is not cut again,
    # and their numbers belong to the tree it shipped with.
    _write(
        repository / "docs" / "reports" / "phase1-execution-report.md",
        _report(WORKING_FIGURES),
    )
    _write(repository / "docs" / "how-to-verify.md", _page(WORKING_NUMBERS, TAG_NUMBERS))
    _write(repository / "docs" / "how-to-verify.zh-CN.md", _page_cn(WORKING_NUMBERS, TAG_NUMBERS))
    _write(repository / "docs" / "releases" / "v1.0.0.md", _text(TAG_NUMBERS))
    _write(
        repository / "docs" / "reports" / "v1.0.0-github-release-body.md",
        _body(TAG_NUMBERS),
    )
    _git(repository, "add", "-A")
    _commit(repository, "the next measurement")
    return repository


def _published(tag: str, repo: str = "") -> tuple[str | None, str]:
    """The release body as it was published, without reaching for the network.

    The body published for v1.0.0 says the numbers v1.0.0 shipped with. It
    was published once; re-publishing it is a release action, and the gate
    only reads it.
    """
    return _text(TAG_NUMBERS), ""


@pytest.fixture
def checker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[object, Path]:
    """The checker, pointed at a repository of this test's own."""
    module = _checker()
    repository = _repository(tmp_path)
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    monkeypatch.setattr(module, "published_body", _published)
    # The citation checker reads a tree with ``git show``, and it runs git in
    # its own root. That root is the repository this test built.
    #
    # The reader is looked up rather than named: an implementation that has
    # no tree reader has to fail on the assertions below and not in the
    # setup, so that taking the fix away shows up as the wrong answer and
    # not as a missing attribute.
    reader = getattr(module, "citation_checker", None)
    if reader is not None:
        monkeypatch.setattr(reader(), "REPO", repository)
    return module, repository


def _mismatches(written: str) -> str:
    """The findings the report prints under "mismatches"."""
    _, marker, rest = written.partition("\nmismatches\n")
    assert marker, f"the report printed no mismatches section:\n{written}"
    return rest.split("\nnot written\n")[0]


def _line_of(text: str, needle: str) -> int:
    """The 1-based line a string is on."""
    for number, line in enumerate(text.split("\n"), 1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} is not in the text:\n{text}")


def test_the_checker_exists() -> None:
    assert SCRIPT.is_file(), "scripts/check-release-numbers.py is missing"


def test_the_published_body_is_compared_against_the_tree_it_shipped(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """The published body is checked against the tagged tree, not the working copy.

    The working copy of this repository has been measured again: its report
    says 200 tests. The release body published for v1.0.0 says the 100 tests
    v1.0.0 shipped with, and it is right -- so the gate has to be green.

    A gate that compared that body with the working copy's measurement would
    go red here, and it would be red for a reason that has nothing to do
    with the release.
    """
    module, _ = checker

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 0, f"the checker found a difference:\n{written}"
    assert "the v1.0.0 tree" in written
    assert "mismatches: 0" in written


def test_a_number_illustrated_in_a_code_block_is_not_a_claim(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A marker that shows the reader what a marker looks like is not a claim.

    The page that teaches the reader what a generated marker looks like
    holds one, in a fenced code block and in an inline code span. Its
    number is the one the page was written with; it is not a number about
    this tree, and the measurement script will not write a number into it
    either. Reading it as a claim turns the page red for a number nobody
    wrote -- and the number goes stale every time the tree is measured
    again.
    """
    module, repository = checker

    page = (repository / "docs" / "how-to-verify.md").read_text(encoding="utf-8")
    assert "<!--fig:tests.total-->100<!--/fig-->" in page, (
        "the page has to carry the illustration for this to mean anything"
    )

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 0, f"the checker found a difference:\n{written}"
    assert "MISMATCH" not in written
    # The illustration is a marker of the release's numbers, not of the
    # working copy's: the working copy says 200.
    assert "tests.total      200" in written


def test_the_release_documents_are_compared_against_the_tag_tree(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """The release notes and the release body belong to the release that shipped.

    They say what v1.0.0 measured. v1.0.0 is frozen -- its tag is not cut
    again -- so their numbers belong to the tree that tag points at, and to
    nothing measured since. The working copy's report has moved on, and
    comparing these two documents against it says they are wrong when they
    are right.
    """
    module, repository = checker

    notes = (repository / "docs" / "releases" / "v1.0.0.md").read_text(encoding="utf-8")
    assert "100 tests" in notes, "the release notes state the numbers v1.0.0 shipped with"

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 0, f"the checker found a difference:\n{written}"
    assert "MISMATCH" not in written
    # Both documents are in the published segment, and that segment is
    # compared against the tagged tree's report.
    assert "segment: the published release v1.0.0" in written
    assert "docs/releases/v1.0.0.md" in written
    assert "docs/reports/v1.0.0-github-release-body.md" in written


def test_a_mismatch_names_the_text_the_number_the_report_and_the_line(
    checker: tuple[object, Path],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A number that does not match is reported with everything needed to fix it.

    Which text, which number, what the report says, what the text says, and
    which line: five things. A checker that only says "inconsistent" leaves
    the reader to find all five on their own.

    The published body is the one that is wrong here, so this also says which
    tree's numbers it is compared against: the tagged tree says 98, and the
    working copy says 198.
    """
    module, _ = checker
    wrong = _text(TAG_NUMBERS | {"passed": "96"})
    monkeypatch.setattr(module, "published_body", lambda tag, repo="": (wrong, ""))

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 1, f"the checker did not go red:\n{written}"
    findings = _mismatches(written)
    assert "GitHub release v1.0.0 (published body)" in findings
    assert "suite.passed" in findings
    # The number of the tagged tree, the tree the release shipped with.
    assert "report: 98" in findings
    assert "this text: 96" in findings
    assert f"(line {_line_of(wrong, '96 passed')})" in findings


def test_the_two_comparisons_are_reported_separately(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader has to be able to tell the two comparisons apart.

    They are two claims about two different trees, and a finding that does
    not say which one it belongs to cannot be acted on.
    """
    module, _ = checker

    module.main([])
    written = capsys.readouterr().out

    assert "segment: the working copy" in written
    assert "segment: the published release v1.0.0" in written
    assert "docs/reports/phase1-execution-report.md (the working copy)" in written
    assert "docs/reports/phase1-execution-report.md (the v1.0.0 tree)" in written


def test_a_published_body_that_cannot_be_read_is_not_an_agreement(
    checker: tuple[object, Path],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A body that cannot be read is reported as not read, not as agreement.

    The fourth text was not checked. That is not the same as the fourth text
    being right, and the exit code says so.
    """
    module, _ = checker
    monkeypatch.setattr(
        module, "published_body", lambda tag, repo="": (None, "gh is not installed")
    )

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 2, written
    assert "the published release body could not be read" in written
    assert "gh is not installed" in written


def test_a_tag_that_is_not_in_the_checkout_is_not_an_agreement(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A tagged tree that cannot be read leaves the second comparison incomplete."""
    module, _ = checker

    code = module.main(["--tag", "v9.9.9"])
    written = capsys.readouterr().out

    assert code == 2, written
    assert "the v9.9.9 tree could not be read" in written
    assert "not in this checkout" in written
