# Phase 1 remaining work: install docs, architecture diagram, and `v0.1.0` release

**Priority:** P0 · **Milestone:** `v0.1.0`

Phase 1's engineering work is done: ingestion, all three backends, the unified analysis
core, evidence, storage, CLI, REST API and report export are implemented, tested against
real APKs, and green in CI. This issue tracks what remains before the Phase 1 exit
checklist in the [roadmap](../../docs/roadmap/ROADMAP.md) can be honestly marked complete.

The per-issue breakdown that originally planned this work is recorded in
`.github/issues/v0.1.0/` and in the git history, so the design decisions behind each
piece are still recoverable.

## Why this is one issue rather than eight

Seven of the original eight tasks are complete. Creating eight open issues now would
report work as outstanding that already shipped, which misrepresents the project to
anyone reading it — including future maintainers.

## Remaining work

- [ ] **Install and Quick Start** in `README.md`, verified on a genuinely clean machine:
      clone, install, run `dexatlas analyze` against a bundled authorised fixture, read
      the report. The current README says this ships with `v0.1.0`.
- [ ] **Architecture diagram** rendering the pipeline: ingestion → backends → unified
      index → search → evidence → report.
- [ ] **Bundled fixture for the demo.** The Phase 1 demo requires a self-built or
      explicitly licensed APK that ships with the repo. Current fixtures are fetched by
      a script, which is right for tests but not for a stranger following the README.
- [ ] **A short demo recording** (target: 30 seconds) — upload an APK, extract the
      manifest and class structure, search for a call chain, show Java and Smali side by
      side, export a report with evidence attached.
- [ ] **`v0.1.0` release** with notes, and a `CHANGELOG.md` entry.

## Exit checklist status

| Item                                                     | Status       |
| -------------------------------------------------------- | ------------ |
| Import and index pipeline verified against test APKs     | Done         |
| JADX, Apktool and Androguard callable, failures handled  | Done         |
| CLI and REST API share the analysis core                  | Done         |
| Classes, methods, references and evidence locations queryable | Done       |
| JSON and Markdown export                                  | Done         |
| Unit and end-to-end tests, ≥80% coverage on first-party code | Done (86%) |
| GitHub Actions green, README reproducible                  | Partly — CI green, README incomplete |
| `v0.1.0` release and demo video                            | Not started   |

**A stranger can already install DexAtlas and analyse an APK. What they cannot yet do is
learn how from the README alone without reading the source.**

## Verification before closing

- [ ] Clone into a fresh directory on a machine with no JADX, Apktool or Androguard
- [ ] Follow only the README, start to finish, to a rendered report
- [ ] Confirm `dexatlas backends` degrades gracefully when nothing is installed
