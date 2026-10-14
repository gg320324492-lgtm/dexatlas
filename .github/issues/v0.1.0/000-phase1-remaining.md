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
- [ ] **Bundled demo fixture.** The fixture used above is fetched by a script, which is
      right for tests but not for a demo someone should be able to run from a clone.
      Needs a self-built application, under a licence permitting redistribution,
      committed as a demo asset.
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
| Unit and end-to-end tests, ≥80% coverage on first-party code | Done (87%) |
| GitHub Actions green                                      | Done         |
| Installation guide verified on a clean machine            | Done         |
| Architecture documentation                                | Done         |
| Demo fixture bundled with the repository                  | Not started  |
| `v0.1.0` release and demo video                          | Not started  |

**A stranger can now clone, install, fetch a fixture, analyse it and read a report,
following the documentation alone.** What remains is a fixture that ships with the
repository rather than being fetched by a script, and the release.

## Verification before closing

- [x] Clone into a fresh directory with no JADX or Apktool installed
- [x] Follow only the documentation, start to finish, to a rendered report
- [x] Confirm `dexatlas backends` degrades gracefully when nothing is installed
