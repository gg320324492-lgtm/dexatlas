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

from pydantic import BaseModel, ConfigDict, Field

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
    field_count: int = 0

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
    """JVM descriptor, e.g. ``(Ljava/lang/String;)V``. Stable across backends."""

    access_flags: list[str] = Field(default_factory=list)
    signature: str | None = None
    decompiled: bool = False
    """False when the backend has the symbol but could not produce a body."""

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

    @property
    def qualified_name(self) -> str:
        return f"{self.class_name}.{self.name}:{self.descriptor}"


class MethodReference(Sourced):
    """An edge: caller method invokes callee method."""

    caller: str
    callee: str
    kind: str = "invoke"
    """``invoke``, ``virtual``, ``direct``, ``interface`` or ``dynamic``."""


class StringConstant(Sourced):
    """A string literal found in the DEX or resources."""

    value: str
    class_name: str | None = None
    method_name: str | None = None


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
