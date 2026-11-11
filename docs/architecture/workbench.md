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
| 5 | Call graph and cross-reference navigation | **built** |
| 6 | Agent workspace | not started |
| 7 | Evidence viewer | not started |
| 8 | Benchmark and report export | not started |

Screen 1 calls `list_projects` and `get_project_status` — the two tools that
answer what a workspace holds and how complete each analysis is. Screen 5
calls `find_callers`, `find_callees`, and `search_symbols` for the method id
it starts from. A screen that needs more calls more tools; it does not add an
endpoint that answers differently.

## Screen 5: the calls into and out of one method

`#/projects/{id}/calls` answers two questions about one method, one API call
per question: `GET /api/projects/{id}/callers?method_id=…` is
`find_callers` and its `CallerView`, `GET /api/projects/{id}/callees?method_id=…`
is `find_callees` and its `CalleeView`. A test asserts the response is the
tool's own `model_dump()` — that is the whole contract claim this screen makes.

**Where the method id comes from.** `find_callers` takes a method id, so the
screen starts from `search_symbols`: an index hit whose kind is `method`
carries the method's canonical id, which is exactly the string the two
cross-reference endpoints take. The reader clicks an id and the analysis is
asked about the same id the analysis indexed.

**What the view draws.** A three-column graph — the callers, the method asked
about, the callees — over an SVG the component lays out itself, plus the two
lists underneath it. The left column and the lists come from the call sites, so
each carries the opcode, the DEX file and the instruction offset the call was
read out of; clicking a node re-asks the same two tools about that method, so a
cross-reference walk is one hop per click rather than a new query shape.

Two things the screen deliberately does not draw:

- **No count on a callee node.** `find_callees` deduplicates its callees and
  answers no per-callee count; its two counts are totals. Drawing a number
  beside a callee would put on the screen a number no query re-derives, so a
  callee node carries the opcode and the totals sit above the graph.
- **No layout library.** The plan asks for "a lightweight graph viewer", and
  three columns of labelled boxes over a `pipeline`-free SVG is that. A
  force-directed layout would add a dependency, and a layout that moves the
  nodes would make a reader's position on the screen unrelated to anything the
  analysis says.

**A method nobody calls is a zero, not a 404.** `find_callers` returns
`call_site_count: 0` for a method no call site names, and the screen shows that
with the sentence that says what it does and does not mean. Turning it into a
404 would convert "the analysis read no call into this method" into "this
method does not exist", and that is the confusion the project exists to prevent.

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
technology the plan names for M4. Three decisions worth restating:

- **The built bundle is not committed.** `web/dist` is regenerable from
  `web/src`, and a generated artifact in the repository is one more thing
  that can quietly describe a tree that no longer exists. `python -m
  dexatlas.workbench` builds it on first start; a machine without npm gets
  told so instead of a silent fallback.
- **No routing library yet.** Three screens hash-route in a few lines; the
  router arrives when a screen needs it.
- **No graph library either.** Screen 5 lays out its three columns itself and
  draws its edges in an SVG, with the nodes as HTML links over it. The plan
  asks for "a lightweight graph viewer", and that is what this is: a
  force-directed layout would add a dependency, and a layout that moves nodes
  around would make where a reader sees a method unrelated to anything the
  analysis says. The nodes are HTML rather than SVG shapes because an `<a>` in
  the SVG namespace is a different element from an `<a>` in HTML, and engines
  disagree about whether clicking one navigates — a node a reader cannot click
  is a cross-reference they cannot follow.

For working on the front end itself:

```bash
cd src/dexatlas/workbench/web
npm install
npm run dev        # Vite's dev server, /api proxied to 127.0.0.1:8618
```

Start the Python side alongside it (`uv run dexatlas-workbench`) and edit
with hot reload.

## Tests

`tests/test_workbench.py` holds the transport's tests: the list, the status and
the cross-reference the browser gets are the MCP contract's shapes unchanged —
asserted by comparing the response against the tool's own `model_dump()` — an
unknown project is the contract's `unknown_project` error as a 404, the limit is
bounded like the MCP tool's is, a method nobody calls answers with zero counts
rather than a 404, the id the index search offers is the id the cross-reference
answers about, and the front end is served when built and says how to build it
when it is not.
