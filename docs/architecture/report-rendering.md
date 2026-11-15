# Report rendering and the evidence package

How one analysis becomes three reports and one exportable package — and why
the reports cannot drift apart.

## One data layer, three renderings

An analysis produces exactly one `AnalysisResult` (`core/pipeline.py`): the
project, the manifest, the evidence, the run. Everything a report can say
comes from it. The rendering layers read that one object and differ only in
how they present it:

| Layer | File | Reader |
|---|---|---|
| Markdown | `reports/markdown.py` | a person reading the file in a repo or an issue |
| JSON | `reports/json_report.py` | a program, and the CLI/API's shared shape |
| HTML | `reports/html_report.py` | a client who installs nothing and opens one file |

The shared numbers live in `reports/summary.py`. `summary_metrics()` returns
the metric table once, and all three renderings state those values. A count
that changes in the model changes in every format at the same moment; a
format that computes its own number would be a second, competing source of
truth, and this project has one.

The boundary is strict: **a rendering layer adds no fact and recomputes
none.** It may format (thousands separators), it may select (the evidence
table is capped at 200 rows in Markdown and HTML alike), it may explain
(each evidence level's meaning is rendered next to the count) — but it may
not derive a number the model did not state.

## The HTML page is offline and inert

The HTML report exists so a client can read a delivery without installing
DexAtlas or connecting to the author's machine. Two properties make that
safe:

- **Self-contained.** No script runs, no stylesheet or image is fetched, no
  iframe loads anything. The file renders on a machine with no network.
- **Escaped.** Every string the analysis did not produce — sample strings,
  class names, component names, tool versions, error messages — goes through
  `html.escape()` before it reaches the page. A hostile APK can write text
  into the report; it cannot write markup. A summary that says
  `<script>alert(1)</script>` renders as those characters, visible and
  inert, never as an element the browser executes.

The page also carries the same honesty markers the Markdown report carries:
the run it describes, a later attempt that published nothing, index gaps,
backend errors, and the cap on the evidence table.

## The minimal evidence package

`dexatlas export <project> --output package.zip` (`reports/evidence_package.py`)
writes an explicit selection, not a workspace dump:

- `reports/report.json`, `reports/report.md`, `reports/report.html` — the
  analysis in all three renderings, from the published snapshot.
- `sources/…` — only the source fragments the evidence cites.
- `manifest.json` — the project/run identity, tool versions, and a SHA-256
  checklist of every packaged file.

What is deliberately **not** packaged is stated in the manifest's
`not_included` block: the client's APK (identified by its SHA-256), the full
source tree, and string constants no evidence record cites. A package that
implied more than it holds would be the failure mode this block exists to
prevent.

### Verification

`verify_package()` checks, in order: the manifest's schema version; that no
archive entry name climbs out of the package (`../`, absolute paths, Windows
separators, drive letters — the whole archive is refused, not stripped entry
by entry); that every file matches its manifest hash; and that the manifest's
project/APK binding matches what the packaged report itself describes. A
package whose manifest names one sample while its report describes another is
mislabeled evidence, and is refused as such.

`verify_citations()` is the migration check: after the package is copied
anywhere, a `jadx:sources/…` locator resolves against the package's own
`sources/` tree, because the package keeps each cited file at the same
relative place the locator names. Nothing in the package points at the
machine that made it.
