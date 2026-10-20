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

Why the measurement is split in two
-----------------------------------

The report's numbers decide whether ``tests/test_docs.py`` passes, so measuring
the suite and writing the numbers into the report is circular: the report the
suite sees is the report the suite is about to change. A refresh that measured
once and wrote once would record the *failing* state of the self-checks — the
state they are in precisely because the numbers are stale — and a second run
would be needed to correct it. An honest tool should not ask for two.

So the refresh measures the two kinds of test apart:

* The **code tests** — everything except the report's own self-checks. They fail
  when the code is broken, and a failure here is a real one.
* The **self-checks** — the tests that read the report's generated numbers. They
  fail when the report is out of date, which is not the same thing at all.

The code tests are measured first, and their failures are reported by name. The
self-checks are then measured against a *candidate* report — one the script
builds in memory and points the checks at, so the file on disk is never caught
half-refreshed. Writing the numbers changes what the self-checks say, so the
candidate is rebuilt and re-measured until the two stop moving. One run of the
script is enough: the report it leaves behind is one the self-checks pass, and
running the script again changes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
#: The status page states the same figures as the report — the test counts and
#: the coverage — and it is the first thing a reader looks at, so a number
#: that has gone stale there is worth catching. It is refreshed together with
#: the report it summarises; pointing the script at another document refreshes
#: only that document, because the test suite refreshes copies of the report
#: and must not write to the real status page while it does so.
STATUS_PATH = REPO_ROOT / "docs" / "status.md"
SOURCE_ROOT = REPO_ROOT / "src" / "dexatlas"
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Coverage is measured on the package, so module paths are relative to it.
SOURCE_PREFIX = "src/dexatlas/"

#: A first-party module below this coverage is a weak spot the report must disclose.
WEAK_MODULE_PERCENT = 90.0

#: The released versions the report compares its own figures against. Their test
#: counts belong to those tags, not to the current tree, so they are measured
#: where they live -- in an archive of the tag itself.
HISTORY_TAGS = ("v0.1.0", "v0.1.1", "v0.1.2", "v0.1.3")

#: ``<!--fig:key-->value<!--/fig-->`` — everything between the markers is generated.
FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)

#: ``<!--report-figures:{...}-->`` — the machine-readable record of the measurement.
RECORD = re.compile(r"<!--report-figures:(.*?)-->", re.DOTALL)

#: A row of the generated weak-module table: "| `core/pipeline.py` | 96.9% | 7 / 228 |".
TABLE_ROW = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)

#: pytest's collection summary, e.g. "196/275 tests collected (79 deselected)".
COLLECTED = re.compile(r"(\d+)(?:/(\d+))? tests collected")

#: The outcome words pytest prints in its final summary line.
OUTCOMES = ("passed", "failed", "skipped", "xfailed", "xpassed", "error", "deselected")

#: The self-checks of the report share this name. They read the report's generated
#: numbers, so they fail when the report is out of date. That is not the same as
#: the code being broken, and the refresh must not confuse the two: the first is
#: its own job to fix, the second belongs to the reader.
REPORT_CHECK = "test_execution_report"

#: How many times the refresh may re-measure the self-checks before it gives up.
MAX_ROUNDS = 3

#: The environment variable the self-checks read the report from. The refresh
#: points it at a candidate copy, so a self-check never sees a half-written
#: report and the report on disk is only ever replaced whole.
REPORT_PATH_ENV = "DEXATLAS_REPORT_PATH"

#: pytest's short summary: "FAILED tests/test_x.py::test_y - AssertionError: ...".
FAILED_LINE = re.compile(r"^(?:FAILED|ERROR) (\S+)(?: - (.*))?$", re.MULTILINE)


@dataclass(frozen=True)
class Outcome:
    """What one run of a set of tests measured."""

    counts: dict[str, int]
    failures: tuple[str, ...] = ()

    def describe(self) -> str:
        parts = [
            f"{name}={self.counts[name]}"
            for name in ("passed", "failed", "skipped", "xfailed")
            if self.counts.get(name)
        ]
        return ", ".join(parts) or "nothing ran"


@dataclass(frozen=True)
class Coverage:
    """What a coverage run measured: per module, and in total."""

    files: dict[str, list[int]]
    statements: int
    missing: int


@dataclass(frozen=True)
class Refresh:
    """The result of bringing a report and its self-checks into agreement."""

    text: str
    record: dict[str, Any]
    checks: Outcome
    converged: bool
    rounds: int


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command in the repository and capture what it says."""
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env)


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


def failed_tests(output: str) -> tuple[str, ...]:
    """The tests pytest reported as failed or errored, by name.

    A count says how many; a name says which. The self-checks are measured
    apart, so a failure listed here is a failure of the code, and the reader has
    to be able to see it.
    """
    failures: list[str] = []
    for node, message in FAILED_LINE.findall(output):
        summary = message.splitlines()[0].strip() if message else ""
        failures.append(f"{node} - {summary}" if summary else node)
    return tuple(dict.fromkeys(failures))


def read_outcome(output: str) -> Outcome:
    """Read a pytest run's summary: the counts and the names that failed."""
    return Outcome(counts=outcome_counts(output), failures=failed_tests(output))


def read_coverage() -> Coverage:
    """Read the coverage the runs produced."""
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
    return Coverage(
        files=files,
        statements=totals["num_statements"],
        missing=totals["missing_lines"],
    )


def measure_code_tests() -> Outcome:
    """Run the whole suite, except the report's own self-checks, with coverage.

    The self-checks are left out on purpose. They read the report's generated
    numbers, so a report that is out of date makes them fail, and counting that
    failure would describe a tree as broken when it is merely out of date. They
    are measured on their own afterwards, against a report that is already
    consistent, and the two results are added up.
    """
    result = run(
        sys.executable,
        "-m",
        "pytest",
        "--cov=dexatlas",
        "--cov-report=term",
        "-k",
        f"not {REPORT_CHECK}",
    )
    return read_outcome(result.stdout)


def measure_report_checks(candidate: str, report_path: Path) -> Outcome:
    """Measure the report's self-checks against a candidate report.

    The candidate is written to a temporary file and the checks are pointed at
    it, so a check never sees the report half-refreshed and the report on disk
    is only ever replaced whole. The coverage of this run is appended to the
    coverage of the code tests, so the figures describe the whole suite.
    """
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / report_path.name
        path.write_text(candidate, encoding="utf-8")
        env = dict(os.environ)
        env[REPORT_PATH_ENV] = str(path)
        result = run(
            sys.executable,
            "-m",
            "pytest",
            "--cov=dexatlas",
            "--cov-append",
            "-k",
            REPORT_CHECK,
            env=env,
        )
    return read_outcome(result.stdout)


def add_counts(first: dict[str, int], second: dict[str, int]) -> dict[str, int]:
    """Add two runs' outcomes together.

    ``deselected`` is left out: the two runs select each other's complement, so
    their deselected counts say nothing once added.
    """
    names = [name for name in OUTCOMES if name != "deselected"]
    return {name: first.get(name, 0) + second.get(name, 0) for name in names}


def source_fingerprint() -> str:
    """A hash of the source tree the coverage figures describe.

    When the code changes, the coverage number in the report stops being true. A
    fingerprint makes that visible without re-measuring: the test suite recomputes
    it and asks for a refresh.

    Line endings are normalised before hashing. Git checks out CRLF on Windows and
    LF on Linux, so hashing the raw bytes would give the same source two different
    fingerprints -- and the report would be declared stale on every platform but
    the one it was measured on. The fingerprint answers "is this the same code?",
    not "is this the same byte sequence?".
    """
    digest = hashlib.sha256()
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
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


def collected_at_tag(tag: str) -> int | None:
    """How many tests a released version's suite contained.

    The number belongs to that tag, not to the current tree, so it is measured
    where it lives: an archive of the tag, collected by pytest. Nothing is
    executed, so the measurement needs no backends, no fixtures and no
    workspace -- it is the same on every machine, and there is no such thing as
    a partial one.

    ``None`` means the tag could not be measured (no git, no such tag, no
    pytest), and the caller keeps the recorded value rather than guessing.
    """
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / tag
        root.mkdir()

        archive = subprocess.run(
            ["git", "archive", tag],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if archive.returncode != 0:
            return None
        try:
            with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
                tar.extractall(root, filter="data")
        except (tarfile.TarError, OSError):
            return None

        # The tag's own source has to win over the installed one, so it goes
        # first on the import path.
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(root / "src"), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])]
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    match = COLLECTED.search(result.stdout)
    return int(match.group(1)) if match else None


def history_figures(text: str, previous: dict[str, Any]) -> dict[str, Any]:
    """The test count of each released version the report compares itself against.

    A tag that cannot be measured keeps the value it already had -- the same
    rule the coverage figures follow when a measurement is partial. A tag that
    was never measured and never recorded keeps whatever the report already
    says, so a missing git checkout cannot stop the refresh over a footnote.
    """
    history: dict[str, Any] = dict(previous.get("history", {}))
    for tag in HISTORY_TAGS:
        count = collected_at_tag(tag)
        if count is not None:
            history[tag] = {"tests": count}
            continue
        if tag in history:
            continue
        for key, value in FIGURE.findall(text):
            if key == f"history.{tag}.tests" and value.isdigit():
                history[tag] = {"tests": int(value)}
                break
    return history


def build_record(
    coverage: Coverage,
    suite: dict[str, int],
    fast: int,
    slow: int,
    total: int,
    history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The record of one measurement: everything the report can state."""
    return {
        "schema": 3,
        "code": code_facts(),
        "coverage": {
            "files": coverage.files,
            "missing": coverage.missing,
            "statements": coverage.statements,
        },
        "history": history or {},
        "source_fingerprint": source_fingerprint(),
        "suite": {
            "passed": suite.get("passed", 0),
            "skipped": suite.get("skipped", 0),
            "xfailed": suite.get("xfailed", 0),
        },
        "tests": {"fast": fast, "slow": slow, "total": total},
    }


def percent(covered: int, total: int) -> str:
    """Coverage as the report states it: one decimal, like every other figure."""
    return f"{covered / total * 100:.1f}%" if total else "n/a"


def weak_modules(files: dict[str, list[int]]) -> list[str]:
    """The modules below the disclosure threshold, weakest first.

    The report promises to show where it is weak. A module that falls below
    the threshold and is not mentioned is a gap in that promise, so the list
    is derived from the measurement rather than written out by hand.
    """
    weak = [
        (module, statements, missing)
        for module, (statements, missing) in files.items()
        if statements and (statements - missing) / statements * 100 < WEAK_MODULE_PERCENT
    ]
    weak.sort(key=lambda row: (row[1] - row[2]) / row[1] * 100)
    return [module for module, _, _ in weak]


def render_weak_modules(files: dict[str, list[int]]) -> str:
    """The weak-module table, as the report shows it.

    The table is generated, so it cannot name a module the measurement does
    not call weak, nor leave out one it does. The leading newline keeps the
    rows out of the opening HTML comment: a comment runs to the first ``-->``,
    and a table inside one would not render.
    """
    lines = [
        "| 模块 | 覆盖率 | 未覆盖行 / 总行数 |",
        "|------|--------|------------------|",
    ]
    modules = weak_modules(files)
    if not modules:
        lines.append(f"| 没有低于 {WEAK_MODULE_PERCENT:.0f}% 的模块 | — | — |")
    for module in modules:
        statements, missing = files[module]
        lines.append(
            f"| `{module}` | {percent(statements - missing, statements)} | {missing} / {statements} |"
        )
    return "\n" + "\n".join(lines) + "\n"


def listed_modules(text: str) -> list[str]:
    """The modules the report's weak-module table names, in the order it lists them."""
    table = "".join(value for key, value in FIGURE.findall(text) if key == "coverage.weak_modules")
    return TABLE_ROW.findall(table)


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
        "coverage.weak_modules": render_weak_modules(coverage["files"]),
    }
    for module, (statements, missing) in coverage["files"].items():
        values[f"coverage.file.{module}.pct"] = percent(statements - missing, statements)
        values[f"coverage.file.{module}.statements"] = str(statements)
        values[f"coverage.file.{module}.missed"] = str(missing)
    for tag, entry in record.get("history", {}).items():
        values[f"history.{tag}.tests"] = str(entry["tests"])
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


def render_report(text: str, record: dict[str, Any]) -> tuple[str, list[str]]:
    """Write a record into the report: the figures, and the record itself."""
    updated, unknown = apply_figures(text, render_figures(record))
    return apply_record(updated, record), unknown


def render_or_fail(text: str, record: dict[str, Any]) -> str:
    """Write a record into the report, or refuse to guess at a figure it cannot fill.

    A figure the script does not know how to fill in is a figure nobody can
    check, and guessing at one would put a number in the report that nothing
    stands behind. Better to stop and say which one it is.
    """
    updated, unknown = render_report(text, record)
    if unknown:
        raise SystemExit(
            "the report refers to figures this script does not know how to fill in: "
            + ", ".join(sorted(set(unknown)))
        )
    return updated


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
    """Weak modules the report's table does not mention — an incomplete disclosure.

    The table is generated, so this should never name anything. It is the
    check that says so: a table edited by hand, or a report written before the
    table was generated, is caught here instead of being believed.
    """
    listed = set(listed_modules(text))
    weak = weak_modules(record["coverage"]["files"])
    return [module for module in weak if module not in listed]


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


def converge(
    text: str,
    report_path: Path,
    code: Outcome,
    coverage: Coverage,
    fast: int,
    slow: int,
    total: int,
    history: dict[str, Any] | None = None,
) -> Refresh:
    """Bring the report and its self-checks into agreement, within one run.

    Writing the numbers changes what the self-checks say, so a refresh that
    measured once and wrote once could leave the two disagreeing: the numbers it
    wrote would describe a run in which the self-checks failed, and the
    self-checks fail because the numbers are stale. So the self-checks are
    measured against a candidate report, and the candidate is rebuilt until the
    two stop moving.

    The loop ends when a candidate is measured and nothing about it changes the
    measurement — at that point the report the refresh leaves behind is one the
    self-checks pass.
    """
    suite = dict(code.counts)
    record = build_record(coverage, suite, fast, slow, total, history)
    candidate = render_or_fail(text, record)

    checks = Outcome(counts={})
    for round_number in range(1, MAX_ROUNDS + 1):
        checks = measure_report_checks(candidate, report_path)
        new_coverage = read_coverage()
        new_suite = add_counts(code.counts, checks.counts)
        if new_suite == suite and new_coverage == coverage:
            return Refresh(
                text=candidate,
                record=record,
                checks=checks,
                converged=True,
                rounds=round_number,
            )
        suite, coverage = new_suite, new_coverage
        record = build_record(coverage, suite, fast, slow, total, history)
        candidate = render_or_fail(text, record)

    return Refresh(
        text=candidate,
        record=record,
        checks=checks,
        converged=False,
        rounds=MAX_ROUNDS,
    )


def figure_changes(text: str, record: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The figures the report states that a fresh measurement would change.

    One line per figure, not per occurrence: the same figure is stated in
    several places, and the reader wants to know which ones moved.
    """
    values = render_figures(record)
    changes: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for key, old in FIGURE.findall(text):
        new = values.get(key)
        if new is not None and new != old and key not in seen:
            seen.add(key)
            changes.append((key, old, new))
    return changes


def report_failures(headline: str, failures: tuple[str, ...]) -> None:
    """Name the tests that failed, so the reader can go and look at them."""
    print(f"\n{headline}")
    for failure in failures:
        print(f"  {failure}")


def display_path(path: Path) -> str:
    """The report's path, relative to the repository when it is inside it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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
    print(f"  {total} tests: {fast} fast, {slow} integration")

    print("Measuring the test counts of the released versions...")
    history = history_figures(text, previous)
    for tag in HISTORY_TAGS:
        entry = history.get(tag)
        print(f"  {tag}: {entry['tests'] if entry else 'not measured'} tests")

    print("Running the suite with coverage (this takes a couple of minutes)...")
    code = measure_code_tests()
    coverage = read_coverage()
    print(f"  {code.describe()} (the report's own self-checks are measured separately)")

    if code.failures:
        report_failures("The tree does not pass its own tests:", code.failures)
        print(
            "\nThe report was not touched. Its figures describe a run in which every "
            "test passed, and this run was not one. Fix the failures and run this again."
        )
        return 1

    # A measurement is complete when it ran the same set of tests the recorded one
    # ran. The canonical basis skips nothing; a tree that has grown a test which
    # always skips is still a tree whose basis has not changed. The self-checks
    # never skip, so the code tests alone decide this.
    recorded_skips = previous.get("suite", {}).get("skipped")
    skipped = code.counts.get("skipped", 0)
    complete = skipped == recorded_skips if recorded_skips is not None else skipped == 0

    if complete:
        print("Measuring the report's self-checks against a candidate report...")
        refresh = converge(text, report_path, code, coverage, fast, slow, total, history)
        record = refresh.record
        updated = refresh.text
        checks = refresh.checks
        if refresh.converged:
            print(
                f"  the self-checks agree with the refreshed report "
                f"({checks.describe()}) after {refresh.rounds} round(s)"
            )
        else:
            print(
                f"  the self-checks and the report did not settle after "
                f"{refresh.rounds} rounds ({checks.describe()})"
            )
    else:
        if not previous.get("coverage") or not previous.get("suite"):
            raise SystemExit(
                "this machine could not take a complete measurement and the report has no "
                "recorded measurement to keep.\n"
                "The report's coverage figures describe a run in which every test "
                "executed; this one skipped "
                f"{skipped} of them.\n"
                "Install what the report lists as its basis, then run this again:\n  "
                + "\n  ".join(missing_prerequisites() or ["(nothing obvious is missing)"])
            )
        # The coverage and the pass/skip split of a partial run describe a
        # different tree, so the previous measurement of them is kept.
        record = build_record(coverage, code.counts, fast, slow, total, history)
        record["coverage"] = previous["coverage"]
        record["suite"] = previous["suite"]
        record["source_fingerprint"] = previous["source_fingerprint"]
        updated = render_or_fail(text, record)
        checks = Outcome(counts={})

    hidden = undisclosed_modules(record, updated)
    if hidden:
        print(
            "These modules are below "
            f"{WEAK_MODULE_PERCENT}% but the report does not list them: " + ", ".join(hidden)
        )

    changes = figure_changes(text, record)

    if not complete:
        warn_partial(code)

    if args.check:
        if updated == text:
            print("The report matches a fresh measurement.")
        else:
            for key, old, new in changes:
                print(f"{key}: {old} -> {new}")
            print("The report does not match a fresh measurement.")
        matched = updated == text
    else:
        report_path.write_bytes(updated.encode("utf-8"))
        if changes:
            for key, old, new in changes:
                print(f"{key}: {old} -> {new}")
        if updated == text:
            print("The report was already up to date.")
        else:
            print(f"Updated {display_path(report_path)}.")
        matched = True

    if checks.failures:
        report_failures(
            "The report's self-checks still fail against the refreshed report, so this "
            "one needs a hand rather than another refresh:",
            checks.failures,
        )
        return 1
    return 0 if matched else 1


def warn_partial(code: Outcome) -> None:
    """Say plainly what this run could and could not measure."""
    print(
        "\nThis run was partial: "
        + ", ".join(
            f"{name}={code.counts.get(name, 0)}"
            for name in ("passed", "skipped", "xfailed")
            if code.counts.get(name)
        )
        + ".\nThe coverage figures were left as they were, because they describe a "
        "complete measurement. A complete one needs:\n  "
        + "\n  ".join(missing_prerequisites() or ["(nothing obvious is missing)"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
