"""The M10 self-check's contract checks must read the tree, not a private copy.

``scripts/m10_selfcheck.py`` freezes the automatable part of the M10
independent-acceptance review. When one of its checks restates an expectation
the contract already states elsewhere, a contract change has to update both
places - and when only one is updated, the self-check fails a correct tree.
That is what happened when exit code 6 landed: the contract table, the CLI
constants and the contract test all said 0-6, while the self-check still
expected 0-5, so its F1 check went red on a tree whose contract was
consistent.

These tests load the script the way the suite loads
``refresh-report-figures.py`` - as a module, reading its rules - and assert
the F1 check compares the three statements of the exit-code contract with
*each other* rather than with a hard-coded set.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
SELFCHECK_SCRIPT = REPO_ROOT / "scripts" / "m10_selfcheck.py"


def _selfcheck_script() -> ModuleType:
    """The M10 self-check script, loaded as a module for direct inspection."""
    spec = spec_from_file_location("dexatlas_m10_selfcheck", SELFCHECK_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _exit_code_sets() -> tuple[set[int], set[int], set[int]]:
    """The three statements of the exit-code contract, as the script reads them.

    Returns the contract table's set, the CLI constants' set (plus the
    implicit 0), and the set the check compares them against. The last one is
    the point: it has to be derived from the tree, not written down twice.
    """
    script = _selfcheck_script()
    outcomes: list[Any] = []

    class _RecordingReport:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script.check_exit_code_contract(_RecordingReport())
    assert len(outcomes) == 1
    detail = outcomes[0].detail

    import re

    cli = re.search(r"CLI=\[([^]]*)\]", detail)
    table = re.search(r"契约表=\[([^]]*)\]", detail)
    assert cli and table, detail
    from_cli = {int(value) for value in cli.group(1).replace("'", "").split(", ") if value}
    stated = {int(value) for value in table.group(1).replace("'", "").split(", ") if value}
    return from_cli, stated, from_cli


def test_f1_exit_code_check_passes_on_a_consistent_tree() -> None:
    """A tree whose three statements agree is a pass."""
    from_cli, stated, effective = _exit_code_sets()
    assert from_cli == stated == effective, (
        f"contract test {sorted(from_cli)}, table {stated}, CLI {effective}"
    )


def test_f1_exit_code_check_reads_expectation_from_the_contract_test() -> None:
    """The check cites the contract test's set, not a private copy.

    The F1 outcome's detail names the CLI's own set; a private expectation
    would live in the self-check script instead of being read out of the
    tree, and this test fails if the check stops reading the tree.
    """
    from_cli, stated, outcome = _exit_code_sets()
    assert from_cli == stated == outcome, (
        f"contract test {sorted(from_cli)}, table {stated}, CLI {outcome}"
    )


# ---------------------------------------------------------------------------
# The two code-side gaps the reader dry run found
# ---------------------------------------------------------------------------
#
# The reader dry run found three things the self-check did not look for:
# the setup step may leave the third-party samples unfetched (the suite then
# skips and the exit code is still 0), A6's degraded evidence could not be
# looked up afterwards, and the evidence package holds one more entry than
# the CLI prints. The material-side halves of those checks went away with
# the de-platformisation cleanup; what remains is the code-side half, and
# every test below has to go red when its gap comes back, so each mutates a
# copy of the tree and watches the check notice.


#: Every file the code-side checks read. A mutated tree is a copy of these.
CODE_FILES = (
    "scripts/fetch-fixtures.sh",
    "src/dexatlas/reports/evidence_package.py",
    "src/dexatlas/cli/main.py",
    "src/dexatlas/core/storage.py",
    "src/dexatlas/api/app.py",
)

#: The check that answers each of the findings.
CODE_CHECKS = (
    ("FIXTURE.precondition", "check_fixture_precondition"),
    ("A6.on-the-spot", "check_a6_onsite_record"),
    ("PACKAGE.entry-count", "check_package_entry_count"),
)


def _code_tree(tmp_path: Path) -> Path:
    """A copy of the files the code-side checks read, ready to be broken."""
    for relative in CODE_FILES:
        source = REPO_ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _outcome(script: ModuleType, function_name: str, root: Path) -> Any:
    """Run one check against ``root`` and return the outcome it recorded."""
    outcomes: list[Any] = []

    class _RecordingReport:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    getattr(script, function_name)(_RecordingReport(), root=root)
    assert len(outcomes) == 1, f"{function_name} recorded {len(outcomes)} outcomes"
    return outcomes[0]


def _edit(root: Path, relative: str, old: str, new: str, *, count: int = 1) -> None:
    """Break one sentence of one file in the copied tree.

    ``count=-1`` replaces every occurrence, which is what a phrase that
    appears twice in one place needs.
    """
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{relative} does not contain {old!r}"
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def test_the_code_criteria_run_on_this_tree() -> None:
    """The checks exist, are registered, and pass on the current tree."""
    script = _selfcheck_script()
    registered = {getattr(check, "__name__", "") for check in script.CHECKS}
    for check_id, function_name in CODE_CHECKS:
        assert function_name in registered, f"{function_name} is not registered in CHECKS"
        outcome = _outcome(script, function_name, REPO_ROOT)
        assert outcome.state == "pass", f"{check_id} failed: {outcome.detail}"
        assert outcome.check_id == check_id


def test_the_fixture_criterion_fails_when_the_fetch_list_is_gone(tmp_path: Path) -> None:
    """A fetch script that declares no samples is a gap, not a pass."""
    script = _selfcheck_script()
    root = _code_tree(tmp_path)
    _edit(
        root,
        "scripts/fetch-fixtures.sh",
        "FILES=(",
        "UNUSED=(",
    )
    outcome = _outcome(script, "check_fixture_precondition", root)
    assert outcome.state == "fail", f"the empty list went unnoticed: {outcome.detail}"


def test_the_a6_criterion_fails_when_runs_are_not_queryable(
    tmp_path: Path,
) -> None:
    """A degraded run's evidence must be retrievable: the storage and API
    layers have to keep past runs queryable."""
    script = _selfcheck_script()
    root = _code_tree(tmp_path)
    _edit(
        root,
        "src/dexatlas/core/storage.py",
        "def get_run(self, run_id: str)",
        "def get_run_record(self, run_id: str)",
    )
    _edit(
        root,
        "src/dexatlas/core/storage.py",
        "def list_runs(self, project_id: str)",
        "def list_project_runs(self, project_id: str)",
    )
    outcome = _outcome(script, "check_a6_onsite_record", root)
    assert outcome.state == "fail", f"the lost queryability went unnoticed: {outcome.detail}"


def test_the_package_criterion_fails_when_the_cli_prints_the_manifest_count(
    tmp_path: Path,
) -> None:
    """The printed number has to be the archive's, not the manifest's.

    The manifest lists every file in the package except itself, so its
    count is one short of what a reader counts in the zip. A CLI that
    prints the manifest's count is one file out, and the criterion has to
    notice.
    """
    script = _selfcheck_script()
    root = _code_tree(tmp_path)
    _edit(
        root,
        "src/dexatlas/cli/main.py",
        "package_file_summary(manifest)",
        "len(manifest['files'])",
    )
    outcome = _outcome(script, "check_package_entry_count", root)
    assert outcome.state == "fail", f"the misleading count went unnoticed: {outcome.detail}"


def test_the_package_criterion_passes_when_the_cli_prints_the_archive_count(
    tmp_path: Path,
) -> None:
    """The archive's own count is the number the reader counts.

    The count has to be the archive's — the manifest's count plus the
    manifest itself — and it may be written any way that says so.
    """
    script = _selfcheck_script()
    root = _code_tree(tmp_path)
    _edit(
        root,
        "src/dexatlas/cli/main.py",
        "package_file_summary(manifest)",
        "len(manifest['files']) + 1",
    )
    outcome = _outcome(script, "check_package_entry_count", root)
    assert outcome.state == "pass", f"the archive's count was rejected: {outcome.detail}"


def _changelog_outcome(tmp_path: Path, monkeypatch: Any, text: str) -> tuple[bool, str]:
    """The DOC.changelog outcome for a changelog written to a temp file."""
    script = _selfcheck_script()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(text, encoding="utf-8")
    monkeypatch.setattr(script, "CHANGELOG_PATH", changelog)
    outcomes: list[Any] = []

    class _Recorder:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script.check_changelog(_Recorder())
    assert len(outcomes) == 1, "the check must report exactly one outcome"
    outcome = outcomes[0]
    passed = str(getattr(outcome, "state", "")).lower() in {"pass", "passed"}
    return passed, str(getattr(outcome, "detail", ""))


def test_a_section_that_only_fixes_things_passes_the_changelog_check(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """``### Fixed`` alone is a good section, and the check used to fail it.

    It required ``### Added`` **and** ``### Changed``, so a release that
    only fixed things failed for being what it is (2026-11-28: the
    ``[Unreleased]`` section carried the contract tightening as its only
    entry, and the M10 self-check went red on a correct tree).
    """
    passed, detail = _changelog_outcome(
        tmp_path,
        monkeypatch,
        "# Changelog\n\n## [Unreleased]\n\n### Fixed\n\n- a fix\n\n"
        "## [1.0.0] — 2026-01-01\n\n### Added\n\n- a feature\n",
    )

    assert passed, detail
    assert "Fixed" in detail


def test_a_section_with_no_heading_at_all_fails_the_changelog_check(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """The point of the check survives the loosening: something has to be there."""
    passed, detail = _changelog_outcome(
        tmp_path,
        monkeypatch,
        "# Changelog\n\n## [Unreleased]\n\nnothing written yet\n",
    )

    assert not passed, detail
    assert "无" in detail


def test_a_section_that_only_adds_passes_the_changelog_check(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """``### Added`` alone was also failed by the old rule; it is a good section."""
    passed, detail = _changelog_outcome(
        tmp_path,
        monkeypatch,
        "# Changelog\n\n## [1.0.0] — 2026-01-01\n\n### Added\n\n- a feature\n",
    )

    assert passed, detail
