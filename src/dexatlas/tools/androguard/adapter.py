"""Androguard backend — classes, methods, fields and cross-references.

This is the *index*. JADX gives readable Java; Apktool gives the manifest and Smali;
Androguard gives the authoritative symbol graph, because parsing DEX is what it does
and a decompiler's text output is the wrong source for structure.

Cross-references are recovered by walking bytecode: Androguard 4.x removed the xref
cache, so a call edge is found by scanning each method's instructions for an
invoke-form opcode and reading the target out of its last operand.

Androguard is a Python library, so there is no tool to shell out to — but the DEX
files it parses are untrusted, and a library parses them in the process that called it.
So the parse is put in a process of its own: a worker that the service starts, bounds
and throws away. A malformed DEX that takes the interpreter down takes down the
worker, and the service carries on with a recorded parse failure. The index the
worker produces is the index the service would have produced itself.

See :mod:`dexatlas.tools.androguard.worker` for the worker, and
``docs/architecture/runtime-isolation.md`` for what the boundary is and why.
"""

from __future__ import annotations

import importlib.util
import logging
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
from dexatlas.tools.androguard.isolation import WorkerJob, run_worker
from dexatlas.tools.base import Backend

if TYPE_CHECKING:  # pragma: no cover
    from androguard.core.dex import DEX

logger = logging.getLogger(__name__)

#: The three budgets of one analysis. They cap the work a single APK can cost,
#: and they are counted **across the whole APK**, not per DEX file: a limit
#: that resets for every DEX file hands a multi-dex APK N times the allowance,
#: which is exactly backwards — the bigger the APK, the more it needs a
#: ceiling. Obfuscated APKs carry hundreds of thousands of methods, and an
#: unbounded walk is a denial of service against ourselves.
DEFAULT_METHOD_LIMIT = 200_000
#: Max string constants indexed per APK.
DEFAULT_STRING_LIMIT = 50_000
#: Max bytecode instructions walked per APK.
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


#: The name Loguru files Androguard's records under.
#:
#: Loguru takes the name from the module the call was made in, so this covers
#: ``androguard`` itself and every module under it.
ANDROGUARD_LOGGER_NAME = "androguard"


@contextmanager
def _suppress_androguard_logging() -> Iterator[None]:
    """Silence Androguard's loguru output, and nothing else.

    On a large APK it emits thousands of parse-trace lines at DEBUG, which buries the
    CLI's own output.

    The suppression is by *name*: Loguru's ``disable``/``enable`` pair turns off the
    records whose module is ``androguard`` or one of its children, and leaves every
    handler in the process exactly where it was. The version this replaced called
    ``logger.remove()``, which deletes *every* handler the process has — including
    the default one and every handler the host application installed. One analysis
    was enough to leave the host with no logging at all, and nothing in the library
    could put it back.

    Two things about the switch are worth knowing, because both are the price of
    not touching the host's handlers:

    - The switch is global, not per-thread. Two analyses running at once share it,
      so the first to finish turns it back on for the one still running. The cost
      is a few extra DEBUG lines in that second analysis.
    - If the host application had disabled Androguard's logging itself, this turns
      it back on. Loguru offers no way to read that state back, and leaving it
      disabled for good would be the worse of the two mistakes.

    Measured on the fixture APK: an analysis emits 200 records, every one of them
    under ``androguard.``; with the name switched off, none of them reaches a
    handler.
    """
    try:
        from loguru import logger as loguru_logger
    except ImportError:
        yield
        return

    loguru_logger.disable(ANDROGUARD_LOGGER_NAME)
    try:
        yield
    finally:
        loguru_logger.enable(ANDROGUARD_LOGGER_NAME)


def _replay_logs(entries: list[tuple[int, str, str]]) -> None:
    """Log what the worker logged.

    The worker is a different process, so the records it wrote would never reach
    the service's log. They come back with the result and are logged here, under
    the name they were written under, so the service says what it would have said
    had the parse happened in-process.
    """
    for level, name, message in entries:
        logging.getLogger(name).log(level, message)


class AndroguardBackend(Backend):
    """Reads DEX metadata via the ``androguard`` library."""

    name = "androguard"
    path_env_var = ""
    install_hint = "Install the analysis extra: uv sync --extra analysis"

    def __init__(self, settings: Settings, *, tool_version: str | None = None) -> None:
        super().__init__(settings)
        # The version can be pinned as well as probed. The worker is given the
        # version the service resolved, so the provenance records it writes carry
        # the same version the service would have written, even though the two
        # processes resolved it separately.
        self._version: str | None = tool_version
        self._version_probed = tool_version is not None

    def resolve(self) -> Path | None:
        """No executable to locate: this backend is a library, so its installed package
        is what "being present" means."""
        if not androguard_available():
            return None
        import androguard

        location = getattr(androguard, "__file__", None)
        return Path(location) if location else Path("androguard")

    def version(self) -> str | None:
        """The installed Androguard version, as a bare version number.

        The same shape the other two backends report: JADX prints its own version and
        Apktool prints its own, so a reader comparing them is comparing version
        numbers. Androguard used to prefix its own name, which made one entry in a
        list of versions read differently from the rest.

        ``None`` means the version is not known — the package is installed without
        metadata, which is rare but not a reason to invent one.

        The answer is probed once and remembered. Every symbol this backend
        indexes carries a provenance record, and every record asks for the
        version; without the cache each of those asks the package index for
        the installed distribution, which turns a run over a large APK into a
        run dominated by bookkeeping.
        """
        if self._version_probed:
            return self._version
        self._version_probed = True
        if not androguard_available():
            return None
        from importlib.metadata import PackageNotFoundError, version

        try:
            self._version = version("androguard")
        except PackageNotFoundError:  # pragma: no cover - installed without metadata
            self._version = None
        return self._version

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

        The DEX files are parsed by a worker process rather than here. Parsing is the
        part of the analysis that runs on bytes the service did not write, so it is
        the part that gets a process of its own: a DEX file that takes the
        interpreter down takes down the worker, and the service sees a recorded
        parse failure instead of a dead process.
        """
        if not androguard_available():
            return [], [], [], [], [], self.missing_error()

        job = WorkerJob(
            apk_path=str(apk.resolve()),
            apk_sha256=apk_sha256,
            method_limit=method_limit,
            string_limit=string_limit,
            instruction_limit=instruction_limit,
            tool_version=self.version(),
            log_level=logging.getLogger().getEffectiveLevel(),
        )
        outcome = run_worker(self, job, timeout=self._settings.tool_timeout_seconds)
        if outcome.result is not None:
            _replay_logs(outcome.result.logs)
            return outcome.result.as_index()
        return [], [], [], [], [], outcome.error

    def _extract_symbols(
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
        """Index the APK's DEX files, in this process.

        This is the worker's job, and the only place where untrusted DEX bytes are
        parsed. The service reaches it through the worker rather than directly, so
        that a DEX file which takes the interpreter down cannot take the service
        down with it.
        """
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
        failures: list[ToolError] = []
        truncations: list[ToolError] = []
        dex_count = 0
        # The three budgets are one budget per analysis, not one per DEX file.
        # A multi-dex APK would otherwise get N times the allowance, which is
        # exactly backwards: the bigger the APK, the more it needs a ceiling.
        instructions_seen = 0
        strings_indexed = 0
        walk_stopped = False

        try:
            # The suppression covers the whole parse, the DEX reading included.
            # It used to stop after the archive was opened, and the parse stayed
            # quiet only because the handler removal it relied on was permanent.
            with _suppress_androguard_logging():
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
                        failures.append(
                            ToolError(
                                tool=self.name,
                                code=ToolErrorCode.PARSE_ERROR,
                                message=f"androguard could not parse {dex_name}",
                                detail=f"{type(exc).__name__}: {exc}"[:2000],
                            )
                        )
                        continue

                    try:
                        literal_sites, instructions_seen, truncation = self._index_dex(
                            dex,
                            apk_sha256=apk_sha256,
                            dex_name=dex_name,
                            classes=classes,
                            methods=methods,
                            fields=fields,
                            references=references,
                            method_limit=method_limit,
                            instruction_limit=instruction_limit,
                            instructions_seen=instructions_seen,
                        )
                        if truncation is not None:
                            # A walk budget is spent: the files after this one are
                            # not walked, so nothing of theirs is in the index.
                            _record_truncation(truncations, truncation)
                            walk_stopped = True
                        if strings_indexed < string_limit:
                            dex_strings, string_truncation = self._index_strings(
                                dex,
                                apk_sha256,
                                locator,
                                string_limit,
                                literal_sites,
                                already_indexed=strings_indexed,
                            )
                            strings.extend(dex_strings)
                            strings_indexed += len(dex_strings)
                            if string_truncation is not None:
                                _record_truncation(truncations, string_truncation)
                        if walk_stopped:
                            break
                    except Exception as exc:
                        logger.warning("androguard: indexing %s failed: %s", dex_name, exc)
                        failures.append(
                            ToolError(
                                tool=self.name,
                                code=ToolErrorCode.PARSE_ERROR,
                                message=f"androguard could not fully index {dex_name}",
                                detail=f"{type(exc).__name__}: {exc}"[:2000],
                            )
                        )
        except Exception as exc:
            logger.warning("androguard: analysis of %s failed: %s", apk.name, exc)
            failures.append(
                ToolError(
                    tool=self.name,
                    code=ToolErrorCode.PARSE_ERROR,
                    message=f"androguard could not fully parse {apk.name}",
                    detail=f"{type(exc).__name__}: {exc}"[:2000],
                )
            )

        if truncations:
            return (
                classes,
                methods,
                fields,
                references,
                strings,
                _truncation_error(truncations, _combine_failures(failures)),
            )
        return (
            classes,
            methods,
            fields,
            references,
            strings,
            _combine_failures(failures) or _no_dex_error(apk, dex_count),
        )

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
        instructions_seen: int,
    ) -> tuple[dict[str, list[tuple[str, str]]], int, ToolError | None]:
        """Index one DEX file, and report where its string constants are used.

        Returns the use sites of the string constants — a map from a constant to
        the ``(class, method)`` pairs whose bytecode loads it — the number of
        instructions walked so far *across the whole APK*, and, when a limit
        stopped the walk, the error that says so. A constant used in two
        methods has two entries, because each of them is a place in the code
        that a reader can be sent to.

        A limit is not a failure: the rows that were written hold. But an index
        that stops early is an index that is missing something, and a reader who
        only sees the counts cannot tell a complete APK from a shortened one.
        So the walk that stops early also says that it stopped.
        """
        locator_base = f"androguard:{dex_name}"
        literal_sites: dict[str, list[tuple[str, str]]] = {}
        class_iter = iter(dex.get_classes())

        for cls in class_iter:
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
                skipped = len(class_methods) + _methods_in(class_iter)
                logger.warning(
                    "androguard: method limit %d reached on %s; index is truncated",
                    method_limit,
                    dex_name,
                )
                return (
                    literal_sites,
                    instructions_seen,
                    ToolError(
                        tool=self.name,
                        code=ToolErrorCode.OUTPUT_TRUNCATED,
                        message=(
                            f"method limit {method_limit} reached while indexing {dex_name}: "
                            f"the index is incomplete — {skipped} methods in this file were not "
                            f"indexed, and the DEX files after it were not walked"
                        ),
                        detail=(
                            f"{len(methods)} methods were indexed before the limit; the classes "
                            f"after this one, their methods, their fields and their "
                            f"cross-references are not in the index, and neither is anything in "
                            f"the DEX files that follow"
                        ),
                    ),
                )

            for method_index, method in enumerate(class_methods):
                if instructions_seen >= instruction_limit:
                    # The budget is spent for the whole APK, so the walk stops
                    # here and not one method further: a method that is not
                    # scanned is not indexed either.
                    skipped = len(class_methods) - method_index + _methods_in(class_iter)
                    logger.warning(
                        "androguard: instruction limit %d reached; xref index is truncated",
                        instruction_limit,
                    )
                    return (
                        literal_sites,
                        instructions_seen,
                        ToolError(
                            tool=self.name,
                            code=ToolErrorCode.OUTPUT_TRUNCATED,
                            message=(
                                f"instruction limit {instruction_limit} reached while indexing "
                                f"{dex_name}: the index is incomplete — {skipped} methods in this "
                                f"file were not indexed, their cross-references were not scanned, "
                                f"and the DEX files after it were not walked"
                            ),
                            detail=(
                                f"{len(methods)} methods were indexed before the limit; the bytecode "
                                f"of the methods after it was not read, so their calls and their "
                                f"string constants are not in the index, and neither is anything "
                                f"in the DEX files that follow"
                            ),
                        ),
                    )
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

        return literal_sites, instructions_seen, None

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
        already_indexed: int = 0,
    ) -> tuple[list[StringConstant], ToolError | None]:
        """The DEX string pool, and where each of its entries is used.

        The pool is every string the DEX holds. A use site is the method whose
        bytecode loads one of them, and it is what turns a constant into
        something a reader can be sent to: a hardcoded key that no method is
        known to use is a value; one that a method uses is a place.

        A constant used in two methods is two rows, one per method, because a
        row has to point at one place. A pool entry that no instruction loads —
        a type descriptor, a member name — has no place to point at, and its
        row carries no location.

        When the limit stops the pool, the returned error says how much of the
        pool is left out: a truncated string index is an index that cannot be
        searched for everything the APK holds.

        ``already_indexed`` is how many rows the APK's other DEX files already
        produced. The budget is one budget per analysis, so a pool is measured
        against the whole APK rather than against itself.
        """
        constants: list[StringConstant] = []
        truncation: ToolError | None = None
        pool_size = 0
        entries_seen = 0
        try:
            pool = list(dex.get_strings())
            pool_size = len(pool)
            for value in pool:
                if not isinstance(value, str) or not value:
                    continue
                entries_seen += 1
                if already_indexed + len(constants) >= limit:
                    truncation = self._string_truncation(
                        limit, pool_size, entries_seen, already_indexed + len(constants)
                    )
                    break
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
                        # One value can be used in several methods, and each use is
                        # its own row. The limit counts rows, so it has to be checked
                        # after every row, not once per value.
                        if already_indexed + len(constants) >= limit:
                            truncation = self._string_truncation(
                                limit, pool_size, entries_seen, already_indexed + len(constants)
                            )
                            break
                    if truncation is not None:
                        break
                if already_indexed + len(constants) >= limit:
                    truncation = self._string_truncation(
                        limit, pool_size, entries_seen, already_indexed + len(constants)
                    )
                    break
        except Exception as exc:
            logger.debug("androguard: string extraction failed: %s", exc)
        return constants, truncation

    def _string_truncation(
        self, limit: int, pool_size: int, entries_seen: int, rows_written: int
    ) -> ToolError:
        """The error that says the string index stopped short.

        The pool's size is known — it is a list — so the number of entries that
        were not indexed is a number, not a guess. A reader can then tell how
        much of the APK's text is missing from the search index.
        """
        missing = max(pool_size - entries_seen, 0)
        logger.warning("androguard: string limit %d reached; index is truncated", limit)
        return ToolError(
            tool=self.name,
            code=ToolErrorCode.OUTPUT_TRUNCATED,
            message=(
                f"string limit {limit} reached: the index is incomplete — {missing} entries of "
                f"this DEX file's string pool were not indexed, and no DEX file after it "
                f"contributed any string"
            ),
            detail=(
                f"the pool holds {pool_size} entries; {entries_seen} were read and {rows_written} "
                f"rows were written before the limit, and the entries after them have neither "
                f"a row nor a use site"
            ),
        )


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


def _methods_in(classes: Iterator[Any]) -> int:
    """How many methods the classes that were never reached hold.

    The walk stopped early, and a reader has to be told what the early stop
    cost. The classes that were not reached are still in the DEX file, so the
    number of methods they hold is counted rather than guessed: it is the
    difference between "the index is incomplete" and "the index is missing
    5,001 methods".
    """
    total = 0
    for cls in classes:
        try:
            total += len(cls.get_methods())
        except Exception:  # pragma: no cover - androguard raises on malformed bytecode
            continue
    return total


def _combine_failures(failures: list[ToolError]) -> ToolError | None:
    """One error for a set of failures that are all the same kind of failure.

    Two DEX files that could not be parsed are two gaps in the index, and the
    reader has to know about both of them: naming only the first would make
    the index look more complete than it is — and a report that says "the index
    is incomplete" has to be able to say how much of it is missing.

    The messages are joined rather than replaced, so each gap keeps its own
    name. The details are joined the same way.
    """
    if not failures:
        return None
    if len(failures) == 1:
        return failures[0]
    return ToolError(
        tool=failures[0].tool,
        code=failures[0].code,
        message="; ".join(failure.message for failure in failures),
        detail="; ".join(failure.detail for failure in failures if failure.detail) or None,
    )


def _record_truncation(truncations: list[ToolError], error: ToolError) -> None:
    """Keep one error per kind of limit.

    A budget that is spent stays spent: the second DEX file to reach the same
    limit is not news, and a report that says the same thing four times reads
    like four separate problems. The kind is the first word of the message —
    "method limit", "instruction limit", "string limit".
    """
    key = error.message.split(" limit", 1)[0]
    if any(existing.message.split(" limit", 1)[0] == key for existing in truncations):
        return
    truncations.append(error)


def _truncation_error(truncations: list[ToolError], other: ToolError | None) -> ToolError:
    """One error for every gap in the index, with the truncation first.

    A truncated index is a different fact from a failed parse, and a reader
    needs both: the truncation says what is missing from the index, the parse
    error says which file could not be read at all. The truncation leads
    because "the index is incomplete" is the fact that changes how every
    number in the report has to be read.
    """
    message = "; ".join(truncation.message for truncation in truncations)
    details = [truncation.detail for truncation in truncations if truncation.detail]
    if other is not None:
        details.append(f"{other.tool} also reported: {other.message}")
    return ToolError(
        tool=truncations[0].tool,
        code=ToolErrorCode.OUTPUT_TRUNCATED,
        message=message,
        detail="; ".join(details) or None,
    )


__all__ = [
    "CONST_STRING_OPCODES",
    "INVOKE_KINDS",
    "INVOKE_OPCODES",
    "AndroguardBackend",
    "androguard_available",
]
