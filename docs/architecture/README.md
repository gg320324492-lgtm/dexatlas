# Architecture

How DexAtlas is put together, and why it is put together that way.

## The one rule everything follows

**Backends fail.** Not sometimes — routinely. A decompiler chokes on obfuscated control
flow, a manifest is a packed binary rather than XML, a DEX file is truncated. Every
external tool exists precisely to be fed things that break it.

So a backend failure is a **value**, never an exception. `Backend.run` returns a
`ToolOutcome` carrying an optional `ToolError`, and the pipeline branches on it. An APK
that defeats JADX completely still yields a manifest, a symbol index and a report — the
report simply says which steps did not run.

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
       ├──► core/pipeline.Analyzer ──► workspace/<project-id>/
       │         │
       │         ├──────────────┬────────────────┬──────────────────┐
       │         ▼              ▼                ▼                  │
       │      Apktool        JADX            Androguard             │
       │      manifest       Java source     symbol index           │
       │      Smali          method bodies   cross-references       │
       │         │              │                │                  │
       │         └──────────────┴────────────────┘                  │
       │                        │                                   │
       │                        ▼                                   │
       │              core/storage.py (SQLite + FTS5)               │
       │                        │                                   │
       │                        ├──► core/evidence.py               │
       │                        │     verified / lead / insufficient│
       │                        ▼                                   │
       │              reports/json_report.py                        │
       │              reports/markdown.py                          │
       │                                                            │
       └─────────────► cli/main.py  ·  api/app.py                   │
                       (one analysis core, two transports)          │
  ───────────────────────────────────────────────────────────────────
```

`cli/main.py` and `api/app.py` hold no analysis logic. Both call `Analyzer`. That is what
makes "CLI and REST API use the same analysis core" a property of the code rather than a
claim in a document.

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
bytecode is still there, and `Analyzer.method_source` falls back to it.

What gets unified is the index and metadata interface. What stays distinct is the
representation.

## Provenance

Every extracted item carries where it came from:

```python
Provenance(
    tool="androguard",
    tool_version="androguard 4.1.4",
    apk_sha256="3bb32dd5...",
    locator="androguard:classes.dex#tests.androguard.Eratosthene#eratosthenes(I)[I",
)
```

Tool, version, APK hash, and a backend-native pointer back to the source. When two
backends see the same class, both entries are kept — `ClassRef.provenance` is a list.
A conclusion that cannot be traced back to a code location is not a conclusion, and this
is the mechanism that makes that checkable rather than aspirational.

## Evidence levels

```text
verified      deterministic tool, locatable code location
lead          static-analysis or model-suggested risk indicator
insufficient  not enough evidence either way; needs a human
```

The level is passed explicitly by the caller and **never inferred from the wording**. A
record that says `CONFIRMED VULNERABILITY: hardcoded credential`, submitted as a `lead`,
stays a `lead`. This is what stops a plausible-sounding model claim from being promoted
to a finding, and there is a test for exactly that.

A backend failure is `verified` evidence — that the tool failed is a fact.

## Security posture

Treated input and untrusted tools, concretely:

- **Subprocess, never linked.** JADX, Apktool and Ghidra run as separate processes. Their
  parsing bugs are not ours to inherit, and their licence obligations stay distinct.
  Androguard is the documented exception — it is a library — and every step is wrapped
  accordingly.
- **Argument arrays, never a shell string.** A path inside an analysed APK cannot inject
  a command. There is a test that proves it.
- **`defusedxml` for the manifest.** It comes from an untrusted APK and declares entity
  expansions to try. An XXE payload is rejected, not expanded.
- **Walk limits.** Obfuscated APKs carry hundreds of thousands of methods and millions of
  instructions. Unbounded traversal is a denial of service against ourselves, so method,
  string and instruction limits are enforced and hitting one is logged.
- **Local-first.** Nothing leaves the machine in Phase 1. Phase 2's model integration
  requires explicit per-request authorization.
- **Workspace scoping.** Extracted artifacts are written under the project workspace
  only. The API publishes the *name* of each analysed file and redacts the server's
  own directories from its error messages, so a response describes the analysis
  rather than the machine it came from.
- **Untrusted names stay inside the tree.** A class name becomes a path to read,
  and class names come from an analysed APK or from a request. Both backends check
  every part of the name before it becomes a path; a name that fails the check is
  "no such class", not an error page.
- **Bounded inputs.** An upload over the size limit is refused while it streams,
  so it is never held in memory and never written in full. An archive whose
  declared contents are too large is refused from its central directory, before a
  byte of it is decompressed.
- **Bounded backends.** A backend that outlives its timeout takes its whole tree
  down with it — the launcher and the tool it started — so a hung decompiler
  cannot outlive the call that started it.

See [SECURITY.md](../../SECURITY.md) for the reporting process.

## Storage

SQLite with FTS5. Content-addressed project ids (`apk_<sha256[:16]>`) make re-analysis
idempotent: analysing the same APK twice replaces its symbols rather than duplicating
them.

FTS5 queries are built as quoted phrases with doubled quotes, so user input is matched
literally and FTS operators in a search term cannot be injected as query syntax.

## Cross-references

Androguard 4.x removed its xref cache, so DexAtlas recovers call edges by walking
bytecode: scan each method's instructions for an invoke-form opcode, read the target
from its final operand.

That walk is bounded by an instruction limit. On a large APK it is the most expensive
thing DexAtlas does, and it is the first thing to give up on.

## What is deliberately absent

- **Kubernetes, microservices, a distributed database.** SQLite is sufficient until it
  measurably is not.
- **A vector database as a hard dependency.** Exact symbol resolution and cross-references
  answer most questions precisely; semantic retrieval is a supplement, not a prerequisite.
- **A flattening model that turns JADX Java, Smali and a DEX graph into one
  representation.** It would be lossy in exactly the places that matter.

## Layout

```text
src/dexatlas/
├── config/       settings and backend discovery
├── core/
│   ├── models.py   the unified analysis model, provenance, evidence levels
│   ├── ingest.py   validation, hashing, archive inspection
│   ├── storage.py  SQLite schema, symbol tables, FTS5 search
│   ├── evidence.py evidence construction and the level discipline
│   └── pipeline.py Analyzer — the single orchestrator
├── tools/
│   ├── base.py     the Backend interface and subprocess execution
│   ├── jadx/       decompilation and source parsing
│   ├── apktool/    manifest and Smali
│   ├── androguard/ DEX symbol index and bytecode xref walk
│   └── registry.py backend discovery
├── reports/      JSON and Markdown renderers
├── cli/          Typer commands, plus the console-encoding layer
└── api/          FastAPI transport
```

Phase 2 adds `agent/`, `mcp/` and `web/` as new directories. They consume this core; they
do not duplicate it.
