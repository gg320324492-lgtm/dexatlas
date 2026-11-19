"""没人守的手写测量数: 门禁守住性质, 红->绿可复现.

审计 (``docs/reports/handwritten-numbers-audit.md``) 查出十处**没有任何门禁会报**的
手写测量数. 本文件守的是那道新门禁 (``scripts/check-unguarded-numbers.py``) 本身:

- 它**守性质, 不守写死的数** -- 门禁从树上把真值算出来, 再和文档里的那句话比;
  真值永远是树本身, 加一个 job, 加一个工具, 加一个测试都会让它自己变红;
- 它**红->绿可复现** -- 把一句话里的数换成错的, 它报; 换成对的, 它不报.

门禁的判定本身是 ``scripts/check-unguarded-numbers.py`` 的退出码, 由 CI 的
``lint`` job 跑. 这里不重复判一次: **套件红会挡住测量脚本写数** (那正是审计里
记着的三个闭环之一), 所以这道门禁的结论不进套件, 只进 CI.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "scripts" / "check-unguarded-numbers.py"
INVENTORY = REPO_ROOT / "scripts" / "unguarded-numbers.json"
BENCHMARKS = REPO_ROOT / "docs" / "benchmarks"


def _checker() -> ModuleType:
    """把门禁脚本当模块加载, 和套件加载别的脚本的方式一样."""
    spec = importlib.util.spec_from_file_location("dexatlas_unguarded_numbers", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _inventory() -> dict[str, object]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def _statements() -> list[dict[str, object]]:
    listed = _inventory().get("statements")
    assert isinstance(listed, list)
    return [statement for statement in listed if isinstance(statement, dict)]


def _statement(identifier: str) -> dict[str, object]:
    return next(item for item in _statements() if item.get("id") == identifier)


# ---------------------------------------------------------------------------
# 红->绿: 同一句话, 错的数报, 对的数不报
# ---------------------------------------------------------------------------


def test_a_watched_sentence_with_the_wrong_number_is_reported() -> None:
    """红: 文档写的数与树上算出的数不一致, 门禁要报出两个数."""
    checker = _checker()
    truths = checker.facts()
    statement = _statement("portfolio-tests-total")
    text = "Strict mypy typing, ruff lint/format, 1,999 tests at 93.3% coverage."
    findings = checker.check_text(statement, text, truths)
    assert len(findings) == 1, findings
    finding = findings[0]
    assert finding.stated == "1,999"
    assert finding.expected == f"{truths['report_tests_total']:g}"
    assert "report_tests_total" in finding.what


def test_the_same_sentence_with_the_right_number_is_silent() -> None:
    """绿: 同一个句子, 数字对了就没有 finding."""
    checker = _checker()
    truths = checker.facts()
    statement = _statement("portfolio-tests-total")
    total = int(truths["report_tests_total"])
    text = f"Strict mypy typing, {total:,} tests at 93.3% coverage."
    assert checker.check_text(statement, text, truths) == []


def test_a_sentence_that_stops_being_a_number_is_not_a_finding() -> None:
    """一句话里的数读不出来时, 门禁不猜 -- 它报「这句话不在了」."""
    checker = _checker()
    truths = checker.facts()
    statement = _statement("mcp-tools-handover")
    text = "The three extras are all needed for the full suite: `dev` for the tools,"
    findings = checker.check_text(statement, text, truths)
    assert len(findings) == 1, findings
    assert "no longer in the document" in findings[0].what


def test_a_group_that_does_not_take_part_is_simply_not_checked() -> None:
    """句子的形状有时只匹配一半: 没匹配上的那一组不参与比较, 也不报错."""
    checker = _checker()
    truths = checker.facts()
    statement = {
        "id": "two-shapes",
        "path": "docs/portfolio.md",
        "pattern": r"(?P<tests>[\d,]+) tests(?:, (?P<pct>[\d.]+)% coverage)?",
        "groups": {"tests": "report_tests_total", "pct": "report_coverage_pct"},
    }
    total = int(truths["report_tests_total"])
    only_tests = checker.check_text(statement, f"{total:,} tests", truths)
    assert only_tests == [], only_tests
    both = checker.check_text(statement, f"{total:,} tests, 93.3% coverage", truths)
    assert both == [], both
    wrong = checker.check_text(statement, "1,999 tests, 93.3% coverage", truths)
    assert len(wrong) == 1, wrong


def test_the_contract_check_count_comes_from_the_contract_script() -> None:
    """静态条数要从契约脚本数出来, 不是从 §7 抄一份.

    词条说静态条数是脚本里 `check()` 调用点的数目 -- 那就照这句话数.
    """
    checker = _checker()
    truths = checker.facts()
    assert "contract_static_checks" in truths
    assert truths["contract_static_checks"] >= 40
    statement = _statement("contract-static-checks")
    glossary = (REPO_ROOT / "docs" / "glossary.md").read_text(encoding="utf-8")
    findings = checker.check_text(statement, glossary, truths)
    assert findings == [], findings


def test_the_numbers_a_document_writes_in_words_are_read() -> None:
    """英文与中文的数都要读得出来: thirteen, 十三, 13."""
    checker = _checker()
    assert checker.parse_number("thirteen") == 13
    assert checker.parse_number("十三") == 13
    assert checker.parse_number("十一") == 11
    assert checker.parse_number("1,733") == 1733
    assert checker.parse_number("93.3") == 93.3
    assert checker.parse_number("the") is None


# ---------------------------------------------------------------------------
# 清单本身不能烂掉: 守着的句子必须还在, 真值必须算得出来
# ---------------------------------------------------------------------------


def test_every_watched_document_is_there() -> None:
    """清单里点的文件必须都在 -- 不然门禁守的是一个不存在的句子."""
    for statement in _statements():
        path = REPO_ROOT / str(statement.get("path"))
        assert path.is_file(), f"{statement.get('id')} names a file that is not there"


def test_every_watched_sentence_is_still_in_its_document() -> None:
    """句子还在不在.

    文档改个说法, 句子可能就没了: 门禁这时必须说「这句话不在了」,
    而不是安静地不再守它. 清单里的每一条都至少要在一处匹配上, 而且那一处
    读得出数.
    """
    checker = _checker()
    truths = checker.facts()
    for statement in _statements():
        path = REPO_ROOT / str(statement.get("path"))
        text = path.read_text(encoding="utf-8")
        findings = checker.check_text(statement, text, truths)
        gone = [finding for finding in findings if "no longer in the document" in finding.what]
        assert not gone, f"{statement.get('id')}: {gone[0].what}"


def test_every_fact_the_inventory_names_can_be_computed() -> None:
    """真值必须算得出来.

    算不出来的事实会让门禁报「不是这道门禁能算的事实」 -- 那是清单写错了,
    不是文档写错了, 两件事不能混成一条 finding.
    """
    checker = _checker()
    truths = checker.facts()
    for statement in _statements():
        groups = statement.get("groups")
        assert isinstance(groups, dict)
        for fact in groups.values():
            assert str(fact) in truths, f"{statement.get('id')} names the fact {fact}"


def test_the_truths_come_from_the_tree_and_not_from_a_number_written_down() -> None:
    """门禁算的是树, 不是抄下来的数.

    CI job 数是从 workflow 的 job 键数出来的, MCP 工具数是从服务器的注册数出来的,
    测试数与覆盖率是从执行报告的标记里读出来的. 这几处若有人把数字写死在脚本里,
    门禁就变成了「检查自己抄的数对不对」, 那正是它要治的病.
    """
    source = CHECKER.read_text(encoding="utf-8")
    for literal in ("== 13", "== 11", "== 1733", "== 93.3"):
        assert literal not in source, f"{literal} is a number written down in the gate"


# ---------------------------------------------------------------------------
# B8: 真模型那次的基准报告, CI 不重生成 -- 没有人守
# ---------------------------------------------------------------------------


def test_the_real_model_reports_regenerate_from_their_committed_traces() -> None:
    """两份真模型的基准报告要能从落盘的 trace 重算出来.

    ``docs/benchmarks/comparison.md`` 由 CI 的 ``m3-comparison`` job 重生成并逐行比对;
    ``comparison-real.md`` 与 ``comparison-stronger.md`` 用的是另外两个 trace 文件,
    CI 不碰它们, 于是它们是「由脚本重算, 却没有人跑」的数. 每一份报告的每个数
    都写明「由 trace 算出, 不要手改」 -- 那就让它真的能被算出来.
    """
    from benchmarks.comparison.run import _markdown, _run_from_document

    for report_name, traces_name, previous in (
        ("comparison-real.md", "comparison-real-traces.json", None),
        (
            "comparison-stronger.md",
            "comparison-stronger-traces.json",
            "comparison-real-traces.json",
        ),
    ):
        traces = BENCHMARKS / traces_name
        assert traces.is_file(), f"{traces_name} is not in the repository"
        run = _run_from_document(json.loads(traces.read_text(encoding="utf-8")))
        generated = _markdown(
            run,
            evidence=traces.name,
            comparison_to=(BENCHMARKS / previous) if previous else None,
        )
        report = (BENCHMARKS / report_name).read_text(encoding="utf-8")
        assert generated == report, f"{report_name} does not regenerate from {traces_name}"
