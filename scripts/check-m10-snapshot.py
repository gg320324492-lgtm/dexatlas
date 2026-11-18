#!/usr/bin/env python3
"""Check that the M10 self-check snapshot describes what the script does.

    uv run --no-sync python scripts/check-m10-snapshot.py

``scripts/m10_selfcheck.py`` turns the 40 items of the M10 acceptance pack
into checks it can run by itself, and prints a verdict: how many passed,
how many failed, how many are left for a human. ``docs/reports/m10-selfcheck.md``
is the record of one run of that script -- the counts it produced and the
list of the checks it ran.

The CI job ran the script and nobody compared the two. A snapshot that had
stopped describing the script stayed in the repository: the document said
43 checks passed and the script had grown a 44th that failed, or the
document listed a check the script no longer has, and the job was green
either way because the job only asked the script.

This script closes that gap. It runs the self-check, reads the snapshot, and
asks whether the two still say the same thing:

* the counts -- passed, failed, left for a human -- have to be the ones the
  snapshot records, and
* the set of checks the script ran has to be the set the snapshot lists. A
  check that was added and a check that was removed both show up here.

The exit code says which kind of wrongness it found:

* 0 -- the snapshot describes the script.
* 1 -- it does not: the snapshot is stale, or the script changed without
  the snapshot being rewritten.
* 2 -- the environment is not ready. The self-check asks whether the gate
  commands are installed, and on a machine without the development extras
  they are not; that is a machine that cannot answer the question, not a
  snapshot that is wrong.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO_ROOT / "docs" / "reports" / "m10-selfcheck.md"
SELFCHECK = REPO_ROOT / "scripts" / "m10_selfcheck.py"

#: How long the self-check may take. It reads files and asks the tool
#: whether it is installed; it does not run the suite.
TIMEOUT_SECONDS = 300

#: The line the snapshot records the verdict of its run on.
RECORDED_SUMMARY = re.compile(
    r"\*\*通过\s*(\d+)，失败\s*(\d+)，需人工\s*(\d+)",  # noqa: RUF001
)

#: A check id as the snapshot writes it: an upper-case family and a
#: lower-case name, in backticks.
CHECK_ID = re.compile(r"`([A-Z][A-Z0-9-]*\.[A-Za-z0-9*.-]+)`")


def recorded_summary(text: str) -> tuple[int, int, int] | None:
    """The counts the snapshot records: passed, failed, left for a human."""
    match = RECORDED_SUMMARY.search(text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def recorded_check_ids(text: str) -> list[str]:
    """The check ids the snapshot's table names.

    The snapshot's table of the checks the script makes is the section that
    follows the "2.1" heading. The section after it lists the items left
    for a human, whose ids are the acceptance pack's own (A1, B2, ...) and
    carry no family, so they are not mistaken for check ids.

    The table does not name every check one by one: the gate commands are
    written as a range ("``G.ruff`` ... ``G.check-version-claims``") and the
    scripts as a wildcard ("``GATE.*``"). What is returned is therefore both
    the names and the families, and the comparison uses the families for the
    groups the table summarises.
    """
    start = text.find("### 2.1")
    if start == -1:
        return []
    end = text.find("### ", start + 1)
    section = text[start:end] if end != -1 else text[start:]
    found: list[str] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        first_cell = line.split("|")[1] if line.count("|") >= 2 else ""
        found.extend(CHECK_ID.findall(first_cell))
    return found


def family_of(check_id: str) -> str:
    """The group a check belongs to: the part before the dot."""
    return check_id.split(".", 1)[0]


def run_selfcheck() -> tuple[dict[str, Any] | None, str]:
    """Run the self-check and return its JSON summary, or why it did not run."""
    env = dict(os.environ)
    # The parent and the child have to agree on the encoding: the child
    # prints Chinese text, and a parent that decodes it with the platform's
    # default codec reads the bytes as something else entirely.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        completed = subprocess.run(
            [sys.executable, str(SELFCHECK), "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "the self-check did not finish"
    if completed.returncode != 0 and not completed.stdout.strip():
        return None, f"the self-check exited {completed.returncode} without printing a summary"
    try:
        return json.loads(completed.stdout), ""
    except json.JSONDecodeError as error:
        return None, f"the self-check did not print a JSON summary ({error})"


def main() -> int:
    for path, what in ((SNAPSHOT, "the M10 self-check snapshot"), (SELFCHECK, "the self-check")):
        if not path.is_file():
            print(f"FAIL {what} is missing: {path}", file=sys.stderr)
            return 1

    snapshot = SNAPSHOT.read_text(encoding="utf-8")
    counts = recorded_summary(snapshot)
    if counts is None:
        print(
            f"FAIL {SNAPSHOT} records no summary line: the snapshot has to say how many "
            "checks passed, failed and were left for a human",
            file=sys.stderr,
        )
        return 1
    listed = recorded_check_ids(snapshot)
    if not listed:
        print(
            f"FAIL {SNAPSHOT} lists no checks: the snapshot has to name the checks the "
            "script judges",
            file=sys.stderr,
        )
        return 1

    summary, why = run_selfcheck()
    if summary is None:
        print(f"FAIL {why}", file=sys.stderr)
        return 2

    outcomes = summary.get("outcomes", [])
    failures = [item for item in outcomes if item.get("state") == "fail"]

    # A check that asks whether a gate command is installed fails on a
    # machine that does not have it. That is the machine, not the
    # snapshot -- and a gate that calls it a mismatch would be wrong on
    # every machine that has not installed the development extras.
    environment_failures = [item for item in failures if "PATH=" in str(item.get("detail", ""))]
    if failures and len(environment_failures) == len(failures):
        missing = ", ".join(str(item.get("id")) for item in environment_failures)
        print(
            f"the self-check could not find the gate commands ({missing}); this machine "
            "cannot answer the question, so the snapshot was not compared",
            file=sys.stderr,
        )
        return 2

    problems: list[str] = []
    ok: list[str] = []

    observed = (
        int(summary.get("pass", 0)),
        int(summary.get("fail", 0)),
        int(summary.get("manual", 0)),
    )
    if observed != counts:
        problems.append(
            f"the snapshot records {counts[0]} passed, {counts[1]} failed and "
            f"{counts[2]} left for a human; the script now reports {observed[0]}, "
            f"{observed[1]} and {observed[2]}"
        )
    else:
        ok.append(
            f"the counts agree: {observed[0]} passed, {observed[1]} failed, "
            f"{observed[2]} left for a human"
        )

    judged = {str(item.get("id")) for item in outcomes if item.get("state") in {"pass", "fail"}}

    # The table names the checks one by one for most families and
    # summarises the rest, so the comparison is made in two steps: every
    # name the table gives has to be a check the script runs, and every
    # family the script has has to be one the table mentions. A check
    # added inside a family the table lists one by one changes the count,
    # which is what the count comparison above is for.
    stale_names = sorted(
        name for name in set(listed) if not name.endswith(".*") and name not in judged
    )
    if stale_names:
        problems.append(
            "the snapshot names checks the script no longer runs: " + ", ".join(stale_names)
        )
    else:
        ok.append(f"every check the snapshot names is one the script runs ({len(listed)} names)")

    script_families = {family_of(name) for name in judged}
    snapshot_families = {family_of(name) for name in listed}
    unmentioned = sorted(script_families - snapshot_families)
    forgotten = sorted(snapshot_families - script_families)
    if unmentioned:
        problems.append(
            "the snapshot does not mention the groups of checks the script now runs: "
            + ", ".join(unmentioned)
        )
    if forgotten:
        problems.append(
            "the snapshot mentions groups of checks the script no longer runs: "
            + ", ".join(forgotten)
        )
    if not unmentioned and not forgotten:
        ok.append(
            f"the snapshot covers the same {len(script_families)} groups of checks the script runs"
        )

    for problem in problems:
        print(f"  FAIL {problem}")
    for line in ok:
        print(f"  PASS {line}")
    if problems:
        print(
            "\nrewrite the snapshot when the script changes: it is a record of a run, "
            "not a second copy of the truth",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
