# Architecture

How DexAtlas is put together, and why it is put together that way.

## The one rule everything follows

**Backends fail.** Not sometimes — routinely. A decompiler chokes on obfuscated control
flow, a manifest is a packed binary rather than XML, a DEX file is truncated. Every
external tool exists precisely to be fed things that break it.

So a backend failure is a **value**, never an exception. `Backend.run` returns a
`ToolOutcome` carrying an optional `ToolError` (`tools/base.py`), and the pipeline
branches on it. An APK that defeats JADX completely still yields a manifest, a symbol
index and a report — the report simply says which steps did not run.

That rule has a boundary, and the boundary is the shape of the thing rather than a
detail of it: **the analysis is not a backend.** A backend that cannot do its job is
recorded on the project and the run carries on without it; the analysis itself — a step
that raises, or a workspace that cannot be written — leaves the project failed and
raises `AnalysisFailed` to the caller (`core/pipeline.py`). A run that says nothing is
not a run that found nothing. A run that was stopped on request raises
`AnalysisCancelled` instead, and is recorded as *cancelled* rather than *failed*,
because nobody asked for this APK to be analysed any more.

That single decision shapes everything below.

## The pipeline

```text
                          ┌─────────────────────────────────────────┐
  app.apk                 │ core/ingest.py                          │
       │                  │  validate · hash · inspect              │
       ▼                  │  stdlib only, no backend trusted yet    │
  ApkMetadata  ──────────►└─────────────────────────────────────────┘
  (sha256, dex, libs)
       │
       ├──► core/pipeline.Analyzer ──► projects/<project-id>/runs/<run-id>/
       │         │                    apktool/ · jadx/ · index.db
       │         │                    (this run's own output)
       │         ├──► Apktool ─────► manifest, resources, Smali
       │         ├──► JADX ────────► Java source, method bodies
       │         └──► Androguard ──► symbol index, call sites
       │                             (parsed in a worker process)
       │              │
       │              ▼
       │              core/evidence.py
       │              verified / lead / insufficient
       │              │
       │              ▼
       │              publish ──► workspace/dexatlas.db
       │              (one transaction: this run's rows, or none)
       │              │
       │              ▼
       │              reports/json_report.py · reports/markdown.py
       │
       └─────────────► cli/main.py · api/app.py · mcp/server.py
                      (one analysis core, three transports)
```

`cli/main.py` and `api/app.py` hold no analysis logic. Both call `Analyzer`, and so
does the MCP server. That is what makes "every transport uses the same analysis core" a
property of the code rather than a claim in a document.

The two stages the diagram puts between the backends and the report are the ones that
were not here before. A run **stages** its results in a database of its own, under its
own directory, and then **publishes** them into the workspace in a single transaction.
Nothing a reader can see changes while a run is writing; a run that dies half way
through leaves the published snapshot exactly as it was.

## Runs: the project is not the analysis

A **project** is the APK. Its id is a content hash — `apk_<sha256[:16]>`
(`Project.new_id`, `core/models.py`) — so the same bytes always map to the same
project.

A **run** is one attempt at analysing it, and its id says nothing about the APK:
`run_<16 hex digits>`, chosen at random (`new_run_id`, `core/runs.py`). The two are
different things, and conflating them is what lets a reader see the symbols of one run
beside the evidence of another. The project id says *which* APK was analysed; it says
nothing about *when*, or *by which tools*, or *whether the result is whole*.

This used to be one thing. The project id was the analysis's identity, and
re-analysing an APK replaced its symbols in place. That is idempotent, which is a good
property for a cache and a bad one for an analysis — and the Phase 1 review found the
same shape of problem twice, in the `evidence` table not being cleared and in the
upload being overwritten, and fixed both by hand. A run fixes the class of it.

A run carries the facts that belong to an attempt rather than to a file: the tool
versions that took part, the hash of the input, how the execution ended (`completed`,
`failed` or `cancelled`), and how much of what the run set out to read it actually read
(`complete` or `partial`). A backend that fails does not make the run's other findings
untrue — but it does make the result incomplete, and a reader who is not told that
reads a partial index as a whole one.

A run stages its results and publishes them as a snapshot. A run that fails or is
cancelled publishes nothing, and the snapshot published before it stands.

See [Analysis runs](analysis-runs.md) for the lifecycle, the schema and the API.

## What each backend is for

The three backends do different jobs, and DexAtlas keeps them separate rather than
flattening their output into one form.

| Backend      | Role                          | Output kept as            |
| ------------ | ----------------------------- | ------------------------- |
| **Apktool**  | Manifest, resources, Smali    | Apktool's own             |
| **JADX**     | Java decompilation            | JADX's Java, verbatim     |
| **Androguard** | Authoritative symbol graph   | Normalized into the index |

Androguard is the *index* because parsing DEX is what it does; a decompiler's text output
is the wrong source for structure. JADX is the *representation*, kept verbatim because
round-tripping Java through a common model would lose exactly the details a reader came
for. Apktool is the **Smali fallback** — when JADX cannot reconstruct a method, the
bytecode is still there, and `Analyzer.method_source_document` falls back to it.

What gets unified is the index and metadata interface. What stays distinct is the
representation.

Androguard is a library rather than a program, so there is nothing to shell out to —
and a library parses in the process that called it. That is why its parse is given a
process of its own; see [Security posture](#security-posture).

## Provenance

Every extracted item carries where it came from:

```python
Provenance(
    tool="androguard",
    tool_version="4.1.4",
    apk_sha256="3bb32dd5...",
    locator="androguard:classes.dex#com.example.Crypto#com.example.Crypto.sign(Ljava/lang/String;)V",
)
```

Tool, version, APK hash, and a backend-native pointer back to the source. When two
backends see the same class, both entries are kept — `ClassRef.provenance` is a list.
A conclusion that cannot be traced back to a code location is not a conclusion, and this
is the mechanism that makes that checkable rather than aspirational.

A locator is a *pointer*, though, and on its own it says nothing about whether anything
is there: one that names a file the analysis never wrote reads exactly like one that
does. That used to be nobody's problem. It is now the check that decides whether a
record may call itself verified — see [Evidence levels](#evidence-levels).

## Evidence levels

```text
verified      deterministic tool, and a citation that resolves inside this analysis
lead          static-analysis or model-suggested risk indicator
insufficient  not enough evidence either way; needs a human
```

The level is passed explicitly by the caller and **never inferred from the wording**. A
record that says `CONFIRMED VULNERABILITY: hardcoded credential`, submitted as a `lead`,
stays a `lead`. This is what stops a plausible-sounding model claim from being promoted
to a finding, and there is a test for exactly that.

**Verified is now a claim about a citation, and the citation has to hold up.** It used
to be a label the caller chose: `EvidenceBuilder.add` wrote whatever level it was
handed. Now a `verified` record whose kind is `CODE_LOCATED` or `CROSS_REFERENCE` is
*checked* before it is written (`EvidenceBuilder._check_the_provenance`), and refused
with `InvalidProvenanceError` when:

- it carries no provenance at all — a located finding with no citation names no place,
  and the report renders it as established by a tool;
- its provenance names another APK — the citation is stale, and following it would take
  the reader to a different analysis;
- its locator is not a locator this project reads;
- no locator in it resolves inside the analysis — the file is not in the workspace, the
  class is not in the DEX, the method is not declared in the source.

The last one is the one that matters most. A fabricated citation is indistinguishable
from a real one by looking at it; only a resolution tells them apart.
`core/locators.py` is what tells them apart: `LocatorResolver` is given the workspace
of one analysis and answers, for one locator, whether the place is really inside it and
whether the thing it names is really there.

A **model's claim is a separate door, and it cannot be promoted.**
`EvidenceBuilder.add_claim` refuses `VERIFIED` outright, so a claim cannot buy itself
a finding by pointing at a place. A claim a tool later confirms is not that claim
promoted — it is the tool's own record, written through `add`.

A backend failure is `verified` evidence — that the tool failed is a fact — and its
locator names the failure rather than a place, which is what a failure is.

See [Evidence invariants](evidence-invariants.md) for the rules in full.

## Security posture

Treated input and untrusted tools, concretely:

- **Subprocess, never linked.** JADX and Apktool run as separate processes
  (`Backend.run`, `tools/base.py`). Their parsing bugs are not ours to inherit, and
  their licence obligations stay distinct.
  *This used to name Ghidra as well. There is no Ghidra backend — the three backends
  are JADX, Apktool and Androguard — and `Settings.ghidra_path` is read by nothing.*
- **The DEX parser runs in a worker process.** Androguard used to be the documented
  exception to the subprocess rule: it is a library, and a library parses in the process
  that called it. That is no longer the shape of it. The parse — the part of an
  analysis that runs on bytes the service did not write — is given a process of its own.
  `AndroguardBackend.extract` hands the job to `run_worker`, which writes a job file and
  starts `python -m dexatlas.tools.androguard.worker`; the worker opens the APK, walks the
  bytecode and writes a result file. It is started through the same `Backend.run`
  machinery, so the same timeout and the same tree kill apply, and it bounds itself as
  well: `setrlimit` on POSIX, a job object on Windows. A malformed DEX takes down the
  worker; the service sees a recorded parse failure and carries on.
- **What crosses that boundary is data.** JSON in both directions, never a pickle. A
  pickle is executable: reading one back is running the code that wrote it, and the
  code that wrote it ran against untrusted input. The models are rebuilt through their
  own validators on the other side, so what arrives is what the service would have
  built itself. See [Runtime isolation](runtime-isolation.md).
- **Everything read out of an APK is data, not instruction.** The strings and the
  decompiled source come from an untrusted file. A sentence inside it is not an
  instruction to whoever reads the response, so the text is carried in a field of its
  own that says so — `UntrustedText` in the MCP server's schemas — and the server's own
  descriptions are checked not to carry the APK's text.
- **Argument arrays, never a shell string.** A path inside an analysed APK cannot inject
  a command. There is a test that proves it.
- **`defusedxml` for the manifest.** It comes from an untrusted APK and declares entity
  expansions to try. An XXE payload is rejected, not expanded.
- **Walk limits.** Obfuscated APKs carry hundreds of thousands of methods and millions of
  instructions. Unbounded traversal is a denial of service against ourselves, so method,
  string and instruction limits are enforced and hitting one is logged. The three
  budgets are counted across the whole APK rather than per DEX file, so a multi-dex APK
  does not get N times the allowance.
- **Local-first.** Nothing leaves the machine. There is no model integration and no
  outbound call anywhere in the code: the MCP server speaks over stdio to a host on the
  same machine, and needs no model provider to do it.
- **Workspace scoping.** Extracted artifacts are written under the project workspace
  only. The API publishes the *name* of each analysed file and redacts the server's own
  directories from its error messages, so a response describes the analysis rather than
  the machine it came from. The redaction happens where the message is written, so every
  transport gets it.
- **Untrusted names stay inside the tree.** A class name becomes a path to read, and
  class names come from an analysed APK or from a request. There is one rule for it now,
  in `core/paths.py`: `class_to_relative_path` refuses any part of a name that would
  change the shape of the path, and both backends go through it — one rule, so they
  cannot drift apart. A name that fails the check is "no such class", not an error page.
- **Bounded inputs.** An upload over the size limit is refused while it streams, so it
  is never held in memory and never written in full. An archive whose declared contents
  are too large is refused from its central directory, before a byte of it is
  decompressed.
- **Bounded backends.** A backend that outlives its timeout takes its whole tree down
  with it — the launcher and the tool it started — so a hung decompiler cannot outlive
  the call that started it.

See [SECURITY.md](../../SECURITY.md) for the reporting process.

## The MCP server

DexAtlas can serve its analysis to an agent over the Model Context Protocol.

It is a **read-only tool server over a workspace**. It exposes what the workspace
already holds — the projects, their symbols, the call sites between their methods, the
evidence records, and the places those records were read from — and nothing else. Ten
tools: `list_projects`, `get_project_status`, `get_manifest`, `search_symbols`,
`get_class_source`, `get_method_source`, `find_callers`, `find_callees`, `get_evidence`
and `resolve_locator`.

It **needs no model**. It has no model, no planner and no opinions, and it makes no
decision about what the caller should look at next. A tool server that needed a model
provider would not be a tool server, and a deployment would not be able to run it
without an API key and a bill. The `mcp` extra is optional; the analysis core does not
need it.

It **never writes**: every tool reads the workspace through `Store.reading()`, a
read-only view that never commits, and the server registers no tool that writes. It
**never runs a shell**, and it **never returns more than a bounded amount of anything**
— every excerpt is cut to a number of lines and a number of bytes, and the cut is
stated in the response rather than left for the reader to guess.

Every tool answers with a shape that says how complete it is. "The analysis did not find
it" and "the analysis did not look" are different answers, and a caller that cannot tell
them apart reports a missing thing as an absent one.

See [The MCP server](mcp-server.md).

## Storage

SQLite with FTS5, in one workspace database — `workspace/dexatlas.db`
(`Settings.database_path`).

The tables are `projects` (one row per APK), `analysis_runs` (one row per attempt),
`classes`, `methods`, `fields`, `call_sites`, `strings`, `resources`,
`resource_references`, `evidence`, and
`search_index` — an FTS5 virtual table over the symbol names.

**A run publishes, and publishing replaces.** The tables that hold a project's published
snapshot — `classes`, `methods`, `fields`, `call_sites`, `strings`, `resources`,
`resource_references`,
`search_index` and `evidence` — are replaced as a whole when a run publishes. The
evidence table is in that list for the same reason the symbol tables are: it is written
afresh by every analysis, and its ids are assigned in sequence, so a record left behind
would keep an id that the new run has already given to a different record — and a report
that cites `E-0007` would send a reader to the wrong row.

The staged result lives in a database of its own, `runs/<run-id>/index.db`, holding the
same schema. That is what lets a finished run be published into the workspace in one
go: `Store.publish_run` copies the staged rows over, writes the project's own row,
moves the pointer to the run and writes the run's row, all in **one transaction**. A
reader sees the previous run's snapshot or this one, never a mixture.

**What happens to the previous snapshot.** Its *rows* are replaced, so the previous
run's symbols are gone. Its *record* is not: `analysis_runs` keeps the history of the
attempt — status, tool versions, errors, timings — and `projects.published_run_id`
names the run whose snapshot is published. The staged database is deleted when the run is
done with it, published or not.

**This is not what the content-addressed id used to mean.** Re-analysing an APK no
longer replaces its symbols in place, because the symbols belong to a *run* and not to
the project. What is idempotent now is the project row — the same bytes map to the
same project — and what gets replaced is the published snapshot, by a run, in one
transaction.

FTS5 queries are built as quoted phrases with doubled quotes, so user input is matched
literally and FTS operators in a search term cannot be injected as query syntax.

## Cross-references

Androguard 4.x removed its xref cache, so DexAtlas recovers the calls by walking
bytecode: scan each method's instructions for an invoke-form opcode, read the target
from its final operand, and count the instruction's offset as you go
(`AndroguardBackend._scan`).

**The walk produces call sites, and a call site is a place.** It names the DEX file the
instruction was read out of, the method that made the call, the instruction offset
inside that method, the opcode that carried the call, and the method that was called.
The index holds these, one row each, in `call_sites`.

**A call edge is the relationship, derived from the sites.** It is the caller, the
callee and the way the call is made, aggregated over the sites that make it
(`core/calls.py`, `derive_edges`). The edge is never the other way round: an edge that
exists without sites has nothing behind it, and the sites are what a citation points at.

One method that calls the same target twice is **two call sites and one call edge**. A
method defined in two DEX files is two call sites and one edge as well — the sites
differ in the DEX file rather than in the offset. The key carries the file *and* the
offset, so neither kind of duplication collapses into the other.

The two are different numbers, and the report says which is which. `reference_count` is
the number of sites; `call_edge_count` is the number of edges, counted as the distinct
`(caller, callee, kind)` triples over the rows. The report prints `Call sites indexed`
and `Call edges indexed` beside each other, with a note saying what each one is.

That walk is bounded by an instruction limit. On a large APK it is the most expensive
thing DexAtlas does, and it is the first thing to give up on.

The citation of a call site is the edge's locator, and the offset is **not** part of
it. That is deliberate: a citation has to resolve inside the analysis, and neither the
Java source nor the Smali carries a bytecode offset, so an offset in a locator would
point at something nothing can check. The offset is structured data — a column in the
table, a field in the API response — and the citation says where the relationship is.

See [Call sites and call edges](call-sites-and-edges.md).

## What is deliberately absent

- **Kubernetes, microservices, a distributed database.** SQLite is sufficient until it
  measurably is not.
- **A vector database as a hard dependency.** Exact symbol resolution and cross-references
  answer most questions precisely; semantic retrieval is a supplement, not a prerequisite.
- **A flattening model that turns JADX Java, Smali and a DEX graph into one
  representation.** It would be lossy in exactly the places that matter.
- **The results of a superseded run.** The published tables hold one snapshot, and a
  run's own record is the history of the attempt.
- **A model inside the MCP server.** It is a tool server, and a tool server that
  needed a model provider could not be run without an API key and a bill.
- **The bytecode offset in a citation.** The offset is in the row; the citation says
  where the relationship is.

## Layout

```text
src/dexatlas/
├── config/       settings: the workspace, the limits, the backend paths
├── core/
│   ├── models.py   the unified analysis model, provenance, evidence levels
│   ├── ingest.py   validation, hashing, archive inspection
│   ├── runs.py     the identity of one analysis attempt
│   ├── storage.py  SQLite schema, symbol tables, FTS5 search
│   ├── calls.py    call sites, call edges, and the difference between them
│   ├── methods.py  which method a request means
│   ├── locators.py resolving a citation against the analysis
│   ├── evidence.py evidence construction and the level discipline
│   ├── paths.py    paths that do not name the machine
│   └── pipeline.py Analyzer — the single orchestrator
├── tools/
│   ├── base.py     the Backend interface and subprocess execution
│   ├── jadx/       decompilation and source parsing
│   ├── apktool/    manifest and Smali
│   ├── androguard/ DEX symbol index, and the worker that parses it
│   └── registry.py backend discovery
├── reports/      JSON and Markdown renderers, and the coverage they report
├── cli/          Typer commands, plus the console-encoding layer
├── api/          FastAPI transport
├── mcp/          the read-only MCP server
└── agent/        the evidence-first agent
```

`mcp/` and `agent/` have landed. `web/` has not. The agent consumes this core through
the MCP tools — it calls them, it inherits their read-only nature, and it checks that
every conclusion it reached has something behind it before it reports it. It does not
duplicate any of it.

The rest of this directory holds the detail: [Analysis runs](analysis-runs.md),
[Call sites and call edges](call-sites-and-edges.md),
[Evidence invariants](evidence-invariants.md), [Runtime isolation](runtime-isolation.md),
[The MCP server](mcp-server.md) and [The agent](agent.md).
