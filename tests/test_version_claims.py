"""The documentation's version claims have to match the repository.

``scripts/check-doc-citations.py`` proves that a ``file:line`` citation still
points at what it names. It cannot prove that "the newest tag is v0.1.2" is
true, because a version is not a line number — and a sentence like that is
exactly how this project has ended up describing a release state that had
already moved on.

The checker in ``scripts/check-version-claims.py`` reads the facts out of the
repository — the tags, the package version, the changelog — and compares them
with what the documents say. These tests feed it fixture text rather than the
real documents: the real ones are being edited, and a test that fails because
somebody fixed a sentence is a test that cannot be trusted to fail when a
sentence is wrong.

Two of the tests below build a repository of their own and run the checker
against it end to end. The rest read the checker as a module, so that a rule
can be broken and the test that pins it turns red.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-version-claims.py"


def _checker() -> ModuleType:
    """Load the checker as a module, the way the suite loads the other scripts."""
    spec = importlib.util.spec_from_file_location("dexatlas_version_claims", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _facts(checker: ModuleType, **overrides: object) -> object:
    """The facts of a repository that has released v0.1.3."""
    values: dict[str, object] = {
        "tags": ("v0.1.0", "v0.1.1", "v0.1.2", "v0.1.3"),
        "versions": frozenset({"0.1.0", "0.1.1", "0.1.2", "0.1.3"}),
        "newest_tag": "0.1.3",
        "package_version": "0.1.3",
        "changelog_versions": ("0.1.3", "0.1.2", "0.1.1", "0.1.0"),
        "changelog_newest": "0.1.3",
        "unreleased_link": "0.1.3",
    }
    values.update(overrides)
    return checker.Facts(**values)  # type: ignore[arg-type]


def _claims(checker: ModuleType, text: str, facts: object | None = None) -> list[object]:
    """The claims the checker finds in a piece of text."""
    return checker.check_text("docs/example.md", text, facts or _facts(checker))


def _kinds(claims: list[object]) -> list[str]:
    return [claim.kind for claim in claims]  # type: ignore[attr-defined]


# -- the script ------------------------------------------------------------


def test_the_version_claim_checker_exists() -> None:
    assert SCRIPT.is_file(), "scripts/check-version-claims.py is missing"


def test_the_checker_has_a_main_that_runs() -> None:
    """The script has to be runnable on its own: ``uv run python scripts/...``."""
    checker = _checker()
    assert callable(checker.main)


# -- "X has been released" -------------------------------------------------


def test_a_released_version_that_is_tagged_is_not_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "v0.1.3 已发布: https://example.com/releases/tag/v0.1.3")
    assert claims == []


def test_a_released_version_without_a_tag_is_a_finding() -> None:
    """A release that does not exist is a claim about nothing."""
    checker = _checker()
    claims = _claims(checker, "v0.1.4 已发布: https://example.com/releases/tag/v0.1.4")
    assert _kinds(claims) == ["released"]
    assert "v0.1.4" in claims[0].message  # type: ignore[attr-defined]


def test_a_release_being_prepared_may_be_called_released() -> None:
    """The release is in the changelog and the tag is a moment behind.

    That is what the tree looks like between "prepare the release" and the
    tag being pushed, and it is not a lie.
    """
    checker = _checker()
    facts = _facts(
        checker,
        versions=frozenset({"0.1.0", "0.1.1", "0.1.2"}),
        newest_tag="0.1.2",
        changelog_versions=("0.1.3", "0.1.2", "0.1.1", "0.1.0"),
        changelog_newest="0.1.3",
        unreleased_link="0.1.3",
    )
    claims = _claims(checker, "v0.1.3 已发布", facts)
    assert claims == []


# -- "X has not been released" ---------------------------------------------


def test_an_unreleased_version_that_is_tagged_is_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "v0.1.2 尚未发布")
    assert _kinds(claims) == ["unreleased"]


def test_a_version_that_was_never_released_may_be_called_unreleased() -> None:
    checker = _checker()
    claims = _claims(checker, "v0.2.0 尚未发布")
    assert claims == []


def test_work_after_the_newest_release_may_be_called_unreleased() -> None:
    """The claim is about the work since v0.1.3, and v0.1.3 is the newest."""
    checker = _checker()
    claims = _claims(checker, "### 3.11 修复（v0.1.3 之后修复，待发布）")  # noqa: RUF001
    assert claims == []


def test_work_after_an_older_release_may_not_be_called_unreleased() -> None:
    """The claim is only true while that release is the last one."""
    checker = _checker()
    claims = _claims(checker, "### 3.11 修复（v0.1.2 之后修复，待发布）")  # noqa: RUF001
    assert _kinds(claims) == ["stale-anchor"]


def test_the_anchor_is_checked_against_the_newest_tag_not_the_newest_changelog() -> None:
    """While a release is being prepared, the newest *tag* is still the old one."""
    checker = _checker()
    facts = _facts(
        checker,
        versions=frozenset({"0.1.0", "0.1.1", "0.1.2"}),
        newest_tag="0.1.2",
        changelog_versions=("0.1.3", "0.1.2", "0.1.1", "0.1.0"),
        changelog_newest="0.1.3",
        unreleased_link="0.1.3",
    )
    claims = _claims(checker, "（v0.1.2 之后修复，待发布）", facts)  # noqa: RUF001
    assert claims == []


# -- "the newest version is X" --------------------------------------------


def test_the_newest_version_may_be_the_newest_tag() -> None:
    checker = _checker()
    claims = _claims(checker, "仓库里目前最新的 tag 是 `v0.1.3`")
    assert claims == []


def test_a_newest_version_that_is_not_the_newest_tag_is_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "仓库里目前最新的 tag 是 `v0.1.2`")
    assert _kinds(claims) == ["latest"]


def test_the_newest_version_frame_needs_a_copula() -> None:
    """ "the current work backlog" is not a claim about a version."""
    checker = _checker()
    claims = _claims(checker, "Start with the `v0.1.0` milestone; the issues are the current work")
    assert claims == []


def test_the_newest_release_may_be_the_release_being_prepared() -> None:
    checker = _checker()
    facts = _facts(
        checker,
        versions=frozenset({"0.1.0", "0.1.1", "0.1.2"}),
        newest_tag="0.1.2",
        changelog_versions=("0.1.3", "0.1.2", "0.1.1", "0.1.0"),
        changelog_newest="0.1.3",
        unreleased_link="0.1.3",
    )
    claims = _claims(checker, "最新版本是 v0.1.3", facts)
    assert claims == []


def test_the_newest_without_a_noun_is_a_finding() -> None:
    """ "最新的是 v0.1.2" names a version and says it is the newest one.

    There is no noun, so there is no way to tell a claim about the newest
    tag from a claim about the newest release — and the number is wrong
    under both readings.
    """
    checker = _checker()
    claims = _claims(checker, "最新的是 v0.1.2")
    assert _kinds(claims) == ["latest"]


def test_the_newest_without_a_noun_in_english_is_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "the latest is v0.1.2")
    assert _kinds(claims) == ["latest"]


def test_the_newest_without_a_noun_that_is_right_is_not_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "最新的是 v0.1.3")
    assert claims == []


def test_the_newest_without_a_noun_survives_a_release_being_prepared() -> None:
    """Without a noun the claim could be about the tag or the release.

    While a release is being prepared the two differ, so the claim is only
    wrong when it is wrong under both readings: v0.1.3 is the newest tag,
    and the claim is not contradicted.
    """
    checker = _checker()
    facts = _facts(
        checker,
        versions=frozenset({"0.1.0", "0.1.1", "0.1.2"}),
        newest_tag="0.1.2",
        changelog_versions=("0.1.3", "0.1.2", "0.1.1", "0.1.0"),
        changelog_newest="0.1.3",
        unreleased_link="0.1.3",
    )
    claims = _claims(checker, "最新的是 v0.1.2", facts)
    assert claims == []


def test_a_number_that_is_not_a_version_is_not_the_newest() -> None:
    """The latest version of another project is not this project's."""
    checker = _checker()
    claims = _claims(checker, "the latest is 1.5.2")
    assert claims == []


# -- quotations ------------------------------------------------------------


def test_a_version_inside_a_quotation_is_not_a_claim() -> None:
    """A closed issue's checklist is quoted, and closed history is not rewritten.

    The status page says the issue wrote "``v0.1.0`` release: Not started".
    That is a true statement about a piece of history.
    """
    checker = _checker()
    claims = _claims(
        checker,
        "issue #1 的清单更旧：它写着「`v0.1.0` release: Not started」。",  # noqa: RUF001
    )
    assert claims == []


def test_a_quoted_release_claim_is_not_a_claim() -> None:
    checker = _checker()
    claims = _claims(checker, "报告里写着「v0.1.4 已发布」")
    assert claims == []


def test_a_code_listing_is_not_a_claim() -> None:
    checker = _checker()
    text = "```console\n$ pip install dexatlas==0.1.4\n```\n"
    assert _claims(checker, text) == []


def test_a_claim_in_a_code_fence_is_not_a_claim() -> None:
    """A fenced block is a listing, not a statement.

    The block above carries no claim to begin with, so it would pass either
    way. This one does: a release claim written inside a fence is a listing
    of what somebody wrote, and the checker must not read it as the
    repository's own claim.
    """
    checker = _checker()
    text = "```console\nv0.1.4 已发布\n```\n"
    assert _claims(checker, text) == []


# -- the ASCII double quote ------------------------------------------------


def test_a_claim_in_ascii_quotes_is_a_claim() -> None:
    """The ASCII double quote is not one of this repository's quotation marks.

    The convention is 「」 and the backtick. An ASCII-quoted phrase is prose,
    so a claim inside one is checked like any other.
    """
    checker = _checker()
    claims = _claims(checker, 'The doc says "the newest version is v0.1.2"')
    assert _kinds(claims) == ["latest"]


def test_an_example_in_ascii_quotes_is_not_a_claim() -> None:
    """An example is not a claim about the project.

    The changelog quotes the checker's own subject this way — "a sentence
    like "the newest tag is v0.1.2" is not a line number" — and the version
    in it is an example of a sentence, not a claim about this repository.
    """
    checker = _checker()
    claims = _claims(checker, 'a sentence like "the newest tag is v0.1.2" is not a line number')
    assert claims == []


# -- versions that are not versions of this project ------------------------


def test_a_tool_version_is_not_a_claim() -> None:
    """Apktool's version is not a release of this project."""
    checker = _checker()
    claims = _claims(
        checker, "这份文档是在 jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 上跑出来的"
    )
    assert claims == []


def test_a_planned_version_is_not_a_claim() -> None:
    """The roadmap names the versions Phase 2 and Phase 3 will have."""
    checker = _checker()
    claims = _claims(checker, "| Phase 2  | `v0.5.0`  | Agentic Intelligence   | planned |")
    assert claims == []


def test_a_number_that_is_not_a_version_is_not_a_claim() -> None:
    checker = _checker()
    claims = _claims(checker, "最大的样本不到 3 KB, 21.0.12.1 是当时用的 JDK 版本")
    assert claims == []


# -- versions without the "v" prefix ---------------------------------------


def test_a_released_version_without_the_prefix_is_a_finding() -> None:
    """A version of this project is a version of this project with or without
    the ``v``: "0.1.4 has been released" says the same thing as the prefixed
    spelling does.
    """
    checker = _checker()
    claims = _claims(checker, "0.1.4 已发布")
    assert _kinds(claims) == ["released"]
    assert "0.1.4" in claims[0].message  # type: ignore[attr-defined]


def test_a_named_release_without_the_prefix_is_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "详见 0.1.4 的 release notes")
    assert _kinds(claims) == ["unknown-version"]


def test_a_tool_version_that_was_released_is_not_a_claim() -> None:
    """Apktool released 2.11.1, and that is not a release of this project.

    The bare number is read as a version of this project only when it is in
    the series this project's own releases live in: 0.1.x here. A tool's
    version is in a series of its own.
    """
    checker = _checker()
    claims = _claims(checker, "apktool 2.11.1 was released in 2023")
    assert claims == []


def test_another_projects_version_in_its_own_series_is_not_a_claim() -> None:
    """Keep a Changelog's own version is not a version of this project."""
    checker = _checker()
    claims = _claims(checker, "The format is based on Keep a Changelog 1.1.0")
    assert claims == []


# -- a release that does not exist -----------------------------------------


def test_a_named_release_without_a_tag_is_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "详见 v0.1.4 的 release notes")
    assert _kinds(claims) == ["unknown-version"]


def test_a_named_release_that_is_tagged_is_not_a_finding() -> None:
    checker = _checker()
    claims = _claims(checker, "详见 v0.1.3 的 release notes")
    assert claims == []


# -- the repository's own sources ------------------------------------------


def test_a_package_version_behind_the_newest_tag_is_a_finding() -> None:
    """The packages once called themselves 0.1.0 after v0.1.2 had shipped."""
    checker = _checker()
    facts = _facts(checker, package_version="0.1.0")
    findings = checker.check_facts(facts)
    assert [finding.kind for finding in findings] == ["fact-package-behind"]


def test_a_tag_without_a_changelog_entry_is_a_finding() -> None:
    checker = _checker()
    facts = _facts(checker, changelog_versions=("0.1.3", "0.1.2", "0.1.1"))
    findings = checker.check_facts(facts)
    assert [finding.kind for finding in findings] == ["fact-changelog-missing"]


def test_a_changelog_entry_without_a_tag_is_a_finding() -> None:
    """An old release cannot have been forgotten and untagged."""
    checker = _checker()
    facts = _facts(
        checker,
        versions=frozenset({"0.1.0", "0.1.1", "0.1.3"}),
        newest_tag="0.1.3",
    )
    findings = checker.check_facts(facts)
    assert [finding.kind for finding in findings] == ["fact-changelog-untagged"]


def test_an_unreleased_link_behind_the_newest_tag_is_a_finding() -> None:
    checker = _checker()
    facts = _facts(checker, unreleased_link="0.1.2")
    findings = checker.check_facts(facts)
    assert [finding.kind for finding in findings] == ["fact-changelog-link-behind"]


def test_a_consistent_repository_has_no_fact_findings() -> None:
    checker = _checker()
    assert checker.check_facts(_facts(checker)) == []


# -- how a finding is identified -------------------------------------------


def test_a_finding_is_the_same_finding_after_the_line_moves() -> None:
    """The identity of a finding is its claim, not where it happens to sit."""
    checker = _checker()
    first = _claims(checker, "仓库里目前最新的 tag 是 `v0.1.2`")
    second = _claims(checker, "\n\n仓库里目前最新的 tag 是 `v0.1.2`")
    assert first[0].key == second[0].key  # type: ignore[attr-defined]
    assert first[0].line != second[0].line  # type: ignore[attr-defined]


def test_a_rewritten_claim_is_a_new_finding() -> None:
    """A claim that is still wrong after being reworded is still a new claim."""
    checker = _checker()
    first = _claims(checker, "仓库里目前最新的 tag 是 `v0.1.2`")
    second = _claims(checker, "仓库里目前最新的 tag 为 `v0.1.2`")
    assert first and second
    assert first[0].key != second[0].key  # type: ignore[attr-defined]


# -- the numbers a release document states ---------------------------------


#: The figures a release is measured by: the number of tests the report
#: measured at that release, and the coverage the report of that release
#: measured.
MEASURED = {"tests.total": "444", "coverage.pct": "94.0%"}


def _stated(checker: ModuleType, text: str) -> list[object]:
    """The findings the checker reports for the numbers a document states."""
    return checker.check_stated_numbers("docs/releases/v0.1.3.md", text, 0, MEASURED, "0.1.3")


def test_a_coverage_number_that_is_not_the_measured_one_is_a_finding() -> None:
    """The release notes of v0.1.3 said 93.9%; the report of that release
    measured 94.0%. Nobody noticed, and the wrong number shipped."""
    checker = _checker()
    claims = _stated(checker, "First-party coverage is **93.9%**.")
    assert _kinds(claims) == ["release-coverage"]
    assert "93.9" in claims[0].message  # type: ignore[attr-defined]


def test_a_coverage_number_that_is_the_measured_one_is_not_a_finding() -> None:
    checker = _checker()
    claims = _stated(checker, "First-party coverage is **94.0%** (1857/1975 lines).")
    assert claims == []


def test_a_release_without_a_measured_coverage_is_not_checked() -> None:
    """The reports before the generated figures have no coverage to compare with."""
    checker = _checker()
    claims = checker.check_stated_numbers(
        "docs/releases/v0.1.2.md",
        "First-party coverage is **89.2%**.",
        0,
        {"tests.total": "275"},
        "0.1.2",
    )
    assert claims == []


def test_a_coverage_without_the_word_is_a_finding() -> None:
    """A percentage that lost its label is still the release's coverage.

    A release document states its measurements, and the coverage is one of
    them. When it is the only percentage in the document, it is that figure:
    "First-party 93.9%" is the coverage with the word left out.
    """
    checker = _checker()
    claims = _stated(checker, "- First-party 93.9% (1857/1975 lines)")
    assert _kinds(claims) == ["release-coverage"]
    assert "93.9" in claims[0].message  # type: ignore[attr-defined]


def test_a_percentage_that_is_not_the_only_one_is_not_checked() -> None:
    """A document with several percentages is stating several things.

    The coverage of the release, the coverage of the one before it and the
    coverage of a module are all percentages, and the checker cannot tell
    them apart. It checks the one the word "coverage" is attached to and
    leaves the rest alone.
    """
    checker = _checker()
    claims = _stated(checker, "- The samples shrank by 30% and by 20% more")
    assert claims == []


def test_the_previous_version_coverage_is_not_a_finding() -> None:
    """ "up from 89.2%" states what the version before this one measured."""
    checker = _checker()
    claims = _stated(checker, "- First-party coverage 94.0%, up from 89.2%")
    assert claims == []


def test_the_previous_release_coverage_is_not_a_finding() -> None:
    """The number belongs to the release before this one.

    The word "coverage" is attached to "89.2%" here, and the number is that
    release's coverage. A checker that reads it as this release's coverage
    reports a figure that was never claimed.
    """
    checker = _checker()
    claims = _stated(checker, "The previous release had 89.2% coverage.")
    assert claims == []


def test_the_previous_release_coverage_the_other_way_round_is_not_a_finding() -> None:
    """The same sentence with the marker behind the number."""
    checker = _checker()
    claims = _stated(checker, "The coverage was 89.2% in the previous release.")
    assert claims == []


def test_the_coverage_of_this_release_is_still_checked() -> None:
    """The exclusion must not swallow the number that *is* this release's.

    "First-party coverage 94.0% ... up from 89.2%" states two figures, and
    only the second of them belongs to the release before this one.
    """
    checker = _checker()
    claims = _stated(checker, "- First-party coverage 93.9%, up from 89.2%")
    assert _kinds(claims) == ["release-coverage"]
    assert "93.9" in claims[0].message  # type: ignore[attr-defined]


def test_a_module_coverage_is_not_a_finding() -> None:
    """A module's own coverage is not the coverage of the release."""
    checker = _checker()
    claims = _stated(checker, "The Apktool adapter, previously at 82.7%, is now 94%.")
    assert claims == []


def test_a_test_count_that_is_the_measured_one_is_not_a_finding() -> None:
    checker = _checker()
    claims = _stated(checker, "- 444 tests (347 fast, 97 integration), up from 275")
    assert claims == []


def test_a_test_count_that_was_copied_wrong_is_a_finding() -> None:
    """The changelog's first release said 208 tests; that tag has 204."""
    checker = _checker()
    claims = _stated(checker, "- 208 tests")
    assert _kinds(claims) == ["release-tests"]
    assert "208" in claims[0].message  # type: ignore[attr-defined]


def test_counts_that_do_not_add_up_are_a_finding() -> None:
    """347 fast and 97 integration are 444 tests, and not 445."""
    checker = _checker()
    claims = _stated(checker, "- 444 tests (347 fast, 98 integration), up from 275")
    assert _kinds(claims) == ["release-tests"]


def test_a_passed_count_of_another_configuration_is_not_a_finding() -> None:
    """The verification table counts what each configuration passed, and they
    are not the same number."""
    checker = _checker()
    claims = _stated(checker, "| No backends installed | 394 passed, 50 skipped |")
    assert claims == []


def test_a_generated_number_is_not_a_finding() -> None:
    """A number between the markers was measured, not written by hand.

    The number here does not match the measurement, and the markers are what
    make the difference: a figure is written by the refresh script, so it is
    the measurement and not a claim about it.
    """
    checker = _checker()
    claims = _stated(checker, "Coverage: <!--fig:coverage.pct-->93.9%<!--/fig-->")
    assert claims == []


def test_the_line_of_a_stated_number_is_reported() -> None:
    checker = _checker()
    claims = _stated(checker, "First-party coverage is **93.9%**.")
    assert claims[0].line == 1  # type: ignore[attr-defined]


# -- the numbers the badges state ------------------------------------------


#: The numbers a badge may state: the tree as it is now, and the release it
#: last shipped.
CURRENT = {"tests": ["493", "444"], "coverage": ["94.0%", "94.0%"]}


def _badges(checker: ModuleType, text: str) -> list[object]:
    """The findings the checker reports for the numbers a badge states."""
    return checker.check_badges("README.md", text, CURRENT)


def test_a_badge_that_is_behind_the_measurement_is_a_finding() -> None:
    """The readme's badge said 275 tests; the project had 444."""
    checker = _checker()
    claims = _badges(
        checker,
        "[![Tests](https://img.shields.io/badge/tests-275%20passing-brightgreen.svg)](tests)",
    )
    assert _kinds(claims) == ["badge"]
    assert "275" in claims[0].message  # type: ignore[attr-defined]


def test_a_badge_that_matches_the_tree_is_not_a_finding() -> None:
    checker = _checker()
    claims = _badges(
        checker,
        "[![Tests](https://img.shields.io/badge/tests-493%20passing-brightgreen.svg)](tests)",
    )
    assert claims == []


def test_a_badge_that_matches_the_last_release_is_not_a_finding() -> None:
    """A badge that states the release the project shipped is not wrong."""
    checker = _checker()
    claims = _badges(
        checker,
        "[![Tests](https://img.shields.io/badge/tests-444%20passing-brightgreen.svg)](tests)",
    )
    assert claims == []


def test_a_coverage_badge_that_matches_the_measurement_is_not_a_finding() -> None:
    checker = _checker()
    claims = _badges(
        checker,
        "[![Coverage](https://img.shields.io/badge/coverage-94.0%25-brightgreen.svg)](pyproject.toml)",
    )
    assert claims == []


def test_a_rounded_coverage_badge_is_not_a_finding() -> None:
    """A badge states a whole percentage, and 89.2% is written "89%" on it."""
    checker = _checker()
    claims = _badges(
        checker,
        "[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](pyproject.toml)",
    )
    assert claims == []


def test_a_badge_that_rounds_the_measured_coverage_is_not_a_finding() -> None:
    """The tolerance is what lets a badge state a rounded number.

    A badge cannot hold "89.2%", so it says "89%". That is the same figure,
    and the checker has to know it: without the tolerance every badge in the
    repository would be a finding.
    """
    checker = _checker()
    claims = checker.check_badges(
        "README.md",
        "[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen.svg)](pyproject.toml)",
        {"coverage": ["89.2%"]},
    )
    assert claims == []


def test_a_badge_that_is_one_test_off_is_a_finding() -> None:
    """The tolerance covers rounding, and nothing else.

    A badge is hand-written, and one that is a whole test out is a badge
    that is wrong: the tolerance is half a percentage point, not a way of
    accepting any number that is roughly the right size.
    """
    checker = _checker()
    claims = _badges(
        checker,
        "[![Tests](https://img.shields.io/badge/tests-443%20passing-brightgreen.svg)](tests)",
    )
    assert _kinds(claims) == ["badge"]


def test_a_badge_about_something_else_is_not_a_finding() -> None:
    """A badge that states a version, or a licence, is not a count of tests."""
    checker = _checker()
    claims = _badges(
        checker,
        "[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)",
    )
    assert claims == []


def test_a_badge_that_counts_failures_is_not_a_finding() -> None:
    """A badge that says how many tests are failing is not a count of tests."""
    checker = _checker()
    claims = _badges(
        checker,
        "[![Tests](https://img.shields.io/badge/tests-0%20failing-brightgreen.svg)](tests)",
    )
    assert claims == []


# -- the documents a release's numbers are read from ------------------------


def test_the_release_notes_are_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    """The notes of a release state that release's numbers, and are checked.

    The changelog's section for a release is one document that states them;
    the release notes are a second, and they are where a number that was
    copied and went stale was found before.
    """
    checker = _checker()
    monkeypatch.setattr(checker, "measured_figures", lambda tag: {"coverage.pct": "94.0%"})
    documents = {"docs/releases/v0.1.3.md": "First-party coverage is **93.9%**."}
    findings = checker.check_release_numbers(_facts(checker), documents)
    assert [finding.kind for finding in findings] == ["release-coverage"]
    assert findings[0].path == "docs/releases/v0.1.3.md"


def test_a_closed_issues_checklist_is_not_checked() -> None:
    """A closed issue's checklist is history, not a claim about the project.

    The project does not rewrite a closed issue's checklist — the status
    page says so — and a checker that reported it would ask for a change
    the project has decided against.
    """
    checker = _checker()
    names = [name for name, _ in checker.documents_in_tree()]
    assert "CHANGELOG.md" in names
    assert not [name for name in names if name.startswith(".github/issues/")]


# -- the base commit's own facts --------------------------------------------


def _git(repository: Path, *args: str) -> str:
    """Run a git command in a repository the test built for itself."""
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def _write_changelog(repository: Path, versions: list[str]) -> None:
    """A changelog with one section per version, newest first."""
    sections = "".join(
        f"## [{version}] — 2026-10-20\n\n### Engineering\n\n- 444 tests (347 fast, 97 integration)\n\n"
        for version in versions
    )
    links = "".join(
        f"[{version}]: https://example.com/releases/tag/v{version}\n" for version in versions
    )
    newest = versions[0]
    (repository / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n"
        + sections
        + f"[Unreleased]: https://example.com/compare/v{newest}...HEAD\n"
        + links,
        encoding="utf-8",
    )


def _repository_with_one_release(repository: Path) -> None:
    """A repository with one release, and a page that describes the state
    after it.

    The page says the work after v0.1.3 has not been released. That is true
    of this commit, and false of the next one.
    """
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.email", "test@example.com")
    _git(repository, "config", "user.name", "test")

    (repository / "src" / "dexatlas").mkdir(parents=True)
    (repository / "src" / "dexatlas" / "__init__.py").write_text(
        '__version__ = "0.1.3"\n', encoding="utf-8"
    )
    (repository / "docs").mkdir()
    (repository / "docs" / "status.md").write_text(
        "# Status\n\n**对应版本：** v0.1.3 之后的开发状态（尚未发布）\n",  # noqa: RUF001
        encoding="utf-8",
    )
    _write_changelog(repository, ["0.1.3"])
    _git(repository, "add", "-A")
    _git(repository, "commit", "--quiet", "-m", "the first release")
    _git(repository, "tag", "v0.1.3")


def _release_a_version(repository: Path) -> None:
    """Release v0.1.4, and change no document.

    The release is a tag, a changelog section, the package version and the
    [Unreleased] link — the facts the checker reads. The page that says the
    work after v0.1.3 has not been released is not touched, and the commit
    makes it false.
    """
    (repository / "src" / "dexatlas" / "__init__.py").write_text(
        '__version__ = "0.1.4"\n', encoding="utf-8"
    )
    _write_changelog(repository, ["0.1.4", "0.1.3"])
    _git(repository, "add", "-A")
    _git(repository, "commit", "--quiet", "-m", "Release v0.1.4")
    _git(repository, "tag", "v0.1.4")


def test_the_base_facts_are_the_base_own_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The base commit's tags are the base commit's tags.

    The tag this commit pushed is not among them: it did not exist when the
    base was written.
    """
    checker = _checker()
    repository = tmp_path / "repository"
    repository.mkdir()
    _repository_with_one_release(repository)
    _release_a_version(repository)
    monkeypatch.setattr(checker, "REPO", repository)

    assert checker.read_facts().tags == ("v0.1.3", "v0.1.4")
    assert checker.read_facts_at("HEAD~1").tags == ("v0.1.3",)


def test_a_claim_the_commit_made_false_is_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Releasing a version makes the claims that deny it false.

    The base commit had no v0.1.4 tag, so the claim on the status page was
    true there and is false here. It is a finding this commit added, and the
    check has to fail: reading the base against this tree's facts would have
    found the same claim in the base as well, and called it drift that was
    already on its way out.
    """
    checker = _checker()
    repository = tmp_path / "repository"
    repository.mkdir()
    _repository_with_one_release(repository)
    _release_a_version(repository)
    monkeypatch.setattr(checker, "REPO", repository)

    assert checker.main(["--base", "HEAD~1"]) == 1
