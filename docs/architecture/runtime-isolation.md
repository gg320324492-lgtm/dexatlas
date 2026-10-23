# Runtime isolation

How the Androguard backend stays inside its box when it is embedded in a long-lived
service.

DexAtlas is about to be embedded in a service that an agent drives. An embedded library
that breaks its host is worse than a library that fails, and the two ways this backend
used to break its host were measured rather than argued about.

## What was wrong

**The adapter deleted the host's logging.** `_quiet_androguard` called loguru's
`remove()` with no argument, which removes *every* handler in the process — the default
one and every handler the host application had added. The `finally` block restored the
`LOGURU_LEVEL` environment variable, which is dead code: loguru reads that variable
once, at import time, so it never affected a handler. After one analysis the process's
handler set was empty and its minimum level was infinity. The host's logging was gone
for good, and DexAtlas had no way to turn it back on.

**The untrusted DEX was parsed in the service's process.** `DEX(blob)` — the expensive
parse, and the part that runs on bytes the service did not write — happened in the
process that would go on to serve the next request. A DEX file that took the interpreter
down took the service down with it.

Both are now fixed, and both fixes have a test that fails without them.

## The shape of it

```text
   service process                         worker process
   ───────────────                         ──────────────
   AndroguardBackend.extract()
     │
     ├─ writes job.json  ──────────────►   dexatlas.tools.androguard.worker
     │                                       │
     │                                       ├─ bounds itself (memory, file size)
     │                                       ├─ opens the APK, parses the DEX
     │                                       ├─ walks the bytecode
     │                                       └─ writes result.json
     │
     ├─ reads result.json ◄────────────────
     ├─ rebuilds the models
     └─ returns (classes, methods, fields, references, strings, error)
```

The worker is started as `python -m dexatlas.tools.androguard.worker` — the same
spelling on Windows and on Linux, and what it starts is a process that can be killed
with its tree. It runs under the base class's subprocess runner, which is the same
machinery that bounds JADX and Apktool.

The service's own process never loads Androguard's parser. Backend discovery may import
the trivial top-level package to find where Androguard is installed — that package
holds nothing but a version string — but nothing that reads a DEX file is loaded
there. That is checked in a fresh interpreter, because the question is what the
*service* has loaded, and the test session may have loaded Androguard already for its
own reasons.

## What crosses the boundary

JSON, in both directions.

The tempting alternative is a pickle, which is smaller and faster. A pickle is also
executable: reading one back is running the code that wrote it, and the code that wrote
it ran against untrusted input. That is a code-execution path from a malformed APK into
the service, which is exactly the thing this boundary exists to prevent.

So the worker writes the models in their JSON form and the service rebuilds them through
their own validators. What arrives is what the service would have built itself: the same
canonical descriptors, the same canonical method ids, the same provenance, the same tool
version. The version is passed to the worker rather than resolved twice, so the two
processes cannot disagree about it.

The result is compared against the in-process path model by model — classes, methods,
fields, cross-references, strings and the error, including the truncation errors that
say a walk stopped short.

## What the worker is bounded by

| Bound         | POSIX                        | Windows                       |
| ------------- | ---------------------------- | ----------------------------- |
| Runtime       | the service's timeout        | the service's timeout         |
| Memory        | `setrlimit(RLIMIT_AS)`       | a job object the worker joins |
| Temporary disk| `setrlimit(RLIMIT_FSIZE)`    | a temporary directory of its own |

**Runtime** is the service's `tool_timeout_seconds`, and the worker is killed with its
tree when it has had its time. A worker that outlives its timeout is a recorded
`timeout` error, not a hang.

**Memory** is a ceiling on the worker, not an allocation. On POSIX it is `RLIMIT_AS`; on
Windows there is no `setrlimit`, so the worker puts *itself* into a job object with a
memory limit, and the kernel refuses the allocation that would take it past the ceiling.
Python sees that as `MemoryError`, which the existing error handling already turns into
a recorded parse failure.

The worker reports which bounds it managed to put in force, and the report travels back
with the result. A bound nobody can see is a claim; this one is a measurement the
service can read.

**Temporary disk** is bounded where the platform can bound it. The worker's temporary
directory variables point at a directory of its own, which is deleted when the worker is
done, so everything it writes while parsing lands in one place. On POSIX the size of a
single file it writes is capped as well. Windows has no per-file cap in the standard
library, so the directory is isolated and cleaned up but not capped — the worker says so
rather than pretending otherwise.

A limit that cannot be applied is not a reason to refuse to work. The worker carries on
without it and records what it could not do: a worker that will not start is worse than
a worker that runs a little less bounded.

### What the isolation is worth

An APK of half a megabyte that carries half a gigabyte of DEX:

|                       | Peak allocation in the service's process |
| --------------------- | ---------------------------------------- |
| Parsed in-process     | 1085 MiB                                 |
| Parsed in the worker  | under 1 MiB                              |

The service's own process does not pay for the DEX file it is asked to read.

## The logging rule

The host's loguru handlers are not ours to touch. Not "not to remove" — not to touch at
all, because the service may legitimately have configured them.

So the suppression is by **name**. Loguru's `disable("androguard")` / `enable("androguard")`
turns off the records whose module is `androguard` or one of its children and leave every
handler in the process where it was. An analysis of the fixture APK emits 200 records,
every one of them under `androguard.`, and with the name switched off none of them
reaches a handler.

Two things about that switch are worth writing down, because both are the price of not
touching the host's handlers:

- **It is global, not per-thread.** Two analyses running at once share it, so the first
  to finish turns it back on for the one still running. The cost is a few extra `DEBUG`
  lines in that second analysis.
- **It cannot read the host's state back.** If the host application had disabled
  Androguard's logging itself, the analysis turns it back on. Loguru offers no way to
  ask, and leaving it disabled for good would be the worse of the two mistakes.

The suppression covers the whole parse now, the DEX reading included. It used to stop
after the archive was opened, and the parse stayed quiet only because the handler removal
it relied on was permanent.

## What this does not cover

The plan's other two P2-005 items — one active writer per APK/run workspace, and upload
retention, cleanup and cancellation — are about the workspace and the API rather than
about the parser. They belong with the code that owns the workspace and the transport,
and they are not addressed here.

Nor is this a sandbox. The worker is a separate process with bounds, not a jail: it runs
with the service's privileges, it can read what the service can read, and it writes only
into the temporary directory it was given. It contains a crash, an unbounded allocation
and a hang. It does not contain a determined attacker with a shell.

## How it is checked

`tests/test_androguard_isolation.py`:

| Test                                        | What it holds down                                      |
| ------------------------------------------- | -------------------------------------------------------- |
| the host's handlers are untouched           | the handler set is *equal* afterwards, not merely present |
| Androguard's output is suppressed          | by name, and nothing else is suppressed with it          |
| the service never loads Androguard         | in a fresh interpreter, so the answer is not polluted    |
| the parse runs in another process          | the worker's process id is not the service's             |
| the worker produces the same index         | model by model, against the in-process path              |
| the truncation errors survive              | a walk that stopped short still says so                  |
| the worker bounds its memory               | the worker reports which bounds it applied               |
| a worker that runs out of memory           | a recorded failure, not a dead service                   |
| a worker that outlives its timeout         | killed, and recorded as a timeout                        |
| a hostile DEX                              | the service's own allocations stay under budget          |
| a malformed DEX                            | a recorded failure, and the service keeps working        |

The two that matter most are the first and the third, because they are the two defects
this document is about. The rest hold down the details: that the boundary loses nothing,
that the bounds are real, and that a hostile input is an event rather than an ending.
