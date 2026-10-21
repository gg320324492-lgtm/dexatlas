# Phase 2 plan — Agentic Intelligence (`v0.5.0`)

**Written after the Phase 1 source review, against the code that exists.**
The roadmap says this plan is written after the review "so that Phase 2 is planned
against real code rather than assumptions written before any code existed"
([ROADMAP.md](../roadmap/ROADMAP.md)). This is that document.

**Inputs:**

| | |
|---|---|
| Review report | [phase1-review-report.md](../reports/phase1-review-report.md) — 6 blocking, 16 important, 12 optional, 9 deferred |
| Maturity assessment | [phase1-maturity-assessment.md](../reports/phase1-maturity-assessment.md) — **5.50 / 10** across six weighted dimensions |
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
safe"**. Two of the roadmap's assumptions do not survive contact with the code:

1. The roadmap assumed the agent layer would sit on a stable core. The review
   found **nine important defects in the core itself**, four of which are still
   open (`#4`, `#7`, `#11`, `#12`). The MCP server would expose them.
2. The roadmap's evidence separation — "an LLM's opinion that code looks risky is
   never promoted to a confirmed vulnerability" — was, at the time of the
   assessment, **a convention and not a mechanism**: nothing stopped a caller
   from constructing `Evidence(kind=BEHAVIOUR, level=VERIFIED)`. It is now a
   validator on the model, and Phase 2's model output lands on `LEAD`.

---

## 1. The issues

### Stage 0 — Phase 1 debt (no schema change, no interface change)

These are open findings from the review. They are cheap, they are independent,
and **they are the debt a Phase 2 would otherwise inherit and expose**.

| # | Issue | Cost | Why now |
|---|---|---|---|
| **#12** | The uploaded APK is never deleted; the workspace grows forever | 1 day (with X1, already done) | The upload is now stored under its content hash, so "delete the copy" is unambiguous |
| **#11** | loguru's global handler is removed and never restored — a library that removes *your* logging | 0.5 day | `logger.disable("androguard")` / `enable()` instead of `logger.remove()` |
| **F8** | 10 dead functions across the tree; ruff cannot find dead functions | 1–2 days | Configure vulture (`--ignore-decorators`, `--ignore-names`, `[tool.vulture]`), delete what it finds, and make its exit code a CI gate. **It under-reports** — names shadowed by locals or enum members are invisible to it — so the tool is a signal, not a proof. |
| **#14/#15** | 25 places where a docstring or comment says one thing and the code does another | 2–3 days | The five high-severity ones are fixed; these are the middle and low ones. Each fix is either "the code was right, the words were wrong" or "the words were right, the code was wrong" — and the second kind must not be resolved by weakening the words. |

### Stage 1 — Storage and concurrency (schema changes)

| # | Issue | Cost | Depends on |
|---|---|---|---|
| **#7** | `xrefs` has no primary key: the same call edge can be written twice, and `reference_count` counts *calls*, not *edges* | 1–2 days | — |
| **#4** | Concurrent analyses of one APK share a workspace directory and write over one another | 2–3 days | X2 (done) |

**#7** is a schema change: primary key `(project_id, caller, callee, kind)`, and
`_migrate` drops and recreates the table — the same shape `resources` already
uses for a changed primary key. It changes what `reference_count` means, so the
execution report, the provenance document and the API's xrefs endpoint all change
with it.

**#4** has two designs (see [phase2-issue-list.md §3](../reports/phase2-issue-list.md)):
a per-run directory that is swapped into place on success, or a file lock that
serialises analyses of one project id. **Recommendation: the run directory**, with
the lock as optional hardening. The run directory is what makes the analysis
*resumable*, which Phase 2 wants anyway.

### Stage 2 — The MCP surface

This is the roadmap's Phase 2 centre of gravity, and it is the dimension the
assessment scored **4 / 10 with a 20% weight** — the weakest dimension, and the
one the project has promised most about.

| Capability | What it means here | Notes |
|---|---|---|
| **MCP server** | Expose DexAtlas's own normalised analysis tools: index a project, query classes/methods/xrefs/evidence, search, read a source document | The tools are the REST API's resources, re-expressed as tools. **No new analysis logic** — the point is that an agent gets the same evidence a human does. |
| **Tool schemas** | Every tool has a schema a model can call, with the *locator* format documented | The `locator` shape (`<tool>:<place>`) is already the portability contract; it becomes the tool's return format. |
| **Evidence in the response** | A tool that returns a conclusion returns its evidence ids and provenance with it | This is the differentiator the roadmap names, and the code already supports it: `Provenance` is frozen and `EvidenceBuilder` cannot be built without tool versions. |
| **Read-only by default** | Tools read the workspace; mutating operations are out of scope | The roadmap says the model never gets arbitrary shell execution. The API already has no such capability, so this is a property to preserve, not to build. |

**What MCP must not do:** bypass the evidence model. A tool that returns "this
looks risky" without a provenance has broken the project's premise, and the
`EvidenceLevel` validator exists to stop exactly that.

### Stage 3 — Agent orchestration

The roadmap's five roles (Planning, Code Analyst, Tool Executor, Evidence Verifier,
Report Builder) are a reasonable decomposition, but the review says the plan
should be written against real code. Two corrections:

- **The Evidence Verifier is not a new role — it is `EvidenceBuilder`.** The
  mechanism that makes a tool's output a finding already exists, and Phase 2
  should route every conclusion through it rather than inventing a second path.
  A model's output is `LEAD`; only a tool's output can be `VERIFIED`.
- **The Report Builder is `reports/markdown.py` and `reports/json_report.py`.** The
  report format is the deliverable, and it is already written. Phase 2 builds the
  thing that fills it in, not a new format.

The genuinely new machinery: a task state machine, failure retry, an iteration
budget, resume-after-interrupt, and human confirmation checkpoints.

### Stage 4 — Web workbench

React + TypeScript against the FastAPI backend. **Deferred until the API is
typed and paginated** (Stage 1) — a workbench built against untyped endpoints
has to be rewritten when they gain response models.

### Deferred to Phase 3

| Item | Why |
|---|---|
| Vector retrieval / heavy RAG | The roadmap already says these are not hard dependencies; code search and precise symbol resolution are the primary channels, and both exist |
| Dynamic instrumentation | Needs its own permission model and a threat model; not a `v0.5.0` item |
| Real commercial APK benchmarking | Needs samples this project does not have |

---

## 2. Implementation order

```
Stage 0  Phase 1 debt ──────────────────────────────────  ~5 days
         #12 · #11 · F8 · #14/#15
         (independent; parallelisable; no schema change)
                    │
                    ▼
Stage 1  Storage & concurrency ─────────────────────────  ~5 days
         #7 xrefs primary key  (schema change: SCHEMA_VERSION + _migrate)
         #4 per-run workspace directory
         (both change what the database holds; do them before anything
          exposes the schema)
                    │
                    ▼
Stage 2  MCP server ────────────────────────────────────  ~2 weeks
         tools over the now-stable resources
         + a locator round-trip test per tool
                    │
                    ▼
Stage 3  Agent orchestration ───────────────────────────  ~3 weeks
         state machine · retry · resume · checkpoints
         + the ≥20-task human-verified task set
                    │
                    ▼
Stage 4  Web workbench ─────────────────────────────────  ~3 weeks
         (only after the API is typed and paginated)
```

**The order is not arbitrary.** Stage 0 and Stage 1 exist because Stage 2 would
otherwise publish the defects: an MCP tool that reads `xrefs` inherits #7's wrong
count, and an MCP server that starts analyses inherits #4's collision. Stage 2
precedes Stage 3 because the orchestration has nothing to orchestrate without
tools, and Stage 4 is last because a workbench written against a moving API is
the most expensive thing to write twice.

**Rough total: ~3 months for `v0.5.0`.** That is a bigger Phase 2 than the
roadmap's exit targets imply, and the difference is Stage 0 and Stage 1 — nine
days of debt that the roadmap did not know about.

---

## 3. Interface changes

Everything below is a change to a contract somebody outside this repository may
depend on. Each one needs a version note in `CHANGELOG.md`.

### 3.1 Storage (`src/dexatlas/core/storage.py`)

| Change | Migration |
|---|---|
| `xrefs` gains `PRIMARY KEY (project_id, caller, callee, kind)` | `SCHEMA_VERSION` 3 → 4; `_migrate` drops and recreates the table, the way `resources` already does |
| `reference_count` changes meaning: it counts **edges**, not calls | The execution report, the provenance document and the API's xrefs endpoint all change with it |

### 3.2 REST API (`src/dexatlas/api/app.py`)

| Change | Notes |
|---|---|
| The 9 untyped endpoints gain response models | `ProjectResponse` and friends already exist; the rest are bare `dict[str, Any]` |
| The endpoints that return lists gain pagination | `limit` exists on some and not all; the xrefs endpoint has no bound at all |
| `GET /projects/{id}/report?format=json` keeps its shape | The `duration_seconds` field was added in Phase 1 and is `null` for workspaces analysed before it |
| **No endpoint is removed or renamed** | Phase 2 is additive on the HTTP surface |

### 3.3 CLI (`src/dexatlas/cli/main.py`)

| Change | Notes |
|---|---|
| New `dexatlas evidence` subcommand | Query evidence by kind, level, or provenance; `--json` for machine output |
| `dexatlas analyze --json` is unchanged | The JSON report shape is a contract |

### 3.4 MCP (new)

| Surface | Shape |
|---|---|
| Tools | One per read-only REST resource; each returns the resource plus the evidence ids and provenance behind it |
| Tool schemas | Explicit input schema; the output carries `locator` strings that resolve to a file in the workspace |
| Errors | A tool failure is a `ToolError`-shaped value, not an exception the model has to interpret |

### 3.5 The evidence model (`src/dexatlas/core/models.py`)

| Change | Notes |
|---|---|
| `EvidenceLevel.LEAD` gets its first producer | Model output. The validator already refuses `BEHAVIOUR + VERIFIED`, so a model cannot promote itself |
| `EvidenceKind.CODE_LOCATED` and `BEHAVIOUR` get producers | `CODE_LOCATED` when a conclusion points at a specific line; `BEHAVIOUR` for a model's observation |
| **The model does not change shape** | `EvidenceKind`, `EvidenceLevel` and `Provenance` are already the contract the tools will speak |

---

## 4. Test plan

### 4.1 For every issue: a test that is red before the fix

The project's own rule, and the one the review enforced: **not "the tests pass"
but "revert the fix and the test goes red"**. The Phase 1 round verified 21 such
breakage experiments; Stage 0 and Stage 1 each carry one.

### 4.2 For the MCP tools: each tool runs against a real fixture

A tool test that only checks the schema is worthless. Each tool gets:

- a call against the bundled demo APK (no download),
- a call against a fixture that **fails** — the tool has to return the failure as
  a value, not an exception,
- a check that the returned locators resolve to files inside the workspace.

### 4.3 For the agent: a task set with human-verified answers

The roadmap's exit target is "≥20 tasks with human-verified answers". This is the
first thing in the project that **cannot be verified automatically**, and it is
the one the roadmap cares about most. The protocol:

1. 20+ tasks over the bundled samples, each with a stated expected answer.
2. Every answer checked by a human against the evidence, not against the model.
3. The task set is a **fixture in the repository** — it is a test, not a demo.
4. It is run on every model provider that is claimed to work.

### 4.4 For the claims: the "no false claims" guard is extended

`tests/test_docs.py` already refuses to let the README claim features that are not
shipped ("MCP server is shipped"). **Phase 2 must extend that guard** to the
MCP server and the agent: the moment a tool exists, the guard has to know what
"exists" means, or it will start passing on a claim that is only half true.

### 4.5 The gates that run every time

| Gate | What it protects |
|---|---|
| `pytest` under three backend configurations | The three configurations are the product's promises |
| `refresh-report-figures.py --check` | The report's numbers describe the tree |
| `check-doc-citations.py` | The documents' line references still say what they say |
| `check-version-claims.py` | The published state matches the repository |
| vulture's exit code | Dead code stays dead |
| A **Linux** run | Two of the three platform defects in this project's history were Windows-only |

---

## 5. Acceptance criteria

### 5.1 The roadmap's Phase 2 exit targets, measured

| Metric | Target | How it is measured |
|---|---|---|
| Agent task set | ≥20 tasks, human-verified answers | The fixture in §4.3; the answers are checked by a human and committed |
| Tool execution | ≥95% success rate on tool tasks | Measured over the task set |
| Evidence | 100% of externally shown conclusions traceable | A checker walks every conclusion in every produced report and resolves its provenance |
| Error recovery | Handles timeouts, tool crashes and model failures | The task set includes the failure cases; each has a stated expected outcome |
| Model coverage | ≥2 providers verified | The task set is run against each |
| User experience | Complete loop: upload APK → read the analysis report | The loop is a test, not a demo |
| Public showcase | ≥2 screen recordings and 1 downloadable sample report | Human work, checked by eye |

### 5.2 The criteria this review added

The review found that the project's failures were all of one kind: **an output
that was self-consistent and about the wrong thing**. So Phase 2's own exit
criteria are about that:

| Criterion | What it rules out |
|---|---|
| Every evidence record a tool returns has a locator that resolves to a file in the workspace | A conclusion about a file that is not there |
| No tool output can carry a level above `VERIFIED` without a tool behind it | A model's opinion published as a finding |
| Every number in every report can be reproduced by a command in the repository | A number nobody can check |
| The MCP server refuses to start against a workspace whose schema it does not understand | A tool reading a table that means something else |
| `grep -rn -i mcp src/dexatlas/` returns something, **and** the README's claim about it is true | The failure mode of this project: shipping a promise |

### 5.3 What "done" means for the debt

Stage 0 and Stage 1 are done when:

- every issue in §1 has a merged commit **and** a test that was red before it;
- the 21 defect classes in [status.md §6](../status.md) each either have an
  automated guard or are listed in the roadmap as accepted;
- the maturity assessment is re-run and its six scores are published alongside
  the previous ones.

---

## 6. What this plan does not cover

- **A timeline in calendar dates.** The estimates are effort, and the project has
  no history of estimating its own work — this is the first plan written against
  a code base rather than an idea.
- **The commercial APK benchmark.** It needs samples this project does not have
  ([phase1-review-report.md §7](../reports/phase1-review-report.md)).
- **Windows and macOS.** Every platform difference in this project's history was
  found on Linux. The gates above run on Linux; the local verification loop is
  WSL.
- **What Phase 3 looks like.** The roadmap's Phase 3 section stands; it will need
  the same treatment when its time comes.
