#!/usr/bin/env python3
"""Check that every gate in this repository is run by something.

    uv run --no-sync python scripts/check-gate-coverage.py

The source fingerprint covers ``src/``, ``tests/``, ``pyproject.toml`` and
the measurement script. Everything else under ``scripts/`` is outside it, so
a change to a gate script does not make the report's numbers stale -- and
nothing notices, because nothing asks whether the gate still works.

The answer to "who runs this gate?" is supposed to be a job in
``.github/workflows/ci.yml`` or a test in ``tests/``. A gate nobody runs is
a document, not a gate: it can be wrong for months and the repository stays
green. This script asks the question of every gate and fails when the
answer is nowhere.

It also holds the other direction. A new gate that is written and not wired
into CI is the same mistake in a different order, so:

* a script that looks like a gate -- ``check-*.py``, ``verify-*.py`` or
  ``*_selfcheck.py`` -- has to be in the list below, and
* a script under ``scripts/`` that a workflow runs has to be in the list
  too, because running it in CI is what makes it a gate.

The list is the registry of the gates. It is written by hand, and a
hand-written list can be rewritten into something easier to tick -- which
is why the two directions above are checked as well: a gate cannot leave
the list without something noticing, and cannot enter CI without being in
it.

The exit code is 0 when every gate is run and 1 when one is not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
TESTS_DIR = REPO_ROOT / "tests"

#: The gates, and what each of them is for. A gate is a script that says
#: whether something about this repository holds; it earns its place by
#: being run.
GATES: dict[str, str] = {
    "scripts/check-contract-records.py": "the live contract check against the record in section 7",
    "scripts/check-doc-citations.py": "every file:line citation in the documentation",
    "scripts/check-gate-coverage.py": "that every gate is run by something",
    "scripts/check-m10-snapshot.py": "the M10 self-check against its snapshot",
    "scripts/check-release-numbers.py": "the release numbers the outward texts state",
    "scripts/check-version-claims.py": "the version claims in the documentation",
    "scripts/m10_selfcheck.py": "the M10 acceptance pack's automatable half",
    "scripts/make-social-preview.py": "the numbers on the front page's card",
    "scripts/refresh-report-figures.py": "the measurement the report records",
    "scripts/verify-public-contracts.py": "the public contracts, live",
}

#: The names that make a script a gate. A script that looks like one and
#: is not in the registry above is a gate that was never wired up.
GATE_NAME = re.compile(r"^(check-.*\.py|verify-.*\.py|.*_selfcheck\.py)$")

#: A script under ``scripts/`` named in a workflow or a test.
SCRIPT_REFERENCE = re.compile(r"scripts/[A-Za-z0-9_.-]+\.(?:py|sh)")


def scripts_referenced_in_workflows() -> dict[str, list[str]]:
    """The scripts the workflows run, and the workflows that run them."""
    found: dict[str, list[str]] = {}
    if not WORKFLOWS_DIR.is_dir():
        return found
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        for name in SCRIPT_REFERENCE.findall(text):
            found.setdefault(name, []).append(workflow.name)
    return found


def scripts_referenced_in_tests() -> set[str]:
    """The scripts the test suite runs."""
    found: set[str] = set()
    if not TESTS_DIR.is_dir():
        return found
    for test in sorted(TESTS_DIR.rglob("test_*.py")):
        text = test.read_text(encoding="utf-8")
        found.update(SCRIPT_REFERENCE.findall(text))
    return found


def main() -> int:
    problems: list[str] = []
    ok: list[str] = []

    workflows = scripts_referenced_in_workflows()
    tests = scripts_referenced_in_tests()

    for name, what in sorted(GATES.items()):
        path = REPO_ROOT / name
        if not path.is_file():
            problems.append(f"{name} is registered as a gate but does not exist")
            continue
        in_workflows = workflows.get(name, [])
        in_tests = name in tests
        if in_workflows:
            where = ", ".join(sorted(set(in_workflows)))
            ok.append(f"{name} runs in {where} -- {what}")
        elif in_tests:
            ok.append(f"{name} runs in the test suite -- {what}")
        else:
            problems.append(
                f"{name} is a gate and nothing runs it: no workflow and no test names it"
            )

    # A gate that was written and never wired up is the same mistake in a
    # different order, so the names that make a script a gate have to be in
    # the registry.
    registered = set(GATES)
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        name = f"scripts/{path.name}"
        if GATE_NAME.match(path.name) and name not in registered:
            problems.append(
                f"{name} looks like a gate but is not registered: add it to GATES in "
                f"{Path(__file__).name} and wire it into a workflow or a test"
            )

    # And a script that a workflow runs is a gate, whether or not anybody
    # thought of it as one.
    for name in sorted(workflows):
        if not name.endswith(".py"):
            continue
        if name not in registered:
            problems.append(
                f"{name} runs in a workflow but is not registered as a gate: "
                f"add it to GATES in {Path(__file__).name}"
            )

    for line in ok:
        print(f"  PASS {line}")
    for line in problems:
        print(f"  FAIL {line}")
    if problems:
        print(
            f"\n{len(problems)} gate(s) are not run by anything.",
            file=sys.stderr,
        )
        return 1
    print(f"\nAll {len(ok)} gates are run by something.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
