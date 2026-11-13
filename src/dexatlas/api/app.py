"""FastAPI application.

Thin transport over :class:`~dexatlas.core.pipeline.Analyzer` — the same object the CLI
uses. The *analysis* is not defined here: the pipeline produces the manifest, the
symbols and the evidence, and both interfaces read the same result out of it.

The transport does have a decision of its own. An upload of an APK that has
already been analysed is answered with the project that holds the result
rather than being analysed again, while the CLI re-analyses every APK it is
given. That is a policy about the work an upload causes, not a difference in
what an analysis produces — but it is a difference between the two, and a
reader of this module should not have to find it in the code.

Analysis is synchronous and CPU-bound, so ``/analyze`` is exposed as a background task
that returns a job id. Phase 3 introduces a proper queue; until then a single-process
background task is honest about what it is rather than pretending to scale.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Any

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

from dexatlas import __version__
from dexatlas.api.uploads import (
    DEFAULT_UPLOAD_NAME,
    MAX_NAME_BYTES,
    RUNNING,
    UPLOAD_DIRNAME,
    UPLOAD_RETENTION_ENV,
    UPLOAD_RETENTION_SECONDS,
    UploadSizeLimitMiddleware,
    expire_uploads,
    run_background_analysis,
    safe_hash,
    stage_upload,
    stored_uploads,
    upload_retention_seconds,
)
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core import ingest
from dexatlas.core.ingest import inspect_apk
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
from dexatlas.core.runs import AnalysisRun
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown
from dexatlas.tools.registry import BackendRegistry

logger = logging.getLogger(__name__)

# The upload policy's names stay importable from this module under their
# historical spellings: this API published them, the deployment policy and
# the tests that pin it read them here, and the definitions live in the
# module the two transports share so they cannot drift.
UPLOAD_DIRNAME = UPLOAD_DIRNAME
DEFAULT_UPLOAD_NAME = DEFAULT_UPLOAD_NAME
MAX_NAME_BYTES = MAX_NAME_BYTES
UPLOAD_RETENTION_SECONDS = UPLOAD_RETENTION_SECONDS
UPLOAD_RETENTION_ENV = UPLOAD_RETENTION_ENV
_EXPIRE = expire_uploads
_RETENTION = upload_retention_seconds
_RUNNING = RUNNING


def _expire_uploads(settings: Settings, *, now: float | None = None) -> list[Path]:
    """Remove expired uploads -- the shared sweep, under its old name."""
    return expire_uploads(settings, now=now)


def _upload_retention_seconds() -> int:
    """How long an uploaded APK is kept -- the shared policy's window."""
    return upload_retention_seconds()


def _run_analysis(analyzer: Analyzer, apk_path: Path, apk: ApkMetadata) -> None:
    """Analyse an APK in the background -- the shared policy, by its old name."""
    run_background_analysis(analyzer, apk_path, apk)


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Expire the uploads the retention window has passed, when the server starts.

    A server that was down kept its uploads and nobody was there to expire
    them. The sweep runs before the first request is served rather than
    after it, so the workspace is already in the state the policy says it
    should be in.
    """
    removed = expire_uploads(get_settings())
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
    """How many call *sites* the index holds: one per place in the bytecode
    where a call happens."""

    call_site_count: int
    """How many call *sites* the index holds.

    The same number as ``reference_count``, under the name the reports and
    the MCP tools use. A reader who has seen one of them should not have to
    guess whether the other means the same thing.
    """

    call_edge_count: int
    """How many call *edges* the index holds: one per relationship between
    two methods, aggregated over the call sites that make it."""

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
    # The staging, the naming, the inspection and the hash-addressed store are
    # the shared upload policy; this transport only decides what an accepted
    # upload causes (a background analysis) and what the caller is told. The
    # inspector is passed by name from this module so a test that counts calls
    # to ``inspect_apk`` here counts the calls the policy makes.
    apk, target, _name = stage_upload(file, settings, inspector=inspect_apk)

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
    background.add_task(run_background_analysis, analyzer, target, apk)
    return AnalyzeJobResponse(
        project_id=f"apk_{apk.sha256[:16]}",
        status="pending",
        detail=f"/projects/{Project.new_id(apk.sha256)}",
    )


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
    if not RUNNING.cancel(project_id):
        raise HTTPException(status_code=404, detail=f"no analysis is running for {project_id!r}")
    return {"project_id": project_id, "status": "cancelling"}


@app.get("/uploads", tags=["uploads"])
def list_uploads(settings: SettingsDep) -> list[UploadResponse]:
    """The stored uploads, and how long they are kept.

    The retention window is a policy of the deployment rather than of the
    analysis: an uploaded APK is kept for a while after the analysis that
    used it, and the sweep removes it when the window has passed.
    """
    window = upload_retention_seconds()
    moment = time.time()
    uploads: list[UploadResponse] = []
    for path in stored_uploads(settings):
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
    removed = expire_uploads(settings)
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
    # Two numbers, because the two are different: a caller that calls the same
    # method twice is two call sites and one call edge. The response says
    # which is which rather than leaving the reader to guess from a number
    # called "total".
    edges = len({(r.caller, r.kind) for r in references})
    return {
        "project_id": project_id,
        # The canonical spelling, not whatever the caller typed. A response that
        # echoes the request is less useful than one that can be pasted into the
        # next call, and the two spellings differ in exactly the way that matters.
        "method_id": canonical_method_id(method_id),
        "call_sites": len(references),
        "call_edges": edges,
        "total": len(references),
        # The unit of `total`, spelled out. Its value did not change — it was
        # the number of indexed rows before and it is the number of call
        # sites now — but a row is a place now, and a reader who only sees
        # "total: 4" would still take it for four relationships.
        "total_unit": "call_sites",
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
    might be. The validation is the shared policy's; this transport turns a
    rejection into the 400 its callers know.
    """
    try:
        return safe_hash(sha256)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{sha256!r} is not a SHA-256 hash") from exc


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
        call_site_count=project.reference_count,
        call_edge_count=project.call_edge_count,
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
