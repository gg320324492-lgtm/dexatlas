# Phase 2 plan — Agentic Intelligence (`v0.5.0`)

**Written after the Phase 1 source review, against the code that exists.**
The roadmap says this plan is written after the review "so that Phase 2 is planned
against real code rather than assumptions written before any code existed"
([ROADMAP.md](ROADMAP.md)). This is that document.

**Accepted baseline:** `phase1-acceptance-2026-10-21` → `a1e81ce8ae262b84fa06bc5a3afb995fd0238660`
**Phase 1 status:** accepted as a functional static-analysis MVP.

**Inputs:**

| | |
|---|---|
| Review report | [phase1-review-report.md](../reports/phase1-review-report.md) — 6 blocking, 16 important, 12 optional, 9 deferred |
| Maturity assessment | [phase1-maturity-assessment.md](../reports/phase1-maturity-assessment.md) — **5.50 / 10**, the **pre-fix** baseline |
| Deferred findings, in detail | [phase2-issue-list.md](../reports/phase2-issue-list.md) — 8 items, each with two options and a recommendation |

**What the assessment changes about the plan.** The roadmap's Phase 2 section was
written as a vision: five agent roles, an MCP server, a web workbench. The review
found that the **evidence model is already the part that was built for agents** —
`EvidenceKind`, `EvidenceLevel`, a frozen four-field `Provenance`, and an
`EvidenceBuilder` that cannot be constructed without the tool versions. It also
found that **MCP does not exist at all**: no server, no client, no SDK dependency,
no tool definitions — `grep -rn -i mcp src/dexatlas/` returns nothing.

So Phase 2 is not "add agents to a project that lacks them". It is **"expose what
already exists to an agent, and make the parts that were assumed safe actually
safe"**.

**The development principle, which is also the acceptance rule:**

> **Evidence before inference. Correctness before autonomy.**

---

## 1. The milestones

| | Milestone | Version | What it delivers |
|---|---|---|---|
| **M0** | Core contracts & reliability | `v0.2.0-pre` | The analyzer is safe and predictable for programmatic access |
| **M1** | Read-only MCP server | `v0.2.0` | The existing analysis is usable by an agent, as tools |
| **M2** | Single evidence-first agent | `v0.3.0` | Planning, tool calls, verification, recovery, human checkpoints |
| **M3** | Evaluation & benchmarking | `v0.4.0` | Measured quality against baselines, not demonstrations |
| **M4** | Web workbench & portfolio | `v0.5.0` | A product a stranger can understand and a client can evaluate |

**The order is not arbitrary.** M0 exists because M1 would otherwise publish the
defects: an MCP tool that reads `xrefs` inherits a wrong count, and a tool that
resolves a method by name alone returns the wrong overload of a method the agent
is about to reason about. M1 precedes M2 because the orchestration has nothing to
orchestrate without tools. M3 precedes M4 because a workbench built against a
moving API is the most expensive thing to write twice.

**Do not develop the agent and the web front end at the same time.** M1 and M2's
tool contracts have to settle first, or the React pages are written twice.

---

## 2. M0 — Core contracts & reliability (`v0.2.0-pre`)

**Goal:** make the existing analyzer safe and predictable for programmatic agent
access.

### P2-001 · Overload-safe method resolution

**Why it is first.** A method resolved by name alone can return the wrong
overload, and that error travels straight into an agent's answer. Fixing it after
the agent ships costs far more.

**The state of the code.** `Analyzer.method_source_document(project_id, class_name,
method_name)` takes **no descriptor** — the CLI's `source` command and the API's
source endpoints take a class name and a method name, and the first match wins.
The DEX descriptor (`(Ljava/lang/String;)Ljava/lang/String;`) is what
distinguishes the overloads, and the index already stores it in `methods.descriptor`
— it is simply not used for the lookup.

**What to do:**

- Canonical method identifiers built on the **full DEX descriptor**, not the name.
- Update `Analyzer`, the JADX and Smali adapters, the CLI and the API.
- When an exact match is impossible, return **explicit ambiguity information**
  rather than a best guess: which candidates matched, and why the exact one could
  not be chosen.
- Tests for overloaded methods, constructors, and ambiguous decompiled signatures.

**Exit criteria:** no overloaded method silently resolves to the wrong body; the
ambiguity is reported rather than guessed.

### P2-002 · `AnalysisRun` and transactional results

**Why.** The project id is a content hash: the same APK always maps to the same
project. So a re-analysis overwrites the previous one **in place**, and a reader
can see the symbols of one run beside the evidence of another. The Phase 1 review
found the same shape of problem twice — the `evidence` table not being cleared,
and the upload being overwritten — and fixed both by hand. A run identifier
fixes the class of it.

**What to do:**

- An `AnalysisRun` with a unique run id **independent of the APK identity**,
  carrying the tool versions, the input SHA-256, the execution status and the
  completeness of the run.
- Each run's results are staged separately and published only as a **committed
  snapshot**.
- No stale evidence after a re-analysis or an interrupted run.
- Schema migration, and tests for legacy workspaces.

**Exit criteria:** no cross-run symbols or evidence are visible; an interrupted
run leaves the previous complete run intact.

### P2-003 · `CallSite` and `CallEdge` semantics

**Why — and a correction to this plan's earlier draft.** The first draft of this
plan proposed giving `xrefs` the primary key `(project_id, caller, callee, kind)`.
**That is wrong**, and it is wrong in a way that loses data: the same caller
reaching the same callee from two different bytecode offsets is two *call sites*,
and a unique key over the pair collapses them into one row. The call sites are
the finer-grained truth, and a de-duplicated table cannot recover them.

**What to do instead:**

- Distinguish **`CallSite`** (one concrete call location: DEX identity, caller,
  **instruction offset**, invocation kind, callee) from **`CallEdge`** (the
  aggregated relationship between two methods).
- A call edge is *derived* from its call sites — never the other way round.
- Every count states which of the two it means: **sites** or **edges**. The Phase 1
  review already found one report conflating them (`cross_references` counted
  calls while `cross_references_with_evidence` counted methods); that conflation
  is what this issue removes at the source.
- Provenance survives the migration.

**Exit criteria:** the number of call sites and the number of call edges are both
available, both correct, and never used for one another.

### P2-004 · Verified evidence invariants

**Why.** The Phase 1 review found that the evidence level was a **convention**
rather than a mechanism: nothing stopped a caller from recording a behaviour as
verified, and the report renders every verified record as "deterministically
established by an analysis tool". A validator now refuses `BEHAVIOUR + VERIFIED`
— but that is one rule, not a proof. The acceptance argument is:

- Separate contracts for **deterministic observations** (a tool read something)
  and **model-generated claims** (a model said something).
- A verified code observation requires **validated source provenance** — the
  locator has to resolve, and it has to resolve inside the analysis.
- A **locator resolver** that confirms source membership and location, so
  "verified" is backed by a resolution rather than by a string that looks right.
- **Model output can never create a verified observation on its own.**
- Negative tests for empty, stale, mismatched and fabricated provenance.

**Exit criteria:** invalid provenance cannot produce a verified code finding.

### P2-005 · Runtime isolation and lifecycle

**Why.** Three things in the current tree are not yet true for an embedded
service, and an agent is an embedded service:

- The Androguard adapter **removes loguru's global handlers** and does not
  restore them. A library that removes *your* logging is a library that breaks
  its host.
- Androguard parses untrusted DEX **in the service process**. A malformed DEX
  that takes the interpreter down takes the service with it.
- The upload retention, cleanup and cancellation behaviour is undefined, and the
  workspace grows.

**What to do:**

- Stop modifying the host application's global loguru handlers.
- Run the untrusted DEX parsing in an **isolated worker**.
- Bound runtime, memory and temporary disk where the platform allows it.
- **One active writer per APK/run workspace** — the concurrency defect the
  Phase 1 review found (`#4`) is a precondition for the agent, not a phase-2
  extra.
- Define upload retention, cleanup and cancellation.
- Keep the existing local-first security boundary.

**Exit criteria:** parallel analyses have deterministic, isolated outcomes; the
host application's logging is untouched.

### M0 exit criteria

- All the critical correctness tests pass.
- No cross-run symbols or evidence are visible.
- No overloaded method silently resolves to the wrong body.
- Invalid provenance cannot produce a verified code finding.
- Parallel analyses have deterministic, isolated outcomes.
- Existing public CLI/API compatibility is **either preserved or explicitly
  versioned** — never silently changed.
- Every bug fix carries a regression test **that fails on the previous
  implementation**.

---

## 3. M1 — Read-only MCP server (`v0.2.0`)

**Goal:** make DexAtlas usable as an evidence-aware tool provider for AI agents.

### The package

`src/dexatlas/mcp/`

```
server.py            the server and its transport
schemas.py           the tool schemas
tools/projects.py    list_projects, get_project_status, get_manifest
tools/symbols.py     search_symbols, get_class_source, get_method_source
tools/references.py  find_callers, find_callees
tools/evidence.py    get_evidence, resolve_locator
tools/search.py      full-text search over the index
security.py          what the tools may and may not do
```

### The tools

| Tool | Responsibility |
|---|---|
| `list_projects` | List local analysis projects |
| `get_project_status` | Read the analysis status and whether the index is complete |
| `get_manifest` | The parsed manifest |
| `search_symbols` | Search the indexed classes, methods and strings |
| `get_class_source` | Java or Smali, with provenance |
| `get_method_source` | **An exact method** — by descriptor, not by name (P2-001) |
| `find_callers` | The references to a method |
| `find_callees` | The methods a method calls |
| `get_evidence` | An evidence record and its source references |
| `resolve_locator` | Resolve a provenance locator into a bounded source excerpt |

Begin with the local **stdio** transport. Remote access is a separate deployment
decision, not a Phase 2 default.

### Requirements

- **Reuse the existing `Analyzer` and `Store`.** No duplicated analysis logic —
  that is the whole point of the project.
- Pydantic input and output schemas.
- Explicit pagination and result-size limits.
- Structured error and completeness information: a missing tool, a missing source
  and a truncated analysis each say which they are.
- **No arbitrary shell execution, no unrestricted file reads, no APK mutation.**
- Treat the APK's strings and decompiled code as **untrusted data, not
  instructions** — the contents of an analysed APK must never be able to steer the
  agent. This is a security property of the tool layer, and it needs a test.
- A runnable MCP client example, and integration tests.

### M1 exit criteria

- Every exposed tool is tested against the **first-party** fixtures.
- A caller can resolve every returned evidence record to the correct source.
- Missing tools, missing sources and truncated analyses return explicit
  structured results.
- The MCP server runs **without any model provider** — it is a tool server, and
  a tool server that needs a model is not a tool server.
- The README carries working setup instructions.

---

## 4. M2 — Single evidence-first agent (`v0.3.0`)

**Goal:** one reliable orchestrator, not a collection of loosely coordinated
autonomous agents.

### The package

`src/dexatlas/agent/`

```
orchestrator.py       the loop
planner.py            turning a question into a bounded plan
tool_executor.py      calling the MCP tools
evidence_verifier.py  checking that a conclusion has evidence
state.py              the task state machine
providers/            the model endpoints
reporter.py           filling the existing report format
```

### The workflow

1. Accept an authorised analysis question.
2. Resolve the APK project **and the analysis-run identity**.
3. Plan a bounded series of tool calls.
4. Execute read-only tools through MCP.
5. Retrieve and validate the supporting source evidence.
6. Identify contradictions, ambiguity and incomplete coverage.
7. Produce conclusions with explicit confidence and limitations.
8. Save the task state, and offer a resumable result.

### Two corrections to the roadmap's original version

- **The Evidence Verifier is not a new role — it is `EvidenceBuilder`.** The
  mechanism that makes a tool's output a finding already exists, and the
  orchestration routes its conclusions through it rather than inventing a second
  path. A model's output is `LEAD`; only a tool's output can be `VERIFIED`.
- **The Report Builder is `reports/markdown.py` and `reports/json_report.py`.**
  The report format is the deliverable and it is already written; Phase 2 fills
  it in rather than replacing it.

The genuinely new machinery: the task state machine, failure retry, the iteration
and token budgets, resume-after-interrupt, and the human confirmation checkpoints.

### Features

- An OpenAI-compatible model endpoint, and a **second independently tested**
  provider or a local model interface.
- Per-task token, iteration and execution budgets.
- Tool-call logging, retries and circuit breakers.
- Persistent task state and resume-after-interrupt.
- User-visible progress, with **no unsupported completion claims**.
- Explicit user approval before sensitive operations.
- Structured reports that separate verified facts, leads and insufficient
  evidence.

### M2 exit criteria

- The agent completes a fixed task suite without arbitrary system access.
- Results carry resolvable evidence ids and locators.
- Timeouts, backend failures and model failures are all tested.
- **It does not interpret instructions found inside the APK as commands.**
- The user can inspect and reproduce every tool-driven conclusion.

---

## 5. M3 — Evaluation and benchmarking (`v0.4.0`)

**Goal:** measured quality, not impressive demonstrations.

### The benchmark set

At least **30 tasks** over the first-party samples and legally reusable
fixtures, covering:

- manifest interpretation
- component declarations
- cross-reference tracing
- string and resource search
- **method overloads**
- multi-DEX analysis
- ambiguity in decompiled code
- partial results and backend failure
- source provenance verification
- questions that **cannot** be answered

Each task carries an independently checked expected answer.

### The baselines

| | |
|---|---|
| **A** | An LLM with decompiled source-text retrieval |
| **B** | An LLM with structured symbol search and call references |
| **DexAtlas agent** | Structured tools, provenance resolution, completeness awareness, evidence verification |

The same model, the same input sample and comparable budgets across the three.

### The metrics

Correct-answer rate · evidence-grounding rate · **unsupported-assertion rate** ·
false-positive rate · tool-call success rate · recovery rate · token consumption ·
execution duration.

### M3 exit criteria

- At least 30 tasks with auditable expected answers.
- **Every reported metric can be regenerated by a script in the repository.**
- At least two model/provider configurations actually tested.
- Tool-execution success reaches the 95% target on the specified benchmark, **or
  the shortfall is disclosed**.
- Every externally reported code conclusion is source-traceable or explicitly
  marked unverified.
- **A comparison never claims an improvement the measurements do not support.**

---

## 6. M4 — Web workbench & portfolio (`v0.5.0`)

**Goal:** a product a new user, a GitHub reader and a potential client can
understand and evaluate.

### The front end

React + TypeScript + Vite, a maintained code-editor component, a lightweight
graph viewer.

### The screens

1. Project dashboard with backend status
2. APK upload and analysis progress
3. Package / class / method explorer
4. Java & Smali source viewer with source-location links
5. Call graph and cross-reference navigation
6. Agent workspace: planned and completed operations
7. Evidence viewer, separating observations from hypotheses
8. Benchmark and report export

### Developer experience

- Docker-based local setup
- Stable REST / OpenAPI schemas
- An MCP integration guide
- An example Python client
- English and Chinese documentation
- Architecture decision records
- A contributing guide, issues, and a versioned changelog

### Public assets

- A 60–90 second end-to-end demo
- A technical architecture diagram
- At least two complete case studies
- A public benchmark summary
- A downloadable example analysis report
- An Upwork-oriented portfolio description

### M4 exit criteria

- A new user can install and run the documented system.
- Upload → analysis → question → evidence navigation → report export works end
  to end.
- Tests pass on the supported platforms and backend configurations.
- Known security and reliability limitations are **disclosed**.
- **No unverified feature appears as a completed feature in the README.**
- Every model-dependent capability can be disabled without breaking the static
  analysis core.

---

## 7. The rules this plan is run under

- One issue produces one reviewable PR wherever that is practical.
- Every bug fix carries a regression test **that fails on the previous
  implementation**.
- **No production claim without a runnable test, a benchmark, or a documented
  manual verification.**
- Published git tags are not edited.
- REST endpoints stay backward-compatible where that is practical.
- Readable code and small interfaces over premature abstractions.
- Third-party APKs, secrets and sensitive customer data stay out of the
  repository.
- **A milestone is advanced only after source review and acceptance.**

---

## 8. What this plan does not cover

- **Calendar dates.** The estimates are engineering effort, and this project has
  no history of estimating its own work — this is the first plan written against
  a code base rather than an idea.
- **The commercial APK benchmark.** It needs samples this project does not have
  ([phase1-review-report.md §7](../reports/phase1-review-report.md)).
- **Windows and macOS.** Every platform difference in this project's history was
  found on Linux. The gates run on Linux; the local verification loop is WSL.
- **What Phase 3 looks like.** The roadmap's Phase 3 section stands; it will need
  the same treatment when its time comes.
