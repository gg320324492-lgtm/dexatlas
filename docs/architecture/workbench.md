# The web workbench

DexAtlas can show its analysis in a browser. The workbench is **read-only
over an existing analysis**: it reads a workspace, and it never writes,
never runs a shell, and never analyses an APK on its own schedule. The one
exception is the upload screen, which hands an APK to exactly the same
analysis pipeline the REST API and the CLI run. It is the M4 screen set of
the [Phase 2 plan](../roadmap/phase2-plan.md)
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
| 2 | APK upload and analysis progress | **built** |
| 3 | Package / class / method explorer | **search + source viewer** |
| 4 | Java & Smali source viewer with source-location links | **source + locator resolution** |
| 5 | Call graph and cross-reference navigation | **built** |
| 6 | Agent workspace | not started |
| 7 | Evidence viewer, separating observations from hypotheses | **records + provenance** |
| 8 | Benchmark and report export | **report export built** |

## Screen 8: export the report

The project page carries an "Export the report" panel with two links:
`GET /api/projects/{id}/report?format=markdown` and
`GET /api/projects/{id}/report?format=json`. They are the renderers the CLI
and the REST API already use — `render_markdown` and `build_json_report`
over the published snapshot — so what the browser downloads is the same
report `dexatlas analyze` writes to disk, with no second format and no
changed field. The export describes the published run; a later attempt
that failed is named by the report, not merged into it.

What the screen does not yet have is the benchmark half of its title: the
measured runs and the comparison the benchmark suite produces are not
surfaced here.

## Screen 2: upload an APK and watch the analysis

The upload screen sits above the project list. A file is chosen, handed to
`POST /api/analyze`, and the analysis runs in a background task; the browser
polls the project's status until the run publishes or fails, and then moves
to the project page. Four things were decided deliberately:

- **The policy is the REST API's, not a copy.** The staging, the name
  sanitising, the size limit, the archive inspection and the
  hash-addressed storage live in `dexatlas.api.uploads`, and both
  transports call the same functions. A file the API refuses, the
  workbench refuses with the same status and the same words: 413 for a
  body over the limit, 422 for a file that is not an APK, 413 again for
  a declared length over the limit before the body is read.
- **An APK that was analysed before is answered with its project.** The
  response says `already_analysed: true`, and the browser opens the
  project instead of waiting for an analysis that is not going to run.
- **The wait is shown as a wait.** Analysis is synchronous and CPU-bound;
  nothing reports a percentage, so the screen does not invent one. It
  says the analysis is running, and it polls `get_project_status` — the
  same read-only tool the dashboard uses — until the project is
  `completed` or `failed`.
- **No upload, no analysis, no writes outside the pipeline.** The
  workbench itself still writes nothing but what the shared upload
  policy and the analysis pipeline write: the upload lands in the
  workspace's `uploads/` directory and the run's results in the project's
  own run directory, exactly as for the REST API.


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
there is no package tree, no editor component, no observation/hypothesis
workspace and no export yet. The call-graph part of screen 5 is the next
screen, below.

Screen 5 calls `find_callers`, `find_callees`, and `search_symbols` for the method id
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
technology the plan names for M4. Three decisions worth restating:

- **The built bundle is not committed.** `web/dist` is regenerable from
  `web/src`, and a generated artifact in the repository is one more thing
  that can quietly describe a tree that no longer exists. `python -m
  dexatlas.workbench` builds it on first start; a machine without npm gets
  told so instead of a silent fallback.
- **No routing library yet.** The hash routes — `#/`, `#/projects/{id}`,
  `#/projects/{id}/search` and `#/projects/{id}/calls` — are matched in a few
  lines; the router arrives when a screen needs it. Search query values and
  provenance locators are always passed through `URLSearchParams`, so a `#`,
  `(` or `->` inside a citation is not mistaken for part of a URL.
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

The third screen's tests are in the same file: the callers and the callees
the browser gets are the MCP contract's shapes unchanged — asserted by
comparing the response against the tool's own `model_dump()` — the limit is
bounded like the MCP tool's is, a method nobody calls answers with zero
counts rather than a 404, and the id the index search offers is the id the
cross-reference answers about.
