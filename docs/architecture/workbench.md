# The web workbench

DexAtlas can show its analysis in a browser. The workbench is **read-only**:
it reads a workspace, and it never writes, never analyses, and never runs a
shell. It is the M4 screen set of the [Phase 2 plan](../roadmap/phase2-plan.md)
being built one screen at a time; this document says what exists now, how to
run it, and the decisions the first two screens were built under.

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
| 3 | Package / class / method explorer | **search + source viewer** |
| 4 | Java & Smali source viewer with source-location links | **source + locator resolution** |
| 5 | Call graph and cross-reference navigation | not started |
| 6 | Agent workspace | not started |
| 7 | Evidence viewer, separating observations from hypotheses | **records + provenance** |
| 8 | Benchmark and report export | not started |

Screen 1 calls `list_projects` and `get_project_status` — the two tools that
answer what a workspace holds and how complete each analysis is.

The second screen is one screen because its questions follow a citation,
not a menu: **search symbols → read class/method source → read one evidence
record → resolve its provenance locator**. It calls five more tools:

| Tool | HTTP endpoint | What the screen does with its answer |
|---|---|---|
| `search_symbols` | `GET /api/projects/{id}/symbols?q=&offset=&limit=` | list index hits and their excerpts |
| `get_class_source` | `GET /api/projects/{id}/source/class?class_name=` | show one class's Java or Smali source |
| `get_method_source` | `GET /api/projects/{id}/source/method?class_name=&method_name=&descriptor=` | show one method's body; a method hit carries its exact descriptor |
| `get_evidence` | `GET /api/projects/{id}/evidence/{evidence_id}` | show one record's kind, level, detail and locators |
| `resolve_locator` | `GET /api/projects/{id}/locators/resolve?locator=` | say whether a citation names a place in this analysis, and show its source when it names a file |

`GET /api/projects/{id}/evidence` is the one endpoint that is not a single
MCP tool: the MCP contract has a tool that reads one record by id, but no
tool that lists the ids. It reads the store's record list and calls
`get_evidence` once per id, so every item in the response is exactly the
shape `/evidence/{id}` returns. It adds a collection, not a second contract:
no field, count or status code is redefined here. The other five endpoints
return their tool's pydantic model directly. An unknown project keeps each
tool's answer too: `search_symbols`, `get_evidence` and `resolve_locator`
raise the contract's `unknown_project` (mapped to 404), while the two source
tools answer `found: false` with a reason.

Text that came out of an APK is still untrusted data. The front end renders
it as text (never as HTML), keeps the MCP `UntrustedText` notice in the API
response, and says once on the screen that a sentence in a source file is
not an instruction. A locator that resolves to a DEX symbol rather than a
file is shown as **resolved with no file to display**, not as a missing
place — those are different facts in `resolve_locator`'s answer.

This screen covers the search, source-reading and evidence-record parts of
plan screens 3, 4 and 7. It does **not** claim the rest of those screens:
there is no package tree, no editor component, no call-graph viewer, no
observation/hypothesis workspace and no export yet.

## Running it

```bash
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas-workbench            # serves http://127.0.0.1:8618
```

The first start builds the front end (npm once), then every start is one
command. The `analyze` line is the one that fills a workspace: this workbench
reads an existing analysis and never analyses an APK itself. Both commands
use the same workspace, which is the one the rest of DexAtlas reads — set
`DEXATLAS_WORKSPACE` to point it somewhere else:

```bash
DEXATLAS_WORKSPACE=/path/to/workspace uv run dexatlas analyze examples/demo-app/demo.apk
DEXATLAS_WORKSPACE=/path/to/workspace uv run dexatlas-workbench
```

Open the project list, choose **search & evidence** on any project (or follow
the link on its status screen), and use the three numbered panels: search a
phrase, click a class or method hit, then open an evidence record and click
**resolve** beside one of its locators. With the demo APK, searching
`Crypto` finds the class and its `sign` method, and evidence `E-0003` carries
two Androguard locators that resolve into that analysis.

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
- **No routing library yet.** Three hash routes — `#/`, `#/projects/{id}`
  and `#/projects/{id}/search` — are matched in a few lines; the router
  arrives when a screen needs it. Search query values and provenance
  locators are always passed through `URLSearchParams`, so a `#`, `(` or
  `->` inside a citation is not mistaken for part of a URL.

For working on the front end itself:

```bash
cd src/dexatlas/workbench/web
npm install
npm run dev        # Vite's dev server, /api proxied to 127.0.0.1:8618
```

Start the Python side alongside it (`uv run dexatlas-workbench`) and edit
with hot reload.

## Tests

`tests/test_workbench.py` holds the transport's tests. They build an
isolated workspace with an indexed class, one Java source file and one
evidence record — no external backend is needed — and check the whole
second-screen chain: a search hit is `search_symbols`' shape (including the
`UntrustedText` notice and the bounded limit), a class and a method open as
`SourceView`s, the evidence list is made of `get_evidence` answers, and a
locator resolves to its place inside that analysis while a locator outside
it says it did not resolve. The unknown-project answers of the five tools
are kept as they are, and the front end is served when built and says how
to build it when it is not.
