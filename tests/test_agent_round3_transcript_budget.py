"""A wide search page does not spend the task's token gate on boilerplate.

The narrow M6 verification's ``strings.api-key.demo`` task died at the
24,000-token gate with the whole spend on the prompt: every iteration re-sent
the transcript, and the transcript carried a page of string-constant rows
whose keys, bookkeeping and data notices outweighed the values they carried —
plus, before the fold and the string-excerpt cut, the same notice in full
twice per row. A task whose reading is one small page of constants must not
pay for that page again on every round.

This test runs the real loop over the real tools with a scripted model, under
a budget that models the benchmark's per-task gate, and asserts the task
*answers* — the transcript-shaped fixes keep the whole exchange inside the
gate. The scripted model bills tokens the way a real provider reports them:
from the serialized request it was handed.

Red state: without the fold, the excerpt cut and the row clip, the same
script over the same workspace bills past the gate and the task dies
``BUDGET_EXHAUSTED`` with no answer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

#: The benchmark's per-task gate, scaled to the scripted tokenizer: the demo
#: workspace is a fraction of a real APK, but the shape of the cost — a page
#: re-sent on every turn — is the same, and the gate has to bind the same way.
GATE_TOKENS = 9_000


def _bill_tokens(request):
    """A scripted response that charges what the request would have cost.

    The harness's tokenizer is crude — four characters to the token — but it
    is crude in the same direction as a real one: a transcript that grows on
    every iteration bills more on every iteration, and a page of boilerplate
    is billed on every turn that follows it.
    """
    size = len(request.instructions) + len(request.question)
    for turn in request.turns:
        size += len(turn.content)
        if getattr(turn, "tool_calls", None):
            size += sum(len(call.name) + len(str(call.arguments)) for call in turn.tool_calls)
    for spec in request.tools:
        size += len(spec.name) + len(spec.description)
    from dexatlas.agent.providers.base import ModelResponse

    return ModelResponse(model="scripted", prompt_tokens=size // 4)


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def test_a_page_of_string_hits_fits_the_token_gate(demo: Demo, tmp_path: Path) -> None:
    """The search-page task answers inside the gate instead of dying on it."""
    provider = ScriptedProvider(
        responses=[
            tool_call(
                "search_symbols",
                {"project_id": PROJECT_ID, "query": "api", "limit": 20, "offset": 0},
                call_id="call-1",
            ),
            tool_call(
                "get_class_source",
                {"project_id": PROJECT_ID, "class_name": "com.example.demo.Crypto"},
                call_id="call-2",
            ),
            lambda request: answer(
                [
                    conclusion(
                        "The string constant api_key is declared in com.example.demo.Crypto",
                        evidence_ids=observation_evidence_ids(request)[-1:],
                    )
                ]
            ),
        ]
    )
    state = make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=GATE_TOKENS, max_iterations=8, max_seconds=60.0),
    ).run("Which class declares the api_key string constant?", project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED, (
        f"the task died {state.status}: {state.error}\n"
        f"tokens used: {state.usage.tokens} of {GATE_TOKENS}"
    )
    assert state.usage.tokens <= GATE_TOKENS
