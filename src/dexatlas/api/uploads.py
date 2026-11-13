"""The upload policy, shared by the REST API and the workbench.

An upload is a policy about work before any analysis: how large a file may
be, where it is staged, how it is named, how long it is kept, and which of
the stored files a running analysis is still reading. Those decisions do
not depend on which transport accepted the bytes, so they live here once;
the REST transport and the workbench both call these functions instead of
carrying two copies that could drift.

What the two transports do with an upload is still theirs to decide: the
REST ``/analyze`` answers with a job reference and the workbench redirects
to its own screens, so the shapes of their answers are not defined here.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from dexatlas.config.settings import Settings
from dexatlas.core.ingest import ApkValidationError, UploadTooLarge, inspect_apk, save_upload
from dexatlas.core.models import ApkMetadata
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import CancellationToken

logger = logging.getLogger(__name__)

#: Uploads land here before analysis. Scoped to the workspace, never executed.
UPLOAD_DIRNAME = "uploads"

#: The name an upload is stored under when the client did not give one.
DEFAULT_UPLOAD_NAME = "upload.apk"

#: The longest a stored file name may be, in bytes.
#:
#: A file name cannot be longer than this on any filesystem DexAtlas runs on,
#: so a longer name cannot name anything -- and a name that is stored is a
#: name somebody may try to use.
MAX_NAME_BYTES = 255

#: The upload is larger than the limit.
#:
#: Starlette renamed this constant and deprecated the old name, so the number
#: is written out rather than imported from a version-dependent place.
HTTP_CONTENT_TOO_LARGE = 413

#: How long an uploaded APK is kept, in seconds.
#:
#: The upload is the bytes the analysis was given, and it is kept for a
#: while so that the operator can look at the file the analysis actually
#: read. It is not kept for ever: the workspace belongs to the server, and
#: an unbounded pile of APKs is how it fills up. The window is counted from
#: the end of the analysis that used the upload, so an APK that is analysed
#: again is kept for another window.
UPLOAD_RETENTION_SECONDS = 24 * 60 * 60

#: The environment variable that overrides the retention window.
#:
#: The project's settings live in ``config/settings.py``, and this change
#: does not touch them, so the variable is read here. It uses the same
#: ``DEXATLAS_`` prefix every other setting uses.
UPLOAD_RETENTION_ENV = "DEXATLAS_UPLOAD_RETENTION_SECONDS"


def stored_name(filename: str | None) -> str:
    """The name the upload is stored under.

    The client's name is kept, because a reader of the report wants to know
    what the file was called. It is made safe first: a name may not name a
    directory, may not be empty, and may not be longer than a file name can
    be -- a name that is stored is a name somebody may try to use.
    """
    name = Path(filename or "").name
    if not name or name in {".", ".."}:
        return DEFAULT_UPLOAD_NAME
    encoded = name.encode("utf-8", errors="replace")
    if len(encoded) > MAX_NAME_BYTES:
        name = encoded[:MAX_NAME_BYTES].decode("utf-8", errors="ignore")
    return name or DEFAULT_UPLOAD_NAME


class UploadSizeLimitMiddleware:
    """Refuse an upload that declares more than the limit, before it is read.

    The framework parses a request's body before the handler ever sees it, so
    the only place a declared size can be refused is in front of the route.
    A request that declares no length — a chunked upload — is caught by the
    counter in the handler instead, which stops the copy while it streams.
    """

    def __init__(self, app: ASGIApp, limit: Callable[[], int]) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        max_bytes = self.limit()
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > max_bytes:
            response = JSONResponse(
                {"detail": f"the upload is larger than the {max_bytes}-byte limit"},
                status_code=HTTP_CONTENT_TOO_LARGE,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


@dataclass
class RunningAnalysis:
    """One analysis that is running, and the way to stop it."""

    token: CancellationToken
    apk_path: Path


class RunningAnalyses:
    """The analyses that are running, by the project they are running for.

    The analysis runs in a background task, so "stop it" cannot be a call
    into it: it has to be a fact the running code can observe. The token is
    that fact -- the request sets it, and the analysis stops at the next
    point where stopping cannot leave half-written results behind.

    The registry is keyed by the project id, which is the handle the API
    already gave the caller when it accepted the upload.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._analyses: dict[str, RunningAnalysis] = {}

    def start(self, project_id: str, apk_path: Path) -> CancellationToken:
        """Register an analysis that is starting, and hand back its token."""
        token = CancellationToken()
        with self._lock:
            self._analyses[project_id] = RunningAnalysis(token=token, apk_path=apk_path)
        return token

    def finish(self, project_id: str) -> None:
        """Forget an analysis that has ended."""
        with self._lock:
            self._analyses.pop(project_id, None)

    def cancel(self, project_id: str) -> bool:
        """Ask an analysis to stop. Whether one was running."""
        with self._lock:
            running = self._analyses.get(project_id)
        if running is None:
            return False
        running.token.cancel()
        return True

    def apk_paths(self) -> set[Path]:
        """The uploads the running analyses are reading."""
        with self._lock:
            return {running.apk_path for running in self._analyses.values()}


#: The analyses this process is running.
RUNNING = RunningAnalyses()


def upload_retention_seconds() -> int:
    """How long an uploaded APK is kept.

    Read from the environment so that a deployment can choose its own
    window without a code change. A value that is not a number, or that is
    negative, falls back to the default: a retention policy that cannot be
    read is not one that should be guessed at.
    """
    raw = os.environ.get(UPLOAD_RETENTION_ENV)
    if raw is None:
        return UPLOAD_RETENTION_SECONDS
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s is not a number; using the default retention", UPLOAD_RETENTION_ENV)
        return UPLOAD_RETENTION_SECONDS
    if value < 0:
        logger.warning("%s is negative; using the default retention", UPLOAD_RETENTION_ENV)
        return UPLOAD_RETENTION_SECONDS
    return value


def stored_uploads(settings: Settings) -> list[Path]:
    """The uploads that are stored, one per file, in their hash-named directory.

    The staging files -- the ones a request is still writing -- live in the
    upload root itself rather than in a hash-named directory, so they are
    not uploads and are not listed.
    """
    root = settings.workspace / UPLOAD_DIRNAME
    if not root.is_dir():
        return []
    found: list[Path] = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file():
                found.append(path)
    return found


def expire_uploads(settings: Settings, *, now: float | None = None) -> list[Path]:
    """Remove the uploads the retention window has passed, and say which.

    The uploads of the analyses that are running are never removed: the
    analysis reads the file it was given, and a file that disappears under
    it is a failure of the analysis rather than of the cleanup.
    """
    root = settings.workspace / UPLOAD_DIRNAME
    if not root.is_dir():
        return []
    window = upload_retention_seconds()
    moment = time.time() if now is None else now
    in_use = RUNNING.apk_paths()
    removed: list[Path] = []
    for path in stored_uploads(settings):
        if path in in_use:
            continue
        try:
            age = moment - path.stat().st_mtime
        except OSError:
            continue
        if age < window:
            continue
        try:
            path.unlink()
        except OSError:
            logger.warning("could not remove the expired upload %s", path.name)
            continue
        removed.append(path)
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        # Not empty: something else lives there, and it is not the sweep's
        # to remove.
        with suppress(OSError):
            directory.rmdir()
    return removed


def touch_upload(path: Path) -> None:
    """Mark a file as used now, so that the retention window starts again."""
    try:
        os.utime(path, None)
    except OSError:
        logger.warning("could not mark the upload %s as used", path.name)


def safe_hash(sha256: str) -> str:
    """A hash that can be used as a directory name.

    The hash comes from a request, and a request is not trusted to name a
    directory: a name that is not a SHA-256 cannot be one, whatever else it
    might be.
    """
    cleaned = sha256.strip().lower()
    if len(cleaned) != 64 or any(char not in "0123456789abcdef" for char in cleaned):
        raise ValueError(f"{sha256!r} is not a SHA-256")
    return cleaned


def stage_upload(
    file: UploadFile,
    settings: Settings,
    *,
    inspector: Callable[[Path], ApkMetadata] = inspect_apk,
) -> tuple[ApkMetadata, Path, str]:
    """Validate and store an uploaded APK; the policy every transport shares.

    The file is streamed to a staging name of the server's choosing, so two
    uploads that carry the same client-supplied name cannot overwrite one
    another; it is inspected -- which refuses an archive that is not an APK
    or one that expands like a bomb -- and only then moved into
    ``uploads/<sha256>/<client-filename>``, where two uploads share a path
    only when they are the same bytes. The sweep runs on the way in, so a
    deployment that receives uploads and analyses none still expires them.

    ``inspector`` is the archive check, injectable so a transport that wraps
    it can keep the wrap: the REST API passes its own name for the check so
    a test that counts calls there counts the calls the policy makes. The
    workbench passes nothing and gets the shared check.

    Returns the inspected metadata, the stored path and the client's name.
    Every failure is an ``HTTPException``: a validation problem is the
    caller's (413 for a size the policy refuses, 422 for a file that is not
    an APK), and only a failure to write is the server's own (500).
    """
    upload_root = settings.workspace / UPLOAD_DIRNAME
    upload_root.mkdir(parents=True, exist_ok=True)
    expire_uploads(settings)
    name = stored_name(file.filename)
    staged = upload_root / f".incoming-{uuid4().hex}"

    try:
        save_upload(file.file, staged)
    except UploadTooLarge as exc:
        # Refused while it streamed: the bytes over the limit were never
        # written, and the partial file has already been removed.
        raise HTTPException(
            status_code=HTTP_CONTENT_TOO_LARGE,
            detail=f"the APK is larger than the {exc.limit}-byte limit",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"could not store the upload: {exc}",
        ) from exc

    try:
        apk = inspector(staged)
    except ApkValidationError as exc:
        staged.unlink(missing_ok=True)
        # The validator names the absolute path; a remote caller has no business
        # learning the server's filesystem layout. What it is told instead is
        # the name it gave the file -- which is the name it has to recognise.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc).replace(str(staged), name),
        ) from exc

    # The bytes are known and valid, so the file can go where it belongs: in a
    # directory named after its own hash. Two uploads can then share a path
    # only when they are the same bytes, and a project can only ever hold the
    # classes of the file that was hashed into its name.
    #
    # The name the client gave is kept as the name of the file inside, because
    # that is the name a reader of the report wants to see.
    stored_dir = upload_root / apk.sha256
    stored_dir.mkdir(parents=True, exist_ok=True)
    target = stored_dir / name
    staged.replace(target)
    apk.path = target
    return apk, target, name


def run_background_analysis(analyzer: Analyzer, apk_path: Path, apk: ApkMetadata) -> None:
    """Analyse an APK in the background.

    Three things can happen, and the log has to tell them apart: the
    analysis can fail, it can be cancelled, or it can finish and find
    nothing. The first two are errors and the third is an answer, and a log
    that says "failed" for all three sends the reader looking for a fault
    that is not there.
    """
    from dexatlas.core.models import Project
    from dexatlas.core.runs import AnalysisCancelled

    project_id = Project.new_id(apk.sha256)
    token = RUNNING.start(project_id, apk_path)
    try:
        result = analyzer.analyze(apk_path, metadata=apk, cancellation=token)
    except AnalysisCancelled:
        # The operator asked for it to stop. That is not a failure of the
        # analysis, and the log should not say it is.
        logger.info("background analysis of %s was cancelled", apk_path)
        return
    except Exception:
        # The pipeline records the failure on the project before it raises, so
        # the project is failed rather than running, and its errors say what
        # happened. The log says the same thing.
        logger.exception("background analysis of %s failed", apk_path)
        return
    finally:
        RUNNING.finish(project_id)
        # The retention window is counted from the end of the analysis that
        # used the upload, so the clock starts again now.
        touch_upload(apk_path)
        # The sweep runs here as well as when the server starts, so a
        # deployment that is never restarted still expires its uploads.
        expire_uploads(analyzer.settings)
    if not result.succeeded:
        logger.warning("background analysis of %s completed but produced no symbols", apk_path)
