#!/usr/bin/env python3
"""Refresh the machine-derived figures in the Phase 1 execution report.

    uv run python scripts/refresh-report-figures.py           # measure and write
    uv run python scripts/refresh-report-figures.py --check   # measure and compare

The execution report is written for a human reader: its structure, its reasoning and
its conclusions are hand-written. The numbers inside it are not — they are
measurements, and a measurement that lives only inside a sentence goes stale the
moment somebody adds a test. This script owns those numbers.

Every generated number in the report sits between two markers:

    <!--fig:tests.total-->275<!--/fig-->

The markers are HTML comments, so a rendered document shows nothing but the number.
The script rewrites what is between them; ``tests/test_docs.py`` checks that what is
between them is what the code actually does.

Two rules keep the report honest:

* A measurement that could not be taken is not written. A partial run — missing
  analysis backends, missing fixtures — produces lower coverage and a different
  pass/skip split, and publishing that as *the* number would be a small lie. The
  script refreshes what it can, says what it could not measure, and leaves the
  coverage figures alone until a complete run is possible.
* The report states the basis of every environment-dependent number, so a reader
  knows what to install before trying to reproduce one.

The record of the last measurement is written into the report as well, in a
machine-readable comment. It carries the fingerprint of the source tree the
coverage numbers describe, which is what lets the test suite notice that the
figures have gone stale.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
SOURCE_ROOT = REPO_ROOT / "src" / "dexatlas"
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Coverage is measured on the package, so module paths are relative to it.
SOURCE_PREFIX = "src/dexatlas/"

#: A first-party module below this coverage is a weak spot the report must disclose.
WEAK_MODULE_PERCENT = 90.0

#: ``<!--fig:key-->value<!--/fig-->`` — everything between the markers is generated.
FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)

#: ``<!--report-figures:{...}-->`` — the machine-readable record of the measurement.
RECORD = re.compile(r"<!--report-figures:(.*?)-->", re.DOTALL)

#: pytest's collection summary, e.g. "196/275 tests collected (79 deselected)".
COLLECTED = re.compile(r"(\d+)(?:/(\d+))? tests collected")

#: The outcome words pytest prints in its final summary line.
OUTCOMES = ("passed", "failed", "skipped", "xfailed", "xpassed", "error", "deselected")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a command in the repository and capture what it says."""
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def collected_tests(marker: str) -> tuple[int, int]:
    """Ask pytest's own collector how many tests a marker expression selects.

    Returns the number of selected tests and the number collected in total. The
    collector is used rather than a count of ``@pytest.mark.slow`` decorators so
    the figure cannot drift from what actually runs.
    """
    result = run(
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        "-m",
        marker,
    )
    match = COLLECTED.search(result.stdout)
    if not match:
        raise SystemExit(f"could not read pytest's collection count:\n{result.stdout[-2000:]}")
    return int(match.group(1)), int(match.group(2) or match.group(1))


def outcome_counts(output: str) -> dict[str, int]:
    """Read pytest's final summary: how many tests passed, skipped, xfailed."""
    counts: dict[str, int] = {}
    for name in OUTCOMES:
        found = re.findall(rf"(\d+) {name}s?\b", output)
        counts[name] = int(found[-1]) if found else 0
    return counts


def measure_suite() -> dict[str, Any]:
    """Run the whole suite with coverage and report what it measured."""
    result = run(sys.executable, "-m", "pytest", "--cov=dexatlas", "--cov-report=term")
    data = json.loads(run(sys.executable, "-m", "coverage", "json", "-o", "-").stdout)

    files: dict[str, list[int]] = {}
    for name, entry in data["files"].items():
        relative = name.replace("\\", "/")
        if not relative.startswith(SOURCE_PREFIX):
            continue
        summary = entry["summary"]
        files[relative[len(SOURCE_PREFIX) :]] = [
            summary["num_statements"],
            summary["missing_lines"],
        ]

    totals = data["totals"]
    return {
        "outcome": outcome_counts(result.stdout),
        "files": files,
        "statements": totals["num_statements"],
        "missing": totals["missing_lines"],
    }


def source_fingerprint() -> str:
    """A hash of the source tree the coverage figures describe.

    When the code changes, the coverage number in the report stops being true. A
    fingerprint makes that visible without re-measuring: the test suite recomputes
    it and asks for a refresh.
    """
    digest = hashlib.sha256()
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def code_facts() -> dict[str, int]:
    """Counts that come from reading the code rather than running it."""
    cli = (REPO_ROOT / "src" / "dexatlas" / "cli" / "main.py").read_text(encoding="utf-8")
    api = (REPO_ROOT / "src" / "dexatlas" / "api" / "app.py").read_text(encoding="utf-8")
    return {
        "cli_commands": cli.count("@app.command()"),
        "api_endpoints": len(re.findall(r"@app\.(get|post|delete|put)\(", api)),
        "sample_apks": len(list(EXAMPLES_ROOT.rglob("*.apk"))),
    }


def build_record(measurement: dict[str, Any], fast: int, slow: int, total: int) -> dict[str, Any]:
    """The record of one measurement: everything the report can state."""
    outcome = measurement["outcome"]
    return {
        "schema": 1,
        "code": code_facts(),
        "coverage": {
            "files": measurement["files"],
            "missing": measurement["missing"],
            "statements": measurement["statements"],
        },
        "source_fingerprint": source_fingerprint(),
        "suite": {
            "passed": outcome["passed"],
            "skipped": outcome["skipped"],
            "xfailed": outcome["xfailed"],
        },
        "tests": {"fast": fast, "slow": slow, "total": total},
    }


def percent(covered: int, total: int) -> str:
    """Coverage as the report states it: one decimal, like every other figure."""
    return f"{covered / total * 100:.1f}%" if total else "n/a"


def render_figures(record: dict[str, Any]) -> dict[str, str]:
    """Turn a record into the strings the report shows between the markers."""
    code = record["code"]
    tests = record["tests"]
    suite = record["suite"]
    coverage = record["coverage"]
    covered = coverage["statements"] - coverage["missing"]

    values = {
        "cli.commands": str(code["cli_commands"]),
        "api.endpoints": str(code["api_endpoints"]),
        "samples.apks": str(code["sample_apks"]),
        "tests.total": str(tests["total"]),
        "tests.fast": str(tests["fast"]),
        "tests.slow": str(tests["slow"]),
        "suite.passed": str(suite["passed"]),
        "suite.skipped": str(suite["skipped"]),
        "suite.xfailed": str(suite["xfailed"]),
        "coverage.pct": percent(covered, coverage["statements"]),
        "coverage.covered": str(covered),
        "coverage.total": str(coverage["statements"]),
        "coverage.missed": str(coverage["missing"]),
    }
    for module, (statements, missing) in coverage["files"].items():
        values[f"coverage.file.{module}.pct"] = percent(statements - missing, statements)
        values[f"coverage.file.{module}.statements"] = str(statements)
        values[f"coverage.file.{module}.missed"] = str(missing)
    return values


def apply_figures(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Write the values into the markers. Returns the text and the unknown keys."""
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            unknown.append(key)
            return match.group(0)
        return f"<!--fig:{key}-->{values[key]}<!--/fig-->"

    return FIGURE.sub(replace, text), unknown


def apply_record(text: str, record: dict[str, Any]) -> str:
    """Write the record into the report, replacing the previous one."""
    block = "<!--report-figures:" + render_record(record) + "-->"
    if RECORD.search(text):
        return RECORD.sub(lambda _: block, text, count=1)
    return text.rstrip("\n") + "\n\n" + block + "\n"


def render_record(record: dict[str, Any]) -> str:
    """The record as JSON, with one line per module.

    ``json.dumps`` would spread every module's two numbers over four lines, which
    would bury the report under a hundred lines of JSON for no gain.
    """
    dumped = json.dumps(record, indent=2, sort_keys=True)
    return re.sub(r"\[\s*\n\s*(\d+),\s*\n\s*(\d+)\s*\n\s*\]", r"[\1, \2]", dumped)


def read_record(text: str) -> dict[str, Any]:
    """The record of the last measurement, or an empty one."""
    match = RECORD.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def undisclosed_modules(record: dict[str, Any], text: str) -> list[str]:
    """Weak modules the report does not mention — an incomplete disclosure."""
    stated = {match.group(1) for match in FIGURE.finditer(text)}
    weak = {
        module
        for module, (statements, missing) in record["coverage"]["files"].items()
        if statements and (statements - missing) / statements * 100 < WEAK_MODULE_PERCENT
    }
    return sorted(module for module in weak if f"coverage.file.{module}.pct" not in stated)


def missing_prerequisites() -> list[str]:
    """What a complete measurement needs and this machine may not have.

    Only used to explain a partial measurement. Whether the measurement was
    complete is decided by what the suite did, not by what is installed here.
    """
    missing: list[str] = []
    if not shutil.which("jadx") and not os.environ.get("DEXATLAS_JADX_PATH"):
        missing.append("JADX (bash scripts/install-backends.sh)")
    if not shutil.which("apktool") and not os.environ.get("DEXATLAS_APKTOOL_JAR"):
        missing.append("Apktool (bash scripts/install-backends.sh)")
    if find_spec("androguard") is None:
        missing.append("androguard (uv sync --extra analysis)")
    if find_spec("PIL") is None:
        missing.append("Pillow (uv sync --extra demo)")
    fixtures = REPO_ROOT / "fixtures" / "apk"
    if not all((fixtures / name).is_file() for name in ("TestActivity.apk", "multidex.apk")):
        missing.append("the integration fixtures (bash scripts/fetch-fixtures.sh)")
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the generated figures in the Phase 1 execution report."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the report with a fresh measurement instead of writing",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPORT_PATH,
        help="the report to refresh (default: docs/reports/phase1-execution-report.md)",
    )
    args = parser.parse_args(argv)

    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    text = report_path.read_text(encoding="utf-8")
    previous = read_record(text)

    print("Collecting the test suite...")
    fast, total = collected_tests("not slow")
    slow, _ = collected_tests("slow")

    print("Running the suite with coverage (this takes a couple of minutes)...")
    measurement = measure_suite()
    outcome = measurement["outcome"]

    # A measurement is complete when it ran the same set of tests the recorded one
    # ran. The canonical basis skips nothing; a tree that has grown a test which
    # always skips is still a tree whose basis has not changed.
    recorded_skips = previous.get("suite", {}).get("skipped")
    complete = (
        outcome["skipped"] == recorded_skips
        if recorded_skips is not None
        else outcome["skipped"] == 0
    )

    record = build_record(measurement, fast, slow, total)
    if not complete:
        if not previous.get("coverage") or not previous.get("suite"):
            raise SystemExit(
                "this machine could not take a complete measurement and the report has no "
                "recorded measurement to keep.\n"
                "The report's coverage figures describe a run in which every test "
                "executed; this one skipped "
                f"{outcome['skipped']} of them.\n"
                "Install what the report lists as its basis, then run this again:\n  "
                + "\n  ".join(missing_prerequisites() or ["(nothing obvious is missing)"])
            )
        record["coverage"] = previous["coverage"]
        record["suite"] = previous["suite"]
        record["source_fingerprint"] = previous["source_fingerprint"]

    values = render_figures(record)
    updated, unknown = apply_figures(text, values)
    updated = apply_record(updated, record)

    if unknown:
        raise SystemExit(
            "the report refers to figures this script does not know how to fill in: "
            + ", ".join(sorted(set(unknown)))
        )

    hidden = undisclosed_modules(record, updated)
    if hidden:
        print(
            "These modules are below "
            f"{WEAK_MODULE_PERCENT}% but the report does not list them: " + ", ".join(hidden)
        )

    # One line per figure, not per occurrence: the same figure is stated in
    # several places, and the reader wants to know which ones moved.
    changes: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for key, old in FIGURE.findall(text):
        new = values.get(key)
        if new is not None and new != old and key not in seen:
            seen.add(key)
            changes.append((key, old, new))

    if args.check:
        if updated == text:
            print("The report matches a fresh measurement.")
        else:
            for key, old, new in changes:
                print(f"{key}: {old} -> {new}")
            print("The report does not match a fresh measurement.")
        warn(outcome, complete)
        return 0 if updated == text else 1

    report_path.write_bytes(updated.encode("utf-8"))
    if changes:
        for key, old, new in changes:
            print(f"{key}: {old} -> {new}")
    if updated == text:
        print("The report was already up to date.")
    else:
        print(f"Updated {report_path.relative_to(REPO_ROOT)}.")
    warn(outcome, complete)
    return 0


def warn(outcome: dict[str, int], complete: bool) -> None:
    """Say plainly what this run could and could not measure."""
    if not complete:
        print(
            "\nThis run was partial: "
            + ", ".join(
                f"{name}={outcome[name]}"
                for name in ("passed", "skipped", "xfailed")
                if outcome[name]
            )
            + ".\nThe coverage figures were left as they were, because they describe a "
            "complete measurement. A complete one needs:\n  "
            + "\n  ".join(missing_prerequisites() or ["(nothing obvious is missing)"])
        )
    if outcome["failed"] or outcome["error"]:
        print(
            f"\nThe suite itself did not pass ({outcome['failed']} failed, "
            f"{outcome['error']} errors). The numbers above describe a tree that does "
            "not pass its own tests; re-run this once it is green."
        )


if __name__ == "__main__":
    raise SystemExit(main())
