# Integrate JADX decompilation backend

**Priority:** P0 · **Depends on:** [#001](001-project-structure-ci-tooling.md)

Wrap the `jadx` CLI as a subprocess adapter and extract class structure and method
bodies from its Java output.

## Scope

- `tools/jadx/adapter.py`: discovery, version probe, decompilation, extraction
- Class indexing from `sources/**/*.java`, with package-aware name resolution
- Class source retrieval, including nested and anonymous classes that share their
  outer class's file
- Method body extraction by brace matching
- Detection of JADX's decompilation-failure placeholders
- `tools/base.py`: the shared `Backend` interface and subprocess execution

## Failure modes that must be values, not exceptions

- **JADX not installed.** Recorded as `NOT_INSTALLED`; analysis continues without it.
- **JADX exits non-zero after partial success.** This is normal on obfuscated input.
  Its output directory is usually populated, so extraction proceeds and the error is
  attached to the project.
- **A single method fails to decompile.** JADX emits a placeholder body; that method is
  marked `decompiled=False` and retains a Smali fallback path.

## Design decisions

- Brace matching skips string literals and comments, so a `}` inside a string cannot
  truncate a method body into a snippet that looks complete.
- Only *top-level* methods are returned. A method body that cannot be isolated
  unambiguously returns `None`, surfaced as "no decompiled source" rather than a guess.
- JADX output is stored verbatim. What DexAtlas unifies is the index and metadata, not
  the representation — a JADX failure and an Apktool Smali body stay different things.

## Acceptance

- [x] Class names are dotted and derived from both the package declaration and the path
- [x] Class kind (class / interface / enum) is detected
- [x] Top-level methods are located; `if` / `for` / `while` blocks never register
- [x] A method body containing a `}` inside a string literal is extracted whole
- [x] Nested classes resolve to their outer class's file
- [x] Decompilation-failure placeholders are recognised as not decompiled
