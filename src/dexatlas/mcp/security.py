"""What the MCP tools may and may not do.

The server is read-only, and that is a property of this module and not a
promise in a docstring:

* **Nothing is written.** The tools open the workspace through a read view,
  which never commits, and the server registers no tool that writes.
* **No file is read that the index did not name.** A path reaches a file only
  by being derived from a class name or a method that the analysis found, and
  the derivation goes through :func:`dexatlas.core.paths.class_to_relative_path`,
  which refuses a name that could climb out of the tree it belongs to.
* **Nothing comes back unbounded.** Every excerpt is cut to a number of lines
  and a number of bytes, and the cut is stated in the response rather than
  left for the reader to guess.
* **Nothing read out of an APK is an instruction.** It is carried in
  :class:`~dexatlas.mcp.schemas.UntrustedText`, which says what it is.
* **No shell runs.** Nothing here starts a process, and nothing a caller says
  reaches a command line.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dexatlas.core.paths import is_inside
from dexatlas.mcp.schemas import (
    MAX_EXCERPT_BYTES,
    MAX_EXCERPT_LINES,
    UntrustedText,
)


def bounded_text(
    text: str,
    *,
    max_lines: int = MAX_EXCERPT_LINES,
    max_bytes: int = MAX_EXCERPT_BYTES,
) -> UntrustedText:
    """Text from an APK, cut to a size, and marked as what it is.

    The cut is stated: a reader who is handed half a method and told
    nothing will draw a conclusion from half of it.
    """
    size = len(text.encode("utf-8"))
    lines = text.splitlines()
    truncated = False

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    kept = "\n".join(lines)
    if len(kept.encode("utf-8")) > max_bytes:
        kept = kept.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        truncated = True

    return UntrustedText(text=kept, truncated=truncated, bytes=size)


def excerpt(
    path: Path,
    root: Path,
    *,
    max_lines: int = MAX_EXCERPT_LINES,
    max_bytes: int = MAX_EXCERPT_BYTES,
) -> UntrustedText:
    """The first lines of a file inside the analysis, and nothing else.

    The path has to be inside ``root``. The callers below derive their
    paths from names the analysis found, and a name that could climb out of
    the tree is refused by the path module before it ever gets here — this
    check is the second lock on the same door, not the first.
    """
    if not is_inside(root, path):
        return bounded_text("", max_lines=max_lines, max_bytes=max_bytes)

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return bounded_text("", max_lines=max_lines, max_bytes=max_bytes)

    return bounded_text(text, max_lines=max_lines, max_bytes=max_bytes)


def source_kind(path: Path) -> Literal["java", "smali"]:
    """Which representation a source file is in.

    The two backends write different things, and a reader who is told which
    one they are looking at does not have to guess from the syntax.
    """
    return "smali" if path.suffix == ".smali" else "java"


__all__ = ["bounded_text", "excerpt", "source_kind"]
