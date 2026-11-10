# The web workbench

DexAtlas can show its analysis in a browser. The workbench is **read-only**:
it reads a workspace, and it never writes, never analyses, and never runs a
shell. It is the M4 screen set of the [Phase 2 plan](../roadmap/phase2-plan.md)
being built one screen at a time; this document says what exists now, how to
run it, and the decisions the first screens were built under.

## What it is

A browser over the same ten read-only tools the [MCP server](mcp-server.md)
exposes. The functions under `src/dexatlas/mcp/tools/` are plain Python that
takes an `Analyzer` — they are the layer the MCP server wraps in stdio, and
the workbench calls them in-process instead. That is the whole design: the
workbench adds no analysis, no writes, and **no second contract**. The JSON
the browser receives is the shape the MCP server would have returned,
produced by the same functions, so a number on a screen traces to the
workspace the same way a number in an MCP answer does.

The screens, from the plan, and where they stand:

| # | Screen | Status |
|---|---|---|
| 1 | Project dashboard with backend status | **built** |
| 2 | APK upload and analysis progress | not started |
| 3 | Package / class / method explorer | not started |
| 4 | Java & Smali source viewer | not started |
| 5 | Call graph and cross-reference navigation | not started |
| 6 | Agent workspace | not started |
| 7 | Evidence viewer | not started |
| 8 | Benchmark and report export | not started |

Screen 1 calls `list_projects` and `get_project_status` — the two tools that
answer what a workspace holds and how complete each analysis is. A screen
that needs more calls more tools; it does not add an endpoint that answers
differently.

## Running it

```bash
uv sync --extra dev --extra analysis --extra mcp
uv run dexatlas-workbench            # serves http://127.0.0.1:8618
```

The first start builds the front end (npm once), then every start is one
command. The workspace is the one the rest of DexAtlas reads — set
`DEXATLAS_WORKSPACE` to point it somewhere else:

```bash
DEXATLAS_WORKSPACE=/path/to/workspace uv run dexatlas-workbench
```

The API is also the app's documentation: `/docs` serves the OpenAPI schema
FastAPI generates.

## The front end

React + TypeScript + Vite, under `src/dexatlas/workbench/web/` — the
technology the plan names for M4. Two decisions worth restating:

- **The built bundle is not committed.** `web/dist` is regenerable from
  `web/src`, and a generated artifact in the repository is one more thing
  that can quietly describe a tree that no longer exists. `python -m
  dexatlas.workbench` builds it on first start; a machine without npm gets
  told so instead of a silent fallback.
- **No routing library yet.** Two screens hash-route in a few lines; the
  router arrives when a screen needs it.

For working on the front end itself:

```bash
cd src/dexatlas/workbench/web
npm install
npm run dev        # Vite's dev server, /api proxied to 127.0.0.1:8618
```

Start the Python side alongside it (`uv run dexatlas-workbench`) and edit
with hot reload.

## Tests

`tests/test_workbench.py` holds the transport's tests: the list and the
status the browser gets are the MCP contract's shapes unchanged, an unknown
project is the contract's `unknown_project` error as a 404, the limit is
bounded like the MCP tool's is, and the front end is served when built and
says how to build it when it is not.
