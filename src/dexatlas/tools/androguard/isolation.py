"""The boundary between the service and the isolated DEX parser.

The Androguard adapter reads an untrusted APK. Parsing is the part of an analysis
that runs on bytes the service did not write, so it is the part that gets a process
of its own: a DEX file that takes the interpreter down takes down the worker, and
the service — which only ever sees a value — carries on.

This module is that boundary. It holds the job the worker is given, the result it
sends back, and the launcher that starts it. Nothing here knows how to index a DEX
file: that is the adapter's job, and the worker calls into it.

The result crosses as JSON rather than as a pickle. A pickle is executable —
reading one back is running the code that wrote it, and the code that wrote it ran
against untrusted input. JSON is data. The models it carries are rebuilt through
their own validators, so what arrives is what the service would have built itself:
the same descriptors, the same canonical ids, the same provenance.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from dexatlas.core.models import (
    ClassRef,
    FieldRef,
    MethodRef,
    MethodReference,
    StringConstant,
    ToolError,
    ToolErrorCode,
)
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome

#: The module the worker runs as.
#:
#: ``python -m`` rather than the path to a script: the same spelling on Windows and
#: on Linux, and what it starts is a process that can be killed with its tree.
WORKER_MODULE = "dexatlas.tools.androguard.worker"

#: How much memory the worker may use.
#:
#: A ceiling, not an allocation: the worker uses what the APK needs and fails when
#: it needs more. The number belongs in :class:`~dexatlas.config.settings.Settings`
#: — an embedder should be able to choose it — but the settings module belongs to
#: another part of the project, so it lives here until it can be moved.
DEFAULT_MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024

#: How large a single file the worker may write.
#:
#: This is the temporary-disk bound the platform can enforce: POSIX caps the size
#: of a file a process writes, and the worker's temporary directory is its own, so
#: everything it writes while parsing lands in one place that is deleted when the
#: worker is done. The limit is generous enough to leave the result file alone.
DEFAULT_TEMP_FILE_LIMIT_BYTES = 1024 * 1024 * 1024

#: The shape the pipeline expects back: the index, and the error that says what
#: was missing from it.
SymbolIndex = tuple[
    list[ClassRef],
    list[MethodRef],
    list[FieldRef],
    list[MethodReference],
    list[StringConstant],
    ToolError | None,
]


@dataclass(frozen=True, slots=True)
class WorkerJob:
    """What the worker is asked to do.

    The job is written to a file rather than passed on the command line: a path can
    be long, and a command line is a place where quoting goes wrong.
    """

    apk_path: str
    apk_sha256: str
    method_limit: int
    string_limit: int
    instruction_limit: int
    tool_version: str | None = None
    result_path: str = ""
    log_level: int = logging.WARNING
    memory_limit_bytes: int = DEFAULT_MEMORY_LIMIT_BYTES
    temp_file_limit_bytes: int = DEFAULT_TEMP_FILE_LIMIT_BYTES


@dataclass(slots=True)
class WorkerResult:
    """What the worker sends back."""

    classes: list[ClassRef]
    methods: list[MethodRef]
    fields: list[FieldRef]
    references: list[MethodReference]
    strings: list[StringConstant]
    error: ToolError | None = None
    logs: list[tuple[int, str, str]] = field(default_factory=list)
    limits: dict[str, bool] = field(default_factory=dict)
    worker_pid: int = 0

    def as_index(self) -> SymbolIndex:
        """The index, in the shape the pipeline expects."""
        return (
            self.classes,
            self.methods,
            self.fields,
            self.references,
            self.strings,
            self.error,
        )


@dataclass(slots=True)
class WorkerOutcome:
    """What came back from the worker: a result, or the reason there is none."""

    result: WorkerResult | None = None
    error: ToolError | None = None


def encode_job(job: WorkerJob) -> dict[str, Any]:
    """The job as JSON."""
    return {
        "apk_path": job.apk_path,
        "apk_sha256": job.apk_sha256,
        "method_limit": job.method_limit,
        "string_limit": job.string_limit,
        "instruction_limit": job.instruction_limit,
        "tool_version": job.tool_version,
        "result_path": job.result_path,
        "log_level": job.log_level,
        "memory_limit_bytes": job.memory_limit_bytes,
        "temp_file_limit_bytes": job.temp_file_limit_bytes,
    }


def decode_job(payload: dict[str, Any]) -> WorkerJob:
    """The job, read back from JSON."""
    return WorkerJob(
        apk_path=str(payload["apk_path"]),
        apk_sha256=str(payload["apk_sha256"]),
        method_limit=int(payload["method_limit"]),
        string_limit=int(payload["string_limit"]),
        instruction_limit=int(payload["instruction_limit"]),
        tool_version=payload.get("tool_version"),
        result_path=str(payload.get("result_path", "")),
        log_level=int(payload.get("log_level", logging.WARNING)),
        memory_limit_bytes=int(payload.get("memory_limit_bytes", DEFAULT_MEMORY_LIMIT_BYTES)),
        temp_file_limit_bytes=int(
            payload.get("temp_file_limit_bytes", DEFAULT_TEMP_FILE_LIMIT_BYTES)
        ),
    )


def encode_result(result: WorkerResult) -> dict[str, Any]:
    """The result as JSON.

    The models are dumped in their JSON form, so what crosses the boundary is data
    and not objects: the receiving side rebuilds the models through their own
    validators and gets exactly the models it would have built itself.
    """
    return {
        "classes": [item.model_dump(mode="json") for item in result.classes],
        "methods": [item.model_dump(mode="json") for item in result.methods],
        "fields": [item.model_dump(mode="json") for item in result.fields],
        "references": [item.model_dump(mode="json") for item in result.references],
        "strings": [item.model_dump(mode="json") for item in result.strings],
        "error": result.error.model_dump(mode="json") if result.error is not None else None,
        "logs": [list(entry) for entry in result.logs],
        "limits": dict(result.limits),
        "worker_pid": result.worker_pid,
    }


def decode_result(payload: dict[str, Any]) -> WorkerResult:
    """The result, read back from JSON.

    The models are rebuilt through their own validators, so a result that crossed
    the boundary is the result the service would have built itself: the same
    canonical descriptors, the same canonical method ids, the same provenance.
    """
    raw_classes: list[Any] = payload.get("classes") or []
    raw_methods: list[Any] = payload.get("methods") or []
    raw_fields: list[Any] = payload.get("fields") or []
    raw_references: list[Any] = payload.get("references") or []
    raw_strings: list[Any] = payload.get("strings") or []
    raw_error: Any = payload.get("error")
    raw_logs: list[Any] = payload.get("logs") or []
    raw_limits: dict[str, Any] = payload.get("limits") or {}

    logs: list[tuple[int, str, str]] = []
    for entry in raw_logs:
        level, name, message = entry
        logs.append((int(level), str(name), str(message)))

    return WorkerResult(
        classes=[ClassRef.model_validate(item) for item in raw_classes],
        methods=[MethodRef.model_validate(item) for item in raw_methods],
        fields=[FieldRef.model_validate(item) for item in raw_fields],
        references=[MethodReference.model_validate(item) for item in raw_references],
        strings=[StringConstant.model_validate(item) for item in raw_strings],
        error=ToolError.model_validate(raw_error) if raw_error else None,
        logs=logs,
        limits={str(key): bool(value) for key, value in raw_limits.items()},
        worker_pid=int(payload.get("worker_pid", 0)),
    )


def worker_environment(work: Path) -> dict[str, str]:
    """The environment the worker runs in.

    The temporary-directory variables point at the worker's own directory, so
    everything it writes while parsing lands in one place, and that place is
    deleted when the worker is done.

    ``PYTHONPATH`` carries the service's import path, so the worker imports the
    same DexAtlas the service is running — including when the package was found
    some other way, such as a source checkout that is already on the path.
    """
    env = dict(os.environ)
    for name in ("TMPDIR", "TEMP", "TMP"):
        env[name] = str(work)
    import_path = [entry for entry in sys.path if entry]
    if import_path:
        inherited = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
        env["PYTHONPATH"] = os.pathsep.join(import_path + inherited)
    return env


def run_worker(runner: Backend, job: WorkerJob, *, timeout: int) -> WorkerOutcome:
    """Run the worker, and bring back what it produced.

    The worker is started through the base class's subprocess runner, which is what
    bounds its runtime: a worker that has had its time is killed with its tree, and
    the outcome says so. Everything the worker wrote lands in a directory of its
    own, which is deleted whether the worker succeeded or not.

    A worker that died is not a raised exception. It is a parse failure, recorded
    the way every other parse failure is recorded, because that is what it means:
    the DEX files were not indexed.
    """
    with tempfile.TemporaryDirectory(prefix="dexatlas-androguard-") as workdir:
        work = Path(workdir)
        result_file = work / "result.json"
        job_file = work / "job.json"
        job = replace(job, result_path=str(result_file))
        job_file.write_text(json.dumps(encode_job(job)), encoding="utf-8")

        outcome = runner.run(
            ToolInvocation(
                argv=[sys.executable, "-m", WORKER_MODULE, str(job_file)],
                env=worker_environment(work),
                timeout=timeout,
            )
        )
        return _read_outcome(outcome, job, result_file)


def _read_outcome(outcome: ToolOutcome, job: WorkerJob, result_file: Path) -> WorkerOutcome:
    """Turn what the worker left behind into a result, or into the reason there is none."""
    apk_name = Path(job.apk_path).name

    if outcome.error is not None:
        if outcome.error.code is ToolErrorCode.TIMEOUT:
            # A timeout is not a parse failure: the parse did not finish, and the
            # record says which of the two happened.
            return WorkerOutcome(error=outcome.error)
        return WorkerOutcome(
            error=ToolError(
                tool="androguard",
                code=ToolErrorCode.PARSE_ERROR,
                message=f"androguard could not fully parse {apk_name}",
                detail=(outcome.error.detail or outcome.error.message)[:2000],
            )
        )

    if not result_file.is_file():
        return WorkerOutcome(
            error=ToolError(
                tool="androguard",
                code=ToolErrorCode.PARSE_ERROR,
                message=f"androguard could not fully parse {apk_name}",
                detail="the isolated worker finished without producing a result",
            )
        )

    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        result = decode_result(payload)
    except Exception as exc:
        return WorkerOutcome(
            error=ToolError(
                tool="androguard",
                code=ToolErrorCode.PARSE_ERROR,
                message=f"androguard could not fully parse {apk_name}",
                detail=(
                    f"the isolated worker produced a result that could not be read: "
                    f"{type(exc).__name__}: {exc}"
                )[:2000],
            )
        )
    return WorkerOutcome(result=result)
