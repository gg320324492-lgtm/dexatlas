# Service scope — Python Backend & Automation

> **Draft for review — not published.**
> One-page scope statement for Upwork proposals in the *Python Backend &
> Automation* direction, based on what the DexAtlas repository demonstrates.
> Checked against the Upwork portfolio guidelines
> (<https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile>).
>
> **Identity note.** I am an individual freelancer. The examples below come
> from my own open-source project (DexAtlas); no client engagement, client
> result, or revenue/time-saving figure is claimed or implied.

---

## What I offer

Design and implementation of Python backends and automation pipelines: CLI and
REST API surfaces, data ingestion and normalization, structured storage,
scheduled or repeatable tasks, and machine-readable reports — with tests,
typing and documentation as part of the deliverable, not an afterthought.

Demonstrated by: **DexAtlas** (open source) — an Android APK analysis platform
with a FastAPI REST API, a CLI, a SQLite evidence store, three integrated
third-party engines, 1,847 tests at 93.3% coverage, strict mypy typing, and
CI across Python 3.12/3.13 and multiple engine configurations.

## Inputs (what I need from you)

- The existing tool, service, data format, or file format to integrate with.
- The expected pipeline: what comes in, what should come out, in what shape.
- Where it should run (your machine, a container, a CI job) and any runtime
  constraints.
- Access or sample data you are authorized to share, plus any compliance
  constraints on handling it.
- Acceptance criteria, if you already have them; otherwise we define them
  before work starts.

## Deliverables (typical)

- A Python package or service implementing the agreed pipeline.
- A CLI and/or REST API with documented endpoints and error semantics.
- Structured output (JSON/Markdown/SQLite/CSV as agreed) with a schema.
- An automated test suite covering the agreed behaviors, plus lint and typing
  configuration.
- A README/runbook: installation, configuration, usage examples, and known
  limitations.
- A short handover walkthrough (written; a call can be scheduled on request).

## Acceptance (how we agree it is done)

- Acceptance criteria are written down before implementation starts.
- Every deliverable is verified by a runnable test or a documented manual
  verification — a number or behavior nobody can re-derive is not a claim.
- You receive the test suite and run instructions, so acceptance is
  reproducible on your side, not a demo you have to take on faith.
- Milestones are reviewed against the written criteria; changes go through an
  agreed change process (below).

## Exclusions (what this service does not include)

- Penetration testing, vulnerability discovery on systems you do not own or
  are not authorized to assess, or security attestations.
- Continuous production operations, 24/7 on-call, or long-term managed
  hosting (I can hand over to your ops setup).
- Guaranteed performance at unspecified scale; load targets must be stated in
  the scope to be engineered and tested for.
- Mobile dynamic analysis, native-library (`so`) reverse engineering, or
  malware determination (the APK analysis I can offer is the limited static
  scope described in the DexAtlas example — see below).
- Content whose analysis or processing you are not authorized to perform.

## Data handling

- Your data stays where you put it: I work in the environment you designate
  (your machine, your repo, your container). Sample data needed for
  development is minimized and agreed in advance.
- Credentials and secrets are never committed to any repository; they are
  passed through your secret manager or environment, and rotated after the
  engagement on request.
- Nothing from your project is reused in other work or published without your
  written permission.

## Changes and scope adjustments

- New requests are triaged as: in-scope (small clarifications), a change
  request (estimated and agreed before work starts), or a new milestone.
- Nothing is "quietly absorbed": if a request changes the estimate, you see
  the impact before I proceed.
- If a technical discovery invalidates an assumption, I stop, report it with
  evidence, and we re-plan together.

## A concrete example from my own work (DexAtlas)

Input: an Android APK file. Pipeline: hashing and validation → manifest
decoding → three-engine symbol indexing (Androguard, JADX, Apktool) →
evidence-grade storage in SQLite → Markdown/JSON reports with per-fact
provenance. Exposed through a CLI and a FastAPI REST API. Every engine
failure is captured as a value and reported, so a partially analyzable input
still produces a complete, honest report. This is the engineering style I
would bring to your backend or automation task.

---

*Draft for review — not published. Personal project example; no client
engagement is described or implied.*
