"""When the question's key fact is in.

The loop used to have one way to stop reading: run out of budget. The M4
re-verification shows what that costs — six successful tool calls, a token
budget spent, no answer. The reading was often complete long before the
budget was.

This module answers one question: *has the key fact this kind of question
needs been read?* The answer is decided from the plan's intent and from the
observations the tools already produced, so it is deterministic, testable and
free. It is not a judgement about whether the evidence is *enough* to prove a
conclusion — that remains the verifier's job, and the model's answer remains
a lead.

A successful read counts even when it found nothing. "The search returned no
match" is a fact about the analysis, and it is the fact a question about an
absent symbol needs. A failed or refused call counts for nothing: its
observation is not a reading.
"""

from __future__ import annotations

from dexatlas.agent.providers.base import Observation
from dexatlas.agent.state import Plan, TaskState

#: The tools whose successful reading is the key fact of each intent.
#:
#: The mapping is deliberately narrow. A search is not the key fact of a
#: callers question, and a status read is never the key fact of anything:
#: only the read that names what the question asked about closes it.
KEY_TOOLS: dict[str, frozenset[str]] = {
    "manifest": frozenset({"get_manifest"}),
    "symbols": frozenset({"search_symbols"}),
    "source": frozenset({"get_class_source", "get_method_source"}),
    "calls": frozenset({"find_callers", "find_callees"}),
    "evidence": frozenset({"get_evidence", "resolve_locator"}),
    "resources": frozenset({"find_resource_declarations"}),
}

#: Every tool that can be the key reading of some question.
ANY_KEY_TOOL: frozenset[str] = frozenset().union(*KEY_TOOLS.values())


def read_tools(state: TaskState) -> frozenset[str]:
    """The tools the task has successfully read through.

    Only a reading counts. A refused call, a timeout, a deferred call and a
    call whose answer was itself a repeat are all excluded — none of them is
    evidence that the question has been answered.
    """
    return frozenset(
        turn.tool
        for turn in state.turns
        if isinstance(turn, Observation) and turn.ok and not turn.duplicate_of
    )


def failed_tools(state: TaskState) -> frozenset[str]:
    """The tools whose call failed with a recorded answer about the analysis.

    A tool error is not a reading of the APK, but some errors *are* the fact
    a question is about: ``no_manifest`` on a workspace whose APK reader was
    absent says "there is no manifest here" — which is the whole answer to
    "what package does the manifest declare". The tools whose failures carry
    that kind of fact count toward the question being settled, so a model
    that keeps re-asking a tool that has already answered "no" is closed
    instead of circling until the budget dies.
    """
    return frozenset(
        turn.tool
        for turn in state.turns
        if isinstance(turn, Observation) and not turn.ok and turn.tool in FAILURE_IS_AN_ANSWER
    )


#: The tools whose failure is itself the fact a partial-configuration
#: question asks about. A ``no_manifest`` error is not a malfunction: it is
#: the analysis saying it holds no manifest, which is exactly what a
#: question asked in a configuration without the APK reader needs to hear.
FAILURE_IS_AN_ANSWER: frozenset[str] = frozenset({"get_manifest"})


def ready_reason(plan: Plan, state: TaskState) -> str | None:
    """Why the reading is complete, or ``None`` while it is not.

    A plan with several intents is complete when every one of them has its
    key reading: "which permissions, and who calls this method" needs both
    the manifest and the callers. A general question — or a plan saved before
    intents were recorded — is complete with any key reading. A failed call
    whose error states the fact the question needs (``no_manifest`` on a
    workspace with no APK reader) closes the intent as well: the analysis
    has answered, and the answer is "there is nothing here to read".
    """
    intents = [intent for intent in plan.intents if intent]
    read = read_tools(state)
    failed = failed_tools(state)

    if not intents or "general" in intents:
        if read & ANY_KEY_TOOL or failed & ANY_KEY_TOOL:
            return "a key reading of the question has returned"
        return None

    missing: list[str] = []
    for intent in intents:
        if (_key_tools(intent) & read) or (_key_tools(intent) & failed):
            continue
        missing.append(intent)
    if missing:
        return None

    tools = sorted(
        {
            tool
            for intent in intents
            for tool in (_key_tools(intent) & read) | (_key_tools(intent) & failed)
        }
    )
    if len(intents) == 1:
        return f"the key reading for the {intents[0]} question has returned: {', '.join(tools)}"
    return f"the key readings for the question have returned: {', '.join(tools)}"


def _key_tools(intent: str) -> frozenset[str]:
    """The tools that close one intent; an unknown intent closes on any of them."""
    return KEY_TOOLS.get(intent, ANY_KEY_TOOL)
