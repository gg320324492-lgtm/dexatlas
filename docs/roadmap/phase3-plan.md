# Phase 3 plan — Production-Ready Open Source (`v1.0.0`)

**Written after the Phase 2 acceptance, against the code that exists.**
The roadmap says Phase 3 "will need the same treatment when its time comes"
([phase2-plan.md](phase2-plan.md) §8): a plan written after the source review,
from the real code, not from the vision section written before any of it existed.
This is that document.

**Accepted baseline:** `v0.2.0` → `0446b13b55274e326446045d1385387c331a6dcf`
**Phase 2 status:** accepted — M0 through M4 all shipped; the M4 acceptance review
upgraded to a pass on 2026-11-14. The stronger-model rerun of the M3 comparison
was still in flight when this plan was written; its outcome adjusts M7's budget
defaults, not its scope.

**Inputs:**

| | |
|---|---|
| Vision | [ROADMAP.md §3](ROADMAP.md) — nine capability areas, three product entry points, a public benchmark |
| Current state | [status.md](../status.md) — v0.2.0 shipped, what remains open |
| Phase 2 debrief | [phase2-plan.md §8](phase2-plan.md) — what the process cost, what to keep |
| Open findings | [phase2-issue-list.md](../reports/phase2-issue-list.md) — F8 (dead code gate) still open; the rest closed |
| Architecture | [architecture/](../architecture/README.md) — backend failure as a value, evidence invariants, runtime isolation, workbench |

**What the current code changes about the plan.** The roadmap's Phase 3 section
was written as a vision: native analysis, dynamic analysis, a plugin system,
multi-project, sandboxing, observability, HTML/PDF reports, an SDK. Reading the
tree shows four things the vision did not know:

- **The extension point already exists and is not a plugin system.**
  `Backend` (`src/dexatlas/tools/base.py`) is an ABC with `resolve`, `version`,
  `available`, `run`, `provenance`; `BackendRegistry` wires three adapters. But
  `Analyzer.analyze` calls the three backends **by name** in a fixed order, and
  `Settings` already carries `ghidra_path` / `rizin_path` fields that **nothing
  reads** — placeholders for a direction that was never built. "Plugin system"
  means making that registry real, not inventing a second one.
- **The multi-process boundary already exists for one backend.** Androguard
  parses untrusted DEX in a **separate worker process** with memory and file-size
  bounds ([runtime-isolation.md](../architecture/runtime-isolation.md)) — that
  pattern is the sandbox story, and it was paid for with real defects. The two
  subprocess backends (JADX, Apktool) already run out-of-process with timeouts,
  output caps and process-group kill. So "sandboxing" is largely **extending and
  proving an existing pattern**, not building one.
- **Multi-project exists at one level only.** The store is one SQLite database
  keyed by `project_id` (a content hash), each project gets its own workspace
  directory, and every analysis writes into its own run directory and publishes
  atomically (P2-002). What does **not** exist: multiple workspaces in one
  process, cross-project queries, history queries beyond per-project run rows,
  and retention beyond the uploads window.
- **Observability is nearly absent by design decision, not oversight.** There is
  structured logging (`loguru`), run rows with timing and completeness, and
  per-tool `ToolError` codes — but no metrics endpoint, no token-usage
  aggregation beyond the agent's per-task budget counters, no error statistics,
  no task log surface beyond the workbench's per-task timeline.

So Phase 3 is not "build the nine vision areas". It is **"harden what a stranger
will touch, expose what an operator needs, and buy only the new analysis
capabilities whose acceptance can actually be demonstrated"**.

**The development principle, unchanged and still the acceptance rule:**

> **Evidence before inference. Correctness before autonomy.**

---

## 1. What Phase 3 takes from the vision, and what it declines

The roadmap lists nine areas ([ROADMAP.md §3.1](ROADMAP.md)). Each gets an
explicit verdict, because an unpriced "yes" is how a phase rots.

| Vision area | Verdict | Why |
|---|---|---|
| Plugin system / tool adapter SDK | **Yes — M5** | The `Backend` ABC and `BackendRegistry` are already the seam. Promoting them to a documented, tested contract is the cheapest large win Phase 3 can buy. |
| Observability (task logs, timings, token usage, error statistics) | **Yes — M6** | The data already exists in `runs`, `ToolError` and the agent budget counters; it is simply not exposed. This is an exposure milestone, not an instrumentation project. |
| Multi-project (isolation, persistence, history queries) | **Yes — M6** | Project-level isolation and atomic run publication exist. What is missing is workspace-level composition and history queries — bounded, testable work. |
| HTML/PDF reports, evidence attachments | **Yes — HTML (M6); PDF declined** | One more renderer over the same `AnalysisResult` fits the existing markdown/JSON pattern and the "one renderer per transport" rule. PDF needs a typesetting engine and a maintenance burden the current report does not justify; see the declination note in M6. |
| Sandboxing / least privilege / sensitive-data handling | **Yes — M8 (as hardening, not a new subsystem)** | Runtime isolation for untrusted input already shipped in Phase 2. M8 audits and closes the remaining gaps (worker coverage for all in-process parsing, workspace permissions, secret hygiene in reports), with tests. |
| Security *analysis* capability (the tool finding vulnerabilities) | **Declined for Phase 3** | The roadmap's table says "analysis sandboxing, least privilege" — about the tool's own safety, not vulnerability research. Vulnerability-finding rules are a product direction of their own and would need their own benchmark; they are not priced here. |
| Native analysis: Ghidra, ELF/ARM symbol index, JNI relations | **Yes — M9, gated on samples** | `ghidra_path`/`rizin_path` are read-nothing placeholders today. The acceptance problem is not the adapter — it is **what samples and rights are needed to demonstrate it**. Committed behind an explicit sample-and-license gate (see M9). |
| Dynamic analysis: Frida instrumentation, log correlation | **Deferred, likely past v1.0.0** | Requires a rooted/emulated device fleet, per-sample harness scripts, and a legal/authorization envelope that self-authored `examples/` cannot supply (they are static APKs, not running apps under test). The evidence-first bar — every dynamic claim traceable to a recorded run — is currently unmeetable for want of harnesses. Revisit only when a partner environment exists; see the risk register. |
| Ecosystem: SDK, plugin examples, third-party contribution docs | **Yes — M10** | Falls out of M5: the adapter contract *is* the SDK seed. Examples and a contribution guide close the phase. |
| Public benchmark (self-authored, published metrics) | **Yes — M7** | M3 built the harness, the 92-task set and the disclosure discipline. Phase 3 publishes it as a standing artifact and adds the native-capability tasks if M9 lands. |
| Interfaces: REST API, MCP server, CLI | **Already shipped in Phase 2** | M6/M10 only extend and freeze them. |
| Optional PostgreSQL / task queues | **Declined until a deployment demands it** | The roadmap itself defers these to "here", meaning Phase 3 *considers* them. The current SQLite + local-files design meets every acceptance test below; adding a queue adds an operational surface no current user has asked for. Revisit on evidence of a real deployment need, not on speculativeness. |

**The three product entry points** (CLI, workbench, SDK/MCP) all exist and share
one kernel — that part of the vision is already true. Phase 3's job is to make
them **survive a stranger**: stable contracts, docs, examples, and a benchmark
that publishes failures alongside successes.

---

## 2. The milestones

| | Milestone | Version | What it delivers |
|---|---|---|---|
| **M5** | Backend contract & plugin seam | `v0.6.0` | A documented, registry-driven backend contract with a working third adapter path and a plugin example |
| **M6** | Operator surfaces: multi-workspace, history, observability, HTML | `v0.7.0` | Multi-workspace composition, run history queries, a metrics/health surface, an HTML report |
| **M7** | Published benchmark & budget tuning | `v0.8.0` | The 92-task benchmark as a published artifact; agent budget defaults set from the stronger-model rerun |
| **M8** | Hardening & least privilege | `v0.9.0` | All untrusted parsing behind the worker boundary; workspace/secret/data-handling audit closed with tests |
| **M9** | Native analysis (sample-gated) | `v0.9.x` (optional) | Ghidra/ELF/JNI capability, shipped only if the sample-and-license gate is met |
| **M10** | SDK, examples & v1.0.0 release | `v1.0.0` | Frozen public contracts, plugin/SDK examples, contribution guide, release audit |

**Why this order.** M5 comes first because every later milestone publishes the
backend contract: M6's metrics count backends, M7's benchmark runs them, M9 *is*
one. M6 precedes M7 because a published benchmark needs the observability to
explain a failed run. M7 sits before M8/M9/M10 so that the stronger-model rerun
(and any budget default it motivates) lands before contracts freeze. M8 is
deliberately late-but-before-release: hardening is cheapest to audit against a
feature-complete tree. M9 is the only milestone whose presence is conditional,
and M10 cannot start until that condition resolves either way.

**Milestones M5–M7 are sequential by contract dependency.** M8–M10 each depend
on all of M5–M7 but not on each other; M9 remains gated as described in its
section.

---

## 3. M5 — Backend contract & plugin seam (`v0.6.0`)

**Goal:** make the backend registry a real extension point that a contributor
can implement without reading the pipeline, and prove it with a plugin that
ships in-tree.

### 3.1 Tasks

- **Freeze the `Backend` contract as a documented interface.** `Backend` in
  [base.py](../../src/dexatlas/tools/base.py) already defines `resolve`,
  `version`, `available`, `missing_error`, `run`, `provenance` and the
  `ToolOutcome`/`ToolError` value model. Write the contract down as
  architecture documentation: what a backend must never do (mutate host state,
  raise instead of returning `ToolError`, trust its input), what `provenance`
  must attest, and how the registry discovers adapters.
- **Make `BackendRegistry` the single construction point.** Remove any direct
  adapter construction from `Analyzer` and the CLI/API/MCP transports, so the
  registry is the only place that maps a backend name to an instance. This is
  the seam plugins plug into.
- **Kill the read-nothing settings, or give them a reader.** `Settings.ghidra_path`
  and `Settings.rizin_path` are currently declared and never consumed. Either
  delete them until M9 needs them, or have the registry consult them during
  discovery — but not both-neither. (Decision recorded in M9; until then the
  fields are dead configuration, which is exactly what F8's lesson says not to
  keep.)
- **Add a first-party example backend.** A small, dependency-free adapter
  (for example, a `ZipInspectBackend` that lists APK entry names and sizes from
  the already-ingested file) that exercises the whole contract: discovery,
  `ToolOutcome` on failure, provenance, evidence emission, report rendering.
  It ships in `examples/` with its own tests and doubles as the plugin template.
- **Plugin discovery shape.** Support in-tree registration first (a
  `register_backend()` call and entry-point-style naming), and document why
  out-of-tree loading (importlib paths, pip entry points) is deferred to M10's
  SDK work — the contract must be stable before third parties load code
  against it.

### 3.2 Exit criteria

1. The backend contract is documented in `docs/architecture/` with the same
   rigor as [runtime-isolation.md](../architecture/runtime-isolation.md):
   invariants, failure semantics, provenance obligations.
2. `Analyzer` constructs no adapter directly; a test asserts the registry is
   the sole source of backends (breaking the registry breaks the test).
3. The example backend passes the full pipeline on a self-authored APK and its
   evidence appears in the rendered report with valid locators.
4. A test suite exercises the contract with a **deliberately broken** backend
   (raises, returns malformed output, lies in provenance) and the pipeline
   degrades per the failure-as-value rule — the report names what did not run.
5. `ruff`, `mypy`, and the three backend CI configurations stay green.

### 3.3 Acceptance

Source review of the registry/contract diff plus an acceptance drill: run the
example backend end-to-end from a clean worktree (the same drill Phase 2 used
for M1's MCP tools), including the deliberately-broken-backend demo.

---

## 4. M6 — Operator surfaces: multi-workspace, history, observability, HTML (`v0.7.0`)

**Goal:** give an operator (not just a caller) the four things the vision
names — multi-project composition, history, observability, richer report
delivery — without changing the analysis kernel.

### 4.1 Tasks

- **Workspace composition.** `Settings.workspace` is a single root today. Add
  explicit multi-workspace support at the transport layer: the CLI/API/MCP
  accept a workspace selector, and the store layer refuses cross-workspace
  `project_id` collisions loudly. Persistence and per-project isolation already
  exist (P2-002); what changes is the *composition* boundary.
- **History queries.** The `runs` table already records per-run status,
  timing and completeness. Expose them: "runs for a project", "compare two
  runs", "which runs hit truncation". CLI subcommands and REST/MCP read-only
  endpoints, backed by the existing store — no new state.
- **Observability surface.** One `/metrics`-style endpoint (format decided in
  review: JSON by default, Prometheus text if trivially cheap) exposing: run
  counts by status and completeness, backend failure counts by `ToolErrorCode`,
  truncation counts, agent task outcomes and token budgets consumed, p50/p95
  analysis durations. **Every number must be derivable from existing records** —
  this milestone exposes data, it does not add new instrumentation; where a
  number cannot be derived (e.g. per-request timings for the workbench), the
  endpoint's docs say so rather than inventing it.
- **HTML report renderer.** A third renderer over `AnalysisResult`, joining
  `render_markdown` and `build_json_report`. Constraints carried over from
  Phase 2: one source of truth (`AnalysisResult`), byte-identical exports per
  format, evidence table with resolvable locators, the "class declarations are
  the index" disclosure, and the figure markers remain generated — the HTML
  renderer must not create a second place where hand-written numbers can hide.
  Self-contained single-file HTML (inline CSS, no JS build step) so the report
  is portable and the web workbench stays the interactive surface.
- **PDF: declined, with reasons on record.** A faithful PDF of the current
  report needs a typesetting dependency (WeasyPrint/ReportLab class), a
  maintenance surface for CJK text and tables, and a licensing review — all to
  serve a delivery format no current consumer requires (the CLI/API/workbench
  all consume markdown/JSON/HTML). The HTML output is printable to PDF by any
  browser, which is recorded as the supported path. Revisit only on a concrete
  consumer demand.

### 4.2 Exit criteria

1. Two workspaces in one process serve disjoint projects with no cross-talk;
   a test proves a `project_id` collision across workspaces is refused, not
   merged.
2. History endpoints answer run-status, truncation and comparison queries from
   the existing store; each has a test seeded with known run rows.
3. The metrics endpoint's every field is asserted equal to a value recomputed
   from the store in the same test — no self-reported numbers.
4. The HTML report of a fixture project is byte-stable across two runs and its
   evidence locators all resolve (reusing the citation-checking discipline).
5. All existing API/MCP/CLI contracts are unchanged (Phase 2's contract tests
   pass unmodified); new surfaces are additive.

### 4.3 Acceptance

Source review plus an operator drill: from a clean worktree, create two
workspaces, run analyses in both, query history and metrics, export an HTML
report and verify its locators resolve — the drill recorded like the M4
end-to-end run was.

---

## 5. M7 — Published benchmark & budget tuning (`v0.8.0`)

**Goal:** turn the M3 comparison harness into a published, standing benchmark,
and fold in the stronger-model rerun's findings.

### 5.1 Tasks

- **Fold in the stronger-model rerun.** The comparison rerun (in flight in a
  parallel session at planning time) decides whether agent budget defaults
  (`DEXATLAS_AGENT_MAX_STEPS`, token budget) change. The M4 drills showed the
  default budget exhausts on enumeration questions; the rerun's traces are the
  evidence that sets the default. **No default changes without a trace-backed
  measurement** — the same rule that governs every figure in this repo.
- **Publish the benchmark as an artifact.** The 92-task set, both trace files,
  the metrics definitions and both reports are already in-repo; M7 adds the
  packaging: a benchmark README that states what each metric means, how to
  reproduce it, and what the disclosures are. Publishing failures alongside
  successes is already the harness's discipline (`unsupported_assertion_rate`,
  `budget_exhausted` breakdowns) — the milestone formalizes it.
- **Extend the task set only where acceptance allows.** New tasks may cover
  resource/manifest questions and the example backend's capability (M5), and —
  if M9 lands — native-code questions. **No dynamic-analysis tasks** (see the
  Frida deferral); the benchmark never invents a capability the tool lacks.
- **CI guard.** The existing "M3 comparison stays reproducible" job extends to
  any newly published trace: a drift between trace and report is a red build.

### 5.2 Exit criteria

1. The benchmark README exists and a stranger can reproduce one metric from it
   with the documented commands (verified in the drill).
2. Any change to agent budget defaults cites the rerun trace in the change
   description, and a test pins the new default.
3. The CI reproducibility job covers every published trace file.
4. The published reports still carry their disclosures verbatim.

### 5.3 Acceptance

Source review plus a reproduction drill: an evaluator follows only the
benchmark README and regenerates one report and one metric table; the outputs
match the committed artifacts byte-for-byte.

---

## 6. M8 — Hardening & least privilege (`v0.9.0`)

**Goal:** close the security/sandbox column of the vision as an audit with
tests, over a feature-complete tree.

### 6.1 Tasks

- **Worker-boundary completeness.** Runtime isolation moved Androguard's DEX
  parse into a bounded worker process. Audit every remaining in-process parse
  of untrusted bytes (upload inspection, resource XML, any M9 native parsers if
  present) and either move it behind the same worker pattern or document why
  the process boundary is not needed for it (e.g. stdlib ZIP parsing with size
  caps already bounded). Each decision is written down, not assumed.
- **Least privilege review of the transports.** The MCP server and API are
  read-only by construction; re-verify after M6's new endpoints that every
  added surface is read-only or explicitly-gated, and that the agent's tool
  allowlist still cannot reach a mutating operation. Extend the
  model-capability-disabled verification drill (which already covers 43
  endpoints) with the M6 surfaces.
- **Sensitive-data handling.** Verify reports and logs never echo secrets:
  agent provider keys stay in the environment, the workbench keeps them
  server-side (M4's review covered this — re-run the checks on the new code),
  and uploaded artifacts live only under the workspace with the retention
  policy enforced.
- **Workspace hygiene.** Retention currently covers `uploads/`. Decide and
  document the retention story for run output trees and agent task records
  (bounds, not unbounded growth), with a cleanup pass that is testable.
- **Close F8.** The dead-code gate (vulture, exit code 0 in CI) is the one
  Phase 2 finding still open; closing it here is cheap and prevents M5–M7 from
  accumulating new dead seams.
- **Dependency & supply-chain audit.** The existing audit job plus a review of
  any new M5–M7 dependencies; pin and document them.

### 6.2 Exit criteria

1. Every untrusted-parse site is either behind the worker boundary or carries
   a written justification; a table in `docs/architecture/runtime-isolation.md`
   lists each site and its verdict.
2. The model-disabled drill passes on the enlarged surface with zero agent
   capabilities reachable.
3. Retention/enforcement tests exist for uploads, run trees and task records;
   each cleanup test fails if the cleanup is removed.
4. The dead-code gate runs in CI and fails on a deliberately introduced dead
   symbol (the F8 acceptance test).
5. No new `Medium`+ advisory in the dependency audit.

### 6.3 Acceptance

Source review with a security reviewer's checklist, plus a drill: inject a
malformed artifact at each parse boundary and observe graceful, recorded
failure — never a process death, never a silent pass.

---

## 7. M9 — Native analysis, sample-gated (`v0.9.x`, conditional)

**Goal:** JNI/ELF/native-library visibility, via Ghidra — **only if the sample
and license gate can be met.** This milestone is planned but not scheduled; its
first task is to resolve the gate, and if it cannot be resolved, the milestone
is formally skipped and the skip is recorded in the v1.0.0 release notes.

### 7.1 The gate — what acceptance actually requires

The evidence-first rule makes this milestone's hard part **samples and rights**,
not code:

- **Self-authored native sample.** The repo's boundary is: every analyzed
  artifact is first-party with sources alongside. A native capability needs a
  self-authored APK **with native code** — a small NDK library (one JNI
  function, one exported symbol) whose C/C++ source, build script and built
  artifacts live in `examples/` under the same first-party rule. Building it
  needs the Android NDK on the build machine, which is a new fixture
  prerequisite to document.
- **Ghidra itself.** Ghidra is a large Java application; CI cannot install it
  per-run cheaply. The realistic acceptance is: headless Ghidra invoked as a
  subprocess backend (matching the existing `Backend` pattern — `resolve`,
  `version`, `available`, timeout, output caps, process-group kill), with CI
  running the **contract tests with the backend absent** (the same
  skip-not-pass discipline the JADX/Apktool jobs already practice) and the
  full drill run manually on a machine where Ghidra is installed. The repo has
  already paid for this exact pattern: `ghidra_path` exists in `Settings` as
  the discovery hook.
- **Licensing.** Ghidra is Apache-2.0; invoking it as an external tool (not
  vendoring it) matches how JADX and Apktool are treated. The contribution
  docs must state that Ghidra is never bundled.
- **What "done" means for JNI relations.** Bounded and honest: the APK's
  `lib/<abi>/*.so` files are inventoried (sizes, exported symbols via the
  parse), JNI `RegisterNatives`/`Java_*` exports are matched against Java-side
  `native` declarations, and each relation is evidence with a locator on both
  sides. **Not in scope:** full decompilation quality parity with JADX, ARM
  instruction-level analysis beyond symbol/export extraction, or dynamic
  hooks.

### 7.2 Tasks (post-gate)

- `NativeBackend` implementing the frozen M5 contract, subprocess-isolated,
  with `ToolOutcome` failure semantics.
- `lib/*.so` inventory and JNI-relation extraction into the store, with
  evidence kinds and locators on both the Java and native sides.
- Report sections (all three renderers) for native libraries and JNI
  relations, with the same "index vs finding" honesty about what a symbol
  export proves.
- Benchmarks (M7) gain native questions only if this milestone lands.

### 7.3 Exit criteria

1. The gate table above is resolved item by item (sample built and committed
   with sources; Ghidra discovery working; license statement written) — or the
   milestone is skipped with the resolution recorded.
2. If landed: a self-authored JNI sample's Java↔native relations appear in all
   three report formats with resolvable locators, and a test fails if the
   native backend's evidence is dropped.
3. CI runs the native-backend contract suite in the backend-absent
   configuration (skips, not silent passes), and the full drill is recorded
   from a Ghidra-equipped machine.

### 7.4 Acceptance

Same review-protocol mechanism: source review plus a recorded drill on the
sample APK, reproducing the JNI-relation evidence end to end.

---

## 8. M10 — SDK, examples & the v1.0.0 release (`v1.0.0`)

**Goal:** freeze the public contracts, ship the ecosystem pieces, and pass the
v1.0.0 exit criteria from the roadmap.

### 8.1 Tasks

- **Freeze and document the public contracts.** The REST API, MCP tool
  schemas, CLI commands, `ToolOutcome`/`ToolError` codes, evidence model and
  the backend contract (M5) are the public surface. Each gets: a versioning
  statement (what counts as breaking), a stability note, and a changelog entry.
  Phase 2 already learned this lesson once (`schema_version` missed an
  upgrade); the release audit re-checks every public shape.
- **SDK packaging.** A thin, versioned client package (Python first) over the
  REST API and/or MCP, generated or hand-written per review decision, with
  tests against the live server. The plugin-example side of the SDK is M5's
  example backend; this is the *consumer* side.
- **Plugin examples.** Beyond M5's in-tree example: one example that adds a
  report section and one that adds an agent tool, both first-party, both
  tested, both documented as templates.
- **Contribution guide.** How to add a backend (pointing at the M5 contract
  and the example), how to add a report renderer, how the evidence invariants
  constrain new features, how CI's three backend configurations work, and the
  sample/licensing boundary (no third-party APKs, ever).
- **Release audit.** Run the full gate battery, re-derive every cited line,
  refresh every generated figure, verify the three product entry points end
  to end, and record the v1.0.0 acceptance against the roadmap's exit
  criteria: reproducible local deployment, published test results, stable
  SDK/API, verifiable security posture, real permission isolation, one
  complete no-intervention user flow.

### 8.2 Exit criteria

1. Every public contract carries a stability statement and breaking-change
   policy; a test suite pins the REST/MCP/CLI response shapes.
2. The SDK client's tests pass against the real server on all read surfaces.
3. Both plugin examples run end-to-end in a clean worktree.
4. The contribution guide's "add a backend" instructions produce a passing
   backend when followed (verified in the drill by actually following them).
5. The v1.0.0 release notes state what shipped, what was declined (PDF,
   Frida, PostgreSQL/queues, out-of-tree plugin loading — with the reasons
   recorded here), and what remains open.

### 8.3 Acceptance

The full review protocol from the roadmap, unchanged: version submission,
architecture/code review, maturity assessment, review report — and the next
phase is planned from that review, not from this document.

---

## 9. Risks and dependencies

| Risk | Milestones hit | Mitigation |
|---|---|---|
| **Ghidra sample gate fails** — no NDK build environment, or the self-authored native sample proves too costly to maintain | M9 | The milestone is explicitly conditional; skipping it is a planned outcome, recorded in release notes. No other milestone depends on M9. |
| **Frida/dynamic analysis stays out** — expectations set by the roadmap's vision | M9, M7, release notes | The declination is written here with reasons (harness fleet, authorization envelope, evidence traceability unmeetable). The benchmark gains no dynamic tasks, and the release notes repeat the boundary so the gap is visible, not hidden. |
| **Contract freeze too early** — M5's backend contract hardens before M9's native backend reveals what it needed | M5, M9, M10 | M5 freezes the *interface* (ToolOutcome, provenance, registry) that all backends already share; M9 adds capability-specific evidence kinds, which are additive. The M10 audit re-opens the contract if M9 landed and strained it. |
| **Observability becomes an instrumentation project** — scope creep into tracing/profiling | M6 | The milestone's rule: expose only what existing records already contain; every metric field must be recomputable from the store in its test. New instrumentation is out of scope and said so. |
| **Stronger-model rerun lands late or contradicts budget hopes** | M7 | The rerun is input, not blocker: if it is not finished when M7 starts, budget defaults stay as-is and the change is deferred with the trace as required evidence. No default moves without a measurement. |
| **Parallel-session conflicts** — the M3 rerun session owns `benchmarks/comparison/` and `docs/benchmarks/comparison-stronger*`; M4 reports are owned by their session | M7 | Those paths are excluded from this plan's work until their owners close; M7's packaging work touches the benchmark README and CI job, not the comparison harness internals. |
| **CI cost growth** — more configurations (native-absent, HTML snapshot, dead-code gate) lengthen builds | M6, M8, M9 | Keep the backend-absent configurations as cheap contract suites (they already exist as a pattern); full drills stay manual and recorded. Native backend never runs Ghidra in CI. |
| **Windows/macOS drift** — CI runs only on `ubuntu-latest`; the dev machine is Windows; process handling already carries `taskkill` fallbacks | M8, M10 | This plan does not promise multi-OS CI (that is a cost decision for the review). It does require: the three existing backend configurations keep covering the Windows-specific paths, the platform-specific code stays behind the tested helpers, and the release notes state plainly which platforms are CI-verified (Linux) versus developed-on (Windows). Overstating platform support would be exactly the "claims the measurement does not support" failure this project polices. |
| **Scope breadth vs. review bandwidth** — six milestones is more surface than Phase 2's five | all | The milestones are ordered so each is independently acceptable and shippable; M9 is droppable without cascading. If bandwidth forces a cut, the cut order is: M9 (gated anyway) → M10's SDK (keep examples + guide) → M6's HTML (keep observability). The kernel and security hardening (M8) are never cut. |

**Dependencies on parallel work.** The stronger-model rerun session owns the
comparison harness and its traces; M7 consumes its output and must not edit its
files. The M4 documentation sessions own `docs/reports/m4-*.md`; this plan
reads them as inputs only. The generated figures in
[phase1-execution-report.md](../reports/phase1-execution-report.md) are
script-owned; nothing here touches them.

---

## 10. Estimation (order of magnitude, no calendar dates)

Order-of-magnitude engineering effort, in the same spirit as the Phase 2
issue list's estimates — deliberately coarse, to be refined per milestone at
its own kickoff review:

| Milestone | Magnitude | Dominant cost |
|---|---|---|
| M5 backend contract & plugin seam | ~1–2 weeks | Contract documentation + registry refactor + example backend with tests |
| M6 operator surfaces | ~2–3 weeks | Multi-workspace composition + metrics endpoint + HTML renderer (all three renderers kept in sync) |
| M7 published benchmark | ~1 week | Packaging/reproduction docs + CI guard extension; budget tuning is measurement-gated, not effort-gated |
| M8 hardening | ~1–2 weeks | Parse-boundary audit + retention tests + dead-code gate + drills |
| M9 native analysis | ~2–3 weeks **if the gate opens** | The sample/NDK fixture and the Ghidra adapter dominate; the store/report plumbing is the smaller half. Gate resolution itself is days, not weeks |
| M10 SDK & release | ~2 weeks | SDK client + examples + contribution guide + the full release audit |

The whole phase is therefore in the **8–13 engineering-week** range for one
maintainer, excluding the calendar cost of the external dependencies (model API
access for the rerun, an NDK-capable build machine, a Ghidra-equipped drill
machine). As in Phase 2, the estimates name the dominant cost so the review can
attack it; they are not commitments.

---

## 11. What this plan deliberately does not do

Recorded so the next review can check the reasoning, not just the outcome:

1. **No Frida / dynamic analysis.** The authorization and harness prerequisites
   cannot be met by this project's first-party sample discipline today; a
   dynamic claim that cannot be traced to a recorded run would violate the
   core rule. Revisit with a partner environment.
2. **No PDF renderer.** HTML is the printable format; a PDF engine is
   maintenance without a consumer.
3. **No PostgreSQL / task queues / multi-node deployment.** SQLite + local
   files meets every acceptance test in this plan; the roadmap defers these to
   "considered here", and the consideration is: declined until a real
   deployment demands them.
4. **No out-of-tree plugin loading.** M5 registers in-tree; loading third-party
   code needs the SDK's stability guarantees first (M10). Documented as the
   follow-up.
5. **No vulnerability-finding analysis rules.** The vision's "security" row is
   read as the tool's own sandboxing/least-privilege posture (M8). Security
   *research* capabilities would need their own benchmark and are not priced
   here.
6. **No multi-OS CI promise.** CI stays Linux; the platform story is stated
   honestly in the release notes (see the risk register) rather than
   overstated.

---

## 12. Process

Every milestone follows the mechanism Phase 2 used, which the roadmap's
[review protocol](ROADMAP.md) defines:

- **Plan against real code.** Each milestone opens with a short current-state
  note written from the tree (like this document's baseline), not from the
  previous milestone's assumptions.
- **Exit criteria are testable before work starts.** A milestone whose exit
  criteria cannot name its tests, its benchmark or its documentation
  deliverable is not ready to start.
- **Every fix carries a regression test that fails on the previous
  implementation** — proven by restoring the old code and watching the test go
  red.
- **No hand-written numbers.** Report figures, benchmark metrics and
  observability fields are generated from measurements; a number nobody can
  re-derive is not a claim.
- **Acceptance = source review + acceptance drill.** Each milestone closes
  with a review against the actual diff and a recorded end-to-end drill from a
  clean worktree. The next milestone's plan is written from that review.
- **Public contracts change loudly.** Any change to a status code, response
  shape or count's meaning is versioned and called out in the release notes —
  never silent.
