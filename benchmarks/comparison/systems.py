"""三个被测系统,一个接口.

M3 比较的是**输入形态**:A 只能读反编译源码文本,B 只能读结构化符号与
调用引用,DexAtlas agent 还有溯源,完整性感知和证据验证. 三个系统看到的
题目完全相同 (``Question`` 的四个字段),预算相同 (``max_tokens``,
``max_calls``),模型接口相同 (``ModelProvider``).

本机没有 model key,默认 provider 是 ``ScriptedProvider``:它是**替身模型**,
不是模型基线. trace 记下 provider 名,报告照实说. 换真模型只需传另一个
``ModelProvider`` 实现,harness 其余部分不变.

每个配置持有自己的 provider 实例——``ScriptedProvider`` 会消耗脚本,共用
一个实例会让后跑的配置拿不到回答.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from benchmarks.comparison.adapters import prose_to_conclusions
from benchmarks.comparison.model import Assertion, Question, SystemKind, SystemResult, ToolCallTrace
from benchmarks.comparison.retrieval import (
    RetrievalTool,
    SourceTextTools,
    StructuredTools,
    keyword_from,
)
from dexatlas.agent.orchestrator import Orchestrator
from dexatlas.agent.providers.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
    Observation,
    ToolSpec,
)
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion
from dexatlas.agent.state import Budget, TaskStore
from dexatlas.agent.tool_executor import McpToolClient, ToolExecutor
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import EvidenceLevel

#: 三个配置共用的回答格式要求. instructions 里没有,也不许有任何来自
#: marking scheme 的内容;provider 只能看到题目和工具返回的东西.
INSTRUCTIONS = (
    "Answer the question about the analysed Android sample. "
    "Use only the tool observations you were given. "
    'Reply with JSON: {"conclusions":[{"statement":"...","evidence_ids":[],'
    '"locators":[]}],"limitations":[]}. '
    "If the observations do not establish an answer, say so in limitations "
    "and give no conclusions."
)


@runtime_checkable
class System(Protocol):
    """三个配置都必须实现的接口."""

    kind: SystemKind
    provider_name: str
    model_name: str
    max_tokens: int

    def answer(self, question: Question) -> SystemResult: ...


@dataclass(frozen=True, slots=True)
class _BaseSystem:
    """A/B 共用的检索循环."""

    kind: SystemKind
    tools: RetrievalTool
    provider: ModelProvider
    max_tokens: int = 2048
    max_calls: int = 4

    @property
    def provider_name(self) -> str:
        return self.provider.name

    @property
    def model_name(self) -> str:
        return getattr(self.provider, "model", "")

    def answer(self, question: Question) -> SystemResult:
        started = time.monotonic()
        keyword = keyword_from(question.question)
        specs = tuple(
            ToolSpec(name=name, description=self.tools.description(name))
            for name in self.tools.available
        )

        calls: list[ToolCallTrace] = []
        observations: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        error = ""
        recovered = False
        content = ""

        # 两个配置跑同一个检索策略. 第一次没拿到事实时用空关键词再试一次,
        # recovery rate 记的是真实发生过的重试,不是纸面能力.
        for index, term in enumerate((keyword, "")[: self.max_calls]):
            tool_name = self.tools.tool_for(term, index)
            call_started = time.monotonic()
            try:
                payload = self.tools.call(tool_name, question, term)
                observation = json.dumps(payload, ensure_ascii=False, default=str)
                facts = _has_facts(payload)
                calls.append(
                    ToolCallTrace(
                        tool=tool_name,
                        ok=True,
                        duration_seconds=time.monotonic() - call_started,
                    )
                )
                observations.append(observation)
            except Exception as exc:  # 工具失败是数据,不是 harness 的崩溃
                message = f"{type(exc).__name__}: {exc}"
                calls.append(
                    ToolCallTrace(
                        tool=tool_name,
                        ok=False,
                        error=message,
                        duration_seconds=time.monotonic() - call_started,
                    )
                )
                observations.append(json.dumps({"error": message}))
                error = message
                continue

            request = ModelRequest(
                instructions=INSTRUCTIONS,
                question=question.question,
                tools=specs,
                turns=tuple(
                    Observation(
                        tool=tool_name,
                        call_id=f"call-{index + 1}",
                        content=observation,
                    )
                    for observation in observations
                ),
                max_tokens=self.max_tokens,
            )
            try:
                response: ModelResponse = self.provider.complete(request)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                continue
            prompt_tokens += response.prompt_tokens
            completion_tokens += response.completion_tokens
            if response.wants_tools or not response.content.strip():
                continue
            if not facts and index == 0:
                # 第一次观察没有事实:这是"恢复"要覆盖的情形,再宽检一次.
                continue
            content = response.content
            if index > 0:
                recovered = True
            break

        parsed = prose_to_conclusions(content)
        assertions = tuple(
            Assertion(text=statement, grounded=False, locator="") for statement in parsed
        )
        return SystemResult(
            answer_text=content,
            # Only what the system actually said is evidence. Handing the
            # scorer the whole retrieval dump would let a substring match
            # pass without the system having said anything -- the "answer
            # with everything" failure mode the task set warns about.
            findings=tuple(assertion.text for assertion in assertions),
            observations=tuple(observations),
            assertions=assertions,
            tool_calls=tuple(calls),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_seconds=time.monotonic() - started,
            recovered=recovered,
            failed=not content and bool(error),
            error=error,
        )


def _has_facts(payload: Any) -> bool:
    """一次检索有没有带回任何事实. 空结果不算失败,但会触发重试."""
    if isinstance(payload, dict):
        if payload.get("error"):
            return False
        for key in ("hits", "symbols", "callers", "callees"):
            if isinstance(payload.get(key), list) and payload[key]:
                return True
    return bool(payload)


class SourceTextSystem(_BaseSystem):
    """配置 A:LLM + 反编译源码文本检索."""

    def __init__(
        self,
        *,
        sources: dict[str, Path],
        provider: ModelProvider | None = None,
        max_tokens: int = 2048,
        max_calls: int = 2,
    ) -> None:
        super().__init__(
            kind=SystemKind.SOURCE_TEXT,
            tools=SourceTextTools(sources),
            provider=provider or scripted_provider(),
            max_tokens=max_tokens,
            max_calls=max_calls,
        )


class StructuredSystem(_BaseSystem):
    """配置 B:LLM + 结构化符号搜索与调用引用."""

    def __init__(
        self,
        *,
        analyzer: Any,
        project_ids: dict[str, str],
        provider: ModelProvider | None = None,
        max_tokens: int = 2048,
        max_calls: int = 2,
    ) -> None:
        super().__init__(
            kind=SystemKind.STRUCTURED,
            tools=StructuredTools(analyzer=analyzer, project_ids=project_ids),
            provider=provider or scripted_provider(),
            max_tokens=max_tokens,
            max_calls=max_calls,
        )


class AgentSystem:
    """配置 D:DexAtlas agent,结构化工具 + 溯源 + 证据验证.

    走真正的 :class:`~dexatlas.agent.orchestrator.Orchestrator`,用进程内的
    :class:`~dexatlas.agent.tool_executor.McpToolClient` (十个 MCP 工具,不经
    stdio). 回答,证据等级,工具调用记录全部从 ``AgentReport`` 取,不另造
    一套判据.
    """

    kind = SystemKind.AGENT

    def __init__(
        self,
        *,
        analyzer: Any,
        analyses: dict[str, Any],
        provider_factory: Callable[[], ModelProvider],
        store_root: Path,
        max_tokens: int = 2048,
    ) -> None:
        self._analyzer = analyzer
        self._analyses = analyses
        self._provider_factory = provider_factory
        self._store_root = store_root
        self.max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        return self._provider_factory().name

    @property
    def model_name(self) -> str:
        return getattr(self._provider_factory(), "model", "")

    def answer(self, question: Question) -> SystemResult:
        started = time.monotonic()
        analysis = self._analyses.get(question.sample)
        if analysis is None:
            return SystemResult(failed=True, error=f"no analysis for {question.sample}")

        provider = self._provider_factory()
        client = McpToolClient(self._analyzer)
        store = TaskStore(self._store_root / question.reference)
        store_root = self._store_root / question.reference
        store_root.mkdir(parents=True, exist_ok=True)

        def builder_for(project_id: str) -> EvidenceBuilder:
            project = analysis.result.project
            return EvidenceBuilder(
                project_id=project_id,
                tool_versions=dict(project.tool_versions),
                apk_sha256=project.apk.sha256,
                workspace=analysis.result.workspace,
            )

        orchestrator = Orchestrator(
            provider=provider,
            client=client,
            builder_for=builder_for,
            store=store,
            limits=Budget(max_tokens=self.max_tokens, max_iterations=4, max_seconds=30.0),
            executor=ToolExecutor(client, timeout=10.0),
            model_attempts=1,
        )
        try:
            state = orchestrator.run(question.question, project_id=analysis.result.project.id)
            report = orchestrator.report(state)
        except Exception as exc:  # 一次 agent 失败是 trace 里的一行,不是崩溃
            return SystemResult(
                duration_seconds=time.monotonic() - started,
                failed=True,
                error=f"{type(exc).__name__}: {exc}",
            )

        calls = tuple(
            ToolCallTrace(
                tool=record.tool,
                ok=record.ok,
                error=record.error_kind or "",
                duration_seconds=record.duration_seconds,
            )
            for record in report.tool_calls
        )
        assertions = tuple(
            Assertion(
                text=record.summary,
                grounded=record.level is EvidenceLevel.LEAD
                or record.level is EvidenceLevel.VERIFIED,
                locator=";".join(source.locator for source in record.provenance),
                verified=record.level is EvidenceLevel.VERIFIED,
            )
            for record in report.findings
        )
        findings = tuple(record.summary for record in report.findings)
        answer_text = " ".join(assertion.text for assertion in assertions)
        return SystemResult(
            answer_text=answer_text,
            findings=findings,
            assertions=assertions,
            tool_calls=calls,
            prompt_tokens=report.usage.tokens,
            duration_seconds=time.monotonic() - started,
            recovered=any(not call.ok for call in calls) and bool(answer_text),
            failed=not answer_text,
            error=report.error or "",
        )


def scripted_provider() -> ScriptedProvider:
    """替身模型:把观察里的事实原样写进结论.

    它不猜答案,不读任务集. 它证明的是 harness 的机械 (工具调用,trace,
    判分,指标)能跑通,不是模型的解题能力. 有 key 时换成
    ``OpenAICompatibleProvider`` 或 ``LocalModelProvider`` 即可.
    """

    def reply(request: ModelRequest) -> ModelResponse:
        observations = request.observation_texts()
        facts = [text.strip() for text in observations if text.strip()]
        if not facts:
            response = answer([], limitations=["no observation was available"])
        else:
            response = answer(
                [conclusion(statement=" ".join(facts)[:2000], evidence_ids=[], locators=[])],
                limitations=[],
            )
        # A scripted provider has no tokenizer, but token consumption still has
        # to be measured and regenerable. The estimate is a deterministic
        # function of the request and reply text, not a guessed constant.
        return ModelResponse(
            content=response.content,
            tool_calls=response.tool_calls,
            model=response.model,
            prompt_tokens=len(request.instruction_text().split())
            + sum(len(text.split()) for text in request.observation_texts()),
            completion_tokens=len(response.content.split()),
        )

    # One reply per allowed retrieval attempt; the loop may call complete()
    # twice when the first observation holds no facts.
    return ScriptedProvider(responses=[reply, reply], name="scripted")


def scripted_agent_provider() -> ScriptedProvider:
    """D 配置的替身模型: 调一个 plan 允许的工具, 再据观察作答.

    工具名从 ``request.tools`` 里选, 而不是硬编码: agent 的 plan 按题目
    决定允许哪些工具, 一个不在 plan 里的调用会被拒为 ``not_allowed``. 脚本
    不含任何题目答案, 观察里有什么就答什么.
    """
    from dexatlas.agent.providers.scripted import tool_call

    #: 每个工具需要的参数. 只挑不需要额外信息的工具, 避免替身模型为了
    #: 凑参数去猜一个类名或 locator -- 那会把任务集的知识带进来.
    ARGUMENTS: dict[str, dict[str, Any]] = {
        "list_projects": {"limit": 50, "offset": 0},
        "search_symbols": {},
    }

    def ask(request: ModelRequest) -> ModelResponse:
        allowed = {spec.name for spec in request.tools}
        for name in ("list_projects", "search_symbols"):
            if name not in allowed:
                continue
            arguments = dict(ARGUMENTS[name])
            if name == "search_symbols":
                arguments.update(query=keyword_from(request.question), limit=50, offset=0)
            return tool_call(name, arguments, call_id="call-1")
        # A plan that allows none of the above still gets an answer, not a
        # fabricated tool call. It will be recorded as a failed call.
        return answer([], limitations=["no permitted retrieval tool"])

    def reply(request: ModelRequest) -> ModelResponse:
        facts = [text.strip() for text in request.observation_texts() if text.strip()]
        statement = " ".join(facts)[:2000] if facts else "the tools returned nothing"
        response = answer([conclusion(statement, evidence_ids=[], locators=[])], limitations=[])
        return ModelResponse(
            content=response.content,
            tool_calls=response.tool_calls,
            model=response.model,
            prompt_tokens=len(request.instruction_text().split())
            + sum(len(text.split()) for text in request.observation_texts()),
            completion_tokens=len(response.content.split()),
        )

    return ScriptedProvider(responses=[ask, reply, reply], name="scripted")


__all__ = [
    "INSTRUCTIONS",
    "AgentSystem",
    "SourceTextSystem",
    "StructuredSystem",
    "System",
    "scripted_agent_provider",
    "scripted_provider",
]
