"""The line between a lead and a finding.

This is the boundary the whole project is built on, and it is the boundary
the agent has to keep:

* a **tool's reading** is a fact, and it is recorded as one;
* a **model's conclusion** is never a fact — the mechanism that says so is
  the project's own ``EvidenceBuilder``, and the agent routes its conclusions
  through it rather than around it;
* a conclusion that names nothing, or that names something that is not
  there, is **insufficient evidence**: not a finding, and not a lead either.

The tests below check each of those, and the last one checks that the
refusal is the mechanism's and not a convention: the builder refuses a
verified claim, so the agent could not have written one even if it wanted to.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.evidence_verifier import (
    SUPPORTS_CLAIMS,
    Conclusion,
    EvidenceVerifier,
    parse_answer,
)
from dexatlas.agent.state import TaskStatus, TaskStore
from dexatlas.core.evidence import EvidenceBuilder, InvalidProvenanceError
from dexatlas.core.models import Evidence, EvidenceKind, EvidenceLevel, Provenance
from tests.agent_harness import (
    FAKE_SHA256,
    TOOL_VERSIONS,
    Demo,
    build_demo,
    make_orchestrator,
)


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _builder(demo: Demo) -> EvidenceBuilder:
    return demo.builder()


def _verifier(demo: Demo, records: list[Evidence], resolves: set[str]) -> EvidenceVerifier:
    """A verifier over some records, and the locators that resolve."""
    index = {record.id: record for record in records}
    return EvidenceVerifier(
        _builder(demo),
        record_for=lambda evidence_id: index.get(evidence_id),
        resolves=lambda locator: locator in resolves,
    )


def test_a_conclusion_that_names_nothing_is_insufficient(demo: Demo) -> None:
    """A conclusion nobody can check is not a lead."""
    verifier = _verifier(demo, [], set())

    record = verifier.verify(Conclusion("the app is safe"))

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert record.kind is EvidenceKind.BEHAVIOUR
    assert "no evidence behind it" in record.summary


def test_a_conclusion_that_names_a_record_the_task_made_is_a_lead(demo: Demo) -> None:
    """A conclusion the tools back is a lead — and nothing more."""
    builder = _builder(demo)
    established = builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="the manifest declares two permissions",
        provenance=[
            Provenance(
                tool="apktool",
                tool_version=TOOL_VERSIONS["apktool"],
                apk_sha256=FAKE_SHA256,
                locator="apktool:AndroidManifest.xml",
            )
        ],
    )
    verifier = _verifier(demo, [established], {"apktool:AndroidManifest.xml"})

    record = verifier.verify(
        Conclusion("the app asks for location access", evidence_ids=[established.id])
    )

    assert record.level is EvidenceLevel.LEAD
    assert record.detail["supported_by"] == [established.id]
    assert record.detail["unsupported"] == []


def test_a_note_about_the_analysis_cannot_carry_a_conclusion(demo: Demo) -> None:
    """A record about the analysis is not an observation of the thing asked about.

    "The analysis is incomplete: apktool did not take part" is true and it
    is worth knowing, but a conclusion that rests on it has nothing behind
    it. The record that says which backends ran is a note about the
    analysis; the question was about the APK.
    """
    builder = _builder(demo)
    note = builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="the analysis is incomplete: apktool did not take part",
        provenance=[],
        detail={SUPPORTS_CLAIMS: False},
    )
    verifier = _verifier(demo, [note], set())

    record = verifier.verify(Conclusion("the app asks for location access", evidence_ids=[note.id]))

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert record.detail["supported_by"] == []
    assert "note about the analysis" in record.detail["unsupported"][0]


def test_a_record_that_establishes_nothing_cannot_carry_a_conclusion(demo: Demo) -> None:
    """A record that says the evidence was insufficient cannot be the ground.

    It is a record of a reading that did not come up to much, so a
    conclusion that cites it is citing the absence of evidence as if it
    were evidence.
    """
    builder = _builder(demo)
    weak = builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.INSUFFICIENT,
        summary="the tool read something, but its citation does not resolve",
        provenance=[],
    )
    verifier = _verifier(demo, [weak], set())

    record = verifier.verify(Conclusion("the app asks for location access", evidence_ids=[weak.id]))

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert record.detail["supported_by"] == []
    assert "note about the analysis" in record.detail["unsupported"][0]


def test_a_conclusion_that_names_a_record_that_is_not_there_is_insufficient(
    demo: Demo,
) -> None:
    """A citation to a record the task never made is no citation at all."""
    verifier = _verifier(demo, [], set())

    record = verifier.verify(Conclusion("the app is safe", evidence_ids=["E-9999"]))

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert "no such record" in record.detail["unsupported"][0]


def test_a_conclusion_that_cites_a_locator_that_does_not_resolve_is_insufficient(
    demo: Demo,
) -> None:
    """A citation to a place that is not there does not support anything."""
    verifier = _verifier(demo, [], set())

    record = verifier.verify(
        Conclusion("the app is safe", locators=["jadx:sources/com/example/demo/Nope.java"])
    )

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert "does not resolve" in record.detail["unsupported"][0]


def test_a_conclusion_that_cites_a_locator_that_resolves_is_a_lead(demo: Demo) -> None:
    """A locator the analysis can follow is a citation."""
    verifier = _verifier(demo, [], {"jadx:sources/com/example/demo/Crypto.java"})

    record = verifier.verify(
        Conclusion(
            "the Crypto class is decompiled Java",
            locators=["jadx:sources/com/example/demo/Crypto.java"],
        )
    )

    assert record.level is EvidenceLevel.LEAD
    assert record.provenance[0].locator == "jadx:sources/com/example/demo/Crypto.java"


def test_a_record_whose_citation_does_not_resolve_does_not_support_a_conclusion(
    demo: Demo,
) -> None:
    """A record that points at a place which is not there supports nothing."""
    builder = _builder(demo)
    dangling = builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="something was read out of a file that is not there",
        provenance=[
            Provenance(
                tool="jadx",
                tool_version=TOOL_VERSIONS["jadx"],
                apk_sha256=FAKE_SHA256,
                locator="jadx:sources/com/example/demo/Gone.java",
            )
        ],
    )
    verifier = _verifier(demo, [dangling], set())

    record = verifier.verify(Conclusion("the app is safe", evidence_ids=[dangling.id]))

    assert record.level is EvidenceLevel.INSUFFICIENT
    assert "does not resolve" in record.detail["unsupported"][0]


def test_a_model_claim_cannot_be_recorded_as_verified(demo: Demo) -> None:
    """The refusal is the mechanism's, and it is already there.

    This is the project's own guard: the builder does not offer a verified
    level for a claim, so a caller that could pass it by mistake cannot.
    """
    builder = _builder(demo)

    with pytest.raises(InvalidProvenanceError):
        builder.add_claim(
            "the app is safe",
            [],
            level=EvidenceLevel.VERIFIED,
        )


def test_a_verifier_never_writes_a_verified_record(demo: Demo) -> None:
    """Whatever the model says, the conclusion is not a fact."""
    builder = _builder(demo)
    established = builder.add(
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="the manifest declares two permissions",
        provenance=[],
    )
    verifier = _verifier(demo, [established], set())

    for conclusion in (
        Conclusion("the app is safe"),
        Conclusion("the app is safe", evidence_ids=[established.id]),
        Conclusion("the app is safe", locators=["apktool:AndroidManifest.xml"]),
    ):
        assert verifier.verify(conclusion).level is not EvidenceLevel.VERIFIED


def test_an_answer_that_is_not_json_is_kept_as_a_conclusion_without_evidence() -> None:
    """An answer the agent cannot read is not thrown away.

    It is recorded as a conclusion that names nothing, which is what it is.
    """
    parsed = parse_answer("The app looks fine to me.")

    assert len(parsed.conclusions) == 1
    assert parsed.conclusions[0].evidence_ids == ()
    assert "without naming any evidence" in parsed.conclusions[0].statement


def test_an_answer_with_no_conclusions_is_an_answer() -> None:
    """ "The analysis does not settle this" is a complete answer."""
    parsed = parse_answer('{"conclusions": [], "limitations": ["nothing was found"]}')

    assert parsed.conclusions == ()
    assert parsed.limitations == ("nothing was found",)


def test_the_agent_records_a_conclusion_it_cannot_back_as_insufficient(
    demo: Demo, tmp_path: Path
) -> None:
    """The rule holds end to end, not only in the verifier.

    The model names an evidence id the task never made, and the report says
    there was not enough evidence rather than passing the sentence off.
    """
    from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion

    provider = ScriptedProvider(
        responses=[answer([conclusion("the app is safe", evidence_ids=["E-9999"])])]
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    findings = [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED]
    assert len(findings) == 1
    assert findings[0].level is EvidenceLevel.INSUFFICIENT

    from dexatlas.agent.reporter import render_agent_markdown

    markdown = render_agent_markdown(orchestrator.report(state))
    assert "## Insufficient evidence" in markdown
    assert "## Leads" in markdown


def test_a_conclusion_may_cite_a_record_the_analysis_already_holds(
    demo: Demo, tmp_path: Path
) -> None:
    """A model that read a record through the tool may cite that record.

    The ids it saw are the analysis's own, and a record that is really there
    supports a conclusion — only a record that is nowhere does not.
    """
    from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion

    provider = ScriptedProvider(
        responses=[answer([conclusion("the manifest is recorded", evidence_ids=["E-0001"])])]
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("What evidence does the analysis hold?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    findings = [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED]
    assert len(findings) == 1
    assert findings[0].level is EvidenceLevel.LEAD, (
        "the analysis holds E-0001 and its citation resolves, so the conclusion is a lead"
    )
    assert findings[0].detail["supported_by"] == ["E-0001"]
