# Case study 2 — Reading an obfuscated app (and a multi-DEX appendix)

**Samples:** [`examples/obfuscated-app/obfuscated.apk`](../../examples/obfuscated-app/obfuscated.apk)
(sha256 `2f8d476fb9e71ac4490059c1d9849f22732254cc7e538a7eebe86aca6c299540`);
appendix on [`examples/multidex-app/multidex.apk`](../../examples/multidex-app/multidex.apk)
(sha256 `a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55`)
**Runs:** 5.1 s and 4.8 s
**Backends:** androguard 4.1.4, apktool 2.11.1, jadx 1.5.2
**Who this is for:** a security researcher or analyst whose targets are
obfuscated or multi-DEX, who wants to know what an evidence-first index still
sees when the names are gone.

---

## 1. Background

Real Android malware and aggressively optimized apps hide their structure
behind name mangling: single-letter packages, single-letter classes and
methods, no source-file names. `obfuscated-app` is a first-party sample built
to that shape on purpose — its own smali carries the comment *"Everything a
reader would use to orient themselves is gone, which is the point — the tool
has to cope with names that carry no information."*

It is a hand-written obfuscation, not a commercial packer: there is no control-
flow flattening, no string encryption, no native loading. What it removes is
the *names*, which is the most common and most disorienting layer. The sample
declares dangerous permissions (`ACCESS_FINE_LOCATION`, `READ_PHONE_STATE`,
`SEND_SMS`), two exported components with no permission guard, a telemetry-
shaped URL, and an SMS-shaped string constant — all inert placeholders, all
committed in source beside the APK.

The question this study answers: with every meaningful name destroyed, what
does DexAtlas still establish, and how much of it is verifiable?

## 2. The analysis, and what the index holds

```bash
uv run dexatlas analyze examples/obfuscated-app/obfuscated.apk
```

```
✓ apk_2f8d476fb9e71ac4 — 4 classes, 11 methods, 10 call sites, 9 call edges,
  0 resource strings (5.1s)
```

The index is complete: 4 of 4 classes, all 11 methods, 10 call sites, 9 call
edges. The manifest reads cleanly through apktool despite the mangling:

```
a.a.a
  version    0.1 (1)
  sdk        min 21 / target 30
  permissions 3
  components  4

Exported components
  activity   a.a.a.a   no permission guard
  receiver   a.a.b.a   no permission guard
```

This is the first thing obfuscation does **not** hide. The manifest is
metadata, not code: the package name `a.a.a`, the three dangerous permissions,
and the two unguarded exported components are read from the binary manifest
and recorded as E-0001/E-0002/E-0003, all `verified`.

## 3. What survives in the source

```bash
uv run dexatlas source apk_2f8d476fb9e71ac4 a.a.a
```

```
source kind: java
jadx 1.5.2 -> jadx:sources/a/a/a.java
```

```java
public class a {
    /* JADX WARN: Multi-variable type inference failed */
    public String a(String str) {
        return "https://telemetry.example.net/collect?d=" + ((String) this);
    }
    ...
}
```

jadx decompiled 7 of 11 methods across all 4 classes (E-0004, `verified`,
`jadx 1.5.2 → jadx:sources`). The four it did not decompile are recorded as
such and remain readable as smali through the apktool fallback — the index
keeps both representations, and the `source kind` line says which one a
command returned.

The decompilation is imperfect (the `JADX WARN` above is real), but it is
readable enough to reconstitute the app's behaviour by hand:

- `a.a.a.a(String)` builds a telemetry URL — the class's method names say
  nothing, but the string constant it appends does.
- `a.a.b.a` (the exported receiver) implements `onReceive`, reading
  `intent.getStringExtra("action")`.
- `a.a.b.a(String)` rewrites a string with `"sms_body_prefix"` →
  `"generic_text_message"`.
- `a.b.a` (the service) returns a fake IMEI string and the constant
  `"AES/ECB/PKCS5Padding"`.

## 4. What the string index still finds

Name obfuscation destroys identifiers; it does nothing to string constants.
Searching for the two recognisable substrings:

```bash
uv run dexatlas search apk_2f8d476fb9e71ac4 "telemetry"
uv run dexatlas search apk_2f8d476fb9e71ac4 "sms"
```

Both hit: `https://telemetry.example.net/c…` and `sms_body_prefix`, one string
record each. Each hit carries the provenance of where the constant lives. This
is the practical value of the string index on an obfuscated target: the
analyst can go from a suspicious keyword to the exact method that uses it —
here, from `telemetry` to `a.a.a.a(String)` — without any readable name
helping.

## 5. Cross-references without names

```bash
uv run dexatlas xrefs apk_2f8d476fb9e71ac4 "a.a.a.a(Ljava/lang/String;)Ljava/lang/String;"
```

```
No callers of a.a.a.a(Ljava/lang/String;)Ljava/lang/String;.
```

A reviewer should read this correctly: **no callers is a measurement, not an
excuse**. The sample's classes never call each other — the database's ten call
sites are all calls into `java.lang.*` and `android.*` from the four
placeholder classes, and the method in question is genuinely uncalled within
the DEX. The CLI prints "No callers of …" rather than treating absence of data
as an error, which is the same discipline as the report's `0` counts: a
measured zero, distinguishable from "the tool did not look".

The full picture the index holds, from the call-site table: every application
method's calls land in the JDK or the framework (StringBuilder, String.replace,
Intent.getStringExtra, Object.<init>), and no application-to-application edge
exists. For this sample that is the true structure; for a real target the same
query family maps exactly the edges a reviewer would walk.

## 6. The evidence chain

Eight evidence records, all `verified`, each with tool, version, APK sha256
and locator:

| ID | Kind | Summary (abridged) | Source |
|---|---|---|---|
| E-0001 | declaration | minSdk=21, targetSdk=30 from the binary manifest | `androguard 4.1.4 → androguard:AndroidManifest.xml` |
| E-0002 | declaration | Package a.a.a (0.1, 21, 30) | `apktool 2.11.1 → apktool:AndroidManifest.xml` |
| E-0003 | declaration | 2 components explicitly exported | `apktool 2.11.1 → apktool:AndroidManifest.xml#/application` |
| E-0004 | observation | jadx produced real Java for 7 of 11 methods in 4 of 4 classes | `jadx 1.5.2 → jadx:sources` |
| E-0005…8 | declaration | Class declarations: a.a.a, a.a.b.a, a.a.b, a.b.a | `androguard 4.1.4 → classes.dex#…` |

Every claim in this study resolves to one of these. When this document says
"7 of 11 methods decompiled", that is E-0004's recorded count, not an
impression.

## 7. Conclusions and their limits

**Established by the tools:** the app's identity, permission set and exported
components survive obfuscation intact; the string index still finds the
telemetry URL and the SMS-shaped constant; 7 of 11 methods decompile to
readable Java; the class graph, method table and call-site table are complete;
each of those claims carries a resolvable citation.

**Not established here:** that this sample is malware. It *looks like* the
shape of a telemetry-collecting, SMS-reading, permission-heavy app, and a
human analyst would reasonably treat it as suspicious — but DexAtlas does not
classify, score or allege. The distinction is the point of the evidence model:
the index's job is to make every observation checkable, and to leave the
judgement to the analyst.

**Honest scope note:** this is hand-written obfuscation — stripped names, no
more. Control-flow obfuscation, string encryption and runtime packing are
outside what this sample exercises, and the [status page](../status.md) tracks
real-world hardened samples as an open gap. The comparison that matters here
is with the same code unobfuscated (the demo-app study above): everything the
manifest and string index produce survives untouched, the class/method/call
index is complete in both, and what obfuscation costs is readability of the
decompiled source — 7 of 11 methods versus 7 of 8, with warnings on the
recovered ones.

## Appendix — one class, two DEX files

[`multidex-app`](../../examples/multidex-app/multidex.apk) is a four-class
sample split across `classes.dex` and `classes2.dex`, built to exercise
something subtler than obfuscation: **the same class name defined in both
files.** Its manifest declares one package (`com.example.multidex`) while its
classes live in two DEX containers.

What the index does with that:

```bash
uv run dexatlas classes apk_a488e43e38c2b8e9
```

`SharedConfig` appears **twice**, once per defining DEX:

```
com.example.multidex.SharedConfig class
  androguard 4.1.4 -> androguard:classes.dex#com.example.multidex.SharedConfig
  androguard 4.1.4 -> androguard:classes2.dex#com.example.multidex.SharedConfig
  … 1 more source not shown (use --all to see all 3)
```

The decompiler side records the collision too:

```java
/* JADX WARN: Classes with same name are omitted:
  classes.dex
 */
/* loaded from: classes2.dex */
public class SharedConfig { ... }
```

jadx keeps one copy and warns about the dropped one; androguard's symbol index
keeps **both**, each with a locator naming the DEX file it was read from. The
call-site rows carry a `dex_name` column (`classes.dex` / `classes2.dex`), so
every call site says which container it was read from — the raw material an
analyst needs to reason about what a class-loader would actually resolve.

The summary for this run: 4 classes, 11 methods, 13 call sites, 10 call edges,
evidence records E-0001…E-0008, jadx 7 of 11 methods decompiled, 4.8 s.
