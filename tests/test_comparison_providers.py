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


def test_structured_retries_and_sums_reported_tokens() -> None:
    endpoint = FakeEndpoint()
    # project_ids 为空:两次检索都拿不到分析,检索失败是数据不是崩溃,
    # provider 照样被问了两次,token 是两次上报值的和.
    system = StructuredSystem(analyzer=object(), project_ids={}, provider=_provider(endpoint))
    question = _questions()[0]

    result = system.answer(question)

    assert not result.failed, result.error
    assert len(endpoint.calls) == 2
    assert result.prompt_tokens == PROMPT_TOKENS * 2
    assert result.completion_tokens == COMPLETION_TOKENS * 2
    # 检索没有抛异常,但它返回的是 error 数据:两次观察都带着 error,
    # 而模型照样按上报的 usage 计了账.
    assert "error" in json.loads(result.observations[0])
    assert result.recovered


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
