# The evidence-first agent

One orchestrator. It takes an analysis question about an APK, plans a bounded
series of tool calls, makes them against a DexAtlas workspace, checks that its
conclusions have evidence behind them, and reports what it found — separated
into what was established, what is a lead, and what is not established.

It is not a swarm of agents. There is one loop, one plan, one budget, one
state, and one report.

> **Evidence before inference. Correctness before autonomy.**

## The loop

```text
  question
     │
     ▼
  1. plan ──────────── which project, which tools, how many calls
     │
     ▼
  2. resolve ───────── the project, the run, and how complete the analysis is
     │
     ▼
  3. ask ───────────── the model what to read
     │
     ▼
  4. read ──────────── through the MCP tools; record what came back as evidence
     │
     ├── the model asked for another tool ──► back to 3
     │
     ▼
  5. check ─────────── every conclusion against the evidence
     │
     ▼
  6. record ─────────── a lead, or insufficient evidence — never a finding
     │
     ▼
  7. report ─────────── established facts · leads · insufficient evidence
     │
     ▼
  8. save ───────────── the state, so the task can be picked up again
```

Steps 3 and 4 are the only ones that involve a model, and the model is not in
charge of any of the rest.

## The package

```text
src/dexatlas/agent/
├── orchestrator.py       the loop
├── planner.py            a question into a bounded plan
├── tool_executor.py      the MCP tools, with a timeout, retries and a breaker
├── evidence_verifier.py  the line between a lead and a finding
├── state.py              the task state machine
├── providers/            the model endpoints
│   ├── base.py             the interface, and the two channels
│   ├── openai_compat.py    an OpenAI-compatible endpoint
│   ├── local.py            a local model endpoint
│   ├── scripted.py         a model that answers from a script
│   └── transport.py        how a provider reaches an endpoint
└── reporter.py           the project's report format, filled in
```

Two of these are not new roles, and the plan says so explicitly:

- **The evidence verifier is `core/evidence.py`.** The mechanism that turns a
  tool's output into a finding already existed. The agent routes its
  conclusions through it rather than inventing a second path to a finding.
- **The report builder is `reports/markdown.py` and `reports/json_report.py`.**
  The report format is the deliverable and it was already written. The agent's
  report is that format, filled in.

What is new is the state machine, the budgets, the retries and the breaker,
the resume, and the confirmation checkpoint.

## The state machine

A task is a value. It is written down, read back, and — after an interruption
— picked up.

`state.py` holds:

| What | Why it is in the state |
|---|---|
| `task_id`, `question` | what the task is |
| `status` | where it is: `pending`, `planning`, `running`, `awaiting_confirmation`, `completed`, `failed`, `budget_exhausted`, `interrupted` |
| `project_id`, `run_id` | which analysis the task is about — a project can have been analysed more than once, and a conclusion that does not name the run cannot be reproduced |
| `plan` | the bounded plan the task is working under |
| `turns` | the whole exchange: the model's turns and the tools' answers |
| `findings` | the records the task produced, with their ids and their citations |
| `tool_calls` | the log: every call, with how it ended and what it cost |
| `events` | what a user can watch happening |
| `limits`, `usage` | the budget and what has been spent |
| `sensitive_calls`, `approved_calls` | how much of the APK's source the task has read, and what a person has said yes to |
| `pending_approval` | the call that is waiting for a person |

The statuses are the milestones of a task, and `ALLOWED_TRANSITIONS` says
which one may follow which. A transition that is not in the table is refused:
a task cannot claim to have completed from a state that never finished, and a
resumed task cannot slip past the checkpoint it was waiting at.

The state is written as one JSON file per task, written whole and renamed into
place — a state that is half written is worse than no state, because it would
be read back as a task that stopped in the middle of a step.

### The budgets

Three, and they are checked **before** each piece of work rather than after:

- **tokens** — what the model said, counted by the provider;
- **iterations** — how many times the task went round the loop;
- **seconds** — how long the task ran.

A plan also bounds the number of **tool calls** a task may make.

A task that runs out of a budget stops, and says that it ran out of budget. It
does not say it found nothing: that is a different claim, and a much worse
one. The report's status line says *did not finish* for every status but
`completed`.

## The boundary between a lead and a finding

This is the part that matters, so it is worth being exact about.

**A tool's reading is a fact.** What `get_manifest` returned is recorded
through `EvidenceBuilder.add`, at the `verified` level, with the citation the
tool gave. The builder checks that citation against the analysis: a record
about a place that is not there is refused rather than written and believed.

**A model's conclusion is never a fact.** Whatever the model says, the
conclusion goes through `EvidenceBuilder.add_claim`, which cannot write a
verified record — it refuses the attempt. A conclusion the tools later confirm
is not that conclusion promoted; it is the tools' own record, recorded
separately.

**A conclusion that names nothing is not a lead.** A lead is a risk indicator
*and* it points at what makes it a lead. So a conclusion has to cite an
evidence id the task actually recorded, or a locator that resolves inside the
analysis. A conclusion that cites nothing, or that cites only things which are
not there, is recorded as **insufficient evidence**: not enough evidence
either way, and it needs a human.

So the report has three sections rather than one list:

| Section | What is in it | Who put it there |
|---|---|---|
| Established facts | what a tool read, with a citation that resolves | the tools, through `EvidenceBuilder.add` |
| Leads | what the model concluded from those facts | the model, through `EvidenceBuilder.add_claim` |
| Insufficient evidence | what could not be settled either way | the verifier |

The model's own opinion of how sure it is — the `confidence` field — is
carried in the record and is **not acted on**. The level of a record is
decided by what backs it, not by how sure the model sounded.

## The plan, and what bounds the agent

The plan is worked out **before the model is asked anything**, from the
question alone. It says which project the task is about, which tools it may
call, and how many calls it may make.

The model then chooses which of those tools to call and with what arguments.
It does not choose the set, and it does not choose the project.

That order is the point. A model handed the tools can ask for whatever it
likes; a model handed a *plan* can only choose within it. And because the
plan is worked out before a single byte of the APK has been read, nothing the
APK contains can widen it.

The executor enforces the plan before each call:

- a tool the plan does not allow is **refused without being made**;
- a call about a project other than the task's is **refused without being
  made**;
- arguments are checked against the tool's own signature, because they come
  from a model.

## The tools

The agent calls the MCP server's tools — the same ones an MCP client calls,
in process, with the same read-only boundary: no writes, no shell, no file
the index did not name.

Three things can go wrong when a tool is called, and each has its own answer.

**A timeout.** A call that takes longer than it is allowed to is abandoned
and recorded as a timeout. Python cannot stop a thread that is already
running, so the abandoned call is left to finish on its own; it is a read, it
writes nothing, and the log says it was abandoned. What matters is that the
task is not left waiting for it.

**A failure worth another attempt.** A timeout is tried again. A request the
server *refused* — an unknown project, a method that is not there — is not,
because it will be refused again and the retry costs the task its budget.

**A tool that keeps failing.** After a few failures the breaker for that tool
opens, and the calls after that are refused without being made. A task being
eaten by a broken workspace fails once instead of once per step. After a
cool-off the breaker lets one probe through, because a breaker that never
probes is a tool that is never tried again.

Every call is logged: the tool, the arguments, whether it worked, how long it
took, and — when it did not — which of the failures above it was.

## The APK is untrusted input

An analysed APK is a file nobody vouched for. A sentence inside it must not be
able to steer the agent, and an agent that obeys one has produced a finding
nobody can check.

Four mechanisms, and each of them is tested:

1. **The plan is worked out before anything is read.** The injected text
   cannot widen the set of tools or change the project.
2. **The observations are a channel of their own.** The request the model is
   given has the instructions and the question in one field and the tools'
   answers in another; the answer text never enters the instructions.
3. **A request whose instructions carry the APK's text is refused**
   (`assert_instructions_are_clean`) — the second lock on the same door.
4. **A conclusion that names nothing is insufficient evidence.** Even a
   hijacked model cannot produce a finding: the most it can produce is a
   claim the report marks as not established.

The test is a real one: the workspace carries an instruction that reads like
an instruction, and the provider in that test is *deliberately hijackable* —
it behaves differently depending on whether the injected text reached it as an
instruction or as data. Removing the mechanism makes the test go red; that is
demonstrated in the hand-over notes, and the report of it is in the commit
that carried the property.

## The providers

One interface, so the orchestration does not know which endpoint it is
talking to:

| Provider | What it is |
|---|---|
| `OpenAICompatibleProvider` | `POST {base_url}/chat/completions` — the shape every compatible endpoint speaks |
| `LocalModelProvider` | `POST {base_url}/api/chat` — a local model, with its own request shape and its own token counts |
| `ScriptedProvider` | a model that answers from a script: the same answer on every run and every machine, with no key and no network |

The providers are thin — a request, a response, an error — so what they need
tested is the *shape* they speak, not a live call. A test that needs an API
key is a test that does not run.

The scripted provider is in the package rather than in the test tree on
purpose: the fixed task suite, the benchmark harness and a reviewer running
the agent offline all need the same thing.

## The report

`reporter.py` fills in the project's own report format. The findings are the
project's own `Evidence` records, in the shape the analysis report uses, in
the same table, with the same words about what the levels mean — and a test
checks that the two reports say the same thing about the levels, so the
wording cannot drift apart.

The machine-readable form is a document of its own (`kind: "agent_report"`,
`schema_version: 1`) that carries the findings, the tool log, the budget and
the events. When the analysis it was about is available, the analysis report
is *nested* under `"analysis"` rather than merged in, so the contract the
analysis report has always had is untouched.

## What it will not do

- **It will not write.** The tools it calls are read-only, and it has no way
  to reach anything else.
- **It will not run a shell.** Nothing in the package starts a process; there
  is a test that reads the package's own source and says so.
- **It will not go outside the plan.** The set of tools and the project are
  fixed before the model is asked anything.
- **It will not report a conclusion it cannot back.** A conclusion with no
  citation, or with a citation that does not resolve, is recorded as
  insufficient evidence — and the report says so in those words.
- **It will not claim to have finished when it did not.** Every status but
  `completed` is rendered as *did not finish*, with the reason.

## What it is not yet

Being straight about the edges:

- **There is no command-line entry point yet.** The agent is a library: a
  caller builds an `Orchestrator` over a workspace and a provider. M2 did not
  touch `cli/`, so there is no `dexatlas agent "..."` yet.
- **The provider is the only thing that needs a network.** The orchestration
  itself never makes an outbound request; the model endpoint is the only
  place where an analysed APK's contents could leave the machine, and the
  contents do reach it — as data, in the observation channel.
- **The fixed task suite runs against a workspace built by hand**
  (`tests/agent_harness.py`). That is what makes it *fixed* — the same
  classes, the same strings and the same citations on every machine, with no
  backend installed and no third-party APK anywhere near it. Beside it, two
  of the tests run the same loop over a **real** analysis of
  `examples/demo-app`, and assert what holds whether or not the backends are
  installed. What is not measured is the whole suite over a real analysis:
  M3's benchmark is where that belongs.
- **The budgets are per task, and there is no global one.** A caller running
  many tasks has to keep the books itself.

## Running the tests

```bash
uv run --no-sync pytest tests/test_agent_task_suite.py       # the fixed suite
uv run --no-sync pytest tests/test_agent_untrusted_input.py  # the property
uv run --no-sync pytest tests/test_agent_failures.py         # the three failure modes
uv run --no-sync pytest tests/test_agent_executor.py         # timeout, retries, breaker
uv run --no-sync pytest tests/test_agent_verifier.py         # lead vs finding
uv run --no-sync pytest tests/test_agent_providers.py        # the endpoint shapes
uv run --no-sync pytest tests/test_agent_state.py            # the state machine
uv run --no-sync pytest tests/test_agent_report.py           # the report format
```

None of them needs a model key, a network, or an analysis backend.
