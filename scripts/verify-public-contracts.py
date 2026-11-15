#!/usr/bin/env python3
"""Verify the public contracts against the real interfaces.

    uv run --no-sync python scripts/verify-public-contracts.py

The contract table is docs/architecture/public-contracts.md; this script is
the "verified" column behind it. It starts a real uvicorn server over
``dexatlas.api.app`` on a scratch workspace, analyses the first-party demo
APK, and checks every REST response against the shapes the table states.
The MCP tools are exercised over the MCP protocol, and the CLI exit codes
are triggered through the same runner the test suite uses. Anything that
drifts from the table fails here, with a non-zero exit code.

The exit codes 3 and 5 cannot be produced by a real backend on every
machine (3 needs the pipeline itself to fail, 5 needs a subprocess backend
whose output is capped), so they are triggered through the documented
mapping in ``cli/main.py`` with a stubbed analyzer — the same mechanism
``tests/test_output_truncation.py`` uses.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
import time
import unittest.mock
from pathlib import Path
from typing import Any

import httpx
from mcp.client import Client
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRATCH = REPO_ROOT / ".scratch" / "verify-contracts"
DEMO_APK = REPO_ROOT / "examples" / "demo-app" / "demo.apk"
PORT = 8977
BASE = f"http://127.0.0.1:{PORT}"

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name}  {detail}")
        FAILURES.append(name)


def section(title: str) -> None:
    print(f"\n== {title} ==")


# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------


def rest_checks() -> None:
    section("REST API over uvicorn")
    workspace = SCRATCH / "workspace"
    env = dict(os.environ)
    env["DEXATLAS_WORKSPACE"] = str(workspace)
    env["TMP"] = str(SCRATCH)
    env["TEMP"] = str(SCRATCH)
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dexatlas.api.app:app", "--port", str(PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _rest_requests()
    finally:
        server.terminate()
        server.wait(timeout=15)


def _rest_requests() -> None:
    apk_bytes = DEMO_APK.read_bytes()
    sha256 = hashlib.sha256(apk_bytes).hexdigest()
    pid = f"apk_{sha256[:16]}"

    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        for _ in range(120):
            try:
                client.get("/health")
                break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            check("server comes up", False, "uvicorn did not answer /health")
            return

        body = client.get("/health").json()
        check(
            "/health shape",
            set(body) == {"status", "version", "backends"} and body["status"] == "ok",
            str(body),
        )
        body = client.get("/backends").json()
        check(
            "/backends shape",
            set(body) == {"available", "missing", "versions"}
            and set(body["available"]).isdisjoint(body["missing"]),
            str(body),
        )

        response = client.post(
            "/analyze",
            files={"file": ("demo.apk", apk_bytes, "application/octet-stream")},
        )
        check(
            "POST /analyze -> 202 job",
            response.status_code == 202
            and set(response.json()) == {"project_id", "status", "detail"},
            f"{response.status_code} {response.text[:120]}",
        )
        check("project id is apk_<sha256[:16]>", response.json()["project_id"] == pid)

        status = ""
        for _ in range(240):
            project = client.get(f"/projects/{pid}").json()
            status = project.get("status", "")
            if status not in {"pending", "running"}:
                break
            time.sleep(0.5)
        check("analysis completes", status == "completed", f"status={status}")

        project_keys = {
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
        check(
            "/projects/{pid} ProjectResponse fields",
            set(project) == project_keys,
            str(set(project) ^ project_keys),
        )
        check(
            "call_site_count == reference_count",
            project["call_site_count"] == project["reference_count"],
        )
        listed = client.get("/projects").json()
        check("/projects lists ProjectResponse[]", isinstance(listed, list) and len(listed) >= 1)

        runs = client.get(f"/projects/{pid}/runs").json()
        check(
            "/runs shape",
            set(runs) == {"project_id", "total", "published_run_id", "runs"}
            and runs["total"] >= 1
            and set(runs["runs"][0])
            == {
                "id",
                "project_id",
                "status",
                "completeness",
                "apk_sha256",
                "tool_versions",
                "errors",
                "started_at",
                "finished_at",
                "duration_seconds",
                "published",
            },
            str(runs)[:200],
        )
        run_id = runs["published_run_id"]
        one_run = client.get(f"/projects/{pid}/runs/{run_id}").json()
        check("published run is published", one_run["published"] is True)

        manifest = client.get(f"/projects/{pid}/manifest")
        check(
            "/manifest answers or says why not",
            manifest.status_code in (200, 404)
            and (manifest.status_code != 404 or "manifest" in manifest.json()["detail"]),
            f"{manifest.status_code} {manifest.text[:120]}",
        )

        classes = client.get(f"/projects/{pid}/classes", params={"limit": 5}).json()
        check(
            "/classes shape and limit",
            set(classes) == {"project_id", "total", "classes"}
            and len(classes["classes"]) <= 5
            and classes["total"] >= len(classes["classes"]),
            str(classes)[:160],
        )

        methods = client.get(f"/projects/{pid}/methods", params={"limit": 5}).json()
        check(
            "/methods shape",
            set(methods) == {"project_id", "total", "methods"} and methods["total"] >= 1,
            str(methods)[:160],
        )

        resources = client.get(f"/projects/{pid}/resources").json()
        check(
            "/resources shape",
            set(resources) == {"project_id", "total", "resources"},
            str(resources)[:160],
        )
        resrefs = client.get(f"/projects/{pid}/resource-references").json()
        check(
            "/resource-references shape",
            set(resrefs) == {"project_id", "total", "references"},
            str(resrefs)[:160],
        )

        method_id = methods["methods"][0].get("id", None)
        if method_id is None:
            first = methods["methods"][0]
            method_id = f"{first['class_name']}.{first['name']}{first['descriptor']}"
        xrefs = client.get(f"/projects/{pid}/xrefs/{method_id}").json()
        check(
            "/xrefs shape and units",
            set(xrefs) >= {"method_id", "call_sites", "call_edges", "total", "total_unit"}
            and xrefs["total_unit"] == "call_sites"
            and xrefs["total"] == xrefs["call_sites"]
            and xrefs["call_edges"] <= xrefs["call_sites"],
            str(xrefs)[:200],
        )

        found = client.get(f"/projects/{pid}/search", params={"q": "demo"}).json()
        check(
            "/search shape",
            set(found) == {"project_id", "query", "results"} and found["query"] == "demo",
            str(found)[:160],
        )

        evidence = client.get(f"/projects/{pid}/evidence").json()
        levels_ok = all(
            row["level"] in {"verified", "lead", "insufficient"} for row in evidence["evidence"]
        )
        check(
            "/evidence shape and levels",
            set(evidence) == {"project_id", "total", "evidence"} and levels_ok,
            str(evidence)[:160],
        )

        source = client.get(f"/projects/{pid}/classes/com.example.demo.MainActivity/source")
        check(
            "/classes/.../source answers or 404",
            source.status_code in (200, 404),
            str(source.status_code),
        )
        if source.status_code == 200:
            check(
                "X-DexAtlas-Source-* headers",
                all(
                    header in source.headers
                    for header in (
                        "x-dexatlas-source-kind",
                        "x-dexatlas-source-tool",
                        "x-dexatlas-source-locator",
                        "x-dexatlas-source-tool-version",
                    )
                ),
                str(dict(source.headers))[:200],
            )

        report = client.get(f"/projects/{pid}/report", params={"format": "json"}).json()
        check(
            "/report json schema_version == 3",
            report["schema_version"] == 3
            and set(report)
            == {
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
            },
            str(report)[:160],
        )
        markdown = client.get(f"/projects/{pid}/report", params={"format": "markdown"})
        check(
            "/report markdown",
            markdown.status_code == 200 and markdown.text.startswith("#"),
            f"{markdown.status_code} {markdown.text[:80]}",
        )
        bogus = client.get(f"/projects/{pid}/report", params={"format": "bogus"})
        check("/report rejects an unknown format with 422", bogus.status_code == 422)

        missing = client.get("/projects/apk_deadbeefdeadbeef")
        check(
            "unknown project is a 404 with detail",
            missing.status_code == 404 and "detail" in missing.json(),
        )

        cleanup = client.post("/uploads/cleanup").json()
        check("POST /uploads/cleanup shape", set(cleanup) == {"removed", "names"})

        deleted = client.delete(f"/uploads/{sha256}")
        check("DELETE /uploads/{sha} -> 204", deleted.status_code == 204, str(deleted.status_code))

        gone = client.delete(f"/projects/{pid}")
        check("DELETE /projects/{pid} -> 204", gone.status_code == 204, str(gone.status_code))


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "list_projects",
    "get_project_status",
    "get_manifest",
    "search_symbols",
    "get_class_source",
    "get_method_source",
    "find_callers",
    "find_callees",
    "get_evidence",
    "resolve_locator",
}


def mcp_checks() -> None:
    section("MCP server over the protocol")
    from dexatlas.config.settings import Settings
    from dexatlas.core.pipeline import Analyzer
    from dexatlas.mcp.server import build_server

    settings = Settings(workspace=SCRATCH / "workspace")
    analyzer = Analyzer(settings)
    analyzer.analyze(DEMO_APK)

    async def ask() -> dict[str, Any]:
        async with Client(build_server(analyzer)) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            read_only = all(
                tool.annotations is not None and tool.annotations.read_only_hint
                for tool in listed.tools
            )
            projects = await client.call_tool("list_projects", {})
            status = await client.call_tool("get_project_status", {"project_id": _pid()})
            search = await client.call_tool(
                "search_symbols", {"project_id": _pid(), "query": "demo", "limit": 5}
            )
            source = await client.call_tool(
                "get_class_source",
                {"project_id": _pid(), "class_name": "com.example.demo.MainActivity"},
            )
            return {
                "names": names,
                "read_only": read_only,
                "projects": projects.structured_content,
                "status": status.structured_content,
                "search": search.structured_content,
                "source": source.structured_content,
            }

    answer = asyncio.run(ask())
    check("tool list is exactly the ten read-only tools", answer["names"] == EXPECTED_TOOLS)
    check("every tool is annotated read-only", answer["read_only"] is True)
    check(
        "list_projects page shape",
        set(answer["projects"]) == {"projects", "total", "offset", "limit"},
        str(answer["projects"])[:160],
    )
    check(
        "get_project_status shape",
        set(answer["status"]) == {"project", "completeness", "published_run", "runs"}
        and set(answer["status"]["completeness"])
        == {"complete", "missing_backends", "truncated", "errors"},
        str(answer["status"])[:200],
    )
    check(
        "search_symbols page shape",
        set(answer["search"]) == {"symbols", "total", "offset", "limit"},
        str(answer["search"])[:160],
    )
    source = answer["source"]
    check(
        "get_class_source says found or why not",
        set(source) >= {"found", "reason", "kind", "text", "provenance", "candidates"},
        str(source)[:200],
    )


def _pid() -> str:
    apk_bytes = DEMO_APK.read_bytes()
    return f"apk_{hashlib.sha256(apk_bytes).hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cli_checks() -> None:
    section("CLI exit codes")
    from dexatlas.cli.main import EXIT_AMBIGUOUS, EXIT_BAD_REQUEST, EXIT_EMPTY, app
    from dexatlas.config.settings import get_settings
    from dexatlas.core.models import (
        ApkMetadata,
        ClassKind,
        ClassRef,
        MethodRef,
        Project,
        ProjectStatus,
        Provenance,
        ToolError,
        ToolErrorCode,
    )
    from dexatlas.core.pipeline import AnalysisFailed, AnalysisResult
    from dexatlas.core.storage import Store

    runner = CliRunner()
    ws = SCRATCH / "workspace"
    os.environ["DEXATLAS_WORKSPACE"] = str(ws)
    get_settings.cache_clear()

    result = runner.invoke(app, ["version"])
    check("version exits 0", result.exit_code == 0, str(result.exit_code))
    result = runner.invoke(app, ["backends"])
    check("backends exits 0", result.exit_code == 0, str(result.exit_code))
    result = runner.invoke(app, ["analyze", str(DEMO_APK)])
    check("analyze of the demo APK exits 0", result.exit_code == 0, result.output[-200:])
    pid = _pid()
    result = runner.invoke(app, ["projects"])
    check("projects exits 0 and lists the project", result.exit_code == 0 and pid in result.stdout)

    result = runner.invoke(app, ["source", pid, "com.example.demo.MainActivity"])
    check("source without a source backend exits 1 (empty)", result.exit_code == EXIT_EMPTY)
    result = runner.invoke(app, ["resources", pid])
    check("resources without a resource backend exits 1 (empty)", result.exit_code == EXIT_EMPTY)

    result = runner.invoke(app, ["classes", "apk_nope"])
    check("unknown project exits 2", result.exit_code == EXIT_BAD_REQUEST)
    result = runner.invoke(app, ["classes", pid, "--limit", "0"])
    check("--limit 0 is refused with 2", result.exit_code == EXIT_BAD_REQUEST)
    result = runner.invoke(app, ["analyze", str(SCRATCH / "not-an-apk.txt")])
    check("a missing file exits 2", result.exit_code == EXIT_BAD_REQUEST)
    (SCRATCH / "not-an-apk.txt").write_text("not an apk", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(SCRATCH / "not-an-apk.txt")])
    check("a file that is not an APK exits 2", result.exit_code == EXIT_BAD_REQUEST)

    # Exit 4: one name, two overloads. The index answers with the candidates.
    store = Store.open(get_settings().database_path)
    synthetic = Project(
        id=Project.new_id("b" * 64),
        apk=ApkMetadata(sha256="b" * 64, size_bytes=1, path=Path("overloaded.apk")),
        status=ProjectStatus.COMPLETED,
    )
    store.save_project(synthetic, ws / "projects" / synthetic.id, manifest=None)
    provenance = [
        Provenance(tool="androguard", apk_sha256="b" * 64, locator="androguard:classes.dex#C")
    ]
    store.save_symbols(
        synthetic.id,
        [ClassRef(name="com.example.Crypto", kind=ClassKind.CLASS, provenance=provenance)],
        [
            MethodRef(
                class_name="com.example.Crypto",
                name="sign",
                descriptor=descriptor,
                provenance=provenance,
            )
            for descriptor in ("(I)V", "(Ljava/lang/String;)V")
        ],
        [],
        [],
        [],
    )
    result = runner.invoke(app, ["source", synthetic.id, "com.example.Crypto", "--method", "sign"])
    check("an ambiguous method name exits 4", result.exit_code == EXIT_AMBIGUOUS)
    check("the candidates are named", "sign" in result.output)

    # Exits 3 and 5 through the documented mapping, with a stubbed analyzer.
    class _Failing:
        def __init__(self, settings: object = None) -> None:
            pass

        def analyze(self, apk: Path) -> object:
            raise AnalysisFailed(
                ToolError(
                    tool="dexatlas",
                    code=ToolErrorCode.ANALYSIS_FAILED,
                    message="the workspace could not be written",
                )
            )

    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _Failing):
        result = runner.invoke(app, ["analyze", str(DEMO_APK)])
    check("a failed analysis exits 3", result.exit_code == 3, str(result.exit_code))

    truncated_project = Project(
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

        def analyze(self, apk: Path) -> AnalysisResult:
            return AnalysisResult(project=truncated_project, manifest=None)

    with unittest.mock.patch("dexatlas.cli.main.Analyzer", _Truncating):
        result = runner.invoke(app, ["analyze", str(DEMO_APK)])
    check("a truncated analysis exits 5", result.exit_code == 5, str(result.exit_code))


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rest_checks()
    mcp_checks()
    cli_checks()
    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        print("failed: " + ", ".join(FAILURES))
        return 1
    print("the public contracts hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
