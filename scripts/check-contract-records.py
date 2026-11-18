#!/usr/bin/env python3
"""Check that the contract table's records describe the live contract check.

    uv run --no-sync python scripts/check-contract-records.py
    uv run --no-sync python scripts/check-contract-records.py --expect without-jadx

``scripts/verify-public-contracts.py`` proves that the public contracts hold:
it starts the API, analyses the demo APK, and checks every response against
the table in ``docs/architecture/public-contracts.md``. The table keeps a
record of what a live run looked like as well -- section 7's tables say how
many checks each backend configuration exercised, how many of them passed,
and what the script exited with.

The live check answers "do the contracts hold". Nothing answered "does the
record still describe the run". A table that had stopped matching the
script stayed in the repository behind a green job: the reader is told that
47 checks ran and all of them passed, while the script now runs a different
number of them and one of the new ones fails. The record is the promise
that the live check is the same check that was recorded.

This script closes that gap. It reads the recorded configurations out of the
table, runs the live check, and asks whether the run it just made is one the
table records. It runs the live check itself rather than reading somebody
else's output, so that the comparison cannot drift into comparing two
different runs.

``--expect`` names the backend configuration the run is supposed to be in:
``with-jadx`` or ``without-jadx``. The table records both, and the two rows
differ by one REST check -- the source headers, which are only asked for
when the decompiler answered. A run that lands in the other configuration
is not a broken contract but the wrong machine, and the exit code says so.

The exit code says which kind of wrongness it found:

* 0 -- the contracts hold, and the live run is one the table records.
* 1 -- a contract failed, the live check crashed, or the live run no longer
  matches any recorded configuration. Either the table is out of date or
  the script changed; both are worth a red build.
* 2 -- the environment could not exercise the paths the record describes:
  the server did not come up, the analysis never finished, or the machine
  is not in the configuration the step asked for. That is not a broken
  contract, and it must not look like one. A gate that reports "not ready"
  as "failed" teaches its readers to ignore it, and a gate that reports
  "not ready" as "passed" is worse -- it is green without having checked
  anything.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "docs" / "architecture" / "public-contracts.md"
LIVE_CHECK = REPO_ROOT / "scripts" / "verify-public-contracts.py"

#: How long the live check may take. The API starts, the demo APK is
#: analysed, and every endpoint is asked; with all three backends that is
#: a couple of minutes.
TIMEOUT_SECONDS = 900

#: A recorded run, as section 7's tables write it: what was run, which
#: backends were in the machine, how many checks ran, how many passed and
#: what the script exited with. The table writes the split in fullwidth
#: parentheses.
RECORDED_RUN = re.compile(
    r"^\|\s*(?P<label>[^|]*)\|\s*(?P<backends>[^|]*)\|\s*"
    r"(?P<total>\d+)（(?P<rest>\d+) REST \+ (?P<mcp>\d+) MCP \+ (?P<cli>\d+) CLI）"  # noqa: RUF001
    r"\s*\|\s*\*\*(?P<passed>\d+)/(?P<passed_total>\d+)\*\*\s*\|\s*(?P<exit_code>\d+)\s*\|",
    re.MULTILINE,
)

#: The backends the live check can be run with.
BACKENDS = ("jadx", "apktool", "androguard")

#: The section headers the live check prints.
SECTION_LINE = re.compile(r"^==\s+(.+?)\s+==$")

#: The summary line the live check prints when it is done.
SUMMARY_LINE = re.compile(r"^(\d+)/(\d+) checks passed$")


@dataclass(frozen=True)
class Configuration:
    """One run of the live check: how much it exercised and how much passed."""

    total: int
    rest: int
    mcp: int
    cli: int
    passed: int
    exit_code: int
    backends: frozenset[str] = frozenset()

    def describe(self) -> str:
        available = ", ".join(sorted(self.backends)) or "no backend"
        return (
            f"{self.total} checks ({self.rest} REST + {self.mcp} MCP + {self.cli} CLI), "
            f"{self.passed} passed, exit {self.exit_code}, backends: {available}"
        )

    def shape(self) -> tuple[int, int, int, int, int, int]:
        """The part of a run that the record has to match.

        The backends are not part of it: a live run does not say which
        backends it used, it only exercises a different number of checks
        depending on which ones were there. Which configuration a run was
        in is read back from the recorded row it matches.
        """
        return (self.total, self.rest, self.mcp, self.cli, self.passed, self.exit_code)

    def has_jadx(self) -> bool:
        return "jadx" in self.backends


def available_backends(cell: str) -> frozenset[str]:
    """The backends a recorded row says were in the machine.

    The table names a backend and the version it had when the backend was
    there, and names it differently when it was not ("JADX and Apktool are
    both not in the environment"). A name followed by a number is a backend
    that was installed.
    """
    found = set()
    for name in BACKENDS:
        if re.search(rf"{name}\s*\d", cell, re.IGNORECASE):
            found.add(name)
    return frozenset(found)


def recorded_configurations(text: str) -> list[Configuration]:
    """Every run section 7 records, in the order the table lists them."""
    found = []
    for match in RECORDED_RUN.finditer(text):
        found.append(
            Configuration(
                total=int(match.group("total")),
                rest=int(match.group("rest")),
                mcp=int(match.group("mcp")),
                cli=int(match.group("cli")),
                passed=int(match.group("passed")),
                exit_code=int(match.group("exit_code")),
                backends=available_backends(match.group("backends")),
            )
        )
    return found


def section_of(title: str) -> str | None:
    """The key a section header belongs to."""
    lowered = title.lower()
    if "rest" in lowered:
        return "rest"
    if "mcp" in lowered:
        return "mcp"
    if "cli" in lowered:
        return "cli"
    return None


def parse_live_output(output: str) -> tuple[dict[str, int], int, int]:
    """What the live check did: checks per section, and its own summary.

    Returns the number of checks per section, the total the script
    reported, and the number that passed.
    """
    counts: dict[str, int] = {"rest": 0, "mcp": 0, "cli": 0}
    section: str | None = None
    total = 0
    passed = 0
    for line in output.splitlines():
        header = SECTION_LINE.match(line.strip())
        if header is not None:
            section = section_of(header.group(1))
            continue
        body = line.strip()
        if body.startswith("PASS ") or body.startswith("FAIL "):
            total += 1
            if body.startswith("PASS "):
                passed += 1
            if section is not None:
                counts[section] += 1
            continue
        summary = SUMMARY_LINE.match(body)
        if summary is not None:
            total = int(summary.group(1))
            passed = int(summary.group(2))
    return counts, total, passed


def run_live_check() -> tuple[str, int, bool]:
    """Run the live check and return its output, its exit code, and whether it crashed."""
    env = dict(os.environ)
    # The parent and the child have to agree on the encoding: the child
    # prints Chinese text, and a parent that decodes it with the platform's
    # default codec reads the bytes as something else entirely.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        completed = subprocess.run(
            [sys.executable, str(LIVE_CHECK)],
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
        return "", 2, False
    output = completed.stdout + ("\n" + completed.stderr if completed.stderr else "")
    crashed = "Traceback (most recent call last)" in output
    return output, completed.returncode, crashed


def report(problems: list[str], ok: list[str]) -> int:
    """Print the verdict. ``0`` when everything held, ``1`` otherwise."""
    for line in ok:
        print(f"  PASS {line}")
    for line in problems:
        print(f"  FAIL {line}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        choices=("with-jadx", "without-jadx"),
        help="the backend configuration the live run is supposed to be in",
    )
    args = parser.parse_args()

    if not CONTRACTS.is_file():
        print(f"FAIL the contract table is missing: {CONTRACTS}", file=sys.stderr)
        return 1
    if not LIVE_CHECK.is_file():
        print(f"FAIL the live check is missing: {LIVE_CHECK}", file=sys.stderr)
        return 1

    recorded = recorded_configurations(CONTRACTS.read_text(encoding="utf-8"))
    if not recorded:
        print(
            "FAIL the contract table records no run: section 7 has to say how many "
            "checks each backend configuration exercised",
            file=sys.stderr,
        )
        return 1

    problems: list[str] = []
    ok: list[str] = []

    # The table has to add up before it can be compared with anything.
    for run in recorded:
        if run.rest + run.mcp + run.cli != run.total:
            problems.append(
                f"the recorded run {run.describe()} does not add up: "
                f"{run.rest} + {run.mcp} + {run.cli} is not {run.total}"
            )
        if run.passed > run.total:
            problems.append(f"the recorded run {run.describe()} claims more passes than checks")
    if not problems:
        ok.append(f"the table records {len(recorded)} run(s), and they add up")

    # A recorded run that failed is history, not a configuration: the table
    # keeps the runs that went wrong next to the ones that worked, and only
    # the working ones describe what a run is supposed to look like now.
    current = [run for run in recorded if run.passed == run.total and run.exit_code == 0]
    if not current:
        problems.append("the table records no passing run to compare a live run against")
        return report(problems, ok)

    print("== the live contract check ==", flush=True)
    output, exit_code, crashed = run_live_check()
    if output:
        print(output.rstrip())
    print()

    if crashed:
        problems.append(
            "the live check crashed: it raised an exception instead of reporting "
            "which contract failed"
        )
        return report(problems, ok)

    counts, total, passed = parse_live_output(output)
    if total == 0:
        print(
            "  the live check exercised none of the recorded paths, and printed no "
            "summary; the environment is not ready to answer the question",
            file=sys.stderr,
        )
        return 2

    observed = Configuration(
        total=total,
        rest=counts["rest"],
        mcp=counts["mcp"],
        cli=counts["cli"],
        passed=passed,
        exit_code=exit_code,
    )
    print(f"== the live run against the record ==\n  the live run: {observed.describe()}")

    matched = [run for run in current if run.shape() == observed.shape()]
    if not matched:
        smallest = min(run.total for run in current)
        if observed.total < smallest:
            # Fewer checks than any recorded configuration exercised: the run
            # never reached the paths the record describes. That is an
            # environment that is not ready, not a contract that is broken.
            print(
                f"  the live run exercised {observed.total} checks, and every recorded "
                f"configuration exercises at least {smallest}: the environment did not "
                "reach the paths the record describes",
                file=sys.stderr,
            )
            return 2
        problems.append(
            f"the live run is not one the table records: {observed.describe()}; the "
            f"table records {'; '.join(run.describe() for run in current)}"
        )
        return report(problems, ok)

    if args.expect is not None:
        wanted = args.expect == "with-jadx"
        if not any(run.has_jadx() == wanted for run in current):
            problems.append(f"the table records no run for the {args.expect} configuration")
            return report(problems, ok)
        if not any(run.has_jadx() == wanted for run in matched):
            print(
                f"  the live run landed in the other configuration: {observed.describe()}; "
                f"this step asked for {args.expect}. The machine is not the one the "
                "record was written on.",
                file=sys.stderr,
            )
            return 2
        ok.append(f"the live run is in the {args.expect} configuration, as asked")

    ok.append(f"the live run is one the table records: {observed.describe()}")
    return report(problems, ok)


if __name__ == "__main__":
    sys.exit(main())
