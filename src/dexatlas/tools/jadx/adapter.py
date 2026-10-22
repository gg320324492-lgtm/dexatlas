"""JADX backend — human-readable Java decompilation.

JADX owns the *representation*: its output stays JADX's Java, stored verbatim. The
symbol index comes from Androguard instead, because a decompiler's text is the wrong
thing to parse for structure. What this backend contributes is source bodies, and the
fact that a particular class or method could not be decompiled at all.

Two failure modes are recorded rather than raised, because both are normal on obfuscated
input:

- JADX exits non-zero after partially succeeding. Its output directory is usually still
  populated, so :meth:`extract` proceeds and the error is attached to the project.
- A single method fails to decompile and JADX emits a placeholder body. Those are
  reported as *not* decompiled, and the method keeps a Smali fallback path.

JADX writes no log file. Its command line reports failures on the console, and the
placeholder bodies it leaves in the ``.java`` files are the only per-method record of
what went wrong — so that is what this backend reads.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dexatlas.config.settings import Settings
from dexatlas.core.methods import (
    AmbiguousMethodError,
    JavaContext,
    MethodCandidate,
    match_parameter_rank,
    parse_parameter_types,
    simple_class_name,
)
from dexatlas.core.models import ClassKind, ClassRef, ToolError
from dexatlas.core.paths import absolute_path, class_to_relative_path, is_inside
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome, which_or_none

logger = logging.getLogger(__name__)

#: JADX substitutes these when a body could not be reconstructed. The text is useful
#: source, but it is not a decompilation and must never back a "verified" claim.
#:
#: A JADX *warning* is not one of them. JADX writes ``/* JADX WARN: ... */`` above a
#: method it decompiled with a caveat — "type inference failed for r0v2" — and the body
#: behind it is real code. Treating that as a failure marked working methods as
#: unreadable.
_DECOMPILE_FAILED_RE = re.compile(
    r"(?:JADX ERROR"
    r"|Method not decompiled"
    r"|Method could not be decompiled"
    r"|UnsupportedOperationException\(\"Method not decompiled)"
)

#: A static initializer block. JADX writes it as ``static { ... }``, which is not a
#: method signature, so the method pattern never sees it — and the DEX calls that
#: method ``<clinit>``.
_STATIC_INITIALIZER_RE = re.compile(r"^[ \t]*static[ \t]*\{", re.MULTILINE)

_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
_TYPE_RE = re.compile(
    r"^\s*(?:public\s+|final\s+|abstract\s+)*(class|interface|enum)\s+(\w+)", re.MULTILINE
)

#: A class declaration, with the modifiers a decompiler writes in front of it.
#:
#: The file a decompiler writes holds the class it is named after and every
#: nested class with it, and a nested class's methods are not the outer class's
#: methods. Which declaration a method belongs to is therefore not a detail:
#: it is the difference between one class's method and another's.
_CLASS_DECL_RE = re.compile(
    r"^[ \t]*(?:(?:public|protected|private|static|final|abstract|sealed|non-sealed)[ \t]+)*"
    r"(?:class|interface|enum|record)[ \t]+(?P<name>\w+)",
    re.MULTILINE,
)

#: A single-type import: the name a source uses, and the class it names.
_IMPORT_RE = re.compile(
    r"^[ \t]*import[ \t]+(?:static[ \t]+)?(?P<name>[\w.]+)[ \t]*;", re.MULTILINE
)

#: A top-level method signature: modifiers, return type, name, parameters, then ``{``.
#: The return type is optional, because a constructor has none — and a constructor
#: is a method like any other as far as the index is concerned. A span without a
#: return type is a constructor, and that is what tells it apart from a method of
#: the same name: an obfuscated class can have a method called exactly what the
#: class is called.
#: Keywords that introduce a block rather than declare a method are excluded.
_METHOD_START_RE = re.compile(
    r"^[ \t]*(?:@[\w.]+(?:\([^)]*\))?[ \t]*\n[ \t]*)*"
    r"(?:(?:public|protected|private|static|final|synchronized|native|abstract|strictfp)[ \t]+)*"
    r"(?:(?P<return_type>[\w.$<>\[\],? \t]+?)[ \t]+)?"
    r"(?P<name>\w+)[ \t]*\((?P<params>[^)]*)\)[ \t]*"
    r"(?:throws[ \w.,\s]+)?[ \t]*\{",
    re.MULTILINE,
)

_NOT_A_METHOD = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "synchronized",
        "return",
        "new",
        "do",
        "else",
        "try",
        "finally",
        "case",
        "assert",
        "throw",
    }
)


@dataclass(frozen=True, slots=True)
class ClassDecompilation:
    """What JADX made of one class file.

    ``decompiled`` holds the method names JADX produced real Java for, and
    ``failed`` the ones it wrote a placeholder for. The two are different
    facts: a placeholder is a method JADX *tried* and could not reconstruct,
    while a method in neither set is one JADX never wrote at all.

    ``constructors`` holds the names of the classes whose constructor JADX
    wrote. A constructor is kept apart from the methods because it is written
    under the class's own name, and a class can have a method of that name too.
    """

    decompiled: frozenset[str] = frozenset()
    failed: frozenset[str] = frozenset()
    constructors: frozenset[str] = frozenset()
    has_static_initializer: bool = False

    def method_status(self, dex_class_name: str, method_name: str) -> bool | None:
        """Whether JADX decompiled one method of a DEX class.

        ``True`` — JADX produced real Java for it.
        ``False`` — JADX wrote the method but could not decompile it.
        ``None`` — there is no Java for it: JADX wrote no source for the method.

        The DEX spells a constructor ``<init>`` and a class initializer
        ``<clinit>``; Java spells them with the class's own name and a static
        block. The names are translated here rather than in the caller, because
        the translation is JADX's convention.
        """
        if method_name == "<clinit>":
            return True if self.has_static_initializer else None
        if method_name == "<init>":
            key = simple_class_name(dex_class_name)
            if key in self.constructors:
                return True
            return False if key in self.failed else None
        if method_name in self.decompiled:
            return True
        if method_name in self.failed:
            return False
        return None


def source_locator(output_dir: Path, path: Path) -> str:
    """The locator for a file inside JADX's output tree.

    The path is relative to the directory JADX wrote into. An absolute path
    would name the machine that ran the analysis rather than the analysis, and
    a reader on another machine cannot follow it — the same file, at the same
    place inside the tree, is what any run of the same JADX over the same APK
    produces.
    """
    return f"jadx:{path.relative_to(output_dir).as_posix()}"


class JadxBackend(Backend):
    """Wraps the ``jadx`` command-line decompiler."""

    name = "jadx"
    path_env_var = "DEXATLAS_JADX_PATH"
    install_hint = "Install the jadx decompiler: https://github.com/skylot/jadx/releases"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._version: str | None = None
        self._version_probed = False

    def resolve(self) -> Path | None:
        """Locate a runnable jadx launcher.

        The jadx distribution ships one launcher per platform, and the plain ``jadx``
        name in ``bin/`` is the shell script. Pointing at it from Windows yields
        "not a valid Win32 application", so the platform's own launcher is preferred
        when one exists next to the configured path.

        The launcher is returned as an absolute path. It is executed with a working
        directory of its own — the output tree — so a relative one would be looked
        up inside that directory instead of the one the operator configured.
        """
        configured = self._settings.jadx_path
        found = which_or_none([configured], names=("jadx", "jadx.bat", "jadx.exe"))
        if found is None:
            return None
        return absolute_path(self._platform_launcher(found))

    def _platform_launcher(self, found: Path) -> Path:
        """Prefer a launcher this platform can actually execute."""
        if os.name != "nt":
            return found
        for sibling in (found.with_suffix(".bat"), found.with_suffix(".exe")):
            if sibling.is_file():
                return sibling
        # A .bat needs cmd.exe; a bare shell script cannot run on Windows at all.
        if found.suffix.lower() not in {".bat", ".exe", ".cmd"}:
            logger.debug("jadx: %s is not executable on Windows; looking for a .bat", found)
        return found

    def version(self) -> str | None:
        if self._version_probed:
            return self._version
        self._version_probed = True
        executable = self.resolve()
        if executable is None:
            return None
        outcome = self.run(ToolInvocation(argv=[str(executable), "--version"], timeout=60))
        first_line = outcome.stdout.strip().splitlines()
        self._version = first_line[0] if outcome.ok and first_line else None
        return self._version

    # -- decompilation -----------------------------------------------------

    def decompile(self, apk: Path, output_dir: Path, *, timeout: int | None = None) -> ToolOutcome:
        """Run JADX over an APK, writing Java sources into ``output_dir/sources``.

        Every path handed to the decompiler names one place. The output directory
        is both the child's working directory and the argument that tells it where
        to write, and a relative path would be read twice — once against this
        process's directory and once against the child's — so JADX would write
        into a doubly-nested copy of the tree it was told to write into, and the
        index would find nothing there. The APK is made absolute for the same
        reason: it is read relative to the child's working directory, which is
        not this process's directory.
        """
        executable = self.resolve()
        if executable is None:
            return ToolOutcome(
                returncode=-1,
                stdout="",
                stderr="",
                duration_seconds=0.0,
                error=self.missing_error(),
            )

        # One directory, one meaning: the same absolute path is the child's
        # working directory and the argument that names its output.
        target = absolute_path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        return self.run(
            ToolInvocation(
                argv=[
                    str(executable),
                    "--no-res",
                    "--no-debug-info",
                    "--show-bad-code",
                    "--threads-count",
                    "4",
                    "--output-dir",
                    str(target),
                    str(absolute_path(apk)),
                ],
                cwd=target,
                timeout=timeout,
            )
        )

    def extract(
        self,
        apk_sha256: str,
        output_dir: Path,
        outcome: ToolOutcome,
    ) -> tuple[list[ClassRef], ToolError | None]:
        """Index the decompiled ``.java`` files JADX wrote.

        Returns the classes found plus JADX's own error, if it reported one. A non-zero
        exit still yields classes whenever JADX wrote files before failing.
        """
        sources = output_dir / "sources"
        if not sources.is_dir():
            return [], outcome.error

        version = self.version()
        classes: list[ClassRef] = []
        for java_file in sorted(sources.rglob("*.java")):
            text = read_text(java_file)
            if text is None:
                continue
            name = self._class_name(java_file, sources, text)
            if name is None:
                continue
            classes.append(
                ClassRef(
                    name=name,
                    kind=self._class_kind(text),
                    provenance=[self.provenance(apk_sha256, source_locator(output_dir, java_file))],
                    method_count=len(self._method_spans(text)),
                )
            )
        logger.debug("jadx %s: indexed %d classes from %s", version, len(classes), apk_sha256)
        return classes, outcome.error

    # -- source access -----------------------------------------------------

    def class_source_path(self, class_name: str, output_dir: Path) -> Path | None:
        """Map a dotted class name back to JADX's output file.

        The name arrives from an HTTP request or from an analysed APK, so it
        is untrusted input, and it is joined onto the output directory to
        make a path. Every part of it has to be a single path component
        before that happens: a name that is already a path — absolute, with a
        drive letter, with a UNC prefix, with a ``..`` in it — is refused
        rather than normalised, because normalising would quietly change
        which file is read.

        A refused name is not an error. It is the same answer as "there is no
        such class", and the caller cannot tell the two apart.
        """
        sources = output_dir / "sources"
        for relative in _java_candidates(class_name):
            candidate = sources / relative
            if not candidate.is_file():
                continue
            # The name was checked, but the file could still be a link out of
            # the tree. The last check is that the file really is inside it.
            if is_inside(sources, candidate):
                return candidate
        return None

    def read_class_source(self, class_name: str, output_dir: Path) -> str | None:
        path = self.class_source_path(class_name, output_dir)
        return read_text(path) if path is not None else None

    def read_method_source(
        self,
        class_name: str,
        method_name: str,
        output_dir: Path,
        descriptor: str | None = None,
        *,
        constructor: bool | None = None,
    ) -> str | None:
        """Extract one top-level method body by brace matching.

        A descriptor picks one overload out of several. Without one, a name that
        matches more than one method is an ambiguity rather than a choice.
        """
        path = self.class_source_path(class_name, output_dir)
        if path is None:
            return None
        text = read_text(path)
        if text is None:
            return None

        classes = _class_layout(text, path, output_dir)
        context = _java_context(text, classes)
        spans = _scoped_spans(self._method_spans(text), classes, class_name)
        candidates = _candidate_spans(spans, class_name, method_name, constructor)

        if not candidates:
            return None

        if descriptor is None:
            if len(candidates) > 1:
                raise AmbiguousMethodError(
                    class_name, method_name, [_java_candidate(span) for span in candidates]
                )
            return _body_from(text, candidates[0].start)

        ranked = [
            (match_parameter_rank(span.param_types, descriptor, context), span)
            for span in candidates
        ]
        matched = [(rank, span) for rank, span in ranked if rank is not None]
        if not matched:
            # The source does not spell this method's signature, so the right
            # body is not the nearest declaration that happens to share a name.
            return None
        best = min(rank for rank, _ in matched)
        winners = [span for rank, span in matched if rank == best]
        if len(winners) > 1:
            raise AmbiguousMethodError(
                class_name, method_name, [_java_candidate(span) for span in winners]
            )
        return _body_from(text, winners[0].start)

    @staticmethod
    def method_decompiled(source: str) -> bool:
        """Whether a body is real decompilation rather than a JADX placeholder."""
        return _DECOMPILE_FAILED_RE.search(source) is None

    def decompilation_status(self, output_dir: Path) -> dict[str, ClassDecompilation]:
        """What JADX decompiled, per class.

        JADX writes a placeholder body for a method it could not reconstruct,
        and the placeholder is indistinguishable from a real body to anything
        that does not know the marker. This is where the marker is read, so the
        rest of DexAtlas can tell a decompilation from a stub.

        The key is the class the file holds — the top-level one. A nested class
        shares its outer class's file, exactly as it does on disk.
        """
        sources = output_dir / "sources"
        if not sources.is_dir():
            return {}

        status: dict[str, ClassDecompilation] = {}
        for java_file in sorted(sources.rglob("*.java")):
            text = read_text(java_file)
            if text is None:
                continue
            class_name = self._class_name(java_file, sources, text)
            if class_name is None:
                continue

            decompiled: set[str] = set()
            failed: set[str] = set()
            constructors: set[str] = set()
            for span in self._method_spans(text):
                # The method is read on its own — its declaration and its body,
                # and nothing that precedes it. The comments JADX writes above
                # a method belong to the class, not to the method: a warning
                # about type inference is not a failed decompilation.
                body = _body_from(text, span.start)
                if body is None:
                    continue
                # A constructor has no return type. That is what tells it apart
                # from a method of the same name, which an obfuscated class
                # can have.
                if span.return_type is None:
                    if self.method_decompiled(body):
                        constructors.add(span.name)
                    else:
                        failed.add(span.name)
                elif self.method_decompiled(body):
                    decompiled.add(span.name)
                else:
                    failed.add(span.name)

            status[class_name] = ClassDecompilation(
                decompiled=frozenset(decompiled),
                failed=frozenset(failed),
                constructors=frozenset(constructors),
                has_static_initializer=_STATIC_INITIALIZER_RE.search(text) is not None,
            )
        return status

    # -- parsing helpers ---------------------------------------------------

    @staticmethod
    def _class_name(java_file: Path, sources: Path, text: str) -> str | None:
        parts = list(java_file.relative_to(sources).with_suffix("").parts)
        if not parts:
            return None
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            parts = [*package_match.group(1).split("."), parts[-1]]
        return ".".join(parts)

    @staticmethod
    def _class_kind(text: str) -> ClassKind:
        match = _TYPE_RE.search(text)
        if not match:
            return ClassKind.CLASS
        try:
            return ClassKind(match.group(1))
        except ValueError:
            return ClassKind.CLASS

    @staticmethod
    def _method_spans(text: str) -> list[_MethodSpan]:
        """Locate top-level method bodies.

        A candidate is accepted only when its braces balance. Control-flow keywords are
        excluded up front, so ``for (...) {`` never registers as a declaration.
        """
        spans: list[_MethodSpan] = []
        for match in _METHOD_START_RE.finditer(text):
            if match.group("name") in _NOT_A_METHOD:
                continue
            end = _match_brace(text, match.end() - 1)
            if end is not None:
                spans.append(
                    _MethodSpan(
                        name=match.group("name"),
                        start=match.start(),
                        end=end,
                        return_type=match.group("return_type"),
                        param_types=parse_parameter_types(match.group("params")),
                    )
                )
        return spans


class _MethodSpan:
    """A located method declaration: its name, its signature and its offsets.

    The parameter types are what tell two overloads apart, so they are kept:
    the signature line already spells them out, and a method that only knows
    its own name cannot tell ``sign(String)`` from ``sign(String, String)``.

    The return type is ``None`` for a constructor, which is what it has in
    Java as well.
    """

    __slots__ = ("end", "name", "param_types", "return_type", "start")

    def __init__(
        self,
        name: str,
        start: int,
        end: int,
        return_type: str | None = None,
        param_types: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.start = start
        self.end = end
        self.return_type = return_type
        self.param_types = param_types


@dataclass(frozen=True, slots=True)
class _ClassSpan:
    """A class declaration in a decompiled file.

    A decompiler writes a nested class inside the file of the class that holds
    it, so one file holds several classes, and a method belongs to exactly one
    of them.
    """

    name: str
    """The name the source writes."""

    start: int
    """Where the declaration starts."""

    end: int
    """Where the class body ends."""

    parent: int | None
    """The index of the class this one is declared inside, when there is one."""


def _class_spans(text: str) -> list[_ClassSpan]:
    """The class declarations in a file, and where each body ends.

    The nesting is read off the braces: a declaration inside another class's
    body is a nested class, and one that is not is a top-level class.
    """
    spans: list[_ClassSpan] = []
    for match in _CLASS_DECL_RE.finditer(text):
        open_index = text.find("{", match.end())
        if open_index == -1:
            continue
        close_index = _match_brace(text, open_index)
        if close_index is None:
            continue
        parent: int | None = None
        for index, enclosing in enumerate(spans):
            if not enclosing.start < match.start() < enclosing.end:
                continue
            if parent is None or enclosing.start > spans[parent].start:
                parent = index
        spans.append(
            _ClassSpan(
                name=match.group("name"),
                start=match.start(),
                end=close_index,
                parent=parent,
            )
        )
    return spans


def _file_class_name(path: Path, output_dir: Path) -> str:
    """The DEX name of the class a decompiled file holds at the top level.

    The file is named after the class it holds, and the DEX spells a class by
    its path with slashes, so the name of the file is the name of the class.
    """
    try:
        relative = path.relative_to(output_dir / "sources")
    except ValueError:
        relative = path
    return relative.with_suffix("").as_posix()


def _class_layout(text: str, path: Path, output_dir: Path) -> list[tuple[_ClassSpan, str]]:
    """The class declarations in a file, each with the DEX name of the class.

    A nested class is named after the class that holds it, with a ``$``
    between: ``com/example/Outer$Helper``. A file a decompiler wrote for a
    class of a flat name holds exactly that class.
    """
    spans = _class_spans(text)
    file_class = _file_class_name(path, output_dir)
    layout: list[tuple[_ClassSpan, str]] = []
    for span in spans:
        if span.parent is None:
            # The first class in the file is the one the file is named after.
            name = file_class if not layout else f"{file_class}${span.name}"
        else:
            name = f"{layout[span.parent][1]}${span.name}"
        layout.append((span, name))
    return layout


def _java_context(text: str, layout: list[tuple[_ClassSpan, str]]) -> JavaContext:
    """What the file says about the names it uses.

    The imports and the package are how a source says which class a bare name
    means, and the classes the file declares are how it says which class a
    nested name means.
    """
    package_match = _PACKAGE_RE.search(text)
    imports: dict[str, str] = {}
    star_imports: list[str] = []
    for match in _IMPORT_RE.finditer(text):
        name = match.group("name")
        if name.endswith(".*"):
            star_imports.append(name[:-2])
        else:
            imports[name.rpartition(".")[2]] = name
    own = {span.name: dex_name for span, dex_name in layout}
    return JavaContext(
        package=package_match.group(1) if package_match else "",
        imports=imports,
        star_imports=tuple(star_imports),
        own_classes=own,
    )


def _scoped_spans(
    spans: list[_MethodSpan],
    layout: list[tuple[_ClassSpan, str]],
    class_name: str,
) -> list[_MethodSpan]:
    """The declarations that belong to the class the request names.

    A nested class's methods are not the outer class's methods, and a file that
    holds both is read for one class or the other — never for both at once.
    """
    wanted = class_name.replace(".", "/")
    scoped = [span for span in spans if _owning_class(span, layout) == wanted]
    if scoped:
        return scoped
    # The file does not declare the class the request names — a name that is not
    # a class at all, or a decompiler that wrote the class somewhere else.
    # Every declaration in the file is then a candidate.
    return spans


def _owning_class(span: _MethodSpan, layout: list[tuple[_ClassSpan, str]]) -> str | None:
    """The DEX name of the class a declaration belongs to.

    The innermost class whose body holds the declaration: a method of a nested
    class is inside the outer class's body as well, and the inner one is the
    class that owns it.
    """
    owner: str | None = None
    owner_start = -1
    for class_span, dex_name in layout:
        if not class_span.start < span.start < class_span.end:
            continue
        if class_span.start > owner_start:
            owner = dex_name
            owner_start = class_span.start
    return owner


def _candidate_spans(
    spans: list[_MethodSpan],
    class_name: str,
    method_name: str,
    constructor: bool | None,
) -> list[_MethodSpan]:
    """The declarations a request could be about.

    A constructor is written under the class's own name in Java, and an
    obfuscated class can have a method of exactly that name too — so a request
    that does not say which of the two it wants is about both.
    """
    if method_name == "<init>" or constructor is True:
        visible = simple_class_name(class_name)
        want_constructor: bool | None = True
    else:
        visible = method_name
        want_constructor = constructor
    candidates = [span for span in spans if span.name == visible]
    if want_constructor is True:
        return [span for span in candidates if span.return_type is None]
    if want_constructor is False:
        return [span for span in candidates if span.return_type is not None]
    return candidates


def _java_candidate(span: _MethodSpan) -> MethodCandidate:
    """A candidate read out of the decompiled source.

    The descriptor is unknown here: the source says ``sign(String)``, and which
    package ``String`` came from is not something the source says.
    """
    name = "<init>" if span.return_type is None else span.name
    spelling = ", ".join(span.param_types)
    return MethodCandidate(name=name, descriptor=None, signature=f"{span.name}({spelling})")


def _match_brace(text: str, open_index: int) -> int | None:
    """Index of the ``}`` matching the ``{`` at ``open_index``, ignoring string and
    comment content. Returns ``None`` if unbalanced."""
    depth = 0
    index = open_index
    length = len(text)
    while index < length:
        char = text[index]
        if char == "/" and index + 1 < length:
            following = text[index + 1]
            if following == "/":
                index = text.find("\n", index)
                if index == -1:
                    return None
                continue
            if following == "*":
                index = text.find("*/", index + 2)
                if index == -1:
                    return None
                index += 1
                continue
        if char in ('"', "'"):
            index = _skip_literal(text, index, char)
            if index == -1:
                return None
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _skip_literal(text: str, start: int, quote: str) -> int:
    """Index just past the string/char literal beginning at ``start``, or -1."""
    index = start + 1
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        if char == "\n" and quote == "'":
            return -1
        index += 1
    return -1


def _body_from(text: str, start: int) -> str | None:
    open_index = text.find("{", start)
    if open_index == -1:
        return None
    close_index = _match_brace(text, open_index)
    if close_index is None:
        return None
    return text[start : close_index + 1]


def _java_candidates(class_name: str) -> list[Path]:
    """The JADX output files a class name could name.

    A nested or anonymous class shares its outer class's file, so the outer
    name is the second candidate. Both are checked as class names: a name
    whose parts are not single path components yields no candidate at all,
    and the caller then finds no file — which is the right answer for a name
    that was never a class name.
    """
    names = [class_name]
    outer = class_name.partition("$")[0]
    if outer != class_name:
        names.append(outer)

    candidates: list[Path] = []
    for name in names:
        relative = class_to_relative_path(name, ".java")
        if relative is not None:
            candidates.append(relative)
    return candidates


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


__all__ = ["ClassDecompilation", "JadxBackend", "read_text", "source_locator"]
