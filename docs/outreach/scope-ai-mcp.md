# Service scope — Evidence-first AI / MCP Integration

> **Draft for review — not published.**
> One-page scope statement for Upwork proposals in the *Evidence-first AI /
> MCP Integration* direction, based on what the DexAtlas repository
> demonstrates. Checked against the Upwork portfolio guidelines
> (<https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile>).
>
> **Identity note.** I am an individual freelancer. The examples below come
> from my own open-source project (DexAtlas); no client engagement, client
> result, or revenue/time-saving figure is claimed or implied.
>
> **Where this goes.** This sheet is an attachment. If the platform's
> project-description field is the target, paste *What I offer* (773
> characters as written); the rest of the sheet is the attachment.

---

## What I offer

Integration of AI assistants and LLM-based workflows with your existing data
and tools through **MCP (Model Context Protocol)** and tool APIs — with an
evidence-first design: the assistant reads your real data through controlled,
read-only or least-privilege tools, and every answer it produces is
traceable to the records it came from. Model output is treated as a lead, not
a finding; your system stays the source of truth.

Demonstrated by: **DexAtlas** (open source) — a read-only MCP server (eleven
tools over stdio) exposing an existing analysis to AI assistants, plus a
single-loop, budget-bounded agent that answers questions with cited evidence
and separates verified facts from leads and unknowns. No write path, no shell
execution, no model dependency in the tool layer.

## Inputs (what I need from you)

- The existing data sources, services, or tools the assistant should work
  with, and how they are accessed (API, database, files).
- A bounded question set: the concrete questions or tasks the AI integration
  must handle. (A bounded set is what makes behavior testable and costs
  predictable.)
- Your model and provider constraints: which provider/model, privacy rules,
  and any data that must not leave your environment.
- Who owns the model account and API keys (see cost attribution below).
- Acceptance criteria, or the willingness to define them with me before work
  starts.

## Deliverables (typical)

- An MCP server or tool layer exposing your data/operations to AI assistants,
  with explicit permissions (read-only by default), bounded responses, and
  audited tool calls.
- An agent or workflow design that plans tool use within a stated budget and
  reports: what was established (with citations), what is only a lead, and
  what could not be established.
- An evaluation pack: a set of questions with expected evidence, a runner,
  and recorded results — so behavior can be re-checked after any change.
- Documentation: architecture, tool catalog, safety boundaries, and the
  evidence/citation format.
- Tests for the tool layer (deterministic, no model needed) and recorded
  evaluations for the model-driven parts.

## Acceptance (how we agree it is done)

- Acceptance criteria are written before implementation starts.
- The tool layer is verified by automated tests; model-driven behavior is
  verified by the agreed evaluation set, and both passes and failures are
  recorded — a failed evaluation is information, not an embarrassment to
  hide.
- Claims in the final report are graded: verified (from your data via tools),
  lead (model suggestion needing human confirmation), or insufficient. Model
  text is never recorded as a verified fact.
- You can re-run the evaluation pack yourself after handover.

## Exclusions (what this service does not include)

- Autonomous vulnerability discovery, autonomous security testing, or any
  agent authorized to modify systems, execute shell commands, or act without
  human review.
- Claims that the AI "finds all bugs", "replaces analysts", or outperforms
  all other models — I do not make those claims, and I will push back if a
  scope assumes them.
- Training or fine-tuning of models on your data (can be discussed
  separately, but is not part of this service).
- Model behavior guarantees beyond the tested question set.

## Model costs and budget boundaries

- **You own the model account and the API keys.** Model usage is billed by
  your provider directly to you; I never mark up model costs.
- Before any model-connected run, we agree a **budget boundary**: which
  model(s), an approximate token/cost ceiling per run and in total, and what
  happens when the ceiling is reached (stop, degrade, or ask).
- Development and testing use the cheapest adequate model by default; you can
  upgrade the target model at any time — the tool layer is model-agnostic.
- All model calls made during the engagement are listed in the handover notes
  with their purpose, so you can audit them against your provider invoice.

## Data handling

- The tool layer runs in your environment; your data does not leave it except
  through the model calls you have authorized, under the privacy rules you
  set.
- Tool responses are bounded and logged; the agent's evidence records carry
  citations back to your records, so any answer can be audited.
- Secrets stay in your secret manager, never in code or prompts; prompts are
  treated as potentially sensitive and are not logged to third parties by the
  integration.

## Changes and scope adjustments

- New question types or tools are triaged as in-scope clarifications, change
  requests (estimated first), or new milestones.
- Model/provider changes are treated as configuration changes and re-run
  against the evaluation pack before acceptance.
- If evaluation shows the approach does not meet the agreed bar, I report
  that with the recorded evidence and we decide together: adjust scope,
  adjust budget, or stop.

## Availability and contact

I work in the `Asia/Shanghai` time zone and am available on weekdays,
10:00-18:00 (`UTC+8`). Contact: <hello@dexatlas.example> or the platform's
message thread.
*(Placeholder contact during the development phase - replace with a live
mailbox before publishing.)*

## A concrete example from my own work (DexAtlas)

Input: a completed APK analysis stored in a local workspace. Integration: a
read-only MCP server exposing projects, symbols, call sites, evidence and
locators to an AI assistant; a single-loop agent that plans tool calls within
a budget and answers questions like "which components are exported and what
permissions do they need" with per-fact citations. The agent separates
verified findings from leads, never records model text as verified, and
treats instructions found inside analyzed data as data, not orders. This is
the design discipline I would bring to your AI/MCP integration.

---

*Draft for review — not published. Personal project example; no client
engagement is described or implied.*
