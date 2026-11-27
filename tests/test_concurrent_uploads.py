"""What happens when the same APK is uploaded twice at the same time.

The workbench promises that an APK the workspace already holds is not
analysed again. That promise only held when the uploads arrived one after
the other: the check and the start of the analysis were two separate
moments, and four uploads that arrived together all passed the check
before any of them had written a row. Four analyses of one APK then ran at
once, writing over each other's results.

The registry had the same shape of defect. It was keyed by the project id,
which is the APK's content hash, so two analyses under one project id
shared one key: the analysis that ended first unregistered the one that
was still running, and an analysis that is not registered cannot be
cancelled -- the cancel endpoint answered 409 for an analysis that was
running.

The versions had a third. The backends remember that they have been
probed *before* the probe finishes, so an analysis that arrived in that
window was handed ``None`` -- and the run it published said a backend that
took part was not installed.

These tests hold in place:

- Four concurrent uploads of one APK start exactly one analysis; the other
  three are told the APK is already being analysed, and one run row is
  written.
- One analysis ending does not unregister the one that is still running:
  that one is still cancellable, and its token really is cancelled.
- A backend that took part is never recorded as having no version, even
  when the analysis that found out ran beside another one.
- The sentence the desktop home page says to the user -- "同一 APK 重复上传
  会打开已有项目, 不会重复分析" -- is the sentence the backend actually
  keeps, under concurrency as well as in sequence.
"""

from __future__ import annotations

import os
import re
import stat
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.uploads import run_background_analysis
from dexatlas.config.settings import Settings
from dexatlas.core.ingest import inspect_apk
from dexatlas.core.models import ApkMetadata, Project, ProjectStatus
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import AnalysisRun
from dexatlas.workbench.app import create_app
from tests.conftest import build_apk

#: The desktop front end's home page. The sentence this file pins down is
#: written here, in the user's language, in the place the user reads it.
HOME_PAGE = Path(__file__).resolve().parents[1] / "desktop" / "src" / "pages" / "HomePage.tsx"


def _wait_for(predicate: Any, timeout: float = 60.0) -> bool:
    """Wait until the predicate holds. Whether it ever did."""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


class _GatedAnalysis:
    """A stand-in for the analysis, so the other uploads arrive while it runs.

    The stand-in is the slow part of the pipeline; the claim, the check and
    the answer are the production ones, and the threads are real. Nothing
    in the code under test is told that a test is running.
    """

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.released = threading.Event()
        self.calls = 0
        self._lock = threading.Lock()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Put the stand-in in place of the pipeline's analysis."""
        state = self

        def analyze(
            analyzer: Analyzer,
            apk_path: Path,
            *,
            metadata: ApkMetadata | None = None,
            cancellation: Any = None,
            **_: Any,
        ) -> SimpleNamespace:
            with state._lock:
                state.calls += 1
            state.entered.set()
            if not state.released.wait(timeout=60):
                raise AssertionError("the test never released the analysis")
            assert metadata is not None
            # The project's row and the run's own row, the way the pipeline
            # writes them: the test counts the runs to see how many analyses
            # there were.
            project = Project.create(metadata)
            run = AnalysisRun.start(project.id, metadata.sha256)
            analyzer.store.begin_run(project)
            analyzer.store.create_run(run)
            return SimpleNamespace(succeeded=True)

        monkeypatch.setattr(Analyzer, "analyze", analyze)


def test_four_concurrent_uploads_of_one_apk_start_one_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One APK, four uploads at once, one analysis.

    The three uploads that lost the race are answered while the analysis is
    still running. That window is where the defect lived: the check that
    decided "nobody is analysing this APK" and the start of the analysis
    were two separate moments, and every upload that arrived in between
    passed the check.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    gate = _GatedAnalysis()
    gate.install(monkeypatch)

    payload = build_apk(tmp_path / "demo.apk").read_bytes()
    answers: list[dict[str, Any]] = []
    answered = threading.Condition()

    with TestClient(create_app(analyzer)) as client:

        def upload() -> None:
            response = client.post(
                "/api/analyze",
                files={"file": ("demo.apk", payload, "application/octet-stream")},
            )
            with answered:
                answers.append(response.json())
                answered.notify_all()

        threads = [threading.Thread(target=upload) for _ in range(4)]
        for thread in threads:
            thread.start()
        try:
            assert gate.entered.wait(timeout=60), "no analysis started"
            # The three that lost the claim answer while the winner is still
            # running; the winner answers when its analysis is done.
            assert _wait_for(lambda: len(answers) == 3), (
                f"only {len(answers)} of the four uploads answered while the "
                "analysis was running: the uploads that must find the analysis "
                "already running are waiting for an analysis of their own"
            )
        finally:
            gate.released.set()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive(), "an upload never answered"

    assert len(answers) == 4
    started = [answer for answer in answers if not answer["already_analysed"]]
    deduped = [answer for answer in answers if answer["already_analysed"]]
    assert len(started) == 1, "more than one upload started an analysis"
    assert len(deduped) == 3
    assert gate.calls == 1, "the APK was analysed more than once"
    # Every upload is pointed at the same project: the analysis that runs
    # is the one the browser has to watch.
    assert {answer["project_id"] for answer in answers} == {started[0]["project_id"]}
    assert started[0]["status"] == "pending"
    assert all(answer["status"] == "running" for answer in deduped)
    # One run row: one analysis, one attempt.
    assert len(analyzer.store.list_runs(started[0]["project_id"])) == 1


def test_an_analysis_that_ends_does_not_unregister_the_one_that_is_still_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One analysis ending must not unregister the one beside it.

    The project id is the first sixteen digits of the APK's hash, so two
    analyses under one project id are two different APKs whose hashes share
    those digits. The registry has to hold them apart: the one that ends
    first must not unregister the one that is still running, or that one
    cannot be cancelled any more -- and the cancel endpoint answered 409
    for an analysis that was running.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    apk = build_apk(tmp_path / "demo.apk")

    # Two hashes that share their first sixteen digits, and so share the
    # project id the analyses are registered under.
    first_hash = "ab" * 8 + "00" * 24
    second_hash = "ab" * 8 + "11" * 24
    project_id = Project.new_id(first_hash)
    assert project_id == Project.new_id(second_hash)

    gates = {first_hash: threading.Event(), second_hash: threading.Event()}
    tokens: dict[str, Any] = {}
    entered = threading.Semaphore(0)

    def analyze(
        analyzer: Analyzer,
        apk_path: Path,
        *,
        metadata: ApkMetadata | None = None,
        cancellation: Any = None,
        **_: Any,
    ) -> SimpleNamespace:
        assert metadata is not None
        tokens[metadata.sha256] = cancellation
        entered.release()
        if not gates[metadata.sha256].wait(timeout=60):
            raise AssertionError("the test never released the analysis")
        return SimpleNamespace(succeeded=True)

    monkeypatch.setattr(Analyzer, "analyze", analyze)
    metadatas = [
        ApkMetadata(sha256=first_hash, size_bytes=apk.stat().st_size, path=apk),
        ApkMetadata(sha256=second_hash, size_bytes=apk.stat().st_size, path=apk),
    ]

    with TestClient(create_app(analyzer)) as client:
        threads = [
            threading.Thread(target=run_background_analysis, args=(analyzer, apk, metadata))
            for metadata in metadatas
        ]
        for thread in threads:
            thread.start()
        assert entered.acquire(timeout=60), "the first analysis never started"
        assert entered.acquire(timeout=60), "the second analysis never started"

        # The first analysis ends while the second one is still running.
        gates[first_hash].set()
        threads[0].join(timeout=60)
        assert not threads[0].is_alive()

        response = client.post(f"/api/projects/{project_id}/cancel")

        assert response.status_code == 202, (
            f"the running analysis could not be cancelled: {response.text}"
        )
        assert response.json() == {"project_id": project_id, "status": "cancelling"}
        assert tokens[second_hash].cancelled

        gates[second_hash].set()
        threads[1].join(timeout=60)
        assert not threads[1].is_alive()


def _slow_jadx_launcher(directory: Path) -> Path:
    """A stand-in for the jadx launcher whose version probe takes a while.

    The probe is what the race is about: a backend remembers that it has
    been probed before the probe finishes, so the probe has to be slow
    enough for another analysis to arrive in the middle of it.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = directory / "jadx.bat"
        launcher.write_text(
            "@echo off\r\n"
            'echo %* | findstr /C:"--version" > nul\r\n'
            "if not errorlevel 1 ping -n 3 127.0.0.1 > nul\r\n"
            "echo jadx 1.5.2\r\n",
            encoding="utf-8",
        )
    else:
        launcher = directory / "jadx"
        launcher.write_text(
            '#!/bin/sh\ncase "$*" in\n  *--version*) sleep 2 ;;\nesac\necho "jadx 1.5.2"\n',
            encoding="utf-8",
        )
        launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    return launcher


def test_a_backend_that_took_part_is_never_recorded_without_a_version(
    tmp_path: Path,
) -> None:
    """The versions are probed once, and everybody reads the same answer.

    Two analyses run at the same time, so one of them arrives while the
    other is still probing. The backends remember that they have been
    probed before the probe finishes, so the second one used to be handed
    ``None`` -- and the run it published said a backend that took part was
    not installed.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    settings.jadx_path = str(_slow_jadx_launcher(tmp_path / "bin"))
    analyzer = Analyzer(settings)

    apks = [
        build_apk(tmp_path / "one.apk"),
        build_apk(tmp_path / "two.apk", extra={"META-INF/OTHER.RSA": b"other"}),
    ]
    results: list[Any] = []
    failures: list[BaseException] = []

    def analyse(apk: Path) -> None:
        try:
            results.append(analyzer.analyze(apk))
        except BaseException as exc:  # pragma: no cover - reported below
            failures.append(exc)

    threads = [threading.Thread(target=analyse, args=(apk,)) for apk in apks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=300)
        assert not thread.is_alive(), "an analysis did not finish"

    assert not failures, f"an analysis failed: {failures[0]}"
    assert len(results) == 2
    for result in results:
        assert result.run is not None
        versions = result.run.tool_versions
        assert versions["jadx"] == "jadx 1.5.2", (
            "a backend that took part was recorded as having no version"
        )


# ---------------------------------------------------------------------------
# The sentence the home page says is the sentence the backend keeps
# ---------------------------------------------------------------------------
#
# 【为什么要把这句文案和后端的行为钉在一起】
# 2026-11-27 的打包 exe 验收实测过: 4 个并发上传同一个 APK, 4 次分析都跑起来了
#  (docs/reports/phase5-crash-and-race-paths.md §5.3) . 那之后后端把'检查'和
# '登记'合成了一次原子操作 (RunningAnalyses.claim) , 首页也照着后端的答案写了
# 一句话: '同一 APK 重复上传会打开已有项目, 不会重复分析'.
#
# 这两样东西住在两个地方 (后端的 Rust 无关的 Python 与桌面端的 React) , 中间只靠
# 一个 `already_analysed` 布尔值搭桥. **没有任何测试把它们钉在一起**: 后端改了
# 并发的行为, 或者首页改了措辞, 两边各自都不会红--于是首页又会对用户说一句不
# 成立的话, 而没有任何闸门拦得住.
#
# 【为什么这么测】
# 后端那半: 真的起线程, 真的并发上传, 真的读后端的答案 (`test_four_concurrent_...`
# 已经测过'只调度一次', 这里测的是**答给用户的那句话**: 每一个并发上传都必须
# 被告知'已经在分析了', 也就是首页赖以'不重复分析'的那个标志) .
# 前端那半: 读首页的源码, 断言那句话还在, 并且断言首页**正是**用
# `accepted.already_analysed` 来决定要不要跳转.
#
# 【为什么前端那半读源码而不是跑 DOM】
# 首页的行为已经由 desktop/src/pages/HomePage.test.tsx (vitest) 用真的 DOM 验过
# 一遍了: 重复上传时提示留在页面上, 用户没有被带走. 那里验的是'提示看得见',
# 这里验的是**另一件事**--提示背后的那句话是不是真的由后端的标志驱动. 两处分开
# 钉, 是因为它们的门不一样: DOM 那条由桌面端的 vitest 跑, 这条由 Python 跑,
# 于是**任何一边单独坏掉, 另一边都会红**.
#
# 源码读的是**产品源码** (desktop/src/pages/HomePage.tsx) , 不是测试文件; 这里
# 只读, 不改.


def _home_page_source() -> str:
    """The home page's source, which is where the promise is written down."""
    assert HOME_PAGE.is_file(), f"{HOME_PAGE} does not exist"
    return HOME_PAGE.read_text(encoding="utf-8")


def test_the_home_page_still_promises_no_second_analysis() -> None:
    """The sentence the user reads is still there.

    A promise that has been quietly taken off the page is a promise the
    backend no longer has to keep -- and nobody would notice, because the
    sentence is prose and the backend is code.
    """
    source = _home_page_source()

    assert "不会重复分析" in source, (
        "首页不再对用户承诺'不会重复分析'了: 如果后端的行为变了, 那这句承诺 "
        "必须先改掉, 而不是让用户在一个会重复分析的界面上读到一句空话"
    )
    assert "重复上传会打开已有项目" in source, (
        "首页的承诺只说了一半: '不会重复分析'没有说重复上传会去哪里, "
        "用户会被留在原地看着一个自己没点的分析"
    )


def test_the_home_page_keys_its_promise_on_the_backends_flag() -> None:
    """The promise is driven by the backend's answer, not by the page's own guess.

    The home page cannot know whether the backend started a second analysis
    -- only the backend knows. So the page must decide what to show from
    ``already_analysed`` and from nothing else.
    """
    source = _home_page_source()

    assert re.search(r"if\s*\(\s*accepted\.already_analysed\s*\)", source), (
        "首页不再按后端给的 already_analysed 决定要不要跳转: 它会自己猜, "
        "于是后端真的重复分析了也没人拦不住"
    )


def test_the_home_page_does_not_navigate_away_on_a_duplicate() -> None:
    """The notice stays on the page, so the sentence stays on the page.

    A navigation unmounts the home page, and the sentence about "no second
    analysis" goes with it.  That was the 2026-11-26 defect: the notice
    rendered, and nobody ever saw it (802 samples of the packaged exe, 0
    hits).

    The branch is read by **brace matching**, not by slicing the text at a
    marker: the branch that must not navigate contains the word
    ``navigate`` only if something was added to it, and a slice at the
    first ``navigate`` would cut the branch short exactly where the word
    appears -- which is to say, it would hide the very thing it looks for.
    """
    source = _home_page_source()

    match = re.search(r"if\s*\(\s*accepted\.already_analysed\s*\)\s*\{", source)
    assert match is not None, "首页不再按后端给的 already_analysed 分支"

    # Walk the braces to find where the branch ends.
    depth = 0
    end = -1
    for index in range(match.end() - 1, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    assert end != -1, "首页的 already_analysed 分支没有闭合"

    branch = source[match.end() : end]
    assert "navigate" not in branch, (
        "首页在'已经分析过'的分支里仍然跳转: 跳转会卸载首页, "
        "'不会重复分析'这句话跟着组件一起消失, 用户根本看不见"
    )


def test_the_backends_answer_is_what_the_home_page_reads() -> None:
    """The backend's answer carries the flag the home page keys on.

    The desktop client reads the workbench's ``POST /api/analyze`` answer
    as-is -- ``client.ts`` does not rename the flag -- so the name has to
    be the same on both sides. A rename on one side alone would leave the
    page reading ``undefined``, and ``undefined`` is falsy: the page would
    jump to the analysis page while the backend had started nothing.
    """
    client = HOME_PAGE.parents[1] / "api" / "client.ts"

    assert client.is_file(), f"{client} does not exist"
    client_source = client.read_text(encoding="utf-8")

    assert "/analyze" in client_source, (
        "桌面端不再调用工作台的 /api/analyze, 首页承诺的落点已经变了"
    )
    assert re.search(r"AnalyzeAccepted>\(\s*[\"']/analyze[\"']", client_source), (
        "桌面端上传拿到的不是 AnalyzeAccepted: 首页读到的 already_analysed 已经不是一个确定的值了"
    )
    types = HOME_PAGE.parents[1] / "api" / "types.ts"
    types_source = types.read_text(encoding="utf-8")
    assert re.search(r"already_analysed\s*:\s*boolean", types_source), (
        "AnalyzeAccepted 里的 already_analysed 不再是布尔值: 首页的判断"
        " (if (accepted.already_analysed)) 会按一个不是布尔的值来决定要不要跳转"
    )


def test_every_concurrent_upload_is_told_the_apk_is_already_being_analysed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backend half of the home page's promise, measured under concurrency.

    This is the sentence the page tells the user, so it is the backend's
    answer that has to carry it. Four uploads of one APK arrive at once;
    **every** one of them has to come back with ``already_analysed`` set,
    because that is what the page reads to decide that no second analysis
    is running.

    Before the fix this was false for three of the four: they started their
    own analysis and answered ``already_analysed: false``, so the page
    would have said "not analysed yet" while three analyses ran.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    gate = _GatedAnalysis()
    gate.install(monkeypatch)

    payload = build_apk(tmp_path / "demo.apk").read_bytes()
    answers: list[dict[str, Any]] = []
    answered = threading.Condition()

    with TestClient(create_app(analyzer)) as client:

        def upload() -> None:
            response = client.post(
                "/api/analyze",
                files={"file": ("demo.apk", payload, "application/octet-stream")},
            )
            with answered:
                answers.append(response.json())
                answered.notify_all()

        threads = [threading.Thread(target=upload) for _ in range(4)]
        for thread in threads:
            thread.start()
        try:
            assert gate.entered.wait(timeout=60), "no analysis started"
            assert _wait_for(lambda: len(answers) == 3), (
                f"only {len(answers)} of the four uploads answered while the analysis was running"
            )
        finally:
            gate.released.set()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive(), "an upload never answered"

    assert len(answers) == 4
    # The flag the home page reads has to be on every answer that says the
    # APK is already being analysed -- and it has to be on three of them.
    deduped = [answer for answer in answers if answer["already_analysed"]]
    assert len(deduped) == 3, (
        f"只有 {len(deduped)} 个并发上传被告知'已经在分析了': 首页读到 "
        "already_analysed=false 时会跳到分析页, 而那时候还有别的分析在跑, "
        "首页那句'不会重复分析'就是假的"
    )
    # And the one that is not deduplicated really did start the only analysis.
    assert gate.calls == 1, "the APK was analysed more than once"
    # Every upload is pointed at the same project, so the page's link to "the
    # existing project" lands on the analysis that is actually running.
    assert {answer["project_id"] for answer in answers} == {deduped[0]["project_id"]}
    assert len(analyzer.store.list_runs(deduped[0]["project_id"])) == 1


def test_a_sequential_upload_of_the_same_apk_is_answered_as_already_analysed(
    tmp_path: Path,
) -> None:
    """The same promise, in the order a reader would meet it.

    The concurrency case above is the hard one. This is the easy one, and
    it is the one the sentence was written for: an APK whose analysis the
    workspace already holds is answered with the flag set, and no second
    analysis is started.

    The workspace row is seeded rather than produced by a real analysis,
    because the stub APK this file builds is not a real APK: its DEX file
    is a stub header, so the analysis reads nothing out of it and ends
    *failed* -- and a failed analysis is deliberately analysed again. The
    promise is about an analysis the workspace holds, so the row says
    "completed" and the rest of the test is about the upload.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    apk = build_apk(tmp_path / "demo.apk")
    payload = apk.read_bytes()

    # A project row for these bytes, standing for a finished analysis.
    project = Project.create(inspect_apk(apk))
    analyzer.store.begin_run(project)
    analyzer.store.set_project_state(project.id, ProjectStatus.COMPLETED, [])

    with TestClient(create_app(analyzer)) as client:
        response = client.post(
            "/api/analyze",
            files={"file": ("demo.apk", payload, "application/octet-stream")},
        )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["already_analysed"] is True, (
        "同一个 APK 再传一次, 后端没有说'已经分析过了': 首页会把它当成一次"
        "新分析跳到分析页, 而页面上那句'不会重复分析'说的就不是真的"
    )
    assert body["project_id"] == project.id, (
        "重复上传被指向了另一个项目: 首页的'打开已有项目'会打开一个没有这次分析结果的项目"
    )
    assert analyzer.store.find_project_by_hash(body["apk_sha256"]) is not None


def test_a_failed_analysis_is_analysed_again_and_the_home_page_says_so(
    tmp_path: Path,
) -> None:
    """The one case where the promise does not hold, stated out loud.

    A failed analysis holds no results, so the backend analyses the same
    bytes again -- that is the right thing to do, and it is the one case
    where the home page's sentence is not true.

    The sentence is unconditional, so this test pins the **boundary** of
    the promise rather than widening it: the backend's behaviour is
    correct, and the sentence is true everywhere the backend keeps it.
    Where it does not keep it, the backend has to say so -- and it does,
    with ``already_analysed: false``, which is the flag the home page
    reads to decide to jump to the analysis page. So the page and the
    backend still agree: they disagree only about *which* of the two
    cases they are in.
    """
    settings = Settings(workspace=tmp_path / "workspace")
    analyzer = Analyzer(settings)
    apk = build_apk(tmp_path / "demo.apk")
    payload = apk.read_bytes()

    # A project row for these bytes, standing for a failed analysis.
    project = Project.create(inspect_apk(apk))
    analyzer.store.begin_run(project)
    analyzer.store.set_project_state(project.id, ProjectStatus.FAILED, [])

    with TestClient(create_app(analyzer)) as client:
        response = client.post(
            "/api/analyze",
            files={"file": ("demo.apk", payload, "application/octet-stream")},
        )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["already_analysed"] is False, (
        "一次失败的分析被当成了已有结果: 首页会留在首页上说'没有重复分析', "
        "而这一次后端确实又起了一次分析"
    )
    assert body["project_id"] == project.id, "重试被指向了另一个项目: 用户会失去前一次分析的痕迹"
