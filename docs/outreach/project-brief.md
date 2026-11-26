# DexAtlas — Upwork project portfolio entry

> **Draft for review — not published.**
> Prepared against the Upwork portfolio guidelines
> (<https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile>):
> the entry states the project, the role, a short description, skills and
> deliverables. Character limits should be re-checked against the live form
> before uploading, because the platform adjusts them.
>
> **Identity note (important).** This is a **personal, self-directed open-source
> project**. There is no client behind it and no client work is implied. The
> entry below is written in the first person and never describes a fictional
> engagement, a fictional client result, or a fictional revenue or time saving.

---

## Project title

DexAtlas — Evidence-First Android APK Static Analysis

## Role

Sole author and maintainer. I designed the architecture, wrote the analysis
core, the three backend integrations, the storage and evidence model, the CLI
and REST API, the read-only MCP server, the evidence-first agent loop, the web
workbench, the test suite and the documentation. AI coding assistants were used
for parts of the implementation; every design decision, integration and line
of shipped code was reviewed and accepted by me.

## Short description

DexAtlas is an open-source, evidence-first Android application analysis
platform. It takes an APK and turns it into a complete, verifiable picture:
the decoded manifest and permissions, a full class/method/field symbol index,
decompiled Java source, call-site and call-graph cross-references, and an
evidence trail that records — for every fact — which tool read it, at which
version, from which byte position. The same analysis is reachable through a
command-line interface, a REST API, a read-only MCP server that an AI
assistant can call, a built-in agent that answers questions with cited
evidence, and a local web workbench.

The design rule the project is built on: **a conclusion must trace back to the
bytes it came from.** Every report fact carries its provenance (tool name and
version, APK sha256, and a file-and-position locator), conclusions are graded
`verified` / `lead` / `insufficient`, and model-generated text can never be
recorded as verified. A backend that fails is reported as a value, not a
crash: an APK that defeats the decompiler still yields a manifest, an index
and a report that says which steps did not run.

- 1,863 automated tests, 93.3% coverage, mypy strict, ruff, and a CI pipeline
  across Python 3.12/3.13 and multiple backend configurations.
- Full documentation with three complete case studies on first-party sample
  APKs that anyone can reproduce from the repository.

## Skills

`Python` · `FastAPI` · `REST API` · `SQLite` · `pytest` · `mypy` ·
`Reverse Engineering` · `Android` · `APK Analysis` · `Static Analysis` ·
`Androguard` · `JADX` · `Apktool` · `Smali` · `MCP (Model Context Protocol)` ·
`LLM Integration` · `AI Agents` · `Command-line Tools` · `Open Source` ·
`Technical Writing`

## Deliverables shown in the repository

- **Analysis pipeline and storage.** APK ingestion (hashing, DEX and
  native-library inventory, binary-manifest decoding), a three-backend symbol
  index, and a SQLite workspace with a reproducible schema.
- **Two transports over one core.** A CLI (`dexatlas analyze / manifest /
  search / source / xref / evidence / report`) and a REST API (FastAPI) over
  the same analyzer.
- **Read-only MCP server.** Eleven tools over stdio exposing projects,
  symbols, call sites, evidence and locators — bounded responses, no write
  path, no shell, no model dependency.
- **Evidence-first agent.** A single-loop agent that plans tool calls over the
  MCP tools within a budget, and reports what was established, what is only a
  lead, and what could not be established.
- **Web workbench.** A local browser UI covering project dashboard, upload and
  analysis progress, search and evidence, cross-references, the agent
  workspace, and report export.
- **Reports.** Markdown and JSON renderers producing per-analysis reports with
  evidence records and resolvable citations.
- **Benchmark harness.** Scripted and real-model comparison runs with
  committed traces and reproducible metrics; scripted and real-model results
  are reported separately and never mixed.
- **Engineering quality gates.** 1,863 tests, coverage and dead-code gates,
  strict typing, lint/format, documentation citation checks, and CI across
  multiple Python and backend configurations.

## Third-party components (attribution)

DexAtlas integrates three established third-party analysis engines and does
not claim their work as its own:

- **Androguard** — authoritative DEX symbol graph (classes, methods, fields,
  call sites).
- **JADX** — decompilation to readable Java source.
- **Apktool** — manifest decoding and Smali fallback.

Each backend's contribution is recorded per analysis; backend failures are
captured as values and surfaced in the report instead of aborting the run.

## Honest limitations

- Android dynamic analysis, native (`so`) reverse engineering, and
  anti-obfuscation/unpacking are out of scope.
- The agent is a bounded single-loop assistant over a completed analysis; it
  is not a general autonomous vulnerability finder, and its default budget
  and known open issues are documented.
- The current release is `v1.1.0` (tagged 2026-11-25); the public contract
  covers the documented CLI/API/MCP surfaces.

## Links

- Repository: <https://github.com/gg320324492-lgtm/dexatlas>
- Case studies: [docs/case-studies/README.md](../case-studies/README.md) in the
  repository
- Benchmark reports: `docs/benchmarks/` in the repository
- Evidence packages, one per case study, each a zip holding the report and a
  manifest of hashes:
  [demo-evidence-package.zip](../case-studies/attachments/demo-evidence-package.zip),
  [obfuscated-evidence-package.zip](../case-studies/attachments/obfuscated-evidence-package.zip),
  [api-integration-evidence-package.zip](../case-studies/attachments/api-integration-evidence-package.zip)
- How to read the three walkthroughs: they cover **three first-party samples**
  — `examples/demo-app/demo.apk`, `examples/obfuscated-app/obfuscated.apk`, and
  a multi-DEX appendix on `examples/multidex-app/multidex.apk` — while the three
  evidence packages hold **only two analyses**: the demo and api-integration
  packages are the same analysis run (same APK, same run id), so their
  `report.md` and `report.html` are byte-identical and only `report.json` and
  `manifest.json` differ. They are not client cases: this is my own
  open-source work on first-party samples.

---

*Draft for review — not published. Personal project; no client engagement is
described or implied.*
