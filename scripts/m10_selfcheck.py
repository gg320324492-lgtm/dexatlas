#!/usr/bin/env python3
"""Run the automatable part of the M10 external-acceptance checklist.

    uv run --no-sync python scripts/m10_selfcheck.py

``docs/reports/m10-acceptance-pack.md`` states 40 acceptance checks for the
M10 independent review. A human reviewer runs most of them on their own
machine; a subset is decidable here, from the repository itself, without
installing a backend or running the whole suite:

* documents exist and their relative cross-references resolve,
* the changelog's ``[Unreleased]`` section exists and is sorted sensibly,
* the README's tests/coverage badges state what the report's figures state,
* the report's ``<!--fig:...-->`` markers are consistent and complete,
* the pack's own tables are complete (40 rows, 19 blocking, no duplicate),
* the gates the pack names are runnable commands that exist on the path,
* the contracts the pack points at (exit codes, MCP tools, report fields,
  routes, the evidence package's ``not_included``) match the code,
* the three gaps a reader dry run found stay closed: the setup step has to
  fetch the third-party samples, A6's degraded evidence has to be written
  down at the time because the CLI cannot replay a past run, and the
  evidence package's entry count is the one the CLI prints and the
  material states.

Every check is a *read* or a *comparison*; the script writes nothing and
never edits the report or the badges. Its verdict is three-valued, like the
pack's own: pass, fail, or manual — a check the repository can answer is
run, and one only a reader on a real machine can answer is left marked.

The exit code is 0 when no check failed (manual checks do not fail the
run), 1 when at least one failed.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The pack's own counts, restated here as the things the checks compare
#: against. They are read from the pack, not invented: the checks below
#: count the rows in its tables and compare them with these.
PACK_PATH = REPO_ROOT / "docs" / "reports" / "m10-acceptance-pack.md"
READER_PATH = REPO_ROOT / "docs" / "reports" / "m10-reader-package.md"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
CONTRACTS_PATH = REPO_ROOT / "docs" / "architecture" / "public-contracts.md"

BLOCKING_IDS = {
    "A2",
    "A4",
    "A6",
    "B1",
    "C1",
    "C2",
    "C3",
    "C5",
    "C6",
    "D1",
    "D2",
    "D3",
    "E2",
    "E3",
    "F1",
    "F5",
    "G2",
    "G3",
    "G5",
}

#: The commands the pack's §6.3 quality gate names, by the binary that has
#: to exist for the command to be runnable. The gate is not executed here;
#: a check that proves the commands *can* run is the automatable part.
GATE_COMMANDS: tuple[tuple[str, str, list[str]], ...] = (
    ("G.ruff", "ruff", ["ruff", "check", "."]),
    ("G.ruff-format", "ruff", ["ruff", "format", "--check", "."]),
    ("G.mypy", "mypy", ["mypy"]),
    (
        "G.vulture",
        "vulture",
        [
            "vulture",
            "src/",
            "tests/",
            "scripts/",
            "benchmarks/",
            "--min-confidence",
            "80",
        ],
    ),
    ("G.pytest", "pytest", ["pytest", "-q"]),
    (
        "G.check-doc-citations",
        "python",
        [
            "python",
            "scripts/check-doc-citations.py",
        ],
    ),
    (
        "G.check-version-claims",
        "python",
        [
            "python",
            "scripts/check-version-claims.py",
            "--base",
            "auto",
        ],
    ),
)

#: The section markers of the verification entry points the pack names.
CONTRACT_TEST = REPO_ROOT / "tests" / "test_public_contracts.py"
VERIFY_CONTRACTS = REPO_ROOT / "scripts" / "verify-public-contracts.py"

#: The three documents that tell a reader how to set a machine up. The reader
#: package is the one-stop entry; the kit and the executive summary repeat
#: the same facts, so a drift between them is a defect a reader meets while
#: following one of them.
READER_KIT_REL = Path("docs/reports/m10-reader-kit.md")
EXEC_SUMMARY_REL = Path("docs/reports/m10-executive-summary.md")

#: The sources the reader-dry-run checks read the tool's behaviour from.
FIXTURE_SCRIPT_REL = Path("scripts/fetch-fixtures.sh")
EVIDENCE_PACKAGE_REL = Path("src/dexatlas/reports/evidence_package.py")
CLI_REL = Path("src/dexatlas/cli/main.py")
STORAGE_REL = Path("src/dexatlas/core/storage.py")

#: Where the third-party samples live once they are fetched. They are not
#: committed, so a fresh clone has none of them.
FIXTURE_DIR_REL = Path("fixtures") / "apk"

FIGURE = re.compile(r"<!--fig:([A-Za-z0-9_./-]+)-->(.*?)<!--/fig-->", re.DOTALL)
BADGE_TESTS = re.compile(r"badge/tests-([\d.]*)%20passing")
BADGE_COVERAGE = re.compile(r"badge/coverage-([\d.]*)%25")

PACK_ROW = re.compile(r"^\| ([A-G]\d) \|", re.MULTILINE)
PACK_BLOCKING = re.compile(r"\| ★ \|")


# ---------------------------------------------------------------------------
# The check framework
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """One check's three-valued result, with the evidence to reproduce it."""

    check_id: str
    title: str
    state: str  # "pass" | "fail" | "manual"
    detail: str = ""
    blocking: bool = False


@dataclass
class Report:
    outcomes: list[Outcome] = field(default_factory=list)

    def add(self, outcome: Outcome) -> None:
        self.outcomes.append(outcome)

    def counts(self) -> dict[str, int]:
        return {
            "pass": sum(1 for o in self.outcomes if o.state == "pass"),
            "fail": sum(1 for o in self.outcomes if o.state == "fail"),
            "manual": sum(1 for o in self.outcomes if o.state == "manual"),
        }

    def rate(self) -> str:
        """The pass rate over the checks this run could decide."""
        decided = self.counts()["pass"] + self.counts()["fail"]
        if not decided:
            return "n/a"
        return f"{self.counts()['pass'] / decided * 100:.1f}%"


def manual(check_id: str, title: str, why: str, blocking: bool = False) -> Outcome:
    return Outcome(check_id, title, "manual", why, blocking)


def outcome_of(
    check_id: str, title: str, ok: bool, detail: str = "", blocking: bool = False
) -> Outcome:
    state = "pass" if ok else "fail"
    return Outcome(check_id, title, state, detail, blocking)


def blocking_flag(item_id: str) -> bool:
    return item_id in BLOCKING_IDS


# ---------------------------------------------------------------------------
# Group 0 — the pack's own structure
# ---------------------------------------------------------------------------


def check_pack_structure(report: Report) -> None:
    """The pack's tables hold 40 items, 19 of them blocking, none duplicated."""
    text = PACK_PATH.read_text(encoding="utf-8")
    ids = PACK_ROW.findall(text)
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    report.add(
        outcome_of(
            "PACK.40-items",
            "验收包恰好 40 项，无重复编号",
            len(ids) == 40 and not duplicates,
            f"读到 {len(ids)} 项" + (f"，重复：{duplicates}" if duplicates else ""),
        )
    )

    blocking_rows = len(PACK_BLOCKING.findall(text))
    declared = sorted(BLOCKING_IDS)
    report.add(
        outcome_of(
            "PACK.19-blocking",
            "阻断项为声明的 19 项",
            blocking_rows == 19 and len(declared) == 19,
            f"表中标 ★ 的行 {blocking_rows} 行；声明清单 {len(declared)} 项",
        )
    )


def check_reader_package(report: Report) -> None:
    """The reader package links back to the pack and names the record template."""
    text = READER_PATH.read_text(encoding="utf-8")
    links_pack = "m10-acceptance-pack.md" in text
    links_template = "m10-review-record-template.md" in text
    report.add(
        outcome_of(
            "PACK.reader-links",
            "读者包链接验收包与记录模板",
            links_pack and links_template,
            f"acceptance-pack 链接={links_pack}，record-template 链接={links_template}",
        )
    )


# ---------------------------------------------------------------------------
# Group 1 — documents and cross-references (A1's document side, pack §3.4/§3.5)
# ---------------------------------------------------------------------------


RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)\s]+)")


def _resolves_literally(base: Path, target: str) -> bool:
    """Whether ``target`` names something, checked component by component.

    ``Path.resolve()`` normalises the way Windows does: there, three dots
    mean "the parent directory", so a placeholder link written as ``...``
    resolved to a directory that exists and passed the check on Windows --
    while a link that means nothing is a broken link on every platform. The
    names are checked literally instead, which is what a file system does on
    every platform, and which is the same rule the document-wide link check
    in ``tests/test_docs.py`` applies.
    """
    current = base
    for part in target.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return current.exists()


def _check_relative_links(path: Path, report: Report, check_id: str, title: str) -> None:
    """Every relative markdown link in a document resolves to a file."""
    text = path.read_text(encoding="utf-8")
    broken: list[str] = []
    for match in RELATIVE_LINK.finditer(text):
        target = match.group(1).split("#")[0]
        if not target:
            continue
        if not _resolves_literally(path.parent, target):
            broken.append(target)
    report.add(
        outcome_of(
            check_id,
            title,
            not broken,
            "全部可解析" if not broken else "断链：" + ", ".join(sorted(set(broken))[:8]),
        )
    )


def check_document_links(report: Report) -> None:
    _check_relative_links(PACK_PATH, report, "DOC.pack-links", "验收包相对链接全部可解析")
    _check_relative_links(READER_PATH, report, "DOC.reader-links", "读者包相对链接全部可解析")
    _check_relative_links(
        CONTRACTS_PATH, report, "DOC.contracts-links", "公共契约表相对链接全部可解析"
    )

    # The case study and the service-regression set the pack's §3.4 and E 组 name.
    case = REPO_ROOT / "docs" / "case-studies" / "demo-app-walkthrough.md"
    service = REPO_ROOT / "docs" / "benchmarks" / "service-regression-set.md"
    report.add(
        outcome_of(
            "DOC.case-study",
            "demo-app 案例文档存在（B 组入口）",
            case.is_file(),
            str(case.relative_to(REPO_ROOT)),
        )
    )
    report.add(
        outcome_of(
            "DOC.service-set",
            "服务回归集文档存在（E 组入口）",
            service.is_file(),
            str(service.relative_to(REPO_ROOT)),
        )
    )


def check_changelog(report: Report) -> None:
    """The changelog's newest section carries Added/Changed headings.

    Before a release that section is ``[Unreleased]``; after it, it is the
    version just tagged. The check follows the newest section rather than a
    fixed name, so it does not expire the day the section is renamed.
    """
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    match = re.search(r"^## \[([^\]]+)\]", text, re.MULTILINE)
    heading = match.group(1) if match else ""
    section = text[match.end() :].split("\n## ", 1)[0] if match else ""
    has_added = "### Added" in section
    has_changed = "### Changed" in section
    report.add(
        outcome_of(
            "DOC.changelog-newest-section",
            "CHANGELOG 最新一节含 Added/Changed",
            bool(heading) and has_added and has_changed,
            f"最新节=[{heading}]，Added={has_added}，Changed={has_changed}",
        )
    )

    # The version the code declares is the newest released version the
    # changelog names — the same claim check-version-claims.py proves.
    init = REPO_ROOT / "src" / "dexatlas" / "__init__.py"
    match = re.search(r'__version__ = "([^"]+)"', init.read_text(encoding="utf-8"))
    version = match.group(1) if match else ""
    released = re.findall(r"^## \[([^\]]+)\] — ", text, re.MULTILINE)
    newest = next((v for v in released if re.match(r"\d+\.\d+\.\d+", v)), "")
    report.add(
        outcome_of(
            "DOC.changelog-version",
            "代码版本与 CHANGELOG 最新发布版本一致",
            bool(version) and version == newest,
            f"__init__.py={version or '未找到'}，CHANGELOG 最新={newest or '未找到'}",
        )
    )


# ---------------------------------------------------------------------------
# Group 2 — report figures and README badges (E3/F4 的对外一致性)
# ---------------------------------------------------------------------------


def check_report_figures(report: Report) -> None:
    """The report's generated figures are internally consistent.

    The figures are measurements, written by refresh-report-figures.py; this
    check only reads them back. Consistency here means: every figure appears
    with one value, and the derived ones add up (fast + slow = total).
    """
    text = REPORT_PATH.read_text(encoding="utf-8")
    figures: dict[str, set[str]] = {}
    for key, value in FIGURE.findall(text):
        figures.setdefault(key, set()).add(value.strip())

    inconsistent = {k: sorted(v) for k, v in figures.items() if len(v) > 1}
    report.add(
        outcome_of(
            "FIG.consistent",
            "报告 fig 标记无同一键多值",
            not inconsistent,
            "一致" if not inconsistent else str(dict(list(inconsistent.items())[:4])),
        )
    )

    def one(key: str) -> int | None:
        values = figures.get(key)
        if not values:
            return None
        try:
            return int(next(iter(values)))
        except ValueError:
            return None

    total, fast, slow = one("tests.total"), one("tests.fast"), one("tests.slow")
    adds_up = None not in (total, fast, slow) and total == fast + slow  # type: ignore[operator]
    report.add(
        outcome_of(
            "FIG.suite-adds-up",
            "tests.total = tests.fast + tests.slow",
            adds_up,
            f"total={total}，fast={fast}，slow={slow}",
        )
    )


def check_readme_badges(report: Report) -> None:
    """The README badges state the numbers the report's figures state."""
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    figures = {k: v.strip() for k, v in FIGURE.findall(report_text)}
    passing = figures.get("suite.passed", "")
    coverage = figures.get("coverage.pct", "").rstrip("%")

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    badge_tests = BADGE_TESTS.search(readme)
    badge_cov = BADGE_COVERAGE.search(readme)

    tests_ok = bool(badge_tests) and badge_tests.group(1) == passing
    cov_ok = bool(badge_cov) and badge_cov.group(1) == coverage
    report.add(
        outcome_of(
            "FIG.badge-tests",
            "README tests 徽章 = 报告 suite.passed",
            tests_ok,
            f"徽章={badge_tests.group(1) if badge_tests else '无'}，报告={passing or '无'}",
        )
    )
    report.add(
        outcome_of(
            "FIG.badge-coverage",
            "README coverage 徽章 = 报告 coverage.pct",
            cov_ok,
            f"徽章={badge_cov.group(1) if badge_cov else '无'}，报告={coverage or '无'}",
        )
    )


# ---------------------------------------------------------------------------
# Group 3 — public contracts the pack's F 组 points at
# ---------------------------------------------------------------------------


def check_contract_sources(report: Report) -> None:
    """F5/F6 的入口存在：契约测试文件与契约实测脚本。"""
    report.add(
        outcome_of(
            "F5.entry",
            "tests/test_public_contracts.py 存在",
            CONTRACT_TEST.is_file(),
            str(CONTRACT_TEST.relative_to(REPO_ROOT)),
        )
    )
    report.add(
        outcome_of(
            "F6.entry",
            "scripts/verify-public-contracts.py 存在",
            VERIFY_CONTRACTS.is_file(),
            str(VERIFY_CONTRACTS.relative_to(REPO_ROOT)),
        )
    )


def check_exit_code_contract(report: Report) -> None:
    """F1：契约表、CLI 源码与契约测试的退出码集合一致。

    The expectation is not restated here: it is read from the contract
    test's ``EXPECTED_EXIT_CODES`` table, so the three places that name the
    codes — the contract table, the CLI constants, and the test that freezes
    them — are compared with *each other*. An expectation copied here would
    have to be updated by hand on every contract change, and a stale copy
    would fail a correct tree (as it did when exit code 6 landed and this
    set still read 0–5).
    """
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    table = contracts.split("### 1.2 退出码", 1)[-1].split("###", 1)[0]
    stated = {int(m) for m in re.findall(r"^\| (\d) \|", table, re.MULTILINE)}

    cli = (REPO_ROOT / "src" / "dexatlas" / "cli" / "main.py").read_text(encoding="utf-8")
    defined = {int(m) for m in re.findall(r"^EXIT_[A-Z_]+ = (\d+)$", cli, re.MULTILINE)}

    test = CONTRACT_TEST.read_text(encoding="utf-8")
    block = test.split("EXPECTED_EXIT_CODES = {", 1)[-1].split("}", 1)[0]
    tested = {int(m) for m in re.findall(r"^\s+(\d+):", block, re.MULTILINE)}
    for name in re.findall(r"^\s+([A-Z][A-Z_]+):", block, re.MULTILINE):
        match = re.search(rf"^{name} = (\d+)$", cli, re.MULTILINE)
        if match:
            tested.add(int(match.group(1)))
    # The implicit success code: typer answers 0 by default, the CLI module
    # defines no constant for it, and the test spells it out as a literal.
    expected = tested | {0}

    report.add(
        outcome_of(
            "F1.exit-codes",
            "退出码契约：契约表、CLI 常量（含隐式成功 0）、契约测试期望一致",
            stated == expected and defined | {0} == expected,
            f"契约表={sorted(stated)}，CLI 常量={sorted(defined)} + 隐式 0，契约测试={sorted(tested)}",
            blocking=True,
        )
    )


def check_mcp_tool_contract(report: Report) -> None:
    """F3：契约表列出的 MCP 工具与测试断言的清单一致。"""
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    section = contracts.split("### 3.1 工具清单", 1)[-1].split("###", 1)[0]
    table_tools = re.findall(r"^\| \d+ \| `([a-z_]+)` \|", section, re.MULTILINE)

    tests = CONTRACT_TEST.read_text(encoding="utf-8")
    block = tests.split("EXPECTED_MCP_TOOLS = {", 1)[-1].split("}", 1)[0]
    test_tools = sorted(re.findall(r'"([a-z_]+)"', block))

    report.add(
        outcome_of(
            "F3.mcp-tools",
            "MCP 工具清单：契约表 = 测试断言",
            sorted(table_tools) == test_tools,
            f"契约表 {len(table_tools)} 个，测试 {len(test_tools)} 个"
            + ("" if sorted(table_tools) == test_tools else "，不一致"),
        )
    )


def check_report_schema_contract(report: Report) -> None:
    """F4：JSON 报告顶层字段与 schema_version，契约表 = 测试断言。"""
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    section = contracts.split("### 5.1 JSON 报告顶层字段", 1)[-1].split("### 5.2", 1)[0]
    table_fields = set(re.findall(r"^\| `([a-z_]+)` \|", section, re.MULTILINE))

    tests = CONTRACT_TEST.read_text(encoding="utf-8")
    block = tests.split("EXPECTED_REPORT_FIELDS = {", 1)[-1].split("}", 1)[0]
    test_fields = set(re.findall(r'"([a-z_]+)"', block))

    report.add(
        outcome_of(
            "F4.report-fields",
            "JSON 报告顶层字段：契约表 = 测试断言",
            table_fields == test_fields,
            f"契约表 {len(table_fields)} 个，测试 {len(test_fields)} 个"
            + (
                ""
                if table_fields == test_fields
                else f"，差异：{sorted(table_fields ^ test_fields)}"
            ),
        )
    )

    json_report = REPO_ROOT / "src" / "dexatlas" / "reports" / "json_report.py"
    version_ok = '"schema_version": 3' in json_report.read_text(encoding="utf-8")
    report.add(
        outcome_of(
            "F4.schema-version",
            "JSON 报告 schema_version 声明为 3",
            version_ok,
            str(json_report.relative_to(REPO_ROOT)),
        )
    )


def check_rest_route_contract(report: Report) -> None:
    """F2 的静态部分：契约测试持有与契约表同源的路由清单（由该测试证明）。"""
    tests = CONTRACT_TEST.read_text(encoding="utf-8")
    has_route_test = "def test_the_rest_route_table_is_the_contract" in tests
    has_exit_test = "def test_the_cli_exit_code_table_is_the_contract" in tests
    has_mcp_test = "def test_the_mcp_tool_table_is_the_contract" in tests
    report.add(
        outcome_of(
            "F2.route-test",
            "契约快照测试覆盖 REST/CLI/MCP 三表",
            has_route_test and has_exit_test and has_mcp_test,
            f"REST={has_route_test}，CLI={has_exit_test}，MCP={has_mcp_test}",
        )
    )


def check_evidence_boundary_contract(report: Report) -> None:
    """D3/G5 的代码侧：证据包 manifest 声明不含 APK、全量源码、未引用字符串，且只装本次分析。"""
    package = REPO_ROOT / "src" / "dexatlas" / "reports" / "evidence_package.py"
    text = package.read_text(encoding="utf-8")
    block = text.split("NOT_INCLUDED = {", 1)[-1].split("}", 1)[0]
    declared = set(re.findall(r'"([a-z_]+)":', block))
    expected = {"apk", "full_sources", "unrelated_strings", "outside_analysis"}
    report.add(
        outcome_of(
            "D3.not-included",
            "证据包 not_included 声明 apk/full_sources/unrelated_strings/outside_analysis",
            declared == expected,
            f"声明={sorted(declared)}",
            blocking=True,
        )
    )


def check_html_offline_contract(report: Report) -> None:
    """D1/D5 的代码侧：HTML 渲染不引用外部资源，且转义后写入。"""
    html = REPO_ROOT / "src" / "dexatlas" / "reports" / "html_report.py"
    text = html.read_text(encoding="utf-8")
    external = re.findall(r"https?://[^\s\"')]+", text)
    # The docstring may mention the promise; only a real attribute would be a
    # violation, so the check looks for loaded resources, not for the word.
    loads = re.findall(r"<(script|link|img|iframe)\b", text)
    report.add(
        outcome_of(
            "D1.no-external",
            "HTML 渲染器源码无外部资源与脚本标签",
            not loads,
            f"外部 URL 引用（含注释）{len(external)} 处，动态标签 {len(loads)} 处",
            blocking=True,
        )
    )
    report.add(
        outcome_of(
            "D5.escape",
            "HTML 渲染器使用 html.escape 处理样本文本",
            "from html import escape" in text or "html.escape" in text,
            "escape 导入存在" if "escape" in text else "未找到 escape",
        )
    )


def check_regression_set_numbers(report: Report) -> None:
    """E1/E5 的静态部分：冻结 20 题清单与完整 92 题的声明同时存在。"""
    frozen = REPO_ROOT / "benchmarks" / "m6_service_set.py"
    text = frozen.read_text(encoding="utf-8")
    prefixes = re.findall(r'^\s{4}"([a-z0-9.-]+)",$', text, re.MULTILINE)
    report.add(
        outcome_of(
            "E1.frozen-20",
            "冻结回归集恰为 20 题",
            len(prefixes) == 20,
            f"读到 {len(prefixes)} 个前缀",
        )
    )

    service = (REPO_ROOT / "docs" / "benchmarks" / "service-regression-set.md").read_text(
        encoding="utf-8"
    )
    full_set = "92" in service
    scripted = (REPO_ROOT / "docs" / "benchmarks" / "m6-level1-scripted.md").is_file()
    report.add(
        outcome_of(
            "E5.both-reported",
            "冻结 20 题与完整 92 题的报告入口同时存在",
            full_set and scripted,
            f"92 题声明={'service-regression-set.md' and full_set}，层级1报告存在={scripted}",
        )
    )


def check_demo_app_present(report: Report) -> None:
    """A4 的入口：一方 demo APK 与其构建脚本同在。"""
    apk = REPO_ROOT / "examples" / "demo-app" / "demo.apk"
    build = REPO_ROOT / "scripts" / "build-demo-apk.sh"
    report.add(
        outcome_of(
            "A4.demo-present",
            "demo.apk 与构建脚本在仓库中",
            apk.is_file() and build.is_file(),
            f"apk={apk.is_file()}，build 脚本={build.is_file()}",
        )
    )


# ---------------------------------------------------------------------------
# Group 4 — the quality gates the pack names (only: can they run?)
# ---------------------------------------------------------------------------


def check_gate_commands(report: Report) -> None:
    """每个门禁命令的入口存在——不执行全量门禁，只证明命令可被调用。

    判据只看项目自己的 venv，不看 PATH：venv 是树的一部分，PATH 是环境的
    一部分。机器上碰巧装了全局工具时，PATH 那一支会让一个还没有同步过
    venv 的工作区判绿；而 CI 的 PATH 上只有 venv，于是同一棵树在两个平台
    上得到不同的答案。venv 缺失时判「需人工」而不是「失败」——那说明环境
    没建好，不是树有问题。
    """
    venv_bin = REPO_ROOT / ".venv" / "Scripts"
    posix_bin = REPO_ROOT / ".venv" / "bin"
    venv_present = venv_bin.is_dir() or posix_bin.is_dir()
    for check_id, binary, argv in GATE_COMMANDS:
        # Script gates are files in this repository, not PATH lookups.
        if binary == "python" and argv[1].endswith(".py"):
            script_exists = (REPO_ROOT / argv[1]).is_file()
            report.add(
                outcome_of(
                    check_id,
                    f"门禁可执行：{' '.join(argv[:2])}",
                    script_exists,
                    f"脚本在仓库中={script_exists}",
                )
            )
            continue
        in_venv = (venv_bin / f"{binary}.exe").is_file() or (posix_bin / binary).is_file()
        if in_venv:
            report.add(
                outcome_of(
                    check_id,
                    f"门禁可执行：{' '.join(argv[:2])}",
                    True,
                    "venv 中存在",
                )
            )
        elif not venv_present:
            report.add(
                manual(
                    check_id,
                    f"门禁可执行：{' '.join(argv[:2])}",
                    "工作区还没有 .venv（先 uv sync），无法判定；这属于环境未就绪，不是树的问题",
                )
            )
        else:
            report.add(
                outcome_of(
                    check_id,
                    f"门禁可执行：{' '.join(argv[:2])}",
                    False,
                    "venv 中未找到该入口",
                )
            )


def check_scripts_runnable(report: Report) -> None:
    """验收包点名的脚本存在且声明了可运行入口（不真正运行）。"""
    for check_id, path in (
        ("F6.script", VERIFY_CONTRACTS),
        ("GATE.refresh", REPO_ROOT / "scripts" / "refresh-report-figures.py"),
        ("GATE.citations", REPO_ROOT / "scripts" / "check-doc-citations.py"),
        ("GATE.version-claims", REPO_ROOT / "scripts" / "check-version-claims.py"),
        ("GATE.remap", REPO_ROOT / "scripts" / "remap-citations.py"),
    ):
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        runnable = 'if __name__ == "__main__":' in text
        report.add(
            outcome_of(
                check_id,
                f"脚本可运行：{path.name}",
                path.is_file() and runnable,
                f"存在={path.is_file()}，main 入口={runnable}",
            )
        )


def check_selftest_regressions(report: Report) -> None:
    """验收包 §6.2 点名的 M8-1 回归测试存在（回归测试是验收证据）。"""
    tests_dir = REPO_ROOT / "tests"
    found = [
        p.name
        for p in sorted(tests_dir.glob("test_*.py"))
        if "verify_citations" in p.read_text(encoding="utf-8")
    ]
    report.add(
        outcome_of(
            "M8-1.regression",
            "verify_citations 回归测试存在（M8-1 教训）",
            bool(found),
            "覆盖文件：" + ", ".join(found[:4]) if found else "未找到",
        )
    )


# ---------------------------------------------------------------------------
# Group H — the three gaps the reader dry run found
# ---------------------------------------------------------------------------
#
# ``docs/reports/reader-dry-run.md`` walked the M10 material on a clean
# machine and found three things the material did not check:
#
# 1. the setup step did not have to fetch the third-party samples, so the
#    integration cases silently skipped and the exit code was still 0;
# 2. A6 asks the reader to capture a degraded run, but the CLI cannot render
#    a past run and a new analysis replaces the project's latest one, so the
#    evidence has to be written down *at the time*;
# 3. the evidence package holds four entries while the CLI prints "3 files"
#    (the count of the reports the manifest lists).
#
# A check that cannot see these is a check that lets the same gap back in.

#: Chinese numerals the materials use for small counts.
_SMALL_NUMBERS = {
    "一": 1,
    "两": 2,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

#: "27 个集成用例会 skip" — the count the material states before the word.
_SKIP_COUNT_BEFORE = re.compile(r"(\d+)\s*个[^\n]{0,12}?skip")
#: "skip 27 个" — the count the material states after the word.
_SKIP_COUNT_AFTER = re.compile(r"skip(?:ped)?[^\d\n]{0,4}?(\d+)\s*个")
#: "两个第三方集成样本" / "2 个 APK" — how many samples the material claims.
_SAMPLE_COUNT = re.compile(
    r"([两三四五六七八九十\d]+)\s*[个份]\s*(?:第三方集成样本|第三方样本|APK)"
)
#: A line that runs the fetch script. Mentioning the script is not the same
#: as telling the reader to run it, and the gap this check exists for is the
#: step that is not there.
_FETCH_STEP = re.compile(r"(?m)^[>\s]*(?:bash|sh)\s+scripts/fetch-fixtures\.sh\s*$")
#: The ways a document says "exit code 0 does not mean everything ran".
_NEGATIONS = ("不说明", "不代表", "不等于", "不意味", "不能证明", "并非")
#: The ways a document could promise that a past run can be looked at later.
_REPLAY_PROMISES = ("事后可以再", "之后可以再查", "随时可以回看", "可以重新渲染", "稍后再看")
#: Why the evidence has to be captured at the time.
_ONSITE_REASONS = ("最新一次运行", "换成新的一次", "覆盖", "重跑")


def _blocks(text: str) -> list[str]:
    """The document's paragraphs, with the blockquote markers stripped.

    A material states a fact in a paragraph, so a check that looks for a
    fact has to look inside the paragraph it belongs to: the caveat about
    the exit code means something only when it hangs off the step that
    causes the skips.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip("> ").strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _as_count(token: str) -> int | None:
    """A number the materials wrote, in digits or in Chinese numerals."""
    if token.isdigit():
        return int(token)
    if len(token) == 1 and token in _SMALL_NUMBERS:
        return _SMALL_NUMBERS[token]
    return None


def _stated_numbers(text: str, pattern: re.Pattern[str]) -> set[int]:
    """Every distinct number ``pattern`` finds in ``text``."""
    values: set[int] = set()
    for token in pattern.findall(text):
        value = _as_count(token)
        if value is not None:
            values.add(value)
    return values


def _stated_skip_counts(text: str) -> set[int]:
    """How many cases the material says will skip without the samples."""
    before = {int(m) for m in _SKIP_COUNT_BEFORE.findall(text)}
    after = {int(m) for m in _SKIP_COUNT_AFTER.findall(text)}
    return before | after


def _fixture_names(script_text: str) -> list[str]:
    """The APKs ``scripts/fetch-fixtures.sh`` fetches."""
    if "FILES=(" not in script_text:
        return []
    block = script_text.split("FILES=(", 1)[-1].split(")", 1)[0]
    return re.findall(r'"([^"]+\.apk)"', block)


def check_fixture_precondition(report: Report, root: Path = REPO_ROOT) -> None:
    """装环境那一步必须抓第三方样本：不抓的后果写在材料里，且各材料一致。

    The reader dry run installed the tool, never fetched the samples, and
    the suite skipped 27 integration cases with exit code 0. A step whose
    failure is silent cannot be left to the reader's judgement, so the
    material has to say the step exists, how many samples it is, what
    happens when it is skipped, and that exit code 0 does not mean every
    case ran.
    """
    script_text = (root / FIXTURE_SCRIPT_REL).read_text(encoding="utf-8")
    reader_text = (root / READER_PATH.relative_to(REPO_ROOT)).read_text(encoding="utf-8")
    kit_text = (root / READER_KIT_REL).read_text(encoding="utf-8")
    summary_text = (root / EXEC_SUMMARY_REL).read_text(encoding="utf-8")

    names = _fixture_names(script_text)
    expected = len(names)

    step_present = bool(_FETCH_STEP.search(reader_text))
    counts = {
        "读者包": _stated_numbers(reader_text, _SAMPLE_COUNT),
        "工具包": _stated_numbers(kit_text, _SAMPLE_COUNT),
        "摘要": _stated_numbers(summary_text, _SAMPLE_COUNT),
    }
    counts_ok = expected > 0 and all(value <= {expected} for value in counts.values())
    counts_ok = counts_ok and expected in counts["读者包"]

    skips = {
        "读者包": _stated_skip_counts(reader_text),
        "工具包": _stated_skip_counts(kit_text),
        "摘要": _stated_skip_counts(summary_text),
    }
    reader_skips = skips["读者包"]
    skips_ok = bool(reader_skips) and all(value == reader_skips for value in skips.values())

    caveat_ok = any(
        "退出码 0" in block
        and any(word in block for word in _NEGATIONS)
        and _stated_skip_counts(block)
        for block in _blocks(reader_text)
    )

    fixture_dir = root / FIXTURE_DIR_REL
    local = sorted(p.name for p in fixture_dir.glob("*.apk")) if fixture_dir.is_dir() else []

    report.add(
        outcome_of(
            "FIXTURE.precondition",
            "装环境必抓第三方样本：不抓的 skip 后果与「退出码 0」的告诫写在材料里",
            step_present and counts_ok and skips_ok and caveat_ok,
            f"本机样本 {len(local)}/{expected}"
            + ("（未抓取，集成用例会 skip）" if len(local) < expected else "")
            + f"；脚本声明 {expected} 个（{', '.join(names) or '未读到'}）"
            + f"；材料所述样本数 {counts}"
            + f"；所述 skip 数 {skips}"
            + f"；退出码 0 的告诫={caveat_ok}",
        )
    )


def check_a6_onsite_record(report: Report, root: Path = REPO_ROOT) -> None:
    """A6 的降级证据要能回看：材料说的能力与工具实际能力一致。

    The CLI renders one particular run: ``dexatlas runs <pid> --run <rid>``
    reads a run's own record back, and ``dexatlas render <pid> <rid>`` writes
    a published run's reports and evidence package to a directory. What the
    material says about that has to stay true: only a run that *completed and
    is still the published one* renders, a new analysis replaces the
    published snapshot, and a failed or cancelled run published nothing. A
    material that drops that bound — or still claims there is no way to look
    at a run again — sends the reader back to a workspace that does not hold
    what was promised.
    """
    cli_text = (root / CLI_REL).read_text(encoding="utf-8")
    storage_text = (root / STORAGE_REL).read_text(encoding="utf-8")
    reader_text = (root / READER_PATH.relative_to(REPO_ROOT)).read_text(encoding="utf-8")
    blocks = _blocks(reader_text)

    cli_can_select_run = "run_id" in cli_text or "run-id" in cli_text
    publish_replaces = "UPDATE projects SET published_run_id" in storage_text

    claims_no_replay = any("渲染" in block and "没有" in block for block in blocks)
    says_onsite = any("当场" in block for block in blocks)
    reason_ok = any(
        "当场" in block and any(marker in block for marker in _ONSITE_REASONS) for block in blocks
    )
    promises_replay = any(marker in reader_text for marker in _REPLAY_PROMISES)
    # The capability stated, and the bound that makes the statement true:
    # only the run that is still the published one renders. The bound is
    # stated by the caveat's own words, not by any mention of a published
    # run — describing what `render` can do names a published run too.
    states_capability = any(
        ("runs" in block and "--run" in block) or ("render" in block and "run" in block)
        for block in blocks
    )
    states_bound = any("仍是已发布" in block for block in blocks)

    if cli_can_select_run:
        ok = (
            states_capability
            and states_bound
            and says_onsite
            and not claims_no_replay
            and not promises_replay
        )
    else:
        ok = claims_no_replay and says_onsite and reason_ok and not promises_replay

    report.add(
        outcome_of(
            "A6.on-the-spot",
            "A6 降级证据要能回看：材料对「按 run 回看」的表述与 CLI 实际能力一致",
            ok,
            f"CLI 能按 run 选运行={cli_can_select_run}；新分析替换已发布运行={publish_replaces}"
            f"；材料说工具不能回看={claims_no_replay}"
            f"；材料写了 runs/render 能力={states_capability}"
            f"；材料写明只有已发布那次能渲染={states_bound}"
            f"；要求当场记录={says_onsite}；说明了原因={reason_ok}"
            f"；承诺无边界的事后可查={promises_replay}",
        )
    )


def check_package_entry_count(report: Report, root: Path = REPO_ROOT) -> None:
    """证据包里的条目数：材料说的数目要等于包里实际有的条目。

    The archive holds every file the manifest lists *plus* the manifest
    itself, so the number a reader counts in the zip is one more than the
    manifest's count. The CLI has to print the archive's count — a print
    built from the manifest's count wears the archive's name and is one
    short of what the reader finds — and the material has to state the
    archive's entry count and how it is made up, or the reader counts a
    different number than the material promised and files it as a defect.
    """
    package_src = (root / EVIDENCE_PACKAGE_REL).read_text(encoding="utf-8")
    cli_src = (root / CLI_REL).read_text(encoding="utf-8")
    reader_text = (root / READER_PATH.relative_to(REPO_ROOT)).read_text(encoding="utf-8")

    roles = []
    if "_REPORT_PATHS = {" in package_src:
        role_block = package_src.split("_REPORT_PATHS = {", 1)[-1].split("}", 1)[0]
        roles = re.findall(r'"(\w+)":\s*"([^"]+)"', role_block)

    # The manifest's own file list is built by ``package_manifest`` from the
    # packaged files' dictionary — the dictionary the packager filled, which
    # never holds the manifest itself. A manifest that listed itself would
    # spell ``manifest.json`` inside that function; one that lists a hand-
    # built array would not read the dictionary at all.
    manifest_fn = ""
    if "def package_manifest(" in package_src:
        manifest_fn = package_src.split("def package_manifest(", 1)[-1].split("\ndef ", 1)[0]
    manifest_written = (
        'archive.writestr("manifest.json"' in package_src
        or "archive.writestr(MANIFEST_NAME" in package_src
    )
    manifest_not_listed = "files.items()" in manifest_fn and '"manifest.json"' not in manifest_fn
    # The printed number has to be the archive's own count, and it has to
    # come from the package module — the one place that knows what the
    # archive holds — or be the manifest's count plus the manifest itself.
    # A print built from ``len(manifest['files'])`` alone is the manifest's
    # count wearing the archive's name.
    cli_prints_manifest_count = (
        re.search(r"len\(manifest\['files'\]\)\}\s*files", cli_src) is not None
    )
    cli_prints_archive_count = (
        re.search(r"package_\w+\(\s*manifest\s*\)", cli_src) is not None
        or re.search(r"len\(manifest\['files'\]\)\s*\+\s*1", cli_src) is not None
    )

    entries = _stated_numbers(reader_text, re.compile(r"(\d+)\s*个条目"))
    reports = _stated_numbers(reader_text, re.compile(r"(\d+)\s*份报告"))
    cli_files = _stated_numbers(reader_text, re.compile(r"「(\d+)\s*files」"))

    counts_ok = (
        bool(roles)
        and len(entries) == 1
        and len(reports) == 1
        and entries == {next(iter(reports)) + 1}
        and reports == {len(roles)}
    )

    report.add(
        outcome_of(
            "PACKAGE.entry-count",
            "证据包条目数：材料说的数目 = 报告数 + manifest，CLI 打印归档里的条目数",
            counts_ok
            and manifest_written
            and manifest_not_listed
            and cli_prints_archive_count
            and not cli_prints_manifest_count,
            f"代码：报告角色 {len(roles)} 个，manifest 写入归档={manifest_written}"
            f"，不进清单={manifest_not_listed}，CLI 打印归档计数={cli_prints_archive_count}"
            f"，CLI 打印清单计数={cli_prints_manifest_count}"
            f"；材料：条目数 {entries}，报告数 {reports}，材料引用的 CLI 数字 {cli_files}",
        )
    )


# ---------------------------------------------------------------------------
# The checks only a reader on a real machine can decide
# ---------------------------------------------------------------------------


MANUAL_CHECKS: tuple[tuple[str, str, str, bool], ...] = (
    ("A1", "取得固定副本并记录 commit", "需要读者 clone 并 checkout 指定 commit", False),
    (
        "A2",
        "依赖安装退出码 0（★）",
        "需要真实机器安装；装环境那一步还要抓第三方样本——不抓则集成用例会 skip，"
        "而退出码 0 不说明该跑的都跑了，跑完整套件时每一条 skip 都要能说出是哪一类",
        True,
    ),
    ("A3", "backends 输出与实际安装一致", "依赖机器上的后端", False),
    ("A4", "首次分析计数（★）", "需要运行分析，脚本只验证入口存在", True),
    ("A5", "三格式报告同源", "需要运行分析", False),
    ("A6", "后端缺失降级（★）", "需要卸载后端后实测", True),
    ("A7", "耗时与卡点记录", "读者体验记录", False),
    ("B1", "案例全程走通（★）", "需要真实执行案例命令", True),
    ("B2", "manifest 计数复述", "需要运行 analyze/manifest", False),
    ("B3", "search 命中复述", "需要运行 search", False),
    ("B4", "source locator 复述", "需要运行 source", False),
    ("B5", "xrefs 两个计数解释", "需要运行 xrefs", False),
    ("B6", "结论/限制复述", "读者理解检查", False),
    ("C1", "3 条 evidence 字段核对（★）", "需要打开真实分析工作区", True),
    ("C2", "locator 解析（★）", "需要真实工作区", True),
    ("C3", "三级语义举例（★）", "读者理解检查（代码侧已由 D5/契约测试覆盖）", True),
    ("C4", "计数复算", "需要真实报告", False),
    ("C5", "verify_package 通过（★）", "需要真实证据包", True),
    ("C6", "verify_citations 通过且可搬迁（★）", "需要真实证据包", True),
    ("D1", "HTML 断网打开（★）", "浏览器行为；代码侧已检查无外部引用", True),
    ("D2", "三格式计数一致（★）", "需要同一次分析的三份输出", True),
    ("D3", "包内容与 not_included 一致（★）", "需要真实证据包；声明已静态核对", True),
    ("D4", "包内引用路径可打开", "需要真实证据包", False),
    ("D5", "异常文本只作文本显示", "浏览器行为；代码侧已检查 escape", False),
    ("E1", "范围复述", "读者理解检查；20 题清单已静态核对", False),
    ("E2", "层级区分复述（★）", "读者理解检查", True),
    ("E3", "不冒充模型能力（★）", "引用方式检查，属人工审阅", True),
    ("E4", "失败解释", "读者理解检查", False),
    ("E5", "完整集同报", "报告存在性已静态核对；同报完整性需人工", False),
    ("F1", "退出码实测 0/1/2（★）", "需要运行 CLI；0–6 语义已静态核对", True),
    ("F2", "REST 抽查 3 端点", "verify-public-contracts.py 覆盖；读者需复跑", False),
    ("F3", "MCP 工具清单/只读注解", "清单已静态核对；协议实测需运行", False),
    ("F4", "报告 schema 抽查", "字段清单已静态核对；响应实测需运行", False),
    ("F5", "契约快照测试全过（★）", "需要运行 pytest；入口与三表覆盖已核对", True),
    ("F6", "契约实测脚本退出码 0", "需要真实运行（起服务、装依赖）", False),
    ("G1", "坏输入退出码 2", "需要运行 CLI", False),
    ("G2", "后端缺失降级（★）", "需要卸载后端实测", True),
    ("G3", "超时降级与 M8-4 缺口（★）", "需要注入超时实测", True),
    ("G4", "重复分析幂等", "需要运行两次分析", False),
    ("G5", "证据隔离（★）", "需要真实证据包；not_included 已静态核对", True),
)


def check_manual_items(report: Report) -> None:
    for item_id, title, why, blocking in MANUAL_CHECKS:
        report.add(manual(item_id, title, why, blocking))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


CHECKS: tuple[Callable[[Report], None], ...] = (
    check_pack_structure,
    check_reader_package,
    check_document_links,
    check_changelog,
    check_report_figures,
    check_readme_badges,
    check_contract_sources,
    check_exit_code_contract,
    check_mcp_tool_contract,
    check_report_schema_contract,
    check_rest_route_contract,
    check_evidence_boundary_contract,
    check_html_offline_contract,
    check_regression_set_numbers,
    check_demo_app_present,
    check_gate_commands,
    check_scripts_runnable,
    check_selftest_regressions,
    check_fixture_precondition,
    check_a6_onsite_record,
    check_package_entry_count,
    check_manual_items,
)


def main(argv: list[str] | None = None) -> int:
    # A failed check names what broke, and the name may carry any character
    # the documents carry. A console that cannot encode it -- GBK on a
    # Chinese Windows -- would kill the script halfway through its report,
    # and the exit code a crash gives is the same 1 a real finding gives.
    # The output is UTF-8 with replacement, so the report finishes on every
    # machine and the exit code means one thing. ``--json`` redirects to a
    # file in this project's own how-to, so the redirected case is the
    # common one, not the exception.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            continue

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable JSON summary instead of the table",
    )
    args = parser.parse_args(argv)

    report = Report()
    for check in CHECKS:
        check(report)

    counts = report.counts()
    if args.json:
        import json

        print(
            json.dumps(
                {
                    "pass": counts["pass"],
                    "fail": counts["fail"],
                    "manual": counts["manual"],
                    "pass_rate_over_decided": report.rate(),
                    "outcomes": [
                        {
                            "id": o.check_id,
                            "title": o.title,
                            "state": o.state,
                            "blocking": o.blocking,
                            "detail": o.detail,
                        }
                        for o in report.outcomes
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        width = max(len(o.check_id) for o in report.outcomes)
        for o in report.outcomes:
            mark = {"pass": "通过", "fail": "失败", "manual": "需人工"}[o.state]
            star = "★" if o.blocking else " "
            print(
                f"[{mark}] {o.check_id:<{width}} {star} {o.title}"
                + (f" —— {o.detail}" if o.detail else "")
            )
        print(
            f"\n自动化判定：通过 {counts['pass']}，失败 {counts['fail']}，"
            f"需人工 {counts['manual']}；已判定项通过率 {report.rate()}"
        )
        print("需人工项不是失败：它们要一位读者在真实机器上按验收包执行并记录。")

    return 0 if counts["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
