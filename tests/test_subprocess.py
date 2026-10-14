"""Subprocess execution.

This is the boundary where DexAtlas hands untrusted APK-derived paths to external
engines, and where a crash or a hang in those engines must degrade one step instead of
the whole run. It is the least-covered code in the project, so it gets the most direct
tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dexatlas.core.models import ToolErrorCode
from dexatlas.tools.base import Backend, ToolInvocation, which_or_none

pytestmark = pytest.mark.slow


class _StubBackend(Backend):
    """Runs ``sys.executable -c <source>`` so tests exercise the real subprocess path."""

    name = "stub"

    def resolve(self) -> Path | None:
        return Path(sys.executable)

    def version(self) -> str:
        return "stub 1.0"


def _backend(settings) -> _StubBackend:
    return _StubBackend(settings)


def test_successful_invocation(settings) -> None:
    outcome = _backend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "print('hello')"])
    )

    assert outcome.ok
    assert outcome.returncode == 0
    assert "hello" in outcome.stdout
    assert outcome.error is None
    assert outcome.duration_seconds >= 0


def test_stderr_is_captured_separately(settings) -> None:
    outcome = _backend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import sys; sys.stderr.write('oops')"])
    )

    assert outcome.ok
    assert "oops" in outcome.stderr
    assert "oops" not in outcome.stdout


def test_nonzero_exit_is_an_error_not_an_exception(settings) -> None:
    """A tool rejecting a file is an expected outcome. It must be a value."""
    outcome = _backend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import sys; sys.exit(3)"])
    )

    assert not outcome.ok
    assert outcome.returncode == 3
    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.EXIT_NONZERO
    assert "3" in outcome.error.message


def test_nonzero_exit_preserves_stderr_for_diagnosis(settings) -> None:
    outcome = _backend(settings).run(
        ToolInvocation(
            argv=[sys.executable, "-c", "import sys; sys.stderr.write('bad dex'); sys.exit(1)"]
        )
    )

    assert outcome.error is not None
    assert "bad dex" in (outcome.error.detail or "")


def test_timeout_terminates_and_records(settings) -> None:
    """A hung backend must be killed, not left to block the pipeline forever."""
    outcome = _backend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import time; time.sleep(30)"], timeout=2)
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.TIMEOUT
    assert "2s" in outcome.error.message


def test_missing_executable_is_recorded(settings) -> None:
    outcome = _backend(settings).run(
        ToolInvocation(argv=[str(Path("nonexistent-tool-xyz")), "--help"])
    )

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.NOT_INSTALLED


def test_empty_invocation_is_rejected(settings) -> None:
    outcome = _backend(settings).run(ToolInvocation(argv=[]))

    assert not outcome.ok
    assert outcome.error is not None
    assert outcome.error.code == ToolErrorCode.UNSUPPORTED


def test_non_utf8_output_does_not_crash(settings) -> None:
    """A tool emitting arbitrary bytes must not take the process down."""
    outcome = _backend(settings).run(
        ToolInvocation(
            argv=[
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'\\xff\\xfe\\x00\\x80binary')",
            ]
        )
    )

    assert outcome.stdout  # decoded with replacement, not raised on


def test_oversized_output_is_truncated(settings) -> None:
    from dexatlas.config.settings import Settings

    bounded = Settings(workspace=settings.workspace, tool_max_output_bytes=2048)
    outcome = _StubBackend(bounded).run(
        ToolInvocation(argv=[sys.executable, "-c", "print('x' * 100000)"])
    )

    assert len(outcome.stdout.encode("utf-8", errors="replace")) < 100000


def test_argv_cannot_inject_a_shell_command(settings, tmp_path: Path) -> None:
    """Arguments are a list, never a shell string — a path containing shell syntax must
    arrive at the tool as a literal argument."""
    marker = tmp_path / "pwned"
    hostile = f"; touch {marker}"

    outcome = _backend(settings).run(
        ToolInvocation(argv=[sys.executable, "-c", "import sys; print(sys.argv[1])", hostile])
    )

    assert hostile in outcome.stdout
    assert not marker.exists()


def test_provenance_records_tool_and_version(settings) -> None:
    backend = _backend(settings)

    provenance = backend.provenance("b" * 64, "some/locator")

    assert provenance.tool == "stub"
    assert provenance.tool_version == "stub 1.0"
    assert provenance.apk_sha256 == "b" * 64
    assert provenance.locator == "some/locator"


def test_missing_error_names_the_tool(settings) -> None:
    error = _backend(settings).missing_error()

    assert error.code == ToolErrorCode.NOT_INSTALLED
    assert "stub" in error.message
    assert "DEXATLAS_" in (error.detail or "")


# -- discovery --------------------------------------------------------------


def test_which_or_none_finds_an_existing_path(tmp_path: Path) -> None:
    target = tmp_path / "tool"
    target.write_text("#!/bin/sh\n", encoding="utf-8")

    assert which_or_none([str(target)]) == target


def test_which_or_none_falls_back_to_path_lookup() -> None:
    found = which_or_none([None], names=("python",))

    assert found is not None
    assert found.name.lower().startswith("python")


def test_which_or_none_returns_none_when_absent(tmp_path: Path) -> None:
    assert which_or_none([str(tmp_path / "missing")], names=("definitely-not-a-real-tool",)) is None
