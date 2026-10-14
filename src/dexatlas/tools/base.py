"""The analysis backend interface.

Backends are subprocess wrappers, never links. Invoking JADX as a separate process keeps
its parsing bugs and license obligations out of our process, and lets a crashing or
hangs engine degrade one step instead of the whole run.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dexatlas.config.settings import Settings
from dexatlas.core.models import Provenance, ToolError, ToolErrorCode

logger = logging.getLogger(__name__)

#: Output that exceeds this is treated as a runaway backend rather than a result.
_DEFAULT_MAX_OUTPUT = 256 * 1024 * 1024


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

    @property
    def ok(self) -> bool:
        return self.error is None


class Backend(ABC):
    """Base class for an external analysis engine.

    Subclasses declare how to locate and probe their tool, then implement extraction.
    """

    #: Stable backend name, recorded in provenance and the project's tool versions.
    name: str = "base"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # -- discovery ---------------------------------------------------------

    @abstractmethod
    def resolve(self) -> Path | None:
        """Locate the backend executable, or ``None`` if it is not installed."""

    @abstractmethod
    def version(self) -> str | None:
        """Backend version string, recorded as provenance."""

    def available(self) -> bool:
        return self.resolve() is not None

    def missing_error(self) -> ToolError:
        return ToolError(
            tool=self.name,
            code=ToolErrorCode.NOT_INSTALLED,
            message=f"{self.name} is not installed or not on PATH",
            detail=(
                f"Install {self.name} and make it discoverable, or set the "
                f"corresponding DEXATLAS_*_PATH environment variable. "
                f"DexAtlas continues without it and records this error."
            ),
        )

    # -- execution ---------------------------------------------------------

    def run(self, invocation: ToolInvocation) -> ToolOutcome:
        """Execute a backend invocation, converting every failure mode into a value.

        Argument arrays only — never a shell string — so nothing inside an analysed APK
        can inject a command.
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
            completed = subprocess.run(
                argv,
                cwd=invocation.cwd,
                env=invocation.env,
                capture_output=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return fail(
                ToolErrorCode.TIMEOUT,
                f"{self.name} exceeded its {timeout}s timeout and was terminated",
            )
        except FileNotFoundError:
            return self._not_found(argv)
        except PermissionError as exc:
            return fail(ToolErrorCode.NOT_INSTALLED, f"{self.name} is not executable: {exc}")
        except OSError as exc:
            return fail(ToolErrorCode.EXIT_NONZERO, f"{self.name} could not be executed: {exc}")

        stdout = self._decode(completed.stdout)
        stderr = self._decode(completed.stderr)

        if completed.returncode != 0:
            return ToolOutcome(
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=time.monotonic() - started,
                error=ToolError(
                    tool=self.name,
                    code=ToolErrorCode.EXIT_NONZERO,
                    message=f"{self.name} exited with code {completed.returncode}",
                    detail=stderr.strip()[-2000:] or stdout.strip()[-2000:] or None,
                ),
                argv=argv,
            )

        return ToolOutcome(
            returncode=0,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
            argv=argv,
        )

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
        limit = self._settings.tool_max_output_bytes
        if len(raw) > limit:
            logger.warning("%s: output truncated from %d to %d bytes", self.name, len(raw), limit)
            raw = raw[:limit]
        return raw.decode("utf-8", errors="replace")

    # -- provenance --------------------------------------------------------

    def provenance(self, apk_sha256: str, locator: str) -> Provenance:
        """Build the provenance record for anything this backend produced."""
        return Provenance(
            tool=self.name,
            tool_version=self.version(),
            apk_sha256=apk_sha256,
            locator=locator,
        )


def which_or_none(candidates: Sequence[str | None], *, names: Sequence[str] = ()) -> Path | None:
    """Resolve the first configured path, else fall back to a ``PATH`` lookup."""
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def java_available() -> bool:
    """Whether a JRE is present. Apktool and JADX both need one."""
    return shutil.which("java") is not None


def parse_error(tool: str, exc: Exception) -> ToolError:
    return ToolError(
        tool=tool,
        code=ToolErrorCode.PARSE_ERROR,
        message=f"could not parse {tool} output: {exc}",
        detail=type(exc).__name__,
    )


def coerce(value: Any) -> Any:
    """Best-effort conversion of a tool's loosely typed JSON field."""
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
