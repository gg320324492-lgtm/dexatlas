"""The M4 workbench: a browser over the read-only MCP contract.

The workbench serves the analysis a workspace already holds, over the same
ten read-only tools the MCP server exposes. The functions under
:mod:`dexatlas.mcp.tools` are plain Python that takes an
:class:`~dexatlas.core.pipeline.Analyzer` — no stdio, no framework — so the
workbench calls them in-process and inherits the contract as it is. The
dashboard calls the two that answer "what is in this workspace":
``list_projects`` and ``get_project_status``. The search/evidence screen
calls five more — ``search_symbols``, ``get_class_source``,
``get_method_source``, ``get_evidence`` and ``resolve_locator`` — so a
reader goes from a phrase in the index to the source it names, to the
evidence record and to the place inside the analysis that record cites.

The workbench adds no analysis, no writes and no second contract: the JSON
the browser receives is the same shape the MCP server would have returned,
produced by the same functions. The front end is the React + TypeScript +
Vite application this package ships under ``web/``, built once into
``web/dist`` and served as static files. The workspace it reads is the same
``Settings`` workspace every other transport uses, so ``DEXATLAS_WORKSPACE``
points it somewhere else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from dexatlas import __version__
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import RequestError, unknown_project
from dexatlas.mcp.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    CalleeView,
    CallerView,
    EvidenceView,
    LocatorResolution,
    ProjectList,
    ProjectStatus,
    SourceView,
    SymbolList,
)
from dexatlas.mcp.tools import evidence as evidence_tools
from dexatlas.mcp.tools import projects as project_tools
from dexatlas.mcp.tools import references as reference_tools
from dexatlas.mcp.tools import symbols as symbol_tools

# The built front end. `npm run build` writes it; `python -m
# dexatlas.workbench` builds it on first start when npm is available. The
# path is resolved from this file, so a wheel or sdist carries it as data.
WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"

_BUILD_HINT = (
    "the workbench front end is not built yet; from the repository root run "
    "`npm install --prefix src/dexatlas/workbench/web` and then "
    "`npm run build --prefix src/dexatlas/workbench/web`"
)


def create_app(analyzer: Analyzer) -> FastAPI:
    """Build the workbench API + static front end around one ready Analyzer."""
    app = FastAPI(
        title="DexAtlas Workbench",
        version=__version__,
        description=(
            "A read-only web UI over the analysis a workspace already holds. "
            "The JSON answers the same ten read-only tools answer over stdio."
        ),
    )
    app.state.analyzer = analyzer

    @app.exception_handler(RequestError)
    def request_error(request: Request, exc: RequestError) -> JSONResponse:
        """The MCP contract's errors, as the browser can branch on them."""
        status_code = 404 if exc.code == "unknown_project" else 400
        return JSONResponse(status_code=status_code, content=exc.as_dict())

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        """Where this workbench reads from, and what code is running."""
        return {
            "version": __version__,
            "workspace": str(analyzer.settings.workspace),
        }

    @app.get("/api/projects", response_model=ProjectList)
    def list_projects(
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    ) -> ProjectList:
        """A page of the projects in this workspace, newest first."""
        return project_tools.list_projects(analyzer, limit=limit, offset=offset)

    @app.get("/api/projects/{project_id}", response_model=ProjectStatus)
    def project_status(project_id: str) -> ProjectStatus:
        """One project: how complete its analysis is, and what it holds."""
        return project_tools.project_status(analyzer, project_id)

    # -- the second screen: index -> source -> evidence -> the place cited --
    #
    # Each endpoint calls one plain-Python tool and answers with that tool's
    # own pydantic shape. A single new endpoint `/evidence` returns a *list*
    # of the same `EvidenceView` objects: MCP has no list-evidence tool, so
    # the browser reads the ids from the store and asks `get_evidence` for
    # each one. No field, count or status code is redefined here.

    # -- the third screen: the calls into and out of one method --
    #
    # Two endpoints, one per direction, each calling one of the two tools that
    # answer that question and returning that tool's own shape. What a reader
    # gets per call site is the caller, the callee, the opcode the call was
    # read from, the DEX file and the instruction offset, plus the locators —
    # so the graph is drawn from places, not from an inference.
    #
    # A method nobody calls answers with zero counts, not with a 404, because
    # that is what the tool answers: the workspace was searched and found
    # nothing. A 404 here would turn "no caller was read" into "this method
    # does not exist", which is the exact confusion this project exists to
    # prevent. The `unknown_method` error stays in the contract for the
    # transports that validate the id shape; these tools do not raise it, and
    # the workbench does not invent an error the tools do not produce.

    @app.get("/api/projects/{project_id}/callers", response_model=CallerView)
    def find_callers(
        project_id: str,
        method_id: str = Query(
            ...,
            description="The method's id, e.g. com.example.Foo.bar(Ljava/lang/String;)V.",
        ),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    ) -> CallerView:
        """Who calls a method, and where in the bytecode each call sits."""
        return reference_tools.find_callers(analyzer, project_id, method_id, limit=limit)

    @app.get("/api/projects/{project_id}/callees", response_model=CalleeView)
    def find_callees(
        project_id: str,
        method_id: str = Query(
            ...,
            description="The method's id, e.g. com.example.Foo.bar(Ljava/lang/String;)V.",
        ),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    ) -> CalleeView:
        """What a method calls, with the call-site and call-edge counts apart."""
        return reference_tools.find_callees(analyzer, project_id, method_id, limit=limit)

    # The screen needs the method ids it can ask about, and the tool that
    # finds them is the one the MCP server exposes: an index hit for a method
    # carries its canonical id, which is exactly what the two endpoints above
    # take. So this is the MCP tool's own call, unchanged.
    @app.get("/api/projects/{project_id}/symbols", response_model=SymbolList)
    def search_symbols(
        project_id: str,
        q: str = Query(..., description="The phrase to look for in the index."),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    ) -> SymbolList:
        """A page of index hits, with the excerpt that says why each matched."""
        return symbol_tools.search_symbols(analyzer, project_id, q, limit=limit, offset=offset)

    @app.get("/api/projects/{project_id}/source/class", response_model=SourceView)
    def class_source(
        project_id: str,
        class_name: str = Query(..., min_length=1),
    ) -> SourceView:
        """One class's Java or Smali, and the locator it was read from."""
        return symbol_tools.class_source(analyzer, project_id, class_name)

    @app.get("/api/projects/{project_id}/source/method", response_model=SourceView)
    def method_source(
        project_id: str,
        class_name: str = Query(..., min_length=1),
        method_name: str = Query(..., min_length=1),
        descriptor: str | None = Query(None),
    ) -> SourceView:
        """One method's source; an ambiguous name answers with its candidates."""
        return symbol_tools.method_source(analyzer, project_id, class_name, method_name, descriptor)

    @app.get("/api/projects/{project_id}/evidence", response_model=list[EvidenceView])
    def list_evidence(project_id: str) -> list[EvidenceView]:
        """Every evidence record, each one the MCP `get_evidence` answer.

        `get_evidence` takes an id, so a reader needs a way to find the ids.
        The ids are the store's own records, in the store's own order; this
        endpoint calls the tool once per id. It adds a collection, not a
        second shape: an item here is byte-for-byte what `/evidence/{id}`
        answers with.
        """
        if analyzer.store.get_project(project_id) is None:
            raise unknown_project(project_id)
        return [
            evidence_tools.get_evidence(analyzer, project_id, record.id)
            for record in analyzer.store.list_evidence(project_id)
        ]

    @app.get("/api/projects/{project_id}/evidence/{evidence_id}", response_model=EvidenceView)
    def get_evidence(project_id: str, evidence_id: str) -> EvidenceView:
        """One record, with the locators a reader can go and check."""
        return evidence_tools.get_evidence(analyzer, project_id, evidence_id)

    @app.get("/api/projects/{project_id}/locators/resolve", response_model=LocatorResolution)
    def resolve_locator(
        project_id: str,
        locator: str = Query(..., min_length=1),
    ) -> LocatorResolution:
        """Whether one provenance locator names a place inside this analysis."""
        return evidence_tools.resolve_locator(analyzer, project_id, locator)

    if front_end_is_built():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="workbench")
    else:

        @app.get("/")
        def front_end_not_built() -> JSONResponse:
            return JSONResponse(
                status_code=503,
                content={"code": "front_end_not_built", "message": _BUILD_HINT},
            )

    return app


def front_end_is_built() -> bool:
    """Whether the built front end is sitting where the app serves it from."""
    return (WEB_DIST / "index.html").is_file()
