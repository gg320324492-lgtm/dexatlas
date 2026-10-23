"""The Androguard adapter parses untrusted DEX in a process of its own.

Two properties are checked here, and both of them used to be false.

**The host's logging is left alone.** The adapter used to call loguru's
``remove()``, which deletes *every* handler in the process — the default one and
every handler the host application had added. One analysis was enough to leave
the host with no logging at all, and nothing in the library could put it back.

**The DEX files are parsed somewhere else.** They used to be parsed in the
service's own process, so a DEX file that took the interpreter down took the
service down with it. The parse now happens in a worker, and the service's
process never even loads the parser.

The checks are made against the service's own process rather than against a
description of it: the point is not that a subprocess was started, but that the
service's process never touched the untrusted bytes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tracemalloc
import zipfile
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ClassRef, ToolErrorCode
from dexatlas.tools.androguard.adapter import (
    ANDROGUARD_LOGGER_NAME,
    AndroguardBackend,
    _suppress_androguard_logging,
    androguard_available,
)
from dexatlas.tools.androguard.isolation import (
    WorkerJob,
    WorkerResult,
    decode_result,
    encode_result,
    run_worker,
)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not androguard_available(), reason="androguard not installed"),
]

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "apk"
FIXTURE_APK = FIXTURE_DIR / "TestActivity.apk"
FIXTURE_SHA = "a" * 64

#: How much the service's own process may allocate while a hostile APK is
#: analysed. The hostile APK carries half a gigabyte of DEX; the service must
#: not pay for it.
SERVICE_MEMORY_BUDGET = 64 * 1024 * 1024

#: A service process that analyses an APK and reports what it found, and what
#: it had loaded, as JSON. Run in a fresh interpreter so that the answer cannot
#: be polluted by what the test session had already imported.
_SERVICE_SCRIPT = """
import json
import sys
from pathlib import Path

from dexatlas.config.settings import Settings
from dexatlas.tools.androguard.adapter import AndroguardBackend

apk_path, out_path, workspace = sys.argv[1], sys.argv[2], sys.argv[3]
backend = AndroguardBackend(Settings(workspace=Path(workspace)))
classes, methods, _fields, _references, _strings, error = backend.extract(
    Path(apk_path), "a" * 64
)
payload = {
    "androguard_modules": sorted(
        name for name in sys.modules if name.split(".")[0] == "androguard"
    ),
    "classes": len(classes),
    "methods": len(methods),
    "error": None if error is None else str(error),
}
Path(out_path).write_text(json.dumps(payload), encoding="utf-8")
"""


@pytest.fixture
def backend(settings: Settings) -> AndroguardBackend:
    return AndroguardBackend(settings)


@pytest.fixture
def fixture_apk(tmp_path: Path) -> Path:
    """A real APK, copied so that nothing can write to the fixture."""
    if not FIXTURE_APK.is_file():
        pytest.skip("fixture not present; run scripts/fetch-fixtures.sh")
    target = tmp_path / FIXTURE_APK.name
    target.write_bytes(FIXTURE_APK.read_bytes())
    return target


@pytest.fixture(scope="module")
def hostile_apk(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An APK whose DEX file is half a gigabyte of nothing.

    The archive is half a megabyte on disk and half a gigabyte when it is read.
    Parsing it in the service's own process costs the service a gigabyte of
    memory; parsing it in the worker costs the worker a gigabyte, which is
    bounded and thrown away.
    """
    path = tmp_path_factory.mktemp("hostile") / "hostile.apk"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"not a manifest")
        with archive.open("classes.dex", "w") as handle:
            chunk = b"\x00" * (1024 * 1024)
            for _ in range(512):
                handle.write(chunk)
    return path


def _job(apk: Path, backend: AndroguardBackend, **overrides: object) -> WorkerJob:
    """The job the service would give the worker for this APK."""
    arguments: dict[str, object] = {
        "apk_path": str(apk),
        "apk_sha256": FIXTURE_SHA,
        "method_limit": 200_000,
        "string_limit": 50_000,
        "instruction_limit": 5_000_000,
        "tool_version": backend.version(),
    }
    arguments.update(overrides)
    return WorkerJob(**arguments)  # type: ignore[arg-type]


# -- the host's logging -----------------------------------------------------


def test_an_analysis_leaves_the_hosts_loguru_handlers_untouched(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """The set of handlers has to be *equal* afterwards, not merely non-empty.

    "Not empty" would pass if the adapter removed the host's handlers and added
    a different one back. Only equality catches that: the host's handlers are
    the host's, and a library that replaces them has broken its host just as
    surely as one that deletes them.

    The handler set is read from loguru's own state, which is private. There is
    no public way to ask "which handlers are installed?", and the question is
    the whole point of the check.
    """
    from loguru import logger as loguru_logger

    before = set(loguru_logger._core.handlers)
    before_level = loguru_logger._core.min_level
    assert before, "the check is meaningless without a handler to protect"

    backend.extract(fixture_apk, FIXTURE_SHA)

    assert set(loguru_logger._core.handlers) == before
    assert loguru_logger._core.min_level == before_level


def test_androguards_own_output_is_suppressed_and_nothing_else_is(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """The suppression is by name, so it turns off Androguard and only Androguard.

    The records are made the way loguru makes them — by the module the call was
    made in — so the check does not depend on Androguard's internals.
    """
    from loguru import logger as loguru_logger

    seen: list[str] = []
    sink = loguru_logger.add(lambda message: seen.append(message.record["name"]), level="TRACE")
    try:
        with _suppress_androguard_logging():
            _emit_as("androguard.core.dex", "an androguard record")
            _emit_as("dexatlas.tools.androguard.adapter", "a dexatlas record")
        _emit_as("androguard.core.dex", "an androguard record afterwards")
    finally:
        loguru_logger.remove(sink)

    assert seen == ["dexatlas.tools.androguard.adapter", "androguard.core.dex"]


def test_an_analysis_delivers_no_androguard_records_to_the_host(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """Nothing Androguard says may reach the host's handlers during an analysis."""
    from loguru import logger as loguru_logger

    seen: list[str] = []
    sink = loguru_logger.add(lambda message: seen.append(message.record["name"]), level="TRACE")
    try:
        backend.extract(fixture_apk, FIXTURE_SHA)
    finally:
        loguru_logger.remove(sink)

    assert [name for name in seen if name.startswith(ANDROGUARD_LOGGER_NAME)] == []


def _emit_as(module_name: str, message: str) -> None:
    """Write a loguru record as if it came from ``module_name``.

    Loguru takes the name of a record from the module the call was made in, so
    a record can only be made under a chosen name by calling from a module with
    that name.
    """
    from loguru import logger as loguru_logger

    namespace = {"__name__": module_name, "logger": loguru_logger, "message": message}
    exec("def _emit():\n    logger.debug(message)\n", namespace)
    namespace["_emit"]()


# -- the boundary ------------------------------------------------------------


def test_the_service_process_never_loads_androguard(fixture_apk: Path, tmp_path: Path) -> None:
    """The parse does not happen in the service's process.

    The check is in a fresh interpreter, because the question is what the
    service's process has loaded — and the test session may well have loaded
    Androguard already, for its own reasons.
    """
    out_path = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            _SERVICE_SCRIPT,
            str(fixture_apk),
            str(out_path),
            str(tmp_path / "workspace"),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    # Backend discovery may import Androguard's trivial top-level package to
    # find where it is installed; that package holds nothing but a version
    # string. What must not be here is the parser.
    assert payload["androguard_modules"] == []
    assert payload["classes"] > 100
    assert payload["error"] is None


def test_the_parse_runs_in_a_process_of_its_own(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """The worker is another process, and it is the one that does the work."""
    outcome = run_worker(backend, _job(fixture_apk, backend), timeout=300)

    assert outcome.error is None
    assert outcome.result is not None
    assert outcome.result.worker_pid != os.getpid()
    assert len(outcome.result.classes) > 100


def test_the_worker_produces_the_index_the_in_process_path_produces(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """The data that crosses the boundary is the data the service would have built.

    Every model is compared: the classes, the methods, the fields, the
    cross-references, the strings and the error. The provenance and the tool
    version are part of those models, so they are compared too.
    """
    in_process = backend._extract_symbols(fixture_apk, FIXTURE_SHA)
    isolated = backend.extract(fixture_apk, FIXTURE_SHA)

    assert isolated == in_process


def test_the_truncation_errors_survive_the_boundary(
    backend: AndroguardBackend, fixture_apk: Path
) -> None:
    """A walk that stopped short says so on the other side of the boundary too."""
    in_process = backend._extract_symbols(fixture_apk, FIXTURE_SHA, method_limit=10)
    isolated = backend.extract(fixture_apk, FIXTURE_SHA, method_limit=10)

    assert isolated[5] is not None
    assert isolated[5].code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "method limit 10 reached" in isolated[5].message
    assert isolated[5] == in_process[5]


def test_the_result_crosses_as_data_and_is_rebuilt_as_models() -> None:
    """The models are rebuilt on the far side, not pickled across.

    A pickle is executable: reading one back runs the code that wrote it, and
    the code that wrote it ran against untrusted input. The boundary is JSON,
    and the models are rebuilt through their own validators.
    """
    result = WorkerResult(
        classes=[ClassRef(name="com.example.Demo", provenance=[])],
        methods=[],
        fields=[],
        references=[],
        strings=[],
        limits={"memory": True},
        worker_pid=4242,
    )

    payload = json.dumps(encode_result(result))
    rebuilt = decode_result(json.loads(payload))

    assert rebuilt.classes == result.classes
    assert rebuilt.limits == {"memory": True}
    assert rebuilt.worker_pid == 4242
    assert "pickle" not in payload


# -- what the worker is bounded by -------------------------------------------


def test_the_worker_bounds_its_memory(backend: AndroguardBackend, fixture_apk: Path) -> None:
    """The worker says which bounds it managed to put in force.

    A bound nobody can see is a claim. The worker reports what it applied, so
    the service can read the answer rather than assume it.
    """
    outcome = run_worker(backend, _job(fixture_apk, backend), timeout=300)

    assert outcome.result is not None
    assert outcome.result.limits.get("memory") is True


def test_a_worker_that_runs_out_of_memory_is_recorded_not_fatal(
    backend: AndroguardBackend, hostile_apk: Path
) -> None:
    """The memory ceiling is the worker's, and it holds there.

    The worker is given a ceiling it cannot inflate half a gigabyte under, and
    what comes back is a recorded parse failure — not a dead service.
    """
    outcome = run_worker(
        backend,
        _job(hostile_apk, backend, memory_limit_bytes=200 * 1024 * 1024),
        timeout=300,
    )

    assert outcome.error is None
    assert outcome.result is not None
    assert outcome.result.error is not None
    assert outcome.result.error.code is ToolErrorCode.PARSE_ERROR
    assert outcome.result.classes == []


def test_a_worker_that_outlives_its_timeout_is_killed(
    backend: AndroguardBackend, hostile_apk: Path
) -> None:
    """The runtime is bounded, and the bound is enforced rather than hoped for."""
    outcome = run_worker(backend, _job(hostile_apk, backend), timeout=1)

    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert outcome.result is None


# -- a hostile APK -----------------------------------------------------------


def test_a_hostile_dex_costs_the_worker_the_memory_not_the_service(
    backend: AndroguardBackend, hostile_apk: Path
) -> None:
    """The service does not pay for the DEX file it is asked to read.

    The APK carries half a gigabyte of DEX in half a megabyte of archive.
    Parsing it in the service's own process costs the service that gigabyte;
    parsing it in the worker costs the worker that gigabyte, which is bounded
    and thrown away. Measured: the service's own allocations stay under the
    budget, where the in-process path reached more than a gigabyte.
    """
    tracemalloc.start()
    try:
        classes, methods, *_rest, error = backend.extract(hostile_apk, FIXTURE_SHA)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < SERVICE_MEMORY_BUDGET, (
        f"the service allocated {peak} bytes while reading a hostile APK"
    )
    assert error is not None
    assert error.code is ToolErrorCode.PARSE_ERROR
    assert classes == []
    assert methods == []


def test_a_malformed_dex_is_recorded_and_the_service_keeps_working(
    backend: AndroguardBackend, fixture_apk: Path, tmp_path: Path
) -> None:
    """A DEX file that cannot be parsed is a recorded failure, not an exception.

    And the service is still the service afterwards: it analyses the next APK
    as if nothing had happened.
    """
    broken = tmp_path / "broken.apk"
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("classes.dex", b"dex\n035\x00" + b"\xff" * 512)

    classes, methods, *_rest, error = backend.extract(broken, FIXTURE_SHA)

    assert error is not None
    assert error.code is ToolErrorCode.PARSE_ERROR
    assert "classes.dex" in error.message
    assert classes == []
    assert methods == []

    afterwards = backend.extract(fixture_apk, FIXTURE_SHA)
    assert afterwards[5] is None
    assert len(afterwards[0]) > 100
