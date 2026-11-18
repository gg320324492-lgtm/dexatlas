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
* A run that could not measure the tree says so with its exit code. It exits
  non-zero, because a gate that cannot fail is not a gate: ``--check`` on a
  tree it could not measure has verified nothing, and reporting success would
  be the small lie this script exists to avoid.
* The report states the basis of every environment-dependent number, so a reader
  knows what to install before trying to reproduce one.

The record of the last measurement is written into the report as well, in a
machine-readable comment. It carries the fingerprint of the tree the coverage
numbers describe -- the code, the suite that measured it, and the configuration
of the tools that did -- which is what lets the test suite notice that the
figures have gone stale.

The record also carries *which* tests sat out, not only how many. A count says
how many; the identities say which, and "the same number of tests skipped" is
not the same fact as "the same tests skipped".

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
import atexit
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import IO, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
#: The status page states the same figures as the report — the test counts and
#: the coverage — and it is the first thing a reader looks at, so a number
#: that has gone stale there is worth catching. It is refreshed together with
#: the report it summarises; pointing the script at another document refreshes
#: only that document, because the test suite refreshes copies of the report
#: and must not write to the real status page while it does so.
STATUS_PATH = REPO_ROOT / "docs" / "status.md"
#: The readmes carry the same two figures as a badge, and a badge is a URL:
#: it cannot hold the report's markers, so its number was written by hand --
#: and a hand-written number drifts the moment the code changes. The number
#: is measured here and written into the URL, so the badge is a measurement
#: too. A readme without the badge is left alone.
README_PATHS = (REPO_ROOT / "README.md", REPO_ROOT / "README.zh-CN.md")
SOURCE_ROOT = REPO_ROOT / "src" / "dexatlas"
#: The suite that measures the code. The pass/skip split the report states is
#: a property of this tree, so a change to it makes the numbers stale too.
TESTS_ROOT = REPO_ROOT / "tests"
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: The files that decide how the measurement comes out, besides the code and
#: the suite: the configuration of the tools that measure it, and the script
#: that asks them. A change to any of them changes what the numbers mean.
FINGERPRINT_FILES = ("pyproject.toml", "scripts/refresh-report-figures.py")

#: A row of the report's test-file table.
#:
#: The table is the reader's map from the report's claims to the code that
#: backs them. Its numbers are generated; its rows are written by hand.
TEST_FILE_ROW = re.compile(r"^\| `(test_[A-Za-z0-9_]+\.py)` \|", re.MULTILINE)

#: The section of the report that holds the test-file table.
TEST_FILE_SECTION = "### 2.1"

#: Coverage is measured on the package, so module paths are relative to it.
SOURCE_PREFIX = "src/dexatlas/"

#: The tool versions the provenance document states its outputs were produced
#: with. A measurement taken with a different version records different
#: numbers -- class counts, method counts, cross-references -- while the
#: document keeps claiming the pinned ones, so the script asks before it
#: writes. A backend that cannot be probed is not a mismatch: absence is
#: dealt with by the completeness check, not here.
DOCUMENTED_TOOL_VERSIONS = {
    "jadx": "1.5.2",
    "apktool": "2.11.1",
    "androguard": "4.1.4",
}


def _probe_tool_version(tool: str) -> str | None:
    """The version of one analysis backend, the way the code itself runs it.

    The probing goes through the backend's own resolution, so the version
    read here is the version an analysis would actually use -- not whatever
    a ``PATH`` search happens to find first.
    """
    try:
        if tool == "jadx":
            from dexatlas.config.settings import Settings
            from dexatlas.tools.jadx.adapter import JadxBackend

            return JadxBackend(Settings()).version()
        if tool == "apktool":
            from dexatlas.config.settings import Settings
            from dexatlas.tools.apktool.adapter import ApktoolBackend

            return ApktoolBackend(Settings()).version()
        if tool == "androguard":
            import importlib.metadata

            return importlib.metadata.version("androguard")
    except Exception:  # any probe failure means "unknown", not "wrong"
        return None
    return None


def documented_version_mismatches() -> list[str]:
    """Where this machine's backends disagree with the documented versions.

    The provenance document states that every output in it was produced with
    three pinned tool versions. A measurement taken with another version
    produces different numbers and the document would keep the old claim, so
    the measurement refuses to describe a run the document does not describe.
    """
    from dexatlas import __version__  # noqa: F401 - presence check only

    mismatches: list[str] = []
    for tool, documented in DOCUMENTED_TOOL_VERSIONS.items():
        found = _probe_tool_version(tool)
        if found is None:
            continue
        # The probes can answer "1.5.2" or "1.5.2 (something)"; the leading
        # version token is the comparison.
        version = found.strip().split()[0] if found.strip() else ""
        if version and version != documented:
            mismatches.append(f"{tool}: documented {documented}, this machine has {version}")
    return mismatches


#: The coverage configuration that makes the measurement subprocess-aware.
#:
#: ``tools/androguard/worker.py`` never runs in the test process: it is the
#: module an untrusted DEX is parsed in, and the service starts it as
#: ``python -m dexatlas.tools.androguard.worker``. A plain ``pytest --cov``
#: records nothing for it — not because the code did not run, but because
#: coverage is recorded per process, and the worker is another process. With
#: ``parallel = true`` every process writes its own data file, and
#: ``COVERAGE_PROCESS_START`` tells a Python that starts *after* the config to
#: measure itself; ``coverage combine`` then merges the parts into one
#: measurement that includes the worker's execution.
COVERAGE_RC = """[run]
parallel = true
source = dexatlas
"""

#: Where a measurement keeps the coverage data it collects.
#:
#: The coverage data file is shared by default: every process in a checkout
#: writes to ``.coverage``, and a ``pytest --cov`` that does not ask to
#: append replaces it wholesale. A measurement that reads the shared file can
#: therefore read another run's numbers -- the doc tests' coverage instead of
#: the suite's -- and publish them as the project's own. A measurement's data
#: file belongs to that measurement alone.
MEASUREMENT_DATA_DIR = REPO_ROOT / ".scratch" / "coverage"

#: The file that keeps two measurements out of the same checkout. It is
#: locked by the operating system, so it is released when the process that
#: holds it ends, however it ends.
MEASUREMENT_LOCK = REPO_ROOT / ".scratch" / "measure.lock"

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

#: The self-checks of the status page share this name, for the same reason:
#: they read the status page's generated numbers, so a status page that has
#: gone stale makes them fail, and that is the refresh's own problem rather
#: than a broken tree.
STATUS_CHECK = "test_status_page"

#: How many times the refresh may re-measure the self-checks before it gives up.
#:
#: The first candidate carries the code tests' counts alone, so a self-check
#: that compares the suite against the number of tests in the tree cannot
#: pass against it. Each round moves the numbers one step closer, and the
#: fourth is the one that settles them.
MAX_ROUNDS = 4

#: The environment variable the self-checks read the report from. The refresh
#: points it at a candidate copy, so a self-check never sees a half-written
#: report and the report on disk is only ever replaced whole.
REPORT_PATH_ENV = "DEXATLAS_REPORT_PATH"

#: The environment variable the status page's self-checks read the page from.
#: The refresh points it at a candidate copy, for the same reason.
STATUS_PATH_ENV = "DEXATLAS_STATUS_PATH"

#: pytest's short summary: "FAILED tests/test_x.py::test_y - AssertionError: ...".
FAILED_LINE = re.compile(r"^(?:FAILED|ERROR) (\S+)(?: - (.*))?$", re.MULTILINE)


@dataclass(frozen=True)
class Outcome:
    """What one run of a set of tests measured."""

    counts: dict[str, int]
    failures: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    """The identities of the tests that did not run.

    A count says how many tests skipped; the identities say which. "The same
    number of skips" is not the same fact as "the same skips" — a measurement
    that skipped a different set of tests measured a different tree, and
    publishing its numbers as *the* numbers would be a small lie.
    """

    xfailed: tuple[str, ...] = ()
    """The identities of the tests that failed as they were expected to."""

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
    status_text: str | None = None
    status_checks: Outcome = Outcome(counts={})


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command in the repository and capture what it says.

    The output is decoded as UTF-8 whatever the machine's locale is. In text
    mode without an encoding, a subprocess decodes with the platform default
    -- GBK here, UTF-8 on CI -- and a byte the decoding cannot read makes the
    stream ``None`` instead of raising, so the failure surfaces later as a
    type error about a value that was never a string. Every process this
    script starts is also run under ``PYTHONUTF8`` (see
    :func:`measurement_env`), so both sides of the pipe agree on the bytes.
    """
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )


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
    r"""Read pytest's final summary: how many tests passed, skipped, xfailed.

    Only pytest's own summary line -- the one between the ``=`` rules -- is
    read, never the whole output. A coverage or warning block elsewhere in
    the output can carry the same words ("16 skipped"), and a count read from
    there is a count of a different run: one measurement added such a stray
    to its own numbers and then could not account for the tree it had just
    measured.

    The match is not allowed to cross a line. A backslash-s matches a newline, so a
    pattern ending in ``\s*`` can start at an ``=`` in the middle of a line -- at
    the ``==`` of an ``assert 1682 == 1695`` -- and run on into the next line,
    swallowing the ``=`` rules that open pytest's summary line. The last match is
    then the tail of that summary line with nothing in it, and the counts of a run
    that passed twelve tests and failed one come out as zero. A summary line that
    is only there when a test failed is exactly the case that hid this: locally
    every self-check passed, on the runner one failed, and only there did the run
    print an ``assert`` line.
    """
    counts: dict[str, int] = {}
    summaries = [
        text for text in re.findall(r"=+[^\S\n]*([^\n]*?)[^\S\n]*=+", output) if text.strip()
    ]
    summary = summaries[-1] if summaries else output
    for name in OUTCOMES:
        found = re.findall(rf"(\d+) {name}s?\b", summary)
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


def discard_stale_coverage() -> None:
    """Delete any coverage data left behind by an earlier run.

    A measurement is only ever about one tree, and the coverage file is where
    a previous measurement leaves its numbers behind. A run that is
    interrupted before pytest-cov erases the file — a Ctrl-C, a crash, a
    collection that never got as far as the plugin — leaves those numbers in
    place, and the next measurement adds itself to them: the report would
    then describe a tree that no longer exists, and two measurements of the
    same tree would disagree by whatever the interrupted one had managed to
    cover. The file is removed before anything runs, so every measurement
    starts from nothing.
    """
    stale = sorted(REPO_ROOT.glob(".coverage*"))
    if not stale:
        return
    for path in stale:
        try:
            path.unlink()
        except OSError as error:
            # Windows refuses to delete a file another process has open, and
            # an open .coverage file is another measurement running in this
            # checkout. Two measurements would fight over the report, so the
            # run stops here with a message instead of a traceback -- and on
            # a platform that allows the delete, stopping is still right: a
            # measurement whose data file is being deleted under it is not a
            # measurement to add numbers to.
            raise SystemExit(
                f"could not remove {path}: {error}\n"
                "another measurement may be running in this checkout; "
                "wait for it to end and run this again."
            ) from error
    print(f"  discarded stale coverage data: {', '.join(path.name for path in stale)}")


def measurement_data_file(run_id: str | None = None) -> Path:
    """The coverage data file one measurement run uses.

    The default data file, ``.coverage``, belongs to everybody in the
    checkout: a ``pytest --cov`` started anywhere in it replaces that file
    wholesale, and a measurement that reads the shared file can end up
    publishing another run's numbers as the project's own. This file belongs
    to the run that names it, and the environment points at it, so a
    concurrent process cannot reach it.
    """
    identifier = run_id if run_id is not None else str(os.getpid())
    directory = MEASUREMENT_DATA_DIR / identifier
    directory.mkdir(parents=True, exist_ok=True)
    return directory / ".coverage"


def measurement_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment a measurement runs in.

    ``COVERAGE_FILE`` names the data file this run owns, so every process
    the measurement starts -- the suite, the coverage tool, the workers the
    tests spawn -- writes into it and nowhere else.

    ``PYTHONUTF8`` pins the child's text encoding: with it, both sides of the
    pipe read the same bytes as UTF-8. Without it the child writes in the
    platform's default -- GBK on a Chinese Windows, UTF-8 on CI -- and a
    parent that decodes as the other encoding reads a value that was never
    written.
    """
    env = dict(os.environ if base is None else base)
    env["COVERAGE_FILE"] = str(measurement_data_file())
    env.setdefault("PYTHONUTF8", "1")
    return env


def discard_stale_measurement_data() -> None:
    """Delete the data files an earlier run left in this run's directory.

    The directory is named after the process, and processes are reused, so
    it can hold the numbers of an earlier run that ended where this one
    starts. A measurement starts from nothing.
    """
    stale = sorted(measurement_data_file().parent.glob(".coverage*"))
    for path in stale:
        path.unlink()
    if stale:
        print(f"  discarded stale measurement data: {', '.join(p.name for p in stale)}")


def try_measurement_slot(path: Path | None = None) -> IO[bytes] | None:
    """Take this checkout's measurement slot, or return ``None`` if it is taken.

    Two measurements in one checkout would fight over the report: whichever
    finished last would write the numbers the other one measured. The slot
    is a file the operating system locks, so it is released when the process
    holding it ends -- however it ends -- and a measurement that finds the
    slot taken says so instead of racing.
    """
    lock_path = MEASUREMENT_LOCK if path is None else path
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # The lock lives as long as the handle, so the handle has to outlive this
    # call: the caller holds the slot for the whole measurement and closes it
    # when it is done.
    handle = open(lock_path, "a+b")  # noqa: SIM115
    handle.seek(0)
    handle.write(b"0")
    handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def read_coverage() -> Coverage:
    """Read the coverage the runs produced."""
    data = json.loads(
        run(sys.executable, "-m", "coverage", "json", "-o", "-", env=measurement_env()).stdout
    )

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


def read_junit_outcomes(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The identities of the tests that did not run, and of the ones that failed
    as they were expected to.

    pytest's own report names every test it ran, so the identities come from
    the tool rather than from a count. The names are pytest's node identities
    -- a dotted module name and a test name -- so they are the same on every
    platform, which a path would not be.
    """
    if not path.is_file():
        return (), ()
    skipped: list[str] = []
    xfailed: list[str] = []
    for case in ET.parse(path).iter("testcase"):
        element = case.find("skipped")
        if element is None:
            continue
        identity = f"{case.get('classname')}::{case.get('name')}"
        if element.get("type") == "pytest.xfail":
            xfailed.append(identity)
        else:
            skipped.append(identity)
    return tuple(sorted(skipped)), tuple(sorted(xfailed))


def measure_tests(
    args: list[str], env: dict[str, str] | None = None, *, full_command: bool = False
) -> Outcome:
    """Run a set of tests and read both what they said and which ones sat out.

    The run's own report is asked for as well as its summary line: the summary
    says how many tests skipped, the report says which. ``args`` are the
    arguments of a ``pytest`` invocation; ``full_command`` says that they are
    already a whole command — the ``coverage run -m pytest`` form the
    subprocess-aware measurement uses — and are to run as they stand.
    """
    command = args if full_command else [sys.executable, "-m", "pytest", *args]
    with tempfile.TemporaryDirectory() as directory:
        junit = Path(directory) / "outcomes.xml"
        result = run(*command, f"--junitxml={junit}", env=env)
        skipped, xfailed = read_junit_outcomes(junit)
    outcome = read_outcome(result.stdout)
    return Outcome(
        counts=outcome.counts,
        failures=outcome.failures,
        skipped=skipped,
        xfailed=xfailed,
    )


def measure_code_tests() -> Outcome:
    """Run the whole suite, except the report's own self-checks, with coverage.

    The self-checks are left out on purpose. They read the report's generated
    numbers, so a report that is out of date makes them fail, and counting that
    failure would describe a tree as broken when it is merely out of date. They
    are measured on their own afterwards, against a report that is already
    consistent, and the two results are added up.

    The run is subprocess-aware: the coverage configuration is written to a
    file, ``COVERAGE_PROCESS_START`` points every Python that starts while it
    is set at that file, and ``coverage combine`` merges the per-process data
    afterwards. Without it the androguard worker — a subprocess by design —
    would be reported as 0%, a statement about the measurement, not the code.
    """
    # The rc file lives in the scratch area and is *left in place* after the
    # measurement. Every subprocess the suite starts while
    # ``COVERAGE_PROCESS_START`` names it — the androguard workers, the
    # launcher grandchildren — reads it from its own ``site`` hook, and a file
    # that disappears under them is a ``ConfigError`` printed onto some
    # backend's stderr instead of coverage data. The name carries the pid,
    # so a measurement never rewrites the configuration another one is
    # reading; the content is rewritten at the start of every measurement, so
    # a stale copy never survives to describe an older tree; the scratch area
    # keeps it out of the repository and out of ``discard_stale_coverage``'s
    # way.
    rc_path = REPO_ROOT / ".scratch" / f"coveragerc-measure-{os.getpid()}.ini"
    rc_path.parent.mkdir(exist_ok=True)
    # newline="\n" keeps the bytes the same on every platform: a text-mode
    # write translates "\n" into os.linesep on Windows, and a configuration
    # file that differs per platform is one more way for two measurements of
    # one tree to disagree.
    rc_path.write_text(COVERAGE_RC, encoding="utf-8", newline="\n")
    env = measurement_env()
    env["COVERAGE_PROCESS_START"] = str(rc_path)
    outcome = measure_tests(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            f"--rcfile={rc_path}",
            "-m",
            "pytest",
            "-k",
            f"not {REPORT_CHECK} and not {STATUS_CHECK}",
        ],
        env=env,
        full_command=True,
    )
    run(sys.executable, "-m", "coverage", "combine", f"--rcfile={rc_path}", env=measurement_env())
    return outcome


def measure_report_checks(candidate: str, report_path: Path) -> Outcome:
    """Measure the report's self-checks against a candidate report.

    The candidate is written to a temporary file and the checks are pointed at
    it, so a check never sees the report half-refreshed and the report on disk
    is only ever replaced whole. The coverage data file is private to this run
    and thrown away with the directory afterwards: these rounds exist to learn
    which of the self-checks pass, not to add coverage, and appending to the
    shared file made the merged coverage grow every round -- a measurement
    that could never settle, because the numbers one round wrote changed the
    numbers the next round read.
    """
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / report_path.name
        # newline="\n" keeps the candidate's bytes the same on every platform,
        # so the self-checks measure one report, not one spelling of it.
        path.write_text(candidate, encoding="utf-8", newline="\n")
        env = measurement_env()
        env["COVERAGE_FILE"] = str(Path(directory) / ".coverage")
        env[REPORT_PATH_ENV] = str(path)
        return measure_tests(
            ["--cov=dexatlas", "-k", REPORT_CHECK],
            env=env,
        )


def measure_status_checks(
    report_candidate: str, status_candidate: str, report_path: Path, status_path: Path
) -> Outcome:
    """Measure the status page's self-checks against the candidate documents.

    The status page states the same figures as the report, so its checks are
    measured against both candidates: a page that has fallen out of step with
    the report is exactly what they are there to notice. The coverage data
    file is private to this run, for the same reason the report checks' is.
    """
    with tempfile.TemporaryDirectory() as directory:
        report_copy = Path(directory) / report_path.name
        status_copy = Path(directory) / status_path.name
        # newline="\n" keeps the candidates' bytes the same on every platform.
        report_copy.write_text(report_candidate, encoding="utf-8", newline="\n")
        status_copy.write_text(status_candidate, encoding="utf-8", newline="\n")
        env = measurement_env()
        env["COVERAGE_FILE"] = str(Path(directory) / ".coverage")
        env[REPORT_PATH_ENV] = str(report_copy)
        env[STATUS_PATH_ENV] = str(status_copy)
        return measure_tests(
            ["--cov=dexatlas", "-k", STATUS_CHECK],
            env=env,
        )


def add_counts(first: dict[str, int], second: dict[str, int]) -> dict[str, int]:
    """Add two runs' outcomes together.

    ``deselected`` is left out: the two runs select each other's complement, so
    their deselected counts say nothing once added.
    """
    names = [name for name in OUTCOMES if name != "deselected"]
    return {name: first.get(name, 0) + second.get(name, 0) for name in names}


def fingerprint_files() -> list[Path]:
    """Every file whose content the measurement depends on.

    The code under test, the suite that measures it, the configuration of the
    tools that do the measuring, and the script that asks them. A change to
    any of them changes what the numbers mean, so any of them makes the
    figures stale.

    The order is the same on every platform: the paths are compared as the
    POSIX paths they are written as, not as the platform's own spelling.
    """
    files: list[Path] = []
    for root in (SOURCE_ROOT, TESTS_ROOT):
        if root.is_dir():
            # The suffix is compared explicitly: a glob pattern matches case-
            # insensitively on Windows and case-sensitively on Linux, so a
            # stray ``.PY`` file would enter the fingerprint here and make
            # the two platforms disagree about what the tree contains.
            files.extend(path for path in root.rglob("*") if path.suffix == ".py")
    for name in FINGERPRINT_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            files.append(path)
    return sorted(set(files), key=lambda path: path.relative_to(REPO_ROOT).as_posix())


def source_fingerprint() -> str:
    """A hash of the tree the measurement describes.

    When the code changes, the coverage number in the report stops being true. A
    fingerprint makes that visible without re-measuring: the test suite recomputes
    it and asks for a refresh.

    The suite is part of what is hashed. The pass/skip split the report states is
    a property of the tree, so adding a test makes those numbers stale as surely
    as changing a line of the code does. Hashing only the code meant a test could
    be added without the report noticing, and the report went on claiming a
    pass/skip split that described a suite nobody had run.

    Line endings are normalised before hashing. Git checks out CRLF on Windows and
    LF on Linux, so hashing the raw bytes would give the same source two different
    fingerprints -- and the report would be declared stale on every platform but
    the one it was measured on. The fingerprint answers "is this the same code?",
    not "is this the same byte sequence?".
    """
    digest = hashlib.sha256()
    for path in fingerprint_files():
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def source_statements() -> dict[str, int]:
    """How many statements each module of the package holds.

    The count comes from coverage's own parser, so it is the number the
    coverage run reports -- but it is measured from the tree, not read out of
    the record the last refresh left behind. That is the difference: a record
    that says something else about the code is caught here, and a record that
    agrees with itself is not.
    """
    import coverage
    from coverage.python import PythonFileReporter

    settings = coverage.Coverage(config_file=True)
    counts: dict[str, int] = {}
    # The suffix is compared explicitly: a glob pattern matches case-
    # insensitively on Windows and case-sensitively on Linux, and a stray
    # ``.PY`` file would enter one platform's statement count but not the
    # other's.
    paths = sorted(
        (path for path in SOURCE_ROOT.rglob("*") if path.suffix == ".py"),
        key=lambda path: path.as_posix(),
    )
    for path in paths:
        relative = path.relative_to(SOURCE_ROOT).as_posix()
        counts[relative] = len(PythonFileReporter(str(path), coverage=settings).lines())
    return counts


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


def union_ids(*groups: Iterable[str]) -> tuple[str, ...]:
    """Every identity, once, in a stable order."""
    return tuple(sorted({identity for group in groups for identity in group}))


def build_record(
    coverage: Coverage,
    suite: dict[str, int],
    fast: int,
    slow: int,
    total: int,
    history: dict[str, Any] | None = None,
    skipped_tests: tuple[str, ...] = (),
    xfailed_tests: tuple[str, ...] = (),
) -> dict[str, Any]:
    """The record of one measurement: everything the report can state."""
    return {
        "schema": 4,
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
            # The outcomes the report does not state. A complete measurement
            # has none of them, and the record says so: every test that ran
            # has exactly one outcome, so these counts add up to the number
            # of tests in the tree.
            "failed": suite.get("failed", 0),
            "xpassed": suite.get("xpassed", 0),
            # Which tests sat out, not only how many. A count cannot tell a
            # measurement that skipped the same tests from one that skipped a
            # different set of the same size.
            "skipped_tests": list(skipped_tests),
            "xfailed_tests": list(xfailed_tests),
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


#: The badge of the test count: ``.../badge/tests-444%20passing-brightgreen.svg``.
#: The number is URL-escaped in the badge and written by hand; this is the
#: pattern that finds it. The number may be empty -- a badge whose number was
#: lost is still a badge, and it has to be repairable.
BADGE_TESTS = re.compile(r"(?P<head>badge/tests-)(?P<number>[\d.]*)(?P<tail>%20passing)")

#: The badge of the coverage: ``.../badge/coverage-94.0%25-brightgreen.svg``.
BADGE_COVERAGE = re.compile(r"(?P<head>badge/coverage-)(?P<number>[\d.]*)(?P<tail>%25)")


def apply_badges(text: str, values: dict[str, str]) -> str:
    """Write the measured figures into the readme badges.

    A badge is a URL, and a URL cannot hold the report's markers -- so the
    number in it was typed by hand. A hand-written number drifts: the badge
    that shipped with v0.1.2 said 275 tests when the project had 444, and
    nothing about the URL said when it was written. The number is measured
    here and written in, so the badge is a measurement like every other.

    A readme without the badge is left alone: not every readme has one, and
    one that does not is not a document with a stale number.
    """
    tests = values.get("tests.passing")
    coverage = values.get("coverage.pct")
    # A value that is missing or empty is not written: a badge with an empty
    # number in it is worse than a badge with a stale one, because it says
    # nothing at all rather than something that can be checked.
    if tests:
        text = BADGE_TESTS.sub(
            lambda match: f"{match.group('head')}{tests}{match.group('tail')}", text
        )
    if coverage:
        # The value carries the percent sign ("94.2%") and the badge is a
        # URL: the tail of the pattern already spells the percent sign as
        # "%25", so the number goes in without one. Writing the value as it
        # stands would spell it twice.
        number = coverage.rstrip("%")
        text = BADGE_COVERAGE.sub(
            lambda match: f"{match.group('head')}{number}{match.group('tail')}", text
        )
    return text


def render_status(record: dict[str, Any], text: str) -> str:
    """Write the measured figures into the status page.

    The status page states the same figures as the report, so it gets the same
    values: the number in the page and the number in the report are one
    measurement, not two copies of it. The page carries no record of its own —
    the report holds the measurement, and the page's own checks compare it
    with the report.

    A figure this script does not know how to fill in is a figure nobody can
    check, and guessing at one would put a number in the page that nothing
    stands behind. Better to stop and say which one it is.
    """
    updated, unknown = apply_figures(text, render_figures(record))
    if unknown:
        raise SystemExit(
            "the status page refers to figures this script does not know how to fill in: "
            + ", ".join(sorted(set(unknown)))
        )
    return updated


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


def test_file_table(text: str) -> tuple[list[str], list[str]] | None:
    """The test files the report's table leaves out, and the ones it names that are gone.

    The table is the reader's map from the report's claims to the code that
    backs them: a file that is not in it is a place the reader is not sent.
    Its numbers are generated, but its rows are written by hand, and the
    script that fills in the numbers never looked at them. A file added to
    the suite without a row in the table left the table quietly short of one
    file, and the refresh wrote the new numbers into it all the same.

    So the two sets are compared here, before anything is written.

    None means the document has no table at all. A document that never
    claimed to hold one has nothing to compare with the suite, and whether
    the report has to have one is the report's own test's business
    (``tests/test_docs.py::test_execution_report_lists_every_test_file``).
    The script says that it did not check, rather than passing in silence.
    """
    if TEST_FILE_SECTION not in text:
        return None
    section = text.split(TEST_FILE_SECTION, 1)[-1].split("\n### ", 1)[0]
    listed = set(TEST_FILE_ROW.findall(section))
    on_disk = {path.name for path in TESTS_ROOT.glob("test_*.py")}
    return sorted(on_disk - listed), sorted(listed - on_disk)


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

    The backends are looked up the way the code itself finds them -- through
    the configured paths, then on ``PATH`` -- rather than by a bare ``PATH``
    search: CI points the code at them with environment variables and never
    puts their directories on ``PATH``, so a bare search reports a backend
    as missing on the very machine that has it.
    """
    missing: list[str] = []
    from dexatlas.tools.base import which_or_none

    if which_or_none([os.environ.get("DEXATLAS_JADX_PATH")], names=("jadx",)) is None:
        missing.append("JADX (bash scripts/install-backends.sh)")
    if (
        not os.environ.get("DEXATLAS_APKTOOL_JAR")
        or not Path(os.environ["DEXATLAS_APKTOOL_JAR"]).is_file()
    ):
        missing.append("Apktool (bash scripts/install-backends.sh)")
    if find_spec("androguard") is None:
        missing.append("androguard (uv sync --extra analysis)")
    if find_spec("PIL") is None:
        missing.append("Pillow (uv sync --extra demo)")
    fixtures = REPO_ROOT / "fixtures" / "apk"
    if not all((fixtures / name).is_file() for name in ("TestActivity.apk", "multidex.apk")):
        missing.append("the integration fixtures (bash scripts/fetch-fixtures.sh)")
    return missing


def measured_the_tree(code: Outcome, total: int) -> tuple[bool, str]:
    """Did the run account for every test the tree collects?

    A run accounted for a test when it ran it, when it skipped it, when it
    failed it, and when it deselected it -- the report's and the status
    page's own self-checks are deselected by the code run and measured
    separately, so they are accounted for as well.

    Whether a test skipped is a fact about the machine, not about the tree:
    the Windows-only tests skip on Linux by design, and that says nothing
    about the tree, so it does not make the measurement a measurement of a
    smaller tree.

    Returns whether the run accounted for the whole tree and, when it did
    not, what it accounted for.
    """
    accounted = sum(
        code.counts.get(name, 0)
        for name in ("passed", "failed", "skipped", "xfailed", "xpassed", "error", "deselected")
    )
    if accounted != total:
        return False, f"the tree has {total} tests; the run accounted for {accounted}"
    return True, ""


def measurement_is_complete(code: Outcome) -> tuple[bool, str]:
    """Could this machine take the measurement the report describes?

    The report names the basis of its coverage numbers: the analysis
    backends, the integration fixtures and the demo extra. A run without
    one of them skips the tests that need it, and the coverage of such a run
    is not the coverage the report claims, so the missing thing is what
    makes the run partial.

    Returns whether the measurement is complete and, when it is not, what is
    missing.
    """
    missing = missing_prerequisites()
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, ""


def same_measurement(recorded: dict[str, Any], fresh: dict[str, Any]) -> bool:
    """Did two measurements exercise the same code?

    The tests that skipped are the tests whose code did not run, so two
    measurements that left the same tests unexercised measured the same code
    and their coverage figures describe the same thing. Two that did not are
    measurements of two different machines: the platform makes some tests
    skip on one of them, the code those tests cover does not run on the
    other, and the two numbers are not two measurements of one thing.

    This is a question about two measurements, not about whether a
    measurement was complete -- ``measurement_is_complete`` answers that.
    """
    old = recorded.get("suite", {})
    new = fresh.get("suite", {})
    if "skipped_tests" in old and "skipped_tests" in new:
        skipped_same = list(old["skipped_tests"]) == list(new["skipped_tests"])
        xfailed_same = list(old.get("xfailed_tests", [])) == list(new.get("xfailed_tests", []))
        return skipped_same and xfailed_same
    # A record from before the identities were kept: the counts are all
    # there is, so they are what is compared.
    return old.get("skipped") == new.get("skipped") and old.get("xfailed") == new.get("xfailed")


def comparable_record(recorded: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """The fresh measurement, with the figures of the machine taken from the record.

    A measurement's coverage and its pass/skip split describe the machine it
    was taken on as much as the tree it was taken on: the same tree measures
    a different coverage on a different platform, because the platform makes
    some tests skip and the code they cover does not run there. When the two
    measurements are not comparable, the recorded figures are the ones the
    check compares, and the check says which ones it could not compare.
    """
    if not recorded.get("coverage") or not recorded.get("suite"):
        return fresh
    comparison = dict(fresh)
    comparison["coverage"] = recorded["coverage"]
    comparison["suite"] = recorded["suite"]
    return comparison


def converge(
    text: str,
    report_path: Path,
    code: Outcome,
    coverage: Coverage,
    fast: int,
    slow: int,
    total: int,
    history: dict[str, Any] | None = None,
    status_text: str | None = None,
    status_path: Path | None = None,
) -> Refresh:
    """Bring the report and its self-checks into agreement, within one run.

    Writing the numbers changes what the self-checks say, so a refresh that
    measured once and wrote once could leave the two disagreeing: the numbers it
    wrote would describe a run in which the self-checks failed, and the
    self-checks fail because the numbers are stale. So the self-checks are
    measured against a candidate report, and the candidate is rebuilt until the
    two stop moving.

    The status page is measured the same way, against candidates of both
    documents: its checks compare it with the report, so they need the report
    the page is being compared to.

    The loop ends when a candidate is measured and nothing about it changes the
    measurement — at that point the report the refresh leaves behind is one the
    self-checks pass.
    """
    suite = dict(code.counts)
    skipped_tests = code.skipped
    xfailed_tests = code.xfailed
    record = build_record(coverage, suite, fast, slow, total, history, skipped_tests, xfailed_tests)
    candidate = render_or_fail(text, record)
    status_candidate = render_status(record, status_text) if status_text is not None else None

    checks = Outcome(counts={})
    status_checks = Outcome(counts={})
    for round_number in range(1, MAX_ROUNDS + 1):
        checks = measure_report_checks(candidate, report_path)
        if status_candidate is not None and status_path is not None:
            status_checks = measure_status_checks(
                candidate, status_candidate, report_path, status_path
            )
        new_coverage = read_coverage()
        new_suite = add_counts(add_counts(code.counts, checks.counts), status_checks.counts)
        new_skipped = union_ids(code.skipped, checks.skipped, status_checks.skipped)
        new_xfailed = union_ids(code.xfailed, checks.xfailed, status_checks.xfailed)
        if (
            new_suite == suite
            and new_coverage == coverage
            and new_skipped == skipped_tests
            and new_xfailed == xfailed_tests
        ):
            return Refresh(
                text=candidate,
                record=record,
                checks=checks,
                converged=True,
                rounds=round_number,
                status_text=status_candidate,
                status_checks=status_checks,
            )
        suite, coverage = new_suite, new_coverage
        skipped_tests, xfailed_tests = new_skipped, new_xfailed
        record = build_record(
            coverage, suite, fast, slow, total, history, skipped_tests, xfailed_tests
        )
        candidate = render_or_fail(text, record)
        status_candidate = render_status(record, status_text) if status_text is not None else None

    return Refresh(
        text=candidate,
        record=record,
        checks=checks,
        converged=False,
        rounds=MAX_ROUNDS,
        status_text=status_candidate,
        status_checks=status_checks,
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

    # The report's test-file table is the reader's map from the report's claims
    # to the code that backs them. Its numbers are generated; its rows are
    # written by hand. Nothing checked them, so a file added to the suite
    # without a row in the table left the table quietly short of one file --
    # and the refresh wrote the new numbers into that table all the same.
    #
    # The two sets are compared before anything is measured, so a table that
    # does not describe the suite is a two-second error rather than a
    # two-minute measurement that ends in a report nobody should read.
    mismatch = test_file_table(text)
    if mismatch is None:
        print(
            f"This document has no {TEST_FILE_SECTION} section, so it has no "
            "test-file table to check."
        )
    else:
        missing, stale = mismatch
        if missing or stale:
            print("The report's test-file table does not describe the suite:")
            for name in missing:
                print(f"  the suite has {name}; the table does not list it")
            for name in stale:
                print(f"  the table lists {name}; the suite does not have it")
            print(
                "\nNothing was written. The table's rows are written by hand: "
                "add the row that is missing, or take out the row that is stale."
            )
            return 1

    previous = read_record(text)

    # The report's figures describe one tree. A tree that has changed since
    # they were measured makes them stale, whether or not this machine can
    # measure the new one.
    previous_fingerprint = previous.get("source_fingerprint")
    current_fingerprint = source_fingerprint()
    tree_changed = bool(previous_fingerprint) and previous_fingerprint != current_fingerprint
    if tree_changed:
        print(
            "The tree has changed since the report was measured:\n"
            f"  {previous_fingerprint}\n  -> {current_fingerprint}\n"
            "The report's figures describe the tree as it was."
        )

    # The status page states the same figures as the report and is refreshed
    # with it. Pointing the script at another document refreshes only that
    # document: the test suite refreshes copies of the report, and it must not
    # write to the real status page while it does so.
    status_path = STATUS_PATH if report_path == REPORT_PATH and STATUS_PATH.is_file() else None
    status_text = status_path.read_text(encoding="utf-8") if status_path else None

    # The provenance document names the tool versions its outputs were made
    # with. A measurement on other versions writes numbers the document does
    # not describe, so the run says so and stops before it measures.
    mismatches = documented_version_mismatches()
    if mismatches:
        print("The backends on this machine do not match the versions the report names:")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        print(
            "\nNothing was written. Install the documented versions "
            "(bash scripts/install-backends.sh) and run this again."
        )
        return 1

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
    if report_path == REPORT_PATH:
        # Only a run that writes this checkout's report needs the slot: two of
        # them would fight over it, the second to finish writing the numbers
        # the first one measured. A run pointed at another document writes
        # that document and leaves this one alone.
        slot = try_measurement_slot()
        if slot is None:
            print(
                "Another measurement is already running in this checkout. Two of them would "
                "fight over the report, so this one did not start."
            )
            return 1
        atexit.register(slot.close)
    discard_stale_coverage()
    discard_stale_measurement_data()
    code = measure_code_tests()
    coverage = read_coverage()
    print(f"  {code.describe()} (the report's own self-checks are measured separately)")

    # The measurement has to describe the tree it ran on. A module the run
    # reported that the tree does not have -- or one the tree has that the run
    # did not report -- means the numbers are about something else.
    measured = set(coverage.files)
    in_tree = set(source_statements())
    if measured != in_tree:
        print(
            "The coverage run and the tree disagree about the modules: "
            f"only in the run: {sorted(measured - in_tree)}; "
            f"only in the tree: {sorted(in_tree - measured)}"
        )

    if code.failures:
        report_failures("The tree does not pass its own tests:", code.failures)
        print(
            "\nThe report was not touched. Its figures describe a run in which every "
            "test passed, and this run was not one. Fix the failures and run this again."
        )
        return 1

    # The run has to have accounted for every test the tree collects. A run
    # that did not account for them all measured a smaller tree, and the
    # report is about the bigger one.
    accounted_for, why_not = measured_the_tree(code, total)
    if not accounted_for:
        print(
            "The run did not account for every test in the tree:\n"
            f"  {why_not}\n"
            "  ("
            + ", ".join(
                f"{name}={code.counts.get(name, 0)}"
                for name in ("passed", "failed", "skipped", "xfailed", "deselected")
                if code.counts.get(name)
            )
            + ")"
        )
        print(
            "\nNothing was written. The figures would describe a tree smaller "
            "than the one the report is about."
        )
        return 1

    # A measurement is complete when this machine has everything the report
    # names as the basis of its coverage numbers.
    #
    # The question is whether *this tree* was measured, not whether this run
    # ran on the same machine as the recorded one. Whether a test skipped is
    # a fact about the machine: the Windows-only tests skip on Linux by
    # design, and that says nothing about the tree. Comparing the identities
    # of the skipped tests with the recorded ones answers a different
    # question -- "did this run run on the machine that wrote the record?" --
    # and it made the measurement gate idle: a Linux run disagreed with a
    # Windows record about which tests skip, threw the measurement away, and
    # reported success.
    complete, incomplete_because = measurement_is_complete(code)
    skipped = code.counts.get("skipped", 0)
    if not complete:
        print(f"This measurement was incomplete: {incomplete_because}.")

    if complete:
        print("Measuring the report's self-checks against a candidate report...")
        refresh = converge(
            text,
            report_path,
            code,
            coverage,
            fast,
            slow,
            total,
            history,
            status_text,
            status_path,
        )
        record = refresh.record
        updated = refresh.text
        checks = refresh.checks
        status_updated = refresh.status_text
        status_checks = refresh.status_checks
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
        if status_path is not None:
            print(f"  the status page's self-checks: {status_checks.describe()}")

        # Every test in the tree has to have an outcome for the run to describe
        # the tree. A test that neither passed, failed, skipped nor was
        # expected to fail is a test the run did not account for -- a
        # collection that stopped early, or a file that was never collected --
        # and the numbers of such a run are numbers about a smaller tree.
        # The script used to accept them, and a badge once said "353 passing"
        # on a tree of 885 tests.
        #
        # The self-checks are measured separately from the code tests and added
        # up here, so the accounting is complete only now.
        accounted = sum(
            record["suite"].get(name, 0)
            for name in ("passed", "failed", "skipped", "xfailed", "xpassed")
        )
        if accounted != total:
            print(
                "The run did not account for every test in the tree:\n"
                f"  the tree has {total} tests; the run accounted for {accounted}\n"
                "  ("
                + ", ".join(
                    f"{name}={record['suite'].get(name, 0)}"
                    for name in ("passed", "failed", "skipped", "xfailed", "xpassed")
                )
                + ")"
            )
            print(
                "\nNothing was written. The figures would describe a tree smaller "
                "than the one the report is about."
            )
            return 1
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
        record = build_record(
            coverage, code.counts, fast, slow, total, history, code.skipped, code.xfailed
        )
        record["coverage"] = previous["coverage"]
        record["suite"] = previous["suite"]
        record["source_fingerprint"] = previous["source_fingerprint"]
        updated = render_or_fail(text, record)
        status_updated = render_status(record, status_text) if status_text is not None else None
        checks = Outcome(counts={})
        status_checks = Outcome(counts={})

    # The figures that describe the machine a measurement was taken on are not
    # the same on two machines: the same tree measures a different coverage on
    # a different platform, because the platform makes some tests skip and the
    # code they cover does not run there. Two measurements are comparable when
    # they left the same tests unexercised; when they are not, the check
    # compares the figures that describe the tree and says which ones it
    # could not compare.
    comparable = complete and same_measurement(previous, record)
    comparison = record if comparable else comparable_record(previous, record)

    if args.check:
        checked = render_or_fail(text, comparison)
        checked_status = render_status(comparison, status_text) if status_text is not None else None
    else:
        checked = updated
        checked_status = status_updated

    hidden = undisclosed_modules(comparison if args.check else record, checked)
    if hidden:
        print(
            "These modules are below "
            f"{WEAK_MODULE_PERCENT}% but the report does not list them: " + ", ".join(hidden)
        )

    # The readme badges state the same two figures, and their numbers were
    # written by hand. They are written here from the same values the report
    # is written from -- the same measurement, not a second calculation of it
    # -- so a badge cannot drift away from the report it summarises.
    #
    # When the measurement is partial, the record keeps the previous suite and
    # coverage, so the badge keeps them too: the numbers it would state are
    # the numbers of a run that did not run everything.
    #
    # The test badge says "passing", so it states the number that passed, not
    # the number the collector found.
    #
    # Only the real readmes are written, and only when the real report is the
    # one being refreshed. The test suite runs this script against copies of
    # the report, with measurements it made up; a script that wrote the readme
    # in that case would put a made-up number in the project's front page --
    # and the suite would do it on every run.
    readmes: list[tuple[Path, str, str]] = []
    if report_path == REPORT_PATH:
        # The check compares the figures that describe the tree. The ones that
        # describe the machine -- the coverage and the pass/skip split -- are
        # only compared when the two measurements are comparable, so the
        # badge is read against the figures the check is comparing.
        measured_values = render_figures(comparison if args.check else record)
        badge_values = {
            "tests.passing": measured_values.get("suite.passed", ""),
            "coverage.pct": measured_values.get("coverage.pct", ""),
        }
        for readme in README_PATHS:
            if not readme.is_file():
                continue
            original = readme.read_text(encoding="utf-8")
            refreshed = apply_badges(original, badge_values)
            if refreshed != original:
                readmes.append((readme, original, refreshed))

    changes = figure_changes(text, comparison if args.check else record)
    if status_text is not None:
        changes.extend(figure_changes(status_text, comparison if args.check else record))
    for readme, original, refreshed in readmes:
        for badge in (BADGE_TESTS, BADGE_COVERAGE):
            before = badge.search(original)
            after = badge.search(refreshed)
            if before and after and before.group("number") != after.group("number"):
                changes.append(
                    (
                        f"{readme.name} badge {badge.pattern.split('-')[0].split('/')[-1]}",
                        before.group("number"),
                        after.group("number"),
                    )
                )

    if not complete:
        warn_partial(code, incomplete_because)

    status_matched = checked_status is None or checked_status == status_text
    badges_matched = not readmes
    if args.check:
        if complete and not comparable:
            print(
                "This run measured the tree on a machine that is not the one the record "
                "was taken on: the coverage and the pass/skip split describe the code "
                "that machine left unexercised, so they were not compared. The figures "
                "that describe the tree were."
            )
        if not complete:
            print("The report was not compared: this run did not measure this tree.")
        elif checked == text and status_matched and badges_matched and not tree_changed:
            print("The report matches a fresh measurement.")
        else:
            for key, old, new in changes:
                print(f"{key}: {old} -> {new}")
            if tree_changed:
                print(f"source fingerprint: {previous_fingerprint} -> {current_fingerprint}")
            print("The report does not match a fresh measurement.")
        matched = checked == text and status_matched and badges_matched and not tree_changed
    else:
        report_path.write_bytes(updated.encode("utf-8"))
        if status_path is not None and status_updated is not None:
            status_path.write_bytes(status_updated.encode("utf-8"))
        for readme, _original, refreshed in readmes:
            readme.write_bytes(refreshed.encode("utf-8"))
        if changes:
            for key, old, new in changes:
                print(f"{key}: {old} -> {new}")
        if updated == text:
            print("The report was already up to date.")
        else:
            print(f"Updated {display_path(report_path)}.")
        if status_path is not None and status_updated is not None and not status_matched:
            print(f"Updated {display_path(status_path)}.")
        for readme, _original, _refreshed in readmes:
            print(f"Updated the badge in {display_path(readme)}.")
        matched = True

    if checks.failures:
        report_failures(
            "The report's self-checks still fail against the refreshed report, so this "
            "one needs a hand rather than another refresh:",
            checks.failures,
        )
        return 1
    if status_checks.failures:
        report_failures(
            "The status page's self-checks still fail against the refreshed documents, "
            "so this one needs a hand rather than another refresh:",
            status_checks.failures,
        )
        return 1
    if not complete:
        # The run could not measure this tree, so it checked nothing about the
        # report's figures: the previous measurement was kept -- it still
        # describes a tree -- but a run that verified nothing must not report
        # success. A gate that returns 0 here is a gate that cannot fail.
        return 1
    return 0 if matched else 1


def warn_partial(code: Outcome, because: str) -> None:
    """Say plainly what this run could and could not measure."""
    print(
        "\nThis run was partial: "
        + ", ".join(
            f"{name}={code.counts.get(name, 0)}"
            for name in ("passed", "skipped", "xfailed")
            if code.counts.get(name)
        )
        + ".\nIt could not measure this tree: "
        + because
        + ".\nThe coverage figures were left as they were, because they describe a "
        "complete measurement. A complete one needs:\n  "
        + "\n  ".join(missing_prerequisites() or ["(nothing obvious is missing)"])
        + "\nThe report's figures were not verified against a complete measurement of "
        "this tree, so this run reports failure."
    )


if __name__ == "__main__":
    raise SystemExit(main())
