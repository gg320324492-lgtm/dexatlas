"""The analysis page stops polling once the back end says the run is over.

The page used to arm its own ``setInterval`` for two sources -- the project
envelope and the runs list -- and kept them running after the analysis had
reached a terminal state.  A finished analysis then kept asking the back end
a question whose answer could not change: two requests every two seconds,
until the tab was closed.

The rule now lives in one place, ``desktop/src/stages.js``:

* ``isTerminalStatus`` -- what counts as terminal;
* ``pollUntilTerminal`` -- stop the timer once the back end's status field
  says so.

The behaviour of that rule is unit-tested in ``desktop/src/stages.test.ts``
(vitest).  What a JavaScript test cannot see is the *wiring* -- that the page
routes every poll through the rule instead of arming a timer of its own, that
each poll carries the same terminal criterion, and that the front end's
terminal set still matches the back end's status domains.  These checks read
the sources for exactly those things.

They go red on the tree before the fix: ``Analysis.tsx`` armed
``window.setInterval`` itself and had no terminal criterion, and
``desktop/src/stages.js`` exported neither function.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SRC = ROOT / "desktop" / "src"
ANALYSIS_PAGE = DESKTOP_SRC / "pages" / "Analysis.tsx"
STAGES_MODULE = DESKTOP_SRC / "stages.js"
BACKEND_RUNS = ROOT / "src" / "dexatlas" / "core" / "runs.py"
BACKEND_MODELS = ROOT / "src" / "dexatlas" / "core" / "models.py"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def _enum_values(source: str, class_name: str) -> list[str]:
    """The string values of a StrEnum, in the order the class declares them."""
    match = re.search(
        rf"class {class_name}\(StrEnum\):(?P<body>.*?)(?=\n\nclass |\Z)", source, re.DOTALL
    )
    assert match, f"no StrEnum {class_name} in the source"
    return re.findall(r'^\s+[A-Z_]+ = "([^"]+)"', match.group("body"), re.MULTILINE)


def _frontend_terminal_statuses() -> list[str]:
    """The terminal set the front end uses to decide a poll may stop."""
    source = _source(STAGES_MODULE)
    match = re.search(r"export const TERMINAL_STATUSES = \[(?P<body>[^\]]*)\]", source)
    assert match, "desktop/src/stages.js does not define TERMINAL_STATUSES"
    return re.findall(r'"([^"]+)"', match.group("body"))


def _frontend_exports() -> list[str]:
    """The names desktop/src/stages.js exports."""
    return re.findall(r"^export (?:const|function) (\w+)", _source(STAGES_MODULE), re.MULTILINE)


# ---------------------------------------------------------------------------
# 1. 终态口径: 前端不许自己发明一个后端没有的状态
# ---------------------------------------------------------------------------


def test_the_terminal_set_is_exactly_the_finished_run_statuses() -> None:
    """The front end may not invent a terminal state, nor drop one the back end has."""
    run_statuses = _enum_values(_source(BACKEND_RUNS), "RunStatus")
    assert run_statuses == ["pending", "running", "completed", "failed", "cancelled"]
    finished = [status for status in run_statuses if status not in {"pending", "running"}]
    assert _frontend_terminal_statuses() == finished


def test_the_project_status_domain_has_no_cancelled_state() -> None:
    """Projects never report 'cancelled': a cancelled run leaves the project failed.

    That is why the shared criterion may name 'cancelled' even though the
    project envelope never carries it -- and why both polling loops can use
    one criterion instead of two that drift apart.
    """
    project_statuses = _enum_values(_source(BACKEND_MODELS), "ProjectStatus")
    assert project_statuses == ["pending", "running", "completed", "failed"]
    assert "cancelled" not in project_statuses
    assert set(project_statuses) <= set(_frontend_terminal_statuses()) | {"pending", "running"}


# ---------------------------------------------------------------------------
# 2. 页面接线: 轮询一律走规则, 规则给出终态判据
# ---------------------------------------------------------------------------


def test_the_page_arms_no_timer_of_its_own() -> None:
    """Every poll on the page goes through the rule that stops at a terminal state."""
    source = _source(ANALYSIS_PAGE)
    assert "window.setInterval" not in source, (
        "Analysis.tsx 又自己挂了定时器: 轮询必须走 stages.js 的 pollUntilTerminal, "
        "否则终态之后定时器还在转"
    )
    assert "pollUntilTerminal" in source, (
        "Analysis.tsx 必须用 stages.js 的 pollUntilTerminal 轮询 (终态自停)"
    )


def test_every_poll_on_the_page_carries_the_shared_terminal_criterion() -> None:
    """One criterion for every loop: project envelope, runs list, stage events."""
    source = _source(ANALYSIS_PAGE)
    polls = source.count("pollUntilTerminal({")
    criteria = source.count("isTerminal: () => isTerminalStatus(")
    assert polls >= 3, (
        f"项目状态, runs 列表, 阶段事件三处轮询都要走 pollUntilTerminal; 现在只有 {polls} 处"
    )
    assert criteria == polls, (
        f"每一处轮询都必须带上同一份终态判据 isTerminalStatus (轮询 {polls} 处, 判据 {criteria} 处)"
    )


def test_the_page_does_not_call_the_stage_events_more_than_they_are() -> None:
    """阶段事件来自后端; 五格的对应关系是前端映射的 -- 两件事别说成一件事."""
    source = _source(ANALYSIS_PAGE)
    assert "真实 pipeline 阶段事件" not in source, (
        "Analysis.tsx 仍把阶段事件连同格子映射一起说成后端给的"
    )
    assert "前端映射" in source, "Analysis.tsx 应写明哪一部分是前端的映射"


# ---------------------------------------------------------------------------
# 3. 规则确实住在那个纯模块里
# ---------------------------------------------------------------------------


def test_the_rule_lives_in_the_pure_module() -> None:
    """The rule is in stages.js, so it can be run and tested without a DOM."""
    exports = _frontend_exports()
    assert "isTerminalStatus" in exports
    assert "pollUntilTerminal" in exports
