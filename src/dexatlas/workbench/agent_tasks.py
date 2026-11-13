"""The agent workspace: one question, one bounded task, one report.

A question about an analysed APK is not answered in the request that asks
it. The agent is a synchronous, CPU- and network-bound loop — it plans, it
calls tools, it asks a model, it checks its conclusions — and a browser
cannot hold a request open for that long. So the workbench runs it the way
the upload screen runs an analysis: the question is accepted, a task id is
returned at once, the loop runs in the background, and the browser polls
the task until it reports.

Three decisions are baked in here, and each one is the project's own rule
carried over:

* **The model is configured, never assumed.** The endpoint — its URL, its
  model name and, when it needs one, its key — arrives through environment
  variables, and the key is read only into the provider that puts it in a
  request header. It is never written to disk, never logged, and never
  placed in a response. With no configuration the task is refused with an
  explicit error: an agent that quietly substituted a scripted model would
  be answering with a rehearsal and calling it an answer.
* **The plan bounds the work.** The tool set, the step count and the
  budgets come from the agent's own :class:`~dexatlas.agent.Planner` and
  :class:`~dexatlas.agent.Budget`; the workbench adds no tool and no
  permission of its own.
* **The state is one file per task, written as the loop goes.** The
  orchestrator saves its :class:`~dexatlas.agent.TaskState` after every
  step, so a poll sees the plan, the tool log and the events as they
  happened — and an interrupted task can be picked up again.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from dexatlas.agent import Budget, Orchestrator, TaskState, TaskStatus, TaskStore
from dexatlas.agent.providers import (
    LocalModelProvider,
    ModelProvider,
    OpenAICompatibleProvider,
)
from dexatlas.agent.reporter import AgentReport, build_agent_json, render_agent_markdown
from dexatlas.agent.state import ApprovalRequest, Plan
from dexatlas.agent.tool_executor import McpToolClient, ToolExecutor
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import RequestError

#: Where the model endpoint's address comes from. Never a default: a model
#: the operator did not point at is not a model this machine should call.
AGENT_BASE_URL_ENV = "DEXATLAS_AGENT_BASE_URL"

#: The model name, as the endpoint knows it.
AGENT_MODEL_ENV = "DEXATLAS_AGENT_MODEL"

#: The key the endpoint asks for, if it asks. Read into a request header
#: and nowhere else.
AGENT_API_KEY_ENV = "DEXATLAS_AGENT_API_KEY"

#: Which provider shape the endpoint speaks: the OpenAI chat-completions
#: shape, or a local model's ``/api/chat``. The OpenAI shape is the default,
#: because it is the shape most hosted endpoints speak.
AGENT_PROVIDER_ENV = "DEXATLAS_AGENT_PROVIDER"
DEFAULT_PROVIDER_KIND = "openai-compatible"
PROVIDER_KINDS = ("openai-compatible", "local")

#: Optional budget overrides. The defaults are the agent's own.
AGENT_MAX_TOKENS_ENV = "DEXATLAS_AGENT_MAX_TOKENS"
AGENT_MAX_ITERATIONS_ENV = "DEXATLAS_AGENT_MAX_ITERATIONS"
AGENT_MAX_SECONDS_ENV = "DEXATLAS_AGENT_MAX_SECONDS"

#: How long one tool call may take before it is abandoned. The tools are
#: reads against a local workspace; a call that takes half a minute has
#: stopped answering.
TOOL_CALL_TIMEOUT_SECONDS = 30.0

#: The longest question the browser may ask. A question is a sentence, not
#: a document; the source it is about is read through the tools.
MAX_QUESTION_LENGTH = 2000

#: The statuses a poll can stop at: the task will not move again on its own.
TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.BUDGET_EXHAUSTED,
        TaskStatus.INTERRUPTED,
    }
)

#: The statuses a task may be moved to ``failed`` from, when something the
#: loop did not anticipate goes wrong in the background.
_FAILURE_REACHABLE: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.PENDING,
        TaskStatus.PLANNING,
        TaskStatus.RUNNING,
        TaskStatus.AWAITING_CONFIRMATION,
    }
)


# -- the configuration -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgentModelConfig:
    """One model endpoint, as the environment describes it."""

    provider_kind: str
    base_url: str
    model: str
    api_key: str | None = None


def read_agent_model_config() -> AgentModelConfig | None:
    """The configured model endpoint, or ``None`` when none is configured.

    A missing URL or model name means "not configured", and the caller says
    so plainly. A provider kind the project does not speak is a
    configuration *error*, and it is refused rather than quietly treated as
    the default.
    """
    base_url = os.environ.get(AGENT_BASE_URL_ENV, "").strip()
    model = os.environ.get(AGENT_MODEL_ENV, "").strip()
    if not base_url or not model:
        return None
    kind = os.environ.get(AGENT_PROVIDER_ENV, "").strip() or DEFAULT_PROVIDER_KIND
    if kind not in PROVIDER_KINDS:
        raise RequestError(
            f"{kind!r} is not a provider this workbench speaks; one of {', '.join(PROVIDER_KINDS)}",
            code="agent_provider_unknown",
            provider=kind,
        )
    api_key = os.environ.get(AGENT_API_KEY_ENV, "").strip() or None
    return AgentModelConfig(provider_kind=kind, base_url=base_url, model=model, api_key=api_key)


def provider_from_config(config: AgentModelConfig) -> LocalModelProvider | OpenAICompatibleProvider:
    """The provider one configuration names.

    The key lives in the provider and travels in the request headers only.
    The return type is the union of the two concrete providers rather than
    the :class:`~dexatlas.agent.providers.base.ModelProvider` protocol: both
    are frozen dataclasses whose ``name`` is read-only, and a protocol
    member declared settable would have mypy refuse the very objects that
    satisfy the protocol at runtime.
    """
    if config.provider_kind == "local":
        return LocalModelProvider(base_url=config.base_url, model=config.model)
    return OpenAICompatibleProvider(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )


def default_agent_provider_factory() -> LocalModelProvider | OpenAICompatibleProvider | None:
    """The provider from the environment, or ``None`` when unconfigured.

    This is what the workbench uses unless a test replaces the factory on
    ``app.state``; a test that needs a model hands the app a scripted one.
    """
    config = read_agent_model_config()
    if config is None:
        return None
    return provider_from_config(config)


def budget_from_env() -> Budget:
    """The task's budget: the agent's own defaults, overridable by env."""
    default = Budget()
    return Budget(
        max_tokens=_int_env(AGENT_MAX_TOKENS_ENV, default.max_tokens),
        max_iterations=_int_env(AGENT_MAX_ITERATIONS_ENV, default.max_iterations),
        max_seconds=_float_env(AGENT_MAX_SECONDS_ENV, default.max_seconds),
    )


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise RequestError(
            f"{name} must be a whole number, not {raw!r}", code="agent_env_invalid"
        ) from None


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise RequestError(
            f"{name} must be a number, not {raw!r}", code="agent_env_invalid"
        ) from None


# -- the background task -----------------------------------------------------


class PinnedTaskStore(TaskStore):
    """A store that keeps every state of one task under the id it was announced with.

    The orchestrator mints its own task id when it starts. The workbench has
    already told the browser which id to poll, so this store pins every
    state the loop writes to that id: the browser sees one task, from the
    pending acknowledgement through the plan and the tool calls to the
    report, under the name it was given at the start.
    """

    def __init__(self, directory: Any, task_id: str) -> None:
        super().__init__(directory)
        self._pinned_id = task_id

    def save(self, state: TaskState) -> None:
        state.task_id = self._pinned_id
        super().save(state)


class _WorkbenchApprovalGate:
    """Says yes to the sensitive reads the plan allows.

    The workbench is the user's own read-only window onto their own
    workspace, and the question that started this task *is* the
    authorisation to read it. The bound is not relaxed: the plan still
    caps how many sensitive reads happen (``max_sensitive_calls``), and the
    loop still refuses any tool the plan does not name. What this gate
    removes is only the pause to ask the same person who asked the
    question.
    """

    def approve(self, request: ApprovalRequest) -> bool:
        return True


def agent_task_store(analyzer: Analyzer) -> TaskStore:
    """Where this workspace's agent tasks are kept."""
    return TaskStore(analyzer.settings.workspace / "agent-tasks")


def builder_for_project(analyzer: Analyzer, project_id: str) -> Callable[[str], EvidenceBuilder]:
    """The builder factory the orchestrator writes its records through.

    The builder is made from what the *analysis* recorded — its tool
    versions, the hash of the APK, the workspace its results were published
    into, the dex files it read — because that is what a citation is
    resolved against. This is the same construction the real-analysis test
    harness uses, and it is what keeps an agent finding's citation pointing
    at the same places an analysis report's citations point.

    The project is the one the question was asked about, given here rather
    than read back from the task state: the loop writes its first records
    while it is still resolving the project, before the state carries an id.
    """

    def build(_task_project_id: str) -> EvidenceBuilder:
        project = analyzer.store.get_project(project_id)
        if project is None:
            raise RequestError(
                f"this workspace holds no project {project_id!r}",
                code="unknown_project",
                project_id=project_id,
            )
        return EvidenceBuilder(
            project_id=project.id,
            tool_versions=dict(project.tool_versions),
            apk_sha256=project.apk.sha256,
            workspace=analyzer.store.get_workspace(project_id),
            dex_files=list(project.apk.dex_files),
        )

    return build


def run_agent_task(
    analyzer: Analyzer,
    *,
    task_id: str,
    question: str,
    project_id: str,
    provider: ModelProvider,
    store: TaskStore,
    limits: Budget,
) -> None:
    """Run one agent task in the background.

    Every state the loop writes lands under ``task_id``, so the task the
    browser polls is the task that is running. A failure the loop itself
    does not anticipate is still written down: a task that vanishes would
    leave a browser polling forever, and a poll that never ends is worse
    than a task that says it failed.
    """
    client = McpToolClient(analyzer)
    orchestrator = Orchestrator(
        provider=provider,
        client=client,
        builder_for=builder_for_project(analyzer, project_id),
        store=PinnedTaskStore(store.directory, task_id),
        executor=ToolExecutor(client, timeout=TOOL_CALL_TIMEOUT_SECONDS),
        limits=limits,
        approvals=_WorkbenchApprovalGate(),
    )
    try:
        orchestrator.run(question, project_id=project_id)
    except Exception as exc:
        # The last resort, so a task never vanishes: a browser polling a
        # task that died without a word would never stop polling. A task
        # that already reached a status the state machine will not leave
        # (completed, budget exhausted) is left as it is.
        state = store.load(task_id)
        if state is None or state.status not in _FAILURE_REACHABLE:
            return
        state.error = f"the task stopped unexpectedly: {exc}"
        with contextlib.suppress(Exception):
            state.transition(TaskStatus.FAILED)
        state.note("failed", state.error)
        store.save(state)


# -- the views the browser reads ---------------------------------------------


class AgentConfigView(BaseModel):
    """Whether a model endpoint is configured, and which one — never the key."""

    configured: bool
    provider: str | None = None
    model: str | None = None


class AgentQuestion(BaseModel):
    """One question about one analysed APK."""

    question: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        description="What you want to know about this APK. The agent reads the answer through the analysis tools.",
    )


class AgentTaskAccepted(BaseModel):
    """A question the workbench took, and the task to poll for its answer."""

    task_id: str
    project_id: str
    status: str
    question: str


class AgentBudgetUsageView(BaseModel):
    tokens: int = 0
    iterations: int = 0
    seconds: float = 0.0


class AgentBudgetView(BaseModel):
    max_tokens: int
    max_iterations: int
    max_seconds: float


class AgentPlanStepView(BaseModel):
    tool: str
    purpose: str
    sensitive: bool = False


class AgentPlanView(BaseModel):
    """The plan the task is bounded by, worked out before any model was asked."""

    project_id: str
    question: str
    allowed_tools: list[str] = Field(default_factory=list)
    steps: list[AgentPlanStepView] = Field(default_factory=list)
    max_steps: int
    max_sensitive_calls: int
    limits: AgentBudgetView


class AgentToolCallView(BaseModel):
    """One tool call, as the tool log records it."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool
    attempt: int = 1
    error: str | None = None
    error_kind: str | None = None
    duration_seconds: float = 0.0
    started_at: str = ""


class AgentEventView(BaseModel):
    at: str
    kind: str
    message: str


class AgentTaskView(BaseModel):
    """One agent task, as a poll sees it: its plan, its tool log, its budget."""

    task_id: str
    question: str
    status: str
    project_id: str | None = None
    run_id: str | None = None
    plan: AgentPlanView | None = None
    tool_calls: list[AgentToolCallView] = Field(default_factory=list)
    events: list[AgentEventView] = Field(default_factory=list)
    usage: AgentBudgetUsageView = Field(default_factory=AgentBudgetUsageView)
    limits: AgentBudgetView = Field(
        default_factory=lambda: AgentBudgetView(
            max_tokens=Budget().max_tokens,
            max_iterations=Budget().max_iterations,
            max_seconds=Budget().max_seconds,
        )
    )
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""
    findings_count: int = 0


def plan_view(plan: Plan) -> AgentPlanView:
    """The plan as the browser reads it."""
    return AgentPlanView(
        project_id=plan.project_id,
        question=plan.question,
        allowed_tools=list(plan.allowed_tools),
        steps=[
            AgentPlanStepView(tool=step.tool, purpose=step.purpose, sensitive=step.sensitive)
            for step in plan.steps
        ],
        max_steps=plan.max_steps,
        max_sensitive_calls=plan.max_sensitive_calls,
        limits=AgentBudgetView(
            max_tokens=plan.limits.max_tokens,
            max_iterations=plan.limits.max_iterations,
            max_seconds=plan.limits.max_seconds,
        ),
    )


def task_view(state: TaskState) -> AgentTaskView:
    """One task state, as the browser polls it."""
    return AgentTaskView(
        task_id=state.task_id,
        question=state.question,
        status=state.status.value,
        project_id=state.project_id,
        run_id=state.run_id,
        plan=plan_view(state.plan) if state.plan is not None else None,
        tool_calls=[
            AgentToolCallView(
                tool=record.tool,
                arguments=dict(record.arguments),
                ok=record.ok,
                attempt=record.attempt,
                error=record.error,
                error_kind=record.error_kind,
                duration_seconds=record.duration_seconds,
                started_at=record.started_at,
            )
            for record in state.tool_calls
        ],
        events=[
            AgentEventView(at=event.at, kind=event.kind, message=event.message)
            for event in state.events
        ],
        usage=AgentBudgetUsageView(
            tokens=state.usage.tokens,
            iterations=state.usage.iterations,
            seconds=state.usage.seconds,
        ),
        limits=AgentBudgetView(
            max_tokens=state.limits.max_tokens,
            max_iterations=state.limits.max_iterations,
            max_seconds=state.limits.max_seconds,
        ),
        error=state.error,
        created_at=state.created_at,
        updated_at=state.updated_at,
        findings_count=len(state.findings),
    )


def agent_report_of(state: TaskState) -> AgentReport:
    """The report of one task, as the agent's own reporter renders it.

    This is the same construction ``Orchestrator.report`` makes; it is
    spelled out here so a completed task can be re-read from its saved
    state without keeping an orchestrator (and a provider) alive for every
    task anyone has ever asked about.
    """
    return AgentReport(
        task_id=state.task_id,
        question=state.question,
        status=state.status,
        project_id=state.project_id,
        run_id=state.run_id,
        findings=tuple(state.findings),
        tool_calls=tuple(state.tool_calls),
        usage=state.usage,
        limits=state.limits,
        events=tuple(state.events),
        limitations=tuple(event.message for event in state.events if event.kind == "limitation"),
        error=state.error,
    )


def agent_report_payload(state: TaskState) -> dict[str, Any]:
    """The agent's report as JSON, with the three sections spelled out.

    The document is ``build_agent_json``'s own; ``sections`` adds nothing
    new — it is the reporter's own established / leads / insufficient
    grouping, listed so the browser does not have to re-derive the rule
    for what counts as established.
    """
    report = agent_report_of(state)
    payload = build_agent_json(report)
    payload["sections"] = {
        "established": [item.model_dump(mode="json") for item in report.established],
        "leads": [item.model_dump(mode="json") for item in report.leads],
        "insufficient": [item.model_dump(mode="json") for item in report.insufficient],
    }
    return payload


def agent_report_markdown(state: TaskState) -> str:
    """The agent's report as Markdown, from the project's own renderer."""
    return render_agent_markdown(agent_report_of(state))
