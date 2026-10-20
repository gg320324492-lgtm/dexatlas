# Installation

Every command here was run against a fresh clone. Where output is shown, it is what that
command actually printed.

## Requirements

| Requirement     | Version | Notes                                                     |
| --------------- | ------- | --------------------------------------------------------- |
| Python          | 3.12+   | 3.12 and 3.13 are tested in CI                             |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager and environment manager         |
| JDK             | 21+     | Required by the JADX and Apktool backends                   |

Analysis backends are optional and independent — see [Backends](#backends).

## Install

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas

uv venv --python 3.12
uv pip install -e ".[analysis]"
```

The `analysis` extra installs Androguard, which parses DEX in-process. Without it you
still get APK validation, hashing and archive inspection.

### Docker

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
docker build -t dexatlas .
docker run --rm dexatlas dexatlas backends
```

The image carries JADX and Apktool; the build fails if either cannot be downloaded and
run, so a broken backend is caught at build time rather than during your first analysis.

```bash
docker run --rm -p 127.0.0.1:8000:8000 -v dexatlas-workspace:/workspace dexatlas
# API docs at http://localhost:8000/docs
```

The port is published on `127.0.0.1` on purpose. **The REST API has no
authentication**: it lists every project, serves their decompiled sources and
accepts APKs to analyse. Publishing it on every interface would publish the
analysis to the network, so the default is this machine only. See
[Exposing the API](#exposing-the-api) for what to do if you need it elsewhere.

> The container's own server binds `0.0.0.0` — it has to, or the port mapping
> would find nothing to connect to. What is published, and where, is decided on
> the host: by the `-p` argument above, or by the `ports:` entry in
> `docker-compose.yml`.

## Backends

Check what is available:

```bash
uv run dexatlas backends
```

```text
                Analysis backends
┌────────────┬───────────┬──────────────────┐
│ Backend    │    Status │ Version          │
├────────────┼───────────┼──────────────────┤
│ jadx       │ available │ 1.5.6            │
│ apktool    │ available │ 3.0.3            │
│ androguard │ available │ androguard 4.1.4 │
└────────────┴───────────┴──────────────────┘
```

A missing backend is a normal state. DexAtlas reports what it can do with what is
installed and records what it could not do as evidence in the report. With **none**
installed you still get validation, hashing and the APK's own metadata.

### Installing a backend

```bash
# JADX — https://github.com/skylot/jadx/releases
# The archive unpacks into bin/ and lib/ with no version-named directory.
curl -LO https://github.com/skylot/jadx/releases/download/v1.5.2/jadx-1.5.2.zip
unzip -q jadx-1.5.2.zip -d /opt/jadx
export DEXATLAS_JADX_PATH=/opt/jadx/bin/jadx

# Apktool — https://github.com/iBotPeaches/Apktool/releases
curl -LO https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar
export DEXATLAS_APKTOOL_JAR=$PWD/apktool_2.11.1.jar
```

Or let DexAtlas find them on `PATH`:

```bash
export PATH="/opt/jadx/bin:$PATH"      # provides jadx
export PATH="$PATH:/path/to/apktool"   # provides apktool or apktool.jar
```

> **Windows:** `DEXATLAS_JADX_PATH` should point at `bin\jadx.bat`, not the extensionless
> shell script. DexAtlas resolves the platform launcher itself when given `bin\jadx`, but
> naming it directly is clearer.

### Configuration

| Variable                  | Purpose                                  | Default            |
| ------------------------- | ---------------------------------------- | ------------------ |
| `DEXATLAS_WORKSPACE`      | Where projects and the database live     | `.dexatlas`        |
| `DEXATLAS_JADX_PATH`      | JADX launcher                            | discovered on PATH |
| `DEXATLAS_APKTOOL_JAR`    | Apktool jar                              | discovered on PATH |
| `DEXATLAS_LOG_LEVEL`      | Python log level                          | `WARNING`          |
| `DEXATLAS_TOOL_TIMEOUT_SECONDS` | Per-backend timeout                  | `900`              |
| `DEXATLAS_TOOL_MAX_OUTPUT_BYTES` | Cap on captured backend output   | `268435456`        |
| `DEXATLAS_GHIDRA_PATH`   | Ghidra install, for Phase 3 native analysis | discovered on PATH |
| `DEXATLAS_RIZIN_PATH`    | Rizin install, for Phase 3 native analysis  | discovered on PATH |

`DEXATLAS_GHIDRA_PATH` and `DEXATLAS_RIZIN_PATH` are reserved for the Phase 3 native
analysis backends and are not yet read by any code path.

## Analyse an APK

Get a fixture to analyse. No APK is committed to this repository, so fetch one:

```bash
bash scripts/fetch-fixtures.sh
```

These come from androguard's own test data under Apache-2.0, and their source and licence
are recorded in `fixtures/apk/SOURCES.md`. **Never commit an APK you are not authorized to
analyse.**

```bash
uv run dexatlas analyze fixtures/apk/TestActivity.apk \
    --output report.md --json report.json
```

```text
✓ apk_3bb32dd50129690b — 340 classes, 2,600 methods, 6,033 cross-references (25.0s)
!  apktool is not installed or not on PATH: Install Apktool and point
   DEXATLAS_APKTOOL_JAR at its jar, or put apktool on PATH: ...
!  jadx is not installed or not on PATH: Install the jadx decompiler: ...
Markdown report → report.md
JSON report → report.json
```

That output is the degradation promise made visible: with no external tools at all you
still get 340 classes, 2,600 methods and 6,033 cross-references from the in-process
Androguard index, and the report says exactly which steps did not run.

## Query the result

```bash
uv run dexatlas projects
uv run dexatlas manifest  apk_3bb32dd50129690b
uv run dexatlas classes   apk_3bb32dd50129690b --prefix tests
uv run dexatlas search    apk_3bb32dd50129690b "eratosthenes"
uv run dexatlas xrefs     apk_3bb32dd50129690b "java.lang.Object.<init>()V"
```

Method and class source, with a Smali fallback when decompilation fails:

```bash
uv run dexatlas source apk_3bb32dd50129690b tests.androguard.Eratosthene
uv run dexatlas source apk_3bb32dd50129690b tests.androguard.Eratosthene \
    --method eratosthenes
```

`source` needs JADX or Apktool. Without either it reports that rather than returning an
empty result.

## REST API

```bash
uv run uvicorn dexatlas.api.app:app --reload
# interactive docs at http://localhost:8000/docs
```

Uvicorn binds `127.0.0.1` unless it is told otherwise, so this listens on
this machine only. The API has **no authentication** — anyone who can reach it
can list every analysed project, read their decompiled sources and upload APKs
to be analysed. That is a reasonable trade for a single-user tool on a laptop,
and an unreasonable one on a network.

### Exposing the API

To reach the API from another machine, put a reverse proxy with
authentication in front of it and publish the proxy, not DexAtlas:

```bash
# 1. Keep DexAtlas on the loopback interface.
docker run --rm -p 127.0.0.1:8000:8000 -v dexatlas-workspace:/workspace dexatlas

# 2. Put your proxy in front of it, with whatever authentication you use.
#    nginx, Caddy, Traefik: all of them can do TLS and an auth layer.
```

What that buys you, and what it costs:

- **The proxy is the security boundary.** DexAtlas itself checks nothing about
  who is calling: no API key, no session, no rate limit. Everything that
  matters — who may list the projects, who may read a source, who may upload an
  APK — is decided by the proxy, so the proxy must actually authenticate.
- **The port mapping is what the network sees.** Publishing `8000:8000` binds
  the API on every interface of the host, and every machine that can route to
  it can use it. `127.0.0.1:8000:8000` cannot be reached from off the host.
- **An upload is a resource.** The API accepts an APK, writes it to the
  workspace and analyses it. Without a proxy in front, an exposed API is an
  invitation to fill the disk. The upload limit below bounds one upload; it
  does not bound how many arrive.
- **The API answers with paths.** It reports the *name* of each analysed file
  and redacts the server's own directories from its error messages — but a
  project listing is still a listing of what you have analysed.

If none of that is what you want, the CLI does the same work with no server and
no network at all:

```bash
uv run dexatlas analyze app.apk --output report.md
```

| Method   | Path                                        | Purpose                       |
| -------- | ------------------------------------------- | ----------------------------- |
| `GET`    | `/health`                                   | Liveness and backend versions |
| `GET`    | `/backends`                                 | Installed vs missing         |
| `POST`   | `/analyze`                                  | Upload an APK                |
| `GET`    | `/projects`                                 | List projects                |
| `GET`    | `/projects/{id}`                            | One project's metadata       |
| `GET`    | `/projects/{id}/manifest`                   | Parsed AndroidManifest.xml    |
| `GET`    | `/projects/{id}/classes`                    | Indexed classes               |
| `GET`    | `/projects/{id}/methods`                    | Indexed methods               |
| `GET`    | `/projects/{id}/resources`                 | Indexed resource strings      |
| `GET`    | `/projects/{id}/classes/{name}/source`      | Class source                 |
| `GET`    | `/projects/{id}/methods/{class}/{method}`   | Method source                |
| `GET`    | `/projects/{id}/xrefs/{method_id}`          | Callers of a method          |
| `GET`    | `/projects/{id}/search?q=`                  | Full-text search             |
| `GET`    | `/projects/{id}/evidence`                   | Evidence records             |
| `GET`    | `/projects/{id}/report?format=json\|markdown` | Report export              |
| `DELETE` | `/projects/{id}`                            | Remove a project             |

```bash
curl -X POST -F "file=@app.apk" http://localhost:8000/analyze
curl "http://localhost:8000/projects/<id>/report?format=markdown"
```

### What the API refuses

| Limit                     | Value  | Why                                                        |
| ------------------------- | ------ | ---------------------------------------------------------- |
| Upload size               | 256 MiB | Above the 200 MB ceiling Google Play puts on an APK, so every distributable APK is accepted |
| Declared uncompressed size | 2 GiB  | A real APK expands two- or three-fold; eight times that is more than any real package needs |
| Expansion ratio           | 100×   | Far past anything real, and far below the thousand-fold expansion of a bomb |

An upload over the size limit is refused with `413` while it streams — it is
never held in memory and never written in full. An archive that declares more
than the limits allow is refused with `422`, and it is refused from the ZIP
central directory, before a single byte of it is decompressed.

## Development

```bash
uv pip install -e ".[dev,analysis]"
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest                      # everything
uv run pytest -m "not slow"        # fast suite, no backends needed
uv run pytest --cov=dexatlas --cov-report=term-missing
```

CI runs the same commands on Python 3.12 and 3.13.

## Troubleshooting

**`jadx is not installed or not on PATH`** — set `DEXATLAS_JADX_PATH`, or run
`scripts/install-backends.sh`, which installs pinned versions and verifies each one runs.

**`is not a valid Win32 application`** — `DEXATLAS_JADX_PATH` points at the extensionless
shell script. Point it at `bin\jadx.bat`.

**`Analysis produced no symbols`** — no backend is installed. Run
`uv run dexatlas backends` and read the report's error section; each one names the
variable to set and where to get the tool.

**`%1 is not a valid Win32 application` for apktool** — set `DEXATLAS_APKTOOL_JAR` to the
`.jar` rather than relying on PATH.

**Garbled characters in terminal output** — your console is on a legacy code page.
DexAtlas reconfigures its streams to UTF-8; if your terminal cannot render them, output
falls back to ASCII.

## Next

- [Architecture](architecture/README.md) — how it fits together and why
- [Roadmap](roadmap/ROADMAP.md) — what comes next
- [Contributing](../CONTRIBUTING.md) — how to propose a change
