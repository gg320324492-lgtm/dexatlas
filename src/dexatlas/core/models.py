"""The unified analysis model.

Design rule: this normalizes the *index and metadata* across analysis backends. It does
not flatten distinct representations into a false common form — a JADX decompilation
failure and an Apktool Smali body stay different things, and both are reachable.

Every extracted item carries :class:`Provenance`: which tool produced it, at what
version, against which APK hash, and where in that tool's output it lives. A conclusion
that cannot be traced back to a code location is not a conclusion.

The location has to survive the trip, too. A locator that names a path on the machine
that ran the analysis points at nothing on the reader's machine, so a locator names a
place *inside an artefact* — the APK, or the output tree a backend wrote — and never
an absolute path.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    ANALYSIS_FAILED = "analysis_failed"
    """The analysis itself did not complete.

    Every other code here describes a *tool* that could not do its job: it
    was not installed, it timed out, it wrote something that could not be
    read. This one describes the failure of the analysis — the pipeline that
    runs the tools — rather than of any one of them. A backend that fails is
    recorded by its own adapter, and the run carries on without it; a failure
    of the analysis is recorded once, on the project, and stops the run.
    """


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


#: The tool that owns the DEX symbol index.
#:
#: Every class, method, field, cross-reference and string constant in the index
#: was read out of the APK's DEX files by this backend, so a failure of this
#: one leaves the index short of the APK. A failure of the decompiler or of the
#: resource reader does not: those contribute a second view of the code and the
#: resource table, and the symbol index is whole without them.
INDEX_TOOL = "androguard"

#: The tool that owns the analysis itself.
#:
#: A backend failure is recorded by the backend's own adapter, under the
#: backend's name: the failure belongs to the tool that failed. A failure of
#: the analysis belongs to no backend — it is DexAtlas itself that did not
#: finish — and it is recorded under this name so that a reader can tell the
#: two apart. A record that says "jadx timed out" is about a tool; a record
#: that says "dexatlas did not complete" is about the run.
ANALYSIS_TOOL = "dexatlas"


def index_gaps(errors: list[ToolError]) -> list[ToolError]:
    """The failures that leave the symbol index short of the whole APK.

    A gap is not the same thing as an error. A decompiler that is not installed
    is an error and not a gap: the index was still built, in full, by the
    reader of the bytecode. A DEX file that could not be parsed is both — the
    index is missing whatever that file held, and every count in a report has
    to be read as a count of *what was indexed* rather than of what the APK
    contains.

    A failure of the analysis is a gap as well. The run stopped, so whatever
    the index would have held is not in it, and a report that says the index
    is complete — over a project with no classes at all — would be the worst
    kind of wrong.
    """
    return [
        error
        for error in errors
        if error.tool == INDEX_TOOL or error.code is ToolErrorCode.ANALYSIS_FAILED
    ]


#: A locator written before the JADX output tree became a relative path. The old
#: form was ``jadx:<absolute path>``, and that path ran through the project
#: workspace on the machine that ran the analysis. Only the tail after the
#: project directory is a fact about the analysis; the rest was a fact about
#: the machine.
_LEGACY_JADX_LOCATOR = re.compile(r"^jadx:.*?/projects/apk_[0-9a-f]{16}/jadx/(?P<path>.+)$")


def normalize_locator(locator: str) -> str:
    """Rewrite a locator written in an older format into the current one.

    The only format that changed is JADX's, which used to carry the absolute
    path of the file it had written. A workspace indexed before the change still
    holds those, and reading them back in the current form keeps an old
    database producing a portable report — without a migration, and without the
    reader having to know which format a row was written in.

    A locator that does not match the old shape is left exactly as it is: an
    unfamiliar locator is not one to guess at.
    """
    match = _LEGACY_JADX_LOCATOR.match(locator)
    if match is None:
        return locator
    return f"jadx:{match.group('path')}"


class Provenance(BaseModel):
    """Where one fact came from."""

    model_config = ConfigDict(frozen=True)

    tool: str
    tool_version: str | None = None
    apk_sha256: str
    #: Backend-native pointer back to the source, e.g. ``jadx:sources/a/Foo.java``.
    #:
    #: The shape is ``<tool>:<place>``, and the place is relative to the
    #: artefact the tool names: a member of the APK for Androguard, a file
    #: inside the output tree for JADX and Apktool. An absolute path would name
    #: the machine that ran the analysis instead of the analysis itself, and a
    #: reader on another machine could not follow it.
    locator: str

    @field_validator("locator")
    @classmethod
    def _read_an_older_locator_in_the_current_form(cls, value: str) -> str:
        """A locator stored in an older format is read as the current one."""
        return normalize_locator(value)

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

    The resource table is a different thing, and is indexed separately: see
    :class:`ResourceString`, which is read out of Apktool's decoded ``res/``
    tree. This model is the DEX string pool and nothing else.

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


#: The tags AndroidManifest.xml declares a component with.
#:
#: The model holds no others: a component of a kind nobody has heard of is not
#: a component this reader knows how to talk about. The set is enforced on the
#: way in rather than described in prose, so the documentation and the code
#: cannot drift apart.
MANIFEST_COMPONENT_KINDS = (
    "activity",
    "activity-alias",
    "service",
    "receiver",
    "provider",
    "application",
)


class ManifestComponent(BaseModel):
    """A declared component from AndroidManifest.xml."""

    kind: str
    """The tag the component was declared with.

    The values are ``activity``, ``activity-alias``, ``service``, ``receiver``,
    ``provider`` and ``application`` — the tags AndroidManifest.xml uses, and
    the only ones the model holds.
    """

    name: str
    exported: bool | None = None
    permission: str | None = None
    intent_filters: list[str] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _known_component_kind(cls, value: str) -> str:
        if value not in MANIFEST_COMPONENT_KINDS:
            raise ValueError(
                f"{value!r} is not a component kind; the known kinds are "
                + ", ".join(MANIFEST_COMPONENT_KINDS)
            )
        return value


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

    Model output is never promoted past :attr:`LEAD`. The mechanism is in
    :class:`Evidence`: a ``BEHAVIOUR`` record may not carry :attr:`VERIFIED`,
    so a claim that no tool established cannot be rendered as a finding.

    ``VERIFIED`` is what a deterministic tool established, with a locatable
    code location. ``LEAD`` is what a model or a heuristic suspects. Nothing
    DexAtlas writes today is a suspicion -- every record it writes was read
    out of a tool's output -- so the level a record carries is ``VERIFIED``.
    The other two are the ceiling for the claims that are not facts, and the
    rule above is what keeps them there.
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

    @model_validator(mode="after")
    def _a_behaviour_is_never_verified(self) -> Self:
        """A behaviour is a claim; only a tool establishes a fact.

        The report renders every ``verified`` record as "deterministically
        established by an analysis tool", so a behaviour that carried that
        level would put a false sentence in the report -- and a reader who
        believed it would act on a guess.

        The rule is on the kind rather than on the level, so a model's output
        can still be a ``lead``, which is what it is written as; what it can
        never become is a finding. A claim that a tool later confirms is not
        that claim promoted: it is the tool's own record, and the two say
        different things.
        """
        if self.kind is EvidenceKind.BEHAVIOUR and self.level is EvidenceLevel.VERIFIED:
            raise ValueError(
                "a behaviour claim may not be verified: only a tool can establish a fact. "
                "Record the tool's confirmation as its own evidence."
            )
        return self


#: The key under which an evidence record's detail carries the decompilation
#: coverage of an analysis. The reports read it back rather than recomputing
#: it: a report built from a stored project has no method list to recompute
#: from, and the record is what the analysis stated.
DECOMPILATION_DETAIL = "decompilation"

#: The key under which a cross-reference record's detail states how many call
#: sites it covers.
#:
#: The unit of a cross-reference record is the *called method*, not the call:
#: one record says "this method of this APK is called from here, here and
#: here", and the call sites it names are the detail. A record that covered
#: one call site and a record that covered fifty are the same kind of thing,
#: and the number of call sites is what tells them apart.
CROSS_REFERENCE_CALL_COUNT = "call_count"


def cross_reference_records(evidence: Sequence[Evidence]) -> int:
    """How many cross-reference records the analysis produced.

    One record per called method of the APK: a method called from fifty places
    is one conclusion, not fifty.
    """
    return sum(1 for item in evidence if item.kind is EvidenceKind.CROSS_REFERENCE)


def cross_reference_call_sites(evidence: Sequence[Evidence]) -> int:
    """How many indexed call sites a cross-reference record covers.

    This is the number the two reports state beside the number of indexed
    cross-references, and it has to be the same unit as that number.

    The indexed cross-references are call *edges* — one row per call — and a
    record covers the call sites of the method it is about. Summing the call
    sites the records cover therefore answers the question the report poses:
    how many of the indexed calls are backed by a record.

    A record that states no call count — one written by an older build, or one
    made by hand — counts as one call site: a record is made from at least one
    reference, so one is the smallest number it can honestly be.
    """
    total = 0
    for item in evidence:
        if item.kind is not EvidenceKind.CROSS_REFERENCE:
            continue
        count = item.detail.get(CROSS_REFERENCE_CALL_COUNT)
        total += count if isinstance(count, int) else 1
    return total


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
    resource_count: int = 0
    """How many resource strings the resource table held.

    Counted from the rows the ``resources`` table holds, the same way the
    other counts are: a number taken from the list that was handed in is a
    number the database cannot produce.
    """
    duration_seconds: float | None = None
    """How long the analysis took, in seconds.

    A measurement of *this run*, not a fact about the APK: the same bytes
    analysed on a faster machine take less time, and the number belongs to
    the run rather than to the project. It is therefore kept here and not on
    :class:`ApkMetadata`, which holds what the archive is.

    ``None`` means the run was never timed — a workspace written before the
    measurement was stored holds none. A report that printed ``0.0s`` for
    such a row would be claiming a measurement that was never taken, so the
    reports say that the time is unknown instead.
    """

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


# ---------------------------------------------------------------------------
# Resource strings
# ---------------------------------------------------------------------------


class ResourceKind(StrEnum):
    """What kind of resource declaration a string came from.

    The kind matters because the three are declared differently and mean
    different things: a ``<string>`` is one named piece of text, the items of a
    ``<string-array>`` share a name and differ only by position, and the items
    of a ``<plurals>`` differ by the quantity they answer.
    """

    STRING = "string"
    """A ``<string>`` element — one named piece of text."""

    STRING_ARRAY = "string_array"
    """One ``<item>`` of a ``<string-array>`` — text with no name of its own."""

    PLURAL = "plural"
    """One ``<item>`` of a ``<plurals>`` — the text for one quantity."""


class ResourceString(Sourced):
    """A string declared in the APK's resource table.

    The DEX string pool and the resource table are two different things, and
    they are indexed as two different things. A pool entry is a symbol the code
    loads; a resource is a declaration a person wrote, which the code may
    reference by id and never by value. A hard-coded key that lives in
    ``strings.xml`` is in neither the pool nor the code, and until the resource
    table was read it was in no index at all.

    One row per declaration site. The same text in two languages is two rows,
    because they are two declarations, and each points at its own file.
    """

    name: str
    """The resource name, e.g. ``app_name``."""

    value: str
    """The text itself."""

    kind: ResourceKind = ResourceKind.STRING
    """Which element the text was declared in."""

    quantity: str | None = None
    """The plural quantity this text answers, e.g. ``other``.

    Set only for the items of a ``<plurals>``; every other kind leaves it
    empty.
    """

    position: int = 0
    """Where the text sits inside its declaration, counting from zero.

    The items of a ``<string-array>`` share a name and differ only by
    position, so the position is part of what makes a row a distinct row: two
    items of the same array are two declarations, not one declaration read
    twice. Every kind that is not an array or a plural leaves it at zero.
    """

    qualifier: str | None = None
    """The values-directory qualifier, e.g. ``zh`` for ``res/values-zh/``.

    ``None`` for the unqualified ``res/values/`` directory. A qualifier is
    part of a resource's identity: the same name in two languages is two
    resources, and only one of them is the default.
    """

    file: str = ""
    """The file the text was declared in, relative to Apktool's output tree.

    The same path the provenance locator names, without the ``apktool:``
    prefix — a locator is a pointer, this is the place it points at.
    """

    @property
    def qualified_name(self) -> str:
        """The resource name, qualified when it is not the default one."""
        if self.qualifier:
            return f"{self.name} ({self.qualifier})"
        return self.name


# ---------------------------------------------------------------------------
# Source documents
# ---------------------------------------------------------------------------


class SourceKind(StrEnum):
    """Which representation a source document holds."""

    JAVA = "java"
    """Decompiled Java, written by JADX."""

    SMALI = "smali"
    """Dalvik bytecode, disassembled by Apktool.

    The fallback for a method the decompiler could not reconstruct. It is not a
    worse kind of source — it is closer to the original fact — but a reader has
    to know which one they are looking at.
    """


class SourceDocument(Sourced):
    """One class's or method's source, and where it came from.

    A bare string cannot say which of the two representations it is, so the
    answer to "is this Java or Smali?" has to travel with the text. The
    provenance says which tool produced it, at what version, and in which file
    of that tool's output tree it lives.
    """

    text: str
    """The source itself — Java, or Smali."""

    kind: SourceKind
    """Which representation it is."""

    @property
    def tool(self) -> str:
        """The tool that produced it, or an empty string when nothing did."""
        return self.provenance[0].tool if self.provenance else ""
