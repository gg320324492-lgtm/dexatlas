# Initialize project structure, CI and developer tooling

**Priority:** P0 · **Roadmap:** [Phase 1](../../../../docs/roadmap/ROADMAP.md)

Establish the repository skeleton, tooling and automation that every later issue depends on.

## Scope

- `pyproject.toml` with Python 3.12+, `uv` dependency management, `hatchling` build
- `ruff` (lint + format), `mypy` in strict mode, `pytest` with coverage
- GitHub Actions covering lint, tests, coverage threshold, backend integration, Docker
  build and dependency audit
- Dockerfile and `docker-compose.yml` for local-first deployment
- `.gitignore`, `.gitattributes`, `.editorconfig`
- Apache-2.0 `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `CHANGELOG.md`
- Issue and pull-request templates
- English and Chinese READMEs that distinguish shipped features from planned ones

## Design decisions to record

- Analysis engines are invoked as subprocesses and are **never vendored or linked**.
  This keeps their licence obligations and parsing bugs separate from ours.
- `defusedxml` is a hard dependency: `AndroidManifest.xml` is untrusted input, and a
  plain XML parser is a denial-of-service vector.
- One Python core package. Later phases add agent, MCP and web directories, but must
  not duplicate analysis logic.

## Acceptance

- [x] `uv sync --extra dev` sets up a working environment on a clean machine
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass
- [x] CI runs every check on push and pull request
- [x] Docker image builds and can run the CLI
- [x] Licence and contribution documents are in place

## Notes

`mypy` strict surfaced a real defect during this work: the pipeline passed an
`ApkMetadata` object where a `Path` was expected, which would have failed on every
analysis once a backend was actually installed. Unit tests with no backends present
did not catch it.
