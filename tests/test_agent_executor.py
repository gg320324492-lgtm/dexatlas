"""The tools are called through a boundary, and the boundary holds.

Three things can go wrong when an agent calls a tool, and each of them has
its own answer:

* the call takes too long — it is abandoned, and the log says so;
* the call fails for a reason that might go away — it is tried again;
* the call keeps failing — the breaker opens, and the tool is not called
  again until it has had a chance to recover.

And two things must not happen at all: a tool the plan does not allow must
not be called, and a call about another project must not be made. Both are
refused *before* the call, so a refusal costs nothing and leaves no trace in
the workspace.

The client here is a stand-in for the MCP tools: it answers from a script,
and it can be told to fail, to hang, or to count its calls.
"""

from __future__ import annotations

import inspect
import time
from pathlib import Path
from typing import Any

import pytest

from dexatlas.agent.providers.base import ToolSpec
from dexatlas.agent.tool_executor import (
    ERROR_CIRCUIT_OPEN,
    ERROR_INVALID_ARGUMENTS,
    ERROR_NOT_ALLOWED,
    ERROR_OUT_OF_SCOPE,
    ERROR_TIMEOUT,
    ERROR_TOOL,
    ToolCallError,
    ToolExecutor,
)
from tests.agent_harness import Demo, build_demo


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    """The workspace the agent's tests run against."""
    return build_demo(settings, tmp_path)


class FakeClient:
    """A tool client that answers from a script."""

    def __init__(self, *, fail_times: int = 0, delay: float = 0.0) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_times = fail_times
        self.delay = delay

    def call(self, tool: str, arguments: Any) -> Any:
        """Answer one call."""
        self.calls.append((tool, dict(arguments)))
        if self.delay:
            time.sleep(self.delay)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ToolCallError(f"{tool} did not answer", kind=ERROR_TOOL, transient=True)
        return {"tool": tool, "arguments": dict(arguments)}

    def describe(self, tool: str) -> ToolSpec:
        """Describe one tool."""
        return ToolSpec(name=tool, description=f"The {tool} tool.")

    def signature(self, tool: str) -> inspect.Signature:
        """The signature of one tool."""
        return inspect.Signature(
            [
                inspect.Parameter(
                    "project_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str
                ),
                inspect.Parameter(
                    "limit", inspect.Parameter.KEYWORD_ONLY, annotation=int, default=50
                ),
            ]
        )


def test_a_call_that_answers_is_recorded() -> None:
    """The ordinary case: the call happened, and the log says so."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert outcome.ok
    assert outcome.record.tool == "get_manifest"
    assert outcome.record.arguments == {"project_id": "apk_one"}
    assert outcome.record.duration_seconds >= 0
    assert client.calls == [("get_manifest", {"project_id": "apk_one"})]


def test_a_call_that_takes_too_long_is_abandoned() -> None:
    """A timeout is a value in the log, not an exception that stops the task.

    Python cannot stop a thread that is already running, so the call is
    abandoned and left to finish on its own. What matters is that the task
    is not left waiting for it, and that the log says the call was
    abandoned rather than that it failed.
    """
    client = FakeClient(delay=0.4)
    executor = ToolExecutor(client, timeout=0.05, max_attempts=1)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_TIMEOUT
    assert "did not answer within" in (outcome.record.error or "")
    assert "timeout" in outcome.content


def test_a_call_that_fails_is_tried_again() -> None:
    """A failure that might go away is tried again."""
    client = FakeClient(fail_times=2)
    executor = ToolExecutor(client, max_attempts=3)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert outcome.ok, outcome.record.error
    assert outcome.record.attempt == 3
    assert len(client.calls) == 3


def test_a_call_that_keeps_failing_gives_up() -> None:
    """The attempts run out, and the task is told why."""
    client = FakeClient(fail_times=10)
    executor = ToolExecutor(client, max_attempts=2)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert not outcome.ok
    assert outcome.record.attempt == 2
    assert outcome.record.error_kind == ERROR_TOOL
    assert len(client.calls) == 2


def test_a_broken_tool_is_not_called_again_and_again() -> None:
    """The breaker opens, and the calls after that are refused.

    A task being eaten by a broken workspace fails once instead of once per
    step, and the log says the tool was not called rather than that it
    failed.
    """
    client = FakeClient(fail_times=100)
    executor = ToolExecutor(client, max_attempts=1, failure_threshold=3)

    for _ in range(3):
        outcome = executor.execute("get_manifest", {"project_id": "apk_one"})
        assert not outcome.ok
        assert outcome.record.error_kind == ERROR_TOOL

    refused = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert not refused.ok
    assert refused.record.error_kind == ERROR_CIRCUIT_OPEN
    assert len(client.calls) == 3, "the tool was called once per failure and no more"


def test_the_breaker_opens_again_after_it_has_had_a_chance_to_recover() -> None:
    """A breaker that never probes is a tool that is never tried again."""
    clock = {"now": 0.0}
    client = FakeClient(fail_times=2)
    executor = ToolExecutor(
        client,
        max_attempts=1,
        failure_threshold=2,
        reset_after=30.0,
        clock=lambda: clock["now"],
    )

    executor.execute("get_manifest", {"project_id": "apk_one"})
    executor.execute("get_manifest", {"project_id": "apk_one"})
    assert executor.execute("get_manifest", {"project_id": "apk_one"}).record.error_kind == (
        ERROR_CIRCUIT_OPEN
    )

    clock["now"] = 31.0
    probed = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert probed.ok, "the breaker let one probe through after the cool-off"
    assert len(client.calls) == 3


def test_a_tool_the_plan_does_not_allow_is_not_called() -> None:
    """The plan is the bound, and it is enforced before the call."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute(
        "get_method_source", {"project_id": "apk_one"}, allowed_tools=frozenset({"get_manifest"})
    )

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_NOT_ALLOWED
    assert client.calls == [], "the tool was not called"


def test_a_call_about_another_project_is_refused() -> None:
    """The project is pinned, and a call about another one is not made."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute(
        "get_manifest", {"project_id": "apk_someone_else"}, project_id="apk_mine"
    )

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_OUT_OF_SCOPE
    assert client.calls == [], "the tool was not called"


def test_an_argument_the_tool_does_not_have_is_refused() -> None:
    """The arguments come from a model, so they are checked."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one", "wat": 1})

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_INVALID_ARGUMENTS
    assert client.calls == []


def test_a_missing_argument_the_tool_needs_is_refused() -> None:
    """A request the tool cannot answer is refused, not attempted."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {})

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_INVALID_ARGUMENTS
    assert "project_id" in (outcome.record.error or "")
    assert client.calls == []


def test_an_argument_of_the_wrong_type_is_refused() -> None:
    """A limit that is a string is not a limit."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one", "limit": "many"})

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_INVALID_ARGUMENTS
    assert client.calls == []


def test_an_optional_argument_may_be_left_out() -> None:
    """The optional arguments are optional."""
    client = FakeClient()
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert outcome.ok


@pytest.mark.parametrize(
    ("kind", "transient"),
    [(ERROR_TOOL, True), (ERROR_TOOL, False)],
)
def test_only_a_transient_failure_is_tried_again(kind: str, transient: bool) -> None:
    """A request the server refused will be refused again.

    Trying it once more costs the task its budget and buys nothing.
    """
    attempts = {"count": 0}

    class Refusing(FakeClient):
        def call(self, tool: str, arguments: Any) -> Any:
            attempts["count"] += 1
            raise ToolCallError("refused", kind=kind, transient=transient)

    executor = ToolExecutor(Refusing(), max_attempts=3)
    outcome = executor.execute("get_manifest", {"project_id": "apk_one"})

    assert not outcome.ok
    assert attempts["count"] == (3 if transient else 1)


def test_the_real_tools_refuse_an_argument_of_the_wrong_type(demo: Demo) -> None:
    """The check has to work on the tools the agent really calls.

    The tools are written with ``from __future__ import annotations``, so
    their annotations are *text* at runtime. A check against the text would
    pass everything, and a check that passes everything is not a check — so
    this is checked against the real client, not against a stand-in.
    """
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    executor = ToolExecutor(client)

    outcome = executor.execute("get_manifest", {"project_id": 42})

    assert not outcome.ok
    assert outcome.record.error_kind == ERROR_INVALID_ARGUMENTS
    assert "project_id" in (outcome.record.error or "")


def test_the_real_tools_accept_the_arguments_they_declare(demo: Demo) -> None:
    """The check does not refuse what the tool does take."""
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    executor = ToolExecutor(client)

    outcome = executor.execute(
        "search_symbols",
        {"project_id": demo.project_id, "query": "collect", "limit": 5, "offset": 0},
    )

    assert outcome.ok, outcome.record.error
