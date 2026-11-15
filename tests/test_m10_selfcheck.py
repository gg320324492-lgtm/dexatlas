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
