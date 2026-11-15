"""The enumeration contract: a question about a class's methods names them all.

The M6 level-2 retest found the agent answering the descriptor question with
the two methods the question named — digestOf and obfuscate share a
descriptor — and leaving out ``sign``, whose different descriptor is the
other half of the answer. The scorer required all three full identities, so
the answer failed on an omission, not on a mistake.

The fix is in the answer contract: the instructions now say a question about
some methods of a class is answered with one finding per method the question
touches, *including the ones that break the pattern*. These tests pin the
contract text.
"""

from __future__ import annotations

from dexatlas.agent.orchestrator import INSTRUCTIONS

#: The instructions are prose with line breaks; the contract's phrases are
#: checked against the text with the breaks folded away.
FLAT = " ".join(INSTRUCTIONS.split())


def test_the_instructions_ask_for_every_method_the_question_touches() -> None:
    """The enumeration rule is in the contract, with the counterexample named."""
    assert "one finding per method the question touches" in FLAT
    assert "including the ones that break the pattern" in FLAT


def test_the_instructions_say_a_partial_enumeration_is_not_an_answer() -> None:
    """The contract says to enumerate every method read, not only the named pair."""
    assert "enumerate every method" in FLAT
    assert "rather than only the two the question named" in FLAT


def test_the_contract_keeps_the_marking_scheme_out_of_the_model() -> None:
    """The rule is phrased as analysis discipline, never as scoring vocabulary."""
    assert "must_contain" not in INSTRUCTIONS
    assert "expect_count" not in INSTRUCTIONS
