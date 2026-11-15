"""A question about the analysis itself is answered from the process records.

The M6 level-2 retest found the no-jadx task — "Does the analysis record
that the decompiler was missing?" — answered with nothing: the model cited
the completeness read, the verifier called the conclusion insufficient
(because a completeness read supports no claim about the *APK*), and the
process-note rule then moved the sentence into the limitations. The scorer
saw an empty answer and failed it.

The rule was right for questions about the APK and wrong for questions
whose *subject is the analysis*. This module pins the fix: on a question
that asks about the analysis's own bookkeeping, a conclusion citing only
the process records stands as a finding.

Red state: the committed code before the subject check — the process-note
demotion fires on the partial question and the answer empties out.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from tests.agent_harness import PROJECT_ID, build_demo, make_orchestrator, observation_evidence_ids

PARTIAL_QUESTION = "Does the analysis record that the decompiler was missing?"


@pytest.fixture
def demo(settings, tmp_path: Path):
    return build_demo(settings, tmp_path, missing_backends=("jadx",))


def _orchestrator(demo, provider: ScriptedProvider, tmp_path: Path):
    return make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )


def test_a_conclusion_about_the_recorded_gap_is_a_finding(demo, tmp_path: Path) -> None:
    """ "The analysis records jadx as missing" stands as a finding on the partial question.

    The conclusion cites only the completeness read — the one record that
    describes the analysis rather than the APK. On a question about the
    analysis itself that citation is the answer's subject, so the finding
    stands instead of being demoted to a limitation.
    """

    def cite_the_completeness_read(request) -> object:
        ids = observation_evidence_ids(request)
        return answer(
            [
                conclusion(
                    "the analysis records that jadx is missing: jadx did not take part",
                    evidence_ids=ids[:1],
                )
            ]
        )

    provider = ScriptedProvider(
        responses=[
            # The plan's own status read happens before the model is asked;
            # the first scripted reply is the answer itself.
            cite_the_completeness_read,
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(PARTIAL_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED
    behaviours = [record for record in state.findings if record.kind.value == "behaviour"]
    assert behaviours, "the recorded gap is the answer, and it must be a finding"
    assert any("jadx" in record.summary for record in behaviours)


def test_a_process_note_is_still_a_limitation_on_an_apk_question(settings, tmp_path: Path) -> None:
    """The subject check does not open the door on ordinary APK questions.

    "Which permissions does this APK request?" is about the APK; a
    conclusion citing only the completeness read is still a process note
    there, and it is still moved to the limitations.
    """
    from tests.agent_harness import build_demo as plain_build

    plain = plain_build(settings, tmp_path)

    def cite_only_the_status_read(request) -> object:
        ids = observation_evidence_ids(request)
        return answer(
            [
                conclusion(
                    "the analysis is complete, so the answer is trustworthy",
                    evidence_ids=ids[:1],
                )
            ]
        )

    provider = ScriptedProvider(
        responses=[
            cite_only_the_status_read,
        ]
    )
    state = _orchestrator(plain, provider, tmp_path).run(
        "Which permissions does this APK request?", project_id=PROJECT_ID
    )

    assert state.status is TaskStatus.COMPLETED
    behaviours = [record for record in state.findings if record.kind.value == "behaviour"]
    assert not behaviours, "a process-only conclusion on an APK question stays a limitation"
