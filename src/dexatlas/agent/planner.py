"""Turning a question into a bounded plan.

The plan is worked out *before* the model is asked anything, and it says three
things: which project the task is about, which tools the task may call, and
how many calls it may make. The model then chooses which of those tools to
call and with what arguments.

That order is the point. A model that is handed the tools can ask for
whatever it likes; a model that is handed a *plan* can only choose within
it. And because the plan is worked out from the question alone — before a
single byte of the APK has been read — nothing the APK contains can widen it.
An instruction that an APK carries is text in a tool's answer, and text in a
tool's answer does not get to decide what the agent is allowed to do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from dexatlas.agent.state import Budget, Plan, PlanStep

#: The tools every task may call.
#:
#: They are the ones a conclusion needs: the status of the analysis, so that
#: a missing backend is known; the evidence and the locator resolver, so that
#: a conclusion can be checked against the analysis it is about.
ALWAYS_ALLOWED: tuple[str, ...] = (
    "list_projects",
    "get_project_status",
    "get_evidence",
    "resolve_locator",
)


class Intent(StrEnum):
    """What kind of question this is."""

    MANIFEST = "manifest"
    SYMBOLS = "symbols"
    SOURCE = "source"
    CALLS = "calls"
    EVIDENCE = "evidence"
    GENERAL = "general"


#: The words that mean each intent.
#:
#: The words are matched against the question the user typed, one whole word
#: at a time. A question that matches nothing is a general question, and a
#: general question is answered with the whole tool set: a question the
#: planner does not understand is not a question the agent cannot work on.
#:
#: The order is the priority order — the more specific an intent is, the
#: earlier it is listed, and the first one that matches is the question's
#: primary intent. It is also the order the tools are unioned in, so a
#: question that mentions both a method and a call gets both sets of tools
#: rather than whichever happened to be matched first.
INTENT_WORDS: dict[Intent, tuple[str, ...]] = {
    Intent.MANIFEST: (
        "manifest",
        "permission",
        "permissions",
        "package",
        "component",
        "components",
        "activity",
        "service",
        "receiver",
        "provider",
        "exported",
        "sdk",
        "version",
    ),
    Intent.EVIDENCE: (
        "evidence",
        "citation",
        "cite",
        "prove",
        "proof",
        "locator",
        "recorded",
    ),
    Intent.CALLS: (
        "call",
        "calls",
        "called",
        "caller",
        "callers",
        "callee",
        "callees",
        "invoke",
        "invoked",
        "invokes",
        "trace",
        "reachable",
    ),
    Intent.SOURCE: (
        "source",
        "code",
        "body",
        "decompiled",
        "smali",
        "java",
        "implementation",
    ),
    Intent.SYMBOLS: (
        "symbol",
        "symbols",
        "class",
        "classes",
        "method",
        "methods",
        "field",
        "fields",
        "string",
        "strings",
        "index",
        "named",
        "find",
        "search",
        "where",
    ),
}

#: The tools each intent may call.
INTENT_TOOLS: dict[Intent, tuple[str, ...]] = {
    Intent.MANIFEST: ("get_manifest",),
    Intent.SYMBOLS: ("search_symbols", "get_class_source", "get_method_source"),
    Intent.SOURCE: ("get_class_source", "get_method_source", "search_symbols"),
    Intent.CALLS: (
        "find_callers",
        "find_callees",
        "search_symbols",
        "get_method_source",
    ),
    Intent.EVIDENCE: ("get_evidence", "resolve_locator", "get_manifest", "search_symbols"),
    Intent.GENERAL: (
        "get_manifest",
        "search_symbols",
        "get_class_source",
        "get_method_source",
        "find_callers",
        "find_callees",
    ),
}

#: What the agent is being asked to find out, for each intent.
OBJECTIVES: dict[Intent, str] = {
    Intent.MANIFEST: (
        "Find out what the manifest says about this APK: its package, the "
        "permissions it asks for, and the components it declares."
    ),
    Intent.SYMBOLS: (
        "Find the symbols of this APK that the question is about, and say which "
        "ones the index holds."
    ),
    Intent.SOURCE: ("Read the source the question is about, and say which backend produced it."),
    Intent.CALLS: ("Trace the calls the question is about: who calls what, and what calls what."),
    Intent.EVIDENCE: (
        "Find the evidence the question is about, and say whether it resolves inside this analysis."
    ),
    Intent.GENERAL: (
        "Find out what the question is about, using the tools, and say what the "
        "analysis can and cannot answer."
    ),
}

#: How many tool calls a task may make.
DEFAULT_MAX_STEPS = 12

#: How many sensitive calls a task may make before a person is asked.
DEFAULT_MAX_SENSITIVE_CALLS = 1


@dataclass(frozen=True, slots=True)
class Planner:
    """Works out what a question needs, before anything is read."""

    limits: Budget = field(default_factory=Budget)
    max_steps: int = DEFAULT_MAX_STEPS
    max_sensitive_calls: int = DEFAULT_MAX_SENSITIVE_CALLS

    def matched_intents(self, question: str) -> list[Intent]:
        """The intents the question mentions, in priority order.

        A question that mentions two things gets both: "what calls the method
        that takes a String" is about the call graph *and* about the symbols,
        and the task may read the symbols and trace the calls.
        """
        words = set(re.findall(r"[a-z0-9_]+", question.lower()))
        matched = [
            intent for intent, markers in INTENT_WORDS.items() if words.intersection(markers)
        ]
        return matched or [Intent.GENERAL]

    def intent(self, question: str) -> Intent:
        """What kind of question this is."""
        return self.matched_intents(question)[0]

    def allowed_tools(self, intents: list[Intent]) -> tuple[str, ...]:
        """The tools a task of these intents may call."""
        tools: list[str] = list(ALWAYS_ALLOWED)
        for intent in intents:
            for tool in INTENT_TOOLS[intent]:
                if tool not in tools:
                    tools.append(tool)
        return tuple(tools)

    def plan(self, question: str, project_id: str | None = None) -> Plan:
        """The plan for one question.

        The first step is always the same: find out what the analysis is and
        how complete it is. A task that read a count before it read the
        status would not know that the count was a count of what was indexed
        rather than a count of what the APK holds.
        """
        intents = self.matched_intents(question)
        steps: list[PlanStep] = []
        if project_id is None:
            steps.append(
                PlanStep(
                    tool="list_projects",
                    purpose="find which analysed APK the question is about",
                    arguments={"limit": 1, "offset": 0},
                )
            )
        steps.append(
            PlanStep(
                tool="get_project_status",
                purpose="read the analysis's status and how complete it is",
                arguments={"project_id": project_id} if project_id else {},
            )
        )
        return Plan(
            project_id=project_id or "",
            question=question,
            steps=tuple(steps),
            allowed_tools=self.allowed_tools(intents),
            max_steps=self.max_steps,
            max_sensitive_calls=self.max_sensitive_calls,
            limits=self.limits,
        )

    def objective(self, question: str) -> str:
        """What the agent is being asked to find out."""
        return OBJECTIVES[self.intent(question)]


__all__ = [
    "ALWAYS_ALLOWED",
    "DEFAULT_MAX_SENSITIVE_CALLS",
    "DEFAULT_MAX_STEPS",
    "INTENT_TOOLS",
    "INTENT_WORDS",
    "OBJECTIVES",
    "Intent",
    "Planner",
]
