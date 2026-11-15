# Upwork cover letter templates

> **Draft for review — not published.**
> Two proposal-letter templates, one per service direction, aligned with the
> scope documents in this folder
> ([scope-backend-automation.md](scope-backend-automation.md),
> [scope-ai-mcp.md](scope-ai-mcp.md)) and the project entry
> ([project-brief.md](project-brief.md)).
> Checked against the Upwork portfolio guidelines
> (<https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile>).
>
> **Identity note.** Both letters describe only my personal open-source
> project (DexAtlas) as prior work. No client engagement, revenue figure, or
> security-testing result is claimed. Each letter emphasizes verifiable
> evidence and a clear scope, and neither promises general autonomous
> analysis or security-testing conclusions.

Usage notes:

- Replace every `{{...}}` placeholder before sending; delete the sections
  that do not apply to the job post.
- Keep the first two paragraphs the same — they state the understanding of
  the job and the concrete plan, which is what a client reads first.
- Attach the matching scope document and, where the platform allows, point to
  the repository's case studies as reproducible work samples.

---

## Template 1 — Python Backend & Automation

**Subject: {{job title}} — a testable pipeline with acceptance criteria you can re-run**

Hi {{client name}},

You are looking for someone to {{one-line restatement of the job post's goal
in the client's words}}. Here is how I would approach it, and what you would
be able to verify at the end.

**What I would deliver:**

- {{Deliverable 1, e.g. "A Python service that ingests your {{input format}}
  and produces {{output format}} with a documented schema"}}
- {{Deliverable 2, e.g. "A CLI and/or REST API with error semantics and a
  runbook"}}
- {{Deliverable 3, e.g. "An automated test suite plus lint/typing
  configuration, wired into your CI if you have one"}}

**How you verify it:** every deliverable ships with a runnable test or a
documented manual verification. Before we start, I write the acceptance
criteria into the milestone; at handover you re-run them yourself instead of
taking a demo on faith.

**How I work:** milestones with written criteria, changes estimated before
they are started, and no silent scope absorption. Your data stays in the
environment you designate; secrets never go into code or repositories.

**Relevant example (my own open-source work):** DexAtlas, an Android APK
analysis platform I built end to end — a FastAPI REST API and CLI over a
SQLite evidence store, three integrated analysis engines with per-engine
failure reporting, ~1,370 automated tests at 91.6% coverage, and CI across
Python 3.12/3.13. It is the same engineering style I would bring to your
task: {{one sentence tying it to the job, e.g. "ingest messy binary input,
normalize it, and produce structured, auditable output"}}.

A few questions to make sure the estimate is right:

1. {{Question about input volume/frequency, e.g. "How many {{items}} per day
   should the pipeline handle?"}}
2. {{Question about environment, e.g. "Should this run in your cloud, a
   container, or on-premise?"}}
3. {{Question about acceptance, e.g. "Do you already have acceptance
   criteria or a reference output I should match?"}}

I can start with a short scoping pass (fixed fee) and give you a written plan
with milestones before any implementation begins.

Best regards,
{{your name}}

---

## Template 2 — Evidence-first AI / MCP Integration

**Subject: {{job title}} — AI integration with auditable, evidence-backed answers**

Hi {{client name}},

You want an AI assistant to work with your {{data/tools}}, and the key risk
is usually not the model — it is whether its answers can be trusted and
audited. My approach is evidence-first: the assistant reads your real data
through controlled tools, and every answer traces back to the records it
came from.

**What I would deliver:**

- {{Deliverable 1, e.g. "An MCP server exposing your {{systems}} to AI
  assistants with read-only permissions, bounded responses, and audited tool
  calls"}}
- {{Deliverable 2, e.g. "An agent workflow that plans tool use within an
  agreed budget and reports verified findings, leads, and unknowns
  separately"}}
- {{Deliverable 3, e.g. "An evaluation pack: a set of questions with expected
  evidence and recorded results, so you can re-check behavior after any
  change"}}

**How you verify it:** the tool layer is covered by automated tests that need
no model; the model-driven behavior is checked against the evaluation set we
agree on, and both passes and failures are recorded and shown to you. Claims
in the final output are graded — verified, lead, or insufficient — and model
text is never recorded as a verified fact.

**Costs and budget:** you own the model account and API keys; model usage is
billed directly to you with no markup from me. Before any run we agree on the
model, a per-run and total cost ceiling, and what happens when the ceiling is
hit. I list every model call made during the engagement in the handover notes
so you can audit it against your invoice.

**Scope boundaries I hold to:** this is integration and evaluation engineering,
not autonomous security testing or a promise that the AI "finds all issues".
The agent works within your question set and your budget, and treats model
output as a lead that a human confirms — not as a finding.

**Relevant example (my own open-source work):** DexAtlas — a read-only MCP
server (eleven tools over stdio) exposing a completed Android APK analysis to AI
assistants, plus a single-loop agent that answers questions with per-fact
citations, separates verified evidence from leads, and treats instructions
found inside analyzed data as data, not orders. The tool layer has no write
path, no shell execution, and no model dependency.

A few questions to make sure the estimate is right:

1. {{Question about data access, e.g. "How should the assistant access your
   data — API, database, or files?"}}
2. {{Question about the question set, e.g. "What are the 5–10 concrete
   questions the assistant must answer reliably?"}}
3. {{Question about model/provider constraints, e.g. "Which provider/model
   and privacy rules apply? Does any data need to stay on-premise?"}}

I can start with a short scoping pass (fixed fee) that produces the written
scope, the evaluation set, and a budget plan before implementation begins.

Best regards,
{{your name}}

---

*Draft for review — not published. Both templates describe only personal
open-source work; no client engagement, security-testing result, or revenue
figure is claimed or implied.*
