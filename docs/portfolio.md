# DexAtlas — portfolio description

**A one-paragraph description for a client brief, and the detail behind it.
Written for potential clients; kept to what the repository demonstrates.**

---

## Short description

DexAtlas is an open-source Android application analysis platform that turns an
APK into a complete, verifiable picture: the manifest and permissions, the full
symbol index, decompiled Java source, the call graph, and an evidence trail
that records — for every fact — which tool read it, at which version, from
which byte position. It runs from the command line, over a REST API, from an
MCP server your AI assistant can call, through a built-in agent that answers
questions with cited evidence, or in a local web workbench.

## What it does

- **Full APK ingestion.** Hashing, validation, DEX/native-library inventory,
  and manifest decoding (package, versions, SDK levels, permissions, exported
  components) — read from the binary manifest, not just the decoded one.
- **A three-backend symbol index.** Androguard builds the authoritative class,
  method, field and call-site tables; JADX decompiles to readable Java; Apktool
  decodes the manifest and provides a Smali fallback when decompilation fails.
  Each backend's contribution is recorded, and a backend failure is reported as
  a value — an APK that defeats the decompiler still yields a complete index
  and a report that says which steps did not run.
- **Cross-reference navigation.** Call sites (with DEX file, instruction
  offset and bytecode-level provenance) and aggregated call edges, queryable
  from the CLI, the API, the browser, or an AI agent.
- **An evidence model with levels.** Conclusions are separated into
  `verified` (deterministically established by a tool, with a citation that
  resolves inside the analysis), `lead` (a risk indicator, not a finding), and
  `insufficient` (not enough evidence either way). Model-generated text can
  never be recorded as verified.
- **Report export.** The same renderer produces Markdown and JSON from the
  workspace; the web workbench serves that renderer's output byte for byte.

## Technical highlights

- **Evidence-first design.** Every fact in a report carries its provenance:
  tool name and version, the APK's sha256, and a locator naming the file and
  position the fact was read from. A reader can follow any claim back to the
  bytes it came from — the project's documentation is itself checked by a
  script that validates every `file:line` citation.
- **Read-only MCP server.** Ten tools over stdio that expose an existing
  analysis — projects, symbols, call sites, evidence, locators — with bounded
  responses and no write path, no shell, and no model dependency. An AI
  assistant can be pointed at a completed analysis without gaining any ability
  to modify the workspace or run code.
- **A single-loop, evidence-checked agent.** One plan, one budget, one state.
  The agent plans tool calls, reads through the MCP tools, and reports what it
  established, what are only leads, and what it could not establish — never
  treating a model's guess as a finding. Instructions found inside an APK are
  data, not orders.
- **Reproducible measurement.** The benchmark harness, its traces, and the
  metrics in its reports are committed to the repository, and the reports state
  what a scripted (non-model) baseline can and cannot show. Documentation
  figures are generated from the code by scripts, not edited by hand: the
  README's test/coverage badges and the report's numbers are recomputed, and
  the release notes' test counts are pinned to archived measurements.
- **Runtime isolation.** Untrusted DEX parsing runs in a separate worker
  process with resource bounds, so a malformed file costs a recorded error,
  not the host service.
- **Quality gates.** Strict mypy typing, ruff lint/format, 1,335 tests at
  91.1% coverage on the first-party code, and six CI jobs covering different
  backend configurations (all three backends; none of the Java-based ones;
  Apktool only) plus Docker and dependency audit.

## Who it is for, and when

- **App owners and development teams** doing due diligence on their own or
  third-party APKs: permissions and exported components at a glance, with
  receipts.
- **Security researchers** triaging a sample: an immediate symbol index, a
  string search that survives name obfuscation, decompiled source with a smali
  fallback, and a call graph to walk — with every observation citable.
- **AI-assisted analysis workflows**: the MCP server and the agent let a model
  read a structured, citation-backed view of an APK instead of raw bytes,
  under an evidence discipline that keeps the model's output labelled as
  leads.
- **Engineering teams building internal tooling**: the REST API and the Python
  core are meant to be driven programmatically; the agent is a library.

It is a good fit when you need **traceable** analysis — a report whose numbers
and claims can be re-derived. It is not a malware classifier or a sandbox; it
does not score risk or allege intent. It shows what the bytes contain, where
each fact was read from, and leaves the judgement to you.

## How to try it quickly

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
uv sync --extra analysis

uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json
```

That analyses a bundled first-party sample in a few seconds and writes both
report formats — no external downloads, no API keys, no model required. The
same workspace can then be opened in the web workbench
(`uv run dexatlas-workbench`) or served to an AI assistant
(`uv run dexatlas-mcp`). Full setup, including the JADX/Apktool backends and
Docker, is in [docs/install.md](install.md).

Two complete worked analyses — a walkthrough of the demo app from upload to
evidence chain, and an obfuscated-sample study — are in
[docs/case-studies/](case-studies/README.md). The architecture is drawn in
[docs/architecture/diagram.md](architecture/diagram.md), and the benchmark
methodology and its disclosures are in [docs/benchmarks/](benchmarks/comparison.md).

## Licensing and status

Apache-2.0. Actively developed; the current release is v0.2.0. Known
limitations are disclosed in the documentation rather than papered over — see
[docs/status.md](status.md) for the honest list, including which agent
configurations complete a question within default budgets.
