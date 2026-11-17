"""The M6 next-round fixes: leak feedback and the three wording contracts.

The M6 level-2 failure deep-dive left four conversion work items, one per
still-unstable task face. This file pins all four:

* a tool-call protocol leak is retried *with a corrective instruction* —
  the same request verbatim leaked three retest rounds running;
* a backend that did not take part is named with the scorer's own failure
  phrases, and its values are never inferred from other backends' rows;
* a key or URL question whose word search only hit field names is sent on
  to the string-constant pool and the common secret prefixes;
* a method's identity is one contiguous ``package.Class.name(descriptor)``
  string, not pieces separated by backticks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.orchestrator import CLOSED_DIRECTIVE, INSTRUCTIONS
from dexatlas.agent.providers.base import ProviderError
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion
from dexatlas.agent.state import TaskStatus, TaskStore
from tests.agent_harness import Demo, build_demo, make_orchestrator


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


# -- the protocol-leak retry carries a correction -----------------------------


def test_a_protocol_leak_is_retried_with_a_correction(demo, tmp_path: Path) -> None:
    """The retry after a correctable failure is not the same request again.

    The retest's multidex task leaked ``<invoke>`` into its prose three
    rounds running, and every retry was the identical request — so every
    retry leaked again. A failure that carries a correction is now retried
    with that correction added to the instructions, so the model is told
    what was wrong with its previous reply.
    """
    leak = ProviderError(
        "the model answered with a tool-call protocol fragment instead of an answer",
        retryable=True,
        correction=(
            "Your previous reply was a tool-call protocol fragment, not an "
            "answer. Reply with the JSON answer document and nothing else."
        ),
    )
    provider = ScriptedProvider(
        responses=[
            leak,
            answer([conclusion("the APK holds two DEX files", evidence_ids=["E-0001"])]),
        ]
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("How many DEX files does this APK hold?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert len(provider.requests) == 2, "the leak was retried once"
    first, second = provider.requests
    assert second.instructions != first.instructions, "the retry carries feedback"
    assert "tool-call protocol" in second.instructions
    assert "tool-call protocol" not in first.instructions
    assert "JSON answer document" in second.instructions


def test_the_openai_provider_attaches_the_leak_correction() -> None:
    """The provider's leak failure carries the correction text with it.

    The orchestrator can only correct what the provider reports: the leak
    failure is the one failure the model itself can undo, so it is raised
    with the correction attached rather than as a bare retryable error.
    """
    from dexatlas.agent.providers.base import PROTOCOL_LEAK_CORRECTION
    from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", model="a-model")
    body = {
        "choices": [{"message": {"role": "assistant", "content": '<invoke name="get_manifest">'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with pytest.raises(ProviderError) as raised:
        provider.parse_response(body)

    assert raised.value.retryable is True
    assert raised.value.correction == PROTOCOL_LEAK_CORRECTION
    assert "JSON" in raised.value.correction


# -- the backend-failure wording contract ------------------------------------


def test_the_instructions_name_the_backend_failure_phrases() -> None:
    """A missing backend is named in the phrases the scorer reads.

    The scorer's backend-failure predicate looks for the backend name next to
    "was not installed", "not_installed" or "did not take part" — the words
    the pipeline itself writes. The contract tells the model to use one of
    those phrases verbatim, and never to infer the values the missing
    backend alone could have read.
    """
    for phrase in ("was not installed", "not_installed", "did not take part"):
        assert phrase in INSTRUCTIONS
    assert "never infer" in INSTRUCTIONS


# -- the credential-constant search contract ---------------------------------


def test_the_instructions_send_a_field_name_hit_to_the_constant_pool() -> None:
    """A key question whose search only hit names is sent on to the constants.

    The api-key task failed three rounds running on the same shape: the word
    search returned the field name ``api_key`` and the model stopped there,
    while the key itself sat in another class's constant pool. The contract
    names the common secret prefixes to search for next, and the class read
    that turns a constant into a cited answer.
    """
    for prefix in ("sk_", "AKIA", "AIza", "ghp_"):
        assert prefix in INSTRUCTIONS
    assert "get_class_source" in INSTRUCTIONS


# -- the contiguous method-identity contract ---------------------------------


def test_the_instructions_ask_for_a_contiguous_method_identity() -> None:
    """The method-identity rule gives a positive, contiguous template.

    The scorer matches ``package.Class.name(descriptor)`` as one string; an
    answer that writes the class, the name and the descriptor as separate
    quoted pieces says the right thing and still fails the substring check.
    The contract now says so, with the whole identity written out.
    """
    assert "unbroken" in INSTRUCTIONS
    assert "contiguous" in INSTRUCTIONS
    assert "com.example.wide.Handler.handle(Ljava/lang/String;)V" in INSTRUCTIONS


def test_the_closed_directive_warns_against_protocol_leaks() -> None:
    """The closing ask carries the same warning the retry carries.

    A model that leaks the tool-call protocol after the tools close is told,
    in the same breath that asks for its answer, that the fragment is not an
    answer and is discarded.
    """
    assert "tool-call protocol" in CLOSED_DIRECTIVE
