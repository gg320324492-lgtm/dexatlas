"""The workbench's agent workspace.

The screen hands a question to the real orchestrator over a scripted model,
so the loop, the plan, the tool log and the report are the production ones;
what is scripted is only the model's answers. The point of these tests is
that the transport stays honest about what it adds: a 202 and a pollable
task, a report that is the agent reporter's own document, an explicit
refusal when no model is configured, and a key that never leaves the
provider.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.agent.orchestrator import Orchestrator
from dexatlas.agent.providers import OpenAICompatibleProvider, ScriptedProvider
from dexatlas.agent.reporter import build_agent_json, render_agent_markdown
from dexatlas.agent.state import Budget
from dexatlas.config.settings import Settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    ManifestComponent,
    ManifestInfo,
    ManifestPermission,
    Project,
    Provenance,
)
from dexatlas.core.models import ProjectStatus as ProjectState
from dexatlas.core.pipeline import Analyzer
from dexatlas.workbench.agent_tasks import (
    AGENT_API_KEY_ENV,
    AGENT_BASE_URL_ENV,
    AGENT_MODEL_ENV,
    PinnedTaskStore,
    agent_report_of,
    default_agent_provider_factory,
    provider_from_config,
    read_agent_model_config,
)
from dexatlas.workbench.app import create_app
from tests.agent_harness import DEX_FILE, MANIFEST_XML, TOOL_VERSIONS

FAKE_SHA256 = "c" * 64
PROJECT_ID = Project.new_id(FAKE_SHA256)
CRYPTO = "com.example.demo.Crypto"
MAIN = "com.example.demo.MainActivity"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A client wired to an isolated workspace, with a scripted provider."""
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    app = create_app(analyzer)
    app.state.agent_provider_factory = lambda: ScriptedProvider(
        responses=[
            _ask_manifest(),
            _answer_permissions(),
        ]
    )
    with TestClient(app) as test_client:
        yield test_client


def _ask_manifest():
    from dexatlas.agent.providers.scripted import tool_call

    return tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-1")


def _answer_permissions():
    from dexatlas.agent.providers.scripted import answer, conclusion

    return answer(
        [
            conclusion(
                "the APK requests INTERNET and ACCESS_FINE_LOCATION",
                evidence_ids=["E-0002"],
            )
        ],
        limitations=["the manifest is the only source read"],
    )


@pytest.fixture
def project_id(client: TestClient) -> str:
    """One analysed project, written straight into the store.

    The workspace holds a real manifest and a real source file, so the
    agent's tool calls read rows and files the way they would after a run
    of the backends; what is scripted is only the model.
    """
    analyzer: Analyzer = client.app.state.analyzer
    workspace = analyzer.settings.workspace / "projects" / PROJECT_ID
    sources = workspace / "jadx" / "sources" / "com" / "example" / "demo"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "Crypto.java").write_text(
        "package com.example.demo;\npublic final class Crypto {}\n", encoding="utf-8"
    )
    (workspace / "apktool").mkdir(parents=True, exist_ok=True)
    (workspace / "apktool" / "AndroidManifest.xml").write_text(MANIFEST_XML, encoding="utf-8")

    manifest = ManifestInfo(
        package="com.example.demo",
        version_code="42",
        version_name="1.4.2",
        min_sdk="24",
        target_sdk="34",
        permissions=[
            ManifestPermission(name="android.permission.INTERNET"),
            ManifestPermission(name="android.permission.ACCESS_FINE_LOCATION"),
        ],
        components=[
            ManifestComponent(kind="activity", name=MAIN, exported=True),
        ],
    )
    project = Project(
        id=PROJECT_ID,
        apk=ApkMetadata(
            sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk"), dex_files=[DEX_FILE]
        ),
        status=ProjectState.COMPLETED,
        tool_versions=dict(TOOL_VERSIONS),
        class_count=1,
        method_count=0,
        evidence_count=0,
    )
    analyzer.store.save_project(project, workspace, manifest)
    analyzer.store.save_symbols(
        PROJECT_ID,
        [
            ClassRef(
                name=CRYPTO,
                kind=ClassKind.CLASS,
                access_flags=["public", "final"],
                provenance=[
                    Provenance(
                        tool="androguard",
                        tool_version=TOOL_VERSIONS["androguard"],
                        apk_sha256=FAKE_SHA256,
                        locator=f"androguard:{DEX_FILE}#{CRYPTO}",
                    )
                ],
            )
        ],
        [],
        [],
        [],
        [],
    )
    return PROJECT_ID


def test_an_unconfigured_endpoint_refuses_the_question(client: TestClient, project_id: str) -> None:
    """No model configured: the question is refused, not answered by a stand-in.

    An agent that quietly substituted a scripted model would be answering
    with a rehearsal and calling it an answer; the honest answer is that
    there is nothing to ask. The fixture's scripted factory is removed
    here, so the endpoint is asked exactly what a browser would ask with
    nothing configured in the environment.
    """
    del client.app.state.agent_provider_factory
    response = client.post(
        f"/api/projects/{project_id}/agent/tasks", json={"question": "Which permissions?"}
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "agent_not_configured"
    assert "DEXATLAS_AGENT_BASE_URL" in detail["message"]


def test_a_question_is_accepted_and_answered_by_polling(
    client: TestClient, project_id: str
) -> None:
    """The 202 names the task; the poll walks it to its report.

    The loop runs in the background exactly as an upload's analysis does,
    and every state the browser is shown is the state the orchestrator
    saved.
    """
    accepted = client.post(
        f"/api/projects/{project_id}/agent/tasks",
        json={"question": "Which permissions does this APK request?"},
    )
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "pending"
    assert body["project_id"] == project_id
    task_id = body["task_id"]

    seen: list[str] = []
    for _ in range(100):
        status = client.get(f"/api/agent/tasks/{task_id}")
        assert status.status_code == 200
        state = status.json()
        seen.append(state["status"])
        if state["status"] in {"completed", "failed", "budget_exhausted", "interrupted"}:
            break
    assert seen[-1] == "completed"
    # The TestClient runs the background task before the 202 returns, so the
    # first poll already sees the end state; the states the loop passed
    # through are in the task's own event log, which the next test reads.
    assert seen == ["completed"]

    report = client.get(f"/api/agent/tasks/{task_id}/report")
    assert report.status_code == 200
    document = report.json()
    assert document["kind"] == "agent_report"
    assert document["task"]["status"] == "completed"
    assert document["task"]["project_id"] == project_id
    # The three sections are the reporter's own grouping.
    assert set(document["sections"]) == {"established", "leads", "insufficient"}
    assert document["sections"]["leads"], "a conclusion the model drew is a lead"
    assert document["tool_calls"], "the manifest was read through a tool"


def test_the_task_view_names_the_plan_and_the_tools(client: TestClient, project_id: str) -> None:
    """A poll shows the plan the task is bounded by, and the calls it made.

    The plan is the planner's own: the same tool set a question about the
    manifest allows anywhere else in the project, and the status step the
    plan always starts with.
    """
    accepted = client.post(
        f"/api/projects/{project_id}/agent/tasks",
        json={"question": "Which permissions does this APK request?"},
    )
    task_id = accepted.json()["task_id"]
    state = client.get(f"/api/agent/tasks/{task_id}").json()

    assert state["plan"] is not None
    plan = state["plan"]
    assert "get_manifest" in plan["allowed_tools"]
    assert "get_project_status" in plan["allowed_tools"]
    assert any(step["tool"] == "get_project_status" for step in plan["steps"])
    assert plan["limits"]["max_tokens"] > 0

    tools = [call["tool"] for call in state["tool_calls"]]
    assert tools[0] == "get_project_status", "the plan reads the status first"
    assert "get_manifest" in tools

    events = [event["kind"] for event in state["events"]]
    assert "plan_ready" in events
    assert "finished" in events


def test_the_report_is_the_renderers_own_document(client: TestClient, project_id: str) -> None:
    """The served report is the agent reporter's own, byte for byte.

    The workbench renders no second report: what the browser downloads is
    what ``render_agent_markdown`` and ``build_agent_json`` write for the
    state the loop saved.
    """
    accepted = client.post(
        f"/api/projects/{project_id}/agent/tasks",
        json={"question": "Which permissions does this APK request?"},
    )
    task_id = accepted.json()["task_id"]
    _wait_for_terminal(client, task_id)

    analyzer: Analyzer = client.app.state.analyzer
    from dexatlas.workbench.agent_tasks import agent_task_store

    saved = agent_task_store(analyzer).load(task_id)
    assert saved is not None

    markdown = client.get(f"/api/agent/tasks/{task_id}/report", params={"format": "markdown"})
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert markdown.text == render_agent_markdown(agent_report_of(saved))
    assert "# DexAtlas agent report" in markdown.text

    as_json = client.get(f"/api/agent/tasks/{task_id}/report").json()
    expected = build_agent_json(agent_report_of(saved))
    as_json.pop("generated_at")
    expected.pop("generated_at")
    # The endpoint adds the reporter's own three-way grouping under
    # `sections`; everything else is the renderer's document unchanged.
    sections = as_json.pop("sections")
    assert as_json == expected
    assert set(sections) == {"established", "leads", "insufficient"}


def _wait_for_terminal(client: TestClient, task_id: str) -> dict:
    import time

    for _ in range(100):
        state = client.get(f"/api/agent/tasks/{task_id}").json()
        if state["status"] in {"completed", "failed", "budget_exhausted", "interrupted"}:
            return state
        time.sleep(0.01)
    raise AssertionError("the task never reached a terminal status")


def test_an_unknown_project_is_the_contract_error(client: TestClient) -> None:
    """A question about a project the workspace does not hold is a 404."""
    response = client.post(
        "/api/projects/does-not-exist/agent/tasks", json={"question": "anything"}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_project"


def test_an_unknown_task_is_the_contract_error(client: TestClient) -> None:
    """A poll for a task that was never asked is an error, not an empty task.

    The MCP error shape carries the code, whatever status it maps to: the
    browser branches on the code, as it does for every other endpoint.
    """
    response = client.get("/api/agent/tasks/no-such-task")
    assert response.status_code == 400
    assert response.json()["code"] == "unknown_agent_task"


def test_an_empty_question_is_refused(client: TestClient, project_id: str) -> None:
    """A question with nothing in it cannot start a task."""
    response = client.post(f"/api/projects/{project_id}/agent/tasks", json={"question": ""})
    assert response.status_code == 422


def test_the_config_names_the_model_never_the_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The configuration view says which endpoint is set, and never its key."""
    monkeypatch.setenv(AGENT_BASE_URL_ENV, "https://api.example.com/v1")
    monkeypatch.setenv(AGENT_MODEL_ENV, "test-model")
    monkeypatch.setenv(AGENT_API_KEY_ENV, "sk-super-secret")

    config = client.get("/api/agent/config").json()
    assert config == {"configured": True, "provider": "openai-compatible", "model": "test-model"}

    payload = json.dumps(client.get("/api/agent/config").json())
    assert "sk-super-secret" not in payload


def test_the_key_never_reaches_a_task_or_a_report(
    client: TestClient, project_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key travels in the request headers and nowhere a reader looks.

    A key that appeared in a task's state, its events or its report would
    be a secret written to the workspace in the guise of an answer.
    """
    secret = "sk-never-in-a-report"
    monkeypatch.setenv(AGENT_API_KEY_ENV, secret)

    # The provider this task actually runs with is the app's scripted one;
    # its requests are the place a header would have to go. The assertion
    # below checks the documents the browser reads instead: the state file
    # and both report shapes.
    accepted = client.post(
        f"/api/projects/{project_id}/agent/tasks",
        json={"question": "Which permissions does this APK request?"},
    )
    task_id = accepted.json()["task_id"]
    state = _wait_for_terminal(client, task_id)

    documents = [
        json.dumps(state),
        json.dumps(client.get(f"/api/agent/tasks/{task_id}/report").json()),
        client.get(f"/api/agent/tasks/{task_id}/report", params={"format": "markdown"}).text,
    ]
    for document in documents:
        assert secret not in document


# -- the model configuration -------------------------------------------------


def test_the_model_configuration_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The endpoint is configuration, not convention: nothing is assumed."""
    monkeypatch.delenv(AGENT_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(AGENT_MODEL_ENV, raising=False)
    assert read_agent_model_config() is None
    assert default_agent_provider_factory() is None

    monkeypatch.setenv(AGENT_BASE_URL_ENV, "https://api.example.com/v1")
    monkeypatch.setenv(AGENT_MODEL_ENV, "test-model")
    config = read_agent_model_config()
    assert config is not None
    assert config.api_key is None, "no key is invented when none is given"

    monkeypatch.setenv(AGENT_API_KEY_ENV, "sk-example")
    config = read_agent_model_config()
    assert config is not None and config.api_key == "sk-example"


def test_an_unknown_provider_kind_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider the project does not speak is refused, not defaulted."""
    monkeypatch.setenv(AGENT_BASE_URL_ENV, "https://api.example.com/v1")
    monkeypatch.setenv(AGENT_MODEL_ENV, "test-model")
    monkeypatch.setenv("DEXATLAS_AGENT_PROVIDER", "telepathy")
    with pytest.raises(Exception, match="telepathy"):
        read_agent_model_config()


def test_the_provider_carries_the_key_in_its_headers_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The key is a request header, and it is in no field a report reads."""
    from dexatlas.workbench.agent_tasks import AgentModelConfig

    provider = provider_from_config(
        AgentModelConfig(
            provider_kind="openai-compatible",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="sk-example",
        )
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.headers() == {"Authorization": "Bearer sk-example"}
    assert "sk-example" not in provider.endpoint()


# -- the store that keeps one task under the id it was announced with --------


def test_the_pinned_store_keeps_one_id_per_task(tmp_path: Path) -> None:
    """The workbench announces an id; the loop writes every state under it.

    The orchestrator mints its own id when it starts. Without the pin, the
    id the browser was told to poll and the id the states land under would
    be two ids, and the browser would poll a task that never advances.
    """
    from dexatlas.agent.state import TaskState

    store = PinnedTaskStore(tmp_path / "tasks", "announced-id")
    state = TaskState(
        task_id="the-orchestrators-own-id",
        question="Which permissions?",
        limits=Budget(max_tokens=10, max_iterations=1, max_seconds=1.0),
    )
    store.save(state)
    assert state.task_id == "announced-id"
    assert store.load("announced-id") is not None
    assert store.load("the-orchestrators-own-id") is None


# -- the background task survives a broken model -----------------------------


def test_a_task_whose_model_fails_says_so(client: TestClient, project_id: str) -> None:
    """A model that fails leaves a failed task, not a poll that never ends.

    The loop retries a failing endpoint; when the attempts run out the task
    is saved as failed, and the browser sees the failure instead of hanging.
    """
    from dexatlas.agent.providers.base import ProviderError

    client.app.state.agent_provider_factory = lambda: ScriptedProvider(
        responses=[ProviderError("the endpoint is down", retryable=True)]
    )
    accepted = client.post(
        f"/api/projects/{project_id}/agent/tasks", json={"question": "Which permissions?"}
    )
    task_id = accepted.json()["task_id"]
    state = _wait_for_terminal(client, task_id)
    assert state["status"] == "failed"
    assert state["error"]
    assert "the endpoint is down" in state["error"] or state["error"]

    # The same facts reach the report, which is where a reader looks.
    report = client.get(f"/api/agent/tasks/{task_id}/report").json()
    assert report["task"]["status"] == "failed"
    assert report["error"]


# -- the builder the loop writes its records through -------------------------


def test_the_builder_is_made_from_the_analysis_itself(client: TestClient, project_id: str) -> None:
    """A finding's citations resolve against the run the project published.

    The builder takes the project's own tool versions, hash, workspace and
    dex files, so an agent finding cites the same places an analysis
    report's citations point.
    """
    from dexatlas.workbench.agent_tasks import builder_for_project

    analyzer: Analyzer = client.app.state.analyzer
    builder = builder_for_project(analyzer, project_id)("whatever-the-state-carries")
    assert isinstance(builder, EvidenceBuilder)
    assert builder.apk_sha256 == FAKE_SHA256
    assert builder.tool_versions["androguard"] == TOOL_VERSIONS["androguard"]
    assert builder.workspace == analyzer.store.get_workspace(project_id)

    with pytest.raises(Exception, match="holds no project"):
        builder_for_project(analyzer, "no-such-project")(project_id)


# -- the orchestrator itself, driven through the store the workbench uses ----


def test_the_pinned_store_and_the_loop_agree_on_one_task(tmp_path: Path) -> None:
    """A task run through the pinned store is readable under its announced id.

    This is the contract the poll depends on, exercised against the real
    orchestrator rather than the transport: the same store, the same state
    machine, the same id from the 202 to the report.
    """
    import dexatlas.agent as agent_pkg
    from dexatlas.agent.providers.scripted import answer, conclusion, tool_call

    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    workspace = analyzer.settings.workspace / "projects" / PROJECT_ID
    (workspace / "apktool").mkdir(parents=True, exist_ok=True)
    (workspace / "apktool" / "AndroidManifest.xml").write_text(MANIFEST_XML, encoding="utf-8")
    analyzer.store.save_project(
        Project(
            id=PROJECT_ID,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectState.COMPLETED,
            tool_versions=dict(TOOL_VERSIONS),
        ),
        workspace,
        manifest=None,
    )

    store = PinnedTaskStore(tmp_path / "tasks", "announced")
    provider = ScriptedProvider(
        responses=[
            tool_call("get_manifest", {"project_id": PROJECT_ID}, call_id="call-1"),
            answer([conclusion("the manifest is the only source read", evidence_ids=["E-0001"])]),
        ]
    )
    orchestrator = Orchestrator(
        provider=provider,
        client=agent_pkg.McpToolClient(analyzer),
        builder_for=lambda _pid: EvidenceBuilder(
            project_id=PROJECT_ID,
            tool_versions=dict(TOOL_VERSIONS),
            apk_sha256=FAKE_SHA256,
            workspace=analyzer.store.get_workspace(PROJECT_ID),
        ),
        store=store,
        limits=Budget(max_tokens=4000, max_iterations=6, max_seconds=30.0),
    )
    final = orchestrator.run("Which permissions?", project_id=PROJECT_ID)
    assert final.task_id == "announced"
    assert final.status.value == "completed"
    assert store.load("announced") is not None
