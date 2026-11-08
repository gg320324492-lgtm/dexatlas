"""The fixed task suite.

A suite is fixed when the same tasks, the same questions and the same
expected answers run on every machine, with no key and no network. That is
what the scripted provider is for: the model asks for the tools the task
needs, and then answers with the evidence the last tool produced — the same
answer every time.

Every task in the suite is checked the same way, and the checks are the
properties the milestone is read against:

* the task finishes, and says that it finished;
* every conclusion names the evidence it rests on;
* that evidence carries a citation, and the citation resolves inside the
  analysis — so a reader can follow it;
* the only tools that were called are the ones the plan allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from dexatlas.agent.orchestrator import Orchestrator
from dexatlas.agent.state import Budget, TaskStatus, TaskStore
from dexatlas.agent.tool_executor import McpToolClient
from dexatlas.core.models import EvidenceLevel
from tests.agent_harness import (
    COLLECT_URL,
    CRYPTO,
    PROJECT_ID,
    SIGN_METHOD_ID,
    Demo,
    build_demo,
    make_orchestrator,
    scripted_provider,
)


@dataclass(frozen=True)
class SuiteTask:
    """One task of the suite."""

    name: str
    question: str
    calls: tuple[tuple[str, dict[str, Any]], ...]
    statement: str
    locator: str
    """The citation the conclusion's evidence has to carry."""


SUITE: tuple[SuiteTask, ...] = (
    SuiteTask(
        name="permissions",
        question="Which permissions does this APK request?",
        calls=(("get_manifest", {"project_id": PROJECT_ID}),),
        statement="the manifest asks for two permissions",
        locator="apktool:AndroidManifest.xml",
    ),
    SuiteTask(
        name="components",
        question="Which components does this APK declare, and which are exported?",
        calls=(("get_manifest", {"project_id": PROJECT_ID}),),
        statement="the manifest declares two components, one of them exported",
        locator="apktool:AndroidManifest.xml",
    ),
    SuiteTask(
        name="string",
        question="Where is the collect URL used in this APK?",
        calls=(
            (
                "search_symbols",
                {"project_id": PROJECT_ID, "query": COLLECT_URL, "limit": 20, "offset": 0},
            ),
        ),
        statement="the index holds the collect URL in MainActivity.onCreate",
        locator="",
    ),
    SuiteTask(
        name="callers",
        question="What calls the sign method that takes a String?",
        calls=(
            ("find_callers", {"project_id": PROJECT_ID, "method_id": SIGN_METHOD_ID, "limit": 50}),
        ),
        statement="the sign method is called from MainActivity.onCreate",
        locator="androguard:classes.dex#com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V",
    ),
    SuiteTask(
        name="source",
        question="Show me the source of the Crypto class.",
        calls=(("get_class_source", {"project_id": PROJECT_ID, "class_name": CRYPTO}),),
        statement="the Crypto class is a decompiled Java class",
        locator="jadx:sources/com/example/demo/Crypto.java",
    ),
    SuiteTask(
        name="evidence",
        question="What evidence does the analysis hold about the manifest?",
        calls=(("get_evidence", {"project_id": PROJECT_ID, "evidence_id": "E-0001"}),),
        statement="the analysis holds a record of the manifest",
        locator="apktool:AndroidManifest.xml",
    ),
)


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    return TaskStore(tmp_path / "tasks")


@pytest.fixture(scope="module")
def analysed_demo(tmp_path_factory: pytest.TempPathFactory):
    """The first-party demo app, really analysed.

    The hand-built workspace is what makes the suite *fixed*; this is the
    other half — the same loop over an analysis that the backends really
    made. The backends may or may not be installed on the machine running
    this, so the tests below assert what holds either way.
    """
    from dexatlas.config.settings import Settings
    from dexatlas.core.pipeline import Analyzer

    demo_apk = Path(__file__).resolve().parent.parent / "examples" / "demo-app" / "demo.apk"
    if not demo_apk.is_file():
        pytest.skip("the demo APK is missing")
    workspace = tmp_path_factory.mktemp("analysed")
    analyzer = Analyzer(Settings(workspace=workspace / "workspace"))
    return analyzer, analyzer.analyze(demo_apk)


def _real_orchestrator(analyzer, result, provider, store: TaskStore) -> Orchestrator:
    """An orchestrator over a real analysis.

    The builder is made from what the analysis recorded: its tool versions,
    the hash of the APK, the workspace its results were published into, and
    the dex files it read. That is what a citation is resolved against.
    """
    from dexatlas.agent.orchestrator import Orchestrator
    from dexatlas.agent.tool_executor import McpToolClient, ToolExecutor
    from dexatlas.core.evidence import EvidenceBuilder

    client = McpToolClient(analyzer)
    project = analyzer.store.get_project(result.project.id)
    assert project is not None
    published = analyzer.store.get_workspace(result.project.id)

    def builder_for(_project_id: str) -> EvidenceBuilder:
        return EvidenceBuilder(
            project_id=project.id,
            tool_versions=dict(project.tool_versions),
            apk_sha256=project.apk.sha256,
            workspace=published,
            dex_files=list(project.apk.dex_files),
        )

    return Orchestrator(
        provider=provider,
        client=client,
        builder_for=builder_for,
        store=store,
        executor=ToolExecutor(client, timeout=30.0),
        limits=Budget(max_tokens=4000, max_iterations=6, max_seconds=120.0),
    )


def _resolves(demo: Demo, locator: str) -> bool:
    """Whether a locator resolves inside the analysis, as a reader would ask."""
    client = McpToolClient(demo.analyzer)
    resolution = client.call("resolve_locator", {"project_id": PROJECT_ID, "locator": locator})
    return bool(resolution.resolved)


@pytest.mark.parametrize("task", SUITE, ids=lambda task: task.name)
def test_the_agent_answers_the_task_with_evidence_behind_it(
    demo: Demo, store: TaskStore, task: SuiteTask
) -> None:
    """Every task in the suite is answered, and the answer can be checked."""
    provider = scripted_provider(list(task.calls), statement=task.statement)
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run(task.question, project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert state.error is None

    conclusions = [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED]
    assert len(conclusions) == 1, "the task answered with one conclusion"
    conclusion = conclusions[0]
    assert conclusion.level is EvidenceLevel.LEAD, (
        "a conclusion the tools back is a lead: it is the model's reading of a fact, "
        "not a fact in its own right"
    )
    assert conclusion.detail["evidence_ids"], "the conclusion names the evidence it rests on"

    cited = conclusion.detail["evidence_ids"]
    for evidence_id in cited:
        assert any(item.id == evidence_id for item in state.findings), (
            f"the conclusion cites {evidence_id}, which this task did not record"
        )

    for item in state.findings:
        for entry in item.provenance:
            assert _resolves(demo, entry.locator), (
                f"{entry.locator} does not resolve inside the analysis, so a reader could "
                "not follow the citation"
            )

    if task.locator:
        assert any(
            entry.locator == task.locator for item in state.findings for entry in item.provenance
        ), f"the task's findings do not cite {task.locator}"


@pytest.mark.parametrize("task", SUITE, ids=lambda task: task.name)
def test_the_agent_only_calls_the_tools_its_plan_allowed(
    demo: Demo, store: TaskStore, task: SuiteTask
) -> None:
    """The agent has no way to reach past the plan it was given."""
    provider = scripted_provider(list(task.calls), statement=task.statement)
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run(task.question, project_id=demo.project_id)

    plan = state.plan
    assert plan is not None
    allowed = set(plan.allowed_tools)
    called = {record.tool for record in state.tool_calls}
    assert called <= allowed | {"resolve_locator"}, (
        f"the agent called {sorted(called - allowed)}, which the plan does not allow"
    )
    for record in state.tool_calls:
        assert record.arguments.get("project_id", PROJECT_ID) == PROJECT_ID, (
            "every call was about the project the task is about"
        )


def test_the_agent_says_what_it_could_not_settle(demo: Demo, store: TaskStore) -> None:
    """A question the analysis cannot answer is answered as such.

    The task is not allowed to end in a finding it cannot back, and it is not
    allowed to end in silence either: the reader is told what could not be
    settled.
    """
    from dexatlas.agent.providers.scripted import ScriptedProvider, answer

    provider = ScriptedProvider(
        responses=[
            answer(
                [],
                limitations=[
                    "the analysis holds no source for com.example.demo.NotThere, "
                    "so it cannot say what that class does"
                ],
            )
        ]
    )
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run("What does com.example.demo.NotThere do?", project_id=demo.project_id)

    assert state.status is TaskStatus.COMPLETED
    assert not [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED], (
        "the task reported no conclusion it could not back"
    )
    report = orchestrator.report(state)
    assert any("NotThere" in limitation for limitation in report.limitations), (
        "the report says what could not be settled"
    )


def test_a_user_can_watch_the_task_happen(demo: Demo, tmp_path: Path) -> None:
    """The progress is visible while the task runs, and it does not lie.

    Every event says what happened, and the task only says it finished when
    it has: an event that claimed a completion before the answer was in
    would be the same claim the report is forbidden to make.
    """
    events: list[Any] = []
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(
        demo, provider, store=TaskStore(tmp_path / "tasks"), progress=events.append
    )

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    kinds = [event.kind for event in events]
    assert "plan_ready" in kinds
    assert "tool_call" in kinds
    assert "finding" in kinds
    assert kinds[-1] == "finished", "the last thing a user is told is that the task finished"
    assert "finished" not in kinds[:-1], "the task said it finished before it had"
    assert state.status is TaskStatus.COMPLETED


def test_the_agent_reads_the_status_of_the_analysis_before_it_answers(
    demo: Demo, store: TaskStore
) -> None:
    """A count is only as good as the analysis behind it.

    The plan's first step is always the status, so the agent knows whether
    the analysis it is reading was complete.
    """
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(demo, provider, store=store)

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    first = state.tool_calls[0]
    assert first.tool == "get_project_status", "the status is read first"
    assert first.ok

    completeness = [item for item in state.findings if "missing_backends" in item.detail]
    assert completeness, "the status was recorded as evidence"
    assert completeness[0].detail["missing_backends"] == [], (
        "this analysis was complete, and the record says so"
    )


def test_the_agent_works_against_a_real_analysis(analysed_demo, tmp_path: Path) -> None:
    """The same loop, over an analysis the backends really made.

    The hand-built workspace is what makes the suite fixed; this is the other
    half. The backends may or may not be installed on the machine running
    this, so what is asserted is what holds either way: the task finishes,
    the status is read first, and every citation the report carries resolves
    inside the analysis.
    """
    analyzer, result = analysed_demo
    project_id = result.project.id
    provider = scripted_provider(
        [(("get_manifest", {"project_id": project_id}))], statement="the manifest says so"
    )
    orchestrator = _real_orchestrator(analyzer, result, provider, TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=project_id)

    assert state.status is TaskStatus.COMPLETED, state.error
    assert state.project_id == project_id
    assert state.tool_calls[0].tool == "get_project_status"

    client = McpToolClient(analyzer)
    for item in state.findings:
        for entry in item.provenance:
            resolution = client.call(
                "resolve_locator", {"project_id": project_id, "locator": entry.locator}
            )
            assert resolution.resolved, (
                f"{entry.locator} does not resolve inside the real analysis, so a reader "
                "could not follow the citation"
            )


def test_the_agent_answers_about_a_real_analysis(analysed_demo, tmp_path: Path) -> None:
    """The answer about a real analysis is a lead, or it says it could not answer.

    Which of the two it is depends on whether the manifest could be read,
    and both are correct answers: a conclusion with nothing behind it is
    recorded as insufficient evidence, never as a finding.
    """
    analyzer, result = analysed_demo
    project_id = result.project.id
    provider = scripted_provider(
        [(("get_manifest", {"project_id": project_id}))], statement="the manifest says so"
    )
    orchestrator = _real_orchestrator(analyzer, result, provider, TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=project_id)

    conclusions = [item for item in state.findings if item.level is not EvidenceLevel.VERIFIED]
    assert len(conclusions) == 1
    conclusion = conclusions[0]

    manifest_read = any(record.tool == "get_manifest" and record.ok for record in state.tool_calls)
    if manifest_read:
        assert conclusion.level is EvidenceLevel.LEAD, "a conclusion the manifest backs is a lead"
        assert conclusion.detail["evidence_ids"], "the conclusion names its evidence"
    else:
        assert conclusion.level is EvidenceLevel.INSUFFICIENT, (
            "the analysis could not answer, and the report says so"
        )
        assert "no evidence behind it" in conclusion.summary
