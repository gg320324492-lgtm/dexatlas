# DexAtlas

An open-source, evidence-first Android static-analysis tool. It takes an APK, runs
three analysis backends (Apktool for the manifest and Smali, JADX for decompiled
Java, Androguard for the authoritative DEX symbol graph), stores the result in a
SQLite workspace, and renders a Markdown/JSON report.

The project's whole point: **a conclusion must trace back to the bytes it came
from.** A reader who follows a report's citations has to arrive at the code the
tool read. Every rule below exists to protect that.

## The rules that are not negotiable

1. **Every bug fix carries a regression test that fails on the previous
   implementation.** Not "the test passes" — *the test goes red when the fix is
   taken away*. Prove it: restore the old version of the file, run the test, show
   it fail.
2. **No production claim without a runnable test, a benchmark, or a documented
   manual verification.** A number nobody can re-derive is not a claim.
3. **The report's numbers are generated, not written.** `<!--fig:...-->` markers
   in `docs/reports/phase1-execution-report.md` are filled in by
   `scripts/refresh-report-figures.py`; the README badge is written by the same
   script. **Do not hand-edit a number.** Change the code, run the script.
4. **The documents' `file:line` citations are checked.** After changing
   anything under `src/`, the cited lines have moved. Re-derive them with
   `python "G:/dexatlas/.scratch/verify/remap_citations.py"`, then run
   `uv run --no-sync python scripts/check-doc-citations.py` and read its output.
   The remapper is not idempotent: reset the two documents to their last
   committed state first, or it will map already-mapped numbers a second time.
5. **Public contracts are preserved or explicitly versioned — never silently
   changed.** A status code, a response shape or a count that means something
   different now is a breaking change; say so loudly.
6. **A milestone is advanced only after source review and acceptance.** Not
   after the code looks finished.
7. **Third-party APKs, DEX, `so`, and secrets stay out of the repository.**
   Samples are either first-party (`examples/`, with their sources alongside) or
   fetched by `scripts/fetch-fixtures.sh` from Apache-2.0 licensed data.

## Running it

```bash
uv sync --extra dev --extra analysis      # once, in your own worktree
uv run --no-sync pytest -q                # the suite
uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
uv run --no-sync mypy                    # strict
uv run --no-sync python scripts/check-doc-citations.py
uv run --no-sync python scripts/check-version-claims.py --base auto
```

`uv sync` creates a `.venv` whose editable install points at *that* directory, so
**every worktree needs its own**. Reusing another checkout's venv silently tests
the wrong code.

### The gates

CI runs six jobs: lint/format/mypy, tests on Python 3.12 (every backend),
tests on Python 3.13 (no external backends), tests with Apktool only, the Docker
image, and the dependency audit. The same configurations are worth running by
hand before a push — the three backend configurations are separate
configurations, not one.

### Measuring the project

`scripts/refresh-report-figures.py` only writes the figures when the
measurement is **complete**: every test ran, none was skipped. A partial run
keeps the previous coverage and the previous suite counts, which leaves the
record describing a tree that no longer exists. The prerequisites are the
backends, the fixtures, Pillow, ffmpeg and the git tags.

## Environment traps this project has already paid for

- **Never `uv sync` in the main checkout from WSL** (or vice versa). It
  overwrites the Windows venv with a Linux one and leaves `cryptography`
  broken in a way `uv sync` refuses to repair because the version already
  matches.
- **Everything this project writes lives in `G:\dexatlas\.scratch`** — the
  analysis backends, the helper scripts, the temporary files, the uv cache. The
  system drive is nearly full. `tests/conftest.py` redirects the temporary
  directory there, so a plain `uv run pytest` writes nothing to the system
  drive.
- **A backend that cannot be found makes its tests skip**, and a skip is not a
  pass. Read the skip count in the summary line, not just the exit code.
- On Windows, `cat >> file <<'EOF'` mixes CRLF and LF line endings and
  `git diff` will not show it. `ruff format --check .` catches it.
- `git push` needs `HTTPS_PROXY=http://127.0.0.1:7897` on this machine.

## Where things are

| | |
|---|---|
| `src/dexatlas/core/` | the analysis model, storage, evidence, the pipeline |
| `src/dexatlas/tools/` | the three backends and the `Backend` interface |
| `src/dexatlas/reports/` | the Markdown and JSON renderers |
| `src/dexatlas/cli/`, `api/` | the two transports over one `Analyzer` |
| `docs/analysis-provenance.md` | which backend produced what, and where it came from |
| `docs/roadmap/phase2-plan.md` | the Phase 2 plan (M0–M4) and the rules above |
| `docs/status.md` | where the project stands, and what is still open |

## The discipline this project is built on

- **Evidence before inference. Correctness before autonomy.** A verified record
  that a tool established, with a citation that resolves inside the analysis. A
  model's output is a lead and can never be promoted to a finding.
- **A backend failure is a value, never an exception.** `Backend.run` returns a
  `ToolOutcome` carrying an optional `ToolError`, and the pipeline branches on
  it. An APK that defeats JADX completely still yields a manifest, an index and
  a report — the report says which steps did not run.
- **Say what the measurement cannot see.** A number that describes a tree which
  no longer exists is a small lie, and this project has collected enough of them.
