# Evidence invariants

**What a `verified` record has to be true of, and what stops a record that is not.**

---

## 1. The problem this answers

Until Phase 2 item P2-004, the evidence level was a **convention**. A caller
passed `level=EvidenceLevel.VERIFIED` and the record was written. One rule
stood in the way of the worst of it — a `BEHAVIOUR` record could not carry
`VERIFIED` — and one rule is not a proof. Nothing stopped a caller from
recording a behaviour as verified under a different kind, and nothing stopped a
caller from attaching a locator that named a file the analysis never wrote.

The cost of that is not a wrong row in a table. The report renders every
verified record as *"Deterministically established by an analysis tool"*, and
the reader is meant to follow the citation to the place the tool read. A
record whose citation names nothing puts a false sentence in the report, and a
reader who believes it acts on a guess.

So `verified` is not a label a caller chooses. It is a claim about a citation,
and the claim has to hold up.

---

## 2. Two contracts, kept apart

There are two kinds of thing a record can be, and they have different rules.

| | **A deterministic observation** | **A model-generated claim** |
|---|---|---|
| What it is | something a tool read | something a model said |
| How it is written | `EvidenceBuilder.add(...)` | `EvidenceBuilder.add_claim(...)` |
| May be `verified` | yes, when the citation resolves | **never** |
| What backs it | provenance that resolves inside the analysis | the level, and nothing else |

The claim path is not the observation path with a different level. It refuses
`VERIFIED` outright, so a caller cannot write a verified claim by mistake as
easily as on purpose. And the observation path refuses a verified record whose
provenance does not resolve, so a claim that names a place cannot buy itself a
finding by pointing at one.

A claim that a tool later confirms is **not** that claim promoted. It is the
tool's own record, written through `add()`, and the two say different things:
one is what a model suspects, the other is what a tool read.

The `Evidence` model refuses `BEHAVIOUR + VERIFIED` on its own, whichever way
the record is built, so the rule holds even for a record that does not come
from the builder.

---

## 3. The locator resolver

`src/dexatlas/core/locators.py` is the part that tells a citation that looks
right from a citation that arrives.

A **locator** is a pointer in the shape `<tool>:<place>[#<fragment>]`:

| Shape | Example |
|---|---|
| a file in a backend's tree | `jadx:sources/com/example/demo/Crypto.java` |
| a member of that file | `jadx:sources/com/example/demo/Crypto.java#sign` |
| a directory of files | `jadx:sources` |
| a class in a dex file | `androguard:classes.dex#com.example.demo.Crypto` |
| a method of that class | `androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.sign(Ljava/lang/String;)V` |
| a call edge | `androguard:classes.dex#com.example.demo.Crypto.sign()V->com.example.demo.Other.hash()V` |
| a backend failure | `jadx:error/not_installed` |

`LocatorResolver` is given the **workspace of one analysis** and the names of
the APK's dex files, and answers for each locator whether it resolves there.
It never computes a workspace path: the workspace is an argument, because the
workspace moves. A published run lives in a versioned directory of its own, and
a resolver that derived the path from a project id would look in the wrong
place the moment that changed. `Store.get_workspace(project_id)` is where a
caller finds it.

### What resolving means

**The place.** A `jadx:` or `apktool:` locator names a path inside that
backend's tree in the workspace — `jadx/…` under the `jadx` directory,
`apktool/…` under the `apktool` one. The path has to exist, and it has to
stay inside the tree it belongs to: a path that climbs out is refused, and so
is one that leaves the tree through a symlink. An `androguard:` locator names a
dex file of the analysed APK, and the place resolves when the APK has that dex
file.

**The member.** A locator with a fragment names something *inside* the place,
and that is checked too:

- a method named in a Java source has to be **declared** there, not merely
  called — `return sign(key)` is a call, `public String sign(String key)` is a
  declaration;
- a method named in a smali file has to match the **descriptor** exactly, so
  two overloads are two things;
- a class named in a dex file has to be in the analysis, which the decoded
  smali says;
- a method of that class has to be declared in it.

**The absence of a backend.** A locator into a tree the analysis does not have
is *absent*, not fabricated: a backend that never ran wrote nothing, so it
named nothing here. The resolver says which of the two it is, and the builder
treats them differently.

---

## 4. The rules

### On the model — always on, no context needed

- A `BEHAVIOUR` record may not carry `VERIFIED`.
- A `VERIFIED` record whose kind is `CODE_LOCATED` must carry provenance. A
  located finding with no citation names no place, so it cannot be what the
  report says it is.

### On the builder — needs the analysis, so it is checked there

A `VERIFIED` record of kind `CODE_LOCATED` or `CROSS_REFERENCE` is **refused** —
with `InvalidProvenanceError` — when:

| The case | What is wrong |
|---|---|
| **empty** | there is no provenance at all |
| **stale** | the provenance names another APK, or a file this analysis does not hold |
| **mismatched** | the locator climbs out of its tree, names a backend that did not run, or names a dex file the APK does not have |
| **fabricated** | the locator is well formed and the file is there, but the class or method it names is not |

The last one is the one that matters most: a fabricated citation is
indistinguishable from a real one by looking at it. Only a resolution tells
them apart.

The two kinds are not treated the same way, and the difference is what the
record *claims*:

- a **located** finding is nothing but its place — "here is the thing, in this
  file, at this method" — so it is refused outright when the builder was not
  told which workspace the analysis lives in. There is no way to check a
  citation without the analysis it belongs to, and a record that claims to be
  verified is refused rather than believed on the strength of a string that
  looks right.
- a **cross-reference** is a fact about the index, and the index is the
  analysis's own artifact: the DEX reader read that edge out of the bytecode.
  It is checked the same way when there is an analysis to check it against,
  and written the way the index states it when there is not.

Records that are **not** findings about code are not subject to the resolution
rule, and are not weakened by it:

- a `DECLARATION` is the index — *this class exists* — and the index may be
  bare;
- an `OBSERVATION` is a statement about the analysis — *jadx produced real Java
  for 7 of 8 methods* — and it points at the analysis rather than at a place
  in the code;
- a `LEAD` is not a finding, so a citation that does not resolve does not stop
  it from being recorded.

---

## 5. What this does not do

Honesty about the edges:

- **A Java descriptor narrows by the number of arguments, not by the types.**
  The source does not spell the descriptor, so `sign(String)` and `sign(int)`
  are the same declaration as far as the source can tell. In smali the
  descriptor *is* spelled, and there the match is exact.
- **A class in a dex file can only be refuted when the analysis decoded the
  APK into smali.** Without an smali tree there is no way to ask whether a
  class is in the analysis, and a question that cannot be asked refutes
  nothing. The dex file's *name* is still checked against the APK.
- **The resolution rule is checked when the builder knows the workspace.** The
  builder takes it as an argument (`EvidenceBuilder(workspace=...)`), and the
  analysis has to pass it — see below. A cross-reference is the one record
  whose citation goes unchecked in the meantime.
- **A record that is read back from the database is not re-checked.** The
  database holds what was written, and a record that was written by an older
  build is still a record. The rules are about what can be *written*.

---

## 6. The integration point

`EvidenceBuilder` takes the workspace and the APK's dex files as arguments:

```python
EvidenceBuilder(
    project_id=project.id,
    tool_versions=project.tool_versions,
    apk_sha256=apk.sha256,
    workspace=workspace,
    dex_files=apk.dex_files,
)
```

Until the analysis passes them, the resolution half of the rule is off in the
real pipeline: a cross-reference's citation goes unchecked, while a located
finding is refused rather than believed. The change is one call site, in
`core/pipeline.py`, where the workspace is already in hand.

The four backend configurations were run with the change applied — all three
backends, JADX alone, Apktool alone, and Androguard alone — and the analysis
completes in each, with every cross-reference's citation resolving.

The backend-relative layout under that root — `jadx/` and `apktool/` — is the
contract between the resolver and the analysis. It is the same contract the
rest of the project already uses, and it is what lets the workspace move to a
versioned run directory without anything here changing.

---

## 7. What the report should say

The report's level table says of `verified`:

> Determininistically established by an analysis tool.

That sentence is now stronger than it was, and it should say so. The wording
this change asks for:

> Determininistically established by an analysis tool, with a citation that
> resolves inside this analysis.

and the closing sentence of the report, which today reads

> This report describes only what was deterministically established by the
> analysis tools listed above.

…should keep saying that, and add that a verified record's citation resolves
inside the analysis the report describes.

The renderer is not changed here: it belongs to whoever merges this, so that
the report is changed in one voice.
