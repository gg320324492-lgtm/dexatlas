# DexAtlas Roadmap

> **From APK to Evidence — Powered by AI Agents.**
> An open-source, evidence-first Android reverse engineering and mobile application analysis platform.

This document is the working contract for how DexAtlas grows. It is a plan, not a
promise of features — the README describes what actually ships, this file describes
what comes next.

- **Current phase:** Phase 1 shipped `v0.1.0` on 2026-10-14, `v0.1.1` on 2026-10-19
  (Foundation Hardening) and `v0.1.2` on 2026-10-20 (Acceptance Checklist) —
  awaiting the Phase 1 source review, which is the entry condition for Phase 2
- **Plan version:** 2026-10
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
| Phase 2  | `v0.5.0`  | Agentic Intelligence   | Demonstrable, evaluable agentic analysis platform               |
| Phase 3  | `v1.0.0`  | Production-Ready       | Extensible, deliverable, maintainable platform with real users  |

**Promotion rule:** a phase is complete when its exit checklist passes *and* the source
review raises no blocking findings. Promotion is not a calendar event.

Phase 1 shipped on 2026-10-14, `v0.1.1` followed on 2026-10-19 with the fixes that the
Phase 1 review work surfaced, and `v0.1.2` on 2026-10-20 with the five self-built test
APKs and the demo video the exit checklist asks for. Its exit checklist now reads in the
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

## Phase 2 — Agentic Intelligence (`v0.5.0`)

**Entry condition:** Phase 1 exit checklist passing and source review complete.

**Goal:** move from automated tools to an assistant that plans, calls tools, verifies
evidence, and recovers from failure.

> **Positioning.** JADX-MCP and JADX-AI-MCP already let a model read decompiled code.
> "JADX + ChatGPT" is therefore not a differentiator. DexAtlas differentiates on
> **multi-tool coordination + evidence-first output + resumable tasks + measurable
> analysis quality.**

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

## Phase 3 — Production-Ready Open Source (`v1.0.0`)

**Goal:** an extensible, deliverable, maintainable platform with demonstrated external
user value.

### 3.1 Product-grade capabilities

| Area               | Requirement                                              |
| ------------------ | -------------------------------------------------------- |
| Native analysis    | Ghidra integration, ELF/ARM symbol index, JNI relations   |
| Dynamic analysis   | Frida instrumentation in authorized test environments, log correlation |
| Plugin system      | Tool adapter SDK, plugin manifest, version compatibility   |
| Multi-project      | Project isolation, persistence, history queries            |
| Security           | Analysis sandboxing, least privilege, sensitive-data handling |
| Observability      | Task logs, timings, token usage, error statistics          |
| Report delivery    | HTML/PDF reports, evidence attachments, remediation notes |
| Interfaces         | REST API, MCP server, CLI                                  |
| Ecosystem          | SDK, plugin examples, third-party contribution docs        |

Optional PostgreSQL, task queues and more complex deployment are considered **here**,
not before.

### 3.2 Three product entry points

| Entry point    | Audience                | Emphasis                                     |
| -------------- | ----------------------- | -------------------------------------------- |
| DexAtlas CLI   | Learners, automation, CI | Speed, stability, reproducibility             |
| Workbench      | Researchers              | Source, call graphs, evidence, Agent results  |
| SDK / MCP      | Third-party developers   | Programmable access to the same analysis core |

All three share one analysis kernel.

### 3.3 Public benchmark

A test set built entirely from self-authored or explicitly licensed samples, covering
plain APKs, Kotlin, multi-DEX, resource references, obfuscation and JNI.

Published metrics:

- Task completion rate and invalid tool-call rate
- Evidence location accuracy
- False-conclusion rate, with human review results
- Per-project analysis time and resource cost
- A/B comparisons: with vs without agent, across models, across retrieval strategies

Publish failures and version-to-version differences alongside the best runs. This is what
separates an evaluable engineering system from an AI wrapper.

### 3.4 Exit criteria for `v1.0.0`

Reproducible local deployment; published test results; stable SDK/API; verifiable
security reports; real permission isolation; and at least one complete user flow that
needs no manual intervention from the author.

Remote multi-user collaboration, commercial SaaS, and Android + iOS expansion are decided
by real user demand at that time — not pre-announced.

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
obligations distinct from this project's. Re-audit before `v1.0.0`.

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
