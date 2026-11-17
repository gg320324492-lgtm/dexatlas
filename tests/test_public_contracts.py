"""The public contracts, as tests.

``docs/architecture/public-contracts.md`` states what DexAtlas promises the
outside world: the REST routes and their shapes, the MCP tools, the CLI exit
codes, the report schema and the meanings of the counts. This module turns
those statements into assertions, so a contract cannot drift quietly — a
change to any of them fails here first, and the person making the change has
to say so in the CHANGELOG.

The contracts are exercised against the real interfaces: the routes are read
off the FastAPI application, the MCP tools are listed over the protocol, and
the CLI exit codes are triggered through the same runner the rest of the
suite uses. No third-party backend is required: the workspace is seeded
directly, the way ``tests/test_cli.py`` seeds its project.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import unittest.mock
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mcp.client import Client
from typer.testing import CliRunner

from dexatlas.api.app import app
from dexatlas.cli.main import (
    EXIT_AMBIGUOUS,
    EXIT_BAD_REQUEST,
    EXIT_EMPTY,
    EXIT_FAILED,
    EXIT_NO_INDEX,
    EXIT_TRUNCATED,
)
from dexatlas.cli.main import app as cli_app
from dexatlas.config.settings import get_settings
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    EvidenceLevel,
    ManifestInfo,
    MethodRef,
    MethodReference,
    Project,
    ProjectStatus,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import AnalysisFailed, AnalysisResult, Analyzer
from dexatlas.core.storage import Store, SymbolCounts
from dexatlas.mcp.schemas import DATA_NOTICE, DEFAULT_LIMIT, MAX_LIMIT, UntrustedText
from dexatlas.mcp.server import build_server
from dexatlas.reports.evidence_package import _REPORT_PATHS, NOT_INCLUDED, PACKAGE_SCHEMA_VERSION

runner = CliRunner()

#: The project id of the seeded workspace: derived from the seed hash, the way
#: every project id is.
SEED_SHA256 = "0123456789abcdef" * 4
SEED_PID = f"apk_{SEED_SHA256[:16]}"

#: A second project, whose method name is shared by two overloads. The exit
#: code for asking for it by name alone is the ambiguous one.
OVERLOAD_SHA256 = "b" * 64
OVERLOAD_PID = f"apk_{OVERLOAD_SHA256[:16]}"

#: Every route the REST API serves, as (method, path). A route that appears
#: here is published; a route that disappears is a breaking change.
EXPECTED_REST_ROUTES = {
    ("GET", "/health"),
    ("GET", "/backends"),
    ("POST", "/analyze"),
    ("GET", "/projects"),
    ("GET", "/projects/{project_id}"),
    ("DELETE", "/projects/{project_id}"),
    ("GET", "/projects/{project_id}/runs"),
    ("GET", "/projects/{project_id}/runs/{run_id}"),
    ("POST", "/projects/{project_id}/cancel"),
    ("GET", "/projects/{project_id}/manifest"),
    ("GET", "/projects/{project_id}/classes"),
    ("GET", "/projects/{project_id}/methods"),
    ("GET", "/projects/{project_id}/resources"),
    ("GET", "/projects/{project_id}/resource-references"),
    ("GET", "/projects/{project_id}/classes/{class_name:path}/source"),
    ("GET", "/projects/{project_id}/methods/{class_name:path}/{method_name}"),
    ("GET", "/projects/{project_id}/xrefs/{method_id:path}"),
    ("GET", "/projects/{project_id}/search"),
    ("GET", "/projects/{project_id}/evidence"),
    ("GET", "/projects/{project_id}/report"),
    ("GET", "/uploads"),
    ("DELETE", "/uploads/{sha256}"),
    ("POST", "/uploads/cleanup"),
}

#: The headers a source response carries beside its body.
EXPECTED_SOURCE_HEADERS = {
    "X-DexAtlas-Source-Kind",
    "X-DexAtlas-Source-Tool",
    "X-DexAtlas-Source-Locator",
    "X-DexAtlas-Source-Tool-Version",
}

#: The read-only tools, and nothing else.
EXPECTED_MCP_TOOLS = {
    "list_projects",
    "get_project_status",
    "get_manifest",
    "search_symbols",
    "get_class_source",
    "get_method_source",
    "find_callers",
    "find_callees",
    "find_resource_declarations",
    "get_evidence",
    "resolve_locator",
}

#: The CLI's exit codes, as the epilog states them.
EXPECTED_EXIT_CODES = {
    0: "the command did what was asked",
    EXIT_EMPTY: "the answer is empty",
    EXIT_BAD_REQUEST: "the request was wrong",
    EXIT_FAILED: "the analysis itself failed",
    EXIT_AMBIGUOUS: "the answer is ambiguous",
    EXIT_TRUNCATED: "a limit cut a step short",
    EXIT_NO_INDEX: "no symbol index could be built",
}

#: The fields of a project response, in the order the schema declares them.
EXPECTED_PROJECT_FIELDS = {
    "id",
    "status",
    "apk_sha256",
    "apk_path",
    "apk_size_bytes",
    "class_count",
    "method_count",
    "reference_count",
    "call_site_count",
    "call_edge_count",
    "evidence_count",
    "resource_count",
    "tool_versions",
    "errors",
}

#: The top-level fields of the JSON report.
EXPECTED_REPORT_FIELDS = {
    "schema_version",
    "generated_at",
    "project",
    "run",
    "latest_attempt_status",
    "tools",
    "errors",
    "manifest",
    "evidence",
    "summary",
}

#: The fields of the evidence package's manifest.
EXPECTED_PACKAGE_MANIFEST_FIELDS = {
    "schema_version",
    "project_id",
    "apk_sha256",
    "run_id",
    "package_generated_at",
    "tool_versions",
    "files",
    "not_included",
}

#: What a backend failure can be recorded as.
EXPECTED_TOOL_ERROR_CODES = {
    "not_installed",
    "timeout",
    "exit_nonzero",
    "parse_error",
    "unsupported",
    "output_truncated",
    "analysis_failed",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated workspace, the way the CLI tests make one."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    get_settings.cache_clear()
    try:
        yield ws
    finally:
        get_settings.cache_clear()


def _provenance(sha256: str, locator: str) -> list[Provenance]:
    return [Provenance(tool="androguard", apk_sha256=sha256, locator=locator)]


def _seed_workspace(ws: Path) -> None:
    """A completed project and an overloaded one, written straight to the store.

    Seeding keeps the contract tests independent of the analysis backends: a
    machine with none of them installed still has to be able to check that
    the interfaces keep their shapes.
    """
    store = Store.open(get_settings().database_path)
    project = Project(
        id=Project.new_id(SEED_SHA256),
        apk=ApkMetadata(sha256=SEED_SHA256, size_bytes=4096, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=1,
        method_count=2,
        reference_count=1,
        call_edge_count=1,
    )
    store.save_project(project, ws / "projects" / project.id, manifest=None)
    store.save_symbols(
        project.id,
        [
            ClassRef(
                name="com.example.demo.MainActivity",
                kind=ClassKind.CLASS,
                provenance=_provenance(SEED_SHA256, "androguard:classes.dex#MainActivity"),
            )
        ],
        [
            MethodRef(
                class_name="com.example.demo.MainActivity",
                name="onCreate",
                descriptor="(Landroid/os/Bundle;)V",
                provenance=_provenance(SEED_SHA256, "androguard:classes.dex#MainActivity"),
            ),
            MethodRef(
                class_name="com.example.demo.MainActivity",
                name="toString",
                descriptor="()Ljava/lang/String;",
                provenance=_provenance(SEED_SHA256, "androguard:classes.dex#MainActivity"),
            ),
        ],
        [],
        [
            # One caller, calling once: one call site, one call edge. The two
            # counts are part of the xref contract, and a seeded row is what
            # the endpoint reads them from.
            MethodReference(
                caller="com.example.demo.Other.onCreate(Landroid/os/Bundle;)V",
                callee="com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V",
            )
        ],
        [],
    )

    overloaded = Project(
        id=Project.new_id(OVERLOAD_SHA256),
        apk=ApkMetadata(sha256=OVERLOAD_SHA256, size_bytes=1, path=Path("overloaded.apk")),
        status=ProjectStatus.COMPLETED,
    )
    store.save_project(overloaded, ws / "projects" / overloaded.id, manifest=None)
    store.save_symbols(
        overloaded.id,
        [
            ClassRef(
                name="com.example.Crypto",
                kind=ClassKind.CLASS,
                provenance=_provenance(OVERLOAD_SHA256, "androguard:classes.dex#Crypto"),
            )
        ],
        [
            MethodRef(
                class_name="com.example.Crypto",
                name="sign",
                descriptor=descriptor,
                provenance=_provenance(OVERLOAD_SHA256, "androguard:classes.dex#Crypto"),
            )
            for descriptor in ("(I)V", "(Ljava/lang/String;)V")
        ],
        [],
        [],
        [],
    )


@pytest.fixture
def seeded_workspace(workspace: Path) -> Path:
    _seed_workspace(workspace)
    return workspace


@pytest.fixture
def client(seeded_workspace: Path) -> Iterator[TestClient]:
    """A REST client over the seeded workspace."""
    app.dependency_overrides[get_settings] = get_settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seeded_analyzer(seeded_workspace: Path) -> Analyzer:
    return Analyzer()


# ---------------------------------------------------------------------------
# The REST contract
# ---------------------------------------------------------------------------


#: Routes FastAPI adds by itself. They are the framework's, not the contract's.
FRAMEWORK_ROUTES = {
    ("GET", "/docs"),
    ("HEAD", "/docs"),
    ("GET", "/redoc"),
    ("HEAD", "/redoc"),
    ("GET", "/openapi.json"),
    ("HEAD", "/openapi.json"),
    ("GET", "/docs/oauth2-redirect"),
    ("HEAD", "/docs/oauth2-redirect"),
}


def test_the_rest_route_table_is_the_contract() -> None:
    """Every published route is on the app, and the app serves nothing else."""
    served = {
        (method, route.path) for route in app.routes for method in getattr(route, "methods", set())
    }
    assert served - FRAMEWORK_ROUTES == EXPECTED_REST_ROUTES, (
        "the published REST surface changed — update "
        "docs/architecture/public-contracts.md and the CHANGELOG"
    )


def test_the_source_endpoints_declare_their_provenance_headers() -> None:
    """The schema says which headers a source response carries.

    OpenAPI spells a starlette ``:path`` converter without the ``:path``.
    """
    schema = app.openapi()
    for path in (
        "/projects/{project_id}/classes/{class_name}/source",
        "/projects/{project_id}/methods/{class_name}/{method_name}",
    ):
        headers = schema["paths"][path]["get"]["responses"]["200"].get("headers", {})
        assert set(headers) >= EXPECTED_SOURCE_HEADERS, f"{path} lost a provenance header"


def test_an_upload_is_answered_with_a_job(client: TestClient, minimal_apk: Path) -> None:
    """``POST /analyze`` accepts and answers with a job, not with an analysis."""
    response = client.post("/analyze", files={"file": ("tiny.apk", minimal_apk.read_bytes())})

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"project_id", "status", "detail"}
    assert body["project_id"].startswith("apk_")


def test_the_project_response_carries_both_call_counts(client: TestClient) -> None:
    """``call_site_count`` and ``reference_count`` are the same number, published twice."""
    body = client.get(f"/projects/{SEED_PID}").json()

    assert set(body) == EXPECTED_PROJECT_FIELDS
    assert body["call_site_count"] == body["reference_count"]


def test_the_xref_response_states_the_unit_of_its_total(client: TestClient) -> None:
    """``total`` is a count of call sites, and the response says so."""
    method_id = "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"
    body = client.get(f"/projects/{SEED_PID}/xrefs/{method_id}").json()

    assert body["total_unit"] == "call_sites"
    assert body["total"] == body["call_sites"]
    assert body["call_edges"] <= body["call_sites"]


def test_the_json_report_is_schema_version_3(client: TestClient) -> None:
    """The report's top level is the documented one, and says which version it is."""
    body = client.get(f"/projects/{SEED_PID}/report", params={"format": "json"}).json()

    assert body["schema_version"] == 3
    assert set(body) == EXPECTED_REPORT_FIELDS


def test_an_unknown_project_is_a_404_with_a_detail(client: TestClient) -> None:
    body = client.get("/projects/apk_deadbeefdeadbeef")

    assert body.status_code == 404
    assert "detail" in body.json()


def test_a_report_rejects_an_unknown_format(client: TestClient) -> None:
    assert client.get(f"/projects/{SEED_PID}/report", params={"format": "xml"}).status_code == 422


# ---------------------------------------------------------------------------
# The MCP contract
# ---------------------------------------------------------------------------


def test_the_mcp_tool_table_is_the_contract(seeded_analyzer: Analyzer) -> None:
    """The tool list is the whole contract, and every tool is read-only."""

    async def ask() -> tuple[set[str], bool]:
        async with Client(build_server(seeded_analyzer)) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            read_only = all(
                tool.annotations is not None
                and tool.annotations.read_only_hint
                and not tool.annotations.destructive_hint
                for tool in listed.tools
            )
            return names, read_only

    names, read_only = asyncio.run(ask())

    assert names == EXPECTED_MCP_TOOLS
    assert read_only


def test_the_mcp_page_bounds_are_the_contract() -> None:
    """A page is at most ``MAX_LIMIT`` rows, and defaults to ``DEFAULT_LIMIT``."""
    assert MAX_LIMIT == 200
    assert DEFAULT_LIMIT == 50
    assert 1 <= DEFAULT_LIMIT <= MAX_LIMIT


def test_apk_text_travels_with_the_data_notice() -> None:
    """Every piece of an APK that reaches a caller says what it is."""
    text = UntrustedText(text="some string from the apk")
    assert text.notice == DATA_NOTICE
    assert "untrusted" in DATA_NOTICE.lower()


# ---------------------------------------------------------------------------
# The CLI contract
# ---------------------------------------------------------------------------


def test_the_cli_exit_code_table_is_the_contract() -> None:
    """The constants, their meanings in the epilog, and the epilog itself agree."""
    from dexatlas.cli.main import EXIT_AMBIGUOUS as AMBIGUOUS
    from dexatlas.cli.main import EXIT_BAD_REQUEST as BAD
    from dexatlas.cli.main import EXIT_EMPTY as EMPTY
    from dexatlas.cli.main import EXIT_FAILED as FAILED
    from dexatlas.cli.main import EXIT_NO_INDEX as NO_INDEX
    from dexatlas.cli.main import EXIT_TRUNCATED as TRUNCATED

    assert (EMPTY, BAD, FAILED, AMBIGUOUS, TRUNCATED, NO_INDEX) == (1, 2, 3, 4, 5, 6)
    epilog = cli_app.info.epilog or ""
    for code, phrase in EXPECTED_EXIT_CODES.items():
        assert str(code) in epilog, f"exit code {code} is not declared in the epilog"
        assert phrase.split()[0] in epilog, f"exit code {code} loses its meaning"


def test_cli_success_is_zero(seeded_workspace: Path) -> None:
    assert runner.invoke(cli_app, ["version"]).exit_code == 0
    assert runner.invoke(cli_app, ["projects"]).exit_code == 0


def test_cli_an_empty_answer_is_one(seeded_workspace: Path) -> None:
    """A project that is there, asked for something it does not hold."""
    result = runner.invoke(cli_app, ["search", SEED_PID, "nothing-matches-this"])

    assert result.exit_code == EXIT_EMPTY


def test_cli_a_wrong_request_is_two(seeded_workspace: Path) -> None:
    """An id that names nothing is a wrong request, not an empty answer."""
    result = runner.invoke(cli_app, ["classes", "apk_nope"])

    assert result.exit_code == EXIT_BAD_REQUEST
    assert "No such project" in result.stderr


def test_cli_an_ambiguous_method_is_four(seeded_workspace: Path) -> None:
    """A name shared by two overloads is answered with the candidates and code 4."""
    result = runner.invoke(
        cli_app, ["source", OVERLOAD_PID, "com.example.Crypto", "--method", "sign"]
    )

    assert result.exit_code == EXIT_AMBIGUOUS
    assert "(I)V" in result.output and "(Ljava/lang/String;)V" in result.output


def test_cli_a_failed_analysis_is_three(seeded_workspace: Path, tmp_path: Path) -> None:
    """The pipeline failing is its own exit code, distinct from empty and wrong."""
    failure = AnalysisFailed(
        ToolError(
            tool="dexatlas",
            code=ToolErrorCode.ANALYSIS_FAILED,
            message="the workspace could not be written",
        )
    )
    # ``analyze`` validates that the file exists before anything else, so the
    # stub is handed a real path to a file it never reads.
    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")

    class _Failing:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> object:
            raise failure

    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _Failing):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == EXIT_FAILED


def test_cli_a_truncated_analysis_is_five(seeded_workspace: Path, tmp_path: Path) -> None:
    """A finished run with a capped step is its own exit code, and says so."""
    truncated = Project(
        id=Project.new_id("c" * 64),
        apk=ApkMetadata(sha256="c" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        errors=[
            ToolError(
                tool="jadx",
                code=ToolErrorCode.OUTPUT_TRUNCATED,
                message="output cut at the cap",
            )
        ],
    )

    class _Truncating:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> AnalysisResult:
            return AnalysisResult(project=truncated, manifest=None)

    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")
    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _Truncating):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == EXIT_TRUNCATED
    assert str(EXIT_TRUNCATED) in result.output


def test_cli_an_analysis_with_no_index_is_six(seeded_workspace: Path, tmp_path: Path) -> None:
    """A finished run whose DEX reader failed but whose manifest survived is 6.

    Three backends that all timed out leave the index empty while the
    manifest Apktool wrote before it was stopped stays readable: the run
    completed and its report is written, but a caller who reads only the exit
    code must be able to tell "nothing was indexed" from a whole run. The
    class count is the published count, so the stub publishes it.
    """
    project = Project(
        id=Project.new_id("d" * 64),
        apk=ApkMetadata(sha256="d" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=0,
        errors=[
            ToolError(
                tool="androguard",
                code=ToolErrorCode.TIMEOUT,
                message="androguard timed out",
            ),
            ToolError(
                tool="jadx",
                code=ToolErrorCode.TIMEOUT,
                message="jadx timed out",
            ),
            ToolError(
                tool="apktool",
                code=ToolErrorCode.TIMEOUT,
                message="apktool timed out",
            ),
        ],
    )

    class _NoIndex:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> AnalysisResult:
            return AnalysisResult(project=project, manifest=ManifestInfo())

    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")
    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _NoIndex):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == EXIT_NO_INDEX
    assert str(EXIT_NO_INDEX) in result.output


def test_cli_a_partial_index_stays_zero(seeded_workspace: Path, tmp_path: Path) -> None:
    """A run that indexed something keeps exit code 0, despite backend errors.

    The new code is for a run with no usable index at all; a partial index is
    described by its errors and its completeness, and stays a success.
    """
    project = Project(
        id=Project.new_id("e" * 64),
        apk=ApkMetadata(sha256="e" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=3,
        errors=[
            ToolError(
                tool="jadx",
                code=ToolErrorCode.TIMEOUT,
                message="jadx timed out",
            ),
        ],
    )

    class _Partial:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> AnalysisResult:
            return AnalysisResult(project=project, manifest=ManifestInfo())

    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")
    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _Partial):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == 0


def test_cli_an_empty_index_without_gaps_stays_zero(seeded_workspace: Path, tmp_path: Path) -> None:
    """An APK with no DEX is a whole answer at 0, not a run that lost its index.

    The class count being zero is only a gap when a DEX reader failed to fill
    it; an APK that holds no code indexed nothing because there was nothing
    to index.
    """
    project = Project(
        id=Project.new_id("f" * 64),
        apk=ApkMetadata(sha256="f" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=0,
    )

    class _ResourceOnly:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> AnalysisResult:
            return AnalysisResult(project=project, manifest=ManifestInfo())

    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")
    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _ResourceOnly):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == 0


def test_cli_no_index_wins_over_truncation(seeded_workspace: Path, tmp_path: Path) -> None:
    """An empty index with a capped step is still 6: no index is the stronger fact."""
    project = Project(
        id=Project.new_id("a1" * 32),
        apk=ApkMetadata(sha256="a1" * 32, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        class_count=0,
        errors=[
            ToolError(
                tool="androguard",
                code=ToolErrorCode.TIMEOUT,
                message="androguard timed out",
            ),
            ToolError(
                tool="jadx",
                code=ToolErrorCode.OUTPUT_TRUNCATED,
                message="output cut at the cap",
            ),
        ],
    )

    class _NoIndexAndTruncated:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, path: Path) -> AnalysisResult:
            return AnalysisResult(project=project, manifest=ManifestInfo())

    apk = tmp_path / "whatever.apk"
    apk.write_bytes(b"")
    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _NoIndexAndTruncated):
        result = runner.invoke(cli_app, ["analyze", str(apk)])

    assert result.exit_code == EXIT_NO_INDEX


# ---------------------------------------------------------------------------
# The shared shapes
# ---------------------------------------------------------------------------


def test_the_tool_error_codes_are_the_contract() -> None:
    """A recorded failure carries one of these codes, and nothing else."""
    assert {code.value for code in ToolErrorCode} == EXPECTED_TOOL_ERROR_CODES


def test_the_evidence_levels_are_the_three() -> None:
    assert {level.value for level in EvidenceLevel} == {"verified", "lead", "insufficient"}


def test_the_symbol_counts_name_what_they_count() -> None:
    """The count fields are the contract: sites and edges are different numbers."""
    assert set(SymbolCounts.__dataclass_fields__) == {
        "classes",
        "methods",
        "fields",
        "call_sites",
        "call_edges",
        "resources",
        "resource_references",
    }


def test_the_evidence_package_manifest_is_versioned() -> None:
    """The manifest says which shape it is, and names what it leaves out."""
    assert PACKAGE_SCHEMA_VERSION == 1
    assert set(_REPORT_PATHS) == {"json", "markdown", "html"}
    assert set(NOT_INCLUDED) == {"apk", "full_sources", "unrelated_strings"}


# ---------------------------------------------------------------------------
# The number of the live checks
# ---------------------------------------------------------------------------

#: The live contract checks, by the section of the script that holds them.
#:
#: The number of ``check()`` call sites in ``scripts/verify-public-contracts.py``
#: is written down by hand in several materials — the changelog, the release
#: notes, the contract table, the release body — so that a reader of any one
#: of them sees the same count. Nothing held the script and the materials
#: together: the number was maintained by whoever remembered to count, and a
#: new check could be added without the five places being touched.
#:
#: The counts are pinned here. A change to the script's checks has to change
#: this, and the materials with it, in the same commit — which is the point
#: of an invariant that is maintained by hand.
CONTRACT_CHECK_SECTIONS = {"_rest_requests": 28, "mcp_checks": 6, "cli_checks": 15}

#: The number those call sites add up to.
CONTRACT_CHECK_TOTAL = 49

#: The materials that repeat the number, and the count they have to repeat.
MATERIALS_THAT_STATE_THE_COUNT = (
    "CHANGELOG.md",
    "docs/architecture/public-contracts.md",
    "docs/how-to-verify.md",
    "docs/how-to-verify.zh-CN.md",
    "docs/releases/v1.0.0.md",
    "docs/reports/v1.0.0-github-release-body.md",
)

#: A statement of the split: "28 REST + 6 MCP + 15 CLI".
CHECK_SPLIT = re.compile(r"(\d+) REST \+ (\d+) MCP \+ (\d+) CLI")

#: A number as a document writes it: "1,588" is one number, and "149" is not
#: "49".
STATED_NUMBER = re.compile(r"(?<![\d,])49(?![\d,])")

#: The root of the checked-out project.
REPO_ROOT = Path(__file__).parent.parent

#: Directories whose markdown is not the project's own.
_NOT_DOCUMENTS = frozenset(
    {".git", ".venv", ".scratch", "build", "dist", "node_modules", ".mypy_cache", ".pytest_cache"}
)

#: Paths that are local working state, not part of the checked-out project.
#:
#: Everything under ``.claude/`` is ignored: a worktree parked there is a
#: *second* copy of the whole repository, carrying documents written to
#: resolve from *its* directories. Reading those as this tree's documents made
#: every parallel session look broken while the project's own documents were
#: fine — a failure pointing at a file nobody had edited. The walk stops at
#: the directory instead of filtering its files afterwards.
_LOCAL_STATE_PATHS = frozenset({".claude"})


def _the_live_check_script() -> Path:
    return Path(__file__).parent.parent / "scripts" / "verify-public-contracts.py"


def _check_call_sites() -> dict[str, int]:
    """The ``check()`` call sites of the live contract script, by section.

    The count is taken from the syntax tree, not from the text: a ``check()``
    in a comment or in a string is not a check, and a text search would count
    it as one.
    """
    tree = ast.parse(_the_live_check_script().read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        calls = sum(
            1
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "check"
        )
        if calls:
            counts[node.name] = calls
    return counts


def _the_documents() -> list[Path]:
    """Every markdown document of the repository.

    The walk prunes the local working state (``.claude/``) instead of
    filtering its files afterwards, the way ``tests/test_docs.py`` prunes its
    own walk: a worktree parked under ``.claude/`` is another checkout of
    this repository, not this tree's documentation.
    """
    found: list[Path] = []
    for root, directories, files in os.walk(REPO_ROOT):
        directories[:] = [
            name
            for name in directories
            if name not in _NOT_DOCUMENTS and name not in _LOCAL_STATE_PATHS
        ]
        found.extend(Path(root) / name for name in files if name.lower().endswith(".md"))
    return sorted(found)


def test_the_document_walk_ignores_the_local_working_state(tmp_path: Path) -> None:
    """A worktree parked under ``.claude/`` is not this tree's documentation.

    Another session's checkout carries the documents of an older tree. When
    this walker read them as this tree's documents, a stale copy of a report
    failed the contract checks while the project's own copy was fine: the
    failure pointed at a file nobody had edited, and the red build it caused
    said nothing about the tree being released. The walk must stop at
    ``.claude/`` — and still find the project's own documents, which is what
    the planted file below asserts.
    """
    nested = tmp_path / ".claude" / "worktrees" / "some-session" / "docs" / "reports"
    nested.mkdir(parents=True)
    (nested / "stale.md").write_text("28 REST + 6 MCP + 15 CLI\n")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "own.md").write_text("a document of this tree\n")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("tests.test_public_contracts.REPO_ROOT", tmp_path)
        documents = _the_documents()

    outside = [path for path in documents if not path.is_relative_to(tmp_path)]
    assert outside == [], f"the walk left the planted root: {outside[:3]}"

    names = sorted(path.relative_to(tmp_path).as_posix() for path in documents)
    assert names == ["docs/own.md"]


def test_the_live_contract_script_has_the_number_of_checks_the_materials_state() -> None:
    """The script's ``check()`` call sites are the number the materials repeat.

    A new check that is not counted in the materials is a number that is
    wrong in five places at once, and nothing used to notice.
    """
    counts = _check_call_sites()

    assert counts == CONTRACT_CHECK_SECTIONS, (
        f"the live contract script has {counts}, the materials say {CONTRACT_CHECK_SECTIONS}"
    )
    assert sum(counts.values()) == CONTRACT_CHECK_TOTAL


def test_every_document_that_states_the_check_count_states_the_right_one() -> None:
    """A document that repeats the split repeats the count that goes with it.

    The live runs state fewer checks — one REST check does not fire without
    a source backend — and those are left alone. The static count is the one
    the script has, and a document that states it has to state 49 with it,
    next to the split or right after it.
    """
    static = (
        f"{CONTRACT_CHECK_SECTIONS['_rest_requests']} REST + "
        f"{CONTRACT_CHECK_SECTIONS['mcp_checks']} MCP + "
        f"{CONTRACT_CHECK_SECTIONS['cli_checks']} CLI"
    )

    for document in _the_documents():
        text = document.read_text(encoding="utf-8")
        for match in re.finditer(re.escape(static), text):
            before = text[max(0, match.start() - 40) : match.start()]
            after = text[match.end() : match.end() + 40]
            assert STATED_NUMBER.search(before) or STATED_NUMBER.search(after), (
                f"{document.name} states the split {static} without stating "
                f"{CONTRACT_CHECK_TOTAL} next to it"
            )


def test_the_release_materials_repeat_the_check_count() -> None:
    """The materials that repeat the count still repeat it.

    The number is repeated so that a reader of any one of them sees the same
    count. A material that stopped repeating it would leave the reader with
    a number nobody had checked.
    """
    root = Path(__file__).parent.parent
    split = (
        f"{CONTRACT_CHECK_SECTIONS['_rest_requests']} REST + "
        f"{CONTRACT_CHECK_SECTIONS['mcp_checks']} MCP + "
        f"{CONTRACT_CHECK_SECTIONS['cli_checks']} CLI"
    )

    for name in MATERIALS_THAT_STATE_THE_COUNT:
        document = root / name
        assert document.is_file(), f"{name} is missing"
        text = document.read_text(encoding="utf-8")
        assert split in text, f"{name} does not state the split {split}"
        assert str(CONTRACT_CHECK_TOTAL) in text, f"{name} does not state {CONTRACT_CHECK_TOTAL}"
