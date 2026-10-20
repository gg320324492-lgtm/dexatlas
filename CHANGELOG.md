# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A status page** — `docs/status.md` says where the project stands and what is left:
  the released versions, the acceptance status of Phase 1, and the gaps that remain.
  It is written in Chinese, like the analysis coverage document.

### Fixed

- **The documentation names the release that shipped each fix.** The Phase 1 execution
  report's opening, the headings of its sections 3.11 – 3.15, and the opening of
  section 6 of the analysis coverage document all described work that had already
  shipped. They now name v0.1.3, which shipped it.
- **The status page named a constant that does not exist.** It referred to a
  `MAX_INSTRUCTION_LIMIT`; the limits the code actually enforces are
  `DEFAULT_METHOD_LIMIT`, `DEFAULT_STRING_LIMIT` and `DEFAULT_INSTRUCTION_LIMIT`.
- **The READMEs pointed at finished work as the current backlog.** The eight tasks that
  planned Phase 1 are archived under `.github/issues/v0.1.0/planned/`; what is
  outstanding is the Phase 1 source review.
- **The v0.1.3 release notes quoted a hand-copied coverage figure.** They said 93.9%,
  which belonged to an earlier tree; the release's own generated report measured
  94.0% (1857/1975 lines) from the tree it was cut from. They now state the
  measured figure.

## [0.1.3] — 2026-10-20

Evidence that points back. A conclusion you cannot point back to is not a
conclusion — this release makes that true of more things than it used to be.

### Added

- **`docs/analysis-provenance.md`** — what each conclusion is actually backed by:
  which backend produces which kind of conclusion, what the four `Provenance`
  fields hold, the real locator format of every backend, and how a reader can
  verify a claim themselves. Every claim in it points at a file and a line, or
  at the output of a real run.
- **Cross-references are evidence now.** The pipeline records one
  `cross_reference` record per called method of the analysed APK. The unit is
  the callee, not the call, and calls into library code stay in the index
  without becoming a conclusion about this application.
- **The decompilation coverage is stated.** The report gained a "Methods
  decompiled by JADX" line and one `observation` record carrying the failed
  methods and the classes JADX wrote no source for. `dexatlas methods` shows a
  "Decompiled" column.
- **The CLI says what it folds.** `dexatlas classes` still shows a short list of
  sources per class, but it now says how many it left out and how to see them:
  `--all` prints every source, `--provenance-limit N` sets the number, and a
  class list cut by `--limit` says so too.
- **Every locator travels.** A locator is now `<tool>:<place>`, where the place
  is relative to the artefact the tool names — the APK for Androguard, the
  output tree for JADX and Apktool. JADX's used to be an absolute path, so a
  report carried a pointer to the machine that produced it and to nothing else;
  the two halves of one record were not even the same kind of thing. A
  workspace indexed before the change still reads back in the current form, so
  no migration is needed.

### Fixed

- **A method id had two spellings.** The methods table and the cross-reference
  table stored the same method differently, so an id copied out of
  `dexatlas methods` never resolved in `dexatlas xrefs` for any method with two
  or more arguments. There is one spelling now — the canonical JVM descriptor —
  in the model, in the store and in the lookup, and a workspace indexed by an
  earlier version still resolves.
- **The report's counts did not match the tables.** Analysing the multi-dex
  sample printed 14 methods where the table held 11 rows. The counts come from
  the tables now, so the number in the report is the number a query returns,
  and the definitions that collapsed into one row keep both provenances.
- **`decompiled` held a different fact than its name.** The flag was set from
  "this method has a code item in the DEX", which is not "JADX decompiled this
  method". It says what it says now: JADX is the only backend that can answer
  the question, so the pipeline reads JADX's own output. A `JADX WARN` comment
  above a method is no longer counted as a failure, and a constructor is
  recognised by having no return type rather than by its name. The database
  column and the API field keep their names; the value under that name changed
  meaning, so an existing workspace holds the old meaning until it is
  re-analysed.
- **The CLI saw less than the API it fronts.** `dexatlas classes` printed the
  first two sources of a class and said nothing, while the REST endpoint
  returned all of them. See "The CLI says what it folds" above.
- **An empty configured path did not disable a backend.** The documented
  three-state semantics — unset means "look on `PATH`", empty means "do not
  use this one", a path means "use this" — were only two states, because an
  empty string was skipped and the lookup fell through to `PATH`. The strict
  `xfail` that recorded the defect is now a plain assertion test.
- **The `LIKE` prefix filter did not escape the underscore.** `--prefix
  com.example.com_ex` also matched `com.example.comXex.Gamma`, because `_` is
  a wildcard in SQL and underscores are legal in Android package names. The
  answer was wrong, not merely fuzzy.
- **The report's account of the cross-reference fix was inverted.** It claimed
  Androguard's `get_descriptor()` returned the canonical spelling; measured on
  4.1.4 it returns the spaced one, which is what made the v0.1.0 fix look
  complete when it was not.
- **The REST endpoint echoed whatever the caller typed.** It returns the
  canonical spelling now, which is the one that can be pasted into the next
  request.
- **The exported-component evidence carried no tool version.** One report held
  `apktool 2.11.1 -> AndroidManifest.xml` next to `apktool ->
  AndroidManifest.xml#/application`: the same tool, the same run, one record
  with a version and one without, and no way to tell "this tool has no
  version" from "nobody filled this in". The backend-error evidence had the
  same hole, and a failure is evidence too. The versions are probed before the
  evidence is built and handed to the builder, so a record cannot be written
  without them; `None` now means exactly one thing — the tool did not run.
- **The report's own figures were written by hand.** They are measured by
  `scripts/refresh-report-figures.py` now, and `tests/test_docs.py` checks the
  report against the code. The refresh converges in one run instead of two, and
  it tells a report that is merely out of date apart from a tree that is
  broken.
- **The source fingerprint depended on line endings.** Git checks out CRLF on
  Windows and LF on Linux, so the same source had two fingerprints and the
  report was declared stale on every platform but the one it was measured on.
- **Nine places where the documentation said one thing and the code did
  another**, plus three smaller ones. The merge rule for a class's `kind` was
  written backwards, the coverage table listed two modules above the threshold
  it claimed to be limited to, two method ids were quoted in a spelling the
  repository does not use, the test file table was missing two files, a code
  block was attributed to the wrong test, the historical test counts were wrong,
  and one section skipped a number. The figures that can be measured now are
  measured, and the ones that were hand-copied are checked by a test.
- **The cross-reference kind said one thing and meant another.** Its
  documentation listed five ways a call can be made; the code only ever
  produced one. It is read from the bytecode instruction now, so a static
  call and a virtual call are distinguishable in the index. `dynamic` is not
  among them: the instructions that would carry it name a call site rather
  than a method, so there is no callee to record.
- **A string constant knew nothing about where it was used.** The fields for
  it existed and were never filled, so a hardcoded key could be found but
  not traced to the method that uses it. The bytecode walk that collects
  cross-references now records the use sites too, at no extra cost. Pool
  entries no instruction loads — type descriptors, member names — still
  have no location, because nothing loads them.
- **The version was wrong in two places at once.** The published packages
  called themselves 0.1.0 after v0.1.1 and v0.1.2 had shipped, and the
  number was written in both the package and the project file. It lives in
  one place now and the build reads it from there.
- **A workflow mistake could not be seen.** A job-level `env:` block used
  `${{ runner.temp }}`, which GitHub does not allow there. The run was
  created and failed without scheduling a single job, with no message and
  nothing to retry — it looked like a platform fault. `actionlint` is part
  of the lint job now, and it applies GitHub's own rules.
- **The Docker build could not read the version.** The dependency layer
  installs before the source is copied, and the build backend needs the
  version file. The image copies that one file into the dependency layer.

### Engineering

- 444 tests (347 fast, 97 integration), up from 275
- First-party coverage 94.0% (1857/1975 lines), up from 89.2%
- `mypy` strict, `ruff` lint and format; the CI workflow covers Python 3.12 and
  3.13, a configuration with one backend deliberately absent, a Docker build, a
  dependency audit, the lint job and a workflow lint

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

[Unreleased]: https://github.com/gg320324492-lgtm/dexatlas/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.3
[0.1.2]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.2
[0.1.1]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.1
[0.1.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0
