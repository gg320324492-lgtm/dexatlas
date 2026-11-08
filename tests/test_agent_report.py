"""The agent's report is the project's report format, filled in.

The report format was written in Phase 1 and it is the deliverable, so the
agent does not invent a second one: the same evidence model, the same table,
the same words about what the levels mean. What is new is the *separation* —
established facts, leads and insufficient evidence are three sections rather
than one list, because a reader has to be able to tell them apart.

And the status line is the honest one: a task that did not finish says that
it did not finish.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.agent.reporter import (
    EVIDENCE_TABLE_HEADER,
    AgentReport,
    build_agent_json,
    render_agent_markdown,
)
from dexatlas.agent.state import TaskStatus, TaskStore
from dexatlas.core.models import (
    ApkMetadata,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    Project,
    ProjectStatus,
)
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.reports.markdown import render_markdown
from tests.agent_harness import (
    PROJECT_ID,
    Demo,
    build_demo,
    make_orchestrator,
    scripted_provider,
)


@pytest.fixture
def demo(settings, tmp_path: Path) -> Demo:
    return build_demo(settings, tmp_path)


def _level_rows(markdown: str) -> list[str]:
    """The rows of the evidence-level table, whichever document they are in."""
    rows = []
    for line in markdown.splitlines():
        if line.startswith("| `") and "|" in line[3:] and "---" not in line:
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) == 3 and parts[0].startswith("`"):
                rows.append(line)
    return rows


def test_the_agent_report_uses_the_evidence_table_of_the_analysis_report() -> None:
    """The two reports are read the same way.

    The table is the analysis report's table: the same columns, the same
    header. A reader who has read one knows how to read the other.
    """
    project = Project(
        id="apk_one",
        apk=ApkMetadata(sha256="a" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        tool_versions={"jadx": "1.5.0"},
    )
    analysis = render_markdown(
        AnalysisResult(
            project=project,
            manifest=None,
            evidence=[
                Evidence(
                    id="E-0001",
                    kind=EvidenceKind.OBSERVATION,
                    level=EvidenceLevel.VERIFIED,
                    summary="something was read",
                )
            ],
        )
    )

    report = AgentReport(
        task_id="task-1",
        question="Which permissions does this APK request?",
        status=TaskStatus.COMPLETED,
        findings=[
            Evidence(
                id="E-0001",
                kind=EvidenceKind.OBSERVATION,
                level=EvidenceLevel.VERIFIED,
                summary="something was read",
            )
        ],
    )
    agent = render_agent_markdown(report)

    assert EVIDENCE_TABLE_HEADER in analysis
    assert EVIDENCE_TABLE_HEADER in agent


def test_the_two_reports_say_the_same_thing_about_the_levels() -> None:
    """The wording about the levels is the project's, not the agent's.

    The words are read out of the analysis report rather than written down
    here, so a change to one is a change to both — and the test is what
    notices.
    """
    project = Project(
        id="apk_one",
        apk=ApkMetadata(sha256="a" * 64, size_bytes=1, path=Path("demo.apk")),
        status=ProjectStatus.COMPLETED,
        tool_versions={"jadx": "1.5.0"},
    )
    analysis = render_markdown(AnalysisResult(project=project, manifest=None, evidence=[]))
    agent = render_agent_markdown(
        AgentReport(
            task_id="task-1",
            question="Which permissions does this APK request?",
            status=TaskStatus.COMPLETED,
        )
    )

    assert _level_rows(analysis) == _level_rows(agent)


def test_the_report_separates_what_was_established_from_what_was_only_suspected() -> None:
    """Three sections, because a reader has to be able to tell them apart."""
    established = Evidence(
        id="E-0001",
        kind=EvidenceKind.OBSERVATION,
        level=EvidenceLevel.VERIFIED,
        summary="the manifest declares two permissions",
    )
    lead = Evidence(
        id="E-0002",
        kind=EvidenceKind.BEHAVIOUR,
        level=EvidenceLevel.LEAD,
        summary="the app may be tracking the user",
    )
    insufficient = Evidence(
        id="E-0003",
        kind=EvidenceKind.BEHAVIOUR,
        level=EvidenceLevel.INSUFFICIENT,
        summary="the app is safe",
    )
    report = AgentReport(
        task_id="task-1",
        question="Is the app safe?",
        status=TaskStatus.COMPLETED,
        findings=(established, lead, insufficient),
    )

    markdown = render_agent_markdown(report)

    assert "## Established facts" in markdown
    assert "## Leads" in markdown
    assert "## Insufficient evidence" in markdown
    assert markdown.index("## Established facts") < markdown.index("## Leads")
    assert markdown.index("## Leads") < markdown.index("## Insufficient evidence")
    assert "E-0001" in markdown
    assert "E-0002" in markdown
    assert "E-0003" in markdown


def test_a_task_that_did_not_finish_says_so(demo: Demo, tmp_path: Path) -> None:
    """The status line is the honest one."""
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)
    markdown = render_agent_markdown(orchestrator.report(state))

    assert "**Status:** completed" in markdown
    assert "did not finish" not in markdown

    state.status = TaskStatus.BUDGET_EXHAUSTED
    state.error = "the iteration budget is spent: 2 of 2 used"
    markdown = render_agent_markdown(orchestrator.report(state))

    assert "did not finish" in markdown
    assert "ran out of budget" in markdown


def test_the_json_report_carries_the_findings_the_budget_and_the_tool_log(
    demo: Demo, tmp_path: Path
) -> None:
    """The machine-readable form has what a reader needs to check it."""
    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)
    document = build_agent_json(orchestrator.report(state))

    assert document["kind"] == "agent_report"
    assert document["schema_version"] == 1
    assert document["task"]["question"] == "Which permissions does this APK request?"
    assert document["task"]["project_id"] == PROJECT_ID
    assert document["findings"], "the report carries the findings"
    for finding in document["findings"]:
        assert set(finding) >= {"id", "kind", "level", "summary", "provenance"}
    assert document["tool_calls"], "the report carries the tool log"
    assert document["budget"]["used"]["iterations"] >= 1
    assert document["budget"]["limits"]["max_iterations"] > 0


def test_the_report_carries_the_analysis_it_was_about(demo: Demo, tmp_path: Path) -> None:
    """The agent's report can carry the analysis report beside it.

    The analysis document is nested rather than merged, so the contract it
    has always had is untouched.
    """
    from dexatlas.core.models import ManifestInfo

    provider = scripted_provider(
        [(("get_manifest", {"project_id": PROJECT_ID}))], statement="the manifest says so"
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))
    state = orchestrator.run("Which permissions does this APK request?", project_id=demo.project_id)

    project = demo.analyzer.store.get_project(PROJECT_ID)
    assert project is not None
    result = AnalysisResult(
        project=project,
        manifest=ManifestInfo(package="com.example.demo"),
        evidence=list(demo.evidence),
        workspace=demo.workspace,
    )
    report = orchestrator.report(state)
    document = build_agent_json(
        AgentReport(
            task_id=report.task_id,
            question=report.question,
            status=report.status,
            project_id=report.project_id,
            run_id=report.run_id,
            findings=report.findings,
            tool_calls=report.tool_calls,
            analysis=result,
        )
    )

    assert document["analysis"] is not None
    assert document["analysis"]["schema_version"] == 2
    assert document["analysis"]["project"]["id"] == PROJECT_ID


def test_the_report_says_what_the_agent_asked(demo: Demo, tmp_path: Path) -> None:
    """The tool log carries the arguments.

    A reader who wants to reproduce a conclusion has to know what the agent
    asked: "which query?" and "which method?" are the difference between a
    check and a guess.
    """
    from tests.agent_harness import COLLECT_URL, scripted_provider

    provider = scripted_provider(
        [
            (
                "search_symbols",
                {"project_id": PROJECT_ID, "query": COLLECT_URL, "limit": 20, "offset": 0},
            )
        ],
        statement="the collect URL is in the index",
    )
    orchestrator = make_orchestrator(demo, provider, store=TaskStore(tmp_path / "tasks"))

    state = orchestrator.run("Where is the collect URL used?", project_id=demo.project_id)
    markdown = render_agent_markdown(orchestrator.report(state))

    assert "search_symbols" in markdown
    assert "query=" in markdown
    assert "collect" in markdown
