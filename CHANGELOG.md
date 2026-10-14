# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing changed yet.

## [0.1.0] — unreleased

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

- 204 tests, 88% coverage on first-party code
- `mypy` strict, `ruff` lint and format, all green in CI on Python 3.12 and 3.13
- Docker image with JADX, Apktool and Androguard verified to run at build time
- Dependency audit via `pip-audit` over the resolved lock file
- Installation and architecture documentation, every install command verified against
  a fresh clone
- No APK, DEX or native library is committed to the repository

[Unreleased]: https://github.com/gg320324492-lgtm/dexatlas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0
