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
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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


#: The figures the execution report of v0.1.3 carries, measured.
MEASURED = {
    "tests.total": "444",
    "tests.fast": "347",
    "tests.slow": "97",
    "coverage.pct": "94.0%",
}


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


def test_the_previous_version_coverage_is_not_a_finding() -> None:
    """ "up from 89.2%" states what the version before this one measured."""
    checker = _checker()
    claims = _stated(checker, "- First-party coverage 94.0%, up from 89.2%")
    assert claims == []


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
    checker = _checker()
    claims = _stated(checker, "- 445 tests (347 fast, 97 integration), up from 275")
    assert _kinds(claims) == ["release-tests"]
    assert "445" in claims[0].message  # type: ignore[attr-defined]


def test_a_passed_count_of_another_configuration_is_not_a_finding() -> None:
    """The verification table counts what each configuration passed, and they
    are not the same number."""
    checker = _checker()
    claims = _stated(checker, "| No backends installed | 394 passed, 50 skipped |")
    assert claims == []


def test_a_generated_number_is_not_a_finding() -> None:
    """A number between the markers was measured, not written by hand."""
    checker = _checker()
    claims = _stated(checker, "Coverage: <!--fig:coverage.pct-->94.0%<!--/fig-->")
    assert claims == []


def test_the_line_of_a_stated_number_is_reported() -> None:
    checker = _checker()
    claims = _stated(checker, "First-party coverage is **93.9%**.")
    assert claims[0].line == 1  # type: ignore[attr-defined]
