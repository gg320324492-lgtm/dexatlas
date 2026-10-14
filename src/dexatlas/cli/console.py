"""Console output that does not crash on a legacy code page.

DexAtlas runs on Windows terminals whose default encoding is a legacy code page — GBK
on many Chinese installations. Printing a ``✓`` or an em dash there raises
``UnicodeEncodeError`` partway through a command, so the CLI appears to crash after it
has already finished the work.

Two layers, because either alone is insufficient: reconfigure the streams to UTF-8 with
a replacing error handler, and fall back to ASCII marks when the terminal still cannot
render a glyph.
"""

from __future__ import annotations

import sys
from typing import Final

from rich.console import Console

#: Status marks used across the CLI.
OK: Final = "✓"
FAIL: Final = "✗"
WARN: Final = "!"
DASH: Final = "—"
ARROW: Final = "→"

#: What to print when the terminal cannot encode the real character.
_ASCII_FALLBACK: Final[dict[str, str]] = {
    OK: "OK",
    FAIL: "X",
    DASH: "-",
    ARROW: "->",
    "…": "...",
    "·": "-",
}


def use_utf8() -> bool:
    """Reconfigure stdout and stderr to UTF-8. Returns whether it took effect.

    ``errors="replace"`` matters: without it, a terminal that genuinely cannot render
    a glyph fails at the same point the bug did, just later.
    """
    ok = True
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            ok = False
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            ok = False
    return ok


def make_console(stderr: bool = False) -> Console:
    """A Rich console, after ensuring the streams can carry the marks we print."""
    use_utf8()
    return Console(stderr=stderr)


def mark(char: str) -> str:
    """Return ``char`` if the stream can encode it, else an ASCII equivalent."""
    stream = sys.stderr if char == WARN else sys.stdout
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        char.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return _ASCII_FALLBACK.get(char, "*")
    return char


__all__ = ["ARROW", "DASH", "FAIL", "OK", "WARN", "make_console", "mark", "use_utf8"]
