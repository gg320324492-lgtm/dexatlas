"""A backend that writes more than the cap has not produced all of its output.

The cap on a backend's output exists so that a runaway tool cannot fill the
disk. What happens to the output past the cap is a matter of record rather
than of silence: the bytes that were kept are the *first* ones the backend
wrote, and a reader handed them without being told has been handed a
shortened thing.

The warning that was supposed to say so could never fire. The output file
was truncated before it was read, so the length of what arrived could never
exceed the cap, and the branch that was meant to notice could never be
taken. A backend whose output was cut was indistinguishable from one whose
output was not, and the report said nothing about either.

These tests need no backend installed. The base class's runner is exercised
directly, with a script that writes more than the cap allows, and the
pipeline is driven with a stand-in backend that says it was truncated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ToolErrorCode
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome
from dexatlas.tools.jadx.adapter import JadxBackend

#: The smallest cap the settings accept, and therefore the one these tests use.
CAP = 1024


class _NoisyBackend(Backend):
    """A backend whose tool writes more than the cap allows.

    The tool is not a tool: the runner is exercised with a script, so the
    test asks the question on any machine.
    """

    name = "noisy"

    def resolve(self) -> Path | None:
        return None

    def version(self) -> str | None:
        return "1.0"


def _a_script_that_writes(path: Path, amount: int) -> Path:
    """A script that writes ``amount`` bytes to stdout and to stderr."""
    path.write_text(
        f"import sys\nsys.stdout.write('x' * {amount})\nsys.stderr.write('y' * {amount})\n",
        encoding="utf-8",
    )
    return path


# -- the runner says what it cut ---------------------------------------------


def test_a_backend_that_writes_too_much_says_that_it_did(
    settings: Settings, tmp_path: Path
) -> None:
    """The output was cut at the cap, and the outcome says so.

    The length of what arrived used to be compared against the cap inside
    the decoder, where it could never be larger. The comparison has to be
    made where the size is still known: at the file, before it is truncated.
    """
    script = _a_script_that_writes(tmp_path / "noisy.py", 5000)
    settings.tool_max_output_bytes = CAP

    outcome = _NoisyBackend(settings).run(ToolInvocation(argv=[sys.executable, str(script)]))

    assert outcome.truncated == ("stdout", "stderr"), "the cut output was not reported"


def test_what_is_kept_is_the_first_of_the_output(settings: Settings, tmp_path: Path) -> None:
    """The cap keeps the head of the output, so the output is a prefix.

    A reader who is told the output was cut has to be able to tell *which*
    part was kept, or "it was truncated" says nothing about what is in
    front of them.
    """
    script = _a_script_that_writes(tmp_path / "noisy.py", 5000)
    settings.tool_max_output_bytes = CAP

    outcome = _NoisyBackend(settings).run(ToolInvocation(argv=[sys.executable, str(script)]))

    assert len(outcome.stdout) == CAP
    assert outcome.stdout == "x" * CAP


def test_an_output_that_fits_is_not_reported_as_cut(settings: Settings, tmp_path: Path) -> None:
    """The limits are limits, not a permanent condition.

    A backend whose output fits says nothing about being cut, or every
    report would carry a warning about a truncation that never happened.
    """
    script = _a_script_that_writes(tmp_path / "quiet.py", 10)
    settings.tool_max_output_bytes = CAP

    outcome = _NoisyBackend(settings).run(ToolInvocation(argv=[sys.executable, str(script)]))

    assert outcome.truncated == ()
    assert outcome.ok


# -- the project says it -----------------------------------------------------


def test_a_truncated_output_is_recorded_on_the_project(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gap has to reach the project, or the report cannot mention it.

    A record in the log is not enough: the report is read by somebody who
    was not watching the log, and a project that holds a complete-looking
    analysis of a backend whose output was cut is a complete-looking lie.
    """
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("/fake/jadx"))
    monkeypatch.setattr(JadxBackend, "version", lambda self: "1.5.2")
    monkeypatch.setattr(
        JadxBackend,
        "decompile",
        lambda self, apk, output_dir, **kwargs: ToolOutcome(
            returncode=0,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            truncated=("stdout",),
        ),
    )
    monkeypatch.setattr(JadxBackend, "extract", lambda self, *args, **kwargs: ([], None))
    monkeypatch.setattr(JadxBackend, "decompilation_status", lambda self, output_dir: {})
    settings.tool_max_output_bytes = CAP

    result = Analyzer(settings).analyze(
        minimal_apk, include_apktool=False, include_androguard=False
    )

    truncations = [
        error for error in result.project.errors if error.code is ToolErrorCode.OUTPUT_TRUNCATED
    ]
    assert truncations, "the truncation was not recorded on the project"
    assert f"{CAP}-byte output cap" in truncations[0].message, (
        "the error does not name the cap that was applied"
    )


def test_the_cap_is_named_with_its_value(settings: Settings) -> None:
    """A limit a reader cannot check is a claim rather than a limit.

    The error says what the cap was, so a reader can compare it with the
    settings their own deployment uses.
    """
    from dexatlas.tools.base import truncation_error

    error = truncation_error("jadx", ("stdout",), CAP)

    assert str(CAP) in error.message
    assert str(CAP) in (error.detail or "")
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
