# The M3 task set

Phase 2 milestone M3 measures quality instead of demonstrating it. The
milestone asks for at least thirty tasks over the first-party samples, each
with an independently checked expected answer, and for every reported metric
to be regenerable by a script in the repository.

**This document is about the task set**: what the tasks ask, how an answer is
checked, how a second person confirms that an expected answer is right
without running anything, and how the set could be gamed. The three
configurations the milestone compares against this set come later.

It is not a report of a measurement. `benchmarks/run.py` prints that, and
prints the same numbers twice.

---

## 1. What a task is

A task is four things and a question:

| | |
|---|---|
| **The question** | in the words a reader of a report would use |
| **What an answer must contain** | the evidence the analysis has to return |
| **What an answer must not contain** | the shape a wrong answer takes |
| **Where the answer comes from** | the file in the sample's own sources that establishes it |

The last one is the whole point. An expectation that was collected by running
the tool under test records the tool's current behaviour and calls it truth —
and a bug in the tool would then be recorded as the correct answer. So every
expectation here is written against the sample's own files: the Smali beside
the APK, the manifest beside the APK, the `strings.xml` beside the APK. A
second person reads those files and confirms the expectation without running
an analysis, a backend or a model.

One of them is worth reading in full, because it is the sharpest:

```python
Task(
    id="xrefs.crypto-sign-callers",
    category=Category.XREFS,
    question="Which method calls Crypto.sign?",
    sample=Sample.DEMO,
    probe=probes.callers(SIGN),
    source=(
        "examples/demo-app/smali/com/example/demo/MainActivity.smali: the onCreate "
        "method holds `invoke-static {v0, v1}, "
        "Lcom/example/demo/Crypto;->sign(Ljava/lang/String;Ljava/lang/String;)"
        "Ljava/lang/String;`."
    ),
    must_contain=("com.example.demo.MainActivity.onCreate", "com.example.demo.Crypto.sign"),
    must_not_contain=("com.example.demo.NetworkClient",),
)
```

The `source` names a file and the instruction in it. The `must_not_contain`
catches the answer that names a plausible caller that the Smali does not.

---

## 2. The ten categories

The categories are the ones the Phase 2 plan names for M3.

| Category | What it asks | Tasks |
|---|---|---|
| `manifest` | What the APK says about itself: package, version, SDK levels, permissions | 12 |
| `components` | The components a manifest declares, and which of them are exported | 6 |
| `xrefs` | Tracing a call from its callee back to its callers | 10 |
| `strings` | Finding a string or a resource, and where it was declared | 10 |
| `overloads` | Telling methods apart when a name is not enough | 7 |
| `multidex` | Reading an APK whose classes are spread over more than one DEX | 7 |
| `ambiguity` | Reading code that does not say plainly what it does | 4 |
| `partial` | What the analysis says when a backend is not there | 8 |
| `provenance` | Checking where a piece of evidence says it came from | 6 |
| `unanswerable` | A question the analysis cannot answer, and must not pretend to | 11 |

**81 tasks in all.** They are spread over the five samples — 39 ask about the
demo application, 14 about the multidex sample, 11 about the obfuscated one,
9 about the strings sample and 8 about the wide one — and over the three
backend configurations: 69 are asked with every backend installed, 8 with the
decompiler absent and 4 with the APK reader absent.

### 2.1 On "method overloads"

The milestone asks for method overloads, and names the demo application's
`sign` methods as the example. **The demo application has one `sign`, not
several**: `Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;`
and nothing else. The independent DEX reader in `benchmarks/dexreader.py`
lists every class and every method of every sample, and no sample contains a
class with two same-named methods of different descriptors.

The category is therefore about the property a descriptor carries rather than
about choosing between two overloads — that a method's identity is its name
*and* its descriptor, and that methods sharing a name across classes, or
across DEX files, are different methods. Three tasks ask whether a given name
resolves to one method or to several: `describe` exists in two classes of the
multidex sample, `handle` in three of the wide sample, and `b` in the
obfuscated one.

This is stated here because a benchmark that claims to cover something it does
not cover is worse than one that says so.

### 2.2 On "questions that cannot be answered"

Thirteen tasks have an answer that is an absence. Eleven of them are in the
`unanswerable` category; the other two are the partial-backend cases where
the manifest or the resource table is gone with the backend that reads it.
**That is sixteen per cent of the set**, against the tenth the milestone
asks for, and the `unanswerable` category on its own is fourteen per cent.

**They are scored, not merely present.** The right answer to "which method
calls `Crypto.digestOf`?" is that nothing does, and a system that answers it
anyway fails the task: it returned a piece of evidence where the answer is
that there is none. The check is an absence, checked as an absence, so a
system cannot pass by saying something plausible.

---

## 3. How an answer is checked

`check()` in `benchmarks/model.py` applies four rules, and a task states
which ones apply to it:

| Rule | Meaning |
|---|---|
| `must_contain` | Every string has to appear in at least one piece of evidence. Matched case-insensitively, as a substring. |
| `must_not_contain` | No string may appear in any piece of evidence. |
| `expect_count` | The answer has to hold exactly this many pieces of evidence. |
| `expect_empty` | The answer has to hold none. |

Three things about the rules are worth stating, because they are where a
benchmark usually goes soft:

- **A count is a count.** "How many components does the obfuscated sample
  declare?" is checked against the number 4, not against the substring "4".
  An answer that lists three of four has not answered it.
- **A task that only forbids something still needs an answer.** A task whose
  only check is `must_not_contain` fails on an empty answer, because "the
  evidence does not say X" is true of no evidence at all. The check would
  pass without anything having been checked.
- **The runner's own note is not evidence.** A note is the account of what the
  query did — "no callers of `Crypto.digestOf`" is the opposite of a claim,
  and checking it would fail a correct answer.

### 3.1 Answers are lists of evidence

An answer is a list of evidence, not a paragraph. DexAtlas's own API answers
that way — a query returns rows, and a query that matches nothing returns no
rows — and the checks are written against rows.

M3's other two configurations answer in prose, so the runner for that
comparison has to turn prose into evidence before it can be checked. The
`Answer` type carries a `text` field for the case where a prose answer is
the evidence in its own right, and it is checked the same way the rows are.
What the task set does not do is decide how a paragraph becomes a list: that
is the adapter's job, and it belongs with the comparison, not with the
marking scheme.

### 3.2 Every task has to be able to fail

A task that cannot fail is not a task, and the tasks that matter most here
are the ones whose answer is an absence: they are supposed to fail a system
that confabulates, and that is only true if the rule really rejects the
fabrication.

So the runner checks every task against the answer that is wrong in the most
obvious way — for a task that expects an absence, a piece of evidence and a
sentence naming something; for a task that expects evidence, no evidence at
all — and refuses to run if a task accepts its own wrong answer:

```
Self-check: every task rejects an answer that is wrong (81 task(s) checked).
```

The check runs before anything is analysed, because a rule that has stopped
rejecting a wrong answer would make every other number meaningless.

On a task whose answer is an absence, `must_not_contain` names the things a
confabulating system would reach for: "MainActivity", "NetworkClient" and
the rest for a method nothing calls. It is empty on the tasks whose question
is about *existence* rather than about a named symbol — "does this APK
mention Google's accounts service?" — because there, any marker would also
appear in a correct answer that says "there is none".

---

## 4. Why the expected answers are independent

Two readers in this directory read the APK's bytes directly, and neither
imports `dexatlas`:

| | |
|---|---|
| `benchmarks/axmlreader.py` | Decodes the binary `AndroidManifest.xml` out of the APK zip: the string pool, the elements, the attributes, the typed values. |
| `benchmarks/dexreader.py` | Decodes each `classes*.dex`: the class table, and each method's name and full DEX descriptor. |

They exist because the samples' own sources are committed next to the APKs,
so an expectation can be *read* rather than *collected* — and because "the
sources are there" is a claim that is worth checking rather than assuming.
It holds: the DEX reader and the Smali trees agree on every class and every
method of all five samples.

### 4.1 The check that found something

The AXML reader was written because of a discrepancy that turned out to be
real. For four of the five samples the minimum SDK level in the APK's binary
manifest is **not** the number the analysis reports:

| Sample | The APK's bytes | The checked-in `AndroidManifest.xml` | What the analysis reports |
|---|---|---|---|
| `demo-app` | 24 | 24 | 24 |
| `wide-app` | 24 | 24 | **25** |
| `multidex-app` | 24 | 24 | **25** |
| `strings-app` | 26 | 26 | **27** |
| `obfuscated-app` | 21 | 21 | **23** |

Three sources agree on the left-hand column: the AXML reader, Androguard's
own reader (a different implementation, and one this project also uses), and
the manifest committed beside the APK.

The number on the right comes from Apktool. Apktool decodes the manifest
without a `<uses-sdk>` element — it moves the SDK levels into the
`apktool.yml` it writes — and the values it writes there are not the ones the
APK's bytes carry. DexAtlas reads that file and reports what it says.

**Why that happens inside Apktool was not established.** The four samples'
APKs hold three files each and no other place the number could come from, and
the target SDK level is read correctly from the same element, so the two
values are not being confused with each other. This document states what was
measured and stops there.

Four of the tasks in the set check the SDK level, one per affected sample,
plus a fifth for the sample where the two agree — so the divergence is
visible as a property of the samples rather than as a single unlucky task.
They are the four tasks that fail today; see section 6.

---

## 5. Running it

```bash
uv run --no-sync python benchmarks/run.py
```

The runner analyses each sample once per configuration the task set needs,
asks every task's question of the analysis through DexAtlas's own API, and
checks the answer. It prints each task, a per-category tally and a total, and
exits 1 when any task failed.

```
Per-category tally
  manifest          8/12
  components        6/6
  xrefs             10/10
  strings           10/10
  overloads         7/7
  multidex          7/7
  ambiguity         4/4
  partial           8/8
  provenance        6/6
  unanswerable      11/11

Total: 77/81 passed (95.1%)
Self-check: every task rejects an answer that is wrong (81 task(s) checked).
```

The numbers are deterministic. A project's id is the APK's SHA-256, so the
same sample produces the same project every time; the task order is fixed;
and the workspace is rebuilt from scratch on every run, so nothing an earlier
run left behind can change the result. Two runs of the same tree produce
byte-identical JSON.

Other things the runner does:

```bash
# The questions, without the marking scheme — what a system under test gets.
uv run --no-sync python benchmarks/run.py --emit-questions

# The tasks and their expectations, without running anything.
uv run --no-sync python benchmarks/run.py --list

# One category, one configuration, one task.
uv run --no-sync python benchmarks/run.py --category unanswerable
uv run --no-sync python benchmarks/run.py --configuration no-jadx
uv run --no-sync python benchmarks/run.py --task xrefs.
```

### 5.1 Which configuration a task is asked in

A task names the configuration it is asked in, because that is part of the
question. The three configurations are the ones this project's CI runs:

| Configuration | What is missing |
|---|---|
| `full` | Nothing. |
| `no-jadx` | The decompiler. The code is still readable, as Smali. |
| `no-apktool` | The APK reader. No manifest, no resources, no Smali. |

An empty setting disables a backend outright rather than looking for it on
`PATH`, which is how this project's own "Apktool only" CI job turns the
decompiler off.

Two tasks are a matched pair, and their expected answers differ:

- `multidex.shared-config-java-comes-from-second-dex` — with the decompiler
  installed, `SharedConfig.origin()` returns `"secondary-dex"`.
- `multidex.shared-config-smali-comes-from-first-dex` — without it, the same
  question returns `"primary-dex"`.

That is not a contradiction. `SharedConfig` is defined in **both** DEX files
and the two definitions disagree; the decompiler keeps the class it read
last, and Apktool's Smali fallback searches its decoded directories in sorted
order, and `smali/` sorts before `smali_classes2/`.

---

## 6. What the run measures today

77 of 81 tasks pass. **The four that fail are the SDK-level tasks of section
4.1**, and they fail for one reason: the analysis reports Apktool's number
where the APK's number is the fact.

| Task | Expected | Reported |
|---|---|---|
| `manifest.min-sdk.wide` | `min_sdk=24` | `min_sdk=25` |
| `manifest.min-sdk.multidex` | `min_sdk=24` | `min_sdk=25` |
| `manifest.min-sdk.strings` | `min_sdk=26` | `min_sdk=27` |
| `manifest.min-sdk.obfuscated` | `min_sdk=21` | `min_sdk=23` |

The expectations are not a guess and the failures are not a task set that was
tuned to pass. Each one is checked against two independent readers of the
APK's bytes and the manifest committed beside the APK.

**This is a defect in the tool, not in the set**, and it is reported here
rather than fixed here: this work is not allowed to touch `src/`. The
direction of the fix is visible from the code. `src/dexatlas/tools/apktool/adapter.py`
says in its own comments that Apktool moves the version and SDK attributes out
of the manifest and into `apktool.yml` when it decodes, and its
`_merge_build_metadata()` fills the gap from that file when the manifest does
not carry the value. The manifest does carry it; the decoded copy does not.

---

## 7. How this set could be gamed

A benchmark that can be gamed is worse than no benchmark, because it reports
a number that means nothing. The ways this one could be gamed, and what stops
each:

**Read the task set and copy the expectation.** The tasks are in the
repository, and several ids say what the answer is
(`unanswerable.crypto-digestof-has-no-callers`). A system under test is
given `--emit-questions`, which carries the question, the sample and the
configuration, and a reference number in place of the id — the marking
scheme is not in it. **The rule for M3's three configurations is that a
system under test never reads `benchmarks/tasks/`.**

**Answer every question with nothing.** Every "there is nothing here"
question passes. The other 68 tasks want evidence, and a system that answers
everything with an absence fails them all.

**Answer every question with everything.** `must_not_contain` and
`expect_count` fail a padded answer: a task that wants exactly three call
sites fails on four, and a task about the demo application's exported
components fails if the answer mentions a receiver.

**Echo the question back.** The checks are against evidence, not against the
question. "Which method calls `Crypto.sign`?" answered with "`Crypto.sign`
has callers" fails: the caller has to be named.

**Guess something plausible for an unanswerable question.** The
`expect_empty` check fails on any evidence at all. Naming a caller for a
method nothing calls is exactly the failure this category exists to catch.
On a prose answer, the `must_not_contain` list names what a confabulator
would reach for.

**Weaken a rule until the task stops failing.** The runner checks every task
against its own wrong answer before it analyses anything, and refuses to run
if one of them accepts it. A rule that has stopped rejecting a fabrication
would make every other number meaningless, and the run says so.

**Special-case the sample.** The samples are public, so a system could
memorise the answers. This set is not a defence against memorisation, and it
is not meant to be: the point of M3's three configurations is that each of
them is given the same APK and has to work it out. A memorised answer is a
number that says nothing about the tool, which is an argument for the set
being **held back** from the systems under test — the questions can be
published, the expectations should not be, until the comparison has been
run.

**Return the manifest's `apktool.yml` value and call it the SDK level.** It
passes the four failing tasks and fails nothing else. This is not a cheat —
it is the defect of section 4.1, and it is in the open.

The last one is the honest summary of the set's value: it found a real
divergence between what an APK says and what the analysis reports about it,
and it did so because the expectation was written against the bytes rather
than against the tool.

---

## 8. Adding a task

1. **Find the fact in the sample's own sources.** Read the Smali, the
   manifest or the resources. If the fact is not written down there, the
   question is not ready — either it is not answerable, or the sample does
   not carry it.
2. **Write the task** in the module for its category, under
   `benchmarks/tasks/`. Give it an id that says what it is about, the
   question in a reader's words, the probe that asks it, and a `source` that
   names the file and the instruction in it.
3. **Say what a wrong answer looks like.** `must_not_contain` is where a
   plausible wrong answer is caught. If the question has a memorable wrong
   shape, write it down.
4. **Check the counts.** If the question is "how many", set `expect_count`.
   If the answer is that there is nothing, set `expect_empty` — and put the
   task in the `unanswerable` category, where it is scored.
5. **Run it.** `uv run --no-sync python benchmarks/run.py --task <id>.` A new
   task that fails on the current tool is a finding, not a mistake: say so in
   the pull request, with the file that establishes the expectation.
6. **Check that it can fail.** The runner does this for you — it checks every
   task against a wrong answer before it analyses anything — but if you have
   written a rule that accepts everything, that is the run that says so.

Adding a task needs no change anywhere else. The runner finds it through
`benchmarks/tasks/__init__.py`, and the category tally follows.

### 8.1 What a new task needs to be worth having

- **The source has to be checkable by a second person**, without running
  anything. That is the whole of the "independently checked" requirement.
- **The answer has to be specific.** "The APK talks to the network" is not an
  answer; `https://api.example.com/v1` is.
- **A question the analysis cannot answer is a task too**, and a better one
  than a question it can. It has to be scored, or it is decoration.

---

## 9. What is not measured here

- **The other two configurations of M3.** The milestone compares a model with
  source retrieval, a model with structured symbol search, and the DexAtlas
  agent. This document is about the task set they would all be measured on;
  only DexAtlas is measured now.
- **A private or commercial APK.** Every task is over the five first-party
  samples, whose sources are in the repository. That is what makes the
  expectations auditable, and it is also what makes them easy to memorise.
- **Token consumption, duration, recovery rate.** The runner does not measure
  them: it measures whether an answer is right, and it does so without a
  model. The other metrics in the milestone belong with the three
  configurations.
- **Why Apktool writes the SDK level it writes.** Section 4.1 states what was
  measured. The mechanism was not established.
- **Whether the failures would also fail under the other configurations.** The
  four failing tasks are asked with every backend installed, because that is
  the configuration in which a manifest exists at all.

---

## 10. What this document asks the next person to do

1. **Fix the SDK level.** The analysis reports a number that is not the
   APK's. The expectation is written down, and the fix has a test waiting
   for it: `manifest.min-sdk.wide` and its three siblings.
2. **Decide who may read the task set.** Section 7 says the marking scheme
   must not reach a system under test. M3's comparison depends on that
   decision being made before the comparison is run, not after.
3. **Add the third configuration's questions.** Two of the three
   configurations are covered by tasks today. A task set for a model with
   source retrieval would need questions about *where* the answer was found,
   not only what it was.
