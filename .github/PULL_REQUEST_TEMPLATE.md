## What this changes

<!-- One or two sentences. Link the issue: Closes #123 -->

## Why

<!-- The problem, not the solution. Why is the current behaviour wrong or missing? -->

## How

<!-- Anything a reviewer should know before reading the diff: design decisions,
     alternatives rejected, trade-offs accepted. -->

## Checklist

- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy` passes
- [ ] `uv run pytest` passes
- [ ] New or changed behaviour has tests; bug fixes include a regression test
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] No APK, decompiled source, credential, or material from an application I am not
      authorized to analyse is included
- [ ] External analysis backends are still invoked as subprocesses, not vendored
- [ ] User-facing interface changes are reflected in the README or `docs/`
