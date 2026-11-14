"""A backend whose launcher is already gone when the tree kill arrives.

``Backend.run`` bounds every invocation, and a call that outlives its bound
is killed with its whole tree. What the outcome then says about the kill is
a claim about the machine, which is why the three outcomes are kept apart:
the tree was killed, the launcher had already exited on its own, or nothing
could be killed and the work may still be running.

No launcher in the suite dies inside the window between the timeout and the
kill on purpose, so on a quiet machine the "already exited" outcome is never
reached — and a measurement of the suite would wobble over whether those
lines ran. These tests force the outcome instead of racing the scheduler:
the kill is made to find the launcher gone, deterministically.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ToolErrorCode
from dexatlas.tools import base
from dexatlas.tools.base import Backend as _Backend
from dexatlas.tools.base import ToolInvocation


class _StubBackend(_Backend):
    """Runs ``sys.executable``, so the tests exercise the real subprocess path."""

    name = "stub"

    def resolve(self) -> Path | None:
        return Path(sys.executable)

    def version(self) -> str | None:
        return "stub 1.0"


class _ProcessNotFound:
    """What ``taskkill`` answers for a pid that has already exited."""

    returncode = 128
    stdout = b""
    stderr = b""


@pytest.fixture
def launcher_dies_before_the_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    """End the launcher between the timeout and the tree kill.

    ``wait`` returns the moment the child dies, so a real run reaches the
    "already exited" outcome only when the launcher dies inside the window
    between the timeout firing and ``taskkill`` running. The fixture makes
    that window deterministic: the kill is answered with "no such process"
    *after* the launcher it names has been ended, which is the state the
    outcome reports.
    """
    real_run = subprocess.run

    if os.name != "nt":
        # On POSIX the tree kill is os.kill over the process group, not a
        # subprocess call. Making the group empty before the kill arrives is
        # the same window: the kill then reports the launcher as already
        # gone instead of claiming it was terminated. The real os.kill is
        # captured first -- the patched name must not recurse into itself.
        real_kill = os.kill

        def _kill_group_when_empty(pid: int, sig: int) -> None:
            with suppress(OSError):
                real_kill(pid, signal.SIGTERM)
            raise ProcessLookupError

        monkeypatch.setattr(base.os, "kill", _kill_group_when_empty)
        return

    def _kill_comes_too_late(argv: list[str], **kwargs: Any) -> Any:
        if argv and argv[0] == "taskkill":
            # The launcher is the process the kill names. Ending it here —
            # after the timeout, before the kill lands — is the window the
            # outcome describes.
            with suppress(OSError):
                os.kill(int(argv[-1]), signal.SIGTERM)
            time.sleep(0.3)  # long enough for the exit to be visible to poll()
            return _ProcessNotFound()
        return real_run(argv, **kwargs)

    monkeypatch.setattr(base.subprocess, "run", _kill_comes_too_late)


def test_a_timeout_whose_launcher_already_exited_says_so(
    settings: Settings, launcher_dies_before_the_kill: None
) -> None:
    """The message must name the launcher's state, not claim a kill.

    "Was terminated" would be false: by the time the kill arrived there was
    nothing left to terminate. "Could not be terminated" would be false too:
    nothing needed terminating, and nothing was left running.
    """
    outcome = _StubBackend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert "already exited" in outcome.error.message
    assert "was terminated" not in outcome.error.message
    assert "could not be terminated" not in outcome.error.message


def test_the_tree_kill_reports_a_launcher_it_cannot_find(
    settings: Settings, launcher_dies_before_the_kill: None
) -> None:
    """The outcome is what the message is built from, so it must be exact.

    A kill that finds the pid gone reports "already exited" — not "killed",
    which would claim the tree was stopped, and not "not terminated", which
    would claim the work may still be running.
    """
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
    try:
        os.kill(process.pid, signal.SIGTERM)
        time.sleep(0.3)
        process.wait()
        assert base._taskkill_tree(process) == base._ALREADY_EXITED
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


@pytest.fixture
def the_kill_cannot_find_the_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the tree kill fail while the launcher is still alive.

    ``taskkill`` can fail for a launcher that is still running — access
    denied is the usual reason — and the outcome must not claim a kill that
    did not happen. Forcing the failure keeps the test off the machine's
    permission state.
    """

    class _Refused:
        returncode = 1  # what taskkill answers when it could not kill
        stdout = b""
        stderr = b""

    def _refused(*args: Any, **kwargs: Any) -> _Refused:
        return _Refused()

    if os.name != "nt":
        # On POSIX the tree kill is os.kill over the process group. A
        # PermissionError is what the same refusal looks like there.
        def _permission_denied(pid: int, sig: int) -> None:
            raise PermissionError

        monkeypatch.setattr(base.os, "kill", _permission_denied)
        return

    monkeypatch.setattr(base.subprocess, "run", _refused)


def test_a_timeout_that_could_not_kill_a_live_launcher_says_so(
    settings: Settings, the_kill_cannot_find_the_tree: None
) -> None:
    """A live launcher the kill could not stop must be reported as such.

    The message is the report reader's only account of what happened on the
    machine: saying "was terminated" here would claim a kill that failed,
    and saying "already exited" would claim a process that is still alive.
    """
    outcome = _StubBackend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert "could not be terminated" in outcome.error.message
    assert "was terminated" not in outcome.error.message
    assert "already exited" not in outcome.error.message


@pytest.fixture
def the_kill_itself_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the kill call itself fail, the way a broken machine would.

    ``taskkill`` is a subprocess call, and the call can fail — the machine
    may be out of handles, or the call may outlive its own bound. The
    outcome must say the tree was not terminated rather than guess.
    """

    def _broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("the kill could not run")

    if os.name != "nt":
        # On POSIX the kill is os.kill; an OSError from it is the same
        # broken-machine refusal.
        monkeypatch.setattr(base.os, "kill", _broken)
        return

    monkeypatch.setattr(base.subprocess, "run", _broken)


def test_a_kill_that_cannot_run_says_the_tree_survived(
    settings: Settings, the_kill_itself_fails: None
) -> None:
    """A kill that failed to run must not be reported as a kill.

    The work the launcher started may still be running, and the reader of
    the message has to know that.
    """
    outcome = _StubBackend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert "could not be terminated" in outcome.error.message
    assert "was terminated" not in outcome.error.message
