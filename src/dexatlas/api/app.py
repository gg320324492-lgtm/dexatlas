"""FastAPI application.

Thin transport over :class:`~dexatlas.core.pipeline.Analyzer` — the same object the CLI
uses. No analysis behaviour is defined here, so the two interfaces cannot diverge.

Analysis is synchronous and CPU-bound, so ``/analyze`` is exposed as a background task
that returns a job id. Phase 3 introduces a proper queue; until then a single-process
background task is honest about what it is rather than pretending to scale.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from dexatlas import __version__
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core import ingest
from dexatlas.core.ingest import ApkValidationError, UploadTooLarge, inspect_apk, save_upload
from dexatlas.core.methods import AmbiguousMethodError, is_descriptor
from dexatlas.core.models import (
    ApkMetadata,
    Project,
    ProjectStatus,
    SourceDocument,
    canonical_method_id,
)
from dexatlas.core.paths import display_path, redact_workspace
from dexatlas.core.pipeline import AnalysisResult, Analyzer
from dexatlas.core.runs import AnalysisCancelled, AnalysisRun, CancellationToken
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown
from dexatlas.tools.registry import BackendRegistry

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


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_analyzer(settings: SettingsDep) -> Analyzer:
    """FastAPI dependency.

    ``settings`` is injected rather than resolved inside :class:`Analyzer`, so that
    overriding the settings dependency redirects the whole analysis stack. Otherwise
    the analyzer would keep reading process-wide settings and write outside the
    intended workspace.
    """
    return Analyzer(settings)


AnalyzerDep = Annotated[Analyzer, Depends(get_analyzer)]


def get_backends(settings: SettingsDep) -> BackendRegistry:
    """FastAPI dependency for the analysis backends.

    The backends are built from the settings alone. An :class:`Analyzer` would
    answer the same question, but building one opens the workspace database —
    and a liveness probe that opens the database takes the write lock SQLite
    allows only one of, so a probe can lock the analysis out of its own
    workspace and be locked out itself. Which backends are installed is a fact
    about the machine, not about the database, so the dependency does not open
    one.
    """
    return BackendRegistry(settings)


BackendRegistryDep = Annotated[BackendRegistry, Depends(get_backends)]


@dataclass
class _RunningAnalysis:
    """One analysis that is running, and the way to stop it."""

    token: CancellationToken
    apk_path: Path


class _RunningAnalyses:
    """The analyses that are running.

    The analysis runs in a background task, so "stop it" cannot be a call
    into it: it has to be a fact the running code can observe. The token is
    that fact -- the request sets it, and the analysis stops at the next
    point where stopping cannot leave half-written results behind.

    The registry is keyed by the project id, which is the handle the API
    already gave the caller when it accepted the upload.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._analyses: dict[str, _RunningAnalysis] = {}

    def start(self, project_id: str, apk_path: Path) -> CancellationToken:
        """Register an analysis that is starting, and hand back its token."""
        token = CancellationToken()
        with self._lock:
            self._analyses[project_id] = _RunningAnalysis(token=token, apk_path=apk_path)
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
_RUNNING = _RunningAnalyses()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Expire the uploads the retention window has passed, when the server starts.

    A server that was down kept its uploads and nobody was there to expire
    them. The sweep runs before the first request is served rather than
    after it, so the workspace is already in the state the policy says it
    should be in.
    """
    removed = _expire_uploads(get_settings())
    if removed:
        logger.info("removed %d expired upload(s)", len(removed))
    yield


app = FastAPI(
    title="DexAtlas",
    version=__version__,
    description=(
        "Evidence-first Android reverse engineering and analysis platform. "
        "Analyses applications you own or are authorized to assess."
    ),
    license_info={"name": "Apache-2.0"},
    lifespan=lifespan,
)


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


app.add_middleware(UploadSizeLimitMiddleware, limit=lambda: ingest.MAX_APK_BYTES)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    backends: dict[str, str | None]


class ErrorResponse(BaseModel):
    tool: str
    code: str
    message: str
    detail: str | None = None


class ProjectResponse(BaseModel):
    id: str
    status: str
    apk_sha256: str
    apk_path: str = Field(
        description=(
            "The analysed APK's file name. The server's directory layout is not "
            "published; the file itself is identified exactly by `apk_sha256`."
        )
    )
    apk_size_bytes: int
    class_count: int
    method_count: int
    reference_count: int
    evidence_count: int
    resource_count: int
    tool_versions: dict[str, str | None]
    errors: list[ErrorResponse]


class AnalyzeJobResponse(BaseModel):
    project_id: str
    status: str
    detail: str = Field(description="Where to poll for the finished analysis.")


class SubmitResponse(BaseModel):
    project_id: str
    sha256: str
    already_analysed: bool


class RunResponse(BaseModel):
    """One analysis run of a project."""

    id: str
    """The run's own identifier, which says nothing about the APK."""

    project_id: str
    status: str
    completeness: str = Field(
        description=(
            "Whether the run read everything it set out to read. A run with "
            "gaps in it is 'partial', and the gaps are in its errors."
        )
    )
    apk_sha256: str
    tool_versions: dict[str, str | None]
    errors: list[ErrorResponse]
    started_at: str
    finished_at: str | None
    duration_seconds: float | None
    published: bool = Field(
        description="Whether this run's results are the ones the project publishes."
    )


class UploadResponse(BaseModel):
    """One stored upload."""

    sha256: str
    name: str
    size_bytes: int
    age_seconds: float = Field(description="How long ago the upload was last used.")
    expires_in_seconds: float | None = Field(
        description="How long the upload is kept for, or nothing when the window has passed."
    )


#: The headers a source response carries, declared so the schema says what the
#: response actually is. A client that generates from this schema can then read
#: the kind of source it got without parsing the body.
_SOURCE_HEADERS: dict[str, dict[str, Any]] = {
    "X-DexAtlas-Source-Kind": {
        "description": "Which representation the body holds.",
        "schema": {"type": "string", "enum": ["java", "smali"]},
    },
    "X-DexAtlas-Source-Tool": {
        "description": "The backend that produced the source.",
        "schema": {"type": "string"},
    },
    "X-DexAtlas-Source-Locator": {
        "description": "Where the source lives inside the producing tool's output tree.",
        "schema": {"type": "string"},
    },
    "X-DexAtlas-Source-Tool-Version": {
        "description": "The version of the producing tool that the analysis recorded.",
        "schema": {"type": "string"},
    },
}

#: The JSON form of a source, declared to match what is actually returned.
_SOURCE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string"},
        "class_name": {"type": "string"},
        "method": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "descriptor": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "kind": {"type": "string", "enum": ["java", "smali"]},
        "provenance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "tool_version": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "apk_sha256": {"type": "string"},
                    "locator": {"type": "string"},
                },
                "required": ["tool", "apk_sha256", "locator"],
            },
        },
        "text": {"type": "string"},
    },
    "required": ["project_id", "class_name", "kind", "provenance", "text"],
}

#: What the source endpoints can answer with. The default is the source text
#: and nothing else, so the body is exactly the file a caller piped it into;
#: the JSON form carries the whole provenance in the document.
_SOURCE_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "The source, as text or — with `?format=json` — as a JSON document.",
        "headers": _SOURCE_HEADERS,
        "content": {
            "text/plain": {"schema": {"type": "string"}},
            "application/json": {"schema": _SOURCE_JSON_SCHEMA},
        },
    },
    404: {
        "description": "No such class, or no source for it.",
        "content": {"application/json": {"schema": {"type": "object"}}},
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(backends: BackendRegistryDep) -> HealthResponse:
    """Liveness plus which backends this deployment can actually use."""
    return HealthResponse(
        status="ok",
        version=__version__,
        backends={b.name: b.version() if b.available() else None for b in backends.all()},
    )


@app.get("/backends", tags=["meta"])
def list_backends(backends: BackendRegistryDep) -> dict[str, Any]:
    """Which analysis backends are installed, and at what version."""
    return {
        "available": [b.name for b in backends.available()],
        "missing": [b.name for b in backends.missing()],
        "versions": backends.versions(),
    }


@app.post(
    "/analyze",
    response_model=AnalyzeJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analysis"],
)
def analyze(
    background: BackgroundTasks,
    analyzer: AnalyzerDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="An APK you are authorized to analyse.")],
) -> AnalyzeJobResponse:
    """Accept an APK and analyse it in the background."""
    upload_root = settings.workspace / UPLOAD_DIRNAME
    upload_root.mkdir(parents=True, exist_ok=True)
    # The sweep runs on the way in as well: a deployment that receives
    # uploads but analyses none of them would otherwise never expire any.
    _expire_uploads(settings)
    # The name the client gave, kept for the reader: it is what the report
    # shows and what a rejection names.
    name = _stored_name(file.filename)
    # The upload is staged under a name of this server's choosing. The name the
    # client gave is not used for the path: two uploads that happen to carry
    # the same name must not be able to write over one another, because the
    # analysis of the first one reads the path the second one would replace.
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
        apk = inspect_apk(staged)
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

    existing = analyzer.store.find_project_by_hash(apk.sha256)
    if existing is not None and existing.status is not ProjectStatus.FAILED:
        return AnalyzeJobResponse(
            project_id=existing.id,
            status=existing.status.value,
            detail=f"/projects/{existing.id}",
        )
    # A project that failed is analysed again. The failure was recorded, with
    # its reason, and sending the same APK is how the operator asks for
    # another go; answering with the failed project instead would make the
    # failure permanent — the project id is the APK's hash, so the upload
    # would find it and return it for ever.

    # The APK has already been inspected, so the analysis is handed the
    # metadata rather than inspecting it a second time.
    background.add_task(_run_analysis, analyzer, target, apk)
    return AnalyzeJobResponse(
        project_id=f"apk_{apk.sha256[:16]}",
        status="pending",
        detail=f"/projects/{Project.new_id(apk.sha256)}",
    )


def _run_analysis(analyzer: Analyzer, apk_path: Path, apk: ApkMetadata) -> None:
    """Analyse an APK in the background.

    Three things can happen, and the log has to tell them apart: the
    analysis can fail, it can be cancelled, or it can finish and find
    nothing. The first two are errors and the third is an answer, and a log
    that says "failed" for all three sends the reader looking for a fault
    that is not there.
    """
    project_id = Project.new_id(apk.sha256)
    token = _RUNNING.start(project_id, apk_path)
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
        _RUNNING.finish(project_id)
        # The retention window is counted from the end of the analysis that
        # used the upload, so the clock starts again now.
        _touch(apk_path)
        # The sweep runs here as well as when the server starts, so a
        # deployment that is never restarted still expires its uploads.
        _expire_uploads(analyzer.settings)
    if not result.succeeded:
        logger.warning("background analysis of %s completed but produced no symbols", apk_path)


@app.get("/projects", tags=["analysis"])
def list_projects(analyzer: AnalyzerDep, settings: SettingsDep) -> list[ProjectResponse]:
    """Every analysed project, newest first."""
    return [_project_response(p, settings) for p in analyzer.store.list_projects()]


@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["analysis"])
def get_project(project_id: str, analyzer: AnalyzerDep, settings: SettingsDep) -> ProjectResponse:
    """One project's metadata, counts and any backend errors."""
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"no project {project_id!r}")
    return _project_response(project, settings)


@app.get("/projects/{project_id}/runs", tags=["analysis"])
def list_runs(project_id: str, analyzer: AnalyzerDep, settings: SettingsDep) -> dict[str, Any]:
    """Every run of a project, newest first.

    A project is the APK; a run is one attempt at analysing it. The run
    that is *published* is the one whose results the project holds -- the
    one a reader of the index is looking at.
    """
    with analyzer.store.reading() as view:
        runs = view.list_runs(project_id)
        published = view.get_published_run_id(project_id)
    return {
        "project_id": project_id,
        "total": len(runs),
        "published_run_id": published,
        "runs": [
            _run_response(run, run.id == published, settings).model_dump(mode="json")
            for run in runs
        ],
    }


@app.get("/projects/{project_id}/runs/{run_id}", tags=["analysis"])
def get_run(
    project_id: str, run_id: str, analyzer: AnalyzerDep, settings: SettingsDep
) -> RunResponse:
    """One run of a project."""
    with analyzer.store.reading() as view:
        run = view.get_run(run_id)
        published = view.get_published_run_id(project_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail=f"no run {run_id!r} for {project_id!r}")
    return _run_response(run, run.id == published, settings)


@app.post(
    "/projects/{project_id}/cancel",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analysis"],
)
def cancel_analysis(project_id: str) -> dict[str, Any]:
    """Ask the analysis that is running for a project to stop.

    The analysis stops at the next point where stopping cannot leave
    half-written results behind: it has published nothing at that point,
    so the snapshot published before it stays exactly as it was.

    The answer is that the request was accepted, not that the analysis has
    stopped. A backend that is half way through reading the APK finishes
    reading it first -- the stop happens between the steps.
    """
    if not _RUNNING.cancel(project_id):
        raise HTTPException(status_code=404, detail=f"no analysis is running for {project_id!r}")
    return {"project_id": project_id, "status": "cancelling"}


@app.get("/uploads", tags=["uploads"])
def list_uploads(settings: SettingsDep) -> list[UploadResponse]:
    """The stored uploads, and how long they are kept.

    The retention window is a policy of the deployment rather than of the
    analysis: an uploaded APK is kept for a while after the analysis that
    used it, and the sweep removes it when the window has passed.
    """
    window = _upload_retention_seconds()
    moment = time.time()
    uploads: list[UploadResponse] = []
    for path in _stored_uploads(settings):
        try:
            stat = path.stat()
        except OSError:
            continue
        age = moment - stat.st_mtime
        uploads.append(
            UploadResponse(
                sha256=path.parent.name,
                name=path.name,
                size_bytes=stat.st_size,
                age_seconds=round(age, 3),
                expires_in_seconds=round(max(window - age, 0.0), 3),
            )
        )
    return uploads


@app.delete("/uploads/{sha256}", status_code=status.HTTP_204_NO_CONTENT, tags=["uploads"])
def delete_upload(sha256: str, settings: SettingsDep) -> None:
    """Remove a stored upload now.

    The bytes the analysis read go with it. The project's own record of
    the APK -- its hash, its size and its name -- does not, and the
    analysis can be repeated from the bytes the client still holds.
    """
    directory = settings.workspace / UPLOAD_DIRNAME / _safe_hash(sha256)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail=f"no upload {sha256!r}")
    removed = False
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        try:
            path.unlink()
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"could not remove the upload: {exc}",
            ) from exc
        removed = True
    if not removed:
        raise HTTPException(status_code=404, detail=f"no upload {sha256!r}")
    # The directory is not empty -- something else was put in it, and it is
    # not this endpoint's to remove.
    with suppress(OSError):
        directory.rmdir()


@app.post("/uploads/cleanup", tags=["uploads"])
def cleanup_uploads(settings: SettingsDep) -> dict[str, Any]:
    """Remove the uploads the retention window has passed.

    The sweep also runs when the server starts and after every analysis.
    This endpoint runs it now, for an operator who wants the workspace
    back to what the policy says it should be without waiting for one.
    """
    removed = _expire_uploads(settings)
    return {"removed": len(removed), "names": sorted(path.name for path in removed)}


@app.get("/projects/{project_id}/manifest", tags=["analysis"])
def get_manifest(project_id: str, analyzer: AnalyzerDep) -> dict[str, Any]:
    """The parsed AndroidManifest.xml."""
    manifest = analyzer.store.get_manifest(project_id)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=f"no manifest for {project_id!r}; the Apktool backend may be unavailable",
        )
    return manifest.model_dump(mode="json")


@app.get("/projects/{project_id}/classes", tags=["analysis"])
def list_classes(
    project_id: str,
    analyzer: AnalyzerDep,
    prefix: Annotated[str | None, Query(description="Filter by package prefix.")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> dict[str, Any]:
    """The project's indexed classes."""
    classes = analyzer.store.list_classes(project_id, prefix=prefix)
    return {
        "project_id": project_id,
        "total": len(classes),
        "classes": [c.model_dump(mode="json") for c in classes[:limit]],
    }


@app.get("/projects/{project_id}/methods", tags=["analysis"])
def list_methods(
    project_id: str,
    analyzer: AnalyzerDep,
    class_name: Annotated[str | None, Query(alias="class")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> dict[str, Any]:
    """The project's indexed methods."""
    methods = analyzer.store.list_methods(project_id, class_name)
    return {
        "project_id": project_id,
        "total": len(methods),
        "methods": [m.model_dump(mode="json") for m in methods[:limit]],
    }


@app.get("/projects/{project_id}/resources", tags=["analysis"])
def list_resources(
    project_id: str,
    analyzer: AnalyzerDep,
    name: Annotated[str | None, Query(description="Show one resource, by its exact name.")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> dict[str, Any]:
    """The resource strings the APK's resource table declares.

    Each row names the file it was declared in and carries the provenance of
    that file, so a value found here can be traced back to its declaration.
    """
    resources = analyzer.resources(project_id, name=name)
    return {
        "project_id": project_id,
        "total": len(resources),
        "resources": [r.model_dump(mode="json") for r in resources[:limit]],
    }


@app.get(
    "/projects/{project_id}/classes/{class_name:path}/source",
    tags=["analysis"],
    responses=_SOURCE_RESPONSES,
)
def get_class_source(
    project_id: str,
    class_name: str,
    analyzer: AnalyzerDep,
    format: Annotated[
        str, Query(pattern="^(text|json)$", description="The source text, or a JSON document.")
    ] = "text",
) -> Any:
    """A class as decompiled Java, falling back to Smali when JADX could not.

    The response says which of the two it is. The plain-text form carries it in
    the ``X-DexAtlas-Source-*`` headers, so the body stays exactly the source;
    the JSON form carries the whole provenance in the document.
    """
    document = analyzer.class_source_document(project_id, class_name)
    if document is None:
        raise HTTPException(status_code=404, detail=f"no source for {class_name!r}")
    if format == "json":
        return _source_payload(project_id, class_name, None, document)
    return PlainTextResponse(document.text, headers=_source_headers(document))


#: The responses of the method source endpoint. It has one the class endpoint does
#: not: a name that matches several overloads is a conflict, not a missing source.
_METHOD_SOURCE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **_SOURCE_RESPONSES,
    409: {
        "description": "The name matches more than one method; a descriptor is needed.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                        "class_name": {"type": "string"},
                        "method": {"type": "string"},
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "descriptor": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                                    "signature": {"type": "string"},
                                },
                                "required": ["name", "signature"],
                            },
                        },
                    },
                    "required": ["detail", "class_name", "method", "candidates"],
                }
            }
        },
    },
}


@app.get(
    "/projects/{project_id}/methods/{class_name:path}/{method_name}",
    tags=["analysis"],
    responses=_METHOD_SOURCE_RESPONSES,
)
def get_method_source(
    project_id: str,
    class_name: str,
    method_name: str,
    analyzer: AnalyzerDep,
    format: Annotated[
        str, Query(pattern="^(text|json)$", description="The source text, or a JSON document.")
    ] = "text",
    descriptor: Annotated[
        str | None,
        Query(
            description="The method's DEX descriptor, e.g. '(Ljava/lang/String;)V'. "
            "Picks one overload out of several."
        ),
    ] = None,
) -> Any:
    """One method's body, preferring decompiled Java and falling back to Smali.

    As with the class source, the response says which representation it is.

    A name that matches more than one overload is answered with ``409`` and the
    candidates, not with one of them: the body of the wrong overload reads like
    evidence, and a caller that quotes it quotes the wrong method. The
    ``descriptor`` query parameter says which overload is meant.
    """
    if descriptor is not None and not is_descriptor(descriptor):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{descriptor!r} is not a DEX descriptor; one looks like '(Ljava/lang/String;)V'"
            ),
        )
    try:
        document = analyzer.method_source_document(project_id, class_name, method_name, descriptor)
    except AmbiguousMethodError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
                "class_name": exc.class_name,
                "method": exc.method_name,
                "candidates": [candidate.model_dump(mode="json") for candidate in exc.candidates],
            },
        )
    if document is None:
        raise HTTPException(
            status_code=404, detail=f"no decompiled source for {class_name}.{method_name}"
        )
    if format == "json":
        return _source_payload(project_id, class_name, method_name, document)
    return PlainTextResponse(document.text, headers=_source_headers(document))


@app.get("/projects/{project_id}/xrefs/{method_id:path}", tags=["analysis"])
def get_references(project_id: str, method_id: str, analyzer: AnalyzerDep) -> dict[str, Any]:
    """Callers of a method, addressed as ``com.example.Foo.bar(Ljava/lang/String;)V``."""
    references = analyzer.store.get_method_references(project_id, method_id)
    return {
        "project_id": project_id,
        # The canonical spelling, not whatever the caller typed. A response that
        # echoes the request is less useful than one that can be pasted into the
        # next call, and the two spellings differ in exactly the way that matters.
        "method_id": canonical_method_id(method_id),
        "total": len(references),
        "references": [r.model_dump(mode="json") for r in references],
    }


@app.get("/projects/{project_id}/search", tags=["analysis"])
def search_code(
    project_id: str,
    analyzer: AnalyzerDep,
    q: Annotated[str, Query(min_length=1, description="Term to search for.")],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    """Full-text search across the project's indexed symbols."""
    return {"project_id": project_id, "query": q, "results": analyzer.search(project_id, q, limit)}


@app.get("/projects/{project_id}/evidence", tags=["analysis"])
def list_evidence(project_id: str, analyzer: AnalyzerDep) -> dict[str, Any]:
    """Every evidence record, each with its source tool, version and locator."""
    evidence = analyzer.store.list_evidence(project_id)
    return {
        "project_id": project_id,
        "total": len(evidence),
        "evidence": [e.model_dump(mode="json") for e in evidence],
    }


@app.get("/projects/{project_id}/report", tags=["reports"])
def export_report(
    project_id: str,
    analyzer: AnalyzerDep,
    format: Annotated[str, Query(pattern="^(json|markdown)$")] = "json",
) -> Any:
    """Export the analysis as JSON or Markdown."""
    result = _rebuild_result(analyzer, project_id)
    if format == "markdown":
        return PlainTextResponse(render_markdown(result), media_type="text/markdown")
    return build_json_report(result)


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["analysis"])
def delete_project(project_id: str, analyzer: AnalyzerDep, settings: SettingsDep) -> None:
    """Remove a project and its symbols."""
    if not analyzer.store.delete_project(project_id):
        raise HTTPException(status_code=404, detail=f"no project {project_id!r}")
    _remove_project_workspace(project_id, settings)


def _stored_name(filename: str | None) -> str:
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


def _redact(message: str, secret: str) -> str:
    """Replace a server-side path with its basename, for messages shown to a caller."""
    return message.replace(secret, Path(secret).name)


def _source_headers(document: SourceDocument) -> dict[str, str]:
    """Headers that say where a source came from.

    The body of the plain-text response is the source and nothing else — a
    caller that pipes it into a file should get the file and not a header — so
    the answer to "is this Java or Smali?" travels beside it. The JSON form
    carries the same information inside the document.
    """
    headers = {"X-DexAtlas-Source-Kind": document.kind.value}
    for source in document.provenance:
        headers["X-DexAtlas-Source-Tool"] = source.tool
        headers["X-DexAtlas-Source-Locator"] = source.locator
        if source.tool_version:
            headers["X-DexAtlas-Source-Tool-Version"] = source.tool_version
    return headers


def _source_payload(
    project_id: str,
    class_name: str,
    method: str | None,
    document: SourceDocument,
) -> dict[str, Any]:
    """The JSON form of a source: the text, and where it came from.

    The descriptor travels with it, because a document that says which method
    it holds is worth more than one that says only the name — and two
    overloads share the name. It is the descriptor the document holds, not the
    one that was asked for: a request that named only a method still says
    which of the overloads it got.
    """
    return {
        "project_id": project_id,
        "class_name": class_name,
        "method": method,
        "descriptor": document.descriptor,
        "kind": document.kind.value,
        "provenance": [p.model_dump(mode="json") for p in document.provenance],
        "text": document.text,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _upload_retention_seconds() -> int:
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


def _stored_uploads(settings: Settings) -> list[Path]:
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


def _expire_uploads(settings: Settings, *, now: float | None = None) -> list[Path]:
    """Remove the uploads the retention window has passed, and say which.

    The uploads of the analyses that are running are never removed: the
    analysis reads the file it was given, and a file that disappears under
    it is a failure of the analysis rather than of the cleanup.
    """
    root = settings.workspace / UPLOAD_DIRNAME
    if not root.is_dir():
        return []
    window = _upload_retention_seconds()
    moment = time.time() if now is None else now
    in_use = _RUNNING.apk_paths()
    removed: list[Path] = []
    for path in _stored_uploads(settings):
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


def _touch(path: Path) -> None:
    """Mark a file as used now, so that the retention window starts again."""
    try:
        os.utime(path, None)
    except OSError:
        logger.warning("could not mark the upload %s as used", path.name)


def _remove_project_workspace(project_id: str, settings: Settings) -> None:
    """Remove the directories a deleted project's runs wrote into.

    Every run writes into a directory of its own, so a deleted project
    leaves a directory per run behind it. The workspace belongs to the
    server, and the analysis of a project nobody holds any more is not
    something to keep for ever.

    A file that cannot be removed -- because a reader still has it open --
    is logged rather than raised: the project is gone from the database
    either way, and what is left is a file in the server's own directory.
    """
    root = settings.projects_dir / project_id
    if not root.is_dir():
        return
    paths = sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True)
    for path in paths:
        try:
            if path.is_symlink() or not path.is_dir():
                path.unlink()
            else:
                path.rmdir()
        except OSError:
            logger.warning("could not remove %s", path.name)
    try:
        root.rmdir()
    except OSError:
        logger.warning("could not remove the workspace of %s", project_id)


def _safe_hash(sha256: str) -> str:
    """A hash that can be used as a directory name, or nothing.

    The hash comes from the request, and a request is not trusted to name a
    directory: a name that is not a SHA-256 cannot be one, whatever else it
    might be.
    """
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise HTTPException(status_code=400, detail=f"{sha256!r} is not a SHA-256 hash")
    return sha256


def _run_response(run: AnalysisRun, published: bool, settings: Settings) -> RunResponse:
    """One run, as the API publishes it.

    The errors are redacted for the same reason the project's are: an
    error's message can quote the path it was handed, and that path is the
    server's.
    """
    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        status=run.status.value,
        completeness=run.completeness.value,
        apk_sha256=run.apk_sha256,
        tool_versions=run.tool_versions,
        errors=[
            ErrorResponse(
                tool=error.tool,
                code=error.code.value,
                message=redact_workspace(error.message, settings.workspace),
                detail=(
                    redact_workspace(error.detail, settings.workspace) if error.detail else None
                ),
            )
            for error in run.errors
        ],
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        duration_seconds=run.duration_seconds,
        published=published,
    )


def _project_response(project: Any, settings: Settings) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        status=project.status.value,
        apk_sha256=project.apk.sha256,
        # The name of the analysed file, not the path to it. The path is the
        # server's filesystem, and this response is published.
        apk_path=display_path(project.apk.path),
        apk_size_bytes=project.apk.size_bytes,
        class_count=project.class_count,
        method_count=project.method_count,
        reference_count=project.reference_count,
        evidence_count=project.evidence_count,
        resource_count=project.resource_count,
        tool_versions=project.tool_versions,
        errors=[
            ErrorResponse(
                tool=error.tool,
                code=error.code.value,
                # Both fields are redacted: an error's message can quote the
                # path it was handed just as easily as its detail can.
                message=redact_workspace(error.message, settings.workspace),
                detail=(
                    redact_workspace(error.detail, settings.workspace) if error.detail else None
                ),
            )
            for error in project.errors
        ],
    )


def _rebuild_result(analyzer: Analyzer, project_id: str) -> AnalysisResult:
    """Reconstruct an :class:`AnalysisResult` from the published snapshot.

    Everything the reports state has to come out of the workspace, including
    how long the analysis took: a report exported over the API that says
    "0.0s" for an analysis that took three seconds states a number the
    analysis never produced.

    The report describes *one* run -- the published one. The project's own
    status says how the latest attempt ended, which is a different thing: a
    re-analysis that failed leaves the published snapshot exactly as it
    was, and the report still has to describe that snapshot rather than the
    failure that came after it.
    """
    with analyzer.store.reading() as view:
        project = view.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"no project {project_id!r}")
        run = view.get_published_run(project_id)
        manifest = view.get_manifest(project_id)
        evidence = view.list_evidence(project_id)
        workspace = view.get_workspace(project_id)

    if run is not None:
        # The project's own row says how the *latest* attempt ended; the
        # published run says how the attempt this report describes ended.
        # They are the same thing until somebody re-analyses the APK, and
        # then they are not -- and a report that said "completed" without
        # saying so would be stating the status of the snapshot as if it
        # were the status of the project.
        published_status = _project_status_of(run)
        latest_attempt_status = project.status if project.status is not published_status else None
        project = project.model_copy(
            update={
                "status": published_status,
                "errors": list(run.errors),
            }
        )
    else:
        latest_attempt_status = None
    return AnalysisResult(
        project=project,
        manifest=manifest,
        evidence=evidence,
        workspace=workspace,
        duration_seconds=project.duration_seconds or 0.0,
        run=run,
        latest_attempt_status=latest_attempt_status,
    )


def _project_status_of(run: AnalysisRun) -> ProjectStatus:
    """The status a published run's project carries.

    A run that was cancelled is never published -- it published nothing --
    so the only statuses that reach here are the ones the project already
    has. The mapping is written out rather than assumed so that a run
    status added later cannot raise in the middle of an export.
    """
    if run.status.value in {status.value for status in ProjectStatus}:
        return ProjectStatus(run.status.value)
    return ProjectStatus.FAILED


__all__ = ["app"]
