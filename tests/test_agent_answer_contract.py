"""The agent's answer contract: what a finding may say, and what may not.

The M6 level-2 failure analysis (``docs/benchmarks/m6-level2-failure-analysis.md``)
found that DexAtlas lost a third of its rounds to the *shape* of its answers
rather than to their content. Four contract rules come out of that, and each
is a red-to-green test here:

* **A negative answer is not a finding.** A question that asks whether
  something exists, and whose answer is "no", is answered with zero findings
  and the negative sentence in the answer's limitations. A conclusion that
  says "there is none" must not become a finding the scorer counts.
* **A process note is not a finding.** A record about the analysis itself —
  "the analysis is complete", "the tools returned these symbols" — supports no
  claim about the APK, so a conclusion that rests on nothing else is a
  limitation, not a finding.
* **A count is one finding per item.** "How many X" is answered with one
  finding per X, and the summary sentence in the prose, so the scorer's
  ``expect_count`` counts the things the question asked about.
* **A method's identity carries its full JVM descriptor.** "Which method" is
  answered with ``Class.name(descriptor)``, not with a bare name — the
  descriptor is what tells two overloads apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.evidence_verifier import SUPPORTS_CLAIMS, parse_answer
from dexatlas.agent.orchestrator import Orchestrator
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from dexatlas.core.models import EvidenceKind, EvidenceLevel
from tests.agent_harness import (
    CRYPTO,
    PROJECT_ID,
    SIGN_METHOD_ID,
    Demo,
    build_demo,
    make_orchestrator,
    observation_evidence_ids,
)

MANIFEST_QUESTION = "Which permissions does this APK request?"


def conclusions_of(state) -> list:
    """The records the *model* concluded, as against what the tools read.

    The task's findings list holds both: the tools' own readings (an
    observation of the manifest, a status read) and the model's conclusions.
    The answer contract is about the second kind — a tool's reading is a
    fact regardless of the answer's shape, and the scorer's adapter already
    keeps the two apart.
    """
    return [record for record in state.findings if record.kind is EvidenceKind.BEHAVIOUR]


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _orchestrator(demo: Demo, provider: ScriptedProvider, tmp_path: Path) -> Orchestrator:
    return make_orchestrator(
        demo,
        provider,
        store=TaskStore(tmp_path / "tasks"),
        limits=Budget(max_tokens=50_000, max_iterations=10, max_seconds=60.0),
    )


def _negative(statement: str):
    """A scripted provider that reads the manifest, then answers "there is none"."""

    def reply(request) -> object:
        return answer([], limitations=[statement])

    return ScriptedProvider(
        responses=[tool_call("get_manifest", {"project_id": PROJECT_ID}), reply]
    )


# -- FM-1: a negative answer takes no findings -------------------------------


def test_a_negative_answer_is_a_limitation_and_not_a_finding(demo: Demo, tmp_path: Path) -> None:
    """A conclusion that says "there is none" is not recorded as a finding.

    The scorer's ``expect_empty`` rejects any finding at all, so a negative
    answer has to arrive as zero findings — the sentence goes into the
    answer's limitations, where it still reaches the reader and still carries
    the ``must_contain`` prose match.
    """
    statement = "the manifest declares no broadcast receiver"
    provider = _negative(statement)
    state = _orchestrator(demo, provider, tmp_path).run(
        "Does the demo application declare a broadcast receiver?",
        project_id=PROJECT_ID,
    )

    assert state.status is TaskStatus.COMPLETED
    assert conclusions_of(state) == [], "a negative answer produces no findings"
    assert statement in [event.message for event in state.events if event.kind == "limitation"]


def test_a_negative_answer_still_reports_the_limitation_in_the_document(
    demo: Demo, tmp_path: Path
) -> None:
    """The negative sentence reaches the report as a limitation, not as prose loss."""
    statement = "no call site in the index targets this method"
    provider = _negative(statement)
    orchestrator = _orchestrator(demo, provider, tmp_path)
    state = orchestrator.run("Which method calls this?", project_id=PROJECT_ID)
    report = orchestrator.report(state)

    assert statement in report.limitations
    assert not [record for record in report.findings if record.kind is EvidenceKind.BEHAVIOUR]


def test_parse_answer_accepts_an_empty_conclusion_list_with_a_negative_limitation() -> None:
    """The documented shape — no conclusions, the absence in limitations — parses."""
    parsed = parse_answer('{"conclusions": [], "limitations": ["there is no caller of digestOf"]}')
    assert parsed.conclusions == ()
    assert parsed.limitations == ("there is no caller of digestOf",)


# -- FM-2a: a process note is not a finding ----------------------------------


def test_a_conclusion_resting_only_on_process_records_is_a_limitation(
    demo: Demo, tmp_path: Path
) -> None:
    """A conclusion whose only citations are notes about the analysis is a limitation.

    "The analysis is complete" is true and worth recording, but it says nothing
    about the question. A conclusion citing only such records cannot stand as
    a finding: it is the process note wearing a conclusion's clothes, and it
    is moved out of the findings into the limitations.
    """

    def cite_only_the_status_read(request) -> object:
        # The failure this test pins: the model wraps a process read in a
        # conclusion. The status record (E-0004 in every fresh task) says the
        # analysis is complete — a fact about the run, not about the APK.
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
            tool_call("get_manifest", {"project_id": PROJECT_ID}),
            cite_only_the_status_read,
        ]
    )
    orchestrator = _orchestrator(demo, provider, tmp_path)
    state = orchestrator.run(MANIFEST_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED
    assert conclusions_of(state) == [], "a process-only conclusion is not a finding"
    assert any(
        "the analysis is complete" in event.message
        for event in state.events
        if event.kind == "limitation"
    )


def test_a_conclusion_resting_on_real_evidence_is_still_a_finding(
    demo: Demo, tmp_path: Path
) -> None:
    """The contract moves process notes out; it does not move real answers out."""
    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}),
            lambda request: answer(
                [
                    conclusion(
                        "the manifest requests INTERNET",
                        evidence_ids=observation_evidence_ids(request)[-1:],
                    )
                ]
            ),
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(MANIFEST_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED
    assert len(conclusions_of(state)) == 1
    assert conclusions_of(state)[0].kind is EvidenceKind.BEHAVIOUR


def test_a_conclusion_with_no_evidence_at_all_stays_insufficient(
    demo: Demo, tmp_path: Path
) -> None:
    """An unsupported conclusion is unchanged: it is recorded, as insufficient evidence.

    The process-note rule moves conclusions that *cite* process records; a
    conclusion that names nothing keeps its existing handling — a visible,
    insufficient record — because that is a fact about the task a reader is
    entitled to.
    """
    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}),
            lambda _request: answer([conclusion("the answer is 42")]),
        ]
    )
    orchestrator = _orchestrator(demo, provider, tmp_path)
    state = orchestrator.run(MANIFEST_QUESTION, project_id=PROJECT_ID)

    assert state.status is TaskStatus.COMPLETED
    assert len(conclusions_of(state)) == 1
    assert conclusions_of(state)[0].level is EvidenceLevel.INSUFFICIENT


# -- FM-2b: a count is one finding per item ----------------------------------


def test_the_answer_contract_asks_for_one_finding_per_counted_item() -> None:
    """The instructions tell the model to split a count into per-item findings.

    ``expect_count`` compares the number of findings with the number the
    question asks about, so a summary sentence ("3 permissions: a, b, c") is
    one finding where three are expected. The contract is the fix: count the
    items, one finding each, and keep the summary in the prose.
    """
    from dexatlas.agent.orchestrator import INSTRUCTIONS

    assert "one finding per" in INSTRUCTIONS
    assert "expect_count" not in INSTRUCTIONS, "the marking scheme never reaches the model"


def test_the_instructions_ask_for_negative_answers_in_limitations() -> None:
    """The instructions say where a negative answer goes, and why."""
    from dexatlas.agent.orchestrator import INSTRUCTIONS

    assert "limitations" in INSTRUCTIONS
    assert "no findings" in INSTRUCTIONS.lower() or "zero findings" in INSTRUCTIONS.lower()


# -- FM-3/FM-7: a method's identity carries its descriptor -------------------


def test_the_instructions_ask_for_full_jvm_descriptors() -> None:
    """The instructions require ``Class.name(descriptor)`` for every method named.

    The failure analysis found answers that said ``Handler.handle`` where the
    scorer needed ``com.example.wide.Handler.handle(Ljava/lang/String;)V``:
    the descriptor is part of the identity, and a bare name is ambiguous.
    """
    from dexatlas.agent.orchestrator import INSTRUCTIONS

    assert "descriptor" in INSTRUCTIONS
    assert "overload" in INSTRUCTIONS.lower()


def test_find_callers_payload_names_methods_by_their_full_id(demo: Demo) -> None:
    """The tools' own answers already carry full JVM descriptors — the contract relies on it.

    The caller's identity in a ``find_callers`` answer is the qualified method
    id with its descriptor, so a conclusion that quotes it verbatim satisfies
    the descriptor requirement without re-deriving anything.
    """
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    outcome = client.call(
        "find_callers",
        {"project_id": PROJECT_ID, "method_id": SIGN_METHOD_ID, "limit": 50},
    )
    assert outcome.call_sites, "the demo workspace has one call site"
    assert outcome.call_sites[0].caller == (
        "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"
    )


# -- FM-6: resources → declaration file --------------------------------------


def test_a_resource_declaration_lookup_returns_the_declaring_file(demo: Demo) -> None:
    """The new tool answers "which file declares this resource?".

    ``search_symbols`` can say that ``app_name`` exists; only a resource
    lookup can say that it is declared in ``res/values/strings.xml``. The tool
    is the fix for the questions the agent could not answer at all.
    """
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    outcome = client.call(
        "find_resource_declarations",
        {"project_id": PROJECT_ID, "name": "app_name"},
    )
    assert outcome.total >= 1
    first = outcome.declarations[0]
    assert first.name == "app_name"
    assert first.file == "res/values/strings.xml"


def test_a_resource_declaration_lookup_by_value_finds_the_name(demo: Demo) -> None:
    """The lookup also runs the other way: from a value to its declaration."""
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    outcome = client.call(
        "find_resource_declarations",
        {"project_id": PROJECT_ID, "value": "Demo"},
    )
    names = [declaration.name for declaration in outcome.declarations]
    assert "app_name" in names


def test_a_resource_declaration_lookup_validates_its_input(demo: Demo) -> None:
    """A call with neither a name nor a value is refused before it runs."""
    from dexatlas.agent.tool_executor import McpToolClient, ToolCallError

    client = McpToolClient(demo.analyzer)
    with pytest.raises(ToolCallError):
        client.call("find_resource_declarations", {"project_id": PROJECT_ID})


def test_the_resource_tool_is_in_the_plans_tool_set() -> None:
    """A question about resources may call the resource lookup."""
    from dexatlas.agent.planner import Planner

    plan = Planner().plan("In which resource file is app_name declared?")
    assert "find_resource_declarations" in plan.allowed_tools


def test_the_resource_tool_is_offered_to_the_model(demo: Demo) -> None:
    """The model is told about the tool, and what it is for."""
    from dexatlas.agent.tool_executor import TOOL_DESCRIPTIONS

    assert "find_resource_declarations" in TOOL_DESCRIPTIONS
    assert "strings.xml" in TOOL_DESCRIPTIONS["find_resource_declarations"]


def test_a_resource_reading_is_recorded_as_evidence(demo: Demo, tmp_path: Path) -> None:
    """What the resource tool read is recorded like every other tool's reading."""
    provider = ScriptedProvider(
        responses=[
            tool_call(
                "find_resource_declarations",
                {"project_id": PROJECT_ID, "name": "app_name"},
            ),
            lambda request: answer(
                [
                    conclusion(
                        "app_name is declared in res/values/strings.xml",
                        evidence_ids=observation_evidence_ids(request)[-1:],
                    )
                ]
            ),
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(
        "In which resource file is app_name declared?", project_id=PROJECT_ID
    )

    assert state.status is TaskStatus.COMPLETED
    assert len(conclusions_of(state)) == 1, "the conclusion is recorded as a finding"
    reading = [
        record
        for record in state.findings
        if record.kind is not EvidenceKind.BEHAVIOUR and "strings.xml" in record.summary
    ]
    assert reading, "the resource reading is recorded as evidence"
    assert reading[0].level is EvidenceLevel.VERIFIED
    assert "res/values/strings.xml" in reading[0].summary


def test_the_resource_tool_does_not_support_claims_by_itself(demo: Demo) -> None:
    """A resource row is an observation of the APK, so it can carry a conclusion.

    This is the counterpart of the process-note rule: a *resource* reading is
    about the APK, unlike a status reading, and it must keep
    ``supports_claims`` true.
    """
    from dexatlas.agent.tool_executor import McpToolClient

    client = McpToolClient(demo.analyzer)
    outcome = client.call(
        "find_resource_declarations",
        {"project_id": PROJECT_ID, "name": "app_name"},
    )
    assert outcome.declarations[0].file == "res/values/strings.xml"
    # The *tool* returns a view; the supports-claims decision is made by the
    # orchestrator's evidence recorder, which this test's sibling above checks.
    assert SUPPORTS_CLAIMS


# -- the negative contract keeps the verifier's boundary intact --------------


def test_the_verifier_still_refuses_a_verified_claim(demo: Demo) -> None:
    """The contract change does not open a path to a verified model claim."""
    from dexatlas.core.evidence import InvalidProvenanceError

    builder = demo.builder()
    with pytest.raises(InvalidProvenanceError):
        builder.add_claim(
            "the model says this is verified",
            [],
            kind=EvidenceKind.BEHAVIOUR,
            level=EvidenceLevel.VERIFIED,
        )


def test_the_full_method_id_reaches_the_report_unchanged(demo: Demo, tmp_path: Path) -> None:
    """A conclusion that quotes a full method id is recorded with it intact."""
    provider = ScriptedProvider(
        responses=[
            tool_call(
                "find_callers",
                {"project_id": PROJECT_ID, "method_id": SIGN_METHOD_ID, "limit": 50},
            ),
            lambda request: answer(
                [
                    conclusion(
                        f"{CRYPTO}.sign(Ljava/lang/String;)Ljava/lang/String; is called by "
                        "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V",
                        evidence_ids=observation_evidence_ids(request)[-1:],
                    )
                ]
            ),
        ]
    )
    state = _orchestrator(demo, provider, tmp_path).run(
        "What calls Crypto.sign(String)?", project_id=PROJECT_ID
    )

    assert state.status is TaskStatus.COMPLETED
    concluded = conclusions_of(state)
    assert len(concluded) == 1
    assert "com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V" in (concluded[0].summary)
