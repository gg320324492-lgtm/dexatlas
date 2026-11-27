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

Which release the gate is about
-------------------------------
That is a third thing, and it is easy to get wrong in a way nothing else
in the report would show. The gate used to name one release in the script
and check that one forever: after v1.1.0 and v1.2.0 had shipped, the CI
job still reported on v1.0.0, and its green verdict read as a verdict on
the release that had just gone out. A gate that checks the past is not a
gate that is wrong -- it is a gate that says nothing about the thing the
reader is asking about.

So the release is resolved, and when it cannot be resolved the gate says
so rather than checking some other release.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-release-numbers.py"


def _figures(
    total: int,
    fast: int,
    slow: int,
    passed: int,
    skipped: int,
    coverage: str,
    covered: int,
) -> dict[str, str]:
    """The figures a report records for one measurement."""
    return {
        "tests.total": str(total),
        "tests.fast": str(fast),
        "tests.slow": str(slow),
        "suite.passed": str(passed),
        "suite.skipped": str(skipped),
        "suite.xfailed": "0",
        "coverage.pct": coverage,
        "coverage.covered": str(covered),
        "coverage.total": "1000",
    }


def _numbers(
    total: int,
    fast: int,
    slow: int,
    passed: int,
    skipped: int,
    coverage: str,
    covered: int,
) -> dict[str, str]:
    """The numbers an outward text states, read out of a figure set."""
    return {
        "total": str(total),
        "fast": str(fast),
        "slow": str(slow),
        "passed": str(passed),
        "skipped": str(skipped),
        "coverage": coverage,
        "covered": str(covered),
        "lines": "1000",
    }


@dataclass(frozen=True)
class Release:
    """One release, as the repository records it."""

    tag: str
    figures: dict[str, str]
    numbers: dict[str, str]


#: The report the release shipped with, in the tagged tree.
TAG_FIGURES = _figures(100, 90, 10, 98, 2, "91.0%", 900)

#: The numbers the outward texts state, read out of a figure set.
TAG_NUMBERS = _numbers(100, 90, 10, 98, 2, "91.0%", 900)

#: The report of the working copy, measured again for the next version.
WORKING_FIGURES = _figures(200, 180, 20, 198, 2, "92.0%", 920)

WORKING_NUMBERS = _numbers(200, 180, 20, 198, 2, "92.0%", 920)

#: A release before the newest one, with numbers of its own.
V1_9 = Release(
    "v1.9.0",
    _figures(90, 80, 10, 88, 2, "90.0%", 880),
    _numbers(90, 80, 10, 88, 2, "90.0%", 880),
)

#: The newest release in these tests. It is newer than v1.9.0, and git
#: lists the two in the other order -- which is the point of it.
V1_10 = Release(
    "v1.10.0",
    _figures(150, 135, 15, 148, 2, "91.5%", 950),
    _numbers(150, 135, 15, 148, 2, "91.5%", 950),
)


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


def _release_documents(repository: Path, release: Release) -> None:
    """The documents a release ships: its notes and its release body."""
    _write(repository / "docs" / "releases" / f"{release.tag}.md", _text(release.numbers))
    _write(
        repository / "docs" / "reports" / f"{release.tag}-github-release-body.md",
        _body(release.numbers),
    )


def _repository(tmp_path: Path, releases: tuple[Release, ...] = ()) -> Path:
    """A checkout with two trees: the tag that shipped, and a copy measured later.

    ``releases`` adds more releases to the checkout, each with its own tag
    and its own numbers. They are committed one after another, so that git
    lists the tags in the order they were cut -- which is not the order of
    the versions.
    """
    repository = tmp_path / "repository"
    repository.mkdir()

    everything = (*releases, Release("v1.0.0", TAG_FIGURES, TAG_NUMBERS))

    # The first release is the one this test has always been about.
    first = everything[0]
    _write(
        repository / "docs" / "reports" / "phase1-execution-report.md",
        _report(first.figures),
    )
    _write(repository / "docs" / "how-to-verify.md", _page(first.numbers, first.numbers))
    _write(repository / "docs" / "how-to-verify.zh-CN.md", _page_cn(first.numbers, first.numbers))
    _release_documents(repository, first)
    _git(repository, "init", "-q")
    _git(repository, "add", "-A")
    _commit(repository, f"the {first.tag} release")
    _git(repository, "tag", first.tag)

    # The other releases ship their own trees, each with its own numbers.
    for release in everything[1:]:
        _write(
            repository / "docs" / "reports" / "phase1-execution-report.md",
            _report(release.figures),
        )
        _write(
            repository / "docs" / "how-to-verify.md",
            _page(release.numbers, first.numbers),
        )
        _write(
            repository / "docs" / "how-to-verify.zh-CN.md",
            _page_cn(release.numbers, first.numbers),
        )
        _release_documents(repository, release)
        _git(repository, "add", "-A")
        _commit(repository, f"the {release.tag} release")
        _git(repository, "tag", release.tag)

    # The working copy is measured again, for the next version.
    #
    # The pages that describe the tree you are standing on are re-synced --
    # they are about the working copy. The documents of the releases that
    # shipped are not: a release is frozen, its tag is not cut again, and
    # their numbers belong to the tree it shipped with.
    _write(
        repository / "docs" / "reports" / "phase1-execution-report.md",
        _report(WORKING_FIGURES),
    )
    _write(repository / "docs" / "how-to-verify.md", _page(WORKING_NUMBERS, first.numbers))
    _write(repository / "docs" / "how-to-verify.zh-CN.md", _page_cn(WORKING_NUMBERS, first.numbers))
    _release_documents(repository, first)
    for release in everything[1:]:
        _release_documents(repository, release)
    _git(repository, "add", "-A")
    _commit(repository, "the next measurement")
    return repository


def _attribute(module: object, name: str):
    """An attribute of the module under test, or None when it has none.

    The gate used to take a plain ``(body, reason)`` pair and now takes a
    value that says which of three things happened. The readers below answer
    in whichever shape the module understands, so that taking the fix away
    shows up as the wrong *answer* -- the gate checking the wrong release,
    or not saying what it did not check -- and not as an ``AttributeError``
    in the setup: a test that fails in the setup proves nothing about the
    behaviour.
    """
    return getattr(module, name, None)


def _reader(module: object, bodies: dict[str, str], state: str = "PUBLISHED"):
    """A reader that answers for each release by its tag.

    The gate asks for one release at a time, and the answer has to be that
    release's own numbers: a reader that answered every tag with the same
    body would let a gate that checked the wrong release pass.

    A tag with no body in the map is answered as "not published yet" -- the
    state a tag push finds when the release has not gone out. ``state``
    names the other state a reader can be in: "UNREADABLE" for a body that
    cannot be read at all.
    """
    published = _attribute(module, "Published")

    def read(tag: str, repo: str = "") -> object:
        if published is None:
            body = bodies.get(tag)
            if body is None:
                return None, f"there is no published release for {tag} yet"
            return body, ""
        if state == "UNREADABLE":
            return published(None, "gh is not installed", _attribute(module, "UNREADABLE"))
        body = bodies.get(tag)
        if body is None:
            return published(
                None,
                f"there is no published release for {tag} yet",
                _attribute(module, "NOT_PUBLISHED"),
            )
        return published(body, "", _attribute(module, "PUBLISHED"))

    return read


@pytest.fixture
def checker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[object, Path]:
    """The checker, pointed at a repository of this test's own."""
    module = _checker()
    repository = _repository(tmp_path)
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    # The body published for v1.0.0 says the numbers v1.0.0 shipped with.
    # It was published once; re-publishing it is a release action, and the
    # gate only reads it.
    monkeypatch.setattr(module, "published_body", _reader(module, {"v1.0.0": _text(TAG_NUMBERS)}))
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
    monkeypatch.setattr(module, "published_body", _reader(module, {"v1.0.0": wrong}))

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

    The message names the release it could not check. A message that only
    said "the body could not be read" would leave the reader to guess which
    release was missing -- and the gate that has just started checking
    several releases is exactly the one whose reader needs to be told.
    """
    module, _ = checker
    monkeypatch.setattr(module, "published_body", _reader(module, {}, state="UNREADABLE"))

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 2, written
    assert "the published release body of v1.0.0 could not be read" in written
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


def test_the_gate_checks_the_newest_release_and_not_a_named_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The gate checks the release that is newest, not one the script names.

    The script used to carry the name of a release in its argument parser --
    ``default="v1.0.0"`` -- and every run without ``--tag`` checked that one
    release. After v1.1.0 and v1.2.0 had shipped, the CI job was still
    reporting on v1.0.0: it went on checking the past, and its green verdict
    read as a verdict on the release that had just gone out.

    So the default is the newest release tag in the checkout. The repository
    here has three, and the newest of them is not the one git lists last:
    ``v1.10.0`` is newer than ``v1.9.0`` even though it sorts before it as
    a string.
    """
    module = _checker()
    repository = _repository(tmp_path, releases=(V1_9, V1_10))
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    monkeypatch.setattr(
        module,
        "published_body",
        _reader(module, {r.tag: _text(r.numbers) for r in (V1_9, V1_10)}),
    )
    reader = getattr(module, "citation_checker", None)
    if reader is not None:
        monkeypatch.setattr(reader(), "REPO", repository)

    code = module.main([])
    written = capsys.readouterr().out

    assert code == 0, written
    assert "release: v1.10.0" in written
    assert "the v1.10.0 tree" in written
    # Not the oldest, and not the one git happens to list last.
    assert "the v1.9.0 tree" not in written
    assert "the v1.0.0 tree" not in written


def test_the_release_the_gate_names_is_the_one_it_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--tag`` picks the release, and the output says which one it picked.

    A tag push has to check the tag that was pushed -- the release that is
    being published -- rather than whichever release the repository happens
    to have newest. And a reader has to be able to see which release the
    verdict is about, because a verdict about the wrong release reads like a
    verdict about the right one.
    """
    module = _checker()
    repository = _repository(tmp_path, releases=(V1_9, V1_10))
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    monkeypatch.setattr(
        module,
        "published_body",
        _reader(module, {r.tag: _text(r.numbers) for r in (V1_9, V1_10)}),
    )
    reader = getattr(module, "citation_checker", None)
    if reader is not None:
        monkeypatch.setattr(reader(), "REPO", repository)

    code = module.main(["--tag", "v1.9.0"])
    written = capsys.readouterr().out

    assert code == 0, written
    assert "release: v1.9.0" in written
    assert "the v1.9.0 tree" in written
    assert "the v1.10.0 tree" not in written


def test_a_run_with_no_release_says_that_no_release_was_checked(
    checker: tuple[object, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A pull request publishes no release, and the gate says so.

    A pull request cuts no tag and publishes no release body. The gate
    checks the working copy -- that part is worth doing -- and says that
    the published release was not checked, and why.

    What it must not do is check some other release's body and report it as
    if it were this one's. The checker's exit code would be about a release
    the pull request has nothing to do with.
    """
    module, _ = checker

    code = module.main(["--no-release", "a pull request publishes no release body"])
    written = capsys.readouterr().out

    assert code == 0, written
    assert "the published release was NOT checked" in written
    assert "a pull request publishes no release body" in written
    # No release segment at all: nothing in the output can be read as a
    # check of a release.
    assert "the published release" not in written.replace(
        "the published release was NOT checked", ""
    )
    # The working copy was still checked.
    assert "segment: the working copy" in written


def test_a_release_that_is_not_published_yet_is_not_a_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A release that is not out yet is the ordinary state of a tag push.

    The CI of a tag runs before the release is published -- on v1.2.0 the
    job finished at 04:18:18Z and the release was published at 04:26:58Z.
    So a missing published body on a tag push is not a fault, and the gate
    must not go red over it.

    It must also not go quiet: the release was not checked, and the output
    says which one.
    """
    module = _checker()
    repository = _repository(tmp_path, releases=(V1_10,))
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    reader = getattr(module, "citation_checker", None)
    if reader is not None:
        monkeypatch.setattr(reader(), "REPO", repository)

    monkeypatch.setattr(module, "published_body", _reader(module, {}))

    code = module.main(["--tag", "v1.10.0", "--expect-unpublished"])
    written = capsys.readouterr().out

    assert code == 0, written
    assert "NOT PUBLISHED YET" in written
    assert "v1.10.0" in written


def test_a_release_that_is_not_published_yet_is_incomplete_without_the_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without the flag, a missing published body is an incomplete check.

    The flag says "this run expects the release to be unpublished". A run
    that was told nothing of the kind, and finds no published body for the
    release it was asked about, has not checked it -- and the exit code
    says so rather than reporting a green agreement it did not reach.
    """
    module = _checker()
    repository = _repository(tmp_path, releases=(V1_10,))
    monkeypatch.setattr(module, "REPO_ROOT", repository)
    reader = getattr(module, "citation_checker", None)
    if reader is not None:
        monkeypatch.setattr(reader(), "REPO", repository)

    monkeypatch.setattr(module, "published_body", _reader(module, {}))

    code = module.main(["--tag", "v1.10.0"])
    written = capsys.readouterr().out

    assert code == 2, written
    assert "was not published yet" in written
    assert "v1.10.0" in written
