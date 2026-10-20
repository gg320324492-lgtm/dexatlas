# Large-APK benchmark

What happens when DexAtlas is pointed at an APK that is big enough to reach the
limits in the Androguard adapter.

`docs/status.md` 4.4 recorded this as an open item: the committed samples are
under 3 KB, the three limits in the Androguard adapter had never been pressed
against a real file, and what would happen on a large APK was a guess.

**This document is the measurement, and it is also a record of a causal chain.**
The stress test found three defects in the adapter. All three are fixed, and
this document says what each one cost, because a fix that nobody can compare
against a measurement is a fix nobody can check. Every number below was
produced by running the code on this machine, against the fixed code, and the
command that produced it is given. Nothing here is estimated.

---

## 1. How the sample is built

There is no large APK in this repository, and there is not going to be one. The
samples under `examples/` are committed, so they stay small, and a sixth
committed sample would make the claim "five first-party samples" false.

So the sample is **generated**, into a temporary directory, and thrown away:

```bash
uv run python scripts/generate-large-apk.py --scale medium --output-dir /tmp/big
```

The script writes smali, assembles it with Apktool, and writes a
**ground-truth manifest** next to the APK: the number of classes it wrote, the
number of methods, the number of call sites, and the per-DEX-file breakdown.
A test that checks the index against those numbers is checking it against what
the generator actually wrote, not against a number somebody typed into a test
file and later forgot to update.

The generated code is first-party: one class per generated file, each with a
constructor and a set of work methods, each work method loading a class marker
and a pooled literal, calling a shared helper, and returning. The
cross-references it produces point at a method the APK really defines, so they
can be resolved against the symbol table.

### The scales

The three budgets the adapter enforces, and where they live:

| Constant | Value | Definition |
|---|---|---|
| `DEFAULT_METHOD_LIMIT` | 200,000 | `src/dexatlas/tools/androguard/adapter.py:53` |
| `DEFAULT_STRING_LIMIT` | 50,000 | `src/dexatlas/tools/androguard/adapter.py:55` |
| `DEFAULT_INSTRUCTION_LIMIT` | 5,000,000 | `src/dexatlas/tools/androguard/adapter.py:57` |

| Scale | Classes | Methods/class | Instructions/method | DEX files | Purpose |
|---|---|---|---|---|---|
| `smoke` | 20 | 8 | 6 | 1 | The CI default. Fast, and below every limit. |
| `medium` | 300 | 40 | 12 | 1 | Comfortably inside every limit. Shows what the pipeline does when nothing is clipped. |
| `large` | 2,050 | 100 | 12 | 4 | **More methods than the method limit** (200,000). The method limit is reached by a real APK rather than by a lowered threshold. |
| `xlarge` | 600 | 100 | 88 | 1 | **More instructions than the instruction limit** (5,000,000) inside a *single* DEX file. |

The scale is an environment variable, so a CI job picks one without rewriting
a command line:

```bash
DEXATLAS_LARGE_APK_SCALE=large uv run pytest -m slow -q
```

---

## 2. The machine

Everything below was measured on one machine, so the timings are statements
about this machine and not about the code. The counts are statements about the
code.

| | |
|---|---|
| OS | Windows 11 (10.0.26200), x86-64 |
| Python | CPython 3.12.13 (uv-managed) |
| Androguard | 4.1.4 |
| Apktool | 2.11.1 |
| JADX | 1.5.2 |
| JDK | OpenJDK 21.0.12.1 (LTS) |
| Filesystem | NTFS, local disk |

The filesystem matters for one part of the story: the version lookup
([§5.3](#53-the-version-of-the-backend-was-probed-once-per-symbol)) stats
every installed distribution on every call, and that is much more expensive on
NTFS than on a Linux CI runner. The *shape* of that finding was not
machine-specific; the magnitude was. The fix removed the per-symbol cost
entirely, so the remaining per-run cost is one probe.

**Timings depend on what else the machine is doing.** The build times in
§3.1 and the test-file times in §7 were measured with nothing else running,
and are the median of three runs where a run was repeated. A run under load
is slower — the same `large` build took 2.5 s to 2.7 s in a quiet window and
noticeably longer when three other analyses were running beside it. The
counts do not depend on the load; only the times do.

---

## 3. The measurements

Every number in this section comes out of the committed test file, which writes
its own measurement to the path `DEXATLAS_LARGE_APK_REPORT` names:

```bash
DEXATLAS_LARGE_APK_SCALE=large \
DEXATLAS_LARGE_APK_REPORT=/tmp/large.json \
  uv run pytest tests/test_large_apk_scale.py -q
```

The dump holds the scale, the APK's size and DEX count, the generator's
ground truth, what the index actually holds, which limits were reached, the
timings, and the errors the run recorded. The tables below are that file.

### 3.1 Building the sample

```bash
uv run python scripts/generate-large-apk.py --scale medium --output-dir /tmp/bench/medium
```

```
scale          medium
classes        300
methods        12,000
instructions   12 per method
dex files      1
apk            /tmp/bench/medium/large.apk (104,673 bytes)
built in       1.08s
```

| Scale | APK size | DEX files | Build time |
|---|---|---|---|
| `smoke` | 3,435 bytes | 1 | 0.66 s |
| `medium` | 104,673 bytes | 1 | 1.0 s |
| `large` | 1,512,275 bytes | 4 | 2.6 s |
| `xlarge` | 557,189 bytes | 1 | 6.0 s |

Building is fast. Apktool assembles 205,000 methods into four DEX files in
about two and a half seconds, which is worth knowing: the expensive part of a
large APK is not making one. (`xlarge` takes longer to build because it
assembles 5.2 million instructions, and instruction count is what the assembler
costs.)

### 3.2 Indexing it

`AndroguardBackend.extract()` on the sample, with the default limits. The
"extract" column below is that call; the "pipeline" column is
`Analyzer.analyze()`, which also runs the other backends and writes the result
into the database. JADX is skipped above 50,000 methods, which is why the two
big rows cost less than their size suggests.

| Scale | APK size | DEX | Extract | Pipeline | Classes | Methods | Cross-references | Strings |
|---|---|---|---|---|---|---|---|---|
| `smoke` | 3,435 B | 1 | 0.02 s | 2.64 s | 21 | 161 | 160 | 337 |
| `medium` | 104,673 B | 1 | 0.62 s | 7.64 s | 301 | 12,001 | 12,000 | 24,049 |
| `large` | 1,512,275 B | 4 | 10.22 s | 26.62 s | 2,002 | 200,001 | 200,000 | 50,000 |
| `xlarge` | 557,189 B | 1 | 7.38 s | 12.48 s | 574 | 57,380 | 57,380 | 50,000 |

The `large` and `xlarge` rows are short, and on purpose: those two samples are
big enough to reach a limit. [§3.4](#34-large-the-method-limit-reached) and
[§3.5](#35-xlarge-the-instruction-limit-reached) say what is missing and why.

The two rows that reach no limit are complete, and the generator's ground truth
is the check:

| Scale | Truth: classes / methods / refs | Indexed | Agreement |
|---|---|---|---|
| `smoke` | 21 / 161 / 160 | 21 / 161 / 160 | exact |
| `medium` | 301 / 12,001 / 12,000 | 301 / 12,001 / 12,000 | exact |

The strings are higher than the number of distinct values in the DEX, because
the string index writes one row per **(value, use site)** pair — a literal
loaded by 39 methods is 39 rows, and that is what makes it pointable. Counted
directly from the DEX:

```
  medium:
    pool entries          2,997
    distinct values used  2,348
    use sites             23,400
    pool entries unused     649
    rows the index writes 24,049      <- 23,400 + 649
```

and the index holds 24,049 rows. The `smoke` sample decomposes the same way:
141 pool entries, 280 use sites, 57 entries nothing loads, 280 + 57 = **337
rows**, and the index holds 337.

One caveat about the ground truth, because a reader will compare the two: the
generator's own model of the string rows (25,448 for `medium`, against the
24,049 actually written) is an over-estimate. It counts one row per distinct
loaded pool value *plus* one row per use site, where a value used k times
yields k rows and a value nothing loads yields one. The difference is exactly
the 2,048 loaded pool values the generator counts against the 649 pool entries
nothing loads. The test only uses that number to decide *whether* a limit was
reached, and it over-estimates in the safe direction.

### 3.3 The full pipeline

`Analyzer.analyze()` on `medium`, with every backend:

```
duration             7.64s
status               completed
class_count          301
method_count         12,001
reference_count      12,000
errors               []
```

The generator wrote 301 classes, 12,001 methods and 12,000 references. The
analysis reports 301, 12,001 and 12,000. The database holds 301 class rows and
12,001 method rows. The search finds the marker string.

**The counts in the report and the rows in the database agree**, at every
level. The report says 12,001 methods, the database holds 12,001 method rows,
and the generator wrote 12,001 methods. The class rows carry the method counts
of the classes they name, and the search index finds a string that is really
there. This is the check the project got wrong once (execution report 3.12:
"the report said 14 methods, the query could list 11"), and it now holds at
12,001 methods rather than 14.

### 3.4 `large`: the method limit, reached

`large` holds 205,001 methods against `DEFAULT_METHOD_LIMIT` (200,000). The
limit is reached during the walk, and this is what the run reports.

The method limit is counted **across the whole APK**: the counter is the
accumulated method list, not a per-file one. So a 4-DEX APK gets one budget of
200,000, not four.

The APK is built with 2,051 classes over four DEX files, and the walk was
traced per file. The index holds 2,002 of those classes and 200,001 of the
205,001 methods:

| DEX file | Methods in it | Methods walked | Instructions walked (cumulative) |
|---|---|---|---|
| `classes.dex` | 60,001 | 60,001 | 714,001 |
| `classes2.dex` | 60,000 | 60,000 | 1,428,001 |
| `classes3.dex` | 60,000 | 60,000 | 2,142,001 |
| `classes4.dex` | 25,000 | **20,000** | 2,380,001 |
| **Total** | **205,001** | **200,001** | **2,380,001** |

What the run reports — this is the whole `project.errors[0]`, verbatim:

```
code    output_truncated
message string limit 50000 reached: the index is incomplete — 1449 entries of this
        DEX file's string pool were not indexed, and no DEX file after it
        contributed any string; method limit 200000 reached while indexing
        classes4.dex: the index is incomplete — 5000 methods in this file were
        not indexed, and the DEX files after it were not walked
```

The status is still `completed`, and that is the right answer: a partial
result is not a wrong result. But the run **says** that the index is short,
says which limit was reached, says how much is missing, and says that the DEX
files after the one it stopped in were not walked at all. A reader of the
report can tell a fully indexed APK from a clipped one.

Three details are worth reading carefully:

- **The count overshoots the limit.** The limit is 200,000 and the index holds
  200,001. The check is made at class granularity — at the top of the class
  loop, before that class's methods are added — so the count can land up to one
  class past the line. Here it landed one method past, because the classes in
  this sample hold 100 methods each. That is a rounding detail, not a defect.
- **The two limits interact.** The string index stopped at 50,000 rows while
  `classes.dex` was being read, so the string budget was already spent by the
  time the walk reached `classes4.dex`; the 1,449 pool entries that error
  names are `classes.dex`'s own, not `classes4.dex`'s. A clipped method index
  quietly clips the string index too.
- **The counts in the report and the rows in the database still agree
  exactly** — 2,002 class rows, 200,001 method rows, 200,000 cross-reference
  rows, and the report says the same three numbers. The database is not wrong.
  It is a faithful record of an index that was cut short, and now it says so.

### 3.5 `xlarge`: the instruction limit, reached

`xlarge` puts 5,228,401 instructions in a **single** DEX file, against
`DEFAULT_INSTRUCTION_LIMIT` (5,000,000). The limit is therefore reached
without any per-file multiplication playing a part — the file is over the limit
on its own.

```
apk: 557,189 bytes, 1 dex file
truth: 601 classes, 60,001 methods, 60,000 refs, 5,228,401 instructions
extract: 7.38s
  classes=574 methods=57,380 refs=57,380
  strings=50,000
```

```
code    output_truncated
message instruction limit 5000000 reached while indexing classes.dex: the index
        is incomplete — 2621 methods in this file were not indexed, their
        cross-references were not scanned, and the DEX files after it were not
        walked; string limit 50000 reached: the index is incomplete — 1299
        entries of this DEX file's string pool were not indexed, and no DEX file
        after it contributed any string
```

The instruction limit truncated the walk: **57,380 of 60,001 methods** were
indexed, and the cross-reference index stopped with it. The method table and
the cross-reference table are short by the same 2,621 methods — 60,001 − 2,621
= 57,380, exactly what the error says. The classes are short by 27 of 601,
because the walk stops in the middle of a class: the class it stops in is in
the index but only partly filled, and the 27 classes after it are not in the
index at all.

The string limit fired in the same file, for the same reason it fires on
`large`: the pool is bigger than the budget.

---

## 4. The three limits are one budget per APK

The three constants in the Androguard adapter — `DEFAULT_METHOD_LIMIT`,
`DEFAULT_STRING_LIMIT` and `DEFAULT_INSTRUCTION_LIMIT` — are named as one
group and read as one budget. **They are now one budget.** All three are
counted across the whole APK, and a DEX file that comes after the one that
spent the budget is not walked at all.

Measured by applying the same limit to the same content in one DEX file and in
ten:

| Limit | 1 DEX file | 10 DEX files | Ratio |
|---|---|---|---|
| `DEFAULT_METHOD_LIMIT` (16) | 16 methods | 16 methods | **1.0×** |
| `DEFAULT_STRING_LIMIT` (10) | 10 strings | 10 strings | **1.0×** |
| `DEFAULT_INSTRUCTION_LIMIT` (3) | 2 cross-references | 2 cross-references | **1.0×** |

The ten-DEX sample is the same smoke content with `--max-methods-per-dex 20`,
which splits 161 methods into ten files. Splitting an APK does not buy it a
bigger budget, which is the point: the number of DEX files in an APK is the app
author's decision, not the tool's, and a ceiling that the app author could
raise was not a ceiling.

### 4.1 The overshoot sample, before and after

A sample built so that **each** DEX file wants more than the whole APK's
budget makes the arithmetic unambiguous — 1,200 classes × 120 methods, in four
DEX files, each wanting 73,448 string rows: 293,792 between them, against a
budget of 50,000 for the whole APK.

Before the fix, that sample produced:

```
  string rows          200,000
  DEFAULT_STRING_LIMIT  50,000
  overshoot               4.0x
```

Four times the budget, because the budget was applied four times, and the only
evidence of it was a log line — the run reported `errors=[]`.

After the fix, the same sample produces:

```
  classes 1,201   methods 144,001   references 144,000
  strings          50,000
  error: string limit 50000 reached: the index is incomplete — 185 entries of
         this DEX file's string pool were not indexed, and no DEX file after it
         contributed any string
```

**Exactly 50,000 rows against a limit of 50,000**, and the shortfall is on the
record. Nothing else about that run is clipped: the method limit is 200,000
and the sample holds 144,001 methods; the instruction limit is 5,000,000 and
the sample holds well under it. The classes, methods and cross-references are
all indexed in full — 1,201, 144,001 and 144,000, exactly what the generator
wrote.

### 4.2 A spent budget stops the walk

Once a budget is spent, the DEX files after the one that spent it are not
walked at all. Walking them would produce rows that cannot be stored, and it
would also produce a second and third copy of the same gap in the report.

On the ten-DEX sample with the method limit lowered to 5:

```
  the APK: 10 DEX files, 161 methods
  DEX file          methods walked  stopped here?
  classes.dex                    8  YES
  classes2.dex          not walked
  classes3.dex          not walked
  ...
  classes10.dex         not walked
  indexed: classes=2 methods=8 refs=8 strings=43
  error  : method limit 5 reached while indexing classes.dex: the index is
           incomplete — 9 methods in this file were not indexed, and the DEX
           files after it were not walked
```

And on the `large` sample with the method limit lowered to 100,000, so that
the stop lands in the second of four files:

```
  the APK: 4 DEX files, 205,001 methods
  DEX file          methods walked  stopped here?
  classes.dex               60,001  no
  classes2.dex              40,000  YES
  classes3.dex          not walked
  classes4.dex          not walked
  indexed: classes=1,002 methods=100,001 refs=100,000 strings=50,000
```

This is the behaviour that makes the error message meaningful. "The DEX files
after it were not walked" is not a caveat — it is the larger half of the gap.
The `large` sample's own run stops in its *last* DEX file, so the message
names a gap of zero there; the two runs above are what make the rule visible.

---

## 5. The three defects this found, and what fixed them

The stress test found three real defects. **All three are fixed**, in
`src/dexatlas/tools/androguard/adapter.py` and `src/dexatlas/tools/base.py`.
Each one has a test that names it, and each of those tests was an
`xfail(strict=True)` marker until the fix landed: a strict xfail turns into a
failure the moment the defect is fixed, so a fix could not land without
someone removing the marker and saying so. The markers are gone. The
assertions are ordinary tests now, and they hold in their own right.

### 5.1 A truncated index is reported as a clean run

**Found by:** the `large` and `xlarge` samples, whose indexes were thousands
of methods short while the project reported `COMPLETED` and
`project.errors` was empty. The adapter logged a warning and returned what it
had. Nothing was recorded on the project, so a reader could not tell a fully
indexed APK from a clipped one — in the one place a reader would look.

**Fixed by:** a limit that truncates the index now produces a `ToolError` whose
code is `OUTPUT_TRUNCATED` — the code `ToolErrorCode` had defined for exactly
this and used for nothing (`src/dexatlas/core/models.py:33-41`). The error is
written into `project.errors`, it appears in the report's "Backend errors"
section, and it appears in the evidence table as
`androguard:error/output_truncated`. The project status stays `completed`,
because a partial result is not a wrong result.

**What it cost:** before the fix, `large` reported 200,001 methods and no
error. After it, the same run reports 200,001 methods *and* the error, and the
error says how much is missing.

**Reproduction:**

```bash
uv run python scripts/generate-large-apk.py --scale large --output-dir /tmp/large
DEXATLAS_LARGE_APK_SCALE=large uv run pytest tests/test_large_apk_scale.py -q
```

### 5.2 Two of the three limits were per-DEX, not per-APK

**Found by:** the same content in one DEX file and in ten, against the same
limits, giving ten times the budget for the string and instruction limits
([§4](#4-the-three-limits-are-one-budget-per-apk)). The overshoot sample made
it exact: 200,000 string rows against a stated limit of 50,000, with
`errors=[]`.

**Fixed by:** all three budgets are counted across the whole APK, and a spent
budget stops the walk. `instructions_seen` is no longer reset per DEX file,
and the string budget is measured against the whole APK rather than against
one file's pool.

**What it allowed:** a 4-DEX APK was allowed 200,000 strings against a stated
limit of 50,000, and 20,000,000 instructions against a stated limit of
5,000,000. A 16-DEX APK was allowed 800,000 strings. Now every APK gets one
budget of 50,000 strings and one budget of 5,000,000 instructions.

**Reproduction:** the same command as above, with
`tests/test_large_apk_scale.py -k "string_limit or instruction_limit"`, and
the overshoot sample:

```bash
uv run python scripts/generate-large-apk.py --scale medium \
  --classes 1200 --methods-per-class 120 --max-methods-per-dex 36000 \
  --output-dir /tmp/overshoot
```

### 5.3 The version of the backend was probed once per symbol

**Found by:** profiling a `medium` run. `Backend.provenance()` built every
symbol's provenance record, and it asked the backend for its version to do it.
The Androguard adapter's `version()` was not cached, so the answer came from
`importlib.metadata.version("androguard")` — which walks the installed
distributions and stats every one of them — once per indexed symbol. JADX and
Apktool both cached theirs; Androguard was the only backend that did not.

The profile of a `medium` run, before the fix:

```
ncalls  tottime  cumtime  filename:lineno(function)
   36951    0.075    80.069  src/dexatlas/tools/base.py:202(provenance)
   36951    0.063    79.771  src/dexatlas/tools/androguard/adapter.py:136(version)
   36951    0.024    79.591  importlib/metadata/__init__.py:882(version)
  258657    0.493    46.430  importlib/metadata/__init__.py:695(search)
  259307   45.882    45.882  {built-in method nt.stat}
```

**80 of the 82 seconds of that run were the version lookup.** The DEX parse
and the instruction walk — the actual work — took about a second.

**Fixed by:** two changes. The adapter's `version()` now probes once and
remembers the answer (`src/dexatlas/tools/androguard/adapter.py:144-172`), and
the `Provenance` record now takes its version from a single probe per backend
rather than one per record (`src/dexatlas/tools/base.py:208-227`).

**What it cost, measured:** the same `medium` sample, the same limits, the
pre-fix source tree extracted from git against the current one, in two
processes:

```
  symbols indexed : 48,651
  pre-fix (5566073)  : 122.20 s   (2.51 ms per symbol)
  current (fixed)    :   0.98 s   (0.02 ms per symbol)
```

**124.7×.** The cost was linear in the number of symbols, so it grew with the
APK: there was no size at which it became affordable. The per-symbol cost is
now flat at a rounding error, and the whole index build is a function of the
DEX rather than of the bookkeeping around it.

**Reproduction:** the test that pins it is the one that counts the probes
rather than the seconds, because a duration is a statement about the machine
and a probe count is a statement about the code:

```bash
uv run pytest tests/test_large_apk_scale.py -k "probed_once" -q
```

---

## 6. What was not measured

Being explicit about the edges of the measurement, because a report that
implies it covered more than it did is the same kind of defect this project
spends its time on.

- **Real APKs.** Every sample here is generated. A real APK has obfuscated
  control flow, native libraries, resources, and a string pool shaped by the
  app rather than by the generator. The *counts* would be different; the
  *behaviour* of the limits would not, because the limits are applied to
  whatever the DEX holds.
- **JADX and Apktool at scale.** The `large` and `xlarge` measurements run
  Androguard only, and the test skips the decompiler above 50,000 methods for
  that reason (`JADX_METHOD_CEILING`). JADX decompiling 205,000 methods is a
  different measurement, and this document does not claim anything about it.
- **The `xlarge` tier with the version lookup *not* cached.** Its uncached
  timing is not quoted, because only the `medium` and `large` tiers are
  measured both ways.
- **Native libraries (`.so`).** Nothing in the index covers them; the APK
  metadata records that they are there, and that is all.
- **Resource strings.** Whether a resource string is in the index is a
  separate question, answered by the resource-coverage work. This document
  does not depend on the answer.
- **Memory.** Peak RSS was observed to reach ~1.3 GB during a `large`
  pipeline, but it was not measured systematically across the scales, so no
  memory numbers are quoted.
- **CI timings on the runners.** The times here are from one machine. The
  runners are faster and slower in ways this document does not measure.
- **The APK's own byte-for-byte reproducibility.** The generator assembles
  through Apktool, and the archive carries timestamps, so two runs of the
  same scale produce the same *content* and different bytes — and a different
  SHA-256. Every measurement here is against a freshly generated APK, and the
  counts do not depend on the bytes.

---

## 7. What this costs CI

The suite is marked `slow`, so it runs in the two CI jobs that have the
backends. The scale is `smoke` by default, and nothing in CI sets
`DEXATLAS_LARGE_APK_SCALE`.

The cost of the test file, per scale, on this machine:

| Scale | Test file, all backends | Test file, Apktool only | Notes |
|---|---|---|---|
| `smoke` (the CI default) | 6.45 s | 2.85 s | Below every limit, so nothing is clipped. |
| `medium` | 12.24 s | 7.27 s | Below every limit, and JADX has 12,001 methods to decompile. |
| `large` | 67.89 s | — | Reaches the method limit. JADX is skipped. |
| `xlarge` | 35.81 s | — | Reaches the instruction limit. JADX is skipped. |

| CI job | Backends | What the new tests do | Cost |
|---|---|---|---|
| Tests (Python 3.12) | all three | Run at the `smoke` scale | ~6 s |
| Tests (Python 3.13) | no JRE, no Apktool, no JADX | **Skip** — the module needs a JRE to assemble the sample | 0 s |
| Tests (Apktool only, no JADX) | Apktool + Androguard | Run at the `smoke` scale; the missing decompiler is recorded as a `NOT_INSTALLED` error, which the test allows | ~3 s |

**The Python 3.13 job skips rather than fails**, because the module's
`skipif` conditions cover all three ways this machine can be missing what the
tests need: Androguard not installed, Apktool not locatable, and no `java` on
`PATH`. The 3.13 job is the second of those — it installs the Python extras
but no Java — and the skip is not silent: pytest reports all 17 tests as
skipped.

**What the fix changed here.** Before it, the `medium` tier cost 201 s, and
the reason was the defect in
[§5.3](#53-the-version-of-the-backend-was-probed-once-per-symbol): the
144.97-second extract was the bulk of it, and 0.77 of those seconds was the
analysis. The same file now takes **12.24 s**, and a `medium` tier would fit
in CI comfortably. The two jobs that run the suite pay about six seconds each
against a slow-suite runtime of a little over a hundred seconds.

**The bigger tiers are still not for CI**, but the reason changed. `large` is
67.89 s and `xlarge` is 35.81 s, and the cost is now the DEX parse and the
walk rather than the bookkeeping — the index build itself is 10.22 s and
7.38 s. A tier that reaches a limit is worth running in CI; whether it is
worth 70 seconds of every push is a question for the person who owns the CI
budget, and this document does not answer it for them.

---

## 8. Reproducing this

```bash
# The samples, at each scale.
uv run python scripts/generate-large-apk.py --scale medium --output-dir /tmp/bench/medium

# The tests, at the default scale.
uv run pytest tests/test_large_apk_scale.py -q

# The tests, at a bigger scale.
DEXATLAS_LARGE_APK_SCALE=medium uv run pytest tests/test_large_apk_scale.py -q

# The measurement, written out as JSON.
DEXATLAS_LARGE_APK_REPORT=/tmp/measurement.json \
  uv run pytest tests/test_large_apk_scale.py -q
```

The generator needs Apktool and a JDK; the tests need Androguard as well. On a
machine with neither, the suite **skips** rather than fails — which is the
configuration the Python 3.13 CI job runs in.

---

## 9. What this document asks the next person to do

The three defects in [§5](#5-the-three-defects-this-found-and-what-fixed-them)
are fixed. What is left is smaller, and none of it is a defect:

- **The string budget is the one that bites first.** On a 1.5 MB APK, the
  string index is full at 50,000 rows while the method index still has
  150,000 rows of room. Whether a report's search results can be trusted
  therefore depends on the string budget more than on the others, and the
  error says so — but the *number* of strings a real APK wants is not
  measured here.
- **A truncated index is a completed analysis.** The status is `completed`
  and the error is on the project, which is the right contract, and the CLI
  prints the error as a warning. But the CLI's exit code is 0 and the summary
  line counts only what was indexed, so a caller that reads the exit code — or
  a reader of the summary line alone — still cannot tell a clipped run from a
  whole one. Nothing in this document claims otherwise.
- **`docs/status.md` now points at this document.** The status page's §4
  records that the large-APK pressure test is closed, names the three defects
  it found, and says what was not measured. The `MAX_INSTRUCTION_LIMIT` it used
  to name — a constant that does not exist — is gone; the three limits the
  adapter actually enforces are `DEFAULT_METHOD_LIMIT`,
  `DEFAULT_STRING_LIMIT` and `DEFAULT_INSTRUCTION_LIMIT` at
  `src/dexatlas/tools/androguard/adapter.py:53-57`.
