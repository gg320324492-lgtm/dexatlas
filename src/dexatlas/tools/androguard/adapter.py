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
    MethodRef,
    MethodReference,
    StringConstant,
    ToolError,
    ToolErrorCode,
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

#: Opcodes that reference a method. The target is the final operand.
INVOKE_OPCODES = frozenset(
    {
        "invoke-virtual",
        "invoke-super",
        "invoke-direct",
        "invoke-static",
        "invoke-interface",
        "invoke-virtual/range",
        "invoke-super/range",
        "invoke-direct/range",
        "invoke-static/range",
        "invoke-interface/range",
    }
)


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
                    self._index_dex(
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
                    strings.extend(self._index_strings(dex, apk_sha256, locator, string_limit))
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
    ) -> None:
        locator_base = f"androguard:{dex_name}"
        instructions_seen = 0

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
                return

            for method in class_methods:
                qualified = f"{class_name}.{method.get_name()}{method.get_descriptor()}"
                methods.append(
                    MethodRef(
                        class_name=class_name,
                        name=method.get_name(),
                        descriptor=method.get_descriptor(),
                        access_flags=sorted(method.get_access_flags_string().split()),
                        # A method with no code item is abstract or native: declared,
                        # but with no body to decompile.
                        decompiled=bool(method.get_code()),
                        provenance=[self.provenance(apk_sha256, f"{class_locator}#{qualified}")],
                    )
                )

                if instructions_seen >= instruction_limit:
                    logger.warning(
                        "androguard: instruction limit %d reached; xref index is truncated",
                        instruction_limit,
                    )
                    return
                instructions_seen, calls = self._calls_in(method, instructions_seen)
                for callee in calls:
                    references.append(
                        MethodReference(
                            caller=qualified,
                            callee=callee,
                            kind="invoke",
                            provenance=[
                                self.provenance(apk_sha256, f"{locator_base}#{qualified}->{callee}")
                            ],
                        )
                    )

    def _calls_in(self, method: Any, instructions_seen: int) -> tuple[int, list[str]]:
        """Method targets invoked by ``method``, read from its bytecode.

        The target is the last operand of an invoke opcode and arrives as a Dalvik
        reference such as ``Ljava/io/PrintStream;->println(Ljava/lang/String;)V``.
        """
        calls: list[str] = []
        if not method.get_code():
            return instructions_seen, calls

        try:
            for instruction in method.get_instructions():
                instructions_seen += 1
                if instruction.get_name() not in INVOKE_OPCODES:
                    continue
                target = instruction.get_output().rsplit(", ", 1)[-1].strip()
                if "->" not in target:
                    continue
                owner, _, member = target.partition("->")
                calls.append(f"{_to_dotted(owner)}.{member}")
        except Exception as exc:
            logger.debug("androguard: decoding %s failed: %s", method.get_name(), exc)
        return instructions_seen, calls

    def _index_strings(
        self, dex: DEX, apk_sha256: str, locator: str, limit: int
    ) -> list[StringConstant]:
        constants: list[StringConstant] = []
        try:
            for value in dex.get_strings():
                if not isinstance(value, str) or not value:
                    continue
                constants.append(
                    StringConstant(
                        value=value,
                        provenance=[self.provenance(apk_sha256, f"{locator}#str/{value[:64]}")],
                    )
                )
                if len(constants) >= limit:
                    logger.warning("androguard: string limit %d reached; truncated", limit)
                    break
        except Exception as exc:
            logger.debug("androguard: string extraction failed: %s", exc)
        return constants


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


__all__ = ["INVOKE_OPCODES", "AndroguardBackend", "androguard_available"]
