# Architecture diagram

One diagram of how DexAtlas is put together, drawn from the tree as it
stands (`v0.2.0`, plus the workbench screens that shipped with it). The prose
behind each box is in [README.md](README.md) (the pipeline and the failure
rule), [mcp-server.md](mcp-server.md), [agent.md](agent.md) and
[workbench.md](workbench.md); this page is the map, not the explanation.

## The shape of it

```text
                              callers / entry points
 ┌──────────┬──────────────┬──────────────────┬─────────────┬──────────────┐
 │          │              │                  │             │              │
 ▼          ▼              ▼                  ▼             ▼              ▼
 CLI       REST API       MCP server       agent        workbench     your code
 (Typer)   (FastAPI)      (stdio, read-   (library,     (FastAPI +     (Python
 dexatlas  uvicorn        only tools)     Orchestrator)  React SPA)    import)
                                              │             │
                                              │  drives     │  browser over the
                                              │  the loop   │  same read-only tools
                                              ▼             ▼
                                        ┌─────────────────────────┐
                                        │   MCP tool functions    │
                                        │   src/dexatlas/mcp/     │
                                        │   10 read-only tools    │
                                        └────────────┬────────────┘
                                                     │
                        ┌────────────────────────────┼──────────────────┐
                        │                            │                  │
                        ▼                            ▼                  ▼
              ┌──────────────────┐        ┌──────────────┐    ┌────────────────┐
              │  core/           │        │  agent/      │    │  reports/      │
              │  pipeline,       │◄───────│  orchestrator│    │  markdown,     │
              │  storage,        │ reads  │  planner,    │    │  json report,  │
              │  evidence,       │ & write│  verifier,   │    │  coverage      │
              │  call graph      │        │  reporter    │    └───────┬────────┘
              └───────┬──────────┘        └──────┬───────┘            │
                      │                          │                    │
                      ▼                          ▼                    ▼
              ┌──────────────────┐        ┌──────────────┐    ┌────────────────┐
              │  tools/          │        │ model provider│   │  SQLite        │
              │  androguard /    │        │ (OpenAI-     │    │  workspace     │
              │  apktool / jadx  │        │  compatible) │    │  projects ·    │
              │  ToolOutcome =   │        └──────────────┘    │  runs ·        │
              │  result OR error │                            │  evidence      │
              └───────┬──────────┘                            └────────────────┘
                      │
                      ▼
              APK bytes (sample or user upload)
```

## What the diagram says, and does not

- **Five entries, one core.** The CLI, the REST API, the MCP server, the
  agent and the web workbench are five ways in. They share the same
  `Analyzer` pipeline, the same workspace, the same evidence records and the
  same report renderers — the workbench and the API serve the renderer's own
  output, not a second copy of it.
- **The MCP layer is the read-only contract.** The workbench calls the same
  tool functions in-process that the MCP server wraps in stdio; neither adds
  analysis, writes, or a second shape of answer. The server itself needs no
  model provider — it is a tool server.
- **The agent is a client of the tools, and the model is not in charge.** One
  loop: plan, resolve, ask the model, read through the MCP tools, check every
  conclusion against evidence, record a lead or "insufficient evidence",
  report, save state. A model's output is a lead and can never be promoted to
  a finding.
- **A backend failure is a value.** `Backend.run` returns a `ToolOutcome`
  carrying an optional `ToolError`; an APK that defeats jadx still yields a
  manifest, an index and a report that says which steps did not run.
- **Untrusted bytes are parsed in a worker.** The androguard backend parses
  DEX in a separate process with bounded resources, so a malformed file costs
  a recorded error, not the host process (see
  [runtime-isolation.md](runtime-isolation.md)).
- **Not shown:** benchmarks and their harness (see
  [docs/benchmarks/](../benchmarks/comparison.md)) — they read the same
  core through the same tool layer; the demo capture scripts; the Docker
  image, which just packages the CLI and the three backends.
