"""三配置共用的检索层:同一策略,三种可见的输入形态.

策略本身与任务集无关:从问题文本抽一个关键词,A 拿它搜反编译源码/smali
文本,B 拿它搜结构化符号索引与调用引用. 抽词规则固定,公开,可读,不读
``benchmarks/tasks/``,也不看任何期望答案.

这是防作弊的机械保证:被测系统能看到的只有 ``Question`` 和工具自己的
返回,三个配置的差别只在"工具给它什么".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar, Protocol, runtime_checkable

#: 问题文本里常见的,不该当检索词的词. 抽词不是理解题目,它只是把问题里
#: 那个反引号包住的符号名挑出来;挑不到就退成空串 (全量检索).
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "many",
        "of",
        "the",
        "this",
        "to",
        "what",
        "which",
        "who",
        "with",
    }
)

_BACKTICKED = re.compile(r"`([^`]+)`")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_./$-]{2,}")


def keyword_from(question: str) -> str:
    """从问题文本抽一个检索词,抽不到返回空串.

    优先取反引号里的符号 (题目里的方法名,类名,URL 都这样写);否则取
    第一个不像停用词的,含点号或大写的长词. 空串意味着"没有可用的词",
    由工具决定是全量检索还是重试,而不是编造一个词.
    """
    quoted = _BACKTICKED.search(question)
    if quoted:
        return quoted.group(1).strip()
    for word in _WORD.findall(question):
        if word.casefold() in _STOPWORDS:
            continue
        if "." in word or any(character.isupper() for character in word[1:]):
            return str(word)
    return ""


@runtime_checkable
class RetrievalTool(Protocol):
    """一个配置的检索工具集."""

    @property
    def available(self) -> tuple[str, ...]: ...

    def description(self, name: str) -> str: ...

    def tool_for(self, question: Any, keyword: str, attempt: int) -> str: ...

    def call(self, name: str, question: Any, keyword: str) -> Any: ...


class SourceTextTools:
    """配置 A:反编译源码文本检索.

    ``sources`` 是 ``{sample: 目录}``. 目录里是仓库自带的 smali,manifest,
    strings.xml,以及 (若后端跑过)JADX 的 Java 源码. 检索只读这些文件,
    不经过 DexAtlas 的结构化索引——这正是 A 与 B 的区别.

    A 是单实例服务多道题, 而后端缺失是**题面配置**的属性: 每次检索按
    ``question.configuration`` 现算缺失后端, 缺哪个后端就藏哪一类文件
    (Apktool 缺则 manifest/资源/smali 都没有,JADX 缺则没有 Java). 这让
    A 的检索面与 B/D 的工作区遵循同一事实, 而不是检索工具的想象.
    """

    #: 每个后端缺席时,从这个配置的检索面里消失的文件后缀.
    _ABSENT_SUFFIXES: ClassVar[dict[str, frozenset[str]]] = {
        "apktool": frozenset({".smali", ".xml", ".yml"}),
        "jadx": frozenset({".java"}),
    }

    def __init__(self, sources: dict[str, Path]) -> None:
        self._sources = dict(sources)

    @staticmethod
    def _absent_for(question: Any) -> frozenset[str]:
        """The backends the question's own configuration says are absent."""
        from benchmarks.model import Configuration

        try:
            configuration = Configuration(str(getattr(question, "configuration", "") or ""))
        except ValueError:
            return frozenset()
        if configuration is Configuration.NO_APKTOOL:
            return frozenset({"apktool"})
        if configuration is Configuration.NO_JADX:
            return frozenset({"jadx"})
        return frozenset()

    @property
    def available(self) -> tuple[str, ...]:
        return ("search_source_text",)

    def description(self, name: str) -> str:
        return "Search the sample's decompiled source and smali text for a phrase."

    def tool_for(self, question: Any, keyword: str, attempt: int) -> str:
        return "search_source_text"

    def call(self, name: str, question: Any, keyword: str) -> dict[str, Any]:
        root = self._sources.get(str(question.sample))
        if root is None or not root.is_dir():
            return {"hits": [], "error": f"no source directory for {question.sample}"}
        suffixes = {".smali", ".java", ".xml", ".yml"}
        for backend in self._absent_for(question):
            suffixes -= self._ABSENT_SUFFIXES.get(backend, frozenset())
        files = sorted(path for path in root.rglob("*") if path.suffix in suffixes)
        needle = keyword.casefold()
        hits: list[dict[str, str]] = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                if (needle and needle in line.casefold()) or (not needle and line.strip()):
                    hits.append(
                        {
                            "file": path.relative_to(root).as_posix(),
                            "line": str(number),
                            "text": line.strip()[:300],
                        }
                    )
                if len(hits) >= 50:
                    break
            if len(hits) >= 50:
                break
        return {"query": keyword, "hits": hits, "truncated": len(hits) >= 50}


class StructuredTools:
    """配置 B:结构化符号搜索与调用引用.

    直接调 MCP 的纯 Python 函数 (不经 stdio),只暴露 ``search_symbols``,
    ``find_callers``,``find_callees`` 和 ``get_manifest``:B 看得到结构,但拿
    不到 A 的整段源码文本,也没有 D 的溯源/证据验证工具.

    The manifest is in the list because a question about the package or the
    SDK levels is a question about the manifest, and a structured endpoint
    answers it. A configuration that could only search symbols would report
    "nothing found" for every manifest question, which measures the tool
    list rather than the retrieval.
    """

    #: The words that mean the question is about the manifest rather than
    #: about a symbol. The question is a reader's own words; the harness has
    #: to recognise them to route the query, and it recognises nothing else.
    MANIFEST_WORDS = frozenset(
        {
            "package",
            "packages",
            "version",
            "versions",
            "sdk",
            "permission",
            "permissions",
            "component",
            "components",
            "activity",
            "service",
            "receiver",
            "provider",
            "exported",
            "manifest",
        }
    )

    def __init__(
        self,
        *,
        analyzer: Any,
        project_ids: dict[str, str],
        analyses_by_config: dict[Any, dict[str, Any]] | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._project_ids = dict(project_ids)
        # 按题面配置路由到对应工作区的分析结果: ``no-jadx`` / ``no-apktool``
        # 题读它们自己的 project, manifest 与错误记录才反映那个配置的真实
        # 状态. 没有分组表时退回单工作区行为 (现有调用与测试兼容).
        self._analyses_by_config = dict(analyses_by_config or {})

    @property
    def available(self) -> tuple[str, ...]:
        return ("search_symbols", "find_callers", "find_callees", "get_manifest")

    def description(self, name: str) -> str:
        return f"Structured query: {name}."

    def tool_for(self, question: Any, keyword: str, attempt: int) -> str:
        """Which structured query answers this question."""
        if attempt > 0:
            return "search_symbols"
        text = str(getattr(question, "question", "") or "")
        words = {word.strip(".,?").casefold() for word in text.split()}
        if words & self.MANIFEST_WORDS:
            return "get_manifest"
        if keyword:
            return "find_callers" if "(" in keyword else "search_symbols"
        return "get_manifest"

    def _routing(self, question: Any) -> tuple[Any, str, str] | None:
        """按题面配置选 (analyzer, project_id); 未路由到时返回 None.

        返回 ``None`` 表示继续用构造时绑定的 full 工作区; 路由到分组表
        里没有的配置也视为未路由, 不在这里编造一个分析.
        """
        by_config = self._analyses_by_config or {}
        if not by_config:
            return None
        try:
            from benchmarks.model import Configuration

            configuration = Configuration(str(getattr(question, "configuration", "") or ""))
        except ValueError:
            return None
        chosen = by_config.get(configuration)
        if chosen is None:
            return None
        analysis = chosen.get(str(question.sample))
        if analysis is None:
            return None
        return analysis.analyzer, analysis.result.project.id, str(question.sample)

    def call(self, name: str, question: Any, keyword: str) -> dict[str, Any]:
        from dexatlas.mcp.errors import RequestError
        from dexatlas.mcp.tools.projects import manifest as manifest_tool
        from dexatlas.mcp.tools.references import find_callees as find_callees_tool
        from dexatlas.mcp.tools.references import find_callers as find_callers_tool
        from dexatlas.mcp.tools.symbols import search_symbols as search_symbols_tool

        routed = self._routing(question)
        analyzer: Any = self._analyzer
        project_id: str | None = None
        if routed is not None:
            analyzer, project_id, _sample = routed
        else:
            project_id = self._project_ids.get(str(question.sample))
        if project_id is None:
            return {"error": f"no analysis for {question.sample}"}
        try:
            view: Any
            if name == "get_manifest":
                view = manifest_tool(analyzer, project_id)
            elif name == "search_symbols":
                view = search_symbols_tool(analyzer, project_id, keyword, limit=50, offset=0)
            elif name == "find_callers":
                view = find_callers_tool(analyzer, project_id, keyword, limit=50)
            else:
                view = find_callees_tool(analyzer, project_id, keyword, limit=50)
        except RequestError as exc:
            # A backend that did not take part is a fact about the analysis,
            # not a failed task. The error carries which backends were absent,
            # and the model is told it as data -- which is what lets it answer
            # "this analysis holds no manifest" instead of the harness
            # recording a run that produced nothing.
            detail = getattr(exc, "detail", {}) or {}
            return {
                "error": str(exc),
                "error_code": getattr(exc, "code", ""),
                "missing_backends": list(detail.get("missing_backends", []) or []),
            }
        return jsonable(view)


def jsonable(value: Any) -> dict[str, Any]:
    """把 Pydantic 视图变成能进 trace 的普通 dict."""
    if hasattr(value, "model_dump"):
        dumped: Any = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {"value": dumped}
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {"value": str(value)}
