# Implement APK ingestion and metadata extraction

**Priority:** P0 · **Depends on:** [#001](001-project-structure-ci-tooling.md)

Validate and characterise an APK before any backend touches it. This runs using only
the standard library, so a file we reject never reaches an external engine.

## Scope

- `core/ingest.py`: `validate_apk` and `inspect_apk`
- File type validation: not a file, empty, not a ZIP, corrupt entry, no Android markers
- SHA-256 content hashing, streamed so a multi-gigabyte APK is not loaded into memory
- Archive inspection: entry count, DEX files, native libraries, signature presence
- `ApkValidationError` for every rejection path, each with a message a user can act on

## Design decisions

- Content-addressed project ids (`apk_<sha256[:16]>`): re-analysing the same APK
  replaces the project rather than accumulating duplicates.
- Reject a ZIP without `AndroidManifest.xml`, `classes.dex` or `resources.arsc`. It is
  not an Android package, and no backend will produce anything useful from it.
- Verify the whole central directory with `testzip()` rather than trusting the
  extension — a truncated APK is common and must be rejected before dispatch.

## Acceptance

- [x] A minimal synthetic APK passes validation
- [x] A plain text file, an empty file, a missing file and a marker-less ZIP are each
      rejected with a specific message
- [x] Multi-DEX APKs report every `classes*.dex`
- [x] Native libraries under `lib/<abi>/` are listed
- [x] The same file content yields the same hash and project id

## Notes

No APK is committed to this repository. Fixtures are generated in-process by
`tests/conftest.py`; third-party APKs used by the integration suite are fetched by
`scripts/fetch-fixtures.sh` and documented in `fixtures/apk/SOURCES.md`.
