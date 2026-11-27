"""The workspace path must not leave the machine inside an error message.

An error message can quote the path it was handed, and that path is the
server's. The redaction that replaces the workspace root with a placeholder
lives where the message is written (``dexatlas.core.paths.redact_workspace``),
so the message is redacted once and is redacted everywhere it is read back
from -- the API, the JSON report, the Markdown report.

**The path is quoted in two shapes, and only one of them was handled.**
``OSError.__str__`` renders the file name through ``repr()``, which doubles
the backslashes: on Windows the message holds ``E:\\\\work\\\\ws`` where the
path is ``E:\\work\\\\ws``. The redaction looked for the plain shape only, so
the path went into the message, into the database and into the interface
unchanged -- and the failure it leaked on is the commonest one there is
("this file was not there").

This was found by fault injection on 2026-11-27: the analysis was made to
fail with a ``FileExistsError`` and the probe read
``redaction changed msg: False``. **It does not reproduce on Linux** -- there
the repr of a path is the path -- so the test below builds the Windows shape
explicitly: the rule is the same on every platform, so the rule is tested on
every platform.
"""

from __future__ import annotations

from pathlib import Path

from dexatlas.core.paths import redact_workspace

#: A workspace root shaped the way Windows spells one. ``Path`` does not
#: split a POSIX path on backslashes, so ``str()`` of it is this text on
#: every platform -- which is what makes the test below platform-independent.
WINDOWS_ROOT = Path(r"C:\work\ws")


def test_a_path_quoted_as_repr_is_redacted() -> None:
    """The shape an ``OSError`` quotes it in must be redacted too.

    This is the shape the message really has on Windows, and it is the shape
    the redaction used to miss.
    """
    quoted = str(WINDOWS_ROOT).replace("\\", "\\\\")
    message = f"[Errno 17] File exists: '{quoted}'"

    redacted = redact_workspace(message, WINDOWS_ROOT)

    assert str(WINDOWS_ROOT) not in redacted, (
        "the workspace path leaked out of the message: " + redacted
    )
    assert "<workspace>" in redacted, "the message lost its path entirely: " + redacted


def test_a_path_quoted_plainly_is_still_redacted() -> None:
    """The shape that worked before must keep working."""
    message = f"cannot read {WINDOWS_ROOT}/projects/p1/runs/r1/dexatlas.db"

    redacted = redact_workspace(message, WINDOWS_ROOT)

    assert str(WINDOWS_ROOT) not in redacted
    assert "<workspace>" in redacted


def test_the_rest_of_the_path_survives() -> None:
    """The workspace root names the machine; what is inside it is the analysis.

    Redacting the whole message would throw away the one part of it that
    says *where* inside the analysis the failure happened.
    """
    quoted = str(WINDOWS_ROOT).replace("\\", "\\\\")
    message = f"[Errno 17] File exists: '{quoted}/projects/p1'"

    redacted = redact_workspace(message, WINDOWS_ROOT)

    assert "<workspace>/projects/p1" in redacted


def test_an_oserror_quotes_its_path_the_way_this_platform_does(tmp_path: Path) -> None:
    """The rule, exercised with the exception the pipeline actually records.

    On Windows this is the shape that leaked; on Linux the plain shape is
    the same thing and it has always been redacted.
    """
    root = tmp_path / "ws"
    root.mkdir()
    message = str(OSError(f"cannot create: {root}"))

    redacted = redact_workspace(message, root)

    assert str(root) not in redacted
    assert "<workspace>" in redacted
