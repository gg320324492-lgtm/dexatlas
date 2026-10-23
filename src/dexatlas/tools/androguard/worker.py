"""The isolated worker: the DEX files are parsed here, not in the service.

Run as ``python -m dexatlas.tools.androguard.worker <job.json>``.

The job names an APK, the limits the walk is held to, and the file the result is
written to. The worker parses the APK with the same adapter the service uses, so
the index it produces is the index the service would have produced — and it
produces it in a process that can be killed, bounded and thrown away.

Nothing here is imported by the service. The service starts the worker as a
subprocess and reads the file it writes; that is the whole contract, and the
contract is deliberately narrow: JSON in, JSON out, no code from this side ever
runs in the other.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dexatlas.core.models import ToolError, ToolErrorCode
from dexatlas.tools.androguard.isolation import (
    WorkerJob,
    WorkerResult,
    decode_job,
    encode_result,
)

logger = logging.getLogger(__name__)

#: The Windows job object the worker put itself in, if it could.
#:
#: The handle is held for the life of the process on purpose: letting it close
#: would take the job — and the memory limit that goes with it — away while the
#: worker is still parsing.
_JOB_HANDLE: Any = None


class _CollectingHandler(logging.Handler):
    """Keeps the worker's log records so that the service can log them too.

    The worker is a different process, so a warning it writes would never reach
    the service's log. Collecting the records and handing them back with the
    result means the service says what it would have said had the parse happened
    in-process.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[tuple[int, str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append((record.levelno, record.name, record.getMessage()))


def main(argv: list[str] | None = None) -> int:
    """Parse the APK named in the job file and write the result beside it."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m dexatlas.tools.androguard.worker <job.json>", file=sys.stderr)
        return 2

    try:
        job = decode_job(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"unreadable job file: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    limits = _apply_limits(job)

    collector = _CollectingHandler()
    root = logging.getLogger()
    root.setLevel(job.log_level)
    root.addHandler(collector)

    try:
        result = _extract(job, collector, limits)
    except Exception as exc:
        result = _failed(job, collector, limits, exc)
    finally:
        root.removeHandler(collector)

    try:
        _write_result(job, result)
    except OSError as exc:
        print(f"could not write the result: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


def _extract(
    job: WorkerJob, collector: _CollectingHandler, limits: dict[str, bool]
) -> WorkerResult:
    """Index the APK, in this process."""
    # Imported here rather than at the top of the module: the service imports this
    # module's siblings, and importing the adapter must not drag Androguard into
    # the service's process.
    from dexatlas.config.settings import Settings
    from dexatlas.tools.androguard.adapter import AndroguardBackend

    backend = AndroguardBackend(Settings(), tool_version=job.tool_version)
    classes, methods, fields, references, strings, error = backend._extract_symbols(
        Path(job.apk_path),
        job.apk_sha256,
        method_limit=job.method_limit,
        string_limit=job.string_limit,
        instruction_limit=job.instruction_limit,
    )
    return WorkerResult(
        classes=classes,
        methods=methods,
        fields=fields,
        references=references,
        strings=strings,
        error=error,
        logs=collector.records,
        limits=limits,
        worker_pid=os.getpid(),
    )


def _failed(
    job: WorkerJob,
    collector: _CollectingHandler,
    limits: dict[str, bool],
    exc: Exception,
) -> WorkerResult:
    """The result of a worker that could not finish at all."""
    return WorkerResult(
        classes=[],
        methods=[],
        fields=[],
        references=[],
        strings=[],
        error=ToolError(
            tool="androguard",
            code=ToolErrorCode.PARSE_ERROR,
            message=f"androguard could not fully parse {Path(job.apk_path).name}",
            detail=f"{type(exc).__name__}: {exc}"[:2000],
        ),
        logs=collector.records,
        limits=limits,
        worker_pid=os.getpid(),
    )


def _write_result(job: WorkerJob, result: WorkerResult) -> None:
    """Write the result where the service will look for it.

    The result is written to a file rather than to stdout: the worker's stdout is
    not ours to keep clean, and a library that writes a line of its own would
    corrupt the result.
    """
    path = Path(job.result_path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(encode_result(result), handle)


def _apply_limits(job: WorkerJob) -> dict[str, bool]:
    """Bound what the worker may use, and say which bounds are in force.

    Memory is bounded where the platform can bound it: POSIX has ``setrlimit``,
    Windows has a job object. The size of a single file the worker writes is
    bounded on POSIX, and the worker writes into a temporary directory of its own
    that is deleted when it is done. The runtime is bounded by the service, which
    kills the worker when it has had its time.

    A limit that cannot be applied is not a reason to refuse to work: the worker
    carries on without it and records what it could not do. A worker that will
    not start is worse than a worker that runs a little less bounded.

    The answer travels back with the result. A bound nobody can see is a claim;
    this one is a measurement the service can read.
    """
    if os.name == "nt":
        return {
            "memory": _apply_windows_memory_limit(job.memory_limit_bytes),
            "temp_file_size": False,
        }
    return _apply_posix_limits(job)


def _apply_posix_limits(job: WorkerJob) -> dict[str, bool]:
    """Bound the worker's memory and file size with ``setrlimit``."""
    # Imported by name rather than with ``import resource``: the module is POSIX
    # only, and a type checker running on Windows cannot see the names in it.
    resource = importlib.import_module("resource")

    applied = {"memory": False, "temp_file_size": False}
    for limit, ceiling, name in (
        (resource.RLIMIT_AS, job.memory_limit_bytes, "memory"),
        (resource.RLIMIT_FSIZE, job.temp_file_limit_bytes, "temp_file_size"),
    ):
        try:
            _hard = resource.getrlimit(limit)[1]
            allowed = ceiling if _hard == resource.RLIM_INFINITY else min(ceiling, _hard)
            resource.setrlimit(limit, (allowed, allowed))
            applied[name] = resource.getrlimit(limit)[0] == allowed
        except (OSError, ValueError) as exc:
            logger.warning("androguard: could not apply a resource limit: %s", exc)
    return applied


def _apply_windows_memory_limit(limit_bytes: int) -> bool:
    """Bound the worker's memory with a Windows job object.

    Windows has no ``setrlimit``, so the ceiling is a job object the worker puts
    itself in: the kernel refuses an allocation that would take the process past
    the limit, and Python sees that as ``MemoryError``.

    A job the worker cannot join — because the process is already in a job that
    does not allow it, or because the limit is below what the interpreter has
    already committed — is not a reason to refuse to work.
    """
    global _JOB_HANDLE

    import ctypes

    load_library = getattr(ctypes, "WinDLL", None)
    if load_library is None:  # pragma: no cover - not Windows
        return False

    kernel32 = load_library("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel32.SetInformationJobObject.restype = ctypes.c_int
    kernel32.SetInformationJobObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    kernel32.AssignProcessToJobObject.restype = ctypes.c_int
    kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetCurrentProcess.argtypes = []

    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    # The two limits that cap memory: one for a process, one for the job.
    process_memory = 0x00000100
    job_memory = 0x00000200

    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        logger.warning("androguard: could not create a job object; the memory is unbounded")
        return False

    information = _ExtendedLimitInformation()
    information.BasicLimitInformation.LimitFlags = process_memory | job_memory
    information.ProcessMemoryLimit = limit_bytes
    information.JobMemoryLimit = limit_bytes
    if not kernel32.SetInformationJobObject(
        handle, 9, ctypes.byref(information), ctypes.sizeof(information)
    ):
        logger.warning("androguard: could not set the job's memory limit; the memory is unbounded")
        kernel32.CloseHandle(handle)
        return False

    if not kernel32.AssignProcessToJobObject(handle, kernel32.GetCurrentProcess()):
        logger.warning(
            "androguard: could not join the job object; the memory is unbounded (error %d)",
            ctypes.get_last_error(),
        )
        kernel32.CloseHandle(handle)
        return False

    _JOB_HANDLE = handle
    return True


if __name__ == "__main__":  # pragma: no cover - the worker's entry point
    raise SystemExit(main())
