"""FastAPI application.

Thin transport over :class:`~dexatlas.core.pipeline.Analyzer` — the same object the CLI
uses. No analysis behaviour is defined here, so the two interfaces cannot diverge.

Analysis is synchronous and CPU-bound, so ``/analyze`` is exposed as a background task
that returns a job id. Phase 3 introduces a proper queue; until then a single-process
background task is honest about what it is rather than pretending to scale.
"""

from __future__ import annotations

import logging
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
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from dexatlas import __version__
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.ingest import ApkValidationError, inspect_apk
from dexatlas.core.models import Project, SourceDocument, canonical_method_id
from dexatlas.core.pipeline import AnalysisResult, Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

logger = logging.getLogger(__name__)

#: Uploads land here before analysis. Scoped to the workspace, never executed.
UPLOAD_DIRNAME = "uploads"


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

app = FastAPI(
    title="DexAtlas",
    version=__version__,
    description=(
        "Evidence-first Android reverse engineering and analysis platform. "
        "Analyses applications you own or are authorized to assess."
    ),
    license_info={"name": "Apache-2.0"},
)


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
    apk_path: str
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(settings: SettingsDep, analyzer: AnalyzerDep) -> HealthResponse:
    """Liveness plus which backends this deployment can actually use."""
    return HealthResponse(
        status="ok",
        version=__version__,
        backends={b.name: b.version() if b.available() else None for b in analyzer.backends.all()},
    )


@app.get("/backends", tags=["meta"])
def list_backends(analyzer: AnalyzerDep) -> dict[str, Any]:
    """Which analysis backends are installed, and at what version."""
    return {
        "available": [b.name for b in analyzer.backends.available()],
        "missing": [b.name for b in analyzer.backends.missing()],
        "versions": analyzer.backends.versions(),
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
    upload_dir = settings.workspace / UPLOAD_DIRNAME
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / Path(file.filename or "upload.apk").name

    try:
        with target.open("wb") as handle:
            handle.write(file.file.read())
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"could not store the upload: {exc}",
        ) from exc

    try:
        apk = inspect_apk(target)
    except ApkValidationError as exc:
        target.unlink(missing_ok=True)
        # The validator names the absolute path; a remote caller has no business
        # learning the server's filesystem layout.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_redact(str(exc), str(target)),
        ) from exc

    existing = analyzer.store.find_project_by_hash(apk.sha256)
    if existing is not None:
        return AnalyzeJobResponse(
            project_id=existing.id,
            status=existing.status.value,
            detail=f"/projects/{existing.id}",
        )

    background.add_task(_run_analysis, analyzer, target)
    return AnalyzeJobResponse(
        project_id=f"apk_{apk.sha256[:16]}",
        status="pending",
        detail=f"/projects/{Project.new_id(apk.sha256)}",
    )


def _run_analysis(analyzer: Analyzer, apk_path: Path) -> None:
    try:
        analyzer.analyze(apk_path)
    except Exception:
        logger.exception("background analysis of %s failed", apk_path)


@app.get("/projects", tags=["analysis"])
def list_projects(analyzer: AnalyzerDep) -> list[ProjectResponse]:
    """Every analysed project, newest first."""
    return [_project_response(p) for p in analyzer.store.list_projects()]


@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["analysis"])
def get_project(project_id: str, analyzer: AnalyzerDep) -> ProjectResponse:
    """One project's metadata, counts and any backend errors."""
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"no project {project_id!r}")
    return _project_response(project)


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


@app.get("/projects/{project_id}/classes/{class_name:path}/source", tags=["analysis"])
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


@app.get("/projects/{project_id}/methods/{class_name:path}/{method_name}", tags=["analysis"])
def get_method_source(
    project_id: str,
    class_name: str,
    method_name: str,
    analyzer: AnalyzerDep,
    format: Annotated[
        str, Query(pattern="^(text|json)$", description="The source text, or a JSON document.")
    ] = "text",
) -> Any:
    """One method's body, preferring decompiled Java and falling back to Smali.

    As with the class source, the response says which representation it is.
    """
    document = analyzer.method_source_document(project_id, class_name, method_name)
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
def delete_project(project_id: str, analyzer: AnalyzerDep) -> None:
    """Remove a project and its symbols."""
    if not analyzer.store.delete_project(project_id):
        raise HTTPException(status_code=404, detail=f"no project {project_id!r}")


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
    project_id: str, class_name: str, method: str | None, document: SourceDocument
) -> dict[str, Any]:
    """The JSON form of a source: the text, and where it came from."""
    return {
        "project_id": project_id,
        "class_name": class_name,
        "method": method,
        "kind": document.kind.value,
        "provenance": [p.model_dump(mode="json") for p in document.provenance],
        "text": document.text,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_response(project: Any) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        status=project.status.value,
        apk_sha256=project.apk.sha256,
        apk_path=str(project.apk.path),
        apk_size_bytes=project.apk.size_bytes,
        class_count=project.class_count,
        method_count=project.method_count,
        reference_count=project.reference_count,
        evidence_count=project.evidence_count,
        resource_count=project.resource_count,
        tool_versions=project.tool_versions,
        errors=[ErrorResponse.model_validate(e.model_dump()) for e in project.errors],
    )


def _rebuild_result(analyzer: Analyzer, project_id: str) -> AnalysisResult:
    """Reconstruct an :class:`AnalysisResult` from storage, for on-demand export."""
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"no project {project_id!r}")
    return AnalysisResult(
        project=project,
        manifest=analyzer.store.get_manifest(project_id),
        evidence=analyzer.store.list_evidence(project_id),
        workspace=analyzer.store.get_workspace(project_id),
    )


__all__ = ["app"]
