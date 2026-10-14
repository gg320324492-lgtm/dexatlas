# DexAtlas demo application

A deliberately small Android application, built from source in this directory, used as
the analysis target in the README and the quick start.

**It is committed** so that a stranger can run an analysis immediately after cloning,
without fetching anything and without needing the Android SDK.

## Provenance

Every byte in `demo.apk` comes from the files next to it:

- `AndroidManifest.xml` — 2 exported components, 1 permission, 2 SDK levels
- `smali/com/example/demo/*.smali` — 4 classes, written by hand
- `res/values/strings.xml` — one string
- `apktool.yml` — build settings

Rebuild and confirm:

```bash
DEXATLAS_APKTOOL_JAR=/path/to/apktool.jar ./scripts/build-demo-apk.sh
```

The rebuild will not be byte-identical (zip timestamps and aapt2 ordering vary). What
matters is that it analyses the same way.

There is no third-party code here, no credentials, no real endpoints, and no user data.
The API host and key-looking string are inert placeholders, present so the analysis has
something recognisable to find.

## What it contains, and why

| Element                       | Why it is there                                          |
| ----------------------------- | -------------------------------------------------------- |
| Exported `activity` + `service` | So the manifest shows exported components with no permission guard — the highest-signal observation DexAtlas reports |
| `Crypto.sign` / `Crypto.obfuscate` | A cross-reference target reachable from `MainActivity.onCreate` |
| `NetworkClient.post`          | A call chain two hops deep, for demonstrating xrefs        |
| `MessageDigest` usage         | A recognisable crypto API reference in the symbol index    |
| A key-shaped string constant  | So `search` has something meaningful to find                |
| `try/catch` in `obfuscate`    | Exercises JADX decompilation of control flow                |

## What a clean analysis looks like

```bash
uv run dexatlas analyze examples/demo-app/demo.apk
```

```text
✓ apk_12cdaf61adea0d1a — 5 classes, 8 methods, 23 cross-references (2.6s)
```

```bash
uv run dexatlas manifest apk_12cdaf61adea0d1a
```

```text
com.example.demo
  version    1.0 (1)
  sdk        min 24 / target 34
  permissions 1
  components 3

Exported components
  activity   com.example.demo.MainActivity  no permission guard
  service    com.example.demo.SyncService  no permission guard
```

The project id is the APK's SHA-256, so it identifies *these exact bytes*. A rebuild
produces different bytes and therefore a different id — use the id your own run prints.
The analysis is identical either way: 5 classes, 8 methods, 23 cross-references.
