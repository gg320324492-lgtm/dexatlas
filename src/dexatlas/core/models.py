"""The unified analysis model.

Design rule: this normalizes the *index and metadata* across analysis backends. It does
not flatten distinct representations into a false common form — a JADX decompilation
failure and an Apktool Smali body stay different things, and both are reachable.

Every extracted item carries :class:`Provenance`: which tool produced it, at what
version, against which APK hash, and where in that tool's output it lives. A conclusion
that cannot be traced back to a code location is not a conclusion.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Errors and provenance
# ---------------------------------------------------------------------------


class ToolErrorCode(StrEnum):
    """Why a backend step did not produce a result."""

    NOT_INSTALLED = "not_installed"
    TIMEOUT = "timeout"
    EXIT_NONZERO = "exit_nonzero"
    PARSE_ERROR = "parse_error"
    UNSUPPORTED = "unsupported"
    OUTPUT_TRUNCATED = "output_truncated"


class ToolError(BaseModel):
    """A recorded backend failure.

    Backends fail often — on obfuscated or hostile input especially. A failure becomes
    a value attached to the affected result, never an exception that aborts a run.
    """

    model_config = ConfigDict(frozen=True)

    tool: str
    code: ToolErrorCode
    message: str
    detail: str | None = None

    def __str__(self) -> str:
        suffix = f": {self.detail}" if self.detail else ""
        return f"[{self.tool}/{self.code}] {self.message}{suffix}"


class Provenance(BaseModel):
    """Where one fact came from."""

    model_config = ConfigDict(frozen=True)

    tool: str
    tool_version: str | None = None
    apk_sha256: str
    #: Backend-native pointer back to the source, e.g. ``jadx:.../Foo.java#42``.
    locator: str

    def ref(self) -> str:
        """Short citation form used in reports.

        Deliberately ASCII: reports are written to files, diffed, and pasted into
        issues, and an arrow or em dash turns into mojibake wherever the reader's
        encoding is not UTF-8.
        """
        version = f" {self.tool_version}" if self.tool_version else ""
        return f"{self.tool}{version} -> {self.locator}"


class Sourced(BaseModel):
    """Mixin for anything traceable to a code location."""

    provenance: list[Provenance] = Field(default_factory=list)

    @property
    def tools(self) -> list[str]:
        """Distinct backends that contributed, in insertion order."""
        return list(dict.fromkeys(p.tool for p in self.provenance))


# ---------------------------------------------------------------------------
# Canonical identifiers
# ---------------------------------------------------------------------------


def canonical_descriptor(descriptor: str) -> str:
    """Return the canonical spelling of a JVM descriptor.

    A descriptor packs its argument types together::

        (Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    Androguard renders the very same descriptor for human reading, with a space after
    every argument separator::

        (Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;

    Both spell one method, so DexAtlas keeps only the canonical form. Otherwise a
    method id copied out of the symbol table never equals the id in the
    cross-reference table, and the lookup silently returns nothing.
    """
    open_paren = descriptor.find("(")
    if open_paren == -1:
        return descriptor.strip()
    # Type descriptors contain no parentheses, so the first ")" after "(" closes the
    # argument list. Everything after it is the return type.
    close_paren = descriptor.find(")", open_paren)
    if close_paren == -1:
        return descriptor.strip()
    arguments = "".join(descriptor[open_paren + 1 : close_paren].split())
    returns = "".join(descriptor[close_paren + 1 :].split())
    return f"({arguments}){returns}"


def canonical_method_id(method_id: str) -> str:
    """Return the canonical spelling of a qualified method id.

    ``com.foo.Bar.baz(Ljava/lang/String; Ljava/lang/String;)V`` becomes
    ``com.foo.Bar.baz(Ljava/lang/String;Ljava/lang/String;)V``. The class and method
    names keep their own spelling; only the whitespace is removed, so an id that was
    wrapped across two lines of a terminal still resolves.
    """
    open_paren = method_id.find("(")
    if open_paren == -1:
        return "".join(method_id.split())
    prefix = "".join(method_id[:open_paren].split())
    return f"{prefix}{canonical_descriptor(method_id[open_paren:])}"


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------


class ClassKind(StrEnum):
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    ANNOTATION = "annotation"


class ClassRef(Sourced):
    """A class as seen by an analysis backend."""

    name: str
    """Fully-qualified dotted name, e.g. ``com.example.app.MainActivity``."""

    kind: ClassKind = ClassKind.CLASS
    superclass: str | None = None
    interfaces: list[str] = Field(default_factory=list)
    access_flags: list[str] = Field(default_factory=list)
    method_count: int = 0
    """How many methods the class has.

    A backend reads one DEX file, so it sees one DEX file's share of a class:
    a class split across two DEX files is two partial views, and each of
    them counts only its own half. The value a backend produces is therefore
    a *view* of the class, not the class's total.

    The number the index stores is the total. It is counted from the rows the
    ``methods`` table holds, so a class row and a method query always agree —
    the storage layer overwrites the view with the count it measured.
    """

    field_count: int = 0
    """How many fields the class has — the same two numbers, and the same
    split between a backend's view of the class and the class's real total.

    The index stores the total, counted from the rows the ``fields`` table
    holds.
    """

    @property
    def package(self) -> str:
        return self.name.rpartition(".")[0]

    @property
    def simple_name(self) -> str:
        return self.name.rpartition(".")[2]


class MethodRef(Sourced):
    """A method as seen by an analysis backend."""

    class_name: str
    name: str
    descriptor: str
    """JVM descriptor, e.g. ``(Ljava/lang/String;)V``. Stable across backends.

    Always canonical: argument types are packed together, with no separator
    whitespace, so that the id is the same everywhere it appears.
    """

    access_flags: list[str] = Field(default_factory=list)
    signature: str | None = None
    decompiled: bool = False
    """Whether the decompiler produced Java for this method.

    True means JADX wrote real Java for it. False means there is no decompiled
    source: either JADX emitted a placeholder for a method it could not
    reconstruct, or it wrote no source for the method at all — an elided
    constructor, an abstract or a native method with no body.

    The flag used to sit on a different fact — Androguard's "this method has a
    code item in the DEX" — which is true of nearly every method in an APK and
    says nothing about whether the code can be read. That other fact is not
    lost: a method with no code item is an abstract or a native method, and the
    access flags say which.
    """

    @field_validator("descriptor")
    @classmethod
    def _canonicalise_descriptor(cls, value: str) -> str:
        return canonical_descriptor(value)

    @property
    def qualified_name(self) -> str:
        return f"{self.class_name}.{self.name}{self.descriptor}"


class FieldRef(Sourced):
    """A field as seen by an analysis backend."""

    class_name: str
    name: str
    descriptor: str
    access_flags: list[str] = Field(default_factory=list)
    constant_value: str | None = None

    @field_validator("descriptor")
    @classmethod
    def _canonicalise_descriptor(cls, value: str) -> str:
        return canonical_descriptor(value)

    @property
    def qualified_name(self) -> str:
        return f"{self.class_name}.{self.name}:{self.descriptor}"


class InvocationKind(StrEnum):
    """How a method is called, as the Dalvik instruction that carries the call says.

    Dalvik has more than one way to invoke a method, and they are different
    opcodes in the bytecode. A static call and a virtual call are not the same
    thing, and the opcode is the only thing that says which one a call site is.
    """

    INVOKE = "invoke"
    """A call edge whose opcode is not known.

    The fallback for an edge that did not come out of a DEX instruction — a
    hand-built reference, or a backend that does not read bytecode. It says
    that a call happened and nothing more.
    """

    VIRTUAL = "virtual"
    """``invoke-virtual``: a call on an instance, dispatched virtually."""

    SUPER = "super"
    """``invoke-super``: a call on the superclass of the current class."""

    DIRECT = "direct"
    """``invoke-direct``: a call on a private or constructor method."""

    STATIC = "static"
    """``invoke-static``: a call on a class method, with no instance."""

    INTERFACE = "interface"
    """``invoke-interface``: a call on an interface method."""


class MethodReference(Sourced):
    """An edge: caller method invokes callee method."""

    caller: str
    callee: str
    kind: InvocationKind = InvocationKind.INVOKE
    """How the call is made.

    The value is the kind of the Dalvik invocation opcode the edge was read
    from. The values are ``invoke``, ``virtual``, ``super``, ``direct``,
    ``static`` and ``interface`` — a static call and a virtual call are not
    the same thing, and the cross-reference is the only place that difference
    shows.

    ``invoke`` is the fallback: it says a call happened without saying which
    opcode it was, and is what an edge carries when the opcode is not known.
    """

    @field_validator("caller", "callee")
    @classmethod
    def _canonicalise_ids(cls, value: str) -> str:
        return canonical_method_id(value)


class StringConstant(Sourced):
    """An entry in the DEX string pool.

    The pool holds more than literals. Type descriptors, member names and
    source-file names are in it too, so this is the pool rather than the set
    of string literals — in a small APK most of the entries are descriptors
    and member names, not text a person wrote.

    Resources are not covered: no backend reads the resource table, so a
    string that exists only in a resource file is not here.

    One row per use site. A constant used in two methods is two rows, one
    per method, because each row has to point at one place in the code. A
    pool entry that no instruction loads — a descriptor, a member name — has
    no place to point at, and its row carries no location.
    """

    value: str
    class_name: str | None = None
    """The class whose bytecode uses this constant, when one does."""

    method_name: str | None = None
    """The method whose bytecode uses this constant, when one does."""


# ---------------------------------------------------------------------------
# APK-level metadata
# ---------------------------------------------------------------------------


class ManifestPermission(BaseModel):
    name: str
    protection_level: str | None = None


class ManifestComponent(BaseModel):
    """A declared component from AndroidManifest.xml."""

    kind: str
    """``activity``, ``service``, ``receiver``, ``provider``, ``application``..."""

    name: str
    exported: bool | None = None
    permission: str | None = None
    intent_filters: list[str] = Field(default_factory=list)


class ManifestInfo(BaseModel):
    """Parsed AndroidManifest.xml."""

    package: str | None = None
    version_code: str | None = None
    version_name: str | None = None
    min_sdk: str | None = None
    target_sdk: str | None = None
    permissions: list[ManifestPermission] = Field(default_factory=list)
    components: list[ManifestComponent] = Field(default_factory=list)
    shared_user_id: str | None = None

    @property
    def exported_components(self) -> list[ManifestComponent]:
        return [c for c in self.components if c.exported is True]


class ApkMetadata(BaseModel):
    """Facts established from the APK archive itself, without any backend."""

    sha256: str
    size_bytes: int
    path: Path
    zip_entries: int = 0
    dex_files: list[str] = Field(default_factory=list)
    native_libraries: list[str] = Field(default_factory=list)
    has_signed_certificate: bool = False


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class EvidenceKind(StrEnum):
    CODE_LOCATED = "code_located"
    CROSS_REFERENCE = "cross_reference"
    DECLARATION = "declaration"
    BEHAVIOUR = "behaviour"
    OBSERVATION = "observation"


class EvidenceLevel(StrEnum):
    """How much weight a finding carries.

    Model output is never promoted past :attr:`LEAD` without grounding. This is the
    mechanism behind "an LLM thinking code looks risky is not a finding".
    """

    VERIFIED = "verified"
    """Reproduced by a deterministic tool, with a locatable code location."""

    LEAD = "lead"
    """A static-analysis or model-suggested risk indicator. Not a confirmed issue."""

    INSUFFICIENT = "insufficient"
    """Not enough evidence either way. Needs human validation."""


class Evidence(Sourced):
    """One traceable observation backing a conclusion."""

    id: str
    kind: EvidenceKind
    level: EvidenceLevel
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


#: The key under which an evidence record's detail carries the decompilation
#: coverage of an analysis. The reports read it back rather than recomputing
#: it: a report built from a stored project has no method list to recompute
#: from, and the record is what the analysis stated.
DECOMPILATION_DETAIL = "decompilation"


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """One analysed APK."""

    id: str
    """Stable identifier, derived from the APK hash."""

    apk: ApkMetadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ProjectStatus = ProjectStatus.PENDING
    tool_versions: dict[str, str | None] = Field(default_factory=dict)
    errors: list[ToolError] = Field(default_factory=list)
    class_count: int = 0
    method_count: int = 0
    reference_count: int = 0
    evidence_count: int = 0

    @classmethod
    def new_id(cls, sha256: str) -> str:
        """Project ids are content-addressed, so re-analysing an APK is idempotent."""
        return f"apk_{sha256[:16]}"

    @classmethod
    def create(cls, apk: ApkMetadata) -> Self:
        return cls(id=cls.new_id(apk.sha256), apk=apk)


# ---------------------------------------------------------------------------
# Hashing helper
# ---------------------------------------------------------------------------


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file through SHA-256 without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
