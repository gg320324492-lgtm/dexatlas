# Service scope — Evidence-first AI / MCP Integration

## What I offer

Integration of AI assistants and LLM-based workflows with your existing data
and tools through **MCP (Model Context Protocol)** and tool APIs — with an
evidence-first design: the assistant reads your real data through controlled,
least-privilege tools, and every answer is traceable to the records it came
from. Model output is treated as a lead, not a finding; your system stays the
source of truth.

Demonstrated by **DexAtlas** (open source): a read-only MCP server (eleven
tools over stdio) exposing an existing analysis to AI assistants, plus a
single-loop, budget-bounded agent that answers with cited evidence and
separates verified facts from leads and unknowns. No write path, no shell
execution, no model dependency in the tool layer.

## Inputs (what I need from you)

- The system or dataset to integrate, and who may read what.
- Which assistant/tool surface you use (Claude, ChatGPT, an in-house agent).
- Your budget boundaries for model usage, if any.

## Deliverables (typical)

- An MCP server or tool layer over your existing capability — read-only
  unless agreed otherwise.
- A short operator guide: what the tools expose, what they never do, and how
  to verify an answer against the records it cites.

## Acceptance (how we agree it is done)

- The tool list is reviewed and frozen before implementation.
- Every tool is demonstrated against your real data, and the answers are
  checked against the underlying records.
- The boundary is written down: what the integration does, and what it
  explicitly does not do.

## Exclusions (what this service does not include)

- No write access to your production systems unless separately agreed and
  scoped.
- No autonomous agents that act without an audit trail.
- No model training on your data.

## Model costs and budget boundaries

Tool calls are the cheap part; model tokens are not. The default posture is
single-loop with a budget cap and tool outputs sized to what the model needs
— not whole databases. Budgets are agreed up front and visible in the
operator guide.

## Data handling

Your data stays in your systems. The integration reads through the tools it
ships; nothing is copied to a third party, and nothing is sent to a model
that you have not chosen.

## A concrete example from my own work (DexAtlas)

An Android static-analysis platform with a read-only MCP server over its
existing analysis: an assistant can list what was analyzed, search symbols,
read the exact source a finding cites, and resolve every claim to the record
that produced it — read-only, budget-bounded, with the evidence attached.
