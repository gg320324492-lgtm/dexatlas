# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/gg320324492-lgtm/dexatlas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0
