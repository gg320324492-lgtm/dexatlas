"""The M10 self-check's contract checks must read the tree, not a private copy.

``scripts/m10_selfcheck.py`` freezes the automatable part of the M10
acceptance pack. When one of its checks restates an expectation the contract
already states elsewhere, a contract change has to update both places - and
when only one is updated, the self-check fails a correct tree. That is what
happened when exit code 6 landed: the contract table, the CLI constants and
the contract test all said 0-6, while the self-check still expected 0-5, so
its F1 check went red on a tree whose contract was consistent.

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
    the point: it has to be derived from the tree, not spelled out in the
    script.
    """
    import re

    script = _selfcheck_script()
    contracts = script.CONTRACTS_PATH.read_text(encoding="utf-8")
    table = contracts.split("### 1.2 退出码", 1)[-1].split("###", 1)[0]
    stated = {int(m) for m in re.findall(r"^\| (\d) \|", table, re.MULTILINE)}

    cli = (script.REPO_ROOT / "src" / "dexatlas" / "cli" / "main.py").read_text(encoding="utf-8")
    defined = {int(m) for m in re.findall(r"^EXIT_[A-Z_]+ = (\d+)$", cli, re.MULTILINE)}

    report: list[Any] = []

    class _RecordingReport:
        def add(self, outcome: Any) -> None:
            report.append(outcome)

    script.check_exit_code_contract(_RecordingReport())
    assert report, "the F1 check recorded no outcome"
    outcome = report[0]
    return stated, defined | {0}, outcome


def test_f1_exit_code_check_passes_on_a_consistent_tree() -> None:
    """The contract table, the CLI constants and the contract test agree."""
    stated, effective, outcome = _exit_code_sets()
    assert outcome.state == "pass", f"F1 failed on a consistent tree: {outcome.detail}"
    assert stated == effective, f"contract table {stated} != CLI {effective}"


def test_f1_exit_code_check_reads_expectation_from_the_contract_test() -> None:
    """The script's expectation must come from ``EXPECTED_EXIT_CODES``, not a copy.

    If the script went back to a hard-coded set, adding an exit code to the
    contract would turn F1 red on a tree where the contract table, the CLI
    and the contract test all agree — the failure mode this file exists to
    prevent. The check's detail line therefore has to name the contract
    test's set as one of the things being compared, and that set has to
    equal the CLI's.
    """
    import re

    script = _selfcheck_script()
    test = script.CONTRACT_TEST.read_text(encoding="utf-8")
    block = test.split("EXPECTED_EXIT_CODES = {", 1)[-1].split("}", 1)[0]
    literals = {int(m) for m in re.findall(r"^\s+(\d+):", block, re.MULTILINE)}
    names = re.findall(r"^\s+([A-Z][A-Z_]+):", block, re.MULTILINE)

    cli = (script.REPO_ROOT / "src" / "dexatlas" / "cli" / "main.py").read_text(encoding="utf-8")
    from_cli = set(literals)
    for name in names:
        match = re.search(rf"^{name} = (\d+)$", cli, re.MULTILINE)
        assert match, f"contract test names {name}, which the CLI does not define"
        from_cli.add(int(match.group(1)))

    stated, effective, outcome = _exit_code_sets()
    assert from_cli == stated == effective, (
        f"contract test {sorted(from_cli)}, table {stated}, CLI {effective}"
    )
    assert "契约测试" in outcome.detail, "the check no longer cites the contract test's set"


# ---------------------------------------------------------------------------
# The three gaps the reader dry run found
# ---------------------------------------------------------------------------
#
# ``docs/reports/reader-dry-run.md`` walked the M10 material on a clean
# machine and found three things the self-check did not look for: the setup
# step may leave the third-party samples unfetched (the suite then skips and
# the exit code is still 0), A6's degraded evidence cannot be looked up
# afterwards, and the evidence package holds one more entry than the CLI
# prints. Each check below has to go red when its gap comes back, so every
# test mutates a copy of the tree and watches the check notice.


#: Every file the three checks read. A mutated tree is a copy of these.
DRY_RUN_FILES = (
    "scripts/fetch-fixtures.sh",
    "docs/reports/m10-reader-package.md",
    "docs/reports/m10-reader-kit.md",
    "docs/reports/m10-executive-summary.md",
    "src/dexatlas/reports/evidence_package.py",
    "src/dexatlas/cli/main.py",
    "src/dexatlas/core/storage.py",
)

#: The check that answers each of the three findings.
DRY_RUN_CHECKS = (
    ("FIXTURE.precondition", "check_fixture_precondition"),
    ("A6.on-the-spot", "check_a6_onsite_record"),
    ("PACKAGE.entry-count", "check_package_entry_count"),
)


def _dry_run_tree(tmp_path: Path) -> Path:
    """A copy of the files the three checks read, ready to be broken."""
    for relative in DRY_RUN_FILES:
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
    """Break one sentence of one document in the copied tree.

    ``count=-1`` replaces every occurrence, which is what a phrase that
    appears twice in one paragraph needs.
    """
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{relative} does not contain {old!r}"
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def test_the_three_dry_run_criteria_run_on_this_tree() -> None:
    """The three checks exist, are registered, and pass on the current tree."""
    script = _selfcheck_script()
    registered = {getattr(check, "__name__", "") for check in script.CHECKS}
    for check_id, function_name in DRY_RUN_CHECKS:
        assert function_name in registered, f"{function_name} is not registered in CHECKS"
        outcome = _outcome(script, function_name, REPO_ROOT)
        assert outcome.state == "pass", f"{check_id} failed: {outcome.detail}"
        assert outcome.check_id == check_id


def test_the_fixture_criterion_fails_when_the_setup_step_is_gone(tmp_path: Path) -> None:
    """A material that never asks for the samples is a gap, not a pass."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-package.md",
        "bash scripts/fetch-fixtures.sh",
        "# the samples are optional",
    )
    outcome = _outcome(script, "check_fixture_precondition", root)
    assert outcome.state == "fail", f"the step's absence went unnoticed: {outcome.detail}"


def test_the_fixture_criterion_fails_when_the_materials_disagree(tmp_path: Path) -> None:
    """Two materials claiming different skip counts is a drift, not a pass."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-kit.md",
        "不抓则 27 个集成用例 skip",
        "不抓则 25 个集成用例 skip",
    )
    outcome = _outcome(script, "check_fixture_precondition", root)
    assert outcome.state == "fail", f"the drift went unnoticed: {outcome.detail}"


def test_the_fixture_criterion_fails_without_the_exit_code_caveat(tmp_path: Path) -> None:
    """Without the caveat, exit code 0 reads as "everything ran"."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-package.md",
        "不说明该跑的都跑了",
        "",
    )
    outcome = _outcome(script, "check_fixture_precondition", root)
    assert outcome.state == "fail", f"the missing caveat went unnoticed: {outcome.detail}"


def test_the_a6_criterion_fails_when_the_material_promises_a_later_look(
    tmp_path: Path,
) -> None:
    """The CLI cannot replay a run, so promising it does is a defect."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-package.md",
        "**当场记下证据**",
        "**事后可以再查**",
    )
    outcome = _outcome(script, "check_a6_onsite_record", root)
    assert outcome.state == "fail", f"the promise went unnoticed: {outcome.detail}"


def test_the_a6_criterion_fails_without_the_on_the_spot_instruction(
    tmp_path: Path,
) -> None:
    """A reader told to look back later will find nothing there."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-package.md",
        "当场",
        "稍后",
        count=-1,
    )
    outcome = _outcome(script, "check_a6_onsite_record", root)
    assert outcome.state == "fail", f"the missing instruction went unnoticed: {outcome.detail}"


def test_the_package_criterion_fails_when_the_material_miscounts(tmp_path: Path) -> None:
    """The zip holds one more entry than the manifest lists."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "docs/reports/m10-reader-package.md",
        "zip 内是 **4 个条目**",
        "zip 内是 **3 个条目**",
    )
    outcome = _outcome(script, "check_package_entry_count", root)
    assert outcome.state == "fail", f"the miscount went unnoticed: {outcome.detail}"


def test_the_package_criterion_fails_when_the_cli_stops_printing_the_manifest_count(
    tmp_path: Path,
) -> None:
    """The printed number has to be the manifest's, or the material lies."""
    script = _selfcheck_script()
    root = _dry_run_tree(tmp_path)
    _edit(
        root,
        "src/dexatlas/cli/main.py",
        "len(manifest['files'])",
        "len(manifest['files']) + 1",
    )
    outcome = _outcome(script, "check_package_entry_count", root)
    assert outcome.state == "fail", f"the changed print went unnoticed: {outcome.detail}"
