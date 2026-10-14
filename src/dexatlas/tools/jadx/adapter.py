"""JADX backend — human-readable Java decompilation.

JADX owns the *representation*: its output stays JADX's Java, stored verbatim. The
symbol index comes from Androguard instead, because a decompiler's text is the wrong
thing to parse for structure. What this backend contributes is source bodies, and the
fact that a particular class or method could not be decompiled at all.

Two failure modes are recorded rather than raised, because both are normal on obfuscated
input:

- JADX exits non-zero after partially succeeding. Its output directory is usually still
  populated, so :meth:`extract` proceeds and the error is attached to the project.
- A single method fails to decompile and JADX emits a placeholder body. Those are marked
  ``decompiled=False`` and keep a Smali fallback path.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dexatlas.config.settings import Settings
from dexatlas.core.models import ClassKind, ClassRef, ToolError
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome, which_or_none

logger = logging.getLogger(__name__)

#: JADX substitutes these when a body could not be reconstructed. The text is useful
#: source, but it is not a decompilation and must never back a "verified" claim.
_DECOMPILE_FAILED_RE = re.compile(
    r"(?:JADX (?:ERROR|WARN)"
    r"|Method not decompiled"
    r"|Method could not be decompiled"
    r"|UnsupportedOperationException\(\"Method not decompiled)"
)

_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
_TYPE_RE = re.compile(
    r"^\s*(?:public\s+|final\s+|abstract\s+)*(class|interface|enum)\s+(\w+)", re.MULTILINE
)

#: A top-level method signature: modifiers, return type, name, parameters, then ``{``.
#: Keywords that introduce a block rather than declare a method are excluded.
_METHOD_START_RE = re.compile(
    r"^[ \t]*(?:@[\w.]+(?:\([^)]*\))?[ \t]*\n[ \t]*)*"
    r"(?:(?:public|protected|private|static|final|synchronized|native|abstract|strictfp)[ \t]+)*"
    r"(?P<return_type>[\w.$<>\[\],?\s]+?)[ \t]+"
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
        """
        configured = self._settings.jadx_path
        found = which_or_none([configured], names=("jadx", "jadx.bat", "jadx.exe"))
        if found is None:
            return None
        return self._platform_launcher(found)

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
        """Run JADX over an APK, writing Java sources into ``output_dir/sources``."""
        executable = self.resolve()
        if executable is None:
            return ToolOutcome(
                returncode=-1,
                stdout="",
                stderr="",
                duration_seconds=0.0,
                error=self.missing_error(),
            )

        output_dir.mkdir(parents=True, exist_ok=True)
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
                    str(output_dir),
                    str(apk),
                ],
                cwd=output_dir,
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
                    provenance=[self.provenance(apk_sha256, f"jadx:{java_file.as_posix()}")],
                    method_count=len(self._method_spans(text)),
                )
            )
        logger.debug("jadx %s: indexed %d classes from %s", version, len(classes), apk_sha256)
        return classes, outcome.error

    # -- source access -----------------------------------------------------

    def class_source_path(self, class_name: str, output_dir: Path) -> Path | None:
        """Map a dotted class name back to JADX's output file."""
        sources = output_dir / "sources"
        candidate = sources / Path(class_name.replace(".", "/") + ".java")
        if candidate.is_file():
            return candidate
        # Nested and anonymous classes share their outer class's file.
        candidate = sources / Path(class_name.partition("$")[0].replace(".", "/") + ".java")
        return candidate if candidate.is_file() else None

    def read_class_source(self, class_name: str, output_dir: Path) -> str | None:
        path = self.class_source_path(class_name, output_dir)
        return read_text(path) if path is not None else None

    def read_method_source(self, class_name: str, method_name: str, output_dir: Path) -> str | None:
        """Extract one top-level method body by brace matching.

        Deliberately conservative: a body is returned only when the signature and its
        braces are unambiguous. Anything it cannot isolate returns ``None``, which the
        caller surfaces as "no decompiled source" rather than guessing.
        """
        text = self.read_class_source(class_name, output_dir)
        if text is None:
            return None

        for span in self._method_spans(text):
            if span.name != method_name:
                continue
            body = _body_from(text, span.start)
            if body is not None:
                return body
        return None

    @staticmethod
    def method_decompiled(source: str) -> bool:
        """Whether a body is real decompilation rather than a JADX placeholder."""
        return _DECOMPILE_FAILED_RE.search(source) is None

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
                spans.append(_MethodSpan(name=match.group("name"), start=match.start(), end=end))
        return spans


class _MethodSpan:
    """A located method declaration: its name and brace offsets."""

    __slots__ = ("end", "name", "start")

    def __init__(self, name: str, start: int, end: int) -> None:
        self.name = name
        self.start = start
        self.end = end


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


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def summarize_jadx_log(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Parse JADX's per-class error log, so a failure is attributable to a class."""
    log = output_dir / "sources" / "resources" / "log" / "error.log"
    if not log.is_file():
        return {}
    contents = read_text(log)
    if contents is None:
        return {}

    summary: dict[str, list[dict[str, Any]]] = {}
    for line in contents.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        class_name = record.get("class")
        if isinstance(class_name, str):
            summary.setdefault(class_name, []).append(record)
    return summary


__all__ = ["JadxBackend", "read_text", "summarize_jadx_log"]
