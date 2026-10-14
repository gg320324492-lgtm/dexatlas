# Build unified analysis API and CLI

**Priority:** P0 · **Depends on:** [#002](002-apk-ingestion-metadata.md), [#003](003-jadx-backend.md), [#004](004-apktool-smali.md), [#005](005-androguard-symbol-index.md)

One analysis core, reachable from a command line and a REST API. Neither entry point
contains analysis logic of its own.

## Scope

- `core/pipeline.py`: `Analyzer` — orchestrates ingestion, backends, indexing, evidence
- `core/storage.py`: `Store` — SQLite persistence and FTS5 full-text search
- `core/models.py`: the unified analysis model
- `cli/main.py`: Typer application
- `api/app.py`: FastAPI application

## API surface

```text
analyze_apk(apk_path)
get_manifest(project_id)
list_classes(project_id)
get_class_source(project_id, class_name)
get_method_source(project_id, method_id)
find_method_references(project_id, method_id)
search_code(project_id, keyword)
export_report(project_id, format)
```

These are DexAtlas's own interfaces, not passthroughs to any single third-party tool.

## Design decisions

- **A backend failure never aborts a run.** Each step records its own `ToolError`, and
  the project is still persisted. An APK that defeats JADX still yields a manifest, a
  symbol index and a report.
- **Classes from different backends are merged, not overwritten.** Apktool knows the
  manifest declaration; Androguard knows the DEX definition. Both provenance entries are
  kept, flags are unioned, and the more specific class kind wins.
- **Method source prefers Java and falls back to Smali.** That fallback is the entire
  point of #004.
- **FTS5 queries are built as quoted phrases**, with quotes doubled, so user input is
  matched literally and FTS operators cannot be injected.
- **Settings are injected, never resolved internally.** Resolving them inside `Analyzer`
  would bypass dependency overrides and write outside the intended workspace — a bug
  the test suite caught while it was writing into the developer's real project
  directory.
- The API redacts server filesystem paths from error messages. A remote caller has no
  business learning the host's directory layout.

## Acceptance

- [x] CLI and REST API run the same `Analyzer`
- [x] Analysis succeeds with zero, one, or several backends installed
- [x] A project analysed through the CLI is visible to a fresh `Analyzer`
- [x] Class, method, reference and manifest queries work
- [x] Full-text search is scoped per project
- [x] FTS operator characters in a search term are literal, not syntax
- [x] Analysis stays inside its configured workspace
- [x] Re-analysing an APK replaces its symbols rather than duplicating them
