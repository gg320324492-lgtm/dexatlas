# Phase 1 remaining work: install docs, architecture diagram, and `v0.1.0` release

**Priority:** P0 · **Milestone:** `v0.1.0`

Phase 1's engineering work is done: ingestion, all three backends, the unified analysis
core, evidence, storage, CLI, REST API and report export are implemented, tested against
real APKs, and green in CI. This issue tracks what remains before the Phase 1 exit
checklist in the [roadmap](../../../docs/roadmap/ROADMAP.md) can be honestly marked complete.

The per-task breakdown that originally planned this work is recorded in
[`.github/issues/v0.1.0/planned/`](planned/), so the design decisions behind each piece
are still recoverable.

## Why this is one issue rather than eight

Seven of the original eight tasks are complete. Creating eight open issues now would
report work as outstanding that already shipped, which misrepresents the project to
anyone reading it — including future maintainers.

## Remaining work

- [x] **Install and Quick Start** — `docs/install.md`, every command run against a
      fresh clone, with its real output shown. Verified end to end: clone → venv →
      install → fetch fixture → analyse → report, including the degraded path with
      no backends installed.
- [x] **Architecture documentation** — `docs/architecture/README.md`, covering the
      pipeline, the division of labour between backends, provenance, evidence levels
      and the security posture.
- [x] **Bundled demo application.** Built from hand-written smali in
      `examples/demo-app/` and rebuildable with `scripts/build-demo-apk.sh`, so it is
      reproducible rather than a mystery binary. `tests/test_demo_app.py` pins the
      numbers the README quotes.
- [x] **Demo recording** — `docs/assets/demo.gif`, rendered from a live run of the real
      CLI rather than staged. Covers backend discovery, the analysis summary, exported
      components, code search, cross-references, decompiled source and the report.
      `scripts/render-demo.py` regenerates it; `tests/test_docs.py` checks the assets
      are valid and that no project id is hard-coded in the capture.
- [x] **`v0.1.0` release** published 2026-10-14, with release notes covering the known
      limitations alongside the features, and a dated `CHANGELOG.md` entry.

---

## Outcome

**Phase 1 is complete.** All eleven exit-checklist items pass. The next step is the
[Phase 1 source review](../../../docs/roadmap/ROADMAP.md#review-protocol), after which
Phase 2's issues get written from that review rather than from this plan.

## Exit checklist status

| Item                                                     | Status       |
| -------------------------------------------------------- | ------------ |
| Import and index pipeline verified against test APKs     | Done         |
| JADX, Apktool and Androguard callable, failures handled  | Done         |
| CLI and REST API share the analysis core                  | Done         |
| Classes, methods, references and evidence locations queryable | Done       |
| JSON and Markdown export                                  | Done         |
| Unit and end-to-end tests, ≥80% coverage on first-party code | Done (88%) |
| GitHub Actions green                                      | Done         |
| Installation guide verified on a clean machine            | Done         |
| Architecture documentation                                | Done         |
| Demo application bundled with the repository            | Done         |
| Demo recording                                            | Done         |
| `v0.1.0` release                                          | Done         |

**A stranger can now clone, install, analyse the bundled demo application and read a
report, following the documentation alone.** What remains is the release itself.

## Verification before closing

- [x] Clone into a fresh directory with no JADX or Apktool installed
- [x] Follow only the documentation, start to finish, to a rendered report
- [x] Rebuild the demo APK from its sources and confirm the analysis is unchanged
- [x] Regenerate the demo recording and confirm every frame is a real run
- [x] Confirm `dexatlas backends` degrades gracefully when nothing is installed
