# Call sites and call edges

Two different things have been called "a cross-reference" in this project, and
they were counted as one. This document says what each of them is, where it
lives, and how the two are told apart.

## The two

A **call site** is one place in the bytecode where a call happens. It names
the DEX file the instruction was read out of, the method that made the call,
the instruction offset inside that method, the opcode that carried the call,
and the method that was called.

A **call edge** is the relationship between two methods, aggregated over the
call sites that make it up.

They are not the same thing, and the difference is not a subtlety:

| | call sites | call edges |
|---|---|---|
| one method calls the same target twice | two | one |
| one method defined in two DEX files, each calling a target | two | one |
| the same call recorded twice by the same reader | one | one |

An edge is **derived** from the sites. Never the other way round: an edge that
exists without sites has nothing behind it, and the sites are what a citation
points at.

## What was wrong

The index held one row per call, and the row said who called whom, how, and
where it was read from. It had no key beyond that, so:

- a method that called the same target twice held **two rows that said exactly
  the same thing** — the reader could not tell "called twice" from "written
  twice";
- `Project.reference_count` counted rows, and the report printed it beside
  "cross-references with evidence", which counted something else. The Phase 1
  review found the two being read as one ratio, and they were not one.

The rows are call sites now. The key carries the DEX file **and** the
instruction offset, because those are what tell two calls apart: a key over
the caller and the callee alone collapses both kinds of duplication, and a key
that adds the offset but not the file collapses the cross-DEX one and loses
the provenance that says which file the call was read out of.

## Where it lives

`src/dexatlas/core/calls.py` holds the two models and the derivation:

- `CallSite` — a `MethodReference` plus `dex_name` and `instruction_offset`;
- `CallEdge` — a `MethodReference` plus `site_count`;
- `derive_edges(sites)` — the edges the sites describe, in a fixed order so
  that two runs over the same APK produce the same list and the same evidence
  ids.

`src/dexatlas/core/storage.py` holds the table:

```sql
CREATE TABLE call_sites (
    project_id         TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    caller             TEXT NOT NULL,
    callee             TEXT NOT NULL,
    kind               TEXT NOT NULL DEFAULT 'invoke',
    dex_name           TEXT NOT NULL DEFAULT '',
    instruction_offset INTEGER NOT NULL DEFAULT -1,
    provenance         TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, caller, callee, kind, dex_name, instruction_offset)
);
```

The `xrefs` table it replaces was rebuilt rather than altered: SQLite cannot
change a primary key in place, and the table is a cache of an analysis rather
than a source of truth, so the next analysis fills it again. The project's
own count of the rows goes with them — a record that says "23 cross-references"
while the table holds nothing is a number a reader cannot check.

## The offset

The DEX reader walks a method's instructions. Androguard's instruction object
does not carry an offset, so the offset is **the sum of the lengths of the
instructions before it**: the walk is over the method's own bytecode, so the
first instruction sits at zero and each one is as long as its encoding says.

A call that did not come out of bytecode has no offset, and it is recorded as
`-1` rather than as `0`: zero is a real offset — the first instruction of a
method — and a caller that cannot tell the two apart is looking at a number
that points somewhere it never went.

## The evidence

One record is made per called method of this APK, and it covers every call
site of that method. The record states **both** numbers, because it is about
two different things:

```python
detail = {
    "callers": [...],
    "call_site_count": sites,
    "call_edge_count": edges,
}
```

A record that stated only one of them would be stating half of what it knows,
and the report cannot put two numbers side by side when one of them does not
say which it is.

## The report and the API

The report prints five numbers, and each says which of the two it is:

| | |
|---|---|
| `Call sites indexed` | the rows the index holds |
| `Call edges indexed` | the distinct relationships those rows make |
| `Call sites with evidence` | the sites the records cover |
| `Call edges with evidence` | the edges those records cover |
| `Cross-reference records` | the records themselves |

The JSON report keeps the old names as well — `cross_references` and
`cross_references_with_evidence` — because their values did not change, so a
reader that knows them still reads the right number, and a reader that wants
to know what the number means has a name that says it. The schema version
moved to 2 when the run block was added.

The API's `/projects/{id}/xrefs/{method_id}` answers with `call_sites` and
`call_edges` beside the old `total`, and each reference in the list carries
the DEX file and the offset it was read from.

## What a citation can still follow

The citation of a call site is the edge's locator —
`androguard:<dex>#<caller>-><callee>` — and the **offset is not part of it**.
That is deliberate, and it is a limit rather than an oversight:

- the citation has to **resolve** inside the analysis, and a resolver can
  only check what the tools wrote out. The sources are Java and Smali, and
  neither carries a bytecode offset, so an offset in a locator would point at
  something nothing can check;
- a citation that looks more precise but cannot be followed is worse than one
  that is coarse and can. It would look like evidence of a place that nobody
  can check.

So the offset is **structured data** — a field on the site, a column in the
table, a value in the API response — and the citation says where the
relationship is. A reader who wants the exact instruction opens the smali and
counts to the offset.

## The two kinds of duplication

They are both call sites, and they are separated by the key rather than by a
rule:

- **the same method calling the same target twice** — the sites differ in the
  **instruction offset**;
- **the same method defined in two DEX files** — the sites differ in the
  **DEX file**, and each copy of the body holds its own calls.

The key carries both, so neither collapses into the other, and the edge count
is the same in both cases: one relationship.
