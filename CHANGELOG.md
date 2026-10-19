# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing changed yet.

## [0.1.2] — 2026-10-20

The Phase 1 acceptance checklist, actually met. Five test APKs built by this
project, a demo video, and a correction to how the checklist had been recorded.

### Added

- **Five self-built test APKs**, the number the Phase 1 acceptance checklist asks
  for. Each covers a different layout, and each is built from the smali sources
  committed beside it, so none is a mystery binary:
  - `demo-app` — the general case: components, permissions, cross-references
  - `multidex-app` — two dexes, so `smali/` and `smali_classes2/` both exist, and
    one class name appears in both
  - `obfuscated-app` — one-letter packages, classes and methods, no source hints
  - `strings-app` — mostly string constants, for the search index
  - `wide-app` — an interface with two implementations and a factory
- `scripts/build-test-apks.sh` rebuilds all five from source;
  `scripts/build-demo-apk.sh` now delegates to it
- **A demo video** at `docs/assets/demo.mp4`, encoded from the same frames as the
  README's GIFs, so the two cannot drift apart
- Tests that keep the acceptance checklist honest: every committed APK must have
  its smali sources beside it, the build script's sample list must match what is
  on disk, and the set of APKs allowed in the repository is derived from the
  filesystem rather than written out by hand

### Fixed

- **The Phase 1 exit checklist had been paraphrased into something easier to tick.**
  The plan asks for "five **self-built** test APKs" and a "demo **video**"; the
  checklist said "verified against test APKs" and "a generated demo recording",
  and every box was ticked. One self-built sample and a GIF are not five samples
  and a video. The wording is now the plan's own, and the items behind it exist.

### Engineering

- 275 tests (196 fast, 79 integration), up from 244
- First-party coverage 89.2% (1525/1709 lines)
- `mypy` strict, `ruff` lint and format, GitHub Actions green on Python 3.12 and 3.13

### Known limitations

- The samples are small — the largest is under 3 KB. The *layouts* are covered, the
  *scale* is not: there is still no large-APK data point, so index performance and
  the instruction limits have never been under real load
- The obfuscated sample is hand-written obfuscation, not a realistically hardened APK

## [0.1.1] — 2026-10-19

Foundation Hardening. The Smali fallback — the mechanism that keeps a finding
verifiable when decompilation fails — had never run, for any APK.

### Fixed

- **The Smali fallback never worked for any APK.** `smali_path()` searched for the
  per-dex directories *inside* `smali/`, but Apktool writes `classes2.dex` to
  `smali_classes2/`, a sibling rather than a child. Single-dex APKs failed too: the
  glob only ever matched subdirectories of `smali/` whose name began with "smali", and
  a normally decoded APK has none, so the function returned `None` for every class.
  A source request reported "No source" while the decoded Smali sat in the workspace,
  with no error recorded anywhere. The directories are now discovered as siblings
  under the output directory and searched in sorted order, so a class present in two
  dexes resolves to the same file on every call.
- **A hostile class name could crash the analysis.** The name was joined into a path
  without validation, so `....//....//etc/passwd` raised `ValueError` from
  `Path.with_suffix()`. A name that is not a class name now returns `None`, which is
  what the rest of the architecture expects: backend failure is a value, not an
  exception.

### Added

- Unit coverage for the three Apktool directory layouts, deterministic resolution of
  duplicate class names, and eight path-traversal payloads
- An integration test that analyses a real two-dex APK with JADX made unavailable, so
  the Smali fallback is the thing actually under test
- A check that the fixture-fetching script and the integration tests agree on the
  fixture list, in both directions — a test that skips because its fixture was never
  fetched is a regression guard that has silently disappeared

### Engineering

- 244 tests (192 fast, 52 integration), up from 208
- First-party coverage 89.1% (1523/1709 lines), up from 87.8%. The Apktool adapter
  went from 82.7% to 94%
- `mypy` strict, `ruff` lint and format, GitHub Actions green on Python 3.12 and 3.13

### Known issues

- **An empty backend path does not disable that backend**, although `settings.py`
  documents that it should. The path is skipped and a `PATH` lookup follows. Recorded
  as a strict `xfail` test so it cannot be forgotten; see the execution report.

## [0.1.0] — 2026-10-14

Phase 1 — Functional Foundation. A working static analysis pipeline that operates with
every language model switched off.

### Added

- **APK ingestion** — ZIP and Android-marker validation, streamed SHA-256 content
  addressing, DEX / native library / signature inspection
- **JADX backend** — Java decompilation, class indexing, method body extraction by
  brace matching, and detection of JADX's decompilation-failure placeholders
- **Apktool backend** — manifest parsing (package, versions, permissions, components,
  exported state) and Smali navigation as the fallback when decompilation fails
- **Androguard backend** — the symbol index: classes, methods, fields, cross-references
  recovered by walking bytecode, and string constants
- **Unified analysis model** — every fact carries provenance: source tool, tool version,
  APK hash and code location
- **Evidence levels** — `verified` / `lead` / `insufficient`, so an ungrounded claim can
  never be presented as a confirmed finding
- **Storage and search** — SQLite with FTS5 full-text search over indexed symbols
- **CLI** — `analyze`, `projects`, `classes`, `methods`, `source`, `search`, `manifest`,
  `xrefs`, `backends`
- **REST API** — the same analysis core over FastAPI, including upload, query and
  report export endpoints
- **Report export** — JSON and Markdown, with backend errors surfaced rather than
  omitted
- **Bundled demo application** — built from smali sources in `examples/demo-app/`,
  rebuildable with `scripts/build-demo-apk.sh`, so a stranger can analyse something
  immediately after cloning
- **Generated demo recordings** — `docs/assets/demo.gif` and `demo-quick.gif`,
  rendered from a live run of the real CLI by `scripts/render-demo.py`. Not staged:
  the capture script reads the project id its own run produced, so the recording
  cannot show a value a reader could not reproduce

### Engineering

- 208 tests, 88% coverage on first-party code
- `mypy` strict, `ruff` lint and format, all green in CI on Python 3.12 and 3.13
- Docker image with JADX, Apktool and Androguard verified to run at build time
- Dependency audit via `pip-audit` over the resolved lock file
- Installation and architecture documentation, every install command verified against
  a fresh clone
- No APK, DEX or native library is committed to the repository

[Unreleased]: https://github.com/gg320324492-lgtm/dexatlas/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.2
[0.1.1]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.1
[0.1.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0
