"""comparison harness 按题面配置 Analyze 的端到端回归测试(Phase 3 M6-③).

失败分析(docs/benchmarks/m6-level2-failure-analysis.md §5.6)的根因之一:
harness 只用 ``Configuration.FULL`` Analyze, ``Question.configuration``
没有任何消费者. 这里的用例锁住路由行为——后端禁用配置的题目, 读到的是
那个配置自己的分析, 而不是 full 工作区的.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from benchmarks.comparison.model import Question
from benchmarks.comparison.retrieval import SourceTextTools, StructuredTools
from benchmarks.comparison.run import _analyse_samples
from benchmarks.model import Configuration, Sample


def test_analyse_samples_groups_by_declared_configuration(tmp_path: Path) -> None:
    """no-apktool 配置得到自己的工作区, apktool 的缺席被记录."""
    _analyzer, by_config, _ids = _analyse_samples(
        tmp_path, samples={Sample.DEMO}, configurations={Configuration.NO_APKTOOL}
    )
    assert set(by_config) == {Configuration.FULL, Configuration.NO_APKTOOL}
    no_apktool = by_config[Configuration.NO_APKTOOL]["demo-app"]
    full = by_config[Configuration.FULL]["demo-app"]
    # project id 由 APK 内容决定, 两配置相同; 工作区才是配置的边界.
    assert no_apktool.result.project.id == full.result.project.id
    assert no_apktool.result.workspace != full.result.workspace
    # no-apktool 的工作区里, apktool 版本是 None(缺席), 且失败已记录;
    # 该配置只禁 apktool, 其余后端按本机安装情况如实出现.
    versions = dict(no_apktool.result.project.tool_versions)
    assert versions["apktool"] is None
    errors = [(error.tool, error.code.value) for error in no_apktool.result.project.errors]
    assert ("apktool", "not_installed") in errors
    # full 工作区里 apktool 不缺席——前提是本机装了它 (CI 与本机的
    # ``DEXATLAS_APKTOOL_JAR``). 没装时 full 与 no-apktool 的差别只剩
    # 工作区路径, no-* 的记录行为已由上面的断言独立成立, 这里跳过.
    if dict(full.result.project.tool_versions)["apktool"] is not None:
        assert no_apktool.result.project.tool_versions["apktool"] is None


def test_structured_tools_route_the_question_to_its_configuration(
    tmp_path: Path,
) -> None:
    """B 对 no-apktool 题调 get_manifest, 拿到 no_manifest 错误而不是包名.

    full 配置的前提是本机装了 Apktool (CI 与本机的
    ``DEXATLAS_APKTOOL_JAR``); 没装时 full 的 manifest 也读不出,
    那是环境前提不成立, 跳过而不是让断言误报.
    """
    _analyzer, by_config, project_ids = _analyse_samples(
        tmp_path, samples={Sample.DEMO}, configurations={Configuration.NO_APKTOOL}
    )
    full_versions = dict(by_config[Configuration.FULL]["demo-app"].result.project.tool_versions)
    if full_versions["apktool"] is None:
        pytest.skip("apktool not installed on this machine")
    tools = StructuredTools(
        analyzer=_analyzer,
        project_ids=project_ids,
        analyses_by_config=by_config,
    )
    question = Question(
        reference="q067",
        question="What package does the demo application declare, when the APK reader "
        "is not installed?",
        sample="demo-app",
        configuration="no-apktool",
    )
    payload = tools.call("get_manifest", question, "package")
    assert payload.get("error_code") == "no_manifest"
    assert "apktool" in payload.get("missing_backends", [])

    # 同一工具面对 full 配置的题, 照常返回包名.
    full_question = Question(
        reference="q001",
        question="What package does the demo application declare?",
        sample="demo-app",
        configuration="full",
    )
    ok = tools.call("get_manifest", full_question, "package")
    assert ok.get("package") == "com.example.demo"


def test_source_text_tools_hide_the_absent_backend_files(tmp_path: Path) -> None:
    """A 对 no-apktool 题检索不到 manifest/smali, 对 full 题照常检索."""
    tools = SourceTextTools({sample.value: sample.source_directory for sample in Sample})
    demo = Sample.DEMO.source_directory

    full_question = Question(
        reference="q001",
        question="What package does the demo application declare?",
        sample="demo-app",
        configuration="full",
    )
    hits = tools.call("search_source_text", full_question, "com.example.demo")
    assert hits["hits"], "the full configuration still sees the sources"

    absent_question = Question(
        reference="q067",
        question="What package does the demo application declare, when the APK reader "
        "is not installed?",
        sample="demo-app",
        configuration="no-apktool",
    )
    hidden = tools.call("search_source_text", absent_question, "com.example.demo")
    assert hidden["hits"] == [], "apktool's files are gone with the backend"

    # jadx 缺失只藏 Java, smali 仍在.
    no_jadx_question = Question(
        reference="q066",
        question="Does the analysis record that the decompiler was missing?",
        sample="demo-app",
        configuration="no-jadx",
    )
    partial = tools.call("search_source_text", no_jadx_question, "const-string")
    assert partial["hits"], "smali survives a missing decompiler"
    assert not any(hit["file"].endswith(".java") for hit in partial["hits"]), "no Java without jadx"
    assert demo.is_dir()
