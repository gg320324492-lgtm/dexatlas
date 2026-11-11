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
from typing import Any, Protocol, runtime_checkable

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
            return word
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
    """

    def __init__(self, sources: dict[str, Path]) -> None:
        self._sources = dict(sources)

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

    def __init__(self, *, analyzer: Any, project_ids: dict[str, str]) -> None:
        self._analyzer = analyzer
        self._project_ids = dict(project_ids)

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

    def call(self, name: str, question: Any, keyword: str) -> dict[str, Any]:
        from dexatlas.mcp.errors import RequestError
        from dexatlas.mcp.tools import projects, references, symbols

        project_id = self._project_ids.get(str(question.sample))
        if project_id is None:
            return {"error": f"no analysis for {question.sample}"}
        try:
            if name == "get_manifest":
                view = projects.manifest(self._analyzer, project_id)
            elif name == "search_symbols":
                view = symbols.search_symbols(
                    self._analyzer, project_id, keyword, limit=50, offset=0
                )
            elif name == "find_callers":
                view = references.find_callers(self._analyzer, project_id, keyword, limit=50)
            else:
                view = references.find_callees(self._analyzer, project_id, keyword, limit=50)
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
