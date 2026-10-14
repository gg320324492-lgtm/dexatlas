# Integrate Apktool and Smali navigation

**Priority:** P0 · **Depends on:** [#001](001-project-structure-ci-tooling.md)

Wrap the `apktool` decoder for `AndroidManifest.xml`, resources and Smali navigation.
Apktool is the **Smali fallback**: when JADX cannot reconstruct a method, the bytecode
is still there, and this backend is what keeps a finding verifiable instead of dropping
it when decompilation fails.

## Scope

- `tools/apktool/adapter.py`: discovery, version probe, decoding, manifest parsing
- Parse package, `versionCode` / `versionName`, `uses-sdk`, permissions and components
- Record exported components, intent filters and permission guards
- Locate and read a class's Smali from `smali*/<package path>/<Class>.smali`, covering
  the multi-DEX smali directories

## Design decisions

- **Sources are decoded deliberately.** `apktool d -s` skips Smali, which would make
  the fallback path unreachable and defeat the purpose of this backend.
- **`versionCode` and `versionName` are read from `<manifest>`, not `<application>`.**
  This is the Android convention; reading them from the wrong element silently yields
  `None` on every APK. A test caught this.
- **The manifest is parsed with `defusedxml`.** It comes from an untrusted APK.
  `defusedxml` refuses entity declarations, DTDs and external references, so an XXE or
  billion-laughs payload is rejected rather than expanded. `defusedxml` is a hard
  runtime dependency for this reason.
- An absent `exported` attribute is `None`, not `False`. Android 12 and earlier
  exported a component when it had an intent filter; treating absence as not-exported
  understates the attack surface, and treating it as exported overstates it.
- A manifest that will not parse is a recorded error, never an exception. The rest of
  the APK is still worth analysing.

## Acceptance

- [x] Package, versions and SDK levels are parsed from a decoded manifest
- [x] Permissions are parsed, including their protection level
- [x] All component kinds are identified, with exported state and permission guards
- [x] An absent `exported` attribute is not reported as exported
- [x] A malformed manifest is recorded, not raised
- [x] An XXE payload is rejected rather than expanded
- [x] Arbitrary junk input never raises
