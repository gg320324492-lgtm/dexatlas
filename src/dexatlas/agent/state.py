"""The task state machine.

What a task is, where it is, and what it may do next. The state is a value:
it is written down, it can be read back, and a task that was interrupted can
be picked up from it. That is the whole point of keeping it in one place —
the orchestrator's loop is a function of this state, and so is everything a
reader can be shown about a task.

The statuses are the milestones of a task, and the table below says which one
may follow which. A transition that is not in the table is refused, because a
state machine whose transitions are not checked is a set of fields.

The plan lives here too: a plan is part of what a task *is*, and a task that
is resumed needs the plan it was interrupted under.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from dexatlas.agent.providers.base import AssistantTurn, Observation, ToolCall
from dexatlas.agent.tool_executor import ToolCallRecord
from dexatlas.core.models import Evidence


class TaskStatus(StrEnum):
    """Where a task is."""

    PENDING = "pending"
    """Accepted, and nothing done with it yet."""

    PLANNING = "planning"
    """Working out which tool calls the question needs."""

    RUNNING = "running"
    """Asking the model, calling the tools, recording what came back."""

    AWAITING_CONFIRMATION = "awaiting_confirmation"
    """Stopped before a sensitive call, waiting for a person to say yes."""

    COMPLETED = "completed"
    """The model answered, and the answer was recorded and checked."""

    FAILED = "failed"
    """The task could not go on: the model failed, or the analysis did not."""

    BUDGET_EXHAUSTED = "budget_exhausted"
    """The task ran out of tokens, iterations or time.

    It did not finish, and it says so. A task that stopped because it ran out
    of budget is not a task that found nothing.
    """

    INTERRUPTED = "interrupted"
    """The task was cut short and can be picked up again."""


#: Which status may follow which.
#:
#: The table is the mechanism: a status that is not reachable is refused, so a
#: task cannot claim to have completed from a state that never finished, and a
#: resumed task cannot slip past the checkpoint it was waiting at.
ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.PLANNING, TaskStatus.FAILED, TaskStatus.INTERRUPTED}),
    TaskStatus.PLANNING: frozenset(
        {
            TaskStatus.RUNNING,
            TaskStatus.FAILED,
            TaskStatus.INTERRUPTED,
            TaskStatus.BUDGET_EXHAUSTED,
        }
    ),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.AWAITING_CONFIRMATION,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.INTERRUPTED,
            TaskStatus.BUDGET_EXHAUSTED,
        }
    ),
    TaskStatus.AWAITING_CONFIRMATION: frozenset(
        {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.INTERRUPTED}
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset({TaskStatus.RUNNING, TaskStatus.INTERRUPTED}),
    TaskStatus.INTERRUPTED: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED}),
    TaskStatus.BUDGET_EXHAUSTED: frozenset({TaskStatus.RUNNING}),
}


class InvalidTransition(Exception):
    """A status was asked for that does not follow from where the task is."""


class BudgetExceeded(Exception):
    """The task ran out of one of its budgets.

    The budget is a promise the task makes to its caller — this many tokens,
    this many turns, this long — and exceeding it stops the task rather than
    quietly spending more.
    """

    def __init__(self, budget: str, limit: int | float, spent: int | float) -> None:
        super().__init__(f"the {budget} budget is spent: {spent} of {limit} used")
        self.budget = budget
        self.limit = limit
        self.spent = spent


@dataclass(frozen=True, slots=True)
class Budget:
    """What one task may spend."""

    max_tokens: int = 20_000
    """How many tokens the model may use, in total."""

    max_iterations: int = 8
    """How many times the task may go round the loop."""

    max_seconds: float = 120.0
    """How long the task may run, in seconds."""


@dataclass(slots=True)
class BudgetUsage:
    """What one task has spent."""

    tokens: int = 0
    iterations: int = 0
    seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        """The usage as a reader can read it."""
        return {
            "tokens": self.tokens,
            "iterations": self.iterations,
            "seconds": round(self.seconds, 3),
        }


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One step of a plan: a tool, and what it is for."""

    tool: str
    purpose: str
    arguments: dict[str, Any] = field(default_factory=dict)
    sensitive: bool = False
    """Whether this step has to be approved by a person before it runs."""


@dataclass(frozen=True, slots=True)
class Plan:
    """A bounded series of tool calls, worked out before the model is asked.

    The plan is what keeps the agent bounded: it names the project the task is
    about, the tools the task may call, and how many calls it may make. The
    model chooses *which* of those tools to call and with what arguments; it
    does not choose the set.

    The plan is worked out before the model sees anything, and nothing the
    model says can widen it — which is also why a string inside the analysed
    APK cannot make the agent call a tool it was not planned to call.
    """

    project_id: str
    question: str
    steps: tuple[PlanStep, ...] = ()
    """The steps the task takes before the model is asked anything."""

    allowed_tools: tuple[str, ...] = ()
    """The tools the task may call. Nothing else is callable."""

    max_steps: int = 8
    """How many tool calls the task may make."""

    max_sensitive_calls: int = 1
    """How many sensitive calls may be made before a person is asked."""

    limits: Budget = field(default_factory=Budget)

    def allows(self, tool: str) -> bool:
        """Whether this plan permits a tool."""
        return tool in self.allowed_tools


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """A sensitive call, waiting for a person to say yes."""

    step: int
    tool: str
    arguments: dict[str, Any]
    reason: str
    asked_at: str
    call_id: str = ""
    """Which call is waiting. A task that is picked up again with a yes
    carries this id, so the call that was approved is the one that runs."""


@dataclass(frozen=True, slots=True)
class TaskEvent:
    """Something a user can watch happening."""

    at: str
    kind: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        """The event as a reader can read it."""
        return {"at": self.at, "kind": self.kind, "message": self.message}


@dataclass(slots=True)
class TaskState:
    """Everything one task is, at one moment.

    This is the thing that is written down when a task is interrupted and read
    back when it is resumed, so it holds the whole exchange: the question, the
    plan, every turn the model had and every answer the tools gave, the
    findings, the tool log, and what the budgets say.
    """

    task_id: str
    question: str
    status: TaskStatus = TaskStatus.PENDING
    project_id: str | None = None
    run_id: str | None = None
    """The analysis run the task is about.

    A project can have been analysed more than once, and a conclusion that
    does not name the run it came from cannot be reproduced.
    """

    plan: Plan | None = None
    turns: list[AssistantTurn | Observation] = field(default_factory=list)
    """The exchange so far: the model's turns and the tools' answers."""

    findings: list[Evidence] = field(default_factory=list)
    """The records the task produced, with their ids and their citations."""

    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    """The tool log: every call, with what it cost and how it ended."""

    events: list[TaskEvent] = field(default_factory=list)
    limits: Budget = field(default_factory=Budget)
    usage: BudgetUsage = field(default_factory=BudgetUsage)
    sensitive_calls: int = 0
    """How many sensitive calls the task has made.

    It is in the state rather than in the loop, because a task that is
    interrupted and picked up again has to remember that it has already read
    what it was allowed to read without asking.
    """

    pending_approval: ApprovalRequest | None = None
    approved_calls: list[str] = field(default_factory=list)
    """The calls a person has already said yes to.

    A task that is picked up again carries these, so the call that was
    approved is the one that runs rather than the one that is asked about
    again.
    """

    error: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def transition(self, new_status: TaskStatus) -> None:
        """Move to a status, if the state machine allows it."""
        if new_status is self.status:
            return
        allowed = ALLOWED_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidTransition(
                f"a task cannot go from {self.status.value} to {new_status.value}"
            )
        self.status = new_status
        self.updated_at = _now()

    def note(self, kind: str, message: str) -> TaskEvent:
        """Record something a user can watch happening."""
        event = TaskEvent(at=_now(), kind=kind, message=message)
        self.events.append(event)
        self.updated_at = event.at
        return event

    def charge(self, *, tokens: int = 0, iterations: int = 0, seconds: float = 0.0) -> None:
        """Record what the task has spent."""
        self.usage.tokens += tokens
        self.usage.iterations += iterations
        self.usage.seconds += seconds

    def check_budget(self, limits: Budget | None = None) -> None:
        """Refuse to go on when a budget is spent.

        The check happens before the work, not after: a task that overshoots
        its budget has already broken the promise the budget was.
        """
        limits = limits or self.limits
        if self.usage.tokens > limits.max_tokens:
            raise BudgetExceeded("token", limits.max_tokens, self.usage.tokens)
        if self.usage.iterations > limits.max_iterations:
            raise BudgetExceeded("iteration", limits.max_iterations, self.usage.iterations)
        if self.usage.seconds > limits.max_seconds:
            raise BudgetExceeded("time", limits.max_seconds, self.usage.seconds)

    @property
    def finished(self) -> bool:
        """Whether the task will not go on by itself."""
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.BUDGET_EXHAUSTED,
        }

    @property
    def resumable(self) -> bool:
        """Whether the task can be picked up again."""
        return self.status in {
            TaskStatus.AWAITING_CONFIRMATION,
            TaskStatus.FAILED,
            TaskStatus.INTERRUPTED,
            TaskStatus.BUDGET_EXHAUSTED,
        }

    def as_dict(self) -> dict[str, Any]:
        """The state as a reader — and as a file — can read it."""
        return {
            "task_id": self.task_id,
            "question": self.question,
            "status": self.status.value,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "plan": _plan_as_dict(self.plan),
            "turns": [_turn_as_dict(turn) for turn in self.turns],
            "findings": [item.model_dump(mode="json") for item in self.findings],
            "tool_calls": [record.as_dict() for record in self.tool_calls],
            "events": [event.as_dict() for event in self.events],
            "limits": {
                "max_tokens": self.limits.max_tokens,
                "max_iterations": self.limits.max_iterations,
                "max_seconds": self.limits.max_seconds,
            },
            "usage": self.usage.as_dict(),
            "sensitive_calls": self.sensitive_calls,
            "approved_calls": list(self.approved_calls),
            "pending_approval": (
                {
                    "step": self.pending_approval.step,
                    "tool": self.pending_approval.tool,
                    "arguments": self.pending_approval.arguments,
                    "reason": self.pending_approval.reason,
                    "asked_at": self.pending_approval.asked_at,
                    "call_id": self.pending_approval.call_id,
                }
                if self.pending_approval is not None
                else None
            ),
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> TaskState:
        """Read a state back from the document it was written as."""
        limits = document.get("limits") or {}
        usage = document.get("usage") or {}
        pending = document.get("pending_approval")
        state = cls(
            task_id=str(document["task_id"]),
            question=str(document["question"]),
            status=TaskStatus(str(document["status"])),
            project_id=document.get("project_id"),
            run_id=document.get("run_id"),
            plan=_plan_from_dict(document.get("plan")),
            turns=[_turn_from_dict(turn) for turn in document.get("turns") or []],
            findings=[Evidence.model_validate(item) for item in document.get("findings") or []],
            tool_calls=[
                ToolCallRecord.from_dict(item) for item in document.get("tool_calls") or []
            ],
            events=[
                TaskEvent(at=str(item["at"]), kind=str(item["kind"]), message=str(item["message"]))
                for item in document.get("events") or []
            ],
            limits=Budget(
                max_tokens=int(limits.get("max_tokens", Budget().max_tokens)),
                max_iterations=int(limits.get("max_iterations", Budget().max_iterations)),
                max_seconds=float(limits.get("max_seconds", Budget().max_seconds)),
            ),
            usage=BudgetUsage(
                tokens=int(usage.get("tokens", 0)),
                iterations=int(usage.get("iterations", 0)),
                seconds=float(usage.get("seconds", 0.0)),
            ),
            sensitive_calls=int(document.get("sensitive_calls", 0)),
            pending_approval=(
                ApprovalRequest(
                    step=int(pending["step"]),
                    tool=str(pending["tool"]),
                    arguments=dict(pending.get("arguments") or {}),
                    reason=str(pending.get("reason", "")),
                    asked_at=str(pending.get("asked_at", "")),
                    call_id=str(pending.get("call_id", "")),
                )
                if isinstance(pending, dict)
                else None
            ),
            approved_calls=[str(item) for item in document.get("approved_calls") or []],
            error=document.get("error"),
            created_at=str(document.get("created_at", "")),
            updated_at=str(document.get("updated_at", "")),
        )
        return state


def _now() -> str:
    """The current time, as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _plan_as_dict(plan: Plan | None) -> dict[str, Any] | None:
    """A plan, as a document."""
    if plan is None:
        return None
    return {
        "project_id": plan.project_id,
        "question": plan.question,
        "steps": [
            {
                "tool": step.tool,
                "purpose": step.purpose,
                "arguments": step.arguments,
                "sensitive": step.sensitive,
            }
            for step in plan.steps
        ],
        "allowed_tools": list(plan.allowed_tools),
        "max_steps": plan.max_steps,
        "max_sensitive_calls": plan.max_sensitive_calls,
        "limits": {
            "max_tokens": plan.limits.max_tokens,
            "max_iterations": plan.limits.max_iterations,
            "max_seconds": plan.limits.max_seconds,
        },
    }


def _plan_from_dict(document: dict[str, Any] | None) -> Plan | None:
    """A plan, read back from its document."""
    if not isinstance(document, dict):
        return None
    limits = document.get("limits") or {}
    return Plan(
        project_id=str(document.get("project_id", "")),
        question=str(document.get("question", "")),
        steps=tuple(
            PlanStep(
                tool=str(step.get("tool", "")),
                purpose=str(step.get("purpose", "")),
                arguments=dict(step.get("arguments") or {}),
                sensitive=bool(step.get("sensitive", False)),
            )
            for step in document.get("steps") or []
        ),
        allowed_tools=tuple(str(tool) for tool in document.get("allowed_tools") or []),
        max_steps=int(document.get("max_steps", 8)),
        max_sensitive_calls=int(document.get("max_sensitive_calls", 1)),
        limits=Budget(
            max_tokens=int(limits.get("max_tokens", Budget().max_tokens)),
            max_iterations=int(limits.get("max_iterations", Budget().max_iterations)),
            max_seconds=float(limits.get("max_seconds", Budget().max_seconds)),
        ),
    )


def _turn_as_dict(turn: AssistantTurn | Observation) -> dict[str, Any]:
    """One turn of the exchange, as a document."""
    if isinstance(turn, Observation):
        return {
            "kind": "observation",
            "tool": turn.tool,
            "call_id": turn.call_id,
            "content": turn.content,
            "ok": turn.ok,
            "error": turn.error,
        }
    return {
        "kind": "assistant",
        "content": turn.content,
        "tool_calls": [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in turn.tool_calls
        ],
    }


def _turn_from_dict(document: dict[str, Any]) -> AssistantTurn | Observation:
    """One turn of the exchange, read back from its document."""
    if document.get("kind") == "observation":
        return Observation(
            tool=str(document.get("tool", "")),
            call_id=str(document.get("call_id", "")),
            content=str(document.get("content", "")),
            ok=bool(document.get("ok", True)),
            error=document.get("error"),
        )
    return AssistantTurn(
        content=str(document.get("content", "")),
        tool_calls=tuple(
            ToolCall(
                id=str(call.get("id", "")),
                name=str(call.get("name", "")),
                arguments=dict(call.get("arguments") or {}),
            )
            for call in document.get("tool_calls") or []
        ),
    )


class TaskStore:
    """Where task states are kept, so a task can be picked up later.

    One JSON file per task, written whole. The write goes through a temporary
    file and a rename, because a state that is half written is worse than no
    state: it would be read back as a task that stopped in the middle of a
    step.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = Path(directory)

    @property
    def directory(self) -> Path:
        """Where the states are kept."""
        return self._directory

    def path_for(self, task_id: str) -> Path:
        """The file one task's state is in."""
        return self._directory / f"{task_id}.json"

    def save(self, state: TaskState) -> None:
        """Write a task's state down."""
        self._directory.mkdir(parents=True, exist_ok=True)
        target = self.path_for(state.task_id)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(state.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        temporary.replace(target)

    def load(self, task_id: str) -> TaskState | None:
        """Read a task's state back, or ``None`` when there is none."""
        path = self.path_for(task_id)
        if not path.is_file():
            return None
        return TaskState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_tasks(self) -> list[str]:
        """The ids of the tasks that are kept here."""
        if not self._directory.is_dir():
            return []
        return sorted(path.stem for path in self._directory.glob("*.json"))


__all__ = [
    "ALLOWED_TRANSITIONS",
    "ApprovalRequest",
    "Budget",
    "BudgetExceeded",
    "BudgetUsage",
    "InvalidTransition",
    "Plan",
    "PlanStep",
    "TaskEvent",
    "TaskState",
    "TaskStatus",
    "TaskStore",
]
