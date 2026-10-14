# Integrate Androguard and symbol indexing

**Priority:** P0 · **Depends on:** [#001](001-project-structure-ci-tooling.md)

Build the authoritative symbol index: classes, methods, fields, cross-references and
string constants. JADX gives readable Java and Apktool gives the manifest, but parsing
DEX is what Androguard does — and a decompiler's *text* is the wrong source for
structure.

## Scope

- `tools/androguard/adapter.py`: DEX walking and symbol extraction
- Classes with superclass, interfaces, access flags and member counts
- Methods with descriptor, flags, and whether a body exists (abstract and native
  methods are declared but have nothing to decompile)
- Fields with descriptor, flags and constant values
- Cross-references between methods
- String constants
- Multi-DEX APKs

## Design decisions

- **Cross-references are recovered by walking bytecode.** Androguard 4.x removed its
  xref cache, so a call edge is found by scanning each method's instructions for an
  invoke-form opcode and reading the target from its final operand. The first
  implementation assumed a `get_xref_from()` that no longer exists and returned zero
  references against every real APK.
- **Walk limits are explicit.** Obfuscated APKs carry hundreds of thousands of methods
  and millions of instructions; an unbounded walk is a denial of service against
  ourselves. Method, string and instruction limits are enforced, and hitting one is
  logged rather than silently truncating.
- **This backend runs in-process**, the one exception to the subprocess rule, because
  it is a library rather than a tool. Every step is therefore wrapped so that a
  malformed DEX raises into a recorded `ToolError` and never out.
- **An archive with no DEX is an error, not an empty success.** Androguard returns empty
  lists without raising; reporting that as success would produce a clean-looking report
  for an APK that was never indexed.
- Androguard's loguru output is suppressed for the duration of extraction. On a large
  APK it emits thousands of parse-trace lines that bury the CLI's own output.

## Acceptance

- [x] Classes, methods, fields, references and strings are all extracted from a real APK
- [x] Class names are dotted, with no leading `L` or trailing `;`
- [x] Superclasses and interfaces are recorded
- [x] Cross-references name real methods — constructor calls to `Object.<init>` are
      present, which a broken invoke detection would miss
- [x] Every reference carries provenance
- [x] Multi-DEX APKs are fully indexed
- [x] Limits truncate without crashing
- [x] A non-APK and a missing file are reported, not raised

## Notes

The Androguard 4.x API differs from what its older documentation implies in three ways
that all broke the first implementation, and none would be caught by a mocked test:
`get_dex()` takes no filename, `get_dex_names()` returns a `filter` rather than a list,
and the xref cache is gone. `tests/test_androguard_integration.py` pins all of these
against real DEX.
