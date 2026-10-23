# Analysis runs

How one analysis is identified, staged, published and cleaned up.

## Why a run exists

A **project** is the APK. Its id is a content hash — `apk_<sha256[:16]>` — so
the same bytes always map to the same project, and re-analysing an APK
replaces what is stored under it.

That is a good property for a cache and a bad one for an analysis. The
project id says *which* APK was analysed and says nothing about *when*, or
*by which tools*, or *whether the result is whole*. So a re-analysis
overwrote the previous one in place, and a reader could see the symbols of
one run beside the evidence of another.

The Phase 1 review found the same shape of problem twice — the `evidence`
table not being cleared, and the upload being overwritten — and fixed both
by hand. A **run** fixes the class of it.

A **run** is one attempt at analysing one APK. It has an id of its own that
says nothing about the APK, and it carries the facts that belong to an
attempt rather than to a file.

## The model

`AnalysisRun` lives in `core/runs.py`.

| Field | What it is |
| ----- | ---------- |
| `id` | `run_<16 hex>`, random. Independent of the APK: two analyses of the same bytes are two runs, and an id derived from the bytes could not tell them apart. |
| `project_id` | The project the run belongs to. |
| `apk_sha256` | The hash of the bytes the run was given. |
| `status` | `pending`, `running`, `completed`, `failed`, `cancelled`. |
| `completeness` | `complete`, or `partial` when the run recorded an error and so has gaps in its result. |
| `tool_versions` | The version of every tool that took part. The versions belong to the run: the same APK analysed twice, with a decompiler upgraded in between, is two runs with two sets of versions. |
| `errors` | What went wrong, in the run that went wrong. |
| `started_at`, `finished_at`, `duration_seconds` | When it ran and how long it took. |
| `workspace` | The directory this run's own output lives in. |

The run's `status` is the *execution* status. The project's `status` is a
separate thing and it answers a different question: whether the project
holds a result.

## The lifecycle

```text
   accept                stage                    publish
     │                     │                         │
     ▼                     ▼                         ▼
  run created  ──►  run_runs/<run-id>/index.db  ──►  published_run_id
  (running)          + apktool/ jadx/                  │
                      (the run's own results)          ▼
                                                    projects.workspace
                                                    points at the run
```

1. **The run is created.** Its id is chosen at random, its workspace is
   `projects/<project-id>/runs/<run-id>/`, and the project's row is marked
   running. Nothing a reader can see has changed yet.

2. **The run stages its results.** The backends write into the run's own
   directory, and the symbols and the evidence are written into the run's
   own database, `runs/<run-id>/index.db`. That database has the same schema
   as the workspace's own, which is what lets a finished run be published
   into it.

3. **The run publishes.** One transaction replaces the published snapshot:
   the symbol tables, the evidence, the project's figures, the pointer to
   the run and the run's own record. A reader sees the previous run's
   snapshot or this one's, and never a mixture.

4. **A run that fails, or is cancelled, publishes nothing.** The snapshot
   that was published before it stays exactly as it was — its symbols, its
   evidence, its counts and its workspace pointer.

## Why the results are staged separately

The symbols and the evidence used to be written in two separate
transactions, and each of them cleared the table it wrote first. A reader
that looked between the two writes saw the **new** run's symbols beside the
**old** run's evidence — two runs' results presented as one.

Staging fixes that in the only way that holds: the run's results live
somewhere a reader cannot see, and they become visible in one commit. A run
that dies half way through leaves nothing behind but its own staging
database, which is discarded.

The staged database is removed once the run has published. The published
tables hold the current snapshot, and the run's own record — its status, its
versions, its errors, its timings — is the history. The results of a
superseded run are not kept.

## One writer per workspace

The output directories used to be handed to the external tools as *their*
output directories, so two analyses of the same APK wrote over each other's
decompiled output, and a request for source could read a half-written
`.java`.

Each run now writes into a directory of its own:

```text
projects/<project-id>/
└── runs/
    ├── <run-id-a>/
    │   ├── apktool/
    │   ├── jadx/
    │   └── index.db
    └── <run-id-b>/
        ├── apktool/
        ├── jadx/
        └── index.db
```

The `projects.workspace` column names the run that is **published**, and it
is moved in the same transaction that publishes the run's results. A reader
follows the pointer and reads one run's files.

The pointer is read **once per request**, inside one transaction, so a
publish that lands while a request is being served cannot send half of it to
one run and half to another. `Store.reading()` is that transaction: a
read-only view in which every read sees the same snapshot of the database.

> The directory swap that would have been the obvious fix — `os.replace` on
> a directory — is not available: on Windows it fails with `PermissionError`
> on a non-empty directory. The versioned directory plus the database
> pointer is the mechanism, and the pointer really is atomic in SQLite.

## The schema

Schema version 4 adds:

- **`analysis_runs`** — one row per attempt, as described above.
- **`projects.published_run_id`** — the run whose snapshot is published.

The migration is additive. A workspace written before runs existed opens,
keeps its symbols and its evidence, and has no published run to point at —
its rows are the published snapshot of an analysis that was never recorded.
The next analysis makes a run and the pointer moves to it.

The `xrefs` table is deliberately untouched. It has no primary key, so the
same call edge can be stored twice; that is Phase 2 item **P2-003**, which
lands after this and rebuilds the table.

## The API

### Runs

| Endpoint | What it answers |
| -------- | --------------- |
| `GET /projects/{id}/runs` | Every run of a project, newest first. The one that is published is marked. |
| `GET /projects/{id}/runs/{run_id}` | One run. |
| `POST /projects/{id}/cancel` | Ask the analysis that is running to stop. |

A cancellation is checked at the points where stopping cannot leave
half-written results behind: between the backends, and before the publish.
A backend that is half way through reading the APK finishes reading it
first — the stop happens between the steps. The endpoint answers `202` when
the request was accepted, which is not the same as the analysis having
stopped.

### Uploads

The upload is already safe: it is staged under a random name and then moved
to `uploads/<sha256>/<client-filename>`, so two uploads cannot overwrite
one another. What follows it was undefined, and is now:

| Endpoint | What it answers |
| -------- | --------------- |
| `GET /uploads` | The stored uploads, their size and how long they are kept. |
| `DELETE /uploads/{sha256}` | Remove one upload now. |
| `POST /uploads/cleanup` | Remove the uploads the retention window has passed. |

**Retention.** An uploaded APK is kept for 24 hours after the analysis that
used it finished, and the window is configurable with
`DEXATLAS_UPLOAD_RETENTION_SECONDS`. The window is counted from the end of
the analysis, so an APK that is analysed again is kept for another window. A
value that is not a number, or that is negative, falls back to the default:
a policy that cannot be read is not one to guess at.

**Cleanup.** The sweep runs when the server starts, when an upload is
accepted, after every analysis, and on demand through the endpoint. The
upload of an analysis that is running is never removed: the analysis reads
the file it was given, and a file that disappears under it is a failure of
the analysis rather than of the cleanup.

The cleanup lives in the API layer, not in the `Analyzer`. The analyzer is
handed a path and cannot tell where it came from, so it has no way to know
that a file it was given is one the server is keeping for a while.

## What is deliberately absent

- **The results of a superseded run.** The published tables hold one
  snapshot, and a run's own record is the history of the attempt. Keeping
  every run's symbols would mean keeping every run's index.
- **A primary key on `xrefs`.** That is P2-003.
- **A queue.** `/analyze` is still a background task on a single process.
