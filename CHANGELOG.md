# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A status page** — `docs/status.md` says where the project stands and what is left:
  the released versions, the acceptance status of Phase 1, and the gaps that remain.
  It is written in Chinese, like the analysis coverage document. Its test count and
  coverage are now written by the same script that writes the execution report's, so
  the page cannot drift away from the measurement it summarises.
- **The APK's resource table is in the index.** Apktool decoded `res/` into the
  workspace and nothing read it: the demo app's `DexAtlas Demo` — a string that
  exists only in `res/values/strings.xml` — was in no index at all, and a key written
  only in a resource file could not be found. The text declarations in `res/values*/`
  are read now, each row carrying the provenance of the file that declared it, and
  they are queryable through `dexatlas resources` and `GET /projects/{id}/resources`.
  Text hard-coded in a layout is still not covered, and the document says so.
- **A source says which backend produced it.** `class_source` returned Smali or Java
  with nothing to tell the two apart, so a caller could not know the difference
  without inspecting the workspace. `class_source_document` and `method_source_document`
  return the text together with its kind, its provenance and the version of the tool
  that wrote it; the REST API reports the same in response headers. The plain-text
  response body is unchanged.
- **The version claims in the documentation are checked.** `check-doc-citations.py`
  proves that a `file:line` citation still points at what it names, but a sentence
  like "the newest tag is v0.1.2" is not a line number and nothing could see it go
  stale. `scripts/check-version-claims.py` reads the tags, the package version, the
  changelog and the generated figures out of the repository and reports the claims
  that contradict them. It runs in CI, and it runs there too.
- **A benchmark for APKs large enough to reach the limits.** The committed samples
  are under 3 KB, so the three limits in the Androguard adapter had never been
  pressed against a real file and what would happen on a large APK was a guess.
  `scripts/generate-large-apk.py` writes a synthetic APK of a chosen size and a
  ground-truth manifest of what it wrote; `docs/benchmarks/large-apk.md` is the
  measurement, and it says what it did not measure. The pressure test found three
  real defects, all fixed — see below.

### Fixed

- **A method asked for by name could be the wrong one.** `read_method_source` took
  the first declaration whose *name* matched and returned it, so a class with two
  overloads of `sign` answered every request for `sign` with whichever one the
  decompiler happened to write first — and the body of the wrong overload reads
  exactly like the body of the right one, all the way into an agent's answer. The
  DEX descriptor tells two overloads apart, and the symbol index already held it:
  a request may now carry one (`--descriptor` on the command line, `?descriptor=`
  in the API), and a name that matches several methods is reported as an ambiguity
  rather than resolved by guessing — the candidates and their descriptors are in
  the error, so the caller can ask again and be sure of the answer. The CLI says
  so with an exit code of its own (4), the API with `409`; `1` (nothing there),
  `2` (a wrong request) and `3` (the analysis failed) still mean what they meant.
  A name that matches exactly one method is answered as before, and so is a
  request that carries a descriptor: the old call sites keep working.
- **A method of a nested class could be the outer class's method.** A decompiler
  writes a nested class into the file of the class that holds it, so one file
  holds several classes, and the lookup read the whole file. A request for
  `Outer$Inner.f` could be answered with `Outer.f`. The methods are now read
  from the class the request names.
- **A class name could walk out of the decompiler's output tree.** The JADX backend
  turned a class name into a path without checking any part of it, so a name that
  was already a path — absolute, with a drive letter, with a UNC prefix — was
  honoured as one, and the file it named was read and served. The Apktool backend
  had checked every part; the rules now live in one place (`dexatlas.core.paths`)
  and both backends use them, so they cannot drift apart. A name that fails the
  check is "no such class" — a 404, not a 500 whose traceback carries the
  server's own directories.
- **The API published the server's paths.** `apk_path` and the JSON report's
  `project.apk.path` carried the absolute path of the analysed file, and a
  manifest parse error carried the absolute path of the decoded file. The file's
  *name* is published now, the workspace root is redacted from error details, and
  the promise the architecture document makes — that the API redacts server paths
  — holds in more than the one place it used to.
- **An upload was read into memory in one piece, and an archive could ask for
  gigabytes.** The upload is streamed and counted, and refused at 256 MiB while it
  streams — never held in memory, never written in full. An archive whose
  declared contents exceed 2 GiB, or that expands more than a hundredfold, is
  refused from its ZIP central directory, before a byte of it is decompressed.
  The same APK was also inspected twice — once by the API and once by the
  analysis — and is inspected once now.
- **A backend that outlived its timeout was not stopped.** The timeout killed the
  process that was started, which for JADX is a `cmd.exe` whose child is the
  `java.exe` doing the work: the work carried on, held the output the caller was
  waiting on, and the call waited for it anyway. The whole tree is taken down
  now — a process group on POSIX, `taskkill /T` on Windows — and the message says
  "could not be terminated" when it could not be.
- **The default deployment published an unauthenticated API on every interface.**
  The API has no authentication by design; it is a single-user tool. But
  `docker-compose.yml` published it on `0.0.0.0` and the installation guide
  taught the same command. Both publish on `127.0.0.1` now, and the guide says
  what exposing it means and what a reverse proxy in front of it is for. The
  server inside the container still binds `0.0.0.0` — it has to, or the port
  mapping would find nothing to connect to.
- **The OpenAPI schema did not describe the source endpoints.** They answer with
  the source text by default and with a JSON document on request, and both carry
  `X-DexAtlas-Source-*` headers; the schema claimed JSON with an empty body. It
  says what the endpoints actually return now, headers included.
- **The backend's version was read once per indexed symbol.** Every class, method,
  field and cross-reference carries a provenance record, and every record asked the
  backend for its version — a query that scans the installed distributions. On a
  12,000-method APK, 80 of the 82 seconds of the run went on that. The version is
  now asked once.
- **Reaching a limit truncated the index silently.** The three limits in the
  Androguard adapter stopped the walk and logged a warning; the project then reported
  `completed` with no errors, and the report's counts matched the rows in the
  database exactly — because both faithfully recorded an index that had been cut
  short. A limit now records an `output_truncated` error that names the limit and
  says what was missed, so the gap is stated beside the numbers instead of hidden
  inside them.
- **Two of the three limits were counted per DEX file.** A four-dex APK got four
  times the allowance, so the largest APKs got the most headroom — the opposite of
  what a limit is for. All three are now one budget per analysis.

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
- **The `[0.1.0]` entry counted 208 tests; the release shipped 204.** A commit made
  after the release overwrote the entry with the test count of the tree at the time.
  The tag measures 204, and the v0.1.0 release notes said 204. The `[0.1.1]` entry
  inherited it as "up from 208", and now says 204.
- **The README's badges had stopped at v0.1.2.** They showed 275 tests and 89%
  coverage — that release's numbers — while the project was on 444 tests and 94.0%.
  A badge URL cannot carry a generated figure, so this is a number to write and
  re-check, not one that can be measured. The badge is written from the
  measurement now — see the review findings below.

### Found by the Phase 1 source review

The review ran three parallel audits against the tree and produced 44 findings;
every one was re-verified on the tree it was found on, and the ones that are
fixed below are fixed with a test that goes red when the fix is reverted.
The review report is `docs/reports/phase1-review-report.md`.

- **An upload's file name was the client's to choose.** Two different APKs
  uploaded under the same name landed on the same path, and the analysis of the
  first one reads that path in the background — so it read the *second* APK's
  bytes, and the project it produced said it held the first APK's classes.
  Nothing a reader could check contradicted the record: the project's hash was
  the first APK's, its identifier was the first APK's, and every provenance
  record named the first APK's hash. The file is stored under its own hash now,
  so two uploads share a path only when they are the same bytes.
- **The default configuration did not decompile Java.** The default workspace is
  a relative path, and the JADX backend handed the same relative path to the
  child process twice — once as `--output-dir` and once as its working
  directory. The path was read against two different bases, so the sources
  landed in a nested copy of the tree the index reads: the report lost the
  decompilation row, the class count dropped by one, and the source fell back
  to Smali — while the tool-version line still credited jadx. Every path a
  backend is handed now means one place, and CI runs the default configuration
  end to end.
- **A read of the database was a write.** The journal mode is a property of the
  database rather than of the connection, and setting it is a write — so every
  read took the one write lock SQLite allows, and a second request failed with
  `database is locked`. It is set once, where the database is created.
- **An analysis that crashed left the project running forever.** The pipeline
  documented that failures are recorded on the project rather than raised, and
  did neither: an exception left the project in `running` with no error
  recorded, and the API answered every later upload of that APK with the
  existing project — so it was never analysed again. A failure now lands the
  project in `failed` with the error on it, and the exception still reaches the
  caller.
  The three kinds of failure are told apart by the exit code: 1 is an empty
  answer, 2 is a wrong request, and **3 is an analysis that broke** — a code
  of its own, so a caller that reads only the exit code can tell a run that
  found nothing from a run that fell over.
  The failure's message is redacted where it is written. An exception's message
  can quote the path it was handed, and that path names the machine the
  analysis ran on; the message is read back through the API, through the JSON
  report and through the Markdown report, so it is redacted once rather than
  three times. The workspace root becomes a placeholder and the path inside it
  survives — that is the part that says what was being worked on.
- **The liveness probe wrote to the database.** `GET /health` built a whole
  analyzer, which opened the workspace and took the write lock, on every
  request. Which backends are installed is a fact about the machine, not about
  the database, and the probe no longer opens one.
- **Two numbers that sat next to each other counted different things.** The
  report's "cross-references with evidence" counted the called methods that
  got a record, while the "cross-references indexed" beside it counted the
  calls — so a method called from three places read as "one of three had
  evidence". Both now count edges, in the same unit, and the report says which
  is which.
- **The evidence table dropped the conclusion it was making room for.** With
  more than 200 classes, the decompilation-coverage record fell outside the
  window: the metric was still in the report and the evidence behind it was
  not. The evidence is ordered so the conclusions come first, and the report
  says how many records were left out and what they were.
- **The exported report said the analysis took no time.** The API rebuilt the
  result from storage and did not restore the duration — and the database had
  no column for it. It is stored now, and an old workspace says "unknown"
  rather than "0.0 seconds".
- **The numbers in the report were compared with themselves.** The suite and
  coverage figures were checked against the record written next to them, so
  writing "999" into both changed nothing anybody could see, and the
  fingerprint that declares them stale covered only the source — adding a test
  did not make them stale. They are measured now, and the fingerprint covers
  the suite and the tools that measure it.
- **The citation checker checked 18 of 94 references, and always passed.** The
  script's `main()` returned 0 whatever it found, and the test re-implemented
  the rules with a different tolerance. Ninety-three of the ninety-four
  references are checked now, and a drifted one fails the check.
- **The version-claim checker passed on the case it was built for.** A commit
  that released a version while the documents still denied it was classified as
  drift the base already had, and the check passed. The base commit is now
  judged against its own facts.
- **A behaviour could be published as a finding.** The evidence level was
  documented as the mechanism that stops an unverified claim from being
  reported as one, and nothing stopped a caller from recording a behaviour as
  verified — which the report renders as "deterministically established by an
  analysis tool". A model cannot promote itself now.
- **The readmes' badges were written by hand.** A badge is a URL, so it cannot
  carry a generated figure, so its number was copied — and it was stale. The
  badge is written from the same measurement the report is written from, and a
  run that does not account for every test in the tree is refused rather than
  published.

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

- 244 tests (192 fast, 52 integration), up from 204
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

- 204 tests, 88% coverage on first-party code
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
