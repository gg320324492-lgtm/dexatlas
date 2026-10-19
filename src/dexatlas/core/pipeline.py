"""The analysis pipeline.

One orchestrator, shared by the CLI and the REST API — a claim the roadmap makes and
this class exists to keep true. Neither entry point contains analysis logic of its own.

Backends run independently and none can abort the run: each step records its own
:class:`ToolError`, and the project is still persisted. An APK that defeats JADX still
yields a manifest, a symbol index and a report.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from dexatlas.config.settings import Settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.ingest import ApkValidationError, inspect_apk
from dexatlas.core.models import (
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    FieldRef,
    ManifestInfo,
    MethodRef,
    MethodReference,
    Project,
    ProjectStatus,
    StringConstant,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.storage import Store
from dexatlas.tools.androguard.adapter import AndroguardBackend
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend
from dexatlas.tools.registry import BackendRegistry

logger = logging.getLogger(__name__)

#: Evidence covers a sample of classes, not all of them — an obfuscated APK has
#: hundreds of thousands and a per-class evidence row would dwarf the findings.
MAX_EVIDENCE_CLASSES = 500


@dataclass(slots=True)
class AnalysisResult:
    """Everything one analysis run produced."""

    project: Project
    manifest: ManifestInfo | None
    evidence: list[Evidence] = field(default_factory=list)
    workspace: Path | None = None
    duration_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.project.status == ProjectStatus.COMPLETED


class Analyzer:
    """Runs the APK → manifest + symbols + evidence pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        from dexatlas.config.settings import get_settings

        self._settings = settings or get_settings()
        self._settings.ensure_workspace()
        self._store = Store.open(self._settings.database_path)

        # Typed handles: each step below calls backend-specific methods, so the
        # pipeline reads as backend usage rather than as casts.
        self._jadx = JadxBackend(self._settings)
        self._apktool = ApktoolBackend(self._settings)
        self._androguard = AndroguardBackend(self._settings)
        self._backends = BackendRegistry(
            self._settings, [self._jadx, self._apktool, self._androguard]
        )

    @property
    def store(self) -> Store:
        return self._store

    @property
    def backends(self) -> BackendRegistry:
        return self._backends

    def analyze(
        self,
        apk_path: Path,
        *,
        include_jadx: bool = True,
        include_apktool: bool = True,
        include_androguard: bool = True,
    ) -> AnalysisResult:
        """Analyse an APK end to end.

        Raises :class:`ApkValidationError` only when the input is not an APK at all.
        Every later failure is recorded on the project instead of raised.
        """
        started = time.monotonic()
        apk = inspect_apk(apk_path)
        project = Project.create(apk)
        workspace = self._settings.projects_dir / project.id

        self._store.save_project(project, workspace, manifest=None)
        self._store.set_status(project.id, ProjectStatus.RUNNING)

        builder = EvidenceBuilder(project_id=project.id, apk_sha256=apk.sha256)
        project.tool_versions = self._backends.versions()

        manifest: ManifestInfo | None = None
        classes: list[ClassRef] = []
        methods: list[MethodRef] = []
        fields: list[FieldRef] = []
        references: list[MethodReference] = []
        strings: list[StringConstant] = []

        if include_apktool:
            manifest, apktool_classes, error = self._run_apktool(project, workspace, builder)
            classes.extend(apktool_classes)
            if error is not None:
                project.errors.append(error)
            if manifest is not None:
                # The manifest's findings come before the code's index: an
                # exported component is a conclusion, and the report's evidence
                # table is capped, so what is recorded last is what gets dropped.
                builder.add_exported_components(manifest.components)

        if include_androguard:
            extracted = self._run_androguard(apk.path, project, builder)
            classes.extend(extracted[0])
            methods.extend(extracted[1])
            fields.extend(extracted[2])
            references.extend(extracted[3])
            strings.extend(extracted[4])
            if extracted[5] is not None:
                project.errors.append(extracted[5])

        if include_jadx:
            jadx_classes, error = self._run_jadx(apk.path, project, workspace, builder)
            classes.extend(jadx_classes)
            if error is not None:
                project.errors.append(error)

        classes = _merge_classes(classes)
        counts = self._store.save_symbols(project.id, classes, methods, fields, references, strings)

        evidence = builder.build()
        project.evidence_count = self._store.save_evidence(project.id, evidence)

        # The counts are the ones the tables hold. A count taken from the lists
        # that went in is a count of symbols the database never stored — a class
        # defined in two dex files is one row — and a report built on it
        # disagrees with every query run against it.
        project.class_count = counts.classes
        project.method_count = counts.methods
        project.reference_count = counts.references
        project.status = (
            ProjectStatus.FAILED if not classes and not manifest else ProjectStatus.COMPLETED
        )

        self._store.save_project(project, workspace, manifest)

        return AnalysisResult(
            project=project,
            manifest=manifest,
            evidence=evidence,
            workspace=workspace,
            duration_seconds=time.monotonic() - started,
        )

    # -- backend steps -----------------------------------------------------

    def _run_apktool(
        self, project: Project, workspace: Path, builder: EvidenceBuilder
    ) -> tuple[ManifestInfo | None, list[ClassRef], ToolError | None]:
        backend = self._apktool
        if not backend.available():
            error = backend.missing_error()
            builder.add_error(error)
            return None, [], error

        output_dir = workspace / "apktool"
        outcome = backend.decode(project.apk.path, output_dir)
        manifest, parse_error = backend.read_manifest(output_dir)

        classes: list[ClassRef] = []
        if outcome.error is not None:
            builder.add_error(outcome.error)
        if parse_error is not None:
            builder.add_error(parse_error)
        if manifest is not None:
            builder.add(
                kind=EvidenceKind.DECLARATION,
                level=EvidenceLevel.VERIFIED,
                summary=(
                    f"Package {manifest.package or '<unknown>'} "
                    f"(versionName={manifest.version_name}, minSdk={manifest.min_sdk}, "
                    f"targetSdk={manifest.target_sdk})"
                ),
                provenance=[backend.provenance(project.apk.sha256, "AndroidManifest.xml")],
                detail={
                    "permissions": [p.name for p in manifest.permissions],
                    "components": len(manifest.components),
                },
            )

        return manifest, classes, outcome.error or parse_error

    def _run_androguard(
        self, apk: Path, project: Project, builder: EvidenceBuilder
    ) -> tuple[
        list[ClassRef],
        list[MethodRef],
        list[FieldRef],
        list[MethodReference],
        list[StringConstant],
        ToolError | None,
    ]:
        classes, methods, fields, references, strings, error = self._androguard.extract(
            apk, project.apk.sha256
        )
        # A method defined in two dex files is one method with two sources, not
        # two methods. The symbol table keys on the method id, so the second
        # definition would replace the first and take its provenance with it —
        # which is how "this method lives in classes.dex" could be lost.
        methods = _merge_methods(methods)
        fields = _merge_fields(fields)

        if error is not None:
            builder.add_error(error)
        else:
            # Conclusions before the index. A cross-reference says something about
            # the code; a class declaration only says the class exists. The
            # report's evidence table is capped, so what is recorded last is what
            # gets dropped.
            builder.add_cross_references(methods, references)
            builder.add_classes(classes[:MAX_EVIDENCE_CLASSES])
            if len(classes) > MAX_EVIDENCE_CLASSES:
                logger.info(
                    "androguard: indexed %d classes; evidence covers the first %d",
                    len(classes),
                    MAX_EVIDENCE_CLASSES,
                )
        return classes, methods, fields, references, strings, error

    def _run_jadx(
        self, apk: Path, project: Project, workspace: Path, builder: EvidenceBuilder
    ) -> tuple[list[ClassRef], ToolError | None]:
        backend = self._jadx
        if not backend.available():
            error = backend.missing_error()
            builder.add_error(error)
            return [], error

        output_dir = workspace / "jadx"
        outcome = backend.decompile(apk, output_dir)
        classes, extract_error = backend.extract(project.apk.sha256, output_dir, outcome)
        if extract_error is not None:
            builder.add_error(extract_error)
        return classes, extract_error

    # -- queries -----------------------------------------------------------

    def class_source(self, project_id: str, class_name: str) -> str | None:
        """JADX's Java for a class, falling back to Apktool's Smali."""
        workspace = self._store.get_workspace(project_id)
        if workspace is None:
            return None

        if self._jadx.available():
            source = self._jadx.read_class_source(class_name, workspace / "jadx")
            if source is not None:
                return source

        if self._apktool.available():
            return self._apktool.read_smali(class_name, workspace / "apktool")
        return None

    def method_source(self, project_id: str, class_name: str, method_name: str) -> str | None:
        """One method's body, preferring decompiled Java and falling back to Smali."""
        workspace = self._store.get_workspace(project_id)
        if workspace is None:
            return None

        if self._jadx.available():
            source = self._jadx.read_method_source(class_name, method_name, workspace / "jadx")
            if source is not None:
                return source

        # Smali fallback: a method JADX cannot decompile is still present in bytecode.
        if not self._apktool.available():
            return None
        smali = self._apktool.read_smali(class_name, workspace / "apktool")
        return _extract_smali_method(smali, method_name) if smali else None

    def search(self, project_id: str, keyword: str, limit: int = 50) -> list[dict[str, object]]:
        return self._store.search(project_id, keyword, limit=limit)


def _extract_smali_method(smali: str, method_name: str) -> str | None:
    """Pull one ``.method`` block out of a Smali file."""
    block: list[str] = []
    inside = False
    for line in smali.splitlines():
        if line.startswith(".method"):
            inside = True
            block = [line]
            continue
        if not inside:
            continue
        block.append(line)
        if line.startswith(".end method"):
            inside = False
            if _smali_declares(block[0], method_name):
                return "\n".join(block)
    return None


def _smali_declares(header: str, method_name: str) -> bool:
    """Whether a ``.method`` header declares ``method_name``.

    Headers look like ``.method public static foo(Ljava/lang/String;)V``; the declared
    name is the last token up to the argument list.
    """
    tokens = header.split()
    return len(tokens) >= 2 and tokens[-1].split("(")[0] == method_name


def _merge_classes(classes: list[ClassRef]) -> list[ClassRef]:
    """Combine per-backend class views into one index, keeping every provenance entry.

    Backends disagree about a class's flags — Apktool knows the manifest declaration,
    Androguard the DEX definition. Both are kept; neither overwrites the other.
    """
    merged: dict[str, ClassRef] = {}
    for cls in classes:
        existing = merged.get(cls.name)
        if existing is None:
            merged[cls.name] = cls.model_copy(deep=True)
            continue
        merged[cls.name] = existing.model_copy(
            update={
                "kind": existing.kind if cls.kind.value == "class" else cls.kind,
                "superclass": existing.superclass or cls.superclass,
                "interfaces": sorted({*existing.interfaces, *cls.interfaces}),
                "access_flags": sorted({*existing.access_flags, *cls.access_flags}),
                "method_count": max(existing.method_count, cls.method_count),
                "field_count": max(existing.field_count, cls.field_count),
                "provenance": [*existing.provenance, *cls.provenance],
            }
        )
    return sorted(merged.values(), key=lambda c: c.name)


def _merge_methods(methods: list[MethodRef]) -> list[MethodRef]:
    """Combine the definitions of one method into one symbol.

    A class defined in two dex files yields two definitions of the same method.
    The symbol table keys on ``(class, name, descriptor)``, so the second
    definition would replace the first — and the method's own provenance, which
    dex file it came from, with it. Merging keeps every source, the way
    :func:`_merge_classes` keeps every backend's view of a class.
    """
    merged: dict[str, MethodRef] = {}
    for method in methods:
        key = method.qualified_name
        existing = merged.get(key)
        if existing is None:
            merged[key] = method.model_copy(deep=True)
            continue
        merged[key] = existing.model_copy(
            update={
                "access_flags": sorted({*existing.access_flags, *method.access_flags}),
                "signature": existing.signature or method.signature,
                # A body in either dex file is a body.
                "decompiled": existing.decompiled or method.decompiled,
                "provenance": [*existing.provenance, *method.provenance],
            }
        )
    return sorted(merged.values(), key=lambda m: m.qualified_name)


def _merge_fields(fields: list[FieldRef]) -> list[FieldRef]:
    """Combine the definitions of one field into one symbol.

    The same thing :func:`_merge_methods` does for methods: the field table keys
    on the field, so a field defined in two dex files is one row, and the row
    has to say so.
    """
    merged: dict[str, FieldRef] = {}
    for field_ref in fields:
        key = field_ref.qualified_name
        existing = merged.get(key)
        if existing is None:
            merged[key] = field_ref.model_copy(deep=True)
            continue
        merged[key] = existing.model_copy(
            update={
                "access_flags": sorted({*existing.access_flags, *field_ref.access_flags}),
                "constant_value": existing.constant_value or field_ref.constant_value,
                "provenance": [*existing.provenance, *field_ref.provenance],
            }
        )
    return sorted(merged.values(), key=lambda f: f.qualified_name)


__all__ = ["AnalysisResult", "Analyzer", "ApkValidationError", "ToolErrorCode"]
