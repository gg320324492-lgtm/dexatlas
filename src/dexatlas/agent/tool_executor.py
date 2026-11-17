"""Calling the tools, and surviving their failures.

The tools are the MCP server's: read-only, bounded, and the only way the
agent learns anything about the APK. This module is the boundary between the
model and those tools, and it holds the three mechanisms that keep the agent
inside its bounds.

**The plan is the bound.** A call to a tool the plan does not allow is
refused without being made, and so is a call that names a project other than
the one the task is about. The plan is worked out before the model is asked
anything, and nothing the model says can widen it — which is why a string
inside the analysed APK cannot make the agent go and read another APK.

**The breaker is the bound on a broken tool.** A tool that keeps failing is
not called again and again: after a few failures the breaker opens, and the
calls after that are refused without being made. A task that is being eaten
by a broken workspace fails once instead of once per step.

**The timeout is the bound on a slow tool.** A call that takes longer than it
is allowed to is abandoned and recorded as a timeout. Python cannot stop a
thread that is already running, so the abandoned call is left to finish on its
own; it is a read, it writes nothing, and the fact that it was abandoned is
in the log.

A failure here is never an exception that reaches the caller: it is a value
in the log, and the task carries on with what it has.
"""

from __future__ import annotations

import inspect
import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import Any, Protocol, Union, get_args, get_origin, get_type_hints, runtime_checkable

from dexatlas.agent.providers.base import ToolSpec
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import RequestError
from dexatlas.mcp.tools import evidence as evidence_tools
from dexatlas.mcp.tools import projects as project_tools
from dexatlas.mcp.tools import references as reference_tools
from dexatlas.mcp.tools import resources as resource_tools
from dexatlas.mcp.tools import symbols as symbol_tools

#: How a call ended badly.
#:
#: The kind is what a reader branches on: a timeout and a broken tool are
#: different facts, and a caller that cannot tell them apart retries the wrong
#: thing.
ERROR_TIMEOUT = "timeout"
ERROR_TOOL = "tool_error"
ERROR_INVALID_ARGUMENTS = "invalid_arguments"
ERROR_NOT_ALLOWED = "not_allowed"
ERROR_OUT_OF_SCOPE = "out_of_scope"
ERROR_CIRCUIT_OPEN = "circuit_open"
ERROR_UNKNOWN_TOOL = "unknown_tool"

#: The kinds worth trying again.
#:
#: A tool that timed out may answer next time; a request the server refused
#: will be refused again, and trying costs the task its budget.
TRANSIENT_ERRORS = frozenset({ERROR_TIMEOUT})


class ToolCallError(Exception):
    """A call that did not produce an answer."""

    def __init__(self, message: str, *, kind: str = ERROR_TOOL, transient: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.transient = transient
        """Whether trying again could plausibly work."""


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """One call, as it happened."""

    tool: str
    arguments: dict[str, Any]
    ok: bool
    attempt: int = 1
    error: str | None = None
    error_kind: str | None = None
    duration_seconds: float = 0.0
    started_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        """The record as a reader can read it."""
        return {
            "tool": self.tool,
            "arguments": self.arguments,
            "ok": self.ok,
            "attempt": self.attempt,
            "error": self.error,
            "error_kind": self.error_kind,
            "duration_seconds": round(self.duration_seconds, 4),
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> ToolCallRecord:
        """Read a record back from its document."""
        return cls(
            tool=str(document.get("tool", "")),
            arguments=dict(document.get("arguments") or {}),
            ok=bool(document.get("ok", False)),
            attempt=int(document.get("attempt", 1)),
            error=document.get("error"),
            error_kind=document.get("error_kind"),
            duration_seconds=float(document.get("duration_seconds", 0.0)),
            started_at=str(document.get("started_at", "")),
        )


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    """What one call produced: the answer, or the reason there is none."""

    record: ToolCallRecord
    payload: Any = None
    """The tool's own answer, as the tool returned it."""

    content: str = ""
    """The answer as text the model can read."""

    @property
    def ok(self) -> bool:
        """Whether the call produced an answer."""
        return self.record.ok


@runtime_checkable
class ToolClient(Protocol):
    """What the executor needs from the tools."""

    def call(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Call one tool and hand back what it returned."""

    def describe(self, tool: str) -> ToolSpec:
        """Describe one tool, for the model."""

    def signature(self, tool: str) -> inspect.Signature:
        """The signature of one tool, so the arguments can be checked."""


#: What each tool is for, as the model is told.
#:
#: The MCP server describes its tools for an MCP client; these are the same
#: tools described for a model that has to choose between them.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_projects": (
        "List the APKs analysed in this workspace, newest first, with their id, "
        "hash, status and counts. Use it when you do not know which project to "
        "ask about."
    ),
    "get_project_status": (
        "Read one project's status and how complete its analysis is: the backends "
        "that did not take part, whether a limit stopped the analysis short, and "
        "the runs it has had. Read it before trusting any count."
    ),
    "get_manifest": (
        "Read the AndroidManifest.xml of an analysed APK: its package, versions, "
        "SDK levels, the permissions it asks for and the components it declares."
    ),
    "search_symbols": (
        "Search the index of an analysed APK for a phrase, across its classes, "
        "methods, fields and strings. It searches the index, not the source. "
        "For a string constant, read the first page with limit=20 before paging "
        "further: string hits share the constant pool, so the first small page "
        "shows the shape of the answer before a wider read spends the budget."
    ),
    "get_class_source": (
        "Read one class's source — Java when the decompiler produced it, Smali "
        "otherwise — with the provenance that says which backend produced it."
    ),
    "get_method_source": (
        "Read one method's source, with its provenance. Pass descriptor to pick "
        "one of several methods that share a name; a name that matches more than "
        "one method is answered with the candidates instead of one of them."
    ),
    "find_callers": (
        "Find the calls into a method: each call site, with the caller, the DEX "
        "file and the instruction offset, and the call-site and call-edge counts "
        "kept apart."
    ),
    "find_callees": (
        "Find the calls out of a method: what it calls, with the call-site and "
        "call-edge counts kept apart."
    ),
    "find_resource_declarations": (
        "Find where a resource string is declared: by its name ('app_name') or by "
        "its value ('Demo'), each declaration with the file that declares it — "
        "res/values/strings.xml and its siblings — and the provenance of the read. "
        "Pass name, value, or both."
    ),
    "get_evidence": (
        "Read one evidence record by its id, with the locators it was read from. "
        "The locators are the places a reader can go to check the record."
    ),
    "resolve_locator": (
        "Resolve a provenance locator into the source it names, and say why it did "
        "not resolve when it did not."
    ),
}

#: The tools whose answers pull bulk text out of the APK.
#:
#: These are the ones a person is asked about before the agent reads them:
#: they are where the untrusted text is largest, and where a hijacked model
#: would do the most damage.
SENSITIVE_TOOLS = frozenset({"get_class_source", "get_method_source"})


class McpToolClient:
    """The MCP server's tools, called in process.

    The tools are the server's own functions, so the agent and an MCP client
    read the same workspace in the same way. The arguments are checked against
    the tool's own signature before the call, because the arguments come from
    a model: an argument the tool does not have is a request nobody can
    answer, and it is refused here rather than raising inside the tool.
    """

    def __init__(self, analyzer: Analyzer) -> None:
        self._analyzer = analyzer
        # The analyzer is bound with ``partial`` rather than wrapped in a
        # lambda, because the signature of the handler is what says what the
        # tool takes. A lambda would hide it behind ``**kwargs``, and the
        # arguments — which come from a model — would then be unchecked.
        self._handlers: dict[str, Callable[..., Any]] = {
            "list_projects": partial(project_tools.list_projects, analyzer),
            "get_project_status": partial(project_tools.project_status, analyzer),
            "get_manifest": partial(project_tools.manifest, analyzer),
            "search_symbols": partial(symbol_tools.search_symbols, analyzer),
            "get_class_source": partial(symbol_tools.class_source, analyzer),
            "get_method_source": partial(symbol_tools.method_source, analyzer),
            "find_callers": partial(reference_tools.find_callers, analyzer),
            "find_callees": partial(reference_tools.find_callees, analyzer),
            "find_resource_declarations": partial(
                resource_tools.find_resource_declarations, analyzer
            ),
            "get_evidence": partial(evidence_tools.get_evidence, analyzer),
            "resolve_locator": partial(evidence_tools.resolve_locator, analyzer),
        }

    @property
    def tools(self) -> tuple[str, ...]:
        """The names of the tools this client can call."""
        return tuple(sorted(self._handlers))

    def handler(self, tool: str) -> Callable[..., Any]:
        """The function behind one tool."""
        try:
            return self._handlers[tool]
        except KeyError as exc:
            raise ToolCallError(
                f"there is no tool called {tool!r}", kind=ERROR_UNKNOWN_TOOL
            ) from exc

    def signature(self, tool: str) -> inspect.Signature:
        """The signature of one tool, with its types resolved.

        The tools are written with ``from __future__ import annotations``,
        so their annotations are *text* at runtime — ``"str"``, not ``str``.
        The arguments are checked against those types, so the text is
        resolved into the types it names. A check against the spelling would
        pass everything, and a check that passes everything is not a check.
        """
        handler = self.handler(tool)
        signature = inspect.signature(handler)
        function = getattr(handler, "func", handler)
        try:
            hints = get_type_hints(function)
        except Exception:
            return signature
        return signature.replace(
            parameters=[
                parameter.replace(annotation=hints.get(name, parameter.annotation))
                for name, parameter in signature.parameters.items()
            ]
        )

    def call(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Call one tool and hand back what it returned."""
        handler = self.handler(tool)
        try:
            return handler(**dict(arguments))
        except RequestError as exc:
            raise ToolCallError(exc.message, kind=ERROR_TOOL, transient=False) from exc
        except TypeError as exc:
            raise ToolCallError(
                f"the tool {tool!r} refused the arguments: {exc}",
                kind=ERROR_INVALID_ARGUMENTS,
            ) from exc

    def describe(self, tool: str) -> ToolSpec:
        """Describe one tool, for the model."""
        signature = self.signature(tool)
        properties: dict[str, object] = {}
        required: list[str] = []
        for name, parameter in signature.parameters.items():
            properties[name] = _describe_parameter(parameter)
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
        return ToolSpec(
            name=tool,
            description=TOOL_DESCRIPTIONS.get(tool, f"The {tool} tool."),
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )


def _describe_parameter(parameter: inspect.Parameter) -> dict[str, object]:
    """How one argument is described to the model."""
    annotation = parameter.annotation
    kind = "string"
    if annotation is int:
        kind = "integer"
    elif annotation is bool:
        kind = "boolean"
    described: dict[str, object] = {"type": kind}
    if parameter.default is not inspect.Parameter.empty:
        described["default"] = parameter.default
    return described


@dataclass
class _Breaker:
    """The state of one tool's breaker."""

    failures: int = 0
    opened_at: float | None = None
    probing: bool = False
    """Whether the one probe a half-open breaker allows has been taken."""

    @property
    def is_open(self) -> bool:
        """Whether the breaker is open."""
        return self.opened_at is not None


class ToolExecutor:
    """Calls the tools, with a timeout, retries and a breaker.

    The executor is what the orchestrator calls. It decides whether a call is
    allowed at all, it makes the call, and it records what happened — every
    time, including the times it did not happen.
    """

    def __init__(
        self,
        client: ToolClient,
        *,
        timeout: float = 10.0,
        max_attempts: int = 3,
        failure_threshold: int = 3,
        reset_after: float = 30.0,
        backoff: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._failure_threshold = max(1, failure_threshold)
        self._reset_after = reset_after
        self._backoff = backoff
        self._clock = clock
        self._sleep = sleeper
        self._breakers: dict[str, _Breaker] = {}

    def execute(
        self,
        tool: str,
        arguments: Mapping[str, Any],
        *,
        allowed_tools: frozenset[str] | None = None,
        project_id: str | None = None,
        timeout: float | None = None,
    ) -> ToolOutcome:
        """Call one tool, and report what came of it.

        The refusals come first, and they cost nothing: a call that is not
        allowed is not made, so a plan that says "read this project" cannot be
        talked into reading another one.
        """
        arguments = dict(arguments)
        started = datetime.now(UTC).isoformat()
        began = self._clock()

        refusal = self._refuse(tool, arguments, allowed_tools=allowed_tools, project_id=project_id)
        if refusal is not None:
            return ToolOutcome(
                record=ToolCallRecord(
                    tool=tool,
                    arguments=arguments,
                    ok=False,
                    error=refusal.message,
                    error_kind=refusal.kind,
                    duration_seconds=0.0,
                    started_at=started,
                ),
                content=_error_content(tool, refusal.kind, refusal.message),
            )

        breaker = self._breakers.setdefault(tool, _Breaker())
        if self._breaker_is_open(tool, breaker):
            message = (
                f"the tool {tool!r} has failed {breaker.failures} times in a row and is "
                "not being called again for now"
            )
            return ToolOutcome(
                record=ToolCallRecord(
                    tool=tool,
                    arguments=arguments,
                    ok=False,
                    error=message,
                    error_kind=ERROR_CIRCUIT_OPEN,
                    duration_seconds=0.0,
                    started_at=started,
                ),
                content=_error_content(tool, ERROR_CIRCUIT_OPEN, message),
            )

        last_error: ToolCallError | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                payload = self._call_with_timeout(
                    tool, arguments, timeout if timeout is not None else self._timeout
                )
            except ToolCallError as exc:
                last_error = exc
                self._record_failure(tool, breaker)
                if not exc.transient or attempt >= self._max_attempts:
                    break
                if self._backoff:
                    self._sleep(self._backoff * attempt)
                continue

            self._record_success(tool, breaker)
            duration = self._clock() - began
            record = ToolCallRecord(
                tool=tool,
                arguments=arguments,
                ok=True,
                attempt=attempt,
                duration_seconds=duration,
                started_at=started,
            )
            return ToolOutcome(
                record=record, payload=payload, content=_success_content(tool, payload)
            )

        assert last_error is not None
        duration = self._clock() - began
        record = ToolCallRecord(
            tool=tool,
            arguments=arguments,
            ok=False,
            attempt=self._max_attempts,
            error=last_error.message,
            error_kind=last_error.kind,
            duration_seconds=duration,
            started_at=started,
        )
        return ToolOutcome(
            record=record,
            content=_error_content(tool, last_error.kind, last_error.message),
        )

    def _refuse(
        self,
        tool: str,
        arguments: Mapping[str, Any],
        *,
        allowed_tools: frozenset[str] | None,
        project_id: str | None,
    ) -> ToolCallError | None:
        """Whether this call may be made at all."""
        if allowed_tools is not None and tool not in allowed_tools:
            return ToolCallError(
                f"the tool {tool!r} is not part of this task's plan", kind=ERROR_NOT_ALLOWED
            )
        if project_id is not None:
            named = arguments.get("project_id")
            if isinstance(named, str) and named != project_id:
                return ToolCallError(
                    f"the tool {tool!r} was asked about project {named!r}, which is not the "
                    f"project this task is about ({project_id!r})",
                    kind=ERROR_OUT_OF_SCOPE,
                )
        try:
            signature = self._client_signature(tool)
        except ToolCallError as exc:
            return exc
        return _check_arguments(signature, tool, arguments)

    def _client_signature(self, tool: str) -> inspect.Signature:
        """The signature of the tool, from whatever client this executor holds."""
        return self._client.signature(tool)

    def _call_with_timeout(self, tool: str, arguments: Mapping[str, Any], timeout: float) -> Any:
        """Make the call, and give up on it if it takes too long.

        The call runs on a thread that is abandoned when the time is up.
        Python has no way to stop a thread that is already running, so the
        abandoned call finishes on its own; it is a read, it writes nothing,
        and the log says that it was abandoned.
        """
        if timeout <= 0:
            return self._client.call(tool, arguments)

        finished = threading.Event()
        answer: list[Any] = []
        failure: list[BaseException] = []

        def run() -> None:
            try:
                answer.append(self._client.call(tool, arguments))
            except BaseException as exc:
                failure.append(exc)
            finally:
                finished.set()

        worker = threading.Thread(target=run, daemon=True, name=f"dexatlas-tool-{tool}")
        worker.start()
        if not finished.wait(timeout):
            raise ToolCallError(
                f"the tool {tool!r} did not answer within {timeout:g} seconds",
                kind=ERROR_TIMEOUT,
                transient=True,
            )
        if failure:
            error = failure[0]
            if isinstance(error, ToolCallError):
                raise error
            if isinstance(error, RequestError):
                raise ToolCallError(error.message, kind=ERROR_TOOL) from error
            raise ToolCallError(
                f"the tool {tool!r} failed: {type(error).__name__}: {error}",
                kind=ERROR_TOOL,
            ) from error
        return answer[0]

    def _breaker_is_open(self, tool: str, breaker: _Breaker) -> bool:
        """Whether the breaker for this tool refuses the call.

        An open breaker lets one probe through once the cool-off has passed.
        The probe is what tells the agent whether the tool has recovered; a
        breaker that never probes is a tool that is never tried again.
        """
        if not breaker.is_open:
            return False
        assert breaker.opened_at is not None
        if self._clock() - breaker.opened_at < self._reset_after:
            return True
        if breaker.probing:
            return True
        breaker.probing = True
        return False

    def _record_failure(self, tool: str, breaker: _Breaker) -> None:
        """A failure: the breaker counts it, and opens when there are enough."""
        breaker.failures += 1
        if breaker.probing:
            # The probe failed: the tool is still broken, and the cool-off
            # starts again from now.
            breaker.opened_at = self._clock()
            breaker.probing = False
            return
        if breaker.failures >= self._failure_threshold:
            breaker.opened_at = self._clock()

    def _record_success(self, tool: str, breaker: _Breaker) -> None:
        """A success: the breaker closes again."""
        breaker.failures = 0
        breaker.opened_at = None
        breaker.probing = False


def _check_arguments(
    signature: inspect.Signature, tool: str, arguments: Mapping[str, Any]
) -> ToolCallError | None:
    """Whether the arguments are ones the tool can be given.

    The arguments come from a model, so they are checked rather than trusted:
    an argument the tool does not have, a missing one it needs, or one of the
    wrong type is refused here, where the refusal can be reported as a
    refusal.
    """
    if not signature.parameters:
        return None
    accepted = signature.parameters
    for name in arguments:
        if name not in accepted:
            return ToolCallError(
                f"the tool {tool!r} has no argument called {name!r}", kind=ERROR_INVALID_ARGUMENTS
            )
    for name, parameter in accepted.items():
        if name not in arguments:
            if parameter.default is inspect.Parameter.empty:
                return ToolCallError(
                    f"the tool {tool!r} needs the argument {name!r}", kind=ERROR_INVALID_ARGUMENTS
                )
            continue
        value = arguments[name]
        if not _type_is_right(value, parameter.annotation):
            return ToolCallError(
                f"the argument {name!r} of the tool {tool!r} has to be "
                f"{_type_name(parameter.annotation)}, not {type(value).__name__}",
                kind=ERROR_INVALID_ARGUMENTS,
            )
    return None


def _type_is_right(value: Any, annotation: Any) -> bool:
    """Whether a value fits the type the tool declared.

    The annotation may be a type or the *spelling* of one — a tool written
    with ``from __future__ import annotations`` declares ``"str"`` rather
    than ``str`` at runtime — so both are understood. A type this project
    does not declare is accepted: the check is there to catch a model that
    got the shape of an argument wrong, not to re-type-check the codebase.
    """
    if annotation is inspect.Parameter.empty or annotation is Any:
        return True
    if isinstance(annotation, str):
        return _spelling_is_right(value, annotation)
    if annotation is bool:
        return isinstance(value, bool)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is str:
        return isinstance(value, str)
    if annotation is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    origin = get_origin(annotation)
    if origin is Union:
        return any(_type_is_right(value, part) for part in get_args(annotation))
    return True


def _spelling_is_right(value: Any, spelling: str) -> bool:
    """Whether a value fits a type that is written as text."""
    text = spelling.replace(" ", "")
    if text == "None":
        return value is None
    if text in {"str", "int", "bool", "float"}:
        return _type_is_right(value, {"str": str, "int": int, "bool": bool, "float": float}[text])
    if text.startswith("Optional[") and text.endswith("]"):
        return value is None or _spelling_is_right(value, text[len("Optional[") : -1])
    if "|" in text:
        return any(_spelling_is_right(value, part) for part in text.split("|"))
    return True


def _type_name(annotation: Any) -> str:
    """How a type is named in a message to a reader."""
    return getattr(annotation, "__name__", str(annotation))


#: What a repeated data notice becomes in the agent's transcript.
#:
#: The first notice in a tool answer keeps its full words; the rest are this
#: marker, which says the notice was already given. The MCP-facing response
#: is untouched: this shapes only what this agent reads, and the loop
#: re-sends it on every turn, so the fold is what keeps a page of wrapped
#: texts from billing its boilerplate again on every round.
FOLDED_NOTICE = "(data notice as above)"


def _success_content(tool: str, payload: Any) -> str:
    """The answer as text the model can read.

    The notices the answer's wrapped texts carry are folded here: the first
    one keeps its full words, and every later one becomes a short marker.
    The MCP response the caller gets is untouched — this shapes only what
    this agent reads, and the loop re-sends it on every turn, so the fold is
    what keeps a page of wrapped texts from billing its boilerplate again
    on every round.
    """
    return clip_tool_content(
        _content(tool, {"ok": True, "data": _fold_repeated_notices(_as_jsonable(payload))})
    )


def _fold_repeated_notices(node: Any) -> Any:
    """Fold repeated ``notice`` fields to one full text and short markers.

    Every piece of text read out of an APK travels with a notice that says
    what it is. The notice is worth reading once; on a page of symbols it is
    repeated for every hit, twice over, and the repeats are the largest
    single part of a big answer. The first notice in the document is kept in
    full — a reader cannot miss what the text is — and every later
    occurrence of the same notice becomes a marker that points back at it.
    A notice that says something different is kept in full: the fold is for
    repetition, not for notice-wearing in general.

    The fold follows the document's own order — lists in list order, fields
    in field order — so the kept notice is the first wrapped text the model
    would have read.
    """
    state: dict[str, set[str]] = {"seen": set()}
    return _fold_node(node, state)


def _fold_node(node: Any, state: dict[str, set[str]]) -> Any:
    if isinstance(node, dict):
        folded: dict[str, Any] = {}
        # The document is serialized with sorted keys, so the fold walks the
        # keys in the same order: the notice the model reads first is the
        # one kept in full.
        for key in sorted(node):
            value = node[key]
            if key == "notice" and isinstance(value, str):
                if value in state["seen"]:
                    folded[key] = FOLDED_NOTICE
                else:
                    state["seen"].add(value)
                    folded[key] = value
            else:
                folded[key] = _fold_node(value, state)
        return folded
    if isinstance(node, list):
        return [_fold_node(item, state) for item in node]
    return node


def _error_content(tool: str, kind: str, message: str) -> str:
    """The reason there is no answer, as text the model can read."""
    return _content(tool, {"ok": False, "error": {"kind": kind, "message": message}})


def _content(tool: str, document: dict[str, Any]) -> str:
    """One tool's answer, as one JSON document."""
    return json.dumps({"tool": tool, **document}, sort_keys=True, default=str)


def _as_jsonable(payload: Any) -> Any:
    """The tool's answer as something JSON can hold."""
    dump = getattr(payload, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return payload


#: The most transcript an answer's *repeated row scaffolding* may cost.
#:
#: A page of symbols is the answer that repeats itself: every row carries
#: the keys, the ``truncated`` and ``bytes`` bookkeeping and the folded
#: notice that says the text is data, and twenty of those rows spend more
#: than three thousand characters saying the same shape. The transcript
#: budget gives each answer a page allowance on top of the per-field text
#: limit, and the row count is cut to fit inside it — with the cut stated,
#: as every cut here is, and ``total`` and ``offset`` kept so a reader can
#: page to what was dropped.
MAX_CONTENT_CHARS = 12_000


#: The longest text a single string field may put in the transcript.
#:
#: A whole-class source read is the biggest thing a tool hands back, and the
#: narrow M6 verification showed what it costs: three tasks spent their whole
#: 24,000-token task budget on the prompt alone — the history re-sent on every
#: iteration carried the same whole-class text again and again — and died
#: before the model could answer. The evidence a conclusion is checked
#: against is recorded from the *payload*, before this clip, so the clip
#: costs the transcript nothing it cannot re-read and the evidence chain
#: nothing at all.
MAX_FIELD_TEXT = 4_000

#: The announcement that replaces the dropped middle of a clipped text.
_CLIP_NOTICE = (
    "\n… [clipped {dropped} characters to keep the transcript readable; "
    "the full text is recorded as evidence]"
)

#: The announcement that replaces the rows a page dropped.
_ROW_NOTICE = (
    "… [{dropped} of {total} rows clipped to keep the transcript readable; "
    "the full page is recorded as evidence — page again with offset={kept}]"
)


def clip_tool_content(content: str, *, max_field_text: int = MAX_FIELD_TEXT) -> str:
    """Clip a tool answer to what a transcript can afford to re-send.

    The transcript is re-sent on every iteration, so a tool answer that
    carries a whole class's source — or a page of rows whose scaffolding
    outweighs its facts — costs its own size again on every turn after it.
    Two cuts, both announced where they happen and both taken after the
    evidence was recorded from the untouched payload:

    * any string field longer than :data:`MAX_FIELD_TEXT` keeps its head —
      where a class's declarations and constants live — and says what was
      dropped;
    * a list of rows longer than :data:`MAX_CONTENT_CHARS` allows keeps the
      first rows and says how many were dropped, with the offset that pages
      to them. ``total`` and ``offset`` stay, so the count is not lost.

    A document that fits is returned unchanged: the clip is for the answers
    that are too big, not for the answers that are already right.
    """
    if len(content) <= max_field_text:
        return content
    try:
        document = json.loads(content)
    except (TypeError, ValueError):
        return content
    clipped = _clip_value(document, max_field_text)
    clipped = _clip_rows(clipped)
    if clipped is document:
        return content
    return json.dumps(clipped, sort_keys=True, default=str)


def _clip_value(value: Any, limit: int) -> Any:
    """Clip one JSON value; return the original object when nothing changed."""
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        head = value[:limit]
        return head + _CLIP_NOTICE.format(dropped=len(value) - limit)
    if isinstance(value, list):
        clipped_items = [_clip_value(item, limit) for item in value]
        if any(new is not old for new, old in zip(clipped_items, value, strict=False)):
            return clipped_items
        return value
    if isinstance(value, dict):
        clipped_fields = {key: _clip_value(item, limit) for key, item in value.items()}
        if clipped_fields != value:
            return clipped_fields
        return value
    return value


def _clip_rows(document: Any, *, max_chars: int = MAX_CONTENT_CHARS) -> Any:
    """Cut a page of rows to the transcript allowance, saying what was dropped.

    A page that fits is returned unchanged. One that does not keeps its
    first rows — the ones a reader reads first — and the row that names the
    cut carries the offset that pages to what was dropped. ``total`` and
    ``offset`` are never touched: a count that survives the clip is the
    count the question asked about.
    """
    if not isinstance(document, dict):
        return document
    data = document.get("data")
    if not isinstance(data, dict):
        return document
    rows_key = next(
        (key for key in ("symbols", "declarations") if isinstance(data.get(key), list)), None
    )
    if rows_key is None:
        return document
    rows = data[rows_key]
    total = data.get("total", len(rows))
    offset = data.get("offset", 0)
    kept: list[Any] = []
    kept_chars = len(json.dumps({k: v for k, v in document.items() if k != "data"}, default=str))
    changed = False
    for index, row in enumerate(rows):
        row_chars = len(json.dumps(row, default=str))
        if kept and kept_chars + row_chars > max_chars:
            notice = _ROW_NOTICE.format(dropped=len(rows) - index, total=total, kept=offset + index)
            kept.append({"row_clip": notice})
            changed = True
            break
        kept.append(row)
        kept_chars += row_chars
    if not changed:
        return document
    clipped = dict(document)
    clipped_data = dict(data)
    clipped_data[rows_key] = kept
    clipped["data"] = clipped_data
    return clipped


__all__ = [
    "ERROR_CIRCUIT_OPEN",
    "ERROR_INVALID_ARGUMENTS",
    "ERROR_NOT_ALLOWED",
    "ERROR_OUT_OF_SCOPE",
    "ERROR_TIMEOUT",
    "ERROR_TOOL",
    "ERROR_UNKNOWN_TOOL",
    "MAX_CONTENT_CHARS",
    "MAX_FIELD_TEXT",
    "SENSITIVE_TOOLS",
    "TOOL_DESCRIPTIONS",
    "TRANSIENT_ERRORS",
    "McpToolClient",
    "ToolCallError",
    "ToolCallRecord",
    "ToolClient",
    "ToolExecutor",
    "ToolOutcome",
    "clip_tool_content",
]
