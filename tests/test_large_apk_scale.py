"""Scale tests: a large APK, a real backend, and the limits that only bite at size.

The samples under ``examples/`` are three kilobytes each. That is the right size
for a committed sample and the wrong size for a question: on a three-kilobyte
APK every limit in the Androguard adapter is far away, so nothing in the suite
ever asks what happens when one of them is reached. The three limits
(``DEFAULT_METHOD_LIMIT``, ``DEFAULT_STRING_LIMIT``,
``DEFAULT_INSTRUCTION_LIMIT``) had never been pressed against a real file, and
``docs/status.md`` 4.4 records that as an open item.

This module presses them. It builds an APK of a chosen size from smali this
project writes, analyses it with the real backends, and asserts what the
analysis *did* — not how fast it did it.

**The samples are generated, never committed.** ``scripts/generate-large-apk.py``
writes the smali and assembles the APK with Apktool into a temporary directory.
Nothing it produces enters the repository: a sixth committed sample would make
the claim "five first-party samples" false, and a large one would put a
multi-megabyte binary in ``git clone``.

The size is chosen by the ``DEXATLAS_LARGE_APK_SCALE`` environment variable and
defaults to ``smoke``, which is small enough for every CI job. The bigger tiers
are opt-in, because they take minutes:

    smoke    20 classes x 8 methods      — the CI default
    medium   300 classes x 40 methods
    large    2,050 classes x 100 methods — more methods than the method limit
    xlarge   600 classes x 100 methods   — more instructions than the instruction limit

Four of the assertions here are marked ``xfail(strict=True)``. They describe how
the code *should* behave and does not: a truncated index has to say so, the
three limits have to bound the whole APK rather than each DEX file in it, and a
backend's version has to be probed once rather than once per symbol. They are
not skipped, and they are not quietly rewritten to match today's behaviour —
``strict=True`` turns a fixed defect into a failure that asks for the marker to
be removed. ``docs/benchmarks/large-apk.md`` has the measurements and the
reproduction for each one.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ProjectStatus, ToolErrorCode
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.androguard.adapter import (
    DEFAULT_INSTRUCTION_LIMIT,
    DEFAULT_METHOD_LIMIT,
    DEFAULT_STRING_LIMIT,
    AndroguardBackend,
    androguard_available,
)
from dexatlas.tools.apktool.adapter import ApktoolBackend

#: The generator. It lives in ``scripts/`` so a person can run it by hand, and it
#: is the single source of truth for what a generated APK contains: the test
#: reads the ground truth it writes rather than repeating its numbers.
GENERATOR = Path(__file__).parent.parent / "scripts" / "generate-large-apk.py"

#: The environment variable that chooses the size.
SCALE_ENV_VAR = "DEXATLAS_LARGE_APK_SCALE"

#: The environment variable that receives the measurement dump. When it is set,
#: the run writes what it measured to that path as JSON.
REPORT_ENV_VAR = "DEXATLAS_LARGE_APK_REPORT"

#: Tiers above this many methods are analysed without the decompiler. JADX's own
#: cost on a 200,000-method APK is a separate measurement, and it would dominate
#: the wall clock of a test that is about the symbol index.
JADX_METHOD_CEILING = 50_000

#: The method limit is applied per APK; the other two are applied per DEX file.
#: The test uses this many DEX files to tell the two apart.
MULTIDEX_METHODS_PER_DEX = 20


def _apktool_ready() -> bool:
    """Whether this machine can assemble an APK.

    Both halves matter: Apktool itself has to be locatable, and it has to have a
    JRE to run under. A machine with the jar but no ``java`` on ``PATH`` is the
    configuration where the generator would fail rather than skip — which is
    exactly the configuration the Python 3.13 CI job runs in.
    """
    if shutil.which("java") is None:
        return False
    return ApktoolBackend(Settings()).resolve() is not None


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not androguard_available(), reason="androguard not installed"),
    pytest.mark.skipif(not _apktool_ready(), reason="apktool (or a JRE) not installed"),
]


def _scale() -> str:
    return os.environ.get(SCALE_ENV_VAR, "smoke")


def _run_generator(output_dir: Path, scale: str, *extra: str) -> dict[str, Any]:
    """Build a sample APK and return the ground truth the generator wrote.

    The generator is run as a subprocess rather than imported: it is a script a
    person can run by hand, and running it the same way a person would is the
    point. Importing it would let the test and the script drift apart in a way
    that only shows up when somebody actually types the command.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--scale",
            scale,
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"the generator failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    manifest = output_dir / "large.manifest.json"
    assert manifest.is_file(), f"the generator wrote no ground truth to {manifest}"
    payload: dict[str, Any] = json.loads(manifest.read_text(encoding="utf-8"))
    return payload


@pytest.fixture(scope="module")
def sample(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The generated APK and the ground truth that describes it."""
    output_dir = tmp_path_factory.mktemp("large-apk")
    truth = _run_generator(output_dir, _scale())
    apk = output_dir / "large.apk"
    assert apk.is_file(), f"the generator wrote no APK to {apk}"
    truth["apk"] = apk
    truth["output_dir"] = output_dir
    return truth


@pytest.fixture(scope="module")
def multi_dex_sample(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """A small sample split across several DEX files.

    A DEX file may hold far fewer methods than the format allows, so a small
    sample can be split into many small ones at no cost. That matters because
    the adapter's three limits are not applied to the same thing: the method
    limit is counted across the whole APK, while the string and instruction
    limits are counted per DEX file. Only an APK with more than one DEX file can
    tell the two apart.

    The size is fixed rather than taken from the environment: this sample is
    about the number of DEX files, not about the number of symbols.
    """
    output_dir = tmp_path_factory.mktemp("large-apk-multidex")
    truth = _run_generator(
        output_dir, "smoke", "--max-methods-per-dex", str(MULTIDEX_METHODS_PER_DEX)
    )
    apk = output_dir / "large.apk"
    assert apk.is_file(), f"the generator wrote no APK to {apk}"
    truth["apk"] = apk
    truth["output_dir"] = output_dir
    return truth


@pytest.fixture(scope="module")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    """A settings object on a workspace of its own.

    Module-scoped, because the analysis below is expensive and must not be
    repeated per test; the repository's own ``settings`` fixture is
    function-scoped.
    """
    return Settings(workspace=tmp_path_factory.mktemp("large-apk-workspace"))


@pytest.fixture(scope="module")
def analysis(settings: Settings, sample: dict[str, Any]) -> dict[str, Any]:
    """Analyse the generated sample once, and share the result."""
    analyzer = Analyzer(settings)
    include_jadx = sample["method_count"] <= JADX_METHOD_CEILING
    started = time.monotonic()
    result = analyzer.analyze(sample["apk"], include_jadx=include_jadx)
    elapsed = time.monotonic() - started
    return {
        "analyzer": analyzer,
        "result": result,
        "project": result.project,
        "settings": settings,
        "seconds": elapsed,
        "include_jadx": include_jadx,
    }


@pytest.fixture(scope="module")
def extracted(sample: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """The Androguard index of the sample, extracted directly.

    The pipeline merges and stores what the backend returns; this fixture keeps
    the backend's own output, so a test can compare what the backend saw with
    what the database ended up holding.
    """
    backend = AndroguardBackend(settings)
    started = time.monotonic()
    classes, methods, fields, references, strings, error = backend.extract(
        sample["apk"], sample["apk_sha256"]
    )
    return {
        "backend": backend,
        "classes": classes,
        "methods": methods,
        "fields": fields,
        "references": references,
        "strings": strings,
        "error": error,
        "seconds": time.monotonic() - started,
    }


def _limits_reached(truth: dict[str, Any]) -> dict[str, bool]:
    """Which of the three limits this sample is big enough to reach.

    The answer is computed from the ground truth rather than from the scale
    name, so a tier that is retuned still gets the right answer. The method
    limit counts the whole APK; the other two count one DEX file at a time, so
    they are compared against the largest DEX file in the sample.
    """
    dex_files = truth["dex_files"]
    return {
        "method": truth["method_count"] > DEFAULT_METHOD_LIMIT,
        "string": max((f["string_rows"] for f in dex_files), default=0) > DEFAULT_STRING_LIMIT,
        "instruction": (
            max((f["instruction_count"] for f in dex_files), default=0) > DEFAULT_INSTRUCTION_LIMIT
        ),
    }


# -- the run completes ------------------------------------------------------


def test_the_large_sample_is_analysed_completely(analysis: dict[str, Any]) -> None:
    """A large sample must not fall over.

    The pipeline is built so that no backend can abort a run, so a sample that
    produces symbols at all is a success by construction. What this pins is
    that a *large* sample takes the same path as a small one: the project
    reaches COMPLETED rather than FAILED.

    An error is only acceptable when it says a backend is not installed. The
    CI job that installs Apktool but not JADX has to pass this suite, and in
    that configuration the missing decompiler is recorded as an error — which
    is the pipeline behaving correctly, not a failure of the analysis.
    """
    project = analysis["project"]

    assert project.status == ProjectStatus.COMPLETED
    assert project.class_count > 0
    assert project.method_count > 0

    unexpected = [
        error for error in project.errors if error.code is not ToolErrorCode.NOT_INSTALLED
    ]
    assert not unexpected, f"the run recorded errors: {unexpected}"


def test_the_index_holds_every_class_the_apk_contains(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """The index must hold what the APK holds.

    This is the assertion that fails when a limit truncates the index, and it
    is written against the generator's ground truth rather than against a
    number written here: the generator says how many classes it wrote, and the
    index has to hold exactly that many.

    A sample that is big enough to hit a limit is a different question — see
    ``test_reaching_a_limit_is_recorded_as_an_error`` — so it is checked
    against the limit's own boundary instead.
    """
    project = analysis["project"]
    indexed = {cls.name for cls in analysis["analyzer"].store.list_classes(project.id)}
    reached = _limits_reached(sample)

    if not reached["method"]:
        assert len(indexed) == sample["class_count"]
        assert "com.example.large.Helper" in indexed
        for name in sample["classes"][:5]:
            assert name in indexed
    else:
        # The method limit stopped the walk, so the index is short. What must
        # hold is that it is short and not wrong: the classes that are there
        # are the ones the APK declares.
        assert 0 < len(indexed) <= sample["class_count"]
        assert "com.example.large.C00000" in indexed


def test_the_index_holds_every_method_the_apk_contains(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """Every method the APK declares must be in the method table."""
    project = analysis["project"]
    methods = analysis["analyzer"].store.list_methods(project.id)
    names = {method.qualified_name for method in methods}
    reached = _limits_reached(sample)

    if not reached["method"]:
        assert len(methods) == sample["method_count"]
    else:
        assert 0 < len(methods) <= sample["method_count"]
    assert "com.example.large.C00000.<init>()V" in names


def test_the_index_holds_every_cross_reference_the_apk_contains(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """Every call the APK makes must be in the cross-reference table.

    The count comes from the generator, which knows how many calls it wrote:
    one per method. A cross-reference index that lost edges would still look
    healthy — it would just be smaller, and a smaller number is exactly what
    this assertion refuses to accept.
    """
    project = analysis["project"]
    with analysis["analyzer"].store.transaction() as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM xrefs WHERE project_id = ?", (project.id,)
        ).fetchone()

    reached = _limits_reached(sample)
    expected = sample["expected_references"]
    if reached["instruction"] or reached["method"]:
        assert 0 < rows[0] <= expected
    else:
        assert rows[0] == expected


# -- the counts agree with the rows -----------------------------------------


def test_the_reports_counts_match_the_rows_a_query_returns(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """The number the report states must be the number a query returns.

    This project shipped a defect where a report said a sample had 14 methods
    and a query could list 11 (execution report 3.12). The counts were taken
    from the lists that went into the database rather than from the rows in it,
    so the report was wrong about a database that was perfectly fine.

    Here the count is compared against the rows in three ways: the project's own
    counters, the JSON report a reader receives, and the store's own listing.
    """
    from dexatlas.reports.json_report import build_json_report

    project = analysis["project"]
    store = analysis["analyzer"].store
    report = build_json_report(analysis["result"])

    class_rows = len(store.list_classes(project.id))
    method_rows = len(store.list_methods(project.id))

    assert project.class_count == class_rows
    assert project.method_count == method_rows
    assert report["summary"]["classes"] == class_rows
    assert report["summary"]["methods"] == method_rows
    assert report["project"]["class_count"] == class_rows
    assert report["project"]["method_count"] == method_rows
    assert report["summary"]["cross_references"] == project.reference_count


def test_the_class_rows_report_the_methods_they_actually_hold(
    analysis: dict[str, Any],
) -> None:
    """A class's method count must be the number of methods the table holds for it.

    The class row's counts are written from the method rows, not from what a
    backend said the class contained. On a class that a backend reported
    partially, the two differ, and the difference is the kind that a report
    states without anybody checking.
    """
    project = analysis["project"]
    store = analysis["analyzer"].store

    for cls in store.list_classes(project.id)[:20]:
        held = len(store.list_methods(project.id, cls.name))
        assert cls.method_count == held, f"{cls.name} claims {cls.method_count}, holds {held}"


def test_the_command_line_lists_the_methods_the_report_counts(
    analysis: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command line must be able to list every method the report counts.

    The report and the command line are two readers of the same database. A
    report that counts 14 methods while the command line lists 11 is the
    defect 3.12 describes, and it is invisible unless both are exercised.
    """
    from rich.console import Console
    from typer.testing import CliRunner

    from dexatlas.cli import main as cli
    from dexatlas.config.settings import get_settings

    project = analysis["project"]
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(analysis["settings"].workspace))
    monkeypatch.setenv("DEXATLAS_JADX_PATH", "")
    monkeypatch.setenv("DEXATLAS_APKTOOL_JAR", "")
    # A method id is longer than a narrow terminal, and Rich then shortens it
    # to fit. A wide console keeps every id whole, so one line is one method
    # and the ids can be checked as well as counted.
    monkeypatch.setattr(cli, "console", Console(width=400))
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli.app, ["methods", project.id, "--limit", "1000000"])
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0, f"the command failed: {result.output}"
    listed = [line for line in result.output.splitlines() if "com.example.large." in line]
    assert len(listed) == project.method_count, (
        f"the report counts {project.method_count} methods, the command line listed {len(listed)}"
    )
    # The whole id, not a shortened one: a truncated id would still be one
    # line, and this is the spelling a reader copies into a query.
    assert any(
        "com.example.large.C00000.m0(Ljava/lang/String;)Ljava/lang/String;" in line
        for line in listed
    ), f"the listing shows a shortened method id: {listed[:3]}"


# -- search -----------------------------------------------------------------


def test_a_search_finds_a_string_the_sample_actually_contains(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """Search has to find something that is really there.

    The marker string belongs to exactly one generated class, so a hit is that
    class's string and not merely a word that appears in many places. A search
    that returned nothing would be a search that quietly stopped working.
    """
    project = analysis["project"]
    marker = sample["marker_sample"]
    hits = analysis["analyzer"].search(project.id, marker)

    assert hits, f"search found nothing for {marker!r}"
    assert any(marker in str(hit["name"]) for hit in hits), (
        f"the hits do not include the string that was searched for: {hits}"
    )


def test_a_search_finds_a_class_by_its_name(
    analysis: dict[str, Any], sample: dict[str, Any]
) -> None:
    """The class itself must be findable, not only the string inside it."""
    project = analysis["project"]
    hits = analysis["analyzer"].search(project.id, "com.example.large.C00001")

    assert hits
    assert any(str(hit["name"]) == "com.example.large.C00001" for hit in hits)


# -- the limits -------------------------------------------------------------


def test_the_method_limit_bounds_the_method_index(
    multi_dex_sample: dict[str, Any], settings: Settings
) -> None:
    """The method limit must bound the method index of the whole APK.

    This one holds today — the method limit is counted across the whole APK,
    and the DEX files in the sample are walked one after another against the
    same counter. It is here as the control: it is the limit the other two are
    expected to behave like.
    """
    backend = AndroguardBackend(settings)
    limit = 30
    _, methods, _, _, _, _ = backend.extract(
        multi_dex_sample["apk"], multi_dex_sample["apk_sha256"], method_limit=limit
    )

    assert len(methods) <= limit + 8, (
        f"the method index holds {len(methods)} methods under a limit of {limit}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The string limit is applied to each DEX file separately, so an APK with N "
        "DEX files is allowed N times the budget. The method limit, counted over "
        "the whole APK, is the control. See docs/benchmarks/large-apk.md."
    ),
)
def test_the_string_limit_bounds_the_string_index(
    multi_dex_sample: dict[str, Any], settings: Settings
) -> None:
    """The string limit must bound the string index of the whole APK.

    ``DEFAULT_STRING_LIMIT`` is one number for one APK, the way
    ``DEFAULT_METHOD_LIMIT`` is — and the method limit is counted across every
    DEX file the APK holds. The string limit is counted per DEX file, so an APK
    with ten DEX files is allowed ten times the budget.

    The sample here is small and split into several DEX files on purpose: the
    difference between the two behaviours is visible on a sample that costs a
    fraction of a second to build, and invisible on a sample that costs
    twenty minutes.
    """
    backend = AndroguardBackend(settings)
    limit = 100
    _, _, _, _, strings, _ = backend.extract(
        multi_dex_sample["apk"], multi_dex_sample["apk_sha256"], string_limit=limit
    )

    assert len(strings) <= limit, (
        f"the string index holds {len(strings)} rows under a limit of {limit}; "
        f"the APK has {multi_dex_sample['dex_file_count']} DEX files"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The instruction limit is applied to each DEX file separately, so an APK "
        "with N DEX files is allowed N times the budget. The method limit, "
        "counted over the whole APK, is the control. "
        "See docs/benchmarks/large-apk.md."
    ),
)
def test_the_instruction_limit_bounds_the_cross_reference_index(
    multi_dex_sample: dict[str, Any], settings: Settings
) -> None:
    """The instruction limit must bound the cross-reference index of the whole APK.

    The counter that tracks walked instructions is reset for every DEX file, so
    a ten-DEX APK gets ten times the instruction budget. The method limit,
    counted across the whole APK, is the control.
    """
    backend = AndroguardBackend(settings)
    limit = 30
    _, _, _, references, _, _ = backend.extract(
        multi_dex_sample["apk"], multi_dex_sample["apk_sha256"], instruction_limit=limit
    )

    assert len(references) <= limit, (
        f"the cross-reference index holds {len(references)} edges under a limit of {limit}; "
        f"the APK has {multi_dex_sample['dex_file_count']} DEX files"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Reaching a limit logs a warning and truncates; it does not record a "
        "ToolError, so the run reports a clean success over a partial index. "
        "See docs/benchmarks/large-apk.md."
    ),
)
def test_reaching_a_limit_is_recorded_as_an_error(
    multi_dex_sample: dict[str, Any], settings: Settings
) -> None:
    """A truncated index has to say that it is truncated.

    The adapter logs a warning when it reaches a limit and then returns what it
    has so far. The warning goes to the log; the run carries on; the project
    is COMPLETED; the report states a class count and a method count that are
    true of the rows in the database and silent about the rows that are not
    there. A reader cannot tell a fully indexed APK from a clipped one.

    The contract this asserts is that a run which stopped early says so, in
    the place a reader looks: as a recorded error on the project.
    """
    backend = AndroguardBackend(settings)
    _, methods, _, _, _, error = backend.extract(
        multi_dex_sample["apk"], multi_dex_sample["apk_sha256"], method_limit=30
    )

    assert methods, "the limit produced nothing at all"
    assert error is not None, "the index was truncated and the run recorded nothing"
    assert "limit" in error.message.lower(), f"the error does not name the limit: {error}"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "A clipped index is reported as a clean run: the project completes with "
        "no errors, so a report cannot tell a fully indexed APK from a partial "
        "one. See docs/benchmarks/large-apk.md."
    ),
)
def test_a_truncated_run_is_not_reported_as_a_clean_one(
    multi_dex_sample: dict[str, Any], settings: Settings
) -> None:
    """A project whose index was clipped must not look identical to a clean one.

    This is the same defect seen from the outside: the report's counts match
    the database, so nothing in the report is wrong. What is missing is any
    statement that the APK was not fully indexed.
    """
    analyzer = Analyzer(settings)
    result = analyzer.analyze(multi_dex_sample["apk"], include_jadx=False, include_apktool=False)
    project = result.project

    assert project.status == ProjectStatus.COMPLETED
    assert project.errors, "a clipped index was reported as a clean run"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The Androguard adapter re-reads its own version once per indexed "
        "symbol, and the lookup rescans the installed distributions every time. "
        "JADX and Apktool both cache theirs. See docs/benchmarks/large-apk.md."
    ),
)
def test_the_backend_version_is_probed_once_not_once_per_symbol(
    multi_dex_sample: dict[str, Any], settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backend's version must be probed once, not once per indexed symbol.

    JADX and Apktool both cache theirs. The Androguard adapter does not: it
    calls ``importlib.metadata.version("androguard")`` for every symbol it
    indexes, and that call re-scans the installed distributions every time. On
    a sample with twelve thousand methods the scan is the overwhelming majority
    of the run — the DEX itself is parsed and walked in a fraction of a second.

    The assertion is about the number of probes, not about a duration: a
    duration would be a statement about the machine, and this is a statement
    about the code.
    """
    probes = 0
    original = AndroguardBackend.version

    def counting(self: AndroguardBackend) -> str | None:
        nonlocal probes
        probes += 1
        return original(self)

    monkeypatch.setattr(AndroguardBackend, "version", counting)
    backend = AndroguardBackend(settings)
    classes, methods, fields, references, strings, _ = backend.extract(
        multi_dex_sample["apk"], multi_dex_sample["apk_sha256"]
    )

    indexed = len(classes) + len(methods) + len(fields) + len(references) + len(strings)
    assert indexed > 0
    assert probes == 1, f"the backend's version was probed {probes} times for {indexed} symbols"


# -- the measurement --------------------------------------------------------


def test_the_run_is_measured(
    analysis: dict[str, Any],
    extracted: dict[str, Any],
    sample: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Record what the run measured, so the benchmark report can cite it.

    The report in ``docs/benchmarks/large-apk.md`` quotes numbers; a number
    nobody can reproduce is a number nobody should quote. Writing the
    measurement out next to the run that produced it is what makes the report
    checkable.

    The file goes to the path ``DEXATLAS_LARGE_APK_REPORT`` names, and to the
    test's own temporary directory when that variable is unset — so the test
    always has something to assert against, and never leaves a file behind in
    whatever directory it ran from.
    """
    project = analysis["project"]
    measurement = {
        "scale": sample["scale"],
        "apk_size_bytes": sample["apk_size_bytes"],
        "dex_files": len(sample["dex_files"]),
        "apk_sha256": sample["apk_sha256"],
        "truth": {
            "classes": sample["class_count"],
            "methods": sample["method_count"],
            "references": sample["expected_references"],
            "instructions": sample["expected_instructions"],
            "string_uses": sample["expected_string_uses"],
        },
        "indexed": {
            "classes": project.class_count,
            "methods": project.method_count,
            "references": project.reference_count,
            "strings": len(extracted["strings"]),
            "fields": len(extracted["fields"]),
        },
        "limits": {
            "method": DEFAULT_METHOD_LIMIT,
            "string": DEFAULT_STRING_LIMIT,
            "instruction": DEFAULT_INSTRUCTION_LIMIT,
        },
        "limits_reached": _limits_reached(sample),
        "seconds": {
            "extract": round(extracted["seconds"], 2),
            "pipeline": round(analysis["seconds"], 2),
        },
        "include_jadx": analysis["include_jadx"],
        "status": project.status.value,
        "errors": [error.model_dump(mode="json") for error in project.errors],
    }

    destination = os.environ.get(REPORT_ENV_VAR, "")
    path = Path(destination) if destination else tmp_path / "measurement.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(measurement, indent=2), encoding="utf-8")

    written: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    assert written["indexed"]["classes"] == project.class_count
    assert written["indexed"]["methods"] == project.method_count
    assert written["status"] == ProjectStatus.COMPLETED.value
