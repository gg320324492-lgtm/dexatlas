# Call sites and call edges

What a cross-reference counts, and which number is which.

## Why there are two numbers

A cross-reference index answers two different questions, and they have
different answers:

* **where** does this method call that one? — the **call sites**: one per
  place in the bytecode, with the dex file and the instruction offset that
  place sits at;
* **what** is the relationship between these two methods? — the **call
  edges**: one per caller, callee and way of calling.

The index used to hold one row per *call*, with no primary key, and every
count in the project, the API and the report quoted that row count. The demo
application holds 21 relationships and 23 calls, and the report said "23
cross-references". A reader who took that for the number of relationships
was reading 21 edges twice over — the two calls `Crypto.sign` makes to
`StringBuilder.append` are two instructions in one method, and the table
could not tell them from one call written twice.

The two kinds of duplication are different, and a design that only handles
one of them loses data:

| What happened | Call sites | Call edges | What tells them apart |
| ------------- | ---------- | ---------- | --------------------- |
| One method calls the same target twice (two invoke instructions) | 2 | 1 | the instruction offset |
| The same method is defined in two dex files, and each copy calls the same target | 2 | 1 | the dex file |

A key that carried only the offset would collapse the second case and lose
the citation of the second dex file. A key that carried only the dex file
would collapse the first case and lose a call. The key carries both.

## The model

`CallSite` and `CallEdge` live in `core/calls.py`.

| Field | What it is |
| ----- | ---------- |
| `caller`, `callee` | The two methods, in the canonical method id. |
| `kind` | The opcode that carried the call: `virtual`, `static`, `direct`, `interface`, `super`. |
| `dex_name` | The dex file the instruction was read out of. A site is a place in *this* apk. |
| `instruction_offset` | Where in the caller's bytecode the instruction sits, in bytes from the first instruction. It is what tells two calls from the same method to the same target apart. |
| `provenance` | Where the call was read from. The citation names the method whose bytecode the call was read out of — a class of this apk, so it resolves inside this analysis — and the dex file it was read from is named in it. |

`CallSite` is a `MethodReference` that knows where it is. A reference that
did not come out of bytecode names no place, and is stored as a site whose
place is not known (`dex_name` empty, offset `-1`) — the same thing a
workspace written before places were recorded holds.

`CallEdge` is the aggregation: the caller, the callee, the kind, the number
of call sites it is made of, and the union of their citations.

**An edge is derived from its call sites, never the other way round.** The
sites are the finer-grained truth, and a table of edges cannot recover them:
the two calls a method makes to the same target are one row in a table of
edges, and there is nothing in that row that says there were two.

## The tables

| Table | One row is | Key |
| ----- | ---------- | --- |
| `call_sites` | one place in the bytecode where a call happens | `(project_id, dex_name, caller, callee, kind, instruction_offset)` |
| `xrefs` | one relationship between two methods | `(project_id, caller, callee, kind)` |

`xrefs` is the table the API and the CLI read, and it is the table a reader
who writes SQL against the workspace meets. It holds one row per edge, and
the citation of an edge is the union of the citations of the call sites it
is made of: the same edge read from two dex files is one row with two
citations, and dropping the second would lose a place the call was read.

## What the numbers say

Every count now says which of the two it is.

| Where | Sites | Edges |
| ----- | ----- | ----- |
| `Project.reference_count` | — | the number of call edges |
| `AnalysisResult.call_site_count` | the number of call sites | — |
| `GET /projects/{id}` | `call_site_count` | `reference_count`, `call_edge_count` |
| `GET /projects/{id}/xrefs/{method_id}` | `call_site_count`, `call_sites` | `total`, `total_unit`, `call_edge_count`, `references` |
| The Markdown report | "Call sites indexed", "Call sites with evidence" | "Call edges indexed", "Call edges with evidence" |
| The JSON report (`schema_version` 3) | `call_sites`, `call_sites_with_evidence` | `cross_references`, `call_edges`, `call_edges_with_evidence` |

### The change to the API's `total`

`GET /projects/{id}/xrefs/{method_id}` answered `total = 4` for a method two
callers call twice, because `total` was the row count of a table that held
one row per call. A reader concluded that four places call the method; there
are two callers and four places.

`total` now counts the **call edges**, and says so:

```json
{
  "total": 2,
  "total_unit": "call_edges",
  "call_edge_count": 2,
  "call_site_count": 4,
  "references": [ ...one row per edge... ],
  "call_sites": [ ...one row per place in the bytecode... ]
}
```

`total_unit` is new, and the two counts are new. The value of `total`
changed for a method that is called more than once, so this is a change to
the API's contract: the number it answers with is a different number. A
client that read `total` as "how many callers" was reading a number that
never said what it counted; a client that read it as "how many places" now
reads `call_site_count`.

### The change to the report's numbers

The Markdown report's "Cross-references indexed" is now "Call edges
indexed", and "Call sites indexed" is beside it. The JSON report's
`cross_references` is the call edge count, and `call_sites` is beside it.
The JSON report's `schema_version` moved from 2 to 3 for this: a reader who
ignores unknown keys is unaffected, and a reader who reads them has both
numbers.

## The migration

The old `xrefs` table had no primary key, so `CREATE TABLE IF NOT EXISTS`
could not change it: the table had to be dropped and created again. The
rows are read out before that happens, because their citations are worth
keeping — the same edge read from two dex files is one edge with two
citations, and a rebuild that kept only the first would lose a place the
call was read.

What the old rows cannot say is *where* the call was: the old index never
recorded the instruction. The places come back with an unknown offset, and
two calls the old index could not tell apart are one row again. That is the
honest answer for a workspace that never knew the difference, and the next
analysis fills the offsets in.

The project's own count is corrected with the table: a record that says 23
while the table holds 21 edges is a number a reader cannot check.
