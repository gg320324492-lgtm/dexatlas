# Case study 1 — From upload to evidence chain

**Sample:** [`examples/demo-app/demo.apk`](../../examples/demo-app/demo.apk)
(sha256 `80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9`)
**Run:** one `dexatlas analyze`, 4.9 s
**Backends:** androguard 4.1.4, apktool 2.11.1, jadx 1.5.2
**Who this is for:** a developer or security researcher who wants to see, end to
end, what an analysis produces and how each claim traces back to the code it
was read from.

---

## 1. Background

`demo-app` is a deliberately small five-class application. It is not a real
product — it is a sample with recognisable shapes in it: an exported activity
and service with no permission guard, a crypto helper, a network client, a
key-shaped string constant. Its purpose is to be analysed immediately after
cloning, with nothing to download, and to exercise every part of the pipeline
without any of them being obscured.

This walkthrough follows the full path a user takes: analyze the APK, read the
manifest, search the index, open source, follow a cross-reference, and land on
the evidence records that say where every number came from. Every step was run
with the commands shown, in one workspace, and the outputs quoted are the
actual outputs of those commands.

## 2. The analysis

```bash
uv run dexatlas analyze examples/demo-app/demo.apk
```

```
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges,
  1 resource string (5.0s)
```

The project id is the sha256 prefix of the APK, so re-running the same bytes
lands on the same project. The summary counts come from the run's report:

| Metric | Value |
|---|---:|
| Classes indexed | 5 |
| Methods indexed | 8 |
| Methods decompiled by jadx | 7 of 8 |
| Call sites indexed | 23 |
| Call edges indexed | 21 |
| Cross-reference records | 3 |
| Evidence records | 11 |
| DEX files | 1 |
| Analysis time | 4.9 s |

Eight of the nine indexes are complete for this sample; jadx decompiled 7 of 8
methods and 5 of 5 classes. The one method jadx did not decompile is not a
silence — the report's decompilation evidence (E-0007, below) records the
count, and the class in question still has its smali representation available
through the apktool fallback.

## 3. The manifest

```bash
uv run dexatlas manifest apk_80a8fe0e81204c9f
```

```
com.example.demo
  version    1.0 (1)
  sdk        min 24 / target 34
  permissions 1
  components  3

Exported components
  activity   com.example.demo.MainActivity  no permission guard
  service    com.example.demo.SyncService   no permission guard
```

Two facts a reviewer would care about, both deterministically read: the app
declares `android.permission.INTERNET` and nothing else, and both exported
components are reachable without a permission check. In the evidence table
these are E-0002 (package, versions, SDK levels — read by apktool from the
decoded manifest) and E-0003 (the two exported components — apktool, locator
`apktool:AndroidManifest.xml#/application`). The SDK levels themselves come
from a separate record, E-0001, read by androguard from the *binary* manifest —
a deliberate double-read, because apktool writes some of those fields into
`apktool.yml` rather than the decoded XML.

## 4. Searching the index

```bash
uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"
```

The index returns one class and three methods under `com.example.demo.Crypto`,
plus the string constants that mention it. Searching for the credential-shaped
constant the app carries:

```bash
uv run dexatlas search apk_80a8fe0e81204c9f "sk_live"
```

returns one string hit, `sk_live_2f8a91c4e7b3`. The sample's README says this
constant is an inert placeholder placed so that search has something real to
find; the analysis cannot know that, and does not claim to — it reports that
the string is in the app, and where.

## 5. Opening the source

```bash
uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity
```

```
source kind: java
jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java
```

```java
public class MainActivity extends Activity {
    private static final String TAG = "MainActivity";
    private String endpoint = "https://api.example.com/v1";

    public static String describe(String str) {
        return "response: " + str;
    }

    @Override // android.app.Activity
    protected void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        String strDescribe = describe(NetworkClient.post(this.endpoint, Crypto.sign("api_key", "sk_live_2f8a91c4e7b3")));
        Log.i(strDescribe, strDescribe);
    }
}
```

The source line names its own provenance: this is jadx 1.5.2's Java, read from
the `jadx:sources` tree of this run. If jadx had failed here, the same command
would have fallen back to apktool's smali and said so in the same place.

## 6. Following the cross-references

```bash
uv run dexatlas xrefs apk_80a8fe0e81204c9f \
  "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"
```

```
1 call site(s), 1 call edge(s)
  com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V  →
    com.example.demo.MainActivity.describe(...)  classes.dex@34
```

Two counts, two meanings: one *call site* (the one place in the bytecode where
the call happens, at offset 34 of `classes.dex`) and one *call edge* (the
caller → callee relationship). The same query on `Crypto.sign` and
`NetworkClient.post` returns one site and one edge each, all from
`MainActivity.onCreate` — the report's summary carries 23 sites and 21 edges in
total, most of them calls into the JDK and the Android framework.

This is the walk a reviewer does: the app builds a request inside
`onCreate`, signing it with a hardcoded string and posting it to a hardcoded
endpoint. Each step of that reading is backed by a record: E-0004 (`Crypto.sign
is called from 1 caller(s) at 1 call site(s)`), E-0005 (`MainActivity.describe
…`), E-0006 (`NetworkClient.post …`), all level `verified`, all with locators
into `classes.dex`.

## 7. The evidence chain

The run produces eleven evidence records. They are the difference between "the
report says so" and "here is who read what, with which tool version, from
where":

| ID | Level | Kind | Summary (abridged) | Source |
|---|---|---|---|---|
| E-0001 | verified | declaration | SDK levels from the binary manifest: minSdk=24, targetSdk=34 | `androguard 4.1.4 → androguard:AndroidManifest.xml` |
| E-0002 | verified | declaration | Package com.example.demo (1.0, minSdk 24, targetSdk 34) | `apktool 2.11.1 → apktool:AndroidManifest.xml` |
| E-0003 | verified | declaration | 2 components explicitly exported | `apktool 2.11.1 → apktool:AndroidManifest.xml#/application` |
| E-0004 | verified | cross_reference | `Crypto.sign` called from 1 caller, 1 site | `androguard 4.1.4 → classes.dex#…onCreate→…sign` |
| E-0005 | verified | cross_reference | `MainActivity.describe` called from 1 caller, 1 site | `androguard 4.1.4 → classes.dex#…` |
| E-0006 | verified | cross_reference | `NetworkClient.post` called from 1 caller, 1 site | `androguard 4.1.4 → classes.dex#…` |
| E-0007 | verified | observation | jadx produced real Java for 7 of 8 methods in 5 of 5 classes | `jadx 1.5.2 → jadx:sources` |
| E-0008…11 | verified | declaration | Class declarations: Crypto, MainActivity, NetworkClient, SyncService | `androguard 4.1.4 → classes.dex#…` |

Every record carries the full provenance: tool, tool version, the sha256 of
the APK the reading was made from, and a locator that names the file and the
position inside it. Opening the report on screen 8, or via
`analyze -o report.md`, prints the same table — the workbench renders the
renderer's output byte for byte (measured in the
[M4 end-to-end run](../reports/m4-e2e-run.md), 2026-11-14).

## 8. Conclusions and their limits

**Established by the tools** (verified records): the app exports an activity
and a service with no permission guard; it carries a credential-shaped string
constant; `onCreate` passes that constant to a signing helper and posts the
result to a hardcoded `api.example.com` endpoint; the whole surface is four
classes plus one activity, one service.

**Not established here**: whether any of this is exploitable, what the real
endpoint would do, or whether the sample resembles any particular production
app. The sample is first-party and its constants are placeholders by
construction. DexAtlas reports what the bytes contain and where each fact was
read from; impact assessment stays with the reader.

**What a human does next with this**: a reviewer gets an accurate, complete
map of a small app in under five seconds and can spend their time on the two
findings that matter (the unguarded exported components, the credential in the
code) instead of on rebuilding context.

## 9. Exporting the report

```bash
uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json
```

Both renderers read the same workspace; the JSON adds the machine-readable
field-level detail (per-call-site locators, the decompilation breakdown), the
Markdown renders the same records for a human reader. The report is a
deliverable a client can open without installing anything.
