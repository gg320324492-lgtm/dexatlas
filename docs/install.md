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
docker run --rm -p 8000:8000 -v dexatlas-workspace:/workspace dexatlas
# API docs at http://localhost:8000/docs
```

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
