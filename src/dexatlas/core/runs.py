"""Analysis runs — the identity of one analysis, and the lifecycle around it.

A *project* is the APK. Its id is a content hash, so the same bytes always map
to the same project, and re-analysing an APK replaces what is stored under it.

A *run* is one attempt at analysing it. The two are different things, and
conflating them is what lets a reader see the symbols of one run beside the
evidence of another: the project id says which APK was analysed and says
nothing about *when*, or *by which tools*, or *whether the result is whole*.

So a run carries an identity of its own — one that says nothing about the
APK — and with it the facts that belong to an attempt rather than to a file:
the tool versions that took part, the hash of the input, how the execution
ended, and how much of what the run set out to read it actually read.

This module holds that model and the two small pieces of machinery around it:
the token that stops a running analysis, and the exception that says it was
stopped.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Self
from uuid import uuid4

from pydantic import BaseModel, Field

from dexatlas.core.models import ToolError

#: How many hex digits of the random identifier a run id carries.
#:
#: Sixteen hex digits are sixty-four bits, which is more than enough to keep
#: two runs apart — and the id is a directory name as well as a key, so it
#: stays short enough to read in a path.
RUN_ID_LENGTH = 16


def new_run_id() -> str:
    """A run id, chosen at random and saying nothing about the APK.

    The id cannot be derived from the APK's hash: two analyses of the same
    bytes are two runs, and an id derived from the bytes would give them the
    same name — which is the identity this whole mechanism exists to remove.
    """
    return f"run_{uuid4().hex[:RUN_ID_LENGTH]}"


class RunStatus(StrEnum):
    """How a run ended.

    The execution status, not the project's: a project says whether it holds
    a result, a run says what happened to one attempt.
    """

    PENDING = "pending"
    """The run exists and has not started."""

    RUNNING = "running"
    """The backends are running."""

    COMPLETED = "completed"
    """The analysis ran to the end."""

    FAILED = "failed"
    """The analysis did not finish: it raised, or it produced nothing."""

    CANCELLED = "cancelled"
    """The analysis was stopped on request."""


class RunCompleteness(StrEnum):
    """How much of what the run set out to read it actually read.

    A backend that fails does not make the run's other findings untrue — but
    it does make the result incomplete, and a reader who is not told that
    reads a partial index as a whole one.
    """

    COMPLETE = "complete"
    """Every step of the run produced its output."""

    PARTIAL = "partial"
    """Some step did not, so the result has gaps in it."""


class AnalysisRun(BaseModel):
    """One analysis of one APK.

    The run's own id is independent of the APK's: two analyses of the same
    bytes are two runs, and the second one does not overwrite the first — it
    is published in its place, and the first stays readable until then.
    """

    id: str
    """This run's identifier. Independent of the APK it analysed."""

    project_id: str
    """The project the run belongs to: the APK's content-addressed id."""

    apk_sha256: str
    """The hash of the bytes the run was given.

    Recorded on the run as well as on the project, because the project id is
    derived from it and a reader asking "which bytes?" should not have to
    know that.
    """

    status: RunStatus = RunStatus.PENDING
    """How the execution ended."""

    completeness: RunCompleteness = RunCompleteness.COMPLETE
    """Whether the result covers everything the run set out to read."""

    tool_versions: dict[str, str | None] = Field(default_factory=dict)
    """The version of every tool that took part.

    A run is reproducible only if the tools that produced it are known. The
    versions belong to the run rather than to the project: the same APK
    analysed twice, with a decompiler upgraded in between, is two runs with
    two sets of versions.
    """

    errors: list[ToolError] = Field(default_factory=list)
    """What went wrong, in the run that went wrong."""

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """When the run began."""

    finished_at: datetime | None = None
    """When the run ended, or ``None`` while it is still going."""

    duration_seconds: float | None = None
    """How long the run took.

    ``None`` means it was never measured — a run that has not finished has
    no duration yet, and zero is a duration no run reported.
    """

    workspace: Path | None = None
    """Where this run's own output lives.

    Every run writes to a directory of its own, so two analyses of one APK
    cannot write over each other's decompiled output. The project's
    ``workspace`` column names the run that is currently published.
    """

    @classmethod
    def start(
        cls,
        project_id: str,
        apk_sha256: str,
        *,
        tool_versions: dict[str, str | None] | None = None,
        workspace: Path | None = None,
    ) -> Self:
        """A run that is about to start."""
        return cls(
            id=new_run_id(),
            project_id=project_id,
            apk_sha256=apk_sha256,
            status=RunStatus.PENDING,
            tool_versions=dict(tool_versions or {}),
            workspace=workspace,
        )

    @property
    def finished(self) -> bool:
        """Whether the run has ended, one way or another."""
        return self.status in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }


class AnalysisCancelled(Exception):
    """The analysis was stopped on request.

    Not a failure of the analysis and not a failure of a backend: nobody
    asked for this APK to be analysed any more. The distinction matters
    because the two leave different things behind — a failure is recorded on
    the project, a cancellation is not.
    """


class CancellationToken:
    """A request to stop a running analysis.

    The analysis runs in a background task on another thread, so "stop it"
    has to be a fact the running code can observe rather than a call into it.
    The token is that fact: the requester sets it, and the analysis checks it
    at the points where stopping is safe.

    Stopping is safe between steps and before the publish. It is not safe in
    the middle of a backend — that process is killed by the backend's own
    timeout, and the analysis picks the result up when it returns.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Ask the analysis to stop."""
        self._event.set()

    @property
    def cancelled(self) -> bool:
        """Whether the analysis has been asked to stop."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Stop the analysis if it has been asked to.

        Called at the points where nothing half-written can be left behind.
        """
        if self._event.is_set():
            raise AnalysisCancelled("the analysis was cancelled")


__all__ = [
    "RUN_ID_LENGTH",
    "AnalysisCancelled",
    "AnalysisRun",
    "CancellationToken",
    "RunCompleteness",
    "RunStatus",
    "new_run_id",
]
