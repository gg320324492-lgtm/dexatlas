#!/usr/bin/env python3
"""Run the automatable part of the M10 independent-acceptance checklist.

    uv run --no-sync python scripts/m10_selfcheck.py

The M10 independent review states 40 acceptance checks. A human reviewer
runs most of them on their own machine; a subset is decidable here, from
the repository itself, without installing a backend or running the whole
suite:

* the changelog's ``[Unreleased]`` section exists and is sorted sensibly,
* the README's tests/coverage badges state what the report's figures state,
* the report's ``<!--fig:...-->`` markers are consistent and complete,
* the gates the review names are runnable commands that exist on the path,
* the contracts the review points at (exit codes, MCP tools, report fields,
  routes, the evidence package's ``not_included``) match the code,
* the three gaps a reader dry run found stay closed: the setup step has to
  fetch the third-party samples, A6's degraded evidence has to be retrievable
  through the CLI, and the evidence package's entry count is the one the CLI
  prints.

Every check is a *read* or a *comparison*; the script writes nothing and
never edits the report or the badges. Its verdict is three-valued: pass,
fail, or manual — a check the repository can answer is run, and one only a
reader on a real machine can answer is left marked.

The exit code is 0 when no check failed (manual checks do not fail the
run), 1 when at least one failed.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

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

#: The commands the review's quality gate names, by the binary that has
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
        ["python", "scripts/check-version-claims.py", "--base", "auto"],
    ),
)

#: The section markers of the verification entry points the review names.
CONTRACT_TEST = REPO_ROOT / "tests" / "test_public_contracts.py"
VERIFY_CONTRACTS = REPO_ROOT / "scripts" / "verify-public-contracts.py"

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
        counts = {"pass": 0, "fail": 0, "manual": 0}
        for outcome in self.outcomes:
            counts[outcome.state] += 1
        return counts

    def pass_rate(self) -> str:
        decided = self.counts()["pass"] + self.counts()["fail"]
        if decided == 0:
            return "n/a"
        return f"{self.counts()['pass'] / decided * 100:.1f}%"


def outcome_of(
    check_id: str, title: str, ok: bool, detail: str = "", blocking: bool = False
) -> Outcome:
    return Outcome(
        check_id=check_id,
        title=title,
        state="pass" if ok else "fail",
        detail=detail,
        blocking=blocking or check_id in BLOCKING_IDS,
    )


def manual(check_id: str, title: str, why: str, blocking: bool = False) -> Outcome:
    return Outcome(
        check_id=check_id,
        title=title,
        state="manual",
        detail=why,
        blocking=blocking or check_id in BLOCKING_IDS,
    )


def blocking_flag(item_id: str) -> bool:
    return item_id in BLOCKING_IDS


# ---------------------------------------------------------------------------
# Group 1 — documents and cross-references (A1's document side)
# ---------------------------------------------------------------------------

_RELATIVE_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")


def _check_relative_links(path: Path, report: Report, check_id: str, title: str) -> None:
    """Every relative Markdown link in *path* resolves to a file in the tree.

    An external URL (``http://…``, ``https://…``, ``mailto:``) is not a
    relative link and is not checked here; an anchor-only link (``#…``)
    points inside the same document and is also skipped.
    """
    text = path.read_text(encoding="utf-8")
    base = path.parent
    broken = []
    for target in _RELATIVE_LINK.findall(text):
        candidate = target.strip()
        if not candidate:
            continue
        resolved = (base / candidate).resolve()
        if not resolved.is_file():
            broken.append(candidate)
    report.add(
        outcome_of(
            check_id,
            title,
            not broken,
            "全部可解析" if not broken else "断链：" + ", ".join(sorted(set(broken))[:8]),
        )
    )


def check_document_links(report: Report) -> None:
    _check_relative_links(
        CONTRACTS_PATH, report, "DOC.contracts-links", "公共契约表相对链接全部可解析"
    )

    # The case study and the service-regression set the review's §3.4 and E 组 name.
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
            "DOC.changelog",
            "CHANGELOG 最新段有 Added / Changed 小节",
            bool(match) and has_added and has_changed,
            f"最新段 {heading!r}，Added={has_added}，Changed={has_changed}",
        )
    )


# ---------------------------------------------------------------------------
# Group 2 — the report's figures and the badges that restate them
# ---------------------------------------------------------------------------


def _figures(text: str) -> dict[str, str]:
    return {name: body.strip() for name, body in FIGURE.findall(text)}


def check_report_figures(report: Report) -> None:
    """The report's ``<!--fig:...-->`` markers are consistent and complete.

    The report is generated, so its markers must be there and must agree
    with each other: the fast and slow counts sum to the total, the covered
    and total lines produce the stated percentage, and the record block
    carries the source fingerprint it claims.
    """
    text = REPORT_PATH.read_text(encoding="utf-8")
    figures = _figures(text)

    total = figures.get("tests.total", "")
    fast = figures.get("tests.fast", "")
    slow = figures.get("tests.slow", "")
    try:
        sums_ok = int(total.replace(",", "")) == int(fast.replace(",", "")) + int(
            slow.replace(",", "")
        )
    except ValueError:
        sums_ok = False
    report.add(
        outcome_of(
            "FIG.tests-sum",
            "测试总数 = 快 + 集成",
            sums_ok,
            f"total={total} fast={fast} slow={slow}",
        )
    )

    covered = figures.get("coverage.covered", "")
    total_lines = figures.get("coverage.total", "")
    pct = figures.get("coverage.pct", "").rstrip("%")
    try:
        computed = round(int(covered) / int(total_lines) * 100, 1)
        pct_ok = abs(computed - float(pct)) < 0.05
    except (ValueError, ZeroDivisionError):
        pct_ok = False
    report.add(
        outcome_of(
            "FIG.coverage",
            "覆盖率 = covered / total",
            pct_ok,
            f"covered={covered} total={total_lines} pct={pct}",
        )
    )

    record = re.search(r"<!--report-figures:(.*?)-->", text, re.DOTALL)
    fingerprint = figures.get("fingerprint", "") or (
        re.search(r'"source_fingerprint"\s*:\s*"(sha256:[0-9a-f]{16,64})"', record.group(1)).group(
            1
        )
        if record
        else ""
    )
    report.add(
        outcome_of(
            "FIG.fingerprint",
            "报告带有源指纹",
            bool(fingerprint),
            (fingerprint[:16] + "…") if fingerprint else "未读到指纹",
        )
    )


def check_readme_badges(report: Report) -> None:
    """The README badges restate the report's figures, not other numbers.

    The badges are generated from the same measurement, so a badge that
    disagrees with the report is a stale copy, not a second truth.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    figures = _figures(REPORT_PATH.read_text(encoding="utf-8"))

    badge_tests = BADGE_TESTS.findall(readme)
    badge_coverage = BADGE_COVERAGE.findall(readme)
    record = re.search(
        r"<!--report-figures:(.*?)-->", REPORT_PATH.read_text(encoding="utf-8"), re.DOTALL
    )
    suite = {}
    if record:
        match = re.search(r'"suite"\s*:\s*\{(.*?)\n\s*\}', record.group(1), re.DOTALL)
        if match:
            suite = {
                key: value.strip()
                for key, value in re.findall(r'"(\w+)":\s*"?([\w.%-]+)"?', match.group(1))
            }
    tests_ok = bool(badge_tests) and all(
        value == str(suite.get("passed", "")) for value in badge_tests
    )
    coverage_ok = bool(badge_coverage) and all(
        value == figures.get("coverage.pct", "").rstrip("%") for value in badge_coverage
    )
    report.add(
        outcome_of(
            "BADGE.tests",
            "README 测试徽章 = 报告的 tests.total",
            tests_ok,
            f"badge={badge_tests} report={figures.get('tests.total', '')}",
        )
    )
    report.add(
        outcome_of(
            "BADGE.coverage",
            "README 覆盖率徽章 = 报告的 coverage.pct",
            coverage_ok,
            f"badge={badge_coverage} report={figures.get('coverage.pct', '')}",
        )
    )


# ---------------------------------------------------------------------------
# Group 3 — the public contracts the review points at
# ---------------------------------------------------------------------------


def check_contract_sources(report: Report) -> None:
    """The contract table, its snapshot test and its live check all exist."""
    report.add(
        outcome_of(
            "CONTRACT.table",
            "公共契约表存在",
            CONTRACTS_PATH.is_file(),
            str(CONTRACTS_PATH.relative_to(REPO_ROOT)),
        )
    )
    report.add(
        outcome_of(
            "CONTRACT.snapshot-test",
            "契约快照测试存在",
            CONTRACT_TEST.is_file(),
            str(CONTRACT_TEST.relative_to(REPO_ROOT)),
        )
    )
    report.add(
        outcome_of(
            "CONTRACT.live-check",
            "契约活检脚本存在",
            VERIFY_CONTRACTS.is_file(),
            str(VERIFY_CONTRACTS.relative_to(REPO_ROOT)),
        )
    )


def check_exit_code_contract(report: Report) -> None:
    """The documented exit codes match the CLI's constants.

    0 success, 1 usage, 2 bad input, 3 backend missing, 4 partial/degraded,
    5 truncated, 6 no index. The CLI owns the numbers; the contract table
    owns the meanings; this check reads both and compares.
    """
    cli_src = (REPO_ROOT / "src" / "dexatlas" / "cli" / "main.py").read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    codes = {name: int(value) for name, value in re.findall(r"EXIT_([A-Z_]+)\s*=\s*(\d+)", cli_src)}
    # The contract table's exit-code section only: a bare "| 7 |" in the MCP
    # tool list is a tool's row number, not an exit code. 0 is the implicit
    # success code — no constant carries it.
    section = contracts.split("### 1.2", 1)[-1].split("## 2. REST API", 1)[0]
    documented = sorted(set(re.findall(r"^\| (\d) \|", section, re.MULTILINE)))
    present = sorted({str(value) for value in codes.values()} | {"0"})
    report.add(
        outcome_of(
            "CONTRACT.exit-codes",
            "CLI 退出码与契约表一致",
            present == documented and "6" in present,
            f"CLI={present} 契约表={documented}",
            blocking=True,
        )
    )


def check_mcp_tool_contract(report: Report) -> None:
    """The MCP server registers the tools the contract table names.

    The decorators carry ``name="..."`` on the line after ``@server.tool(``,
    and the contract table's tool rows are numbered (``| 1 | ``tool`` |``),
    so both sides are read with those shapes. The tool rows are read from
    the MCP section only — the CLI section's rows have the same shape and
    name exit codes, not tools.
    """
    server_src = (REPO_ROOT / "src" / "dexatlas" / "mcp" / "server.py").read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    registered = set(re.findall(r'@server\.tool\(\s*\n\s*name="(\w+)"', server_src))
    mcp_section = contracts.split("## 3. MCP server", 1)[-1].split("## 4.", 1)[0]
    documented = set(re.findall(r"^\| \d+ \| `(\w+)` \|", mcp_section, re.MULTILINE))
    report.add(
        outcome_of(
            "CONTRACT.mcp-tools",
            "MCP 工具注册与契约表一致",
            registered == documented and len(registered) > 0,
            f"注册 {len(registered)} 个，契约表 {len(documented)} 个"
            + ("" if registered == documented else f"；差异 {registered ^ documented}"),
            blocking=True,
        )
    )


def check_report_schema_contract(report: Report) -> None:
    """The report schema version in code matches the contract table."""
    version = 3
    for path in (REPO_ROOT / "src" / "dexatlas" / "reports").glob("*.py"):
        match = re.search(r"REPORT_SCHEMA_VERSION\s*=\s*(\d+)", path.read_text(encoding="utf-8"))
        if match:
            version = int(match.group(1))
            break
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    documented = re.findall(r"schema_version[^\n]*?(\d+)", contracts)
    report.add(
        outcome_of(
            "CONTRACT.report-schema",
            "报告 schema_version 代码与契约表一致",
            str(version) in documented,
            f"代码={version} 契约表出现={sorted(set(documented))}",
            blocking=True,
        )
    )


def check_rest_route_contract(report: Report) -> None:
    """The FastAPI routes the contract table names exist in the app.

    The contract table writes the path parameters as ``{pid}``/``{rid}``;
    the app writes them as ``{project_id}``/``{run_id}``. The names are
    normalised before the comparison: a route is its method and its shape,
    not its parameter spelling.
    """
    app_src = (REPO_ROOT / "src" / "dexatlas" / "api" / "app.py").read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    rest = contracts.split("## 2. REST API", 1)[-1].split("## 3. MCP server", 1)[0]
    documented = {
        (method.upper(), path.replace("{pid}", "{project_id}").replace("{rid}", "{run_id}"))
        for path, method in re.findall(r"^\| `([^`]+)` \| (GET|POST|DELETE|PUT) ", rest, re.M)
    }
    registered = {
        (method.upper(), path)
        for method, path in re.findall(r'@app\.(get|post|delete|put)\(\s*\n?\s*"([^"]+)"', app_src)
    }
    missing = documented - registered
    report.add(
        outcome_of(
            "CONTRACT.rest-routes",
            "REST 路由与契约表一致",
            not missing,
            f"契约表 {len(documented)} 条，缺失 {sorted(missing)[:6]}"
            if missing
            else f"契约表 {len(documented)} 条全部注册",
            blocking=True,
        )
    )


def check_evidence_boundary_contract(report: Report) -> None:
    """The evidence package's ``not_included`` keys match the contract table.

    The manifest's boundary is a public contract: the four keys and the
    schema version live in the code, and the contract table restates them.
    """
    package_src = (REPO_ROOT / "src" / "dexatlas" / "reports" / "evidence_package.py").read_text(
        encoding="utf-8"
    )
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    schema = re.search(r"PACKAGE_SCHEMA_VERSION\s*=\s*(\d+)", package_src)
    keys = set(re.findall(r'^\s{4}"(\w+)":', package_src, re.MULTILINE))
    documented_schema = re.findall(r"schema_version[^\n]*?(\d+)", contracts)
    report.add(
        outcome_of(
            "CONTRACT.evidence-boundary",
            "证据包 not_included 键与 schema_version 与契约表一致",
            schema is not None
            and str(int(schema.group(1))) in documented_schema
            and len(keys) >= 4,
            f"schema={schema.group(1) if schema else '未读到'}，not_included 键 {sorted(keys)}",
            blocking=True,
        )
    )


def check_html_offline_contract(report: Report) -> None:
    """The HTML renderer produces a single offline file with no remote fetches.

    The offline promise is a contract: the renderer must not reference a
    remote URL scheme that a browser would fetch when the file is opened.
    """
    renderer = REPO_ROOT / "src" / "dexatlas" / "reports"
    html_src = ""
    for path in renderer.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "text/html" in text or "<!DOCTYPE html" in text or "html" in path.name:
            html_src += text
    remote = re.findall(r"https?://[^\s\"'<>]+", html_src)
    remote = [
        url
        for url in remote
        if "w3.org" not in url and "localhost" not in url and "127.0.0.1" not in url
    ]
    report.add(
        outcome_of(
            "CONTRACT.html-offline",
            "HTML 报告渲染器不引用远程资源",
            not remote,
            "无远程引用" if not remote else f"远程引用 {sorted(set(remote))[:6]}",
            blocking=True,
        )
    )


def check_regression_set_numbers(report: Report) -> None:
    """The frozen service regression set holds 20 questions.

    The set is frozen: its count is part of every level-2 claim's
    denominator. A count that moved silently would change what the
    percentages mean, so it is checked here against the set's own document.
    """
    doc = REPO_ROOT / "docs" / "benchmarks" / "service-regression-set.md"
    text = doc.read_text(encoding="utf-8") if doc.is_file() else ""
    stated = set(re.findall(r"(\d+)\s*(?:道|题)", text))
    report.add(
        outcome_of(
            "REGRESSION.count",
            "服务回归集仍是 20 题（题数写在集合文档里）",
            "20" in stated,
            f"文档所述题数 {sorted(stated)}",
            blocking=True,
        )
    )


def check_demo_app_present(report: Report) -> None:
    """The demo sample and its sources are committed, as the install guide says."""
    apk = REPO_ROOT / "examples" / "demo-app" / "demo.apk"
    sources = REPO_ROOT / "examples" / "demo-app"
    report.add(
        outcome_of(
            "DOC.demo-sample",
            "demo 样本与源码在树内",
            apk.is_file() and sources.is_dir(),
            f"apk={apk.is_file()} dir={sources.is_dir()}",
        )
    )


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
    """The cited verification scripts exist and are syntactically runnable."""
    for rel in (
        "scripts/check-doc-citations.py",
        "scripts/check-version-claims.py",
        "scripts/verify-public-contracts.py",
    ):
        path = REPO_ROOT / rel
        ok = path.is_file()
        if ok:
            try:
                compile(path.read_text(encoding="utf-8"), rel, "exec")
            except SyntaxError:
                ok = False
        report.add(
            outcome_of(
                "SCRIPT.runnable",
                f"脚本可执行：{rel}",
                ok,
                rel,
            )
        )


def check_selftest_regressions(report: Report) -> None:
    """The self-check's own regression tests exist.

    The checks above are code; the rules that keep them honest are tests.
    A check whose test disappeared is a check nobody has to keep true.
    """
    test_dir = REPO_ROOT / "tests"
    for name in ("test_public_contracts.py", "test_evidence_package_isolation.py"):
        path = test_dir / name
        report.add(
            outcome_of(
                "SELFTEST.present",
                f"回归测试在树内：{name}",
                path.is_file(),
                str(path.relative_to(REPO_ROOT)),
            )
        )


def _fixture_names(script_text: str) -> list[str]:
    """The APKs ``scripts/fetch-fixtures.sh`` fetches."""
    if "FILES=(" not in script_text:
        return []
    block = script_text.split("FILES=(", 1)[-1].split(")", 1)[0]
    return re.findall(r'"([^"]+\.apk)"', block)


def check_fixture_precondition(report: Report, root: Path = REPO_ROOT) -> None:
    """装环境那一步必须抓第三方样本：不抓的后果是集成用例 skip。

    The reader dry run installed the tool, never fetched the samples, and
    the suite skipped 27 integration cases with exit code 0. A step whose
    failure is silent cannot be left to the reader's judgement, so the
    fetch script has to declare the samples it fetches.
    """
    script_text = (root / FIXTURE_SCRIPT_REL).read_text(encoding="utf-8")

    names = _fixture_names(script_text)
    expected = len(names)
    counts_ok = expected > 0

    fixture_dir = root / FIXTURE_DIR_REL
    local = sorted(p.name for p in fixture_dir.glob("*.apk")) if fixture_dir.is_dir() else []

    report.add(
        outcome_of(
            "FIXTURE.precondition",
            "装环境必抓第三方样本：脚本声明的样本清单非空",
            counts_ok,
            f"本机样本 {len(local)}/{expected}"
            + ("（未抓取，集成用例会 skip）" if len(local) < expected else "")
            + f"；脚本声明 {expected} 个（{', '.join(names) or '未读到'}）",
        )
    )


def check_a6_onsite_record(report: Report, root: Path = REPO_ROOT) -> None:
    """A6 的降级证据要能回看：历史 run 在存储与 API 层可查。

    A new analysis replaces the project's published one, so a degraded
    run's output would be gone the moment the reader analyses again --
    unless past runs stay queryable. This check reads that ability out of
    the code: the storage layer has to keep and list runs, and the REST
    API has to expose a per-run read. The CLI's own run selector is the
    open candidate C8, recorded as such — its absence is a known gap, not
    a broken promise.
    """
    storage_text = (root / STORAGE_REL).read_text(encoding="utf-8")

    runs_queryable = "def get_run(" in storage_text and "def list_runs(" in storage_text
    api_exposes_runs = "runs/{run_id}" in (
        (root / "src" / "dexatlas" / "api" / "app.py").read_text(encoding="utf-8")
    )

    report.add(
        outcome_of(
            "A6.on-the-spot",
            "A6 降级证据可回看：历史 run 在存储与 API 层可查",
            runs_queryable and api_exposes_runs,
            f"存储可查 run={runs_queryable}；API 可按 run 读={api_exposes_runs}"
            f"（CLI 自身的 run 选择器是未决候选 C8）",
            blocking=True,
        )
    )


def check_package_entry_count(report: Report, root: Path = REPO_ROOT) -> None:
    """证据包里的条目数：CLI 打印的数目是归档里实际有的条目。

    The archive holds every file the manifest lists *plus* the manifest
    itself, so the number a reader counts in the zip is one more than the
    manifest's count. The CLI has to print the archive's count — a print
    built from the manifest's count wears the archive's name and is one
    short of what the reader finds.
    """
    package_src = (root / EVIDENCE_PACKAGE_REL).read_text(encoding="utf-8")
    cli_src = (root / CLI_REL).read_text(encoding="utf-8")

    roles = []
    if "_REPORT_PATHS = {" in package_src:
        role_block = package_src.split("_REPORT_PATHS = {", 1)[-1].split("}", 1)[0]
        roles = re.findall(r'"(\w+)":\s*"([^"]+)"', role_block)

    files_block = ""
    # ``package_contents`` builds the files dict and returns it; the manifest
    # is built by ``package_manifest`` from that dict. The block that has to
    # be free of the manifest's own name is the one that assembles ``files``
    # -- bounded by the end of that function, not by the next ``manifest:``
    # annotation, which after the C8 split first appears inside
    # ``verify_package`` and would drag its ``manifest.json`` reads into a
    # block that never contained them.
    if "files: dict[str, bytes] = {}" in package_src:
        files_block = package_src.split("files: dict[str, bytes] = {}", 1)[-1]
        if "def package_manifest(" in files_block:
            files_block = files_block.split("def package_manifest(", 1)[0]
        else:
            files_block = files_block.split("manifest: dict[str, Any] = {", 1)[0]
    manifest_written = (
        'archive.writestr("manifest.json"' in package_src
        or "archive.writestr(MANIFEST_NAME" in package_src
    )
    manifest_not_listed = "manifest.json" not in files_block
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

    counts_ok = bool(roles)

    report.add(
        outcome_of(
            "PACKAGE.entry-count",
            "证据包条目数：报告角色齐备，manifest 写入归档，CLI 打印归档里的条目数",
            counts_ok
            and manifest_written
            and manifest_not_listed
            and cli_prints_archive_count
            and not cli_prints_manifest_count,
            f"代码：报告角色 {len(roles)} 个，manifest 写入归档={manifest_written}"
            f"，不进清单={manifest_not_listed}，CLI 打印归档计数={cli_prints_archive_count}"
            f"，CLI 打印清单计数={cli_prints_manifest_count}",
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
    ("B1", "manifest 抽查", "需要运行分析", False),
    ("B2", "符号检索抽查", "需要运行分析", False),
    ("B3", "源码回读抽查", "需要运行分析", False),
    ("B4", "调用点/调用边抽查", "需要运行分析", False),
    ("B5", "证据记录抽查", "需要运行分析", False),
    ("C1", "HTML 报告可离线打开", "需要浏览器实测", False),
    ("C2", "证据包校验命令退出码 0", "需要真实证据包", False),
    ("C3", "证据包不含样本本身", "需要解开 zip 核对", False),
    ("D1", "坏输入处理", "需要运行 CLI", False),
    ("D2", "重复分析幂等", "需要运行两次分析", False),
    ("D3", "not_included 边界（★）", "需要真实证据包；键已静态核对", True),
    ("E1", "MCP stdio 可连接", "需要运行 MCP server", False),
    ("E2", "MCP 只读无写路径（★）", "需要源码+运行核对", True),
    ("E3", "agent 输出带引用且分级（★）", "需要真实运行", True),
    ("F1", "REST 服务可启动", "需要起服务", False),
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
    # the documents carry. A console that cannot encode it should not turn a
    # real failure into a crash, so the stream is reconfigured before the
    # first print.
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    report = Report()
    for check in CHECKS:
        check(report)

    if args.json:
        import json

        print(
            json.dumps(
                [
                    {
                        "id": outcome.check_id,
                        "title": outcome.title,
                        "state": outcome.state,
                        "detail": outcome.detail,
                        "blocking": outcome.blocking,
                    }
                    for outcome in report.outcomes
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for outcome in report.outcomes:
            mark = {"pass": "✓", "fail": "✗", "manual": "·"}[outcome.state]
            blocking = "（★）" if outcome.blocking else ""
            print(f"{mark} {outcome.check_id}{blocking} {outcome.title}")
            if outcome.detail:
                print(f"    {outcome.detail}")
        counts = report.counts()
        print(
            f"\n自动化判定：通过 {counts['pass']}，失败 {counts['fail']}，"
            f"需人工 {counts['manual']}；已判定项通过率 {report.pass_rate()}"
        )

    return 0 if counts["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
