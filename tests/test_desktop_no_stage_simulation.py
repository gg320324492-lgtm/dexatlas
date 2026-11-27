"""Regression tests for the removed front-end stage simulation (Phase 5 收尾).

The Phase 5 execution order's completion definition (§5) and the W2 acceptance
criterion both require "前端模拟代码删除".  Until this change the analysis page
still advanced the five-stage timeline on a 2.4 s timer whenever the runs
endpoint was unavailable and stamped the result with a "前端模拟" badge — a
fabricated progress shown exactly when no backend fact could be read.

The checks that pin the removal go red on the tree before it:

* the module still exported ``deriveStageStates`` (time-based advancement);
* the run-status badge still said ``前端粒度模拟``;
* the page still carried ``useStageSimulation`` / ``STAGE_TICK_MS`` and the
  "阶段进度回退为前端模拟" banner;
* there was no retry entry for a failed runs request;
* switching projects kept the previous project's stage events (found in the
  browser walkthrough), so a page with no run was stamped "后端真实阶段事件".

Node executes the shipped plain-ESM module, as the other desktop checks do; the
wiring is read from the page source.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SRC = ROOT / "desktop" / "src"
ANALYSIS_PAGE = DESKTOP_SRC / "pages" / "Analysis.tsx"
STAGES_MODULE = DESKTOP_SRC / "stages.js"

#: Load the shipped module, then either list its exports or call named
#: functions with the given arguments.  Reading the calls from stdin keeps the
#: shell out of it entirely.
PROBE = """
const mod = await import(process.argv[1]);
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const calls = JSON.parse(Buffer.concat(chunks).toString("utf8"));
const results = calls.map((call) => {
  if (call.fn === "__exports__") return Object.keys(mod).sort();
  return mod[call.fn](...call.args);
});
process.stdout.write(JSON.stringify(results));
"""


def _node() -> str:
    exe = shutil.which("node")
    if exe is None:
        pytest.fail(
            "Node.js is required to execute desktop/src/stages.js: install Node "
            "and re-run rather than skipping the check."
        )
    return exe


def _probe(calls: list[dict[str, object]]) -> list[object]:
    """Run the shipped stages module under Node and return the raw results."""
    assert STAGES_MODULE.exists(), "desktop/src/stages.js is missing"
    proc = subprocess.run(
        [_node(), "--input-type=module", "-e", PROBE, STAGES_MODULE.as_uri()],
        input=json.dumps(calls),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        timeout=120,
    )
    assert proc.returncode == 0, f"the probe on stages.js failed on Node:\n{proc.stderr}"
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# 1. 模块本身: 时间模拟函数已删除, 角标只留真实来源
# ---------------------------------------------------------------------------


def test_module_no_longer_exports_the_time_simulation() -> None:
    """The time-based advancement function must be gone, not merely unused."""
    exports = _probe([{"fn": "__exports__", "args": []}])[0]
    assert isinstance(exports, list)
    assert "deriveStageStates" not in exports, (
        "stages.js 仍导出 deriveStageStates: 按时间推进阶段的时间模拟没有删干净"
    )
    assert "deriveStageBadge" in exports, "真实来源 (stages / run-status) 的角标必须保留"


def test_no_run_data_maps_to_pending_not_to_invented_progress() -> None:
    """Without run data, every slot says 待处理 — never a running slot."""
    result = _probe([{"fn": "deriveStagesFromRun", "args": [None, None]}])[0]
    assert isinstance(result, dict)
    assert result["states"] == {
        "collect": "pending",
        "parse-apktool": "pending",
        "index": "pending",
        "decompile-jadx": "pending",
        "report": "pending",
    }


def test_run_status_badge_no_longer_claims_simulation() -> None:
    """The old-run badge names the backend run status, not a front-end simulation."""
    badge = _probe([{"fn": "deriveStageBadge", "args": ["run-status", False]}])[0]
    assert isinstance(badge, dict)
    assert "模拟" not in badge["text"]
    # 角标同时点明两件事: 状态来自后端, 格子是前端的映射 (2026-11-26 修).
    assert badge["text"] == "阶段推进：后端 run 状态 + 前端映射"  # noqa: RUF001
    assert "不随时间推进" in badge["title"]
    assert "前端" in badge["title"]


def test_run_status_badge_still_discloses_an_unavailable_stages_endpoint() -> None:
    """Falling back to coarse run status must still say the stages endpoint is gone."""
    badge = _probe([{"fn": "deriveStageBadge", "args": ["run-status", True]}])[0]
    assert isinstance(badge, dict)
    assert "stages 端点不可用" in badge["text"]


# ---------------------------------------------------------------------------
# 2. 页面接线: 没有模拟路径, 失败时如实报错并保留重试
# ---------------------------------------------------------------------------


def test_analysis_page_has_no_simulation_path() -> None:
    """No timer, no simulation state, no simulation badge or banner."""
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    for marker in (
        "useStageSimulation",
        "STAGE_TICK_MS",
        "deriveStageStates",
        "前端模拟",
        "模拟阶段",
    ):
        assert marker not in source, f"Analysis.tsx 仍含模拟路径标记: {marker}"


def test_analysis_page_reports_unavailable_backend_with_a_retry() -> None:
    """A failed runs request says the progress cannot be obtained and offers 重试."""
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    assert "后端不可用，阶段进度无法取得" in source, (  # noqa: RUF001
        "runs 请求失败时必须如实说明拿不到阶段进度, 而不是画一个推进的时间线"
    )
    assert "setRunsRetryNonce" in source, "阶段进度错误状态必须保留重试入口"


def test_analysis_page_says_unknown_when_there_is_no_run_data() -> None:
    """An empty runs list is shown as unknown, not as progress."""
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    assert "五个阶段的状态未知，这里不推测进度" in source, (  # noqa: RUF001
        "没有 run 数据时必须说明五个阶段状态未知, 而不是让五格看起来在推进"
    )
    # 五个格子与后端的五个推进点一一对应: inspect / parse-apktool /
    # index-androguard / decompile-jadx / publish 各占一格。
    slots_source = STAGES_MODULE.read_text(encoding="utf-8")
    assert '"parse-apktool": "parse-apktool"' in slots_source, (
        "parse-apktool 必须独占一格, 不能与 decompile-jadx 合并"
    )
    assert '"decompile-jadx": "decompile-jadx"' in slots_source, "decompile-jadx 必须独占一格"


def test_analysis_page_clears_stage_facts_when_the_run_changes() -> None:
    """Cross-project navigation must not reuse the previous project's stage events.

    The browser walkthrough found this: opening a project with real stages and
    then a project with no run kept the previous ``runStageEvents``, so the
    empty project's card was stamped "后端真实阶段事件" while its five slots
    said 待处理.  The fix clears the run list, the stage events and their errors
    whenever the project or run changes.
    """
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    assert "observedProjectRef" in source, "换项目时必须清掉上一个项目的 run"
    assert "polledRunRef" in source, "换 run 时必须清掉上一个轮次的阶段事件"
    assert "setStages(null)" in source and "setRuns([])" in source
