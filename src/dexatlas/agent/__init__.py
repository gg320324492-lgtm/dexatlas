"""The evidence-first agent.

One orchestrator that takes an analysis question about an APK, plans a bounded
series of tool calls, makes them against a DexAtlas workspace, checks that
its conclusions have evidence behind them, and reports what it found —
separated into what was established, what is a lead, and what is not
established.

The pieces:

* :mod:`~dexatlas.agent.orchestrator` — the loop;
* :mod:`~dexatlas.agent.planner` — a question into a bounded plan;
* :mod:`~dexatlas.agent.tool_executor` — the MCP tools, with a timeout, retries
  and a circuit breaker;
* :mod:`~dexatlas.agent.evidence_verifier` — the line between a lead and a
  finding;
* :mod:`~dexatlas.agent.state` — the task state machine, and where a task is
  kept so it can be picked up again;
* :mod:`~dexatlas.agent.providers` — the model endpoints;
* :mod:`~dexatlas.agent.reporter` — the project's own report format, filled in.

The rule the whole package exists to keep:

    **Evidence before inference. Correctness before autonomy.**
"""

from __future__ import annotations

from dexatlas.agent.evidence_verifier import (
    Conclusion,
    EvidenceVerifier,
    ParsedAnswer,
    parse_answer,
)
from dexatlas.agent.orchestrator import ApprovalGate, Orchestrator
from dexatlas.agent.planner import Intent, Planner
from dexatlas.agent.reporter import AgentReport, build_agent_json, render_agent_markdown
from dexatlas.agent.state import (
    Budget,
    BudgetExceeded,
    Plan,
    PlanStep,
    TaskState,
    TaskStatus,
    TaskStore,
)
from dexatlas.agent.tool_executor import (
    McpToolClient,
    ToolCallError,
    ToolCallRecord,
    ToolExecutor,
    ToolOutcome,
)

__all__ = [
    "AgentReport",
    "ApprovalGate",
    "Budget",
    "BudgetExceeded",
    "Conclusion",
    "EvidenceVerifier",
    "Intent",
    "McpToolClient",
    "Orchestrator",
    "ParsedAnswer",
    "Plan",
    "PlanStep",
    "Planner",
    "TaskState",
    "TaskStatus",
    "TaskStore",
    "ToolCallError",
    "ToolCallRecord",
    "ToolExecutor",
    "ToolOutcome",
    "build_agent_json",
    "parse_answer",
    "render_agent_markdown",
]
