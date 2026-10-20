"""Androguard backend — classes, methods, fields and cross-references.

This is the *index*. JADX gives readable Java; Apktool gives the manifest and Smali;
Androguard gives the authoritative symbol graph, because parsing DEX is what it does
and a decompiler's text output is the wrong source for structure.

Cross-references are recovered by walking bytecode: Androguard 4.x removed the xref
cache, so a call edge is found by scanning each method's instructions for an
invoke-form opcode and reading the target out of its last operand.

Androguard runs in-process rather than as a subprocess — it is a Python library, so
there is nothing to shell out to. That is the one exception to the subprocess rule, and
it is why every step below is wrapped: a malformed DEX raises inside Androguard, and
that must still land as a recorded :class:`ToolError` rather than kill the run.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    FieldRef,
    InvocationKind,
    MethodRef,
    MethodReference,
    StringConstant,
    ToolError,
    ToolErrorCode,
    canonical_descriptor,
)
from dexatlas.tools.base import Backend

if TYPE_CHECKING:  # pragma: no cover
    from androguard.core.dex import DEX

logger = logging.getLogger(__name__)

#: Max methods walked per APK. Obfuscated APKs carry hundreds of thousands; an
#: unbounded walk is a denial of service against ourselves.
DEFAULT_METHOD_LIMIT = 200_000
DEFAULT_STRING_LIMIT = 50_000
DEFAULT_INSTRUCTION_LIMIT = 5_000_000

#: The Dalvik invocation opcodes, and the kind of call each one records. The
#: target of an invoke opcode is its final operand, and the opcode's own name
#: says how the call is made: a static call and a virtual call are different
#: opcodes, and the edge is the only place that difference shows.
#:
#: The ``/range`` variants take their arguments in a register range instead of
#: in the instruction, and are the same kind of call.
INVOKE_KINDS: dict[str, InvocationKind] = {
    "invoke-virtual": InvocationKind.VIRTUAL,
    "invoke-super": InvocationKind.SUPER,
    "invoke-direct": InvocationKind.DIRECT,
    "invoke-static": InvocationKind.STATIC,
    "invoke-interface": InvocationKind.INTERFACE,
    "invoke-virtual/range": InvocationKind.VIRTUAL,
    "invoke-super/range": InvocationKind.SUPER,
    "invoke-direct/range": InvocationKind.DIRECT,
    "invoke-static/range": InvocationKind.STATIC,
    "invoke-interface/range": InvocationKind.INTERFACE,
}

#: Opcodes that reference a method. The target is the final operand.
INVOKE_OPCODES = frozenset(INVOKE_KINDS)

#: Opcodes that load a string constant. ``const-string/jumbo`` is the same
#: instruction with a 32-bit pool index, for a pool larger than 65535 entries.
CONST_STRING_OPCODES = frozenset({"const-string", "const-string/jumbo"})


def androguard_available() -> bool:
    return importlib.util.find_spec("androguard") is not None


def _to_dotted(name: str) -> str:
    """``Lcom/foo/Bar;`` → ``com.foo.Bar``. DexAtlas stores dotted names throughout."""
    return name.lstrip("L").rstrip(";").replace("/", ".")


@contextmanager
def _quiet_androguard() -> Iterator[None]:
    """Silence Androguard's loguru output.

    On a large APK it emits thousands of parse-trace lines at DEBUG, which buries the
    CLI's own output. Suppressed here rather than configured globally, because the
    library may legitimately be used at debug level elsewhere in the process.
    """
    try:
        from loguru import logger as loguru_logger
    except ImportError:
        yield
        return

    previous = os.environ.get("LOGURU_LEVEL")
    os.environ["LOGURU_LEVEL"] = "ERROR"
    loguru_logger.remove()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("LOGURU_LEVEL", None)
        else:
            os.environ["LOGURU_LEVEL"] = previous


class AndroguardBackend(Backend):
    """Reads DEX metadata via the ``androguard`` library."""

    name = "androguard"
    path_env_var = ""
    install_hint = "Install the analysis extra: uv sync --extra analysis"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def resolve(self) -> Path | None:
        """No executable to locate: this backend is a library, so its installed package
        is what "being present" means."""
        if not androguard_available():
            return None
        import androguard

        location = getattr(androguard, "__file__", None)
        return Path(location) if location else Path("androguard")

    def version(self) -> str | None:
        if not androguard_available():
            return None
        from importlib.metadata import PackageNotFoundError, version

        try:
            return f"androguard {version('androguard')}"
        except PackageNotFoundError:  # pragma: no cover - installed without metadata
            return "androguard"

    # -- extraction --------------------------------------------------------

    def extract(
        self,
        apk: Path,
        apk_sha256: str,
        *,
        method_limit: int = DEFAULT_METHOD_LIMIT,
        string_limit: int = DEFAULT_STRING_LIMIT,
        instruction_limit: int = DEFAULT_INSTRUCTION_LIMIT,
    ) -> tuple[
        list[ClassRef],
        list[MethodRef],
        list[FieldRef],
        list[MethodReference],
        list[StringConstant],
        ToolError | None,
    ]:
        """Walk the APK's DEX files and build the symbol index.

        Returns ``(classes, methods, fields, references, strings, error)``. On failure
        the error is populated and whatever was indexed so far is returned — never an
        exception.
        """
        if not androguard_available():
            return [], [], [], [], [], self.missing_error()

        try:
            from androguard.core.apk import APK
            from androguard.core.dex import DEX
        except ImportError as exc:
            return (
                [],
                [],
                [],
                [],
                [],
                ToolError(
                    tool=self.name,
                    code=ToolErrorCode.UNSUPPORTED,
                    message=f"androguard could not be imported: {exc}",
                    detail="Install the analysis extra: uv sync --extra analysis",
                ),
            )

        classes: list[ClassRef] = []
        methods: list[MethodRef] = []
        fields: list[FieldRef] = []
        references: list[MethodReference] = []
        strings: list[StringConstant] = []
        error: ToolError | None = None
        dex_count = 0

        try:
            with _quiet_androguard():
                apk_obj = APK(str(apk))
                # Androguard returns filters here, not sequences.
                names = list(apk_obj.get_dex_names())
                blobs = list(apk_obj.get_all_dex())
                dex_count = len(blobs)

            for index, blob in enumerate(blobs):
                dex_name = names[index] if index < len(names) else f"classes{index + 1}.dex"
                locator = f"androguard:{dex_name}"
                try:
                    dex = DEX(blob)
                except Exception as exc:
                    logger.warning("androguard: %s could not be parsed: %s", dex_name, exc)
                    error = error or ToolError(
                        tool=self.name,
                        code=ToolErrorCode.PARSE_ERROR,
                        message=f"androguard could not parse {dex_name}",
                        detail=f"{type(exc).__name__}: {exc}"[:2000],
                    )
                    continue

                try:
                    literal_sites = self._index_dex(
                        dex,
                        apk_sha256=apk_sha256,
                        dex_name=dex_name,
                        classes=classes,
                        methods=methods,
                        fields=fields,
                        references=references,
                        method_limit=method_limit,
                        instruction_limit=instruction_limit,
                    )
                    strings.extend(
                        self._index_strings(dex, apk_sha256, locator, string_limit, literal_sites)
                    )
                except Exception as exc:
                    logger.warning("androguard: indexing %s failed: %s", dex_name, exc)
                    error = error or ToolError(
                        tool=self.name,
                        code=ToolErrorCode.PARSE_ERROR,
                        message=f"androguard could not fully index {dex_name}",
                        detail=f"{type(exc).__name__}: {exc}"[:2000],
                    )
        except Exception as exc:
            logger.warning("androguard: analysis of %s failed: %s", apk.name, exc)
            error = error or ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"androguard could not fully parse {apk.name}",
                detail=f"{type(exc).__name__}: {exc}"[:2000],
            )

        return classes, methods, fields, references, strings, error or _no_dex_error(apk, dex_count)

    def _index_dex(
        self,
        dex: DEX,
        *,
        apk_sha256: str,
        dex_name: str,
        classes: list[ClassRef],
        methods: list[MethodRef],
        fields: list[FieldRef],
        references: list[MethodReference],
        method_limit: int,
        instruction_limit: int,
    ) -> dict[str, list[tuple[str, str]]]:
        """Index one DEX file, and report where its string constants are used.

        Returns the use sites of the string constants: a map from a constant to
        the ``(class, method)`` pairs whose bytecode loads it. A constant used
        in two methods has two entries, because each of them is a place in the
        code that a reader can be sent to.
        """
        locator_base = f"androguard:{dex_name}"
        instructions_seen = 0
        literal_sites: dict[str, list[tuple[str, str]]] = {}

        for cls in dex.get_classes():
            class_name = _to_dotted(cls.get_name())
            class_locator = f"{locator_base}#{class_name}"
            superclass = cls.get_superclassname()
            class_methods = cls.get_methods()

            classes.append(
                ClassRef(
                    name=class_name,
                    kind=_class_kind(cls),
                    superclass=_to_dotted(superclass) if superclass else None,
                    interfaces=[_to_dotted(i) for i in cls.get_interfaces()],
                    access_flags=sorted(cls.get_access_flags_string().split()),
                    # What this dex file holds, not what the class holds: a class
                    # split across two dex files is seen partly by each. The
                    # storage layer counts the class's real total from the rows
                    # it wrote.
                    method_count=len(class_methods),
                    field_count=len(cls.get_fields()),
                    provenance=[self.provenance(apk_sha256, class_locator)],
                )
            )

            for field in cls.get_fields():
                fields.append(
                    FieldRef(
                        class_name=class_name,
                        name=field.get_name(),
                        descriptor=field.get_descriptor(),
                        access_flags=sorted(field.get_access_flags_string().split()),
                        provenance=[
                            self.provenance(apk_sha256, f"{class_locator}#{field.get_name()}")
                        ],
                    )
                )

            if len(methods) >= method_limit:
                logger.warning(
                    "androguard: method limit %d reached on %s; index is truncated",
                    method_limit,
                    dex_name,
                )
                return literal_sites

            for method in class_methods:
                # Androguard renders a descriptor for human reading, with a space
                # after every argument separator. Canonicalise it here, where the
                # descriptor enters DexAtlas, so that the method table and the
                # cross-reference table spell every id the same way.
                descriptor = canonical_descriptor(method.get_descriptor())
                qualified = f"{class_name}.{method.get_name()}{descriptor}"
                methods.append(
                    MethodRef(
                        class_name=class_name,
                        name=method.get_name(),
                        descriptor=descriptor,
                        access_flags=sorted(method.get_access_flags_string().split()),
                        # Whether a method was decompiled is the decompiler's
                        # answer, not this backend's: Androguard reads the DEX,
                        # and a method with a code item is not the same thing as
                        # a method JADX turned into Java. The pipeline sets the
                        # flag once JADX has run.
                        provenance=[self.provenance(apk_sha256, f"{class_locator}#{qualified}")],
                    )
                )

                if instructions_seen >= instruction_limit:
                    logger.warning(
                        "androguard: instruction limit %d reached; xref index is truncated",
                        instruction_limit,
                    )
                    return literal_sites
                instructions_seen, calls, literals = self._scan(method, instructions_seen)
                for callee, kind in calls:
                    references.append(
                        MethodReference(
                            caller=qualified,
                            callee=callee,
                            kind=kind,
                            provenance=[
                                self.provenance(apk_sha256, f"{locator_base}#{qualified}->{callee}")
                            ],
                        )
                    )
                for literal in literals:
                    literal_sites.setdefault(literal, []).append((class_name, method.get_name()))

        return literal_sites

    def _scan(
        self, method: Any, instructions_seen: int
    ) -> tuple[int, list[tuple[str, InvocationKind]], list[str]]:
        """The calls and the string constants in ``method``'s bytecode.

        Both come out of the same walk. A call is the final operand of an
        invoke opcode, and it arrives as a Dalvik reference such as
        ``Ljava/io/PrintStream;->println(Ljava/lang/String;)V``; the opcode's
        own name says how the call is made. A string constant is the operand
        of a const-string opcode. The walk was already happening for the call
        edges, so the constants cost one set lookup per instruction.
        """
        calls: list[tuple[str, InvocationKind]] = []
        literals: list[str] = []
        if not method.get_code():
            return instructions_seen, calls, literals

        try:
            for instruction in method.get_instructions():
                instructions_seen += 1
                name = instruction.get_name()
                if name in INVOKE_KINDS:
                    target = instruction.get_output().rsplit(", ", 1)[-1].strip()
                    qualified = _parse_dalvik_reference(target)
                    if qualified is not None:
                        calls.append((qualified, INVOKE_KINDS[name]))
                elif name in CONST_STRING_OPCODES:
                    value = _string_operand(instruction)
                    if value:
                        literals.append(value)
        except Exception as exc:
            logger.debug("androguard: decoding %s failed: %s", method.get_name(), exc)
        # A method that loads the same constant twice is still one place, so
        # the constant is one entry.
        return instructions_seen, calls, list(dict.fromkeys(literals))

    def _index_strings(
        self,
        dex: DEX,
        apk_sha256: str,
        locator: str,
        limit: int,
        sites: dict[str, list[tuple[str, str]]],
    ) -> list[StringConstant]:
        """The DEX string pool, and where each of its entries is used.

        The pool is every string the DEX holds. A use site is the method whose
        bytecode loads one of them, and it is what turns a constant into
        something a reader can be sent to: a hardcoded key that no method is
        known to use is a value; one that a method uses is a place.

        A constant used in two methods is two rows, one per method, because a
        row has to point at one place. A pool entry that no instruction loads —
        a type descriptor, a member name — has no place to point at, and its
        row carries no location.
        """
        constants: list[StringConstant] = []
        try:
            for value in dex.get_strings():
                if not isinstance(value, str) or not value:
                    continue
                uses = sites.get(value, [])
                if not uses:
                    constants.append(
                        StringConstant(
                            value=value,
                            provenance=[self.provenance(apk_sha256, f"{locator}#str/{value[:64]}")],
                        )
                    )
                else:
                    for class_name, method_name in uses:
                        constants.append(
                            StringConstant(
                                value=value,
                                class_name=class_name,
                                method_name=method_name,
                                provenance=[
                                    self.provenance(
                                        apk_sha256,
                                        f"{locator}#{class_name}.{method_name}#str/{value[:64]}",
                                    )
                                ],
                            )
                        )
                if len(constants) >= limit:
                    logger.warning("androguard: string limit %d reached; truncated", limit)
                    break
        except Exception as exc:
            logger.debug("androguard: string extraction failed: %s", exc)
        return constants


def _string_operand(instruction: Any) -> str | None:
    """The value a const-string instruction loads.

    Androguard renders the operand as a triple: the kind of the reference, the
    index into the DEX string pool, and the value itself. The pool index is
    the one ``DEX.get_strings()`` lists, so the value can be matched against a
    pool entry by value.

    The rendered instruction output is not used: it quotes the value and
    escapes it, and a string with a quote in it comes back changed.
    """
    try:
        operands = instruction.get_operands()
    except Exception:  # pragma: no cover - androguard raises on malformed bytecode
        return None
    if not operands:
        return None
    last = operands[-1]
    if len(last) < 3:
        return None
    value = last[2]
    return value if isinstance(value, str) else None


def _parse_dalvik_reference(reference: str) -> str | None:
    """Normalise an Androguard instruction operand into a canonical method id.

    Androguard renders a call target for human reading, with the argument descriptors
    space-separated::

        Ljava/io/PrintStream;->println(Ljava/lang/String; Ljava/lang/Object;)V

    Taking that string verbatim produces a descriptor that never equals the one the
    symbol table stores — ``get_descriptor()`` spaces its arguments the same way — so
    every cross-reference becomes unfindable. Re-join the argument list without spaces
    to get an id that matches ``MethodRef.qualified_name``.
    """
    if "->" not in reference:
        return None

    owner, _, member = reference.partition("->")
    open_paren = member.find("(")
    if open_paren == -1:
        return None
    # Type descriptors contain no parentheses, so the first ")" after "(" closes the
    # argument list. Everything after it is the return type.
    close_paren = member.find(")", open_paren)
    if close_paren == -1:
        return None

    name = member[:open_paren].strip()
    arguments = member[open_paren + 1 : close_paren].replace(" ", "")
    returns = member[close_paren + 1 :].strip()
    return f"{_to_dotted(owner)}.{name}({arguments}){returns}"


def _no_dex_error(apk: Path, dex_count: int) -> ToolError | None:
    """Record a warning when a readable archive yielded no DEX at all.

    Androguard returns empty lists without raising when there is no bytecode to parse.
    Reporting that as a success would produce a clean-looking report for an APK that was
    never actually indexed, so the gap is surfaced as evidence instead.
    """
    if dex_count > 0:
        return None
    return ToolError(
        tool="androguard",
        code=ToolErrorCode.PARSE_ERROR,
        message=f"{apk.name} contains no DEX bytecode to index",
        detail="The archive opened but no classes.dex was present, so no symbols were extracted.",
    )


def _class_kind(cls: Any) -> ClassKind:
    """Map a DEX access-flag string onto a :class:`ClassKind`."""
    try:
        flags = cls.get_access_flags_string()
    except Exception:
        return ClassKind.CLASS
    if "interface" in flags:
        return ClassKind.ANNOTATION if "annotation" in flags else ClassKind.INTERFACE
    if "enum" in flags:
        return ClassKind.ENUM
    return ClassKind.CLASS


__all__ = [
    "CONST_STRING_OPCODES",
    "INVOKE_KINDS",
    "INVOKE_OPCODES",
    "AndroguardBackend",
    "androguard_available",
]
