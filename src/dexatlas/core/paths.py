"""Paths that do not name the machine.

Two rules live here, and both exist because a path that reaches a reader has to
describe the analysis rather than the server:

- A class name arrives from an analysed APK or from an HTTP request, so it is
  untrusted input, and turning it into a path without a guard walks straight
  out of the tree it is meant to name. :func:`class_to_relative_path` is that
  guard, and every backend that resolves a class name to a file uses it — one
  rule, so the two backends cannot drift apart.
- A path that names the server's filesystem is replaced by one that names the
  file, so an API response or a report can be read on another machine.

A third rule is about the paths that never reach a reader at all: the ones
handed to another process, and the ones written down and read back later.
:func:`absolute_path` is what settles them.
"""

from __future__ import annotations

from pathlib import Path

#: The longest a path component may be, in bytes. POSIX filesystems cap a
#: component's name at 255 bytes, and Windows caps it at the same number, so a
#: longer one cannot name a file anywhere.
#:
#: The rule is here rather than only in the callers because a name that long
#: is refused by the *filesystem*, not by the shape of the path: the path is
#: built, the file is asked for, and the answer arrives as an error from the
#: operating system instead of as "no such file".
MAX_COMPONENT_BYTES = 255


def absolute_path(path: Path) -> Path:
    """The path, anchored to a directory that cannot move under it.

    A relative path has two readings: "the directory this process is in now",
    and "the directory this process was in when the path was written down". A
    subprocess reads the second one — it resolves a relative argument against
    its *own* working directory — so a relative path handed to one can name
    two different places at once. A path that is written into a database and
    read back later has the same problem: it names whatever directory the
    reader happens to be in.

    ``absolute()`` settles it. A relative path is anchored to the current
    directory, and an absolute path is left exactly as it was. ``resolve()``
    would also follow symlinks, and that rewrites a path the operator chose:
    the configured workspace would stop being the name they gave it, in the
    database and in every message that mentions it, and the subprocess would
    be handed a path the index does not read.
    """
    return path.absolute()


def is_single_component(part: str) -> bool:
    """Whether ``part`` is exactly one path component and nothing more.

    Callers reach this only for non-empty segments:
    :func:`class_to_relative_path` rejects a name with any empty segment before
    it splits into components, so an empty string never arrives here. ``"."``
    and ``".."`` are refused as well — they are the two components that change
    where a path points, and a rule that refused them only because of what
    the caller happened to filter first would be a rule with a hole in it.
    """
    # A separator or drive letter means the caller handed us a path, not a class name.
    if "/" in part or "\\" in part or ":" in part:
        return False
    # The two components that move the path somewhere else.
    if part in {".", ".."}:
        return False
    # NUL and control characters have no place in a class name and truncate paths in
    # the C runtime that Windows ultimately calls.
    if any(ord(char) < 0x20 or char == "\x7f" for char in part):
        return False
    # Wildcards would make a glob match something other than this class.
    if any(char in part for char in "*?[]"):
        return False
    # A component longer than the filesystem allows is not a file name at all.
    return len(part.encode("utf-8", errors="replace")) <= MAX_COMPONENT_BYTES


def class_to_relative_path(class_name: str, suffix: str) -> Path | None:
    """``com.foo.Bar`` → ``com/foo/Bar<suffix>``, or None if the name is not a class name.

    Class names come from an analysed APK or from a request, so they are
    untrusted input. Each part must be a single path component; anything that
    would change the shape of the path — ``..``, an absolute prefix, a
    separator, a drive letter — is rejected rather than normalised, because
    normalising would silently change which file is read.

    A rejected name is not an error: it is the answer "there is no such class",
    which is what a caller asking for a class that does not exist gets too.
    """
    parts = class_name.split(".")
    if not parts or not all(parts):
        return None
    for part in parts:
        if not is_single_component(part):
            return None
    return Path(*parts).with_suffix(suffix)


def display_path(path: Path) -> str:
    """The path as a reader outside the machine should see it.

    The file's name and nothing else. A path into the server's filesystem says
    more about the server than about the analysis, and the analysis is what the
    reader came for. The file itself is identified exactly by its SHA-256,
    which every response carrying a path also carries.
    """
    return path.name


def redact_workspace(message: str, *roots: Path) -> str:
    """Replace the server's workspace paths in a message with a placeholder.

    An error message can quote the path it was handed, and that path is the
    server's. The workspace root is the part that names the machine; what is
    left of the path is a place inside the analysis, and that is worth keeping.

    This lives here rather than in the API because the redaction belongs to
    the *message*, not to one transport: a message recorded on a project is
    read back through the API, through the JSON report and through the
    Markdown report, and redacting it at each of those is three chances to
    forget one. Redacted once, where it is written, it is redacted everywhere.
    """
    for root in roots:
        for candidate in (str(root), str(root.resolve())):
            message = message.replace(candidate, "<workspace>")
    return message


def is_inside(root: Path, candidate: Path) -> bool:
    """Whether the file really is inside the tree, links resolved.

    The name was checked before the path was built, so this is the belt to
    that braces: a link inside an output tree that points somewhere else
    would otherwise be read like a file of the analysis.
    """
    try:
        return candidate.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


__all__ = [
    "absolute_path",
    "class_to_relative_path",
    "display_path",
    "is_inside",
    "is_single_component",
]
