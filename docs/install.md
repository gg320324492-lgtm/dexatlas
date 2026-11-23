# Installation

Every command here was run against a fresh clone. Where output is shown, it is what that
command actually printed.

## Requirements

| Requirement     | Version | Notes                                                     |
| --------------- | ------- | --------------------------------------------------------- |
| Python          | 3.12+   | 3.12 and 3.13 are tested in CI                             |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager and environment manager         |
| JDK             | 21+     | Required by the JADX and Apktool backends                   |
| [Node.js](https://nodejs.org/) + npm | 18+ | Only to build the web workbench front end; not needed for the CLI, the API or the agent |

Analysis backends are optional and independent — see [Backends](#backends).

## Install

The full route — all four extras, installed from the lockfile:

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas

uv sync --extra dev --extra analysis --extra mcp --extra demo
```

| Extra     | Installs                                   | Needed by                                              |
| --------- | ------------------------------------------ | ------------------------------------------------------ |
| `analysis`| Androguard                                 | In-process DEX parsing, the authoritative symbol graph |
| `mcp`     | the Model Context Protocol SDK             | `dexatlas-mcp`, the read-only MCP server               |
| `demo`    | Pillow                                     | `scripts/render-demo.py` (frames; ffmpeg encodes them)  |
| `dev`     | pytest, pytest-cov, ruff, mypy, vulture, httpx | The test suite and this repository's gates          |

`uv sync` installs the versions pinned in `uv.lock`, so the environment is the one CI
tested. CI itself installs `dev`, `analysis` and `mcp`; `demo` is only needed to
regenerate the demo and the report's figures.

For the CLI and the REST API alone, the smaller route is enough:

```bash
uv venv --python 3.12
uv pip install -e ".[analysis]"
```

The `analysis` extra installs Androguard, which parses DEX in-process. Without it you
still get APK validation, hashing and archive inspection. This route installs neither
the MCP server nor the demo renderer; use `.[analysis,mcp,demo]` when you need them.

### Docker

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
docker build -t dexatlas .
docker run --rm dexatlas dexatlas backends
```

The image carries JADX and Apktool; the build fails if either cannot be downloaded and
run, so a broken backend is caught at build time rather than during your first analysis.

**The image carries the code and the repository's own first-party samples**, so an
analysis can start without mounting an APK of your own:

```bash
docker run --rm -v dexatlas-workspace:/workspace dexatlas \
  dexatlas analyze examples/demo-app/demo.apk
```

The path is relative: it is resolved inside the container, where the samples sit next to
the code.

The analysis is written into the `dexatlas-workspace` volume, so it is still there for the
next command:

```bash
docker run --rm -v dexatlas-workspace:/workspace dexatlas \
  dexatlas projects --workspace /workspace
```

To analyse your own APK, mount the directory it is in. The volume is mounted read-only
because the analysis reads the APK and writes only into the workspace.

```bash
docker run --rm -v "$PWD/my-apks:/samples:ro" -v dexatlas-workspace:/workspace dexatlas \
  dexatlas analyze /samples/app.apk
```

```bash
docker run --rm -p 127.0.0.1:8000:8000 -v dexatlas-workspace:/workspace dexatlas
# API docs at http://localhost:8000/docs
```

Every command names its workspace the same way: `--workspace`/`-w` on `analyze` **and**
on each query (`projects`, `export`, `search`, …), or `DEXATLAS_WORKSPACE` for the whole
container. An analysis written with `--workspace` is queried back with the same option;
a query pointed at a directory that does not exist says so and exits `2` rather than
creating an empty workspace, so a typo is visible instead of silent.

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
│ jadx       │ available │ 1.5.2            │
│ apktool    │ available │ 2.11.1          │
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

> **The exports above only affect the shell that runs them.**
> `scripts/install-backends.sh` downloads both backends, but the `export PATH=…` and
> `export DEXATLAS_JADX_PATH=…` it performs belong to *its own* process — a script
> cannot change the environment of the shell that started it. Note that the script's
> own output at the end is only the two installed version lines (`jadx …`, `apktool …`);
> it does not print the two `export` lines to copy. Set them in your own shell (as
> shown above) before running `dexatlas backends`, otherwise it will still report the
> backend as missing.
>
> **Windows:** the `curl`/`unzip` steps above are the POSIX path. From Git Bash run
> `scripts/install-backends.sh` instead, then set the two variables in your own
> shell as above.

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

**Five first-party sample APKs are committed under [`examples/`](../examples/)** —
`demo-app/demo.apk`, `multidex-app/multidex.apk`, `obfuscated-app/obfuscated.apk`,
`strings-app/strings.apk` and `wide-app/wide.apk` — each with the Smali sources it
was built from beside it. You can analyse them as they are, and the three
[case studies](case-studies/README.md) run on three of them — `demo-app`,
`obfuscated-app` and `multidex-app`, the last one as the multi-DEX appendix
of the obfuscated-sample study:

```bash
uv run dexatlas analyze examples/demo-app/demo.apk \
    --output report.md --json report.json --html report.html
```

For the third-party integration fixtures the test suite uses — androguard's test
data, fetched on demand — run:

```bash
bash scripts/fetch-fixtures.sh
```

That script reads the fixture APKs through the GitHub API, so the
[`gh` CLI](https://cli.github.com/) has to be installed and authenticated
(`gh auth login`). It is only needed for those fixtures, not for DexAtlas itself,
and nothing it fetches is committed: the fixtures come from androguard's own test
data under Apache-2.0, and their source and licence are recorded in
`fixtures/apk/SOURCES.md`. **Never commit an APK you are not authorized to
analyse.**

```text
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges,
  1 resource string (5.0s)
!  apktool is not installed or not on PATH: Install Apktool and point
   DEXATLAS_APKTOOL_JAR at its jar, or put apktool on PATH: ...
!  jadx is not installed or not on PATH: Install the jadx decompiler: ...
Markdown report → report.md
JSON report → report.json
HTML report → report.html
```

That output is the degradation promise made visible: with no external tools at all you
still get the class, method and cross-reference index from the in-process Androguard
backend, and the report says exactly which steps did not run.

The three report formats are three renderings of one analysis — the numbers in
the HTML page are the numbers in the Markdown and JSON reports. `--html` writes a
single self-contained file: no scripts, no fetched resources, and every string the
analysis did not produce (sample strings, class names) escaped, so a hostile APK
cannot write markup into the reader's browser.

## Export a minimal evidence package

To hand a client the analysis without the workspace, export the evidence
package:

```bash
uv run dexatlas export apk_80a8fe0e81204c9f --output evidence.zip
```

The package holds the report in all three formats, the evidence records, the
source fragments the evidence cites, and a `manifest.json` with a SHA-256
checklist of every file. It does not hold the analysed APK, the full source
tree, or string constants no evidence record cites — the manifest says so
explicitly. A reader who copies the package elsewhere can still follow every
citation, because everything in it is located by a path relative to the
package.

### Exit codes

`dexatlas analyze` — and every other command — answers with one of these:

| Code | Meaning |
| ---- | ------- |
| `0` | The command did what was asked: a whole, complete analysis. |
| `1` | The answer is empty: no classes matched, no callers, no source. |
| `2` | The request was wrong: no such project, or the input is not an APK. |
| `3` | The analysis itself failed: a step raised, or the workspace could not be written. |
| `4` | The method name matches several overloads and no descriptor was given; the candidates are named. |
| `5` | The analysis finished, but a limit cut a step short (`output_truncated`), so the report describes a shortened index. |
| `6` | The analysis finished, but no symbol index could be built: every code backend failed, so the report describes no classes. |

Code 5 is the difference between "the run fell over" (3) and "the run finished
on a shortened index": a truncated run still completes, still writes its
report, and every number in it is exactly what was indexed — but a caller that
reads only the exit code can now tell a clipped run from a whole one without
opening the project record.

Code 6 is the difference between "the APK holds no code" (0, an APK with no
DEX is a whole answer) and "the run indexed nothing because every code backend
failed": the manifest may still be readable — Apktool can write it before it
is stopped — but the index holds no classes. The report is still written and
readable, and `summary.index_complete == false` carries the same fact; a
caller that reads only the exit code can tell a run that read nothing from a
whole one without opening the project record.

## Query the result

```bash
uv run dexatlas projects
uv run dexatlas manifest  apk_80a8fe0e81204c9f
uv run dexatlas classes   apk_80a8fe0e81204c9f
uv run dexatlas search    apk_80a8fe0e81204c9f "Crypto"
uv run dexatlas xrefs     apk_80a8fe0e81204c9f "java.lang.Object.<init>()V"
```

Method and class source, with a Smali fallback when decompilation fails:

```bash
uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity
uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity \
    --method onCreate
```

`source` needs JADX or Apktool. Without either it reports that rather than returning an
empty result.

## Runs — one analysis attempt, kept readable

A project is the APK; a run is one attempt at analysing it. Re-analysing the same
APK does not overwrite a run — it publishes a new one in its place — and the
project's counts describe the *published* run, the last one that completed.
`dexatlas runs` shows a project's attempts; `--run` reads one run's own record
back, including every error it recorded:

```bash
uv run dexatlas runs apk_80a8fe0e81204c9f
uv run dexatlas runs apk_80a8fe0e81204c9f --run run_0123456789abcdef
```

`dexatlas render` writes one run to a directory a reader can archive or carry
away: the three report formats that run's snapshot describes, the evidence
package (`evidence/evidence-package.zip`, the same archive `dexatlas export`
writes), and the run's own record as `run.json`:

```bash
uv run dexatlas render apk_80a8fe0e81204c9f run_0123456789abcdef \
    --output rendered-run/
```

Only a run that completed and is still the project's published one renders: a
later analysis replaces the published snapshot, and a run that failed or was
cancelled published nothing to render. The render reads the workspace — no
analysis runs, no backend starts.

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
  and redacts the server's own directories — from its error messages and from
  the health check, which names the workspace directory but never its path —
  but a project listing is still a listing of what you have analysed.

If none of that is what you want, the CLI does the same work with no server and
no network at all:

```bash
uv run dexatlas analyze app.apk --output report.md
```

The table below is the **REST API's** contract (`dexatlas.api.app`). The web
workbench serves its **own** `/api/...` subset over the same eleven read-only
tools — the paths differ; see [the workbench architecture](architecture/workbench.md)
for that list.

| Method   | Path                                           | Purpose                       |
| -------- | ---------------------------------------------- | ----------------------------- |
| `GET`    | `/health`                                      | Liveness and backend versions |
| `GET`    | `/backends`                                    | Installed vs missing          |
| `POST`   | `/analyze`                                     | Upload an APK                 |
| `GET`    | `/projects`                                    | List projects                 |
| `GET`    | `/projects/{id}`                               | One project's metadata        |
| `GET`    | `/projects/{id}/runs`                          | Runs of one project           |
| `GET`    | `/projects/{id}/runs/{run_id}`                 | One run's status              |
| `POST`   | `/projects/{id}/cancel`                        | Stop a running analysis       |
| `GET`    | `/projects/{id}/manifest`                      | Parsed AndroidManifest.xml    |
| `GET`    | `/projects/{id}/classes`                       | Indexed classes               |
| `GET`    | `/projects/{id}/methods`                       | Indexed methods               |
| `GET`    | `/projects/{id}/resources`                     | Indexed resource strings      |
| `GET`    | `/projects/{id}/resource-references`           | Resource-to-file references   |
| `GET`    | `/projects/{id}/classes/{name}/source`         | Class source                  |
| `GET`    | `/projects/{id}/methods/{class}/{method}`      | Method source                 |
| `GET`    | `/projects/{id}/xrefs/{method_id}`             | Callers of a method           |
| `GET`    | `/projects/{id}/search?q=`                     | Full-text search              |
| `GET`    | `/projects/{id}/evidence`                      | Evidence records              |
| `GET`    | `/projects/{id}/report?format=json\|markdown`  | Report export                 |
| `GET`    | `/uploads`                                     | Stored uploads and retention  |
| `DELETE` | `/uploads/{sha256}`                            | Remove a stored upload        |
| `POST`   | `/uploads/cleanup`                             | Delete uploads past retention |
| `DELETE` | `/projects/{id}`                               | Remove a project              |

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
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest                      # everything
uv run pytest -m "not slow"        # fast suite, no backends needed
uv run pytest --cov=dexatlas --cov-report=term-missing
```

`dev` alone is not enough for the whole suite: `tests/test_public_contracts.py`
imports the MCP SDK. Regenerating the report's figures also needs `demo`
(Pillow) and `ffmpeg` on `PATH`.

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
- [The web workbench](architecture/workbench.md) — the browser UI; its first start
  builds the front end, it serves on `127.0.0.1:8618`, and if that port is taken it
  names the fix: pass another one with `--port <other>`
- [Roadmap](roadmap/ROADMAP.md) — what comes next
- [Contributing](../CONTRIBUTING.md) — how to propose a change