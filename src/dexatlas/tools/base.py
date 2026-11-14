"""The analysis backend interface.

The rule is that a backend parses untrusted input in a process of its own: the engines
are invoked, never linked.

Androguard is a library rather than a program, so there is no tool to shell out to. It
parses the DEX files in a worker process instead, started through this class's runner
so that the same timeout and the same tree kill apply. What comes back across the
boundary is data, and a malformed DEX is a ToolError, not the end of the run.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from dexatlas.config.settings import Settings
from dexatlas.core.models import Provenance, ToolError, ToolErrorCode

logger = logging.getLogger(__name__)

#: The signal that ends a process without giving it a chance to react.
#:
#: ``SIGKILL`` does not exist on Windows, where the tree is killed by
#: ``taskkill`` instead, so the portable name is looked up rather than imported.
_KILL_SIGNAL = getattr(signal, "SIGKILL", signal.SIGTERM)

#: Windows' flag for putting a child into a process group of its own.
_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

#: How long the tree is given to die before the call gives up on it.
_TERMINATION_GRACE_SECONDS = 5.0

#: How long ``taskkill`` is given to do its work.
_TASKKILL_TIMEOUT_SECONDS = 30.0

#: What the tree kill achieved.
#:
#: "Was terminated" is a claim about the machine, so the three outcomes are
#: kept apart: the tree was killed, the launcher had already exited on its own,
#: or nothing could be killed.
_KILLED = "killed"
_ALREADY_EXITED = "already-exited"
_NOT_TERMINATED = "not-terminated"


@dataclass(slots=True)
class ToolInvocation:
    """A single backend call."""

    argv: Sequence[str]
    cwd: Path | None = None
    timeout: int | None = None
    env: dict[str, str] | None = None


@dataclass(slots=True)
class ToolOutcome:
    """The result of a backend call — a value, never an exception.

    ``returncode != 0`` is a normal outcome for tools parsing hostile input. Callers
    branch on :attr:`error` and continue; they do not catch a backend failure.
    """

    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    error: ToolError | None = None
    argv: Sequence[str] = field(default_factory=tuple)
    truncated: tuple[str, ...] = ()
    """The streams whose output was cut short at the cap.

    A backend that writes more than the cap did not fail: it wrote more than
    the caller is willing to hold. What is here is the first
    ``tool_max_output_bytes`` of it and the rest is gone, so a reader of the
    result has to be told that it is not the whole of it.
    """

    @property
    def ok(self) -> bool:
        return self.error is None


class Backend(ABC):
    """Base class for an external analysis engine.

    Subclasses declare how to locate and probe their tool -- :meth:`resolve` and
    :meth:`version` -- and then implement the step that reads the APK. There is
    no common ``extract`` to implement: the three backends read different things
    from an APK, so each one names its own way of doing it, and a pipeline that
    called all of them through one signature would have to invent a shape that
    fits none of them.
    """

    #: Stable backend name, recorded in provenance and the project's tool versions.
    name: str = "base"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # The version, asked for once per backend. Every symbol a backend
        # indexes carries a provenance record, and every record names the
        # version, so a backend that has to consult the package index to
        # answer would do that once per symbol.
        self._record_version: str | None = None
        self._record_version_known = False

    # -- discovery ---------------------------------------------------------

    @abstractmethod
    def resolve(self) -> Path | None:
        """Locate the backend executable, or ``None`` if it is not installed."""

    @abstractmethod
    def version(self) -> str | None:
        """Backend version string, recorded as provenance."""

    def available(self) -> bool:
        return self.resolve() is not None

    #: Environment variable that pins this backend's location, when there is one.
    #:
    #: Empty means there is no variable to point at, and the not-installed
    #: message stays quiet about one. A backend that *does* have a variable
    #: overrides this with its own name: there is no pattern to fill in, because
    #: a reader told to set ``DEXATLAS_<BACKEND>_PATH`` has been told nothing
    #: they can act on.
    path_env_var: str = ""

    #: Shell command that installs this backend, shown in the not-installed error.
    install_hint: str = "Install it and make it discoverable on PATH."

    def missing_error(self) -> ToolError:
        pin = f" Or point {self.path_env_var} at it." if self.path_env_var else ""
        return ToolError(
            tool=self.name,
            code=ToolErrorCode.NOT_INSTALLED,
            message=f"{self.name} is not installed or not on PATH",
            detail=(
                f"{self.install_hint}{pin} "
                f"DexAtlas continues without {self.name} and records this error."
            ),
        )

    # -- execution ---------------------------------------------------------

    def run(self, invocation: ToolInvocation) -> ToolOutcome:
        """Execute a backend invocation, converting every failure mode into a value.

        Argument arrays only — never a shell string — so nothing inside an analysed APK
        can inject a command.

        The call really is bounded by the timeout: a backend that spawns a launcher
        which spawns the tool takes the whole tree down with it, rather than
        leaving the work running behind the caller's back.

        The output is captured through files rather than pipes. A pipe stays
        open for every process that inherited it, so a tool that outlived its
        launcher would keep the reader waiting long past the timeout — which is
        exactly the case the timeout exists for.
        """
        started = time.monotonic()
        argv = list(invocation.argv)
        timeout = invocation.timeout or self._settings.tool_timeout_seconds

        def fail(code: ToolErrorCode, message: str, detail: str = "") -> ToolOutcome:
            return ToolOutcome(
                returncode=-1,
                stdout="",
                stderr=detail,
                duration_seconds=time.monotonic() - started,
                error=ToolError(tool=self.name, code=code, message=message, detail=detail or None),
                argv=argv,
            )

        if not argv:
            return fail(ToolErrorCode.UNSUPPORTED, "empty invocation")

        logger.debug("%s: %s", self.name, " ".join(argv))

        try:
            with _temp_binary_file() as out_file, _temp_binary_file() as err_file:
                try:
                    process = subprocess.Popen(
                        argv,
                        cwd=invocation.cwd,
                        env=invocation.env,
                        stdin=subprocess.DEVNULL,
                        stdout=out_file,
                        stderr=err_file,
                        shell=False,
                        **_process_group_options(),
                    )
                except FileNotFoundError:
                    return self._not_found(argv)
                except PermissionError as exc:
                    return fail(
                        ToolErrorCode.NOT_INSTALLED, f"{self.name} is not executable: {exc}"
                    )
                except OSError as exc:
                    return fail(
                        ToolErrorCode.EXIT_NONZERO, f"{self.name} could not be executed: {exc}"
                    )

                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    message = _timeout_message(self.name, timeout, _terminate_tree(process))
                    return fail(ToolErrorCode.TIMEOUT, message)

                stdout_raw, stdout_size = _read_capped(
                    out_file, self._settings.tool_max_output_bytes
                )
                stderr_raw, stderr_size = _read_capped(
                    err_file, self._settings.tool_max_output_bytes
                )
                stdout = self._decode(stdout_raw)
                stderr = self._decode(stderr_raw)
                # The cap is a promise about what is read, so exceeding it has
                # to be said out loud: the output that is here is the first
                # part of what the backend wrote, and a caller that reads it
                # without knowing that reads a cut-off thing as if it were
                # whole.
                limit = self._settings.tool_max_output_bytes
                truncated = tuple(
                    name
                    for name, size in (("stdout", stdout_size), ("stderr", stderr_size))
                    if size > limit
                )
                for name in truncated:
                    logger.warning(
                        "%s: %s output was cut at the %d-byte cap", self.name, name, limit
                    )

                if process.returncode != 0:
                    return ToolOutcome(
                        returncode=process.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        duration_seconds=time.monotonic() - started,
                        error=ToolError(
                            tool=self.name,
                            code=ToolErrorCode.EXIT_NONZERO,
                            message=f"{self.name} exited with code {process.returncode}",
                            detail=stderr.strip()[-2000:] or stdout.strip()[-2000:] or None,
                        ),
                        argv=argv,
                        truncated=truncated,
                    )

                return ToolOutcome(
                    returncode=0,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=time.monotonic() - started,
                    argv=argv,
                    truncated=truncated,
                )
        except OSError as exc:
            return fail(ToolErrorCode.EXIT_NONZERO, f"{self.name} could not be executed: {exc}")

    def _not_found(self, argv: Sequence[str]) -> ToolOutcome:
        executable = argv[0] if argv else self.name
        return ToolOutcome(
            returncode=-1,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            error=ToolError(
                tool=self.name,
                code=ToolErrorCode.NOT_INSTALLED,
                message=f"{executable} not found",
                detail="Install the backend or configure its path via the DEXATLAS_* environment.",
            ),
            argv=tuple(argv),
        )

    def _decode(self, raw: bytes) -> str:
        """The bytes a backend wrote, as text.

        The bytes have already been cut at the cap by :func:`_read_capped`, so
        there is nothing left to cut here. A check for it would be a branch
        that can never be taken, and a truncation nobody can see is the one
        defect this class exists to prevent.
        """
        return raw.decode("utf-8", errors="replace")

    # -- provenance --------------------------------------------------------

    def provenance(self, apk_sha256: str, locator: str) -> Provenance:
        """Build the provenance record for anything this backend produced."""
        return Provenance(
            tool=self.name,
            tool_version=self._version_for_records(),
            apk_sha256=apk_sha256,
            locator=locator,
        )

    def _version_for_records(self) -> str | None:
        """The backend's version, asked for once per backend.

        A version cannot change while an analysis runs, so the answer is
        remembered: the cost of a symbol should be the cost of the symbol,
        and not a question asked of the tool for every one of them.
        """
        if not self._record_version_known:
            self._record_version_known = True
            self._record_version = self.version()
        return self._record_version


def _timeout_message(tool: str, timeout: int, outcome: str) -> str:
    """What to say about a backend that outlived its timeout.

    The message is a claim about the machine, so it says what actually
    happened: the tree was killed, the launcher had already exited on its own,
    or nothing could be killed and the work may still be running.
    """
    if outcome == _KILLED:
        return f"{tool} exceeded its {timeout}s timeout and was terminated"
    if outcome == _ALREADY_EXITED:
        return f"{tool} exceeded its {timeout}s timeout; its launcher had already exited"
    return f"{tool} exceeded its {timeout}s timeout and could not be terminated"


def _process_group_options() -> dict[str, Any]:
    """Put the child into a process group of its own.

    A backend is a launcher as often as it is a tool: ``jadx.bat`` runs
    ``java.exe``, and the launcher is all that a timeout on the direct child
    would reach. A group of its own is what lets the whole tree be taken down
    together — on POSIX by signalling the group, on Windows by asking
    ``taskkill`` to walk the children.
    """
    if os.name == "nt":
        return {"creationflags": _CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_tree(process: subprocess.Popen[bytes]) -> str:
    """Kill the process and everything it started.

    Killing only the direct child leaves the tool running. On Windows
    ``jadx.bat`` is a ``cmd.exe`` whose child is ``java.exe``: the work
    carries on, holding the output it inherited, and the call that started it
    waits for it anyway.

    Returns what was achieved — see :data:`_KILLED` and its neighbours.
    """
    outcome = _taskkill_tree(process) if os.name == "nt" else _kill_process_group(process)
    _reap(process)
    return outcome


def _kill_process_group(process: subprocess.Popen[bytes]) -> str:
    """Kill the child's process group, which on POSIX is the whole tree.

    The child leads its own group, so the group's id is the child's pid.
    ``kill`` with a negative pid addresses a process group, which is what
    ``killpg`` does and is spelled the same way on every platform.
    """
    try:
        os.kill(-process.pid, _KILL_SIGNAL)
    except ProcessLookupError:
        # The group is empty, so everything in it is already gone.
        return _ALREADY_EXITED
    except (PermissionError, OSError):
        logger.warning("could not kill the process group %d", process.pid)
        return _NOT_TERMINATED
    return _KILLED


def _taskkill_tree(process: subprocess.Popen[bytes]) -> str:
    """Kill a process tree on Windows.

    ``taskkill /T`` walks the parent-child relationship, so a launcher and the
    tool it started die together, and ``/F`` is what makes it immediate.

    Only a successful call counts as a kill. A launcher that had already
    exited cannot be walked from, so whatever it started would be left
    running — and "terminated" is a claim about the machine, not about the
    attempt.
    """
    try:
        completed = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            timeout=_TASKKILL_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _NOT_TERMINATED
    if completed.returncode == 0:
        return _KILLED
    if process.poll() is not None:
        # The launcher had already exited — it had finished the work itself,
        # or it had left something behind that no longer has a parent to be
        # found through.
        return _ALREADY_EXITED
    return _NOT_TERMINATED


def _reap(process: subprocess.Popen[bytes]) -> None:
    """Collect the killed child, waiting briefly for it to go."""
    try:
        process.wait(timeout=_TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            logger.warning("a backend process did not exit after being killed")


@contextmanager
def _temp_binary_file() -> Iterator[IO[bytes]]:
    """A temporary file as a plain binary file object, on every platform.

    ``tempfile.TemporaryFile`` returns a plain file object on POSIX and a
    wrapper carrying a ``.file`` attribute on Windows. Code that reaches for
    ``.file`` therefore works on the machine it was written on and fails on
    every other one — which is exactly what happened here, and why the capture
    does not use ``TemporaryFile`` at all.

    The file is created with ``mkstemp`` and handed to ``os.fdopen``, so what
    the caller holds is the same kind of object on Linux and on Windows, and
    the subprocess can inherit the descriptor from it on both.
    """
    descriptor, path = tempfile.mkstemp(prefix="dexatlas-backend-")
    try:
        with os.fdopen(descriptor, "w+b") as handle:
            yield handle
    finally:
        with suppress(OSError):  # pragma: no cover - already gone
            os.unlink(path)


def _read_capped(handle: IO[bytes], limit: int) -> tuple[bytes, int]:
    """What a backend wrote, up to the cap, and how much of it there was.

    The file is truncated first. A runaway backend can write far more than the
    cap allows, and the cap exists to keep that from becoming the problem.

    The size the file had is handed back as well. A reader that is given the
    first ``limit`` bytes of a longer file has to be told that the rest is not
    there, and the only place that knows it is here.
    """
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    if size > limit:
        handle.truncate(limit)
    handle.seek(0)
    return handle.read(), size


def truncation_error(tool: str, streams: Sequence[str], limit: int) -> ToolError:
    """The error that says a backend's output was cut at the cap.

    A backend that wrote more than the cap did not fail, but what came back is
    not all of it. The caller that turns this into a record on the project is
    the pipeline; the error is made here so that every backend says the same
    thing about the same event.

    The cap is named with its value, because a limit a reader cannot check is
    a claim rather than a limit.
    """
    names = ", ".join(streams)
    return ToolError(
        tool=tool,
        code=ToolErrorCode.OUTPUT_TRUNCATED,
        message=(
            f"{tool} wrote more than the {limit}-byte output cap: its {names} output was cut "
            f"short, and what was read is not all of it"
        ),
        detail=(
            f"the cap is Settings.tool_max_output_bytes ({limit} bytes). What was kept is the "
            f"first {limit} bytes of what the backend wrote; the rest was discarded."
        ),
    )


def which_or_none(candidates: Sequence[str | None], *, names: Sequence[str] = ()) -> Path | None:
    """Resolve the first configured path, else fall back to a ``PATH`` lookup.

    A candidate says one of three things, and the three are not interchangeable:

    - ``None`` — not configured. The tool is looked up on ``PATH``, the default
      behaviour.
    - ``""`` — explicitly disabled. No ``PATH`` lookup happens, so a tool that
      happens to be installed cannot be used against the operator's wishes.
    - a path — the tool to use. A path that does not exist is ignored and the
      ``PATH`` lookup still applies, so a stale pin does not take a backend
      offline; the substitution is logged rather than made silently.

    An empty string anywhere in ``candidates`` disables the backend outright: an
    explicit "not this one" outranks any other candidate.
    """
    if any(candidate == "" for candidate in candidates):
        return None
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
            logger.warning("configured path %s does not exist; falling back to a PATH lookup", path)
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None
