# Security Policy

## Supported versions

DexAtlas is pre-1.0. Security fixes land on the latest `main` and are backported to the
most recent tag.

| Version | Supported |
| ------- | --------- |
| `main`  | ✅        |
| `v0.1.x`| ✅        |
| < `v0.1`| ❌        |

## Reporting a vulnerability

**Do not open a public issue.** Report privately via
[GitHub Security Advisories](https://github.com/gg320324492-lgtm/dexatlas/security/advisories/new).

Please include the affected version, reproduction steps, and impact. You should get an
acknowledgement within 72 hours and a status update within seven days.

If you prefer not to use GitHub advisories, open a regular issue containing only
"Please contact me privately about a security report" and nothing else.

## Scope

In scope:

- Code execution or path traversal triggered by processing a hostile APK, DEX or resource
  archive
- Injection in DexAtlas's own CLI, REST API or MCP surface
- Unsafe deserialization of uploaded or analyzed artifacts
- Unintended execution of an external analysis backend with attacker-controlled arguments
- Leakage of files or secrets outside the intended workspace

Out of scope:

- Findings in JADX, Apktool, Androguard, Ghidra, Rizin or Frida themselves — report those
  upstream. We will happily help coordinate.
- Vulnerabilities in applications analysed *with* DexAtlas. This is an analysis tool; a flaw
  in a target APK is a finding, not a bug in DexAtlas.
- Denial of service from deliberately feeding DexAtlas a pathological multi-gigabyte APK.
- Running analysis backends without antivirus or in an untrusted container.

## Analysis safety model

DexAtlas treats every analysed artifact as untrusted input.

- **Read-only by default.** Analysis does not modify the APK or the host system.
- **Subprocess isolation.** External engines run as separate processes, never linked into
  the Python process, so their parsing bugs are not ours to inherit.
- **No shell.** Backend invocations use argument arrays, never a shell string, so APK
  contents cannot inject commands.
- **Workspace scoping.** Extracted artifacts are written under the project workspace only.
- **Local-first.** No application data leaves the machine in Phase 1. Phase 2's model
  integration requires explicit, per-request user authorization, and sends only the code
  context a user has selected — never the APK, credentials or device data.
- **Explicit authorization for state-changing operations.** Dynamic instrumentation and any
  operation that mutates a target require deliberate user consent.

## Scope of authorized use

DexAtlas is for applications you own or are authorized to assess. Do not use it to bypass
protections, forge signatures, extract unauthorized data, or analyze third-party
applications without permission. See `Intended Use` in the README.
