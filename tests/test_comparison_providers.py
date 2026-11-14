"""M3 三配置在真实 provider 下的端到端.

``tests/test_comparison_metrics.py`` 由主会话维护,这里不动它. 这份测试
管另一段:run.py 的 provider 选择把 ``OpenAICompatibleProvider`` 接进三个
配置之后,trace 里的 token 必须是端点在 ``usage`` 里上报的数——scripted
替身用 ``len(text.split())`` 估算,真实 provider 时那条估算路径必须被
绕开. 假端点上报 911/137 这两个估算不可能凑出来的数,断言就写在这两个
数上;key 走环境变量,只进请求头,不进任何落盘的东西.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from benchmarks.comparison.metrics import compare
from benchmarks.comparison.model import Question, SystemKind, TaskTrace
from benchmarks.comparison.run import _provider_factory, _questions, _score, _sources
from benchmarks.comparison.systems import (
    AgentSystem,
    SourceTextSystem,
    StructuredSystem,
    System,
)

from dexatlas.agent.providers.base import ModelProvider
from dexatlas.agent.providers.local import LocalModelProvider
from dexatlas.agent.providers.openai_compat import OpenAICompatibleProvider

#: 假端点上报的 usage. 这两个数是刻意选的:任何 ``len(text.split())`` 之
#: 类的估算都凑不出它们,所以断言成立就证明 token 来自上报值.
PROMPT_TOKENS = 911
COMPLETION_TOKENS = 137
ENDPOINT_MODEL = "bench-model"
API_KEY_ENV = "DEXATLAS_BENCH_TEST_API_KEY"
API_KEY = "k-bench-never-on-disk"

_ANSWER = json.dumps(
    {
        "conclusions": [
            {
                "statement": "The sample declares the INTERNET permission in its manifest.",
                "evidence_ids": [],
                "locators": [],
            }
        ],
        "limitations": ["answered from a fixed document, not from an observation"],
    }
)


@dataclass
class FakeEndpoint:
    """固定 chat-completion 响应的假端点;记下收到的每个请求."""

    calls: list[tuple[str, dict[str, Any], dict[str, str]]] = field(default_factory=list)

    def __call__(
        self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
    ) -> dict[str, Any]:
        self.calls.append((url, payload, dict(headers)))
        return {
            "model": ENDPOINT_MODEL,
            "choices": [{"message": {"role": "assistant", "content": _ANSWER}}],
            "usage": {"prompt_tokens": PROMPT_TOKENS, "completion_tokens": COMPLETION_TOKENS},
        }


def _provider(endpoint: FakeEndpoint, *, api_key: str = "") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="http://localhost:9999/v1",
        model=ENDPOINT_MODEL,
        api_key=api_key or None,
        transport=endpoint,
    )


def _analysis_stub() -> Any:
    """AgentSystem 需要的 analysis 的最小形状:builder 只读这几个字段."""
    project = SimpleNamespace(
        id="p-fake",
        tool_versions={"jadx": "test-suite"},
        apk=SimpleNamespace(sha256="0" * 64),
    )
    return SimpleNamespace(result=SimpleNamespace(project=project, workspace=Path("ws-fake")))


def _scored(question: Question, system: System) -> TaskTrace:
    """跑一题,过 run.py 的判分路径,得到合法 trace."""
    raw = TaskTrace(
        reference=question.reference,
        system=system.kind,
        provider=system.provider_name,
        model=system.model_name,
        max_tokens=system.max_tokens,
        question=question.question,
        result=system.answer(question),
    )
    return _score(question, raw)


def test_source_text_tokens_are_the_reported_ones() -> None:
    endpoint = FakeEndpoint()
    system = SourceTextSystem(sources=_sources(), provider=_provider(endpoint))
    question = _questions()[0]

    result = system.answer(question)

    assert not result.failed, result.error
    assert 1 <= len(endpoint.calls) <= 2
    assert result.prompt_tokens == PROMPT_TOKENS * len(endpoint.calls)
    assert result.completion_tokens == COMPLETION_TOKENS * len(endpoint.calls)
    url, payload, _ = endpoint.calls[0]
    assert url.endswith("/chat/completions")
    assert payload["max_tokens"] == system.max_tokens


def test_a_failed_retrieval_still_reaches_the_model() -> None:
    """A retrieval that failed is data, not a crash: the model is asked anyway.

    The two retrieval attempts fail, and the model is asked once with both
    failures in front of it. It is not asked twice: the first answer is the
    answer, and asking again would spend the tokens a second time for
    nothing. The usage the endpoint reported is what the trace records.
    """
    endpoint = FakeEndpoint()
    # project_ids is empty: both retrievals find no analysis, so the
    # retrieval returns error data rather than raising.
    system = StructuredSystem(analyzer=object(), project_ids={}, provider=_provider(endpoint))
    question = _questions()[0]

    result = system.answer(question)

    assert not result.failed, result.error
    assert len(endpoint.calls) == 1
    assert result.prompt_tokens == PROMPT_TOKENS
    assert result.completion_tokens == COMPLETION_TOKENS
    # The retrieval did not raise, but what it returned is error data, and
    # the model was asked with it in front of it.
    assert "error" in json.loads(result.observations[0])
    assert result.answer_text, "the model's answer was thrown away"


def test_agent_charges_the_reported_usage_to_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    endpoint = FakeEndpoint()
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:9999/v1",
        model=ENDPOINT_MODEL,
        api_key=os.environ[API_KEY_ENV],
        transport=endpoint,
    )
    question = _questions()[0]
    system = AgentSystem(
        analyzer=object(),
        analyses={question.sample: _analysis_stub()},
        provider_factory=lambda: provider,
        store_root=tmp_path / "agent-states",
    )

    result = system.answer(question)

    assert not result.failed, result.error
    # D 的 token 走 Orchestrator 的预算记账:state.charge(tokens=
    # response.total_tokens),来源同样是端点上报的 usage.
    assert result.prompt_tokens == PROMPT_TOKENS + COMPLETION_TOKENS
    assert len(endpoint.calls) == 1
    _, _, headers = endpoint.calls[0]
    assert headers["Authorization"] == f"Bearer {API_KEY}"


def test_three_systems_share_one_provider_construction(tmp_path: Path) -> None:
    """同一个构造,三个配置:trace 过判分,序列化往返,key 不落盘."""
    endpoint = FakeEndpoint()
    factory = lambda: _provider(endpoint, api_key=API_KEY)  # noqa: E731

    question = _questions()[0]
    systems: tuple[System, ...] = (
        SourceTextSystem(sources=_sources(), provider=factory(), max_tokens=2048),
        StructuredSystem(analyzer=object(), project_ids={}, provider=factory(), max_tokens=2048),
        AgentSystem(
            analyzer=object(),
            analyses={question.sample: _analysis_stub()},
            provider_factory=factory,
            store_root=tmp_path / "agent-states",
            max_tokens=2048,
        ),
    )
    traces = tuple(_scored(question, system) for system in systems)

    for trace in traces:
        assert trace.provider == "openai-compatible"
        assert trace.model == ENDPOINT_MODEL
        assert trace.task_id, "the scorer wrote the task id into the trace"
        document = json.dumps(trace.to_dict())
        assert API_KEY not in document, "the key must never reach a trace"
        restored = TaskTrace.from_dict(trace.to_dict())
        assert restored.tokens == trace.tokens

    assert {trace.system for trace in traces} == set(SystemKind)


def test_metrics_accept_a_real_provider_trace(tmp_path: Path) -> None:
    """八项指标照常从真实 provider 的 trace 算出来."""
    endpoint = FakeEndpoint()
    factory = lambda: _provider(endpoint)  # noqa: E731

    question = _questions()[0]
    systems: tuple[System, ...] = (
        SourceTextSystem(sources=_sources(), provider=factory(), max_tokens=2048),
        StructuredSystem(analyzer=object(), project_ids={}, provider=factory(), max_tokens=2048),
        AgentSystem(
            analyzer=object(),
            analyses={question.sample: _analysis_stub()},
            provider_factory=factory,
            store_root=tmp_path / "agent-states",
            max_tokens=2048,
        ),
    )
    traces = tuple(_scored(question, system) for system in systems)

    metrics = compare(list(traces))

    assert set(metrics) == {kind.value for kind in SystemKind}
    for values in metrics.values():
        assert values["token_consumption"] is not None


def test_cli_provider_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def args(provider: str, **extra: str) -> argparse.Namespace:
        return argparse.Namespace(
            provider=provider,
            base_url=extra.get("base_url", ""),
            model=extra.get("model", ""),
            api_key_env=extra.get("api_key_env", ""),
            # _provider_factory reads this for the openai-compat provider; the
            # default is the CLI's own (run.py --request-timeout, 180s).
            request_timeout=extra.get("request_timeout", 180.0),
        )

    monkeypatch.setenv(API_KEY_ENV, API_KEY)

    # scripted 仍是默认:真实 provider 的参数对它是错误,不是静默忽略.
    assert _provider_factory(args("scripted")) is None
    with pytest.raises(SystemExit):
        _provider_factory(args("scripted", base_url="http://localhost:9999/v1"))
    with pytest.raises(SystemExit):
        _provider_factory(args("openai-compat", base_url="http://localhost:9999/v1"))
    with pytest.raises(SystemExit):
        _provider_factory(args("openai-compat", model="bench-model"))
    with pytest.raises(SystemExit):
        _provider_factory(args("local"))

    # key 从环境变量读:变量在,factory 造出的 provider 拿到它;
    # 变量不在,fail-fast,而不是发一个没有 key 的请求等 401.
    factory = _provider_factory(
        args(
            "openai-compat",
            base_url="http://localhost:9999/v1",
            model="bench-model",
            api_key_env=API_KEY_ENV,
        )
    )
    assert factory is not None
    provider = factory()
    assert isinstance(provider, ModelProvider)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_key == API_KEY
    assert provider.name == "openai-compatible"
    assert provider.model == "bench-model"

    monkeypatch.delenv(API_KEY_ENV)
    with pytest.raises(SystemExit):
        _provider_factory(
            args(
                "openai-compat",
                base_url="http://localhost:9999/v1",
                model="bench-model",
                api_key_env=API_KEY_ENV,
            )
        )

    # local 端点不发 key:给 --api-key-env 是理解错了,报错而不是忽略.
    with pytest.raises(SystemExit):
        _provider_factory(
            args(
                "local",
                base_url="http://localhost:9999",
                model="bench-model",
                api_key_env=API_KEY_ENV,
            )
        )
    local_factory = _provider_factory(
        args("local", base_url="http://localhost:9999", model="bench-model")
    )
    assert local_factory is not None
    local = local_factory()
    assert isinstance(local, LocalModelProvider)
    assert local.name == "local-model"


def test_a_retrieval_system_does_not_offer_the_model_tools() -> None:
    """A and B are "a model with retrieval", not "a model with tools".

    The retrieval is done by the harness under one fixed strategy, and its
    result is handed to the model. A model offered tools asks for them
    instead of answering -- which measures the harness's tool loop rather
    than the model reading what the retrieval found.
    """
    endpoint = FakeEndpoint()
    system = SourceTextSystem(sources=_sources(), provider=_provider(endpoint))
    question = _questions()[0]

    system.answer(question)

    assert endpoint.calls, "the model was never asked"
    payload = endpoint.calls[0][1]
    assert "tools" not in payload, "the model was offered tools it must not use"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_the_retrieved_material_reaches_the_model_as_data() -> None:
    """The retrieval result is in the prompt, marked as data, not as an instruction."""
    endpoint = FakeEndpoint()
    system = SourceTextSystem(sources=_sources(), provider=_provider(endpoint))
    question = _questions()[0]

    system.answer(question)

    messages = endpoint.calls[0][1]["messages"]
    contents = " ".join(str(message.get("content", "")) for message in messages)
    assert "data" in contents, "the retrieval is not marked as data"
    assert "Crypto" in contents or "demo" in contents, "the retrieval is not in the prompt"


def test_an_empty_retrieval_does_not_discard_the_models_answer() -> None:
    """Nothing found is a fact about the retrieval, not a reason to drop the answer.

    The answer may well be "there is none", which is the right answer to an
    unanswerable question. Discarding it and asking again would lose the
    answer the model gave.
    """
    endpoint = FakeEndpoint()
    system = StructuredSystem(
        analyzer=object(),
        project_ids={},
        provider=_provider(endpoint),
    )
    question = _questions()[0]

    result = system.answer(question)

    assert result.answer_text, "the model's answer was thrown away"
    assert result.assertions, "the answer produced no claim"


def test_the_agent_gets_enough_iterations_to_answer(tmp_path: Path) -> None:
    """Four iterations stopped the agent before it answered.

    With a real model, 42 of 92 tasks ran out of iterations before they
    answered, which measured the budget rather than the agent. The default
    is now the agent's own default of eight, and a caller can raise it.
    """
    system = AgentSystem(
        analyzer=object(),
        analyses={},
        provider_factory=lambda: _provider(FakeEndpoint()),
        store_root=tmp_path / "agent-states",
    )

    assert system.max_iterations >= 8
    assert system.total_tokens >= system.max_tokens


def test_a_backend_that_did_not_take_part_is_data_not_a_failed_task() -> None:
    """A missing manifest is a fact about the analysis, not a crashed run.

    The CI smoke run asks the harness questions with no backend installed,
    and the manifest tool says which backends were absent. That answer has
    to reach the model as data: a task that raised instead would be recorded
    as a run that produced nothing, and the model would never get the chance
    to say "this analysis holds no manifest".
    """
    from benchmarks.comparison.retrieval import StructuredTools

    class _Analyzer:
        """An analyzer whose analysis holds no manifest.

        The project is there -- its Apktool step simply never ran, which is
        what the error is for.
        """

        class store:  # stands in for the store the tool reads
            @staticmethod
            def get_project(project_id: str) -> object:
                return SimpleNamespace(tool_versions={"apktool": None, "jadx": None})

            @staticmethod
            def get_manifest(project_id: str) -> None:
                return None

    tools = StructuredTools(analyzer=_Analyzer(), project_ids={"demo-app": "apk_1"})
    payload = tools.call("get_manifest", _questions()[0], "")

    assert payload["error"], "the missing manifest was not reported"
    assert payload["error_code"] == "no_manifest"
    assert payload["missing_backends"]
