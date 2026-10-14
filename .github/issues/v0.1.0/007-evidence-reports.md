# Implement evidence-based report generation

**Priority:** P1 · **Depends on:** [#006](006-unified-api-cli.md)

Generate reports in which every claim can be checked without opening a database.

## Scope

- `core/evidence.py`: `EvidenceBuilder` — evidence records with ids and levels
- `core/models.py`: `Evidence`, `EvidenceKind`, `EvidenceLevel`
- `reports/json_report.py`: the machine-readable form
- `reports/markdown.py`: the human-readable form

## The evidence discipline

This is the mechanism behind "evidence over speculation", and it is the project's main
differentiator. Three levels:

| Level           | Meaning                                                    |
| --------------- | ---------------------------------------------------------- |
| `verified`      | Reproduced by a deterministic tool, with a locatable code location |
| `lead`          | A static-analysis or model-suggested risk indicator. Not a confirmed issue |
| `insufficient`  | Not enough evidence either way. Needs human validation       |

Two rules follow, and both are tested:

- **A level is passed explicitly by the caller, never inferred from the summary text.**
  A record worded `CONFIRMED VULNERABILITY: hardcoded credential` submitted as a `lead`
  stays a `lead`.
- **A backend failure is `verified` evidence.** That the tool failed is a fact. The
  absence of a result is not.

## Design decisions

- Evidence ids are sequential and stable across re-analysis (`E-0001`, `E-0002`, …), so
  an id in a report resolves back to the same row in the database.
- Every record carries provenance: source tool, tool version, APK hash, locator.
- **Backend errors appear in the report rather than being omitted.** A report that hides
  which steps did not run is exactly the report that gets over-trusted.
- Caller lists are truncated with an explicit `truncated` flag rather than silently
  cut off.
- Report output is **ASCII**. Reports are written to files, diffed and pasted into
  issues; an arrow or em dash turns into mojibake wherever the reader's encoding is not
  UTF-8.

## Acceptance

- [x] Evidence ids are sequential and constant-width
- [x] Level is never inferred from wording
- [x] Backend failures are recorded as evidence and shown in the report
- [x] Every record carries provenance
- [x] Exported components are recorded once, not per component
- [x] Long caller lists truncate with a flag
- [x] The JSON report is serialisable and round-trips
- [x] The Markdown report renders levels, errors, manifest and evidence
- [x] Pipe characters in summaries are escaped so the table does not break
- [x] An empty report states that plainly
