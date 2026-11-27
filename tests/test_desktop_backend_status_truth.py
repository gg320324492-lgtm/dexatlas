"""The backend status card must be able to tell two apart that look alike.

The card on the analysis page answers one question per backend: what
happened to it in *this* analysis.  Two of the facts it needs come from
the backend and are easy to confuse:

* the run's ``tool_versions`` says which versions the run **recorded** --
  and a recorded version may be ``null``;
* ``GET /api/backends`` says which backends are **installed on this
  machine**.

A ``null`` version means one of two things -- "not probed yet" or "not
installed" -- and the run's record cannot tell them apart.  Measured on
the packaged executable on 2026-11-27, both were said wrong: an analysis
in progress called three installed backends "not installed", and a
finished analysis on a machine without jadx/apktool kept calling them
"version being probed" long after the probing was over.

The mapping itself is unit-tested by the desktop's own door
(``desktop/src/stages.test.ts``, vitest); what this file pins down is the
**wiring** -- that the page actually hands the machine's list to the
mapping, so the two facts cannot drift apart again.

This file also pins the third meaning of a ``null``, which the two
sources above cannot separate on their own: a backend that **is**
installed but whose version **probe failed**.  The three meanings are
pinned here from the backend side -- where each one is produced -- and in
``desktop/src/stages.test.ts`` from the UI side -- what the card says
about each.  The pair the UI cannot separate is stated rather than
papered over.
"""

from __future__ import annotations

import os
import re
import stat
import threading
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.registry import BackendRegistry

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PAGE = ROOT / "desktop" / "src" / "pages" / "Analysis.tsx"
STAGES_MODULE = ROOT / "desktop" / "src" / "stages.js"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def test_the_page_asks_the_machine_which_backends_are_missing() -> None:
    """The machine's list is what separates "not probed" from "not installed"."""
    source = _source(ANALYSIS_PAGE)

    assert "getBackends()" in source, (
        "the analysis page does not read GET /api/backends, so it cannot tell "
        "a backend that is missing from one whose version is not probed yet"
    )


def test_the_page_hands_the_machine_s_list_to_the_mapping() -> None:
    """The list has to reach ``deriveBackends``; reading it is not enough."""
    source = _source(ANALYSIS_PAGE)

    assert re.search(r"deriveBackends\(\s*latestRun\s*,\s*machineBackends\s*\)", source), (
        "the analysis page does not hand the machine's backend list to deriveBackends"
    )
    assert "setMachineBackends" in source, (
        "the machine's backend list is never stored, so it cannot be handed over"
    )


def test_the_mapping_reads_the_missing_list() -> None:
    """The mapping has to use the list, not only the run's record."""
    source = _source(STAGES_MODULE)

    assert re.search(r"machine\s*&&\s*machine\.missing", source), (
        "deriveBackends does not read the missing list, so a missing backend "
        "still reads as one that is being probed"
    )


def test_the_card_says_where_each_claim_comes_from() -> None:
    """A reader who lands on the card can see which fact each line rests on."""
    source = _source(ANALYSIS_PAGE)

    assert "/api/backends" in source, "the card does not name the machine's list"
    assert "tool_versions" in source, "the card does not name the run's record"


# ---------------------------------------------------------------------------
# The three meanings of a ``null`` version
# ---------------------------------------------------------------------------
#
# 【null 有三种含义, 不是两种】
# 一轮分析在 ``run.tool_versions`` 里记下的版本可能是 ``null``. 三种东西都会
# 写出这个 ``null``:
#
#   ① **还没探测** -- 探测还没跑完 (或者正在跑) . 管道在探测前先把**名字**写
#      下去 (pipeline.py) , 所以键在, 值为空.
#   ② **压根没装** -- 机器上没有这个后端, 探测无从谈起.
#   ③ **探测失败** -- 后端**装着** (`available()` 为真) , 但 `--version` 跑起来
#      非零退出或什么都没打印, 于是版本是 ``null``.
#
# ② 和 ③ 只有一条证据能分开: **机器的那份名单** (`GET /api/backends` 的
# `missing`) . 名单上是'没装'的才是 ②; 名单上**没有**它, 而它确实装着, 就是
# ③ 或者 ①. ① 和 ③ 的分界证据是**时间**: 轮次还在跑时探测可能没结束, 分析结
# 束之后还没版本, 就只可能是探测失败了.
#
# 【这个文件钉住哪一半】
# 这里钉的是**后端那半**: 每一种 ``null`` 究竟是在什么地方被写出来的. 这件事
# 只能在后端量--前端只能看见一个 ``null``, 分不出它是哪一种. 另一半 (界面把
# 每一种说成什么) 由 ``desktop/src/stages.test.ts`` (vitest) 钉住.
#
# 【为什么不能只测前端的映射】
# 前端的映射函数接收的是一个 ``null`` 和一份机器名单, 它**不知道** ``null``
# 是怎么来的. 如果后端改了探测的写法 (把探测失败也写成'没装', 或者反过来) ,
# 前端的映射一个字都不用改, 它还是绿的, 而它说的那句话已经不对了. 所以这里要
# 从产生 ``null`` 的那一侧量.


def _broken_launcher(directory: Path) -> Path:
    """A launcher that exists and can be found, but whose version probe fails.

    This is meaning ③: the backend **is** on the machine -- ``available()``
    is true, the registry does not list it as missing -- but running it
    with ``--version`` produces no version.

    The launcher has to be a real file for the backend to find it, and it
    has to exit without printing a version for the probe to fail. Both are
    spelled differently on the two platforms, so both are written.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = directory / "jadx.bat"
        launcher.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
    else:
        launcher = directory / "jadx"
        launcher.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    return launcher


def test_a_backend_that_is_not_installed_reports_no_version(tmp_path: Path) -> None:
    """Meaning ②: the backend is not on the machine.

    ``resolve()`` finds nothing, so the probe never runs and the version is
    ``None``.  The registry lists the backend as missing, and that is the
    fact the machine's list carries to the front end.
    """
    settings = Settings(workspace=tmp_path / "workspace", jadx_path="")
    registry = BackendRegistry(settings)

    backend = registry.get("jadx")
    assert backend.available() is False, (
        "jadx_path 被显式关掉之后, 后端仍然说自己装着: 机器名单会把 ② 说成 ③"
    )
    assert backend.version() is None, "没装的后端报出了一个版本"
    assert "jadx" in [b.name for b in registry.missing()], (
        "没装的后端没有进机器名单: 界面分不出 ② 和 ①/③"
    )


def test_a_backend_whose_probe_failed_reports_no_version_but_is_installed(
    tmp_path: Path,
) -> None:
    """Meaning ③: the backend is installed and its version probe failed.

    This is the meaning the two sources cannot separate on their own: the
    run's record says ``None`` and the backend says ``None``, but the
    backend is **on the machine** -- ``available()`` is true and the
    registry does not list it as missing.

    The version probe failing is not a hypothetical: a launcher that cannot
    be run (a wrong architecture, a broken jar, a missing Java) produces
    exactly this, and the analysis still goes on without it.
    """
    launcher = _broken_launcher(tmp_path / "bin")
    settings = Settings(workspace=tmp_path / "workspace", jadx_path=str(launcher))
    registry = BackendRegistry(settings)

    backend = registry.get("jadx")
    assert backend.available() is True, (
        "探测失败的后端被说成'没装': 机器名单会把 ③ 和 ② 混成一件, 而这两个意思对读者是完全不同的"
    )
    assert backend.version() is None, (
        "探测失败的后端报出了一个版本: 这个测试要量的正是'装着, 但版本问不出来'"
    )
    assert "jadx" not in [b.name for b in registry.missing()], (
        "探测失败的后端进了机器的'没装'名单: ③ 被说成了 ②"
    )
    # And the machine's list says it is there, with no version -- which is
    # the pair of facts the card has to read.
    versions = registry.versions()
    assert versions["jadx"] is None
    assert "jadx" in [b.name for b in registry.available()]


def test_the_core_treats_every_null_version_as_a_missing_backend(
    tmp_path: Path,
) -> None:
    """The core's own list cannot tell the three apart either -- and says so.

    ``missing_backends()`` reads a ``null`` version as "this backend did
    not take part".  That is true of ② and of ①, and **false** of ③: a
    backend that is installed and whose probe failed did take part -- it is
    recorded as failing in the errors, and the analysis went on without it.

    This test pins the *current* behaviour of the core, which is what the
    desktop's "missing backends" banner reads.  It is a measurement, not
    an endorsement: the point of a measurement is that the next change to
    the code has to come here and say what it means.

    The desktop's own card does not read this list -- it reads the run's
    record and the machine's list, and those two *do* separate ③ from ②.
    This is the one place where the three meanings are still collapsed, and
    it is named here so that it is a decision rather than an accident.

    The measurement is made against a **real** analysis: a jadx that is
    installed on the machine and whose version probe fails.  The analysis
    succeeds (the DEX reader does the work), and jadx's failure is
    recorded under jadx's own name -- so the record says "jadx did not
    take part" about a backend that was on the machine the whole time.
    """
    from dexatlas.mcp.tools.projects import missing_backends

    launcher = _broken_launcher(tmp_path / "bin")
    settings = Settings(workspace=tmp_path / "workspace", jadx_path=str(launcher))
    analyzer = Analyzer(settings)

    # The first-party sample: a real APK, so the analysis really succeeds.
    apk = ROOT / "examples" / "demo-app" / "demo.apk"
    result = analyzer.analyze(apk)

    # jadx was installed and took part -- the analysis only failed to ask it
    # for its version.
    assert analyzer.backends.get("jadx").available() is True, (
        "这个测试要的是一个**装着**的后端, 不是一个没装的"
    )
    assert result.project.tool_versions["jadx"] is None, (
        "这个测试要的是 ③ (装着, 但版本问不出来) , 而版本问出来了"
    )
    assert any(error.tool == "jadx" for error in result.project.errors), (
        "jadx 的失败没有记在 jadx 名下: 记录里看不出它参与过"
    )

    # And the core's list says it did not take part.
    absent = missing_backends(result.project)
    assert "jadx" in absent, (
        "核心的 missing_backends() 不再把每个 null 版本都算成'没参与'了: "
        "这要么是一次行为改动 (那就得说明它在三种含义之间怎么选) , 要么是笔误"
    )


def test_the_three_meanings_of_a_null_version_come_from_three_different_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three meanings are three different facts, and they are told apart.

    This is the summary of the three tests above, measured end to end: the
    three meanings are not one meaning wearing three hats, and each one is
    produced by a place in the code.

    - ① comes from the pipeline writing the **names** down before it probes;
    - ② comes from ``resolve()`` finding nothing;
    - ③ comes from the probe running and coming back with no version.

    The two facts the front end has -- the run's record and the machine's
    list -- separate ① from ② and ② from ③.  They do **not** separate ①
    from ③ while the run is alive: both are about a backend that is
    installed and whose version is not recorded yet.  That is the pair the
    card cannot tell apart, and it is what the vitest suite pins down on
    the front end's side.
    """
    from dexatlas.core.ingest import inspect_apk
    from dexatlas.core.models import Project
    from dexatlas.core.runs import RunStatus
    from tests.conftest import build_apk

    # ② -- not installed: the machine's list says so.
    not_installed = BackendRegistry(Settings(workspace=tmp_path / "w1", jadx_path=""))
    assert "jadx" in [b.name for b in not_installed.missing()]

    # ③ -- installed, probe failed: the machine's list does NOT say so.
    launcher = _broken_launcher(tmp_path / "bin")
    probe_failed = BackendRegistry(Settings(workspace=tmp_path / "w2", jadx_path=str(launcher)))
    assert probe_failed.get("jadx").available() is True
    assert "jadx" not in [b.name for b in probe_failed.missing()], (
        "③ 和 ② 在机器名单上分不开了: 装着的后端被说成没装"
    )
    assert probe_failed.versions()["jadx"] is None

    # ① -- the analysis has started and the probe has not finished: the run's
    # record names the backends, and the machine's list says they are there.
    settings = Settings(workspace=tmp_path / "w3")
    analyzer = Analyzer(settings)
    apk = build_apk(tmp_path / "demo.apk")

    reached = threading.Event()
    release = threading.Event()
    original = BackendRegistry.versions

    def versions(self: BackendRegistry) -> dict[str, str | None]:
        reached.set()
        assert release.wait(timeout=30), "the test never released the probe"
        return original(self)

    monkeypatch.setattr(BackendRegistry, "versions", versions)

    failure: list[BaseException] = []

    def run() -> None:
        try:
            analyzer.analyze(apk, include_jadx=False, include_apktool=False)
        except BaseException as exc:  # pragma: no cover - reported below
            failure.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        assert reached.wait(timeout=30), "the analysis never reached the probe"
        project_id = Project.create(inspect_apk(apk)).id
        stored = analyzer.store.list_runs(project_id)[0]
        assert stored.status is RunStatus.RUNNING
        # The order matters: the name has to be there before the version can
        # be asked about, so the name is checked first.
        assert "androguard" in stored.tool_versions, (
            "① 的样子不对: 探测开始前, 轮次行上连名字都没有 -- "
            "读者看到的是'这台机器上一个后端都没有', 而不是'正在探测'"
        )
        assert stored.tool_versions["androguard"] is None, (
            "① 的样子不对: 探测还没开始, 版本却已经记下来了"
        )
    finally:
        release.set()
        worker.join(timeout=60)

    assert not failure, failure
    # ① and ③ are told apart by **time**: once the probe is done, a version
    # is on the row, so a null that is still there afterwards is ③.
    after = analyzer.store.list_runs(project_id)[0]
    assert after.tool_versions.get("androguard") is not None, (
        "探测结束了, 轮次行上的版本还是空的: ① 和 ③ 就再也分不开了"
    )
