"""Regression tests for the desktop analysis page's stage mapping.

Phase 5 W2 (PR #14) wired the desktop analysis page to the backend's real
stage events (``GET /projects/{pid}/runs/{rid}/stages``).  The mapping from
those events onto the five slots on the page had a defect that only showed
up once a run had finished: the backend's last stage is ``publish``, which
maps onto the 报告 slot, so the inference that fills the 证据 slot was
skipped and a completed run showed 「证据 · 待处理」 while the same page
claimed 「已完成」 and 「12 条证据」 above it (9/9 in
``.scratch/phase5-w2-retest.md`` §P1).

The mapping lives in ``desktop/src/stages.js`` — a plain ESM module on
purpose, so that this test can execute the *shipped* file with Node: CI's
Python job installs no npm dependencies and the Node on the runner predates
TypeScript type stripping, so a ``.ts`` module could not be run here
without a build step in between.  The types are not lost: ``tsconfig.json``
sets ``allowJs`` + ``checkJs``, so ``tsc --noEmit`` checks the module
against its JSDoc annotations like any other file.

The page's own copy of the mapping was removed; the last test in this file
guards against it being pasted back in.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STAGES_MODULE = ROOT / "desktop" / "src" / "stages.js"
ANALYSIS_PAGE = ROOT / "desktop" / "src" / "pages" / "Analysis.tsx"

#: The five slots the page shows, in the order it shows them.
SLOTS = ["collect", "parse", "index", "evidence", "report"]

#: The probe: load the shipped module, call the named function with the
#: given arguments, print the results as JSON.  Reading the scenario list
#: from stdin keeps the shell out of it entirely.
PROBE = """
const mod = await import(process.argv[1]);
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const scenarios = JSON.parse(Buffer.concat(chunks).toString("utf8"));
const results = scenarios.map((scenario) => mod[scenario.fn](...scenario.args));
process.stdout.write(JSON.stringify(results));
"""


def _node() -> str:
    exe = shutil.which("node")
    if exe is None:
        pytest.fail(
            "Node.js is required for the desktop stage-mapping tests: they execute "
            "desktop/src/stages.js directly, because CI's Python job installs no npm "
            "dependencies and its Node predates TypeScript type stripping. "
            "Install Node and re-run rather than skipping the check."
        )
    return exe


def _stage(stage: str, finished: bool = True) -> dict[str, object]:
    """One stage event: ``finished=False`` means the stage had not ended."""
    return {
        "stage": stage,
        "started_at": "2026-11-25T10:00:00Z",
        "finished_at": "2026-11-25T10:00:01Z" if finished else None,
    }


def _run(status: str, completeness: str = "complete") -> dict[str, object]:
    return {"status": status, "completeness": completeness}


#: Every stage the backend emits, in pipeline order.
ALL_STAGES = [
    "inspect",
    "parse-apktool",
    "index-androguard",
    "decompile-jadx",
    "publish",
]

#: A completed run: every stage ended.
COMPLETED_EVENTS = [_stage(name) for name in ALL_STAGES]
#: A run in the middle of the JADX stage (the retest's t=5044ms sample).
AT_JADX_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool"),
    _stage("index-androguard"),
    _stage("decompile-jadx", finished=False),
]
#: A run in the middle of the Apktool stage (t=2204ms).
AT_APKTOOL_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool", finished=False),
]
#: A run in the middle of the Androguard stage (t=3011ms).
AT_INDEX_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool"),
    _stage("index-androguard", finished=False),
]
#: A run that failed while Apktool was running.
FAILED_AT_APKTOOL_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool", finished=False),
]
#: A run that failed while JADX was running — the stage right before the
#: evidence slot, and the case where the old inference left the evidence
#: slot reading 「进行中」 on a run that was already over.
FAILED_AT_JADX_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool"),
    _stage("index-androguard"),
    _stage("decompile-jadx", finished=False),
]
#: A run that was cancelled while Androguard was running.
CANCELLED_AT_INDEX_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool"),
    _stage("index-androguard", finished=False),
]
#: A run that failed while the report was being published.
FAILED_AT_PUBLISH_EVENTS = [
    _stage("inspect"),
    _stage("parse-apktool"),
    _stage("index-androguard"),
    _stage("decompile-jadx"),
    _stage("publish", finished=False),
]

SCENARIOS: dict[str, dict[str, object]] = {
    "completed_with_stages": {
        "fn": "deriveStagesFromRun",
        "args": [_run("completed"), COMPLETED_EVENTS],
    },
    "running_at_jadx": {
        "fn": "deriveStagesFromRun",
        "args": [_run("running"), AT_JADX_EVENTS],
    },
    "running_at_apktool": {
        "fn": "deriveStagesFromRun",
        "args": [_run("running"), AT_APKTOOL_EVENTS],
    },
    "running_at_index": {
        "fn": "deriveStagesFromRun",
        "args": [_run("running"), AT_INDEX_EVENTS],
    },
    "old_run_completed": {
        "fn": "deriveStagesFromRun",
        "args": [_run("completed"), []],
    },
    "old_run_running": {
        "fn": "deriveStagesFromRun",
        "args": [_run("running"), []],
    },
    "old_run_failed": {
        "fn": "deriveStagesFromRun",
        "args": [_run("failed"), []],
    },
    "old_run_pending": {
        "fn": "deriveStagesFromRun",
        "args": [_run("pending"), []],
    },
    "failed_at_apktool": {
        "fn": "deriveStagesFromRun",
        "args": [_run("failed"), FAILED_AT_APKTOOL_EVENTS],
    },
    "failed_at_jadx": {
        "fn": "deriveStagesFromRun",
        "args": [_run("failed"), FAILED_AT_JADX_EVENTS],
    },
    "cancelled_at_index": {
        "fn": "deriveStagesFromRun",
        "args": [_run("cancelled"), CANCELLED_AT_INDEX_EVENTS],
    },
    "failed_at_publish": {
        "fn": "deriveStagesFromRun",
        "args": [_run("failed"), FAILED_AT_PUBLISH_EVENTS],
    },
    "no_run": {
        "fn": "deriveStagesFromRun",
        "args": [None, None],
    },
    "partial_completed": {
        "fn": "deriveStagesFromRun",
        "args": [_run("completed", "partial"), COMPLETED_EVENTS],
    },
    "simulation_completed": {
        "fn": "deriveStageStates",
        "args": [5, "completed"],
    },
    "simulation_running": {
        "fn": "deriveStageStates",
        "args": [2, "running"],
    },
    "badge_stages": {
        "fn": "deriveStageBadge",
        "args": ["stages"],
    },
    "badge_run_status": {
        "fn": "deriveStageBadge",
        "args": ["run-status", False],
    },
    "badge_run_status_unavailable": {
        "fn": "deriveStageBadge",
        "args": ["run-status", True],
    },
    "badge_simulation": {
        "fn": "deriveStageBadge",
        "args": ["simulation"],
    },
}


@pytest.fixture(scope="module")
def results() -> dict[str, object]:
    """Run every scenario once and hand the results to the tests."""
    scenarios = list(SCENARIOS.values())
    proc = subprocess.run(
        [_node(), "--input-type=module", "-e", PROBE, STAGES_MODULE.as_uri()],
        input=json.dumps(scenarios),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        timeout=120,
    )
    assert proc.returncode == 0, f"the stage-mapping probe failed on Node:\n{proc.stderr}"
    payload = json.loads(proc.stdout)
    assert len(payload) == len(scenarios)
    return dict(zip(SCENARIOS, payload, strict=True))


def _states(results: dict[str, object], name: str) -> dict[str, str]:
    outcome = results[name]
    assert isinstance(outcome, dict)
    states = outcome["states"]
    assert isinstance(states, dict)
    return states


def test_completed_run_marks_every_slot_done(results: dict[str, object]) -> None:
    """A finished run shows five finished slots — the evidence slot included.

    The backend's last stage is ``publish``, which lands on the 报告 slot;
    the evidence slot has to be filled from that fact, otherwise a completed
    run claims 「证据 · 待处理」 next to 「已完成」 and 「12 条证据」
    (retest report §P1).
    """
    states = _states(results, "completed_with_stages")
    assert states == {
        "collect": "done",
        "parse": "done",
        "index": "done",
        "evidence": "done",
        "report": "done",
    }


def test_running_run_shows_the_evidence_slot_in_progress(results: dict[str, object]) -> None:
    """The inference for a running run must not regress.

    At the retest's t=5044ms sample the backend was inside ``decompile-jadx``
    with ``index-androguard`` finished; the page showed 解析 进行中 and
    证据 进行中.  That reading is correct and has to survive the fix.
    """
    states = _states(results, "running_at_jadx")
    assert states == {
        "collect": "done",
        "parse": "running",
        "index": "done",
        "evidence": "running",
        "report": "pending",
    }


def test_running_run_before_the_evidence_is_produced(results: dict[str, object]) -> None:
    """Before the indexing stage ends, the evidence slot stays pending."""
    states = _states(results, "running_at_apktool")
    assert states["evidence"] == "pending"
    assert states["parse"] == "running"

    states = _states(results, "running_at_index")
    assert states["evidence"] == "pending"
    assert states["index"] == "running"


def test_old_run_without_stages_uses_the_status_fallback(results: dict[str, object]) -> None:
    """A run written before the stages endpoint still maps by status."""
    states = _states(results, "old_run_completed")
    assert states == dict.fromkeys(SLOTS, "done")

    states = _states(results, "old_run_running")
    assert states["collect"] == "done"
    assert states["parse"] == "running"
    assert states["index"] == "pending"

    states = _states(results, "old_run_failed")
    assert states["collect"] == "done"
    assert states["parse"] == "error"

    states = _states(results, "old_run_pending")
    assert states == dict.fromkeys(SLOTS, "pending"), (
        "a run that has not started must not claim that a stage failed"
    )


def test_completed_run_looks_the_same_with_and_without_stage_events(
    results: dict[str, object],
) -> None:
    """The same finished state must not look different on old and new runs.

    The retest found the fallback path showing five finished slots while the
    stages path showed 「证据 · 待处理」 for the very same backend.
    """
    assert _states(results, "completed_with_stages") == _states(results, "old_run_completed")


def test_failed_run_does_not_leave_the_evidence_slot_running(results: dict[str, object]) -> None:
    """A run that is over cannot have a stage in progress."""
    states = _states(results, "failed_at_apktool")
    assert states["collect"] == "done"
    assert states["parse"] == "error"
    assert states["evidence"] == "pending"
    assert states["report"] == "pending"

    # The stage right before the evidence slot: the old inference read this
    # one as 「进行中」 and left it there for a run that had already failed.
    states = _states(results, "failed_at_jadx")
    assert states["collect"] == "done"
    assert states["parse"] == "error"
    assert states["index"] == "done"
    assert states["evidence"] == "pending"
    assert states["report"] == "pending"


def test_cancelled_run_does_not_leave_the_evidence_slot_running(results: dict[str, object]) -> None:
    """Same for a cancelled run."""
    states = _states(results, "cancelled_at_index")
    assert states["collect"] == "done"
    assert states["parse"] == "done"
    assert states["index"] == "error"
    assert states["evidence"] == "pending"
    assert states["report"] == "pending"


def test_failed_run_that_reached_the_report_keeps_the_evidence(results: dict[str, object]) -> None:
    """The pipeline builds the evidence before it publishes the report.

    A run that failed while publishing had already produced its evidence
    (``pipeline.py``: the evidence is built before the publish stage), so
    the evidence slot must not fall back to pending.
    """
    states = _states(results, "failed_at_publish")
    assert states["evidence"] == "done"
    assert states["report"] == "error"


def test_run_without_data_leaves_every_slot_pending(results: dict[str, object]) -> None:
    states = _states(results, "no_run")
    assert states == dict.fromkeys(SLOTS, "pending")


def test_partial_completeness_marks_the_affected_slot(results: dict[str, object]) -> None:
    """A partial run still says so on the slot it could not finish."""
    outcome = results["partial_completed"]
    assert isinstance(outcome, dict)
    states = outcome["states"]
    labels = outcome["partialLabels"]
    assert isinstance(states, dict)
    assert isinstance(labels, dict)
    assert states["report"] == "skipped"
    assert labels["report"] == "部分"


def test_simulation_path_is_unchanged(results: dict[str, object]) -> None:
    """The front-end time simulation is only a fallback; keep it honest."""
    outcome = results["simulation_completed"]
    assert isinstance(outcome, dict)
    assert outcome == dict.fromkeys(SLOTS, "done")

    outcome = results["simulation_running"]
    assert isinstance(outcome, dict)
    assert outcome == {
        "collect": "done",
        "parse": "done",
        "index": "running",
        "evidence": "pending",
        "report": "pending",
    }


def test_badge_says_where_the_stages_come_from(results: dict[str, object]) -> None:
    """The badge must name the source, and admit what is inferred.

    The page's 证据 slot has no backend stage behind it, and its 解析 slot
    covers two backend stages; the badge's tooltip has to say so (retest
    report §P3).
    """
    for name, expected_text in (
        # The badge texts are the UI's own labels, so they carry the UI's
        # fullwidth punctuation: RUF001 exists for identifiers where a
        # lookalike could hide a bug, and a label is read by a reader.
        ("badge_stages", "阶段推进：后端真实阶段事件"),  # noqa: RUF001
        ("badge_run_status", "阶段推进：后端 run 状态 + 前端粒度模拟"),  # noqa: RUF001
        ("badge_simulation", "阶段推进为前端模拟"),
    ):
        badge = results[name]
        assert isinstance(badge, dict)
        assert badge["text"] == expected_text
        title = badge["title"]
        assert isinstance(title, str)
        assert "证据" in title, "the badge must say that the evidence slot is inferred"
        assert "推断" in title
        assert "parse-apktool" in title, "the badge must say that 解析 covers two stages"


def test_badge_says_the_stages_endpoint_is_unavailable(results: dict[str, object]) -> None:
    """A stages endpoint that cannot be reached must not be hidden."""
    badge = results["badge_run_status_unavailable"]
    assert isinstance(badge, dict)
    assert "stages 端点不可用" in badge["text"]


def test_analysis_page_uses_the_shared_mapping() -> None:
    """The page must not grow its own copy of the mapping.

    The mapping was extracted so that it could be tested; a second copy in
    the page would be a second implementation nobody runs the tests on.
    """
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    assert 'from "../stages"' in source, "the page must import the shared stage mapping"
    assert "STAGE_TO_SLOT" not in source, "the stage table must not be duplicated in the page"
    assert "lastDoneSlot" not in source, "the slot inference must not be duplicated in the page"
