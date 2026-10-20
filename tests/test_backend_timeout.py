"""A backend that outlives its timeout.

A backend is often a launcher rather than the work itself: ``jadx.bat`` is a
``cmd.exe`` whose child is ``java.exe``. Killing the process that was started
does not kill the work it started — and the work keeps the output the caller
is waiting on, so the call waits for it anyway. The timeout said the call was
over while the decompiler was still running.

These tests hold the whole tree down, and they say so when they cannot.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ToolErrorCode
from dexatlas.tools.base import Backend, ToolInvocation
from dexatlas.tools.jadx.adapter import JadxBackend

EXAMPLES = Path(__file__).parent.parent / "examples"


class _StubBackend(Backend):
    """Runs ``sys.executable``, so the tests exercise the real subprocess path."""

    name = "stub"

    def resolve(self) -> Path | None:
        return Path(sys.executable)

    def version(self) -> str | None:
        return "stub 1.0"


#: A launcher that starts the work and then waits for a long time.
#:
#: The grandchild is the work: it writes its marker five seconds in, so a
#: marker that appears means the tree was not taken down. It inherits the
#: launcher's output, which is what the old implementation was waiting on.
LAUNCHER = """
import subprocess
import sys
import time

subprocess.Popen([
    sys.executable,
    "-c",
    "import pathlib, sys, time; time.sleep(5); pathlib.Path(sys.argv[1]).write_text('alive')",
    sys.argv[1],
])
time.sleep(60)
"""

#: The same shape as ``jadx.bat``: a batch file that runs the work in the
#: foreground, so the work is the ``cmd.exe``'s child.
WINDOWS_LAUNCHER = (
    "@echo off\r\n"
    '"{python}" -c "import pathlib, sys, time; time.sleep(5); '
    'pathlib.Path(sys.argv[1]).write_text(\'alive\')" "{marker}"\r\n'
)


def test_a_timeout_takes_the_whole_tree_down(settings, tmp_path: Path) -> None:
    """The launcher is not the work, and killing it must not leave the work.

    The old implementation killed the direct child only. The grandchild went
    on, wrote its marker, and the call waited for it — so a one-second
    timeout took as long as the work did.
    """
    marker = tmp_path / "grandchild-ran"
    launcher = tmp_path / "launcher.py"
    launcher.write_text(LAUNCHER, encoding="utf-8")

    started = time.monotonic()
    outcome = _StubBackend(settings).run(
        ToolInvocation(argv=[sys.executable, str(launcher), str(marker)], timeout=1)
    )
    elapsed = time.monotonic() - started

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert elapsed < 3.0, f"the call took {elapsed:.1f}s to give up on a 1s timeout"

    # The grandchild would have written its marker five seconds in.
    time.sleep(5.2)
    assert not marker.exists(), "the process the launcher started was still running"


@pytest.mark.skipif(os.name != "nt", reason="a batch file is a Windows launcher")
def test_a_windows_launcher_is_stopped_with_its_work(settings, tmp_path: Path) -> None:
    """The shape ``jadx.bat`` has: a ``cmd.exe`` whose child is the work.

    The old timeout killed the ``cmd.exe`` and left the work running, and the
    call waited for the work — so a one-second timeout took five.
    """
    marker = tmp_path / "grandchild-ran"
    launcher = tmp_path / "launcher.bat"
    launcher.write_text(
        WINDOWS_LAUNCHER.format(python=sys.executable, marker=marker),
        encoding="utf-8",
    )

    started = time.monotonic()
    outcome = _StubBackend(settings).run(ToolInvocation(argv=[str(launcher)], timeout=1))
    elapsed = time.monotonic() - started

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert elapsed < 3.0, f"the call took {elapsed:.1f}s to give up on a 1s timeout"

    time.sleep(5.2)
    assert not marker.exists(), "the work the launcher started was still running"


def test_a_timeout_that_could_not_stop_the_tree_says_so(settings, monkeypatch) -> None:
    """The message must not claim a termination that did not happen.

    "Was terminated" is a promise about the machine, and a promise the code
    cannot keep has to be withdrawn rather than repeated.
    """
    from dexatlas.tools import base

    monkeypatch.setattr(base, "_terminate_tree", lambda process: base._NOT_TERMINATED)

    outcome = _StubBackend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    assert "could not be terminated" in outcome.error.message
    assert "was terminated" not in outcome.error.message


@pytest.mark.slow
@pytest.mark.skipif(JadxBackend(Settings()).resolve() is None, reason="jadx not installed")
def test_the_real_decompiler_is_stopped_by_the_timeout(settings, tmp_path: Path) -> None:
    """The real launcher chain, on the real decompiler.

    ``jadx.bat`` is a ``cmd.exe`` whose child is ``java.exe``. The old timeout
    killed the ``cmd.exe``, left the ``java.exe`` running and waited for it:
    a one-second timeout took as long as the decompiler did.

    The decompiler on a small APK finishes its writing early, so what is
    checked here is that the timeout is what ended the call — and the batch
    file above is the same launcher shape, watched for the work itself.
    """
    backend = JadxBackend(settings)
    apk = (EXAMPLES / "demo-app" / "demo.apk").resolve()

    outcome = backend.decompile(apk, tmp_path / "jadx", timeout=1)

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code is ToolErrorCode.TIMEOUT
    # Either the tree was killed, or the launcher had already finished the
    # work itself — what must not happen is a message that says nothing could
    # be stopped while the decompiler is still going.
    assert "could not be terminated" not in outcome.error.message
