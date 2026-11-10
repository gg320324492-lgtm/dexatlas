"""Turn a system under test's output into :class:`benchmarks.model.Answer`.

``docs/benchmarks/task-set.md`` section 3.1 assigns prose-to-evidence
adaptation to the comparison harness: the task set does not define how a
paragraph becomes a list of evidence. This is that layer, shared by all three
configurations so that a difference in phrasing cannot become a difference
in scoring.

Two outputs, deliberately separate:

* :func:`answer_from_result` is for the scorer. The system's *conclusions*
  become findings, and its raw prose stays in ``Answer.text``.
* :func:`prose_to_conclusions` splits prose into claims for the metrics.

It knows nothing about tasks or expected answers and never reads
``benchmarks/tasks/``.
"""

from __future__ import annotations

from benchmarks.comparison.model import SystemResult
from benchmarks.model import Answer, Finding
from dexatlas.agent.evidence_verifier import parse_answer


def answer_from_result(result: SystemResult) -> Answer:
    """Convert one system output into an ``Answer`` the scorer can check.

    A system's conclusion is a claim that something is the case, so it is
    evidence in the scorer's sense. That matters on the tasks whose right
    answer is an absence: ``check()`` rejects any finding at all on those, and
    a prose system that says "a caller exists" must not pass simply because
    the task has no ``must_not_contain`` marker. Saying "there is none" belongs
    in ``limitations``, not in ``conclusions``, so it produces no finding.

    The raw prose stays in ``text`` for ``must_contain`` matching. A system
    that names the right symbol in a sentence still gets credit for it.
    """
    findings = tuple(Finding(text=assertion.text) for assertion in result.assertions)
    # Only the claims themselves, not the JSON envelope or the retrieval dump.
    # Handing the scorer the whole observation would let a substring match
    # pass without the system having said anything.
    said = "\n".join(assertion.text for assertion in result.assertions)
    return Answer(findings=findings, text=said, note="")


def is_empty(answer: Answer) -> bool:
    """Whether the scorer sees no evidence at all.

    Only findings count. The raw prose is kept for ``must_contain`` matching,
    but a JSON envelope that says "no conclusions" is still an empty answer.
    """
    return not answer.findings


def prose_to_conclusions(content: str) -> tuple[str, ...]:
    """Split a model's final answer into its claims.

    Reuses the agent's own :func:`parse_answer`. An answer that is not JSON,
    or that names no evidence, is kept as one unsupported claim rather than
    discarded -- that is exactly what unsupported-assertion rate counts.
    An empty ``conclusions`` list (with the absence reported in
    ``limitations``) produces no claims at all.
    """
    parsed = parse_answer(content)
    return tuple(conclusion.statement for conclusion in parsed.conclusions)
