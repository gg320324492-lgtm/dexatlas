"""Resolving a locator against the analysis that claims to have produced it.

A locator is a pointer. ``jadx:sources/com/example/demo/Crypto.java#sign`` says
where a reader would look for the thing a record is about; on its own it says
nothing about whether anything is there. A locator that names a file the
analysis never wrote, a class the DEX does not hold or a method the source
does not declare reads exactly like one that does.

This module is what tells the two apart. A resolver is given the workspace of
one analysis and answers, for one locator: is this place inside that analysis,
and is the thing it names really there?

The workspace is the analysis's own testimony about itself. A ``jadx/``
directory in it means JADX ran and wrote there; a locator into a tree that is
not there names something this analysis never produced, and a locator into a
tree that *is* there but names a file that is not names something stale. Those
are different failures, and the resolver says which one it is.

The resolver never computes a workspace path. It is given one, because the
workspace moves: a published run lives in a versioned directory of its own,
and a resolver that derived the path from a project id would look in the wrong
place the moment that changed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from dexatlas.core.methods import descriptor_arguments, dex_class_name

#: The backend that reads the APK's own DEX files.
#:
#: Its locator names a member of the APK rather than a file in the workspace,
#: so it is resolved against the APK's dex files and against the sources the
#: workspace holds of the same classes.
DEX_BACKEND = "androguard"

#: The backends that write an output tree into the workspace, and the name of
#: that directory.
#:
#: The directory name is the contract with the rest of the project: a workspace
#: holds one ``jadx/`` tree and one ``apktool/`` tree, and a locator says which
#: of the two it belongs to. A locator for one backend never resolves in the
#: other's tree.
OUTPUT_BACKENDS: dict[str, str] = {"jadx": "jadx", "apktool": "apktool"}

#: The prefix of a locator that names a backend failure rather than a place.
#:
#: ``jadx:error/not_installed`` says the tool did not complete. There is no
#: file behind it, and there is nothing to resolve: the failure *is* the fact
#: the record is about.
ERROR_PREFIX = "error/"


class LocatorKind(StrEnum):
    """What a locator points at."""

    SOURCE_PATH = "source_path"
    """A path inside a backend's output tree — a file, or a directory of them."""

    SOURCE_MEMBER = "source_member"
    """A method named inside the file at a path in a backend's output tree."""

    DEX_FILE = "dex_file"
    """A dex file of the analysed APK."""

    DEX_CLASS = "dex_class"
    """A class defined in a dex file."""

    DEX_MEMBER = "dex_member"
    """A method or a field of a class in a dex file."""

    DEX_CALL_EDGE = "dex_call_edge"
    """A call edge between two methods in a dex file."""

    DEX_STRING = "dex_string"
    """A string constant in a dex file."""

    TOOL_ERROR = "tool_error"
    """A backend failure. It names no place, and needs none."""


class ResolutionReason(StrEnum):
    """Why a locator did or did not resolve."""

    RESOLVED = "resolved"
    """The place is inside this analysis, and so is what it names."""

    TOOL_ERROR = "tool-error"
    """The locator names a backend failure. The failure is the fact."""

    MALFORMED = "malformed"
    """The locator is not a locator this project reads."""

    UNKNOWN_BACKEND = "unknown-backend"
    """The locator names a backend that did not take part in the analysis."""

    UNSAFE_PATH = "unsafe-path"
    """The locator names a path that climbs out of the tree it belongs to."""

    BACKEND_ABSENT = "backend-absent"
    """The backend wrote no tree into this analysis, so it named nothing here."""

    MISSING_PLACE = "missing-place"
    """The place the locator names is not in this analysis."""

    MISSING_MEMBER = "missing-member"
    """The place is there, and the thing the locator names is not."""

    UNKNOWN_DEX = "unknown-dex"
    """The locator names a dex file the analysed APK does not have."""


class InvalidLocatorError(ValueError):
    """The locator is not a locator.

    Raised by :func:`parse_locator`, which is the one place that decides what
    the shape of a locator is. An unfamiliar locator is not one to guess at.
    """

    def __init__(self, message: str, reason: ResolutionReason = ResolutionReason.MALFORMED) -> None:
        super().__init__(message)
        self.reason = reason
        """Why the locator was refused."""


@dataclass(frozen=True)
class ParsedLocator:
    """A locator split into the tool that wrote it, the place it names and the fragment."""

    tool: str
    """The backend that produced the locator."""

    place: str
    """What the locator points at: a path in a backend's tree, or a dex file."""

    fragment: str | None
    """What it points at inside the place, when it says."""

    kind: LocatorKind
    """What the place and the fragment are."""


@dataclass(frozen=True)
class Resolution:
    """What one analysis says about one locator."""

    ok: bool
    """Whether the locator resolves inside the analysis."""

    reason: ResolutionReason
    """Why it did or did not."""

    detail: str
    """A sentence a reader can act on."""

    path: Path | None = None
    """Where it resolved to, when it resolved to a file."""


def parse_locator(locator: str) -> ParsedLocator:
    """Split a locator into the tool, the place and the fragment.

    The shape is ``<tool>:<place>`` with an optional ``#<fragment>`` after the
    place. What the place and the fragment *are* depends on the tool: for a
    backend that writes an output tree they are a path inside that tree and a
    member named in the file at that path; for the DEX reader they are a dex
    file of the APK and a symbol in it.
    """
    tool, separator, rest = locator.partition(":")
    if not separator or not tool:
        raise InvalidLocatorError(f"{locator!r} has no tool in front of its place")
    if tool not in OUTPUT_BACKENDS and tool != DEX_BACKEND:
        raise InvalidLocatorError(
            f"{tool!r} is not a backend this project reads locators from",
            ResolutionReason.UNKNOWN_BACKEND,
        )
    if rest.startswith(ERROR_PREFIX):
        return ParsedLocator(tool, rest, None, LocatorKind.TOOL_ERROR)
    if tool == DEX_BACKEND:
        return _parse_dex_locator(locator, tool, rest)
    return _parse_source_locator(locator, tool, rest)


def _parse_source_locator(locator: str, tool: str, rest: str) -> ParsedLocator:
    place, separator, fragment = rest.partition("#")
    if not _is_a_safe_relative_path(place):
        raise InvalidLocatorError(
            f"{locator!r} names {place!r}, which is not a relative path inside the {tool} tree"
        )
    if not separator:
        return ParsedLocator(tool, place, None, LocatorKind.SOURCE_PATH)
    if not fragment:
        raise InvalidLocatorError(f"{locator!r} ends in a separator with nothing after it")
    return ParsedLocator(tool, place, fragment, LocatorKind.SOURCE_MEMBER)


def _parse_dex_locator(locator: str, tool: str, rest: str) -> ParsedLocator:
    place, separator, fragment = rest.partition("#")
    if not place:
        raise InvalidLocatorError(f"{locator!r} names no dex file")
    if not separator:
        return ParsedLocator(tool, place, None, LocatorKind.DEX_FILE)
    if not fragment:
        raise InvalidLocatorError(f"{locator!r} ends in a separator with nothing after it")
    if "->" in fragment:
        return ParsedLocator(tool, place, fragment, LocatorKind.DEX_CALL_EDGE)
    if fragment.startswith("str/"):
        return ParsedLocator(tool, place, fragment, LocatorKind.DEX_STRING)
    if "#" in fragment or "(" in fragment:
        return ParsedLocator(tool, place, fragment, LocatorKind.DEX_MEMBER)
    return ParsedLocator(tool, place, fragment, LocatorKind.DEX_CLASS)


_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def _is_a_safe_relative_path(path: str) -> bool:
    """Whether a path stays inside the tree it is relative to.

    A locator points into the analysis, and the analysis is a directory. A
    path that climbs out of it names something outside the analysis, and an
    absolute path names a machine rather than an analysis. Neither is a
    locator this project can resolve, and both are refused before they are
    ever joined to a directory.
    """
    if not path or path != path.strip():
        return False
    if "\\" in path or "\x00" in path:
        return False
    if _WINDOWS_DRIVE.match(path):
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute():
        return False
    return ".." not in pure.parts


class LocatorResolver:
    """Answers whether one locator resolves inside one analysis.

    The resolver is given the workspace of the analysis and the names of the
    dex files of the analysed APK. The workspace is where the backends wrote
    what they read, so it is also what says which of them ran.
    """

    def __init__(self, workspace_root: Path, *, dex_files: Sequence[str] = ()) -> None:
        self._root = Path(workspace_root)
        self._dex_files = tuple(dex_files)

    @property
    def workspace_root(self) -> Path:
        """The workspace this resolver answers for."""
        return self._root

    def resolve(self, locator: str) -> Resolution:
        """Resolve one locator against this analysis.

        A locator that cannot even be read is reported as such rather than
        raised: the caller is asking about a locator, not parsing one.
        """
        try:
            parsed = parse_locator(locator)
        except InvalidLocatorError as exc:
            return Resolution(False, exc.reason, str(exc))
        if parsed.kind is LocatorKind.TOOL_ERROR:
            return Resolution(
                True,
                ResolutionReason.TOOL_ERROR,
                f"{parsed.tool} did not complete, and that failure is the fact",
            )
        if parsed.kind in _DEX_KINDS:
            return self._resolve_dex(parsed)
        return self._resolve_source(parsed)

    # -- the output trees ---------------------------------------------------

    def _resolve_source(self, parsed: ParsedLocator) -> Resolution:
        tree = self._root / OUTPUT_BACKENDS[parsed.tool]
        if not tree.is_dir():
            return Resolution(
                False,
                ResolutionReason.BACKEND_ABSENT,
                f"this analysis holds no {parsed.tool} tree, so it named nothing here",
            )
        resolved = (tree / parsed.place).resolve()
        if not resolved.is_relative_to(tree.resolve()):
            return Resolution(
                False,
                ResolutionReason.UNSAFE_PATH,
                f"{parsed.place!r} is outside the {parsed.tool} tree",
            )
        if not resolved.exists():
            return Resolution(
                False,
                ResolutionReason.MISSING_PLACE,
                f"{parsed.place!r} is not in the {parsed.tool} tree of this analysis",
            )
        if parsed.kind is LocatorKind.SOURCE_MEMBER:
            fragment = parsed.fragment or ""
            if not _member_in_source(resolved, fragment):
                return Resolution(
                    False,
                    ResolutionReason.MISSING_MEMBER,
                    f"{fragment!r} is not declared in {parsed.place!r}",
                )
        return Resolution(True, ResolutionReason.RESOLVED, str(resolved), resolved)

    # -- the dex files ------------------------------------------------------

    def _resolve_dex(self, parsed: ParsedLocator) -> Resolution:
        if self._dex_files and parsed.place not in self._dex_files:
            return Resolution(
                False,
                ResolutionReason.UNKNOWN_DEX,
                f"{parsed.place!r} is not a dex file of the analysed APK",
            )
        fragment = parsed.fragment or ""
        if parsed.kind is LocatorKind.DEX_CLASS:
            return self._resolve_dex_class(parsed.place, fragment)
        if parsed.kind is LocatorKind.DEX_MEMBER:
            return self._resolve_dex_member(parsed.place, fragment)
        if parsed.kind is LocatorKind.DEX_CALL_EDGE:
            return self._resolve_dex_call_edge(parsed.place, fragment)
        return Resolution(
            True,
            ResolutionReason.RESOLVED,
            f"{parsed.place} is a dex file of this analysis",
        )

    def _resolve_dex_class(self, dex_file: str, class_name: str) -> Resolution:
        if not self._class_in_analysis(class_name):
            return Resolution(
                False,
                ResolutionReason.MISSING_MEMBER,
                f"{class_name} is not in this analysis",
            )
        return Resolution(True, ResolutionReason.RESOLVED, f"{class_name} is in {dex_file}")

    def _resolve_dex_member(self, dex_file: str, fragment: str) -> Resolution:
        class_name, name, descriptor = _split_member(fragment)
        if class_name is None:
            return Resolution(
                False,
                ResolutionReason.MALFORMED,
                f"{fragment!r} names no class to hold a member",
            )
        if not self._class_in_analysis(class_name):
            return Resolution(
                False,
                ResolutionReason.MISSING_MEMBER,
                f"{class_name} is not in this analysis",
            )
        declared = self._member_in_class(class_name, name, descriptor)
        if declared is False:
            return Resolution(
                False,
                ResolutionReason.MISSING_MEMBER,
                f"{name} is not declared in {class_name}",
            )
        return Resolution(True, ResolutionReason.RESOLVED, f"{name} is in {class_name}")

    def _resolve_dex_call_edge(self, dex_file: str, fragment: str) -> Resolution:
        caller, _, callee = fragment.partition("->")
        for side, text in (("caller", caller), ("callee", callee)):
            class_name, name, descriptor = _split_member(text)
            if class_name is None:
                return Resolution(
                    False,
                    ResolutionReason.MALFORMED,
                    f"the {side} of {fragment!r} names no class",
                )
            if not self._class_in_analysis(class_name):
                return Resolution(
                    False,
                    ResolutionReason.MISSING_MEMBER,
                    f"{class_name} is not in this analysis",
                )
            if self._member_in_class(class_name, name, descriptor) is False:
                return Resolution(
                    False,
                    ResolutionReason.MISSING_MEMBER,
                    f"{name} is not declared in {class_name}",
                )
        return Resolution(
            True,
            ResolutionReason.RESOLVED,
            "the call edge is between two members of this analysis",
        )

    def _class_in_analysis(self, class_name: str) -> bool:
        """Whether the analysis holds this class.

        A class is in the analysis when the sources of the analysis hold it.
        When the analysis decoded the APK into smali — which is what Apktool
        does — the class is there as a file, and a class that is not there is
        not in the analysis. When the analysis holds no smali at all, the
        question cannot be asked, and a question that cannot be asked refutes
        nothing.
        """
        if self._smali_file(class_name) is not None:
            return True
        return not self._smali_trees()

    def _member_in_class(self, class_name: str, name: str, descriptor: str | None) -> bool | None:
        """Whether the class declares the member. ``None`` when it cannot be told."""
        smali = self._smali_file(class_name)
        if smali is None:
            return None
        return _smali_declares(_read_text(smali), name, descriptor)

    def _smali_file(self, class_name: str) -> Path | None:
        """The smali file of a class, in whichever smali tree holds it."""
        relative = f"{dex_class_name(class_name)}.smali"
        for tree in self._smali_trees():
            candidate = tree / relative
            if candidate.is_file():
                return candidate
        return None

    def _smali_trees(self) -> list[Path]:
        """The smali trees of the analysis, in a stable order.

        Apktool writes ``smali/`` for the first dex and ``smali_classes2/``
        and onwards for the rest, and a class defined in two dex files is in
        both. The trees are sorted so that a class is found in the same one
        every time.
        """
        apktool = self._root / OUTPUT_BACKENDS["apktool"]
        if not apktool.is_dir():
            return []
        return sorted(path for path in apktool.glob("smali*") if path.is_dir())


_DEX_KINDS = frozenset(
    {
        LocatorKind.DEX_FILE,
        LocatorKind.DEX_CLASS,
        LocatorKind.DEX_MEMBER,
        LocatorKind.DEX_CALL_EDGE,
        LocatorKind.DEX_STRING,
    }
)


def _split_member(fragment: str) -> tuple[str | None, str, str | None]:
    """Split a member fragment into the class that holds it, its name and its descriptor.

    The fragment is one of the shapes the DEX reader writes: ``Class#member``,
    ``Class.method(Ljava/lang/String;)V`` or a field name. The first names
    the class twice, once for the class and once inside the member.
    """
    if "#" in fragment:
        class_name, _, member = fragment.partition("#")
        inner_class, name, descriptor = _split_qualified(member)
        return (class_name or inner_class), name, descriptor
    return _split_qualified(fragment)


def _split_qualified(text: str) -> tuple[str | None, str, str | None]:
    """Split ``com.example.Foo.sign(Ljava/lang/String;)V`` into its parts."""
    open_paren = text.find("(")
    head = text if open_paren == -1 else text[:open_paren]
    descriptor = None if open_paren == -1 else text[open_paren:]
    name = head.rpartition(".")[2]
    class_name = head[: len(head) - len(name)].rstrip(".")
    return (class_name or None), name, descriptor


# -- what a file declares ---------------------------------------------------


def _member_in_source(path: Path, fragment: str) -> bool:
    """Whether the file at ``path`` declares the member the fragment names."""
    text = _read_text(path)
    suffix = path.suffix.lower()
    if suffix == ".smali":
        name, descriptor = _split_name_and_descriptor(fragment)
        return _smali_declares(text, name, descriptor)
    if suffix == ".java":
        name, descriptor = _split_name_and_descriptor(fragment)
        return _java_declares(text, name, descriptor)
    if suffix == ".xml":
        return _xml_declares(text, fragment)
    return False


def _split_name_and_descriptor(fragment: str) -> tuple[str, str | None]:
    """Split a method fragment into the name and the descriptor it carries."""
    open_paren = fragment.find("(")
    if open_paren == -1:
        return fragment, None
    return fragment[:open_paren], fragment[open_paren:]


_SMALI_METHOD = re.compile(r"^\.method\b.*?([\w$<>]+)\(([^)]*)\)(\S+)", re.MULTILINE)
_SMALI_FIELD = re.compile(r"^\.field\b.*?([\w$<>]+):(\S+)", re.MULTILINE)


def _smali_declares(text: str, name: str, descriptor: str | None) -> bool:
    """Whether a smali file declares a method or a field under that name.

    Smali spells the method the way the DEX does — ``sign(args)return`` — so a
    descriptor can be compared with it exactly. Two overloads share a name and
    differ in their arguments, and only the descriptor tells them apart.
    """
    for match in _SMALI_METHOD.finditer(text):
        if match.group(1) != name:
            continue
        if descriptor is None:
            return True
        arguments = "".join(match.group(2).split())
        if f"({arguments}){match.group(3)}" == descriptor:
            return True
    return any(match.group(1) == name for match in _SMALI_FIELD.finditer(text))


_JAVA_MODIFIERS = frozenset(
    {
        "public",
        "private",
        "protected",
        "static",
        "final",
        "abstract",
        "synchronized",
        "native",
        "default",
        "strictfp",
        "transient",
        "volatile",
    }
)

_JAVA_KEYWORDS = frozenset(
    {
        "return",
        "new",
        "throw",
        "if",
        "while",
        "for",
        "switch",
        "catch",
        "else",
        "do",
        "case",
        "assert",
        "yield",
        "instanceof",
    }
)

_JAVA_PRIMITIVES = frozenset(
    {"void", "int", "long", "short", "byte", "char", "float", "double", "boolean", "var"}
)


def _java_declares(text: str, name: str, descriptor: str | None) -> bool:
    """Whether a Java source declares a method under that name.

    A descriptor narrows the answer: two overloads share a name, and the
    descriptor says which one. The source does not spell the descriptor, so
    the narrowing is by the number of arguments — which is what tells the
    overloads apart in the source the reader is sent to.
    """
    declarations = _java_declarations(text, name)
    if not declarations:
        return False
    if descriptor is None:
        return True
    arguments = descriptor_arguments(descriptor)
    if arguments is None:
        return True
    return len(arguments) in declarations


def _java_declarations(text: str, name: str) -> list[int]:
    """The number of arguments of each declaration of ``name`` in a Java source.

    A call and a declaration share a shape — ``name(`` — so the text in front
    of the name decides which it is. A declaration has a type in front of it;
    a call does not. ``return sign(key)`` has the word ``return`` in front of
    the name and is a call; ``public String sign(String key)`` has a type and
    is a declaration.
    """
    pattern = re.compile(rf"(?<![\w.$]){re.escape(name)}\s*\((?P<arguments>[^()]*)\)")
    counts: list[int] = []
    for line in _without_java_comments(text).splitlines():
        for match in pattern.finditer(line):
            words = line[: match.start()].split()
            while words and words[-1] in _JAVA_MODIFIERS:
                words.pop()
            if not words:
                continue
            head = words[-1]
            if head in _JAVA_KEYWORDS:
                continue
            if not (
                head in _JAVA_PRIMITIVES or head.endswith("[]") or "<" in head or head[:1].isupper()
            ):
                continue
            counts.append(_argument_count(match.group("arguments")))
    return counts


def _argument_count(arguments: str) -> int:
    """How many arguments a parameter list holds.

    A generic type carries commas of its own — ``Map<String, Integer>`` — so
    only the commas at the outermost level are counted.
    """
    if not arguments.strip():
        return 0
    depth = 0
    count = 1
    for character in arguments:
        if character in "<([":
            depth += 1
        elif character in ">)]":
            depth -= 1
        elif character == "," and depth == 0:
            count += 1
    return count


def _without_java_comments(text: str) -> str:
    """The source with its comments taken out, so a commented-out method is not one."""
    without_blocks = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", without_blocks)


def _xml_declares(text: str, fragment: str) -> bool:
    """Whether an XML file holds the element the fragment names.

    The fragment is the path of an element inside the document — ``/application``
    for the manifest's application element — so the element it ends in is the
    one to look for.
    """
    element = fragment.rstrip("/").rpartition("/")[2]
    if not element:
        return False
    return re.search(rf"<{re.escape(element)}[\s/>]", text) is not None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


__all__ = [
    "DEX_BACKEND",
    "ERROR_PREFIX",
    "OUTPUT_BACKENDS",
    "InvalidLocatorError",
    "LocatorKind",
    "LocatorResolver",
    "ParsedLocator",
    "Resolution",
    "ResolutionReason",
    "parse_locator",
]
