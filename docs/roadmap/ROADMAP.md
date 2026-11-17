# DexAtlas Roadmap

> **From APK to Evidence — Powered by AI Agents.**
> An open-source, evidence-first Android reverse engineering and mobile application analysis platform.

This document is the working contract for how DexAtlas grows. It is a plan, not a
promise of features — the README describes what actually ships, this file describes
what comes next.

- **Current phase:** Phase 2 delivered; M4 source review and acceptance passed
  on 2026-11-14. Phase 3 is under way: M5 and M7 are complete, M6 and M8 are
  partly done, M9 materials are drafted but unpublished, and M10 has not
  started. Per-milestone evidence is in [§3.4](#34-progress-2026-11-15); see
  [current status](../status.md) and the [Phase 3 plan](phase3-plan.md).
- **Plan version:** 2026-11-15 (Phase 3 scope revision; prior phase history retained)
- **Owner:** @gg320324492-lgtm
- **Review protocol:** see [`Review Protocol`](#review-protocol). Every phase ends with a
  source review, and the next phase's issue list is written from the review, not from
  this document.

---

## Positioning

DexAtlas is an **evidence-first Android analysis platform**, not an AI wrapper around
JADX. The ordering matters:

1. **Phase 1 works with every LLM switched off.** Decompilation, indexing, search and
   reporting must stand on their own. Many "AI agent" projects have an unreliable
   substrate; ours will not.
2. **Differentiation lives in orchestration, evidence and recovery** — unified tool
   interfaces, evidence linkage, resumable tasks, measurable analysis quality — not in
   re-inventing decompilation. JADX, Apktool, Androguard and Ghidra already do that
   better than we will.
3. **Security boundaries are product design**, not an afterthought: local-first,
   read-only by default, explicit opt-in for anything that leaves the machine or
   mutates state.
4. **Usability outranks star count.** A stranger who can install it, run it and get a
   real report in ten minutes is worth more than ten more features.

### Legal and ethical boundary

DexAtlas analyses applications the operator **owns or is authorized to assess**.
Shipping it must never depend on evading third-party protection mechanisms,
extracting unauthorized data, or reproducing proprietary application code. See
[`SECURITY.md`](../../SECURITY.md) and `Intended Use` in the README.

---

## Phase overview

| Phase    | Version   | Theme                  | Outcome                                                       |
| -------- | --------- | ---------------------- | ------------------------------------------------------------- |
| Phase 1  | `v0.1.0`  | Functional Foundation  | ✅ Shipped 2026-10-14                                        |
| Phase 1  | `v0.1.1`  | Foundation Hardening   | ✅ Shipped 2026-10-19                                        |
| Phase 1  | `v0.1.2`  | Acceptance Checklist  | ✅ Shipped 2026-10-20                                        |
| Phase 1  | `v0.1.3`  | Evidence That Points Back | ✅ Shipped 2026-10-20                                   |
| Phase 2  | `v0.2.0`  | Agentic Intelligence   | ✅ Shipped 2026-11-14 — M0–M3 + the workbench; M4 review passed 2026-11-14 |
| Phase 3  | `v1.0.0`  | Production-Ready       | Extensible, deliverable, maintainable platform with real users  |

**Promotion rule:** a phase is complete when its exit checklist passes *and* the source
review raises no blocking findings. Promotion is not a calendar event.

Phase 1 shipped on 2026-10-14, `v0.1.1` followed on 2026-10-19 with the fixes that the
Phase 1 review work surfaced, `v0.1.2` on 2026-10-20 with the five self-built test
APKs and the demo video the exit checklist asks for, and `v0.1.3` the same day with
cross-references becoming evidence, locators that travel with the report, and the
documentation checked against the code it describes. Its exit checklist now reads in the
plan's own words, and the items behind it exist; the source review is still outstanding
and is what gates Phase 2.

---

## Phase 1 — Functional Foundation (`v0.1.0`)

**Goal:** complete a reliable Android APK static analysis pipeline with no dependency on
any language model.

### 1.1 Core capabilities

| Module            | Content                                             | Priority |
| ----------------- | --------------------------------------------------- | -------- |
| APK ingestion     | File validation, SHA-256, package metadata parsing  | P0       |
| JADX integration  | Java pseudocode, class/method/field extraction       | P0       |
| Apktool integration | Manifest, resources, Smali analysis               | P0       |
| Androguard integration | DEX metadata, method refs, call relations      | P0       |
| Code search       | Class, method, string and signature search           | P0       |
| Unified analysis model | Normalize results across tools to one JSON shape | P0       |
| CLI               | Typer entry point, run analysis, export results      | P0       |
| REST API          | FastAPI task submit and query endpoints              | P0       |
| Report export     | JSON and Markdown                                    | P1       |
| Engineering       | Logging, error handling, caching, base tests         | P0       |

> **Design note.** JADX and Apktool outputs are *kept as-is*, not flattened into one
> pseudocode dialect. What gets unified is the index and metadata interface — not the
> representation. Methods JADX cannot decompile reliably are flagged with an error and
> retain a fallback path to Smali.

### 1.2 Recommended stack

| Layer        | Choice                                  |
| ------------ | --------------------------------------- |
| Language     | Python 3.12+                            |
| API          | FastAPI + Pydantic                      |
| CLI          | Typer                                   |
| Dependencies | `uv`                                    |
| Storage      | SQLite + local files                    |
| Search       | SQLite FTS5                             |
| Backends     | JADX, Apktool, Androguard               |
| Quality      | pytest, ruff, mypy                      |
| CI           | GitHub Actions                          |
| Deployment   | Docker, local-first                     |

No Kubernetes, no microservices, no distributed database at this stage.

### 1.3 The critical path

```
APK ingest → hash + validate → task scheduler
    ├─ JADX         → Java pseudocode
    ├─ Apktool      → Manifest / resources / Smali
    └─ Androguard   → DEX metadata / xrefs
              ↓
      unified symbol index
              ↓
   search / method-reference query
              ↓
       evidence linkage
              ↓
    JSON / Markdown report
```

The externally stable tool interface (a DexAtlas API, not a passthrough to any one
third-party tool):

```text
analyze_apk(apk_path)
get_manifest(project_id)
list_classes(project_id)
get_class_source(project_id, class_name)
get_method_source(project_id, method_id)
find_method_references(project_id, method_id)
search_code(project_id, keyword)
export_report(project_id, format="markdown")
```

**Every result records** its source tool, that tool's version, the project hash, and the
code location it came from. A finding without a location is not a finding.

### 1.4 Exit checklist

Last updated 2026-10-20. See [`CHANGELOG.md`](../../CHANGELOG.md) for the full list.

The eight items are the Phase 1 acceptance checklist, in the original plan's wording.
An earlier version of this file paraphrased them — "verified against test APKs" for
"five **self-built** test APKs", and "demo recording" for "demo **video**" — and then
ticked every box. The wording was doing the work the items were supposed to do. This
version keeps the original phrasing so the ticks mean what they say.

- [x] Import and index pipeline verified against **five self-built test APKs**
      (under [examples/](../../examples/demo-app), each built from committed smali
      sources and rebuildable with `scripts/build-test-apks.sh`: a general one, a
      two-dex one, an obfuscated one, a strings-heavy one, and one with an interface
      hierarchy)
- [x] JADX, Apktool and Androguard all callable, with failures handled not crashed on
- [x] CLI and REST API run the same analysis core
- [x] Classes, methods, references and evidence locations are queryable
- [x] JSON and Markdown export supported
- [x] Unit tests plus end-to-end tests; **coverage above the 80% target on first-party
      code** — the current figure is in
      [the execution report](../reports/phase1-execution-report.md)
- [x] GitHub Actions green on Python 3.12 and 3.13
- [x] Installation guide, every command verified against a fresh clone
      ([docs/install.md](../install.md))
- [x] Architecture documentation ([docs/architecture/README.md](../architecture/README.md))
- [x] `v0.1.0` release published 2026-10-14
- [x] A demo **video** ([docs/assets/demo.mp4](../assets/demo.mp4)), encoded from the
      same frames as the GIFs in the README, so the two cannot drift apart
- [x] `v0.1.1` release published 2026-10-19 — Foundation Hardening, fixing the Smali
      fallback that had never worked for any APK
- [x] `v0.1.2` release published 2026-10-20 — Acceptance Checklist: the five
      self-built test APKs and the demo video
- [x] `v0.1.3` release published 2026-10-20 — Evidence That Points Back:
      cross-references as evidence, portable locators, and a checked document

**Phase complete means:** a stranger follows the README, installs DexAtlas on a clean
machine, analyses a bundled authorized test APK, and gets a reproducible structured
report. That is worth more than supporting ten more models in v0.1.

A stranger can today clone, install, analyse the bundled demo application and read a
report, following the README alone. What remains is the source review. Tracked in
[issue #1](https://github.com/gg320324492-lgtm/dexatlas/issues/1).

### 1.5 Issue backlog (`v0.1.0` milestone)

The eight tasks that planned Phase 1. Seven are complete; their issue files are kept
under [`.github/issues/v0.1.0/planned/`](../../.github/issues/v0.1.0/planned/) as a
record of the design decisions behind each piece, rather than left open on GitHub as
work that is not outstanding.

| #    | Task                                                      | Status      |
| ---- | --------------------------------------------------------- | ----------- |
| 001  | Initialize project structure, CI and developer tooling    | Complete    |
| 002  | Implement APK ingestion and metadata extraction            | Complete    |
| 003  | Integrate JADX decompilation backend                       | Complete    |
| 004  | Integrate Apktool and Smali navigation                     | Complete    |
| 005  | Integrate Androguard and symbol indexing                  | Complete    |
| 006  | Build unified analysis API and CLI                         | Complete    |
| 007  | Implement evidence-based report generation                 | Complete    |
| 008  | Add reproducible fixtures, tests and documentation         | Partly      |

Live Phase 1 tracking: [issue #1](https://github.com/gg320324492-lgtm/dexatlas/issues/1).

Phase 2's issues get written **after** the Phase 1 source review, so that Phase 2 is
planned against real code rather than assumptions written before any code existed.

---

## Phase 2 — Agentic Intelligence (`v0.2.0`)

**Entry condition:** Phase 1 exit checklist passing and source review complete.

**Goal:** move from automated tools to an assistant that plans, calls tools, verifies
evidence, and recovers from failure.

> **Status: delivered.** All five milestones shipped with v0.2.0 (2026-11-14);
> M4 passed its source review and acceptance the same day
> ([review report](../reports/m4-review.md)). Phase 3 planning is in
> [phase3-plan.md](phase3-plan.md).

> **Positioning.** JADX-MCP and JADX-AI-MCP already let a model read decompiled code.
> "JADX + ChatGPT" is therefore not a differentiator. DexAtlas differentiates on
> **multi-tool coordination + evidence-first output + resumable tasks + measurable
> analysis quality.**

> **The plan is written.** The source review is complete, so Phase 2 is planned
> against the code that exists rather than against the assumption that it does
> not: **[Phase 2 plan](phase2-plan.md)** — the issues, the implementation order,
> the interface changes, the test plan and the acceptance criteria.
> It opens with two stages of debt the review found and this section did not know
> about, and it corrects two assumptions below: the evidence model is already
> built, and MCP does not exist at all.

### 2.1 Agent orchestration

Start with **one primary agent with explicit internal roles**, not a dozen independent
agents:

| Role                    | Responsibility                                  |
| ----------------------- | ----------------------------------------------- |
| Planning Agent          | Understand the question, split it, pick tools   |
| Code Analyst            | Call-chain and behavioural analysis             |
| Tool Executor           | Invoke MCP / CLI / API adapters                 |
| Evidence Verifier       | Check symbol and reference grounding            |
| Report Builder          | Assemble conclusions into a report              |

**Persistent analysis state:** task status, tool logs, result cache, evidence store.

Core mechanics: a task state machine, failure retry, a maximum iteration count, a token
budget, resume-after-interrupt, and human confirmation checkpoints.

**Permission boundary:** the model never gets arbitrary shell execution. Tools run
through scoped adapters, read-only by default. Dynamic instrumentation and any mutating
operation require explicit user authorization.

### 2.2 MCP and model support

| Capability          | Approach                                                     |
| ------------------- | ------------------------------------------------------------ |
| MCP Server          | Expose DexAtlas's own normalized analysis tools               |
| LLM Provider        | OpenAI-compatible endpoints, with optional other providers    |
| Tool calling        | Schema validation, timeouts, permission checks                |
| Agent memory        | Methods already analyzed, findings and evidence for this APK  |
| Context retrieval   | Code search and symbol refs first; vector retrieval optional  |
| Reasoning trace     | Auditable task steps and tool results (not model internals)   |
| Resume              | Continue from saved state after interruption                  |

Vector databases and heavy RAG are **not** hard dependencies. Code search, precise
symbol resolution and cross-references are the primary retrieval channels; semantic
retrieval is a supplement.

### 2.3 Web workbench

React + TypeScript against the FastAPI backend: project explorer (package → class tree),
code and evidence pane with Java/Smali and cross-references, evidence IDs linking a
conclusion back to its source, and live Agent task progress.

This matters for GitHub: a stranger should understand the product from a short video,
not just from terminal output.

### 2.4 Security analysis and reporting

Rule-assisted checks mapped to OWASP MASVS / MASTG, scoped initially to storage,
network, platform-interface and general code-security patterns.

Reports must separate:

- **Verified** findings
- **Static-analysis leads** (risk indicators, not confirmed)
- **Insufficient evidence** — requires human validation

An LLM's opinion that code "looks risky" is never promoted to a confirmed vulnerability.

### 2.5 Exit targets

These are targets to be measured, **not** current performance claims.

| Metric          | Target                                            |
| --------------- | ------------------------------------------------- |
| Agent task set  | ≥20 tasks with human-verified answers              |
| Tool execution  | ≥95% success rate on tool tasks in a normal environment |
| Evidence        | 100% of externally shown conclusions traceable     |
| Error recovery  | Handles timeouts, tool crashes and model failures  |
| Model coverage  | At least 2 provider integrations verified          |
| User experience | Complete loop: upload APK → read AI analysis report |
| Public showcase | ≥2 screen recordings and 1 downloadable sample report |

At this point the repository supports Upwork applications for AI Agent, Python
Automation, LLM Integration and Backend Development roles.

---

## Phase 3 — Portfolio & Delivery (tagged `v1.0.0`)

**Replanned on 2026-11-15 for a personal GitHub / Upwork portfolio.**
The executable scope and acceptance criteria are in the
[Phase 3 plan](phase3-plan.md). It supersedes the earlier platform-expansion
vision in this section. Phase 3 is under way and **has not been accepted**;
`v1.0.0` was tagged on 2026-11-17. The status below records only evidence merged into
the repository.

### 3.1 Goal and scope

A newcomer can reproduce a complete workflow, an engineer can follow each
conclusion to its evidence, and a prospective client can inspect a scoped
sample deliverable. Existing CLI, REST, MCP, agent and workbench interfaces
continue to share one analysis core.

| Milestone | Deliverable |
|---|---|
| M5 | Reconcile public claims, existing measurements and the accepted baseline |
| M6 | Reliable bounded agent tasks, explicit budgets and real-model evaluation |
| M7 | Offline HTML and portable evidence packages, client-style case studies |
| M8 | Clean installation, failure handling, data boundaries and public contracts |
| M9 | GitHub presentation and ready-to-review English Upwork materials |
| M10 | Independent reproduction, source review, readiness reassessment and release candidate |

These are new meanings for the unaccepted M5–M10 draft milestone numbers.
Native/Ghidra/JNI, Frida, plugin loading, a separate SDK, cross-workspace
composition, PostgreSQL, queues and multi-tenant hosting are deferred until
concrete demand justifies their own plans. PDF is optional; offline HTML and
existing Markdown/JSON delivery are the required report surfaces.

### 3.2 Evaluation and evidence

Keep the existing benchmark and publish failures alongside successes. Distinguish
scripted demonstrations, actual model runs and changes to budgets/approval
conditions. Do not infer stronger-model performance from a same-model budget rerun.
Freeze the scoped service regression set before tuning and disclose its limits;
retain evaluation on the complete existing set.

### 3.3 Exit criteria

The [readiness assessment](../reports/portfolio-readiness-2026-11-15.md)
provides a manual portfolio rubric, distinct from the historical maturity rubric
below. Reassess GitHub and Upwork separately, targeting at least 90% each, with
source review and acceptance required regardless of score.

Required evidence includes clean-environment reproduction, inspectable client
samples with portable citations, truthful agent demonstrations and evaluation,
stable declared contracts, documented data boundaries, passing quality gates,
and a complete workflow performed by a reader who did not implement it.
Version `v1.0.0`'s stability promises cover the explicitly
documented contracts. Portfolio readiness does not promise orders, revenue,
security certification or commercial SaaS readiness.

### 3.4 Progress (2026-11-15)

Only work merged into the repository is listed; anything without merged
evidence is marked as not started or unverified. **Independent acceptance has
not begun; the Phase 3 exit criteria are not met; `v1.0.0` was tagged on 2026-11-17 with the boundaries stated in its release notes.**

| Milestone | Status | Evidence and what remains |
|---|---|---|
| M5 | **Done** | [phase3-baseline.md](../reports/phase3-baseline.md): claims inventory, all three benchmarks recomputed from committed traces, demo labelling for scripted versus real-model runs |
| M6 | **Partly done** | 20-question service regression set frozen at `100b191` ([service-regression-set.md](../benchmarks/service-regression-set.md)); level 0 deterministic scoring **20/20**; level 1 scripted drill complete ([m6-level1-scripted.md](../benchmarks/m6-level1-scripted.md)). The scripted provider is a stand-in, so its published scores test the question/trace/scoring machinery, not model capability. Level 2 real-model batch complete ([m6-level2-real.md](../benchmarks/m6-level2-real.md), all figures recomputed by script from [m6-level2-traces.json](../benchmarks/m6-level2-traces.json)): MiniMax-M3.1-Flash over the frozen 20 questions, 3 rounds — DexAtlas 24/60 (40.0%, rounds 45%/40%/35%), A source-text 24/60 (40.0%), B structured retrieval 18/60 (30.0%) — **below the acceptance line (≥80% per round, ≥90% over three rounds): verdict "not passed"**. All traces total 853,103 tokens, 53,103 over the authorized 800,000 cap, so the full 92-question sweep was not run. After failure-mode analysis and five root-cause fixes, the full three-round retest on the complete 20-question denominator scored DexAtlas **49/60 = 81.7% (rounds 15/16/18)** ([m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md)): r2 and r3 met the per-round ≥16/20 line, r1 did not, and 81.7% is still below the three-round ≥90% bar. The subsequent narrow verification round 2 over the six known failure surfaces (6 questions × 3 rounds × 3 configurations, 54 traces, all figures recomputed by script from [m6-level2-narrow-verify2-traces.json](../benchmarks/m6-level2-narrow-verify2-traces.json)) converted DexAtlas **2/6** questions (deterministic-fix questions **2/5**) — **below the narrow-verification gate (≥4/6 and ≥3/5)** ([m6-level2-narrow-verify2.md](../benchmarks/m6-level2-narrow-verify2.md)). A third narrow round after the budget-efficiency fixes (resources closure, notice folding, string-excerpt clipping, idle-tool notice; 54 traces, 380,881 tokens inside the 450,000 authorization) converted DexAtlas **3/6** questions (deterministic-fix questions **3/5**) — still below the gate ([m6-level2-narrow-verify3.md](../benchmarks/m6-level2-narrow-verify3.md)) — so per the plan investment stopped for good and M6 moved to the state-of-record disclosure plan; the milestone stays open |
| M7 | **Done** | Three customer-structured case studies ([case-studies/](../case-studies/README.md)); offline HTML and the minimal evidence package, with post-move citation checks and adversarial tests, in [report-rendering.md](../architecture/report-rendering.md) |
| M8 | **Partly done** | Clean-install, Docker and failure-recovery rehearsal done; macOS unverified ([m8-install-rehearsal.md](../reports/m8-install-rehearsal.md)). Public contract table done ([public-contracts.md](../architecture/public-contracts.md)). M8-2 (query commands lacked `--workspace`) and M8-3 (`install.md` extras mismatch) are **fixed and merged** (d90baff). M8-4 (all three backends failing with a readable manifest still yielded exit code 0) is **fixed by contract change**: exit code 6 (`EXIT_NO_INDEX`) added per the approved [proposal](../proposals/exit-code-partial-read.md); codes 0–5 unchanged (1f6ef05) |
| M9 | **Showcase done; materials unpublished** | Bilingual README entry, documentation map, third-party attribution and this roadmap status are merged. English Upwork materials remain **drafts, not published** ([outreach/](../outreach/project-brief.md)) |
| M10 | **Preparation ready; acceptance not started** | The 40-item acceptance pack ([m10-acceptance-pack.md](../reports/m10-acceptance-pack.md)), the reader package ([m10-reader-package.md](../reports/m10-reader-package.md)) and the author-side automated self-check ([m10-selfcheck.md](../reports/m10-selfcheck.md), 40/40 checks pass) are merged. Independent reproduction, readiness re-scoring and the release candidate remain; a real independent reader must run them |

---

## Review protocol

Every phase ends the same way.

1. **Version submission** — push the source; provide the repo link, tag or commit SHA,
   reproducible run commands, test results and known limitations. No secrets, no real
   user data, no APKs you lack the right to publish.
2. **Architecture and code review** — actual file layout, module dependencies, core
   implementations, call paths, exception handling, interface consistency, permission
   boundaries, test coverage.
3. **Maturity assessment** — scored across six dimensions, based only on evidence that
   can actually be seen and run.
4. **Review report** — blocking issues, important improvements, optional enhancements,
   and what should be deferred, with priority and risk.
5. **Re-plan the next phase** — next-phase issues, implementation order, interface changes,
   test plan and acceptance criteria, derived from the real code.

| Review dimension            | Weight |
| -------------------------- | ------ |
| Core functionality & completeness | 25% |
| Software architecture & code quality | 20% |
| Agent / MCP engineering     | 20%    |
| Testing, reliability & security | 15% |
| Documentation & developer experience | 10% |
| GitHub / Upwork presentation value | 10% |

This is an internal project scoring rubric, not an industry certification. A feature that
does not run is not judged as passing because the README claims it.

---

## Portfolio strategy

Position DexAtlas as proof of three distinct capabilities, not one:

| Positioning                     | Demonstrated by                                                    |
| ------------------------------- | ----------------------------------------------------------------- |
| **AI Agent Engineer**           | Agent workflow recording + MCP architecture diagram                |
| **Python Backend & Automation**| API docs + Docker deployment + CI test results                     |
| **Mobile Application Security** | Security analysis case study on self-built test apps + evidence report |

Lead with Agent engineering and Python backend: they map onto the broadest set of
OpenAI-compatible agent jobs. Add the security-reporting case once mature.

**Roadmap to community growth:**

| Phase    | Focus                                                          | Measures                          |
| -------- | -------------------------------------------------------------- | --------------------------------- |
| Phase 1  | English README, 30-second demo, Quick Start, first release      | Install success rate, first-time user feedback |
| Phase 2  | Interactive demo video, technical blog, public benchmark, community discussion | External users, issues, reuse and citations |
| Phase 3  | Plugin examples, contribution guide, releases, case studies     | External contributors, returning users, maintainability |

Maintain `CHANGELOG.md`, `CONTRIBUTING.md` and issue templates throughout. Star targets
(non-binding, no statistical basis): **30+** by end of Phase 1, **150+** by Phase 2,
**500+** long-term. Use them as motivation, never as acceptance criteria.

### The Phase 1 demo to prepare

> Upload a self-built Android APK → extract Manifest and class structure automatically →
> search for the call chain of one feature → show Java/Smali side by side → export a
> report with evidence attached.

Phase 2 upgrades this to a natural-language demo:

> "Which components are exported, and where are they declared? Show the supporting
> evidence."

An Agent that calls tools, lists results and jumps to evidence locations is enough to
show real engineering value.

---

## Portfolio positioning on Upwork

| Job direction                       | What DexAtlas proves                             |
| ----------------------------------- | ------------------------------------------------ |
| AI Agent / LLM Developer            | Agent orchestration, multi-tool integration, RAG-free retrieval design |
| Python Automation Engineer          | Analysis pipeline, task scheduling, error recovery |
| Backend / AI Integration Developer  | Deployable FastAPI service, REST, Docker, tests    |
| Mobile Security Analyst             | APK/DEX/Java/Smali static analysis, evidence reports |
| Full-Stack AI Developer             | Complete analysis workbench (Phase 2)              |

Market context is tracked against the
[Upwork in-demand skills report](https://www.upwork.com/research/in-demand-skills-2026);
engineering priorities get adjusted from real demand rather than trend-chasing.

---

## License

**Apache-2.0.** Chosen after auditing that no first-party file copies, modifies, links
or redistributes third-party code. JADX, Apktool, Androguard, Ghidra, Rizin and Frida are
invoked **as separate processes**, never embedded or vendored — which keeps their
obligations distinct from this project's. Re-audited for `v1.0.0`; re-audit before the next minor.

---

## Anti-goals

Features explicitly **out of scope** so far, and why:

- **Re-implementing decompilation.** JADX and Ghidra are excellent and free.
- **Signature forging, license bypass, protection evasion, or unauthorized data
  extraction.** Not a product feature, not a selling point, not a demo.
- **Embedding proprietary third-party code or APKs** in tests, fixtures or examples.
- **Kubernetes / microservices / distributed databases** before Phase 3 needs them.
- **Hard dependency on a vector database** for code search.
- **Publishing unreviewed model output as confirmed vulnerability.** Evidence first.
