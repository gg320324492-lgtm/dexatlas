# Add reproducible fixtures, tests and documentation

**Priority:** P0 · **Depends on:** all other Phase 1 issues

Make it possible for a stranger to verify the project, and for a contributor to change
it without fear.

## Scope

- **No APK is committed to this repository.** A `git clone` should not carry binaries
  whose provenance a reader cannot check from the tree alone.
- Synthetic fixtures built in-process by `tests/conftest.py`
- Third-party fixtures fetched by `scripts/fetch-fixtures.sh`, with source and licence
  recorded in `fixtures/apk/SOURCES.md`
- Unit tests for every module
- CLI smoke tests that actually execute each command
- Subprocess-boundary tests: timeout, non-zero exit, missing executable, non-UTF-8
  output, output truncation, shell-injection resistance
- Documentation: README, roadmap, contribution guide

## Design decisions

- **The suite runs without the `analysis` extra.** Unit tests must not require androguard.
- **Integration tests are marked `slow`** and skip cleanly when their fixture or backend
  is absent, so the fast suite stays fast and hermetic.
- **CLI commands are executed, not just imported.** Rich markup errors and unencodable
  glyphs only surface when a command actually runs — five unpaired `[/dim]` tags shipped
  a CLI that crashed on ordinary commands, and an importing unit test missed every one.
  `tests/test_cli.py` now scans every output string for unpaired markup.
- **Console output must survive a legacy code page.** Windows terminals default to GBK
  on many Chinese installations, where printing `✓` raises `UnicodeEncodeError`
  partway through a command. Streams are reconfigured to UTF-8, and glyphs degrade to
  ASCII when the terminal still cannot render them.
- **Subprocess arguments are lists, never shell strings**, and there is a test that
  proves a path containing shell syntax arrives as a literal argument.

## Acceptance

- [x] No APK, DEX or native library is committed
- [x] Every third-party fixture has a recorded source and licence
- [x] `pytest -m "not slow"` passes with no external tools installed
- [x] `pytest -m slow` passes with backends installed
- [x] Coverage on first-party code is ≥80%
- [x] Every CLI command is exercised by a test that runs it
- [x] Output is correct under a non-UTF-8 console encoding
- [x] A stranger can follow the README and reproduce an analysis

## Remaining before `v0.1.0`

- [ ] Install and Quick Start sections in the README, verified on a clean machine
- [ ] Architecture diagram
- [ ] A demo recording
- [ ] `v0.1.0` release
