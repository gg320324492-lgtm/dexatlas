# Contributing to DexAtlas

Thanks for your interest. This document explains how to set up a development environment,
what we expect from a pull request, and — importantly — what we will not accept.

## Table of contents

- [Hard rules](#hard-rules)
- [Development setup](#development-setup)
- [Running the checks](#running-the-checks)
- [Adding an analysis backend](#adding-an-analysis-backend)
- [Pull request expectations](#pull-request-expectations)
- [Issue reports](#issue-reports)
- [Code of conduct](#code-of-conduct)

## Hard rules

These are not style preferences. A pull request violating any of them will be closed.

1. **No unauthorized application material.** Do not commit APKs, DEX files, native
   libraries, decompiled source, smali, manifests or resources from any application you do
   not own or have written permission to assess. Test fixtures must be apps you built
   yourself, or ones under a license that permits redistribution.
2. **No credential or PII material.** No keys, tokens, `.env` files, device dumps, or
   captured traffic from real devices or accounts.
3. **No attack tooling.** Signature forging, license bypass, certificate pinning defeat,
   root/hook detection evasion and unauthorized data extraction are out of scope. We will
   not review, merge or ship them, regardless of how they are framed.
4. **No model output presented as confirmed fact.** Any security finding must state whether
   it is verified, a static-analysis lead, or insufficiently evidenced. See the
   [evidence model](docs/roadmap/ROADMAP.md#24-security-analysis-and-reporting).

## Development setup

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and a JDK if you want to run the
JADX or Apktool backends locally.

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
uv sync --extra dev --extra analysis
uv run pytest
```

Analysis backends are external binaries discovered from `PATH` or set through environment
variables. DexAtlas degrades gracefully: a backend that is missing or crashes produces a
recorded error for that step, not a failed analysis. Backends are invoked as subprocesses
and are never vendored into this repository.

## Running the checks

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # strict type checking on src/dexatlas
uv run pytest                # unit tests
uv run pytest --cov=dexatlas --cov-report=term-missing
uv run pytest -m slow        # tests that shell out to real backends
```

CI runs the same commands. Mark a test `@pytest.mark.slow` if it invokes a real external
analysis engine — those need the tool installed and are excluded from the fast suite.

First-party code carries an **80% coverage target**. New code without tests will be asked
for them.

## Adding an analysis backend

Backends implement one interface and live under `src/dexatlas/tools/<name>/`. Keep these
boundaries:

- **Shell out, do not link.** Call the tool as a subprocess. Do not vendor its source or
  import it into our process — that changes its license obligations and its failure modes.
- **Preserve the raw output.** Store what the tool returned. Unify the *index and metadata*,
  never flatten distinct representations into a false common form.
- **Record provenance.** Every extracted item carries source tool, tool version, project
  hash and code location. This is what makes evidence traceable.
- **Fail loudly into the record, never crash the run.** A tool that exits non-zero becomes a
  recorded error attached to the affected results.

## Pull request expectations

- One logical change per PR; keep them reviewable.
- Explain *why*, not just *what*. Link the issue if there is one.
- Update the README or `docs/` if you change a user-facing interface.
- Add or update tests. Bug fixes need a regression test that fails without the fix.
- Add a `CHANGELOG.md` entry under `Unreleased`.
- Make the checks pass locally before pushing.
- Draft PRs and early feedback are welcome — open a draft rather than holding a branch.

## Issue reports

A good report includes:

- What you ran, on which OS, with which DexAtlas version
- The exact command and the full output or traceback
- What you expected and what happened instead
- A **minimal** reproduction

For analysis bugs, the hash of a test APK you built yourself is far more useful than the
APK itself.

## Reporting security issues

Do not open a public issue for a vulnerability in DexAtlas or in an analysis backend it
wraps. See [SECURITY.md](SECURITY.md).

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
