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
    DECOMPILATION_DETAIL,
    ApkMetadata,
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
    Provenance,
    ResourceString,
    SourceDocument,
    SourceKind,
    StringConstant,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.storage import Store
from dexatlas.tools.androguard.adapter import AndroguardBackend
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.apktool.adapter import source_locator as apktool_source_locator
from dexatlas.tools.jadx.adapter import ClassDecompilation, JadxBackend, source_locator
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
        metadata: ApkMetadata | None = None,
        include_jadx: bool = True,
        include_apktool: bool = True,
        include_androguard: bool = True,
    ) -> AnalysisResult:
        """Analyse an APK end to end.

        Raises :class:`ApkValidationError` only when the input is not an APK at all.
        Every later failure is recorded on the project instead of raised.

        ``metadata`` is an inspection the caller has already done, so an APK that
        was inspected twice is not inspected twice.
        """
        started = time.monotonic()
        apk = metadata if metadata is not None else inspect_apk(apk_path)
        project = Project.create(apk)
        workspace = self._settings.projects_dir / project.id

        self._store.save_project(project, workspace, manifest=None)
        self._store.set_status(project.id, ProjectStatus.RUNNING)

        # The versions are probed before the evidence is built, because the
        # evidence names the version of the tool that produced it. Probing them
        # once, here, keeps one answer for the project record and for every
        # evidence record.
        project.tool_versions = self._backends.versions()
        builder = EvidenceBuilder(
            project_id=project.id,
            tool_versions=project.tool_versions,
            apk_sha256=apk.sha256,
        )

        manifest: ManifestInfo | None = None
        classes: list[ClassRef] = []
        methods: list[MethodRef] = []
        fields: list[FieldRef] = []
        references: list[MethodReference] = []
        strings: list[StringConstant] = []
        resources: list[ResourceString] = []

        if include_apktool:
            manifest, apktool_resources, errors = self._run_apktool(project, workspace, builder)
            resources.extend(apktool_resources)
            for apktool_error in errors:
                project.errors.append(apktool_error)
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
            jadx_classes, error, jadx_status = self._run_jadx(apk.path, project, workspace, builder)
            classes.extend(jadx_classes)
            if error is not None:
                project.errors.append(error)
            # The decompiler is the only backend that can say whether a method
            # was decompiled, so the flag is set here — after JADX has run, and
            # before the symbols are written.
            _apply_decompilation(methods, jadx_status)
            _record_decompilation(
                builder,
                project=project,
                classes=classes,
                methods=methods,
                status=jadx_status,
                output_dir=workspace / "jadx",
            )

        classes = _merge_classes(classes)
        counts = self._store.save_symbols(
            project.id, classes, methods, fields, references, strings, resources
        )

        evidence = builder.build()
        project.evidence_count = self._store.save_evidence(project.id, evidence)

        # The counts are the ones the tables hold. A count taken from the lists
        # that went in is a count of symbols the database never stored — a class
        # defined in two dex files is one row — and a report built on it
        # disagrees with every query run against it.
        project.class_count = counts.classes
        project.method_count = counts.methods
        project.reference_count = counts.references
        project.resource_count = counts.resources
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
    ) -> tuple[ManifestInfo | None, list[ResourceString], list[ToolError]]:
        """Apktool's share of the run: the manifest, the resources and the Smali.

        No classes come back, and that is the truth about the backend rather
        than an omission: Apktool reads the manifest, the resource table and
        the disassembled bytecode, and the classes in the index are described
        by Androguard and JADX. The Smali is read on demand, when a caller
        asks for source the decompiler did not produce.
        """
        backend = self._apktool
        if not backend.available():
            error = backend.missing_error()
            builder.add_error(error)
            return None, [], [error]

        output_dir = workspace / "apktool"
        outcome = backend.decode(project.apk.path, output_dir)
        manifest, parse_error = backend.read_manifest(output_dir)
        resources, resource_errors = backend.read_resources(output_dir, project.apk.sha256)

        errors: list[ToolError] = []
        if outcome.error is not None:
            builder.add_error(outcome.error)
            errors.append(outcome.error)
        if parse_error is not None:
            builder.add_error(parse_error)
            errors.append(parse_error)
        for error in resource_errors:
            # A resource table that could not be read is a gap in the index, and
            # a gap that is not recorded reads like an absence of resources.
            builder.add_error(error)
            errors.append(error)
        if manifest is not None:
            builder.add(
                kind=EvidenceKind.DECLARATION,
                level=EvidenceLevel.VERIFIED,
                summary=(
                    f"Package {manifest.package or '<unknown>'} "
                    f"(versionName={manifest.version_name}, minSdk={manifest.min_sdk}, "
                    f"targetSdk={manifest.target_sdk})"
                ),
                provenance=[backend.provenance(project.apk.sha256, "apktool:AndroidManifest.xml")],
                detail={
                    "permissions": [p.name for p in manifest.permissions],
                    "components": len(manifest.components),
                },
            )

        return manifest, resources, errors

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
        # Conclusions before the index. A cross-reference says something about
        # the code; a class declaration only says the class exists. The
        # report's evidence table is capped, so what is recorded last is what
        # gets dropped.
        #
        # The evidence is built from what came back, whether or not something
        # went wrong. Every one of those rows was read out of the bytecode, so
        # it holds — a row that was read is a fact, whatever else failed.
        #
        # A DEX file that could not be parsed contributes nothing at all: it
        # was skipped, so its classes and its call edges are *missing* from the
        # index rather than wrong in it. That is a gap, and the report says so
        # — but it is not a reason to withhold the evidence of the DEX files
        # that were read. Treating one broken DEX file as a reason to draw no
        # conclusion from the whole APK threw away facts that were true: the
        # classes of the DEX file that parsed really do exist, and the calls
        # really are in the bytecode.
        builder.add_cross_references(methods, references)
        builder.add_classes(classes, limit=MAX_EVIDENCE_CLASSES)
        if len(classes) > MAX_EVIDENCE_CLASSES:
            # The operator gets the same news the reader does: the evidence
            # holds a sample of the classes, and the report says so.
            logger.info(
                "androguard: indexed %d classes; evidence covers the first %d",
                len(classes),
                MAX_EVIDENCE_CLASSES,
            )
        return classes, methods, fields, references, strings, error

    def _run_jadx(
        self, apk: Path, project: Project, workspace: Path, builder: EvidenceBuilder
    ) -> tuple[list[ClassRef], ToolError | None, dict[str, ClassDecompilation]]:
        backend = self._jadx
        if not backend.available():
            error = backend.missing_error()
            builder.add_error(error)
            return [], error, {}

        output_dir = workspace / "jadx"
        outcome = backend.decompile(apk, output_dir)
        classes, extract_error = backend.extract(project.apk.sha256, output_dir, outcome)
        if extract_error is not None:
            builder.add_error(extract_error)
        return classes, extract_error, backend.decompilation_status(output_dir)

    # -- queries -----------------------------------------------------------

    def class_source(self, project_id: str, class_name: str) -> str | None:
        """JADX's Java for a class, falling back to Apktool's Smali.

        The text alone does not say which of the two it is. A caller that has to
        know — because it renders the source, or cites it — should use
        :meth:`class_source_document`, which carries the provenance with it.
        """
        document = self.class_source_document(project_id, class_name)
        return document.text if document is not None else None

    def method_source(self, project_id: str, class_name: str, method_name: str) -> str | None:
        """One method's body, preferring decompiled Java and falling back to Smali.

        As with :meth:`class_source`, the text does not say where it came from;
        :meth:`method_source_document` does.
        """
        document = self.method_source_document(project_id, class_name, method_name)
        return document.text if document is not None else None

    def class_source_document(self, project_id: str, class_name: str) -> SourceDocument | None:
        """A class's source, and which backend produced it.

        JADX's Java when the decompiler wrote one, Apktool's Smali when it did
        not. The provenance says which, so the caller never has to infer it from
        the shape of the text or from what happens to be in the workspace.

        The locator names the file inside the producing tool's own output tree,
        so it points at the artefact rather than at the machine that made it.
        """
        context = self._source_context(project_id)
        if context is None:
            return None
        project, workspace = context

        if self._jadx.available():
            output_dir = workspace / "jadx"
            source = self._jadx.read_class_source(class_name, output_dir)
            path = self._jadx.class_source_path(class_name, output_dir)
            if source is not None and path is not None:
                return SourceDocument(
                    text=source,
                    kind=SourceKind.JAVA,
                    provenance=[
                        self._source_provenance(project, "jadx", source_locator(output_dir, path))
                    ],
                )

        if self._apktool.available():
            output_dir = workspace / "apktool"
            source = self._apktool.read_smali(class_name, output_dir)
            path = self._apktool.smali_path(class_name, output_dir)
            if source is not None and path is not None:
                return SourceDocument(
                    text=source,
                    kind=SourceKind.SMALI,
                    provenance=[
                        self._source_provenance(
                            project, "apktool", apktool_source_locator(output_dir, path)
                        )
                    ],
                )
        return None

    def method_source_document(
        self, project_id: str, class_name: str, method_name: str
    ) -> SourceDocument | None:
        """One method's body, and which backend produced it.

        The Smali fallback is the case this exists for: a method the decompiler
        could not reconstruct is still readable as bytecode, and a reader who is
        not told that is looking at Smali will read it as Java.
        """
        context = self._source_context(project_id)
        if context is None:
            return None
        project, workspace = context

        if self._jadx.available():
            output_dir = workspace / "jadx"
            source = self._jadx.read_method_source(class_name, method_name, output_dir)
            path = self._jadx.class_source_path(class_name, output_dir)
            if source is not None and path is not None:
                locator = f"{source_locator(output_dir, path)}#{method_name}"
                return SourceDocument(
                    text=source,
                    kind=SourceKind.JAVA,
                    provenance=[self._source_provenance(project, "jadx", locator)],
                )

        # Smali fallback: a method JADX cannot decompile is still present in bytecode.
        if not self._apktool.available():
            return None
        output_dir = workspace / "apktool"
        smali = self._apktool.read_smali(class_name, output_dir)
        path = self._apktool.smali_path(class_name, output_dir)
        if not smali or path is None:
            return None
        body = _extract_smali_method(smali, method_name)
        if body is None:
            return None
        locator = f"{apktool_source_locator(output_dir, path)}#{method_name}"
        return SourceDocument(
            text=body,
            kind=SourceKind.SMALI,
            provenance=[self._source_provenance(project, "apktool", locator)],
        )

    def _source_context(self, project_id: str) -> tuple[Project, Path] | None:
        """The project and its workspace, when both are still there."""
        project = self._store.get_project(project_id)
        workspace = self._store.get_workspace(project_id)
        if project is None or workspace is None:
            return None
        return project, workspace

    def _source_provenance(self, project: Project, tool: str, locator: str) -> Provenance:
        """The provenance of a source read out of a stored workspace.

        The version is the one the *analysis* recorded, not the one installed
        now. The file on disk was written by the tool that ran then; a
        decompiler upgraded since would otherwise be credited with it.
        """
        return Provenance(
            tool=tool,
            tool_version=project.tool_versions.get(tool),
            apk_sha256=project.apk.sha256,
            locator=locator,
        )

    def search(self, project_id: str, keyword: str, limit: int = 50) -> list[dict[str, object]]:
        return self._store.search(project_id, keyword, limit=limit)

    def resources(self, project_id: str, *, name: str | None = None) -> list[ResourceString]:
        """The resource strings indexed for a project."""
        return self._store.list_resources(project_id, name=name)


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

    Two backends produce class definitions, and both of them are kept: Androguard
    reads the DEX definition, and JADX reads the class it decompiled. Apktool
    produces no class rows at all — it reads the manifest, the resources and the
    Smali, and the Smali is read on demand rather than indexed.

    They do not disagree about a class's flags, because only one of them reports
    them: Androguard's access flags, superclass and interfaces are kept as they
    are, and what JADX adds is the kind, its own provenance, and a method count of
    its own. Where the two disagree about the kind, the one that is not a plain
    class wins — a class JADX could not classify is still what Androguard read.

    The method and field counts are *views*, not totals. A backend reads one dex
    file, so a class split across two dex files is seen partly by each of them,
    and neither view is the class's total — the largest of them is not either.
    The number the index stores is counted from the rows it wrote; see
    :meth:`dexatlas.core.storage.Store.save_symbols`.
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


# ---------------------------------------------------------------------------
# Decompilation status
# ---------------------------------------------------------------------------

#: Methods listed in a record's detail before truncating.
MAX_LISTED_METHODS = 50


def _apply_decompilation(
    methods: list[MethodRef], status: dict[str, ClassDecompilation]
) -> list[MethodRef]:
    """Mark the methods the decompiler produced Java for.

    The flag on a method says whether JADX turned it into Java, so only JADX
    can set it. A method in a class JADX never wrote has no decompiled source,
    and so has a method JADX wrote a placeholder for — the two are different
    facts, and the index keeps the difference.
    """
    for method in methods:
        entry = status.get(method.class_name.partition("$")[0])
        if entry is None:
            continue
        if entry.method_status(method.class_name, method.name) is True:
            method.decompiled = True
    return methods


def _record_decompilation(
    builder: EvidenceBuilder,
    *,
    project: Project,
    classes: list[ClassRef],
    methods: list[MethodRef],
    status: dict[str, ClassDecompilation],
    output_dir: Path,
) -> None:
    """Record how much of the APK the decompiler could read.

    "The decompiler failed on this class" is a fact about the analysis, and
    without it a reader cannot tell an APK that is mostly unreadable from one
    that is fully readable. It used to be nowhere: JADX wrote no log file, so
    the only trace of a failure was the placeholder in the Java, which nothing
    read.
    """
    if not status:
        return

    decompiled = [method for method in methods if method.decompiled]
    failed: list[str] = []
    for method in methods:
        entry = status.get(method.class_name.partition("$")[0])
        if entry is None:
            continue
        if entry.method_status(method.class_name, method.name) is False:
            failed.append(method.qualified_name)

    # A class the decompiler never wrote is a gap too, and it is invisible in
    # the method list: every one of its methods simply has no source.
    indexed = {cls.name for cls in classes}
    without_source = sorted(name for name in indexed if name.partition("$")[0] not in status)

    sources = output_dir / "sources"
    builder.add(
        kind=EvidenceKind.OBSERVATION,
        # The coverage is read out of the decompiler's own output, and that
        # output is a location a reader can open.
        level=EvidenceLevel.VERIFIED,
        summary=(
            f"jadx produced real Java for {len(decompiled)} of {len(methods)} methods "
            f"in {len(status)} of {len(indexed)} classes"
        ),
        provenance=[
            Provenance(
                tool="jadx",
                tool_version=project.tool_versions.get("jadx"),
                apk_sha256=project.apk.sha256,
                locator=source_locator(output_dir, sources),
            )
        ],
        detail={
            DECOMPILATION_DETAIL: {
                "methods_decompiled": len(decompiled),
                "methods_total": len(methods),
                "classes_with_source": len(status),
                "classes_total": len(indexed),
                "methods_jadx_failed": failed[:MAX_LISTED_METHODS],
                "methods_jadx_failed_truncated": len(failed) > MAX_LISTED_METHODS,
                "classes_without_source": without_source[:MAX_LISTED_METHODS],
                "classes_without_source_truncated": len(without_source) > MAX_LISTED_METHODS,
            }
        },
    )


__all__ = ["AnalysisResult", "Analyzer", "ApkValidationError", "ToolErrorCode"]
