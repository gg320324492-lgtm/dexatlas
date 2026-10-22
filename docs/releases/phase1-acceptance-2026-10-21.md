# Phase 1 acceptance — 2026-10-21

**Accepted commit:** `a1e81ce8ae262b84fa06bc5a3afb995fd0238660`
**Milestone tag:** `phase1-acceptance-2026-10-21`
**Baseline:** the `main` branch at that commit — **not** the published `v0.1.3`

> This is a milestone marker, not a release. Nothing here was published to a
> release; the capabilities below are in `main` and **not** in `v0.1.3`.

---

## What was accepted

Phase 1 is accepted as a **functional static-analysis MVP**: the analysis core,
the three backends and their fallbacks, the CLI, the REST API, the evidence
model and the reports.

| Protocol step | Artefact |
|---|---|
| 1. Version submission | `v0.1.0` … `v0.1.3` |
| 2. Architecture and code review | three reviews, **44 findings** |
| 3. Maturity assessment | [phase1-maturity-assessment.md](../reports/phase1-maturity-assessment.md) |
| 4. Review report | [phase1-review-report.md](../reports/phase1-review-report.md) |
| 5. Re-plan the next phase | [phase2-plan.md](../roadmap/phase2-plan.md) |

### The findings

| Severity | Count | State |
|---|---|---|
| Blocking | 6 | **all fixed** |
| Important | 16 | **all fixed** |
| Optional | 12 | not fixed; each records why it is not a defect |
| Deferred | 9 | each with two options and a recommendation, in [phase2-issue-list.md](../reports/phase2-issue-list.md) |

Every fix that the review produced carries a test **that fails when the fix is
reverted** — 21 breakage experiments were run to prove it.

### The CI at the accepted commit

| Configuration | Collected | Result |
|---|---|---|
| Python 3.12, all backends | 890 | 885 passed, 5 skipped |
| Apktool present, JADX absent | 890 | 883 passed, 7 skipped |
| Python 3.13, no JADX or Apktool | 890 | 812 passed, 78 skipped |

Six jobs, all green: the three test configurations, lint (ruff, ruff format,
mypy strict, actionlint, the version-claim check), the Docker image, and the
dependency audit.

---

## What this acceptance does **not** say

- **Not production readiness, not multi-user deployment, not a professional
  security audit tool.** It is an MVP that works.
- **The maturity score is a baseline, not a verdict.** The assessment's
  5.50 / 10 was measured on `b8ef71a` — *before* the review's fixes. It
  measures how severe the problems were. The accepted tree has **not** been
  assessed again, because that means really running a full analysis and
  recording who ran it, where, and when.
- **The accepted commit is 76 commits ahead of `v0.1.3`.** The capabilities the
  review produced must not be described as shipped in `v0.1.3` — they are in
  `main` and will first be published in `v0.2.0-pre`.

---

## The findings that shape Phase 2

Four of the review's findings are not merely bugs — they are the reason the
agent layer cannot be built on top of the analysis core as it stands.

| Finding | Why it matters for an agent |
|---|---|
| A method is resolved **by name alone** | Two overloads, one answer, and the wrong one is indistinguishable. It would travel straight into the agent's conclusion. |
| Symbols and evidence are **not committed as one snapshot** | A reader can see the symbols of one run beside the evidence of another. |
| Concurrent analyses of one APK **share a workspace** | They overwrite each other's intermediate files. |
| `VERIFIED` is constrained by **one rule**, not by a proof | A verified observation needs a *validated* provenance, not a string that looks right. |

These are M0 in the [Phase 2 plan](../roadmap/phase2-plan.md), and they are
scheduled before the MCP server — because a tool that returns the wrong
overload of a method is worse than no tool.

### One design correction the acceptance made

The first draft of the Phase 2 plan proposed giving the cross-reference table
the primary key `(project_id, caller, callee, kind)`. **That is wrong**: the
same caller reaching the same callee from two different bytecode offsets is two
*call sites*, and a unique key over the pair collapses them into one row. The
plan now separates the **call site** from the **call edge**, derives the edge
from its sites, and requires every count to say which of the two it means.

---

## Where to look

| | |
|---|---|
| [Review report](../reports/phase1-review-report.md) | what was found, what was fixed, what was deferred |
| [Maturity assessment](../reports/phase1-maturity-assessment.md) | six weighted dimensions, and the fourteen things the assessor could not verify |
| [Phase 2 issue list](../reports/phase2-issue-list.md) | the deferred findings, each with two options |
| [Phase 2 plan](../roadmap/phase2-plan.md) | M0–M4, with the acceptance criteria for each |
| [Status page](../status.md) | where the project stands now |
