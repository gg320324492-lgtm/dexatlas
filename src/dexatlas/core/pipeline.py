"""The analysis pipeline.

One orchestrator, shared by the CLI and the REST API — a claim the roadmap makes and
this class exists to keep true. Neither entry point contains analysis logic of its own.

Backends run independently and none can abort the run: each step records its own
:class:`ToolError`, and the project is still persisted. An APK that defeats JADX still
yields a manifest, a symbol index and a report. The analysis itself is not a backend:
when it fails, the project is left failed and the failure is raised to the caller.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from dexatlas.config.settings import Settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.ingest import ApkValidationError, inspect_apk
from dexatlas.core.methods import AmbiguousMethodError, MethodCandidate, simple_class_name
from dexatlas.core.models import (
    ANALYSIS_TOOL,
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
    canonical_descriptor,
)
from dexatlas.core.paths import redact_workspace
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

        Raises :class:`ApkValidationError` when the input is not an APK at
        all. A backend that cannot do its job is recorded on the project and
        the run carries on. A failure of the analysis itself leaves the
        project failed and is raised as :class:`AnalysisFailed`: a run that
        says nothing is not a run that found nothing.

        ``metadata`` is an inspection the caller has already done.
        """
        started = time.monotonic()
        apk = metadata if metadata is not None else inspect_apk(apk_path)
        project = Project.create(apk)
        workspace = self._settings.projects_dir / project.id

        self._store.save_project(project, workspace, manifest=None)
        self._store.set_status(project.id, ProjectStatus.RUNNING)

        try:
            # The versions are probed before the evidence is built, because the
            # evidence names the version of the tool that produced it. Probing
            # them once, here, keeps one answer for the project record and for
            # every evidence record.
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
            dex_classes: list[ClassRef] = []

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
                # The classes the DEX reader found. The evidence declares these
                # and not the decompiler's: the DEX reader is the one that read
                # the class definitions out of the bytecode.
                dex_classes = extracted[0]
                classes.extend(dex_classes)
                methods.extend(extracted[1])
                fields.extend(extracted[2])
                references.extend(extracted[3])
                strings.extend(extracted[4])
                if extracted[5] is not None:
                    project.errors.append(extracted[5])

            if include_jadx:
                jadx_classes, error, jadx_status = self._run_jadx(
                    apk.path, project, workspace, builder
                )
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

            # The class declarations are the index, not a conclusion: a class
            # declaration says the class exists, and a report of an APK with two
            # thousand classes is mostly an index. They are therefore recorded
            # last, after the conclusions — what the APK exports, how much of it
            # the decompiler could read — so that the conclusions are the records
            # that survive the report's cap on the evidence table. What is
            # recorded last is what gets dropped.
            builder.add_classes(dex_classes, limit=MAX_EVIDENCE_CLASSES)
            if len(dex_classes) > MAX_EVIDENCE_CLASSES:
                # The operator gets the same news the reader does: the evidence
                # holds a sample of the classes, and the report says so.
                logger.info(
                    "androguard: indexed %d classes; evidence covers the first %d",
                    len(dex_classes),
                    MAX_EVIDENCE_CLASSES,
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

            # The time the run took is measured once and stored, so that a report
            # exported later from the workspace states the number the report
            # written at the time stated.
            elapsed = time.monotonic() - started
            project.duration_seconds = elapsed
            self._store.save_project(project, workspace, manifest)

            return AnalysisResult(
                project=project,
                manifest=manifest,
                evidence=evidence,
                workspace=workspace,
                duration_seconds=elapsed,
            )
        except Exception as exc:
            # The analysis failed. The project is left failed — never running —
            # and the reason is recorded on it, so that the failure is in the
            # database as well as in the exception the caller is about to get.
            raise AnalysisFailed(self._record_failure(project, workspace, exc)) from exc
        except BaseException:
            # A keyboard interrupt or a shutdown is not an analysis failure,
            # and it is not swallowed either. The run is over, though, and the
            # project must not be left running: the API finds a project by the
            # APK's hash and hands it back as it is.
            self._record_failure(project, workspace, None)
            raise

    def _record_failure(
        self, project: Project, workspace: Path, exc: BaseException | None
    ) -> ToolError:
        """Leave the project failed, and say what failed.

        A project that is left running is a project that is never coming back:
        the API finds it by the APK's hash and hands it back as it is, so an
        analysis that died half way through would be reported as an analysis
        that is still going. The failure is therefore recorded on the project
        before the exception goes on to the caller.

        The failure is recorded as a :class:`ToolError` of DexAtlas itself,
        not of a backend: no backend failed, the analysis did. A backend's
        own failure is recorded by its own adapter, under the backend's name.

        The message is redacted here, where it is written. An exception's
        message can quote the path it was handed -- a file that was not
        there, a directory that could not be created -- and that path is the
        server's. The message is read back through the API, through the JSON
        report and through the Markdown report, so redacting it at each of
        those would be three chances to forget one.
        """
        if exc is None:
            message = "the analysis did not complete: it was interrupted"
        else:
            message = f"the analysis did not complete: {type(exc).__name__}"
            if str(exc):
                message = f"{message}: {exc}"
        redacted = redact_workspace(message, self._settings.workspace, workspace)
        message = redacted if redacted is not None else message

        error = ToolError(
            tool=ANALYSIS_TOOL,
            code=ToolErrorCode.ANALYSIS_FAILED,
            message=message,
        )
        project.status = ProjectStatus.FAILED
        project.errors.append(error)
        try:
            self._store.save_project(project, workspace, manifest=None)
        except Exception:
            # The workspace is what failed, most likely. The failure still has
            # to reach the caller, and the log is where it can be read.
            logger.exception("could not record the analysis failure on %s", project.id)
        return error

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
        # gets dropped — which is why the class declarations are recorded by
        # the caller, after the decompiler has had its say.
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

    def method_source(
        self,
        project_id: str,
        class_name: str,
        method_name: str | None = None,
        descriptor: str | None = None,
    ) -> str | None:
        """One method's body, preferring decompiled Java and falling back to Smali.

        As with :meth:`class_source`, the text does not say where it came from;
        :meth:`method_source_document` does.
        """
        document = self.method_source_document(project_id, class_name, method_name, descriptor)
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
        self,
        project_id: str,
        class_name: str,
        method_name: str | None = None,
        descriptor: str | None = None,
    ) -> SourceDocument | None:
        """One method's body, and which backend produced it.

        The Smali fallback is the case this exists for: a method the decompiler
        could not reconstruct is still readable as bytecode, and a reader who is
        not told that is looking at Smali will read it as Java.

        A name that matches more than one method is an error rather than a
        choice: the body of the wrong overload reads like evidence, and an
        agent that quotes it quotes the wrong method. The error names the
        candidates, so the caller can ask again with a descriptor.
        """
        context = self._source_context(project_id)
        if context is None:
            return None
        project, workspace = context

        identity = self._resolve_method(project_id, class_name, method_name, descriptor)
        fragment = _method_fragment(identity)

        # A decompiled signature can be ambiguous where the bytecode is not — a
        # decompiler that could not work out a parameter type writes the same
        # name twice. The bytecode carries the descriptor, so the fallback is
        # tried before the ambiguity is reported.
        ambiguity: AmbiguousMethodError | None = None
        if self._jadx.available():
            output_dir = workspace / "jadx"
            try:
                source = self._jadx.read_method_source(
                    class_name,
                    identity.name,
                    output_dir,
                    identity.descriptor,
                    constructor=identity.constructor,
                )
                if source is None and identity.unique:
                    # The source does not spell this method's signature — a
                    # decompiler that wrote the parameters differently, or a
                    # type it could not work out. The index says the name is
                    # one method of the class, so the one declaration of that
                    # name is the method, and the signature that disagrees
                    # with it is a spelling.
                    source = self._jadx.read_method_source(
                        class_name,
                        identity.name,
                        output_dir,
                        None,
                        constructor=identity.constructor,
                    )
            except AmbiguousMethodError as exc:
                ambiguity = exc
            else:
                path = self._jadx.class_source_path(class_name, output_dir)
                if source is not None and path is not None:
                    locator = f"{source_locator(output_dir, path)}#{fragment}"
                    return SourceDocument(
                        text=source,
                        kind=SourceKind.JAVA,
                        descriptor=identity.descriptor,
                        provenance=[self._source_provenance(project, "jadx", locator)],
                    )

        # Smali fallback: a method JADX cannot decompile is still present in bytecode.
        if not self._apktool.available():
            if ambiguity is not None:
                raise ambiguity
            return None
        output_dir = workspace / "apktool"
        smali = self._apktool.read_smali(class_name, output_dir)
        path = self._apktool.smali_path(class_name, output_dir)
        if not smali or path is None:
            if ambiguity is not None:
                raise ambiguity
            return None
        body = _extract_smali_method(smali, identity, class_name)
        if body is None:
            if ambiguity is not None:
                raise ambiguity
            return None
        locator = f"{apktool_source_locator(output_dir, path)}#{fragment}"
        return SourceDocument(
            text=body,
            kind=SourceKind.SMALI,
            descriptor=identity.descriptor,
            provenance=[self._source_provenance(project, "apktool", locator)],
        )

    def _resolve_method(
        self,
        project_id: str,
        class_name: str,
        method_name: str | None,
        descriptor: str | None,
    ) -> _MethodIdentity:
        """Which method a request is about, as far as it can be pinned down.

        The symbol index is the authority: it holds the DEX names and
        descriptors of the methods the APK really has. A name that matches
        several of them is an ambiguity, and the error says which — the
        caller can then ask again with a descriptor. When the index does not
        hold the method the request falls back to the source, which knows the
        names but not the descriptors.
        """
        indexed = self._store.list_methods(project_id, class_name)
        if descriptor is not None:
            target = canonical_descriptor(descriptor)
            matching = [method for method in indexed if method.descriptor == target]
            if method_name is not None:
                # The DEX name is the precise reading of the name, and a
                # descriptor alongside it is a pair the index holds: an agent
                # that read a method out of the symbol table has exactly that
                # pair, and asking with it has to reach the method it names.
                #
                # A constructor is written under the class's own name in Java,
                # so that name is accepted too — but only when nothing in the
                # index answers to it under its DEX name, because an obfuscated
                # class can have a method called exactly what the class is
                # called, and the two have to stay apart.
                by_dex_name = [method for method in matching if method.name == method_name]
                if by_dex_name:
                    matching = by_dex_name
                else:
                    matching = [
                        method
                        for method in matching
                        if method.name == "<init>" and method_name == simple_class_name(class_name)
                    ]
            if len(matching) == 1:
                return _identity_of(matching[0], target, indexed, class_name)
            if len(matching) > 1:
                raise AmbiguousMethodError(class_name, method_name or "", _candidates_of(matching))
            return _MethodIdentity(method_name or "", target, None, False)

        if method_name is None:
            return _MethodIdentity("", None, None, False)

        matching = [
            method for method in indexed if _method_is_named(method, class_name, method_name)
        ]
        if len(matching) > 1:
            raise AmbiguousMethodError(class_name, method_name, _candidates_of(matching))
        if len(matching) == 1:
            # The index says one method answers to this name, and it holds that
            # method's descriptor. The descriptor is what the source is matched
            # against: a name is not a method, and the index is the one place
            # that knows which method this name is.
            return _identity_of(matching[0], matching[0].descriptor, indexed, class_name)
        return _MethodIdentity(method_name, None, None, False)

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


@dataclass(frozen=True, slots=True)
class _MethodIdentity:
    """The method a request is about, as far as it could be pinned down."""

    name: str
    """The DEX method name, or the caller's name when the index could not say."""

    descriptor: str | None
    """The DEX descriptor, when it is known."""

    constructor: bool | None
    """Whether the method is the class's constructor.

    ``None`` when the request did not say and the index could not tell: the
    constructor and a method of the same name are then both candidates.
    """

    unique: bool = False
    """Whether the index holds exactly one method under this name.

    The index is the authority on which methods a class has, so a name that
    answers to one of them has one declaration in the source as well — and a
    decompiler that spelled the signature differently has not made it another
    method. The source may then be asked for the name when it cannot be asked
    for the descriptor.
    """


def _identity_of(
    method: MethodRef,
    descriptor: str | None,
    indexed: list[MethodRef],
    class_name: str,
) -> _MethodIdentity:
    """The identity of an indexed method.

    The descriptor is the one the source has to match, and it is not always
    the one the index holds: a name that answers to one method is found by
    that name, and only a name that several methods share needs a descriptor
    to tell them apart.
    """
    named = [other for other in indexed if _method_is_named(other, class_name, method.name)]
    return _MethodIdentity(
        name=method.name,
        descriptor=descriptor,
        constructor=method.name == "<init>",
        unique=len(named) == 1,
    )


def _method_fragment(identity: _MethodIdentity) -> str:
    """How a method is named in a provenance locator.

    A name is not a method, so the descriptor is part of the name when it is
    known: two overloads share a name, and a locator that named only the name
    would point at both of them. This is the spelling the symbol table uses
    for a method, and the Androguard locator already carries it.
    """
    if identity.descriptor is not None:
        return f"{identity.name}{identity.descriptor}"
    return identity.name


def _candidates_of(methods: list[MethodRef]) -> list[MethodCandidate]:
    """The candidates an ambiguous name matched, with their exact descriptors."""
    return [
        MethodCandidate(
            name=method.name,
            descriptor=method.descriptor,
            signature=f"{method.name}{method.descriptor}",
        )
        for method in methods
    ]


def _method_is_named(method: MethodRef, class_name: str, method_name: str) -> bool:
    """Whether an indexed method is the one a request names.

    A constructor is written under the class's own name in Java, so a request
    for that name is a request for the constructor — and an obfuscated class
    can have a method of exactly that name too, which makes the request
    ambiguous rather than answered.
    """
    if method.name == method_name:
        return True
    return method.name == "<init>" and method_name == simple_class_name(class_name)


def _smali_names(identity: _MethodIdentity, class_name: str) -> set[str]:
    """The DEX names a request could be about.

    A constructor is written under the class's own name in Java, so a request
    for that name is a request for the constructor — and a request that could
    be about either is about both.
    """
    if identity.constructor is True:
        return {"<init>"}
    names = {identity.name}
    if identity.constructor is None and identity.name == simple_class_name(class_name):
        names.add("<init>")
    return names


def _extract_smali_method(smali: str, identity: _MethodIdentity, class_name: str) -> str | None:
    """Pull one ``.method`` block out of a Smali file.

    A Smali header carries the DEX descriptor, so a request that knows one
    matches exactly. A request that does not is matched by name, and a name
    several blocks share is an ambiguity rather than a choice.
    """
    wanted = _smali_names(identity, class_name)
    found: list[tuple[str, str, str]] = []
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
            declared = _smali_signature(block[0])
            if declared is None:
                continue
            name, descriptor = declared
            if name not in wanted:
                continue
            if identity.descriptor is not None and descriptor != identity.descriptor:
                continue
            found.append((name, descriptor, "\n".join(block)))
    if not found:
        return None
    if len(found) > 1:
        raise AmbiguousMethodError(
            class_name,
            identity.name,
            [
                MethodCandidate(name=name, descriptor=descriptor, signature=f"{name}{descriptor}")
                for name, descriptor, _body in found
            ],
        )
    return found[0][2]


def _smali_signature(header: str) -> tuple[str, str] | None:
    """The DEX name and descriptor a ``.method`` header declares.

    Headers look like ``.method public static foo(Ljava/lang/String;)V``; the
    declared name and descriptor are the last token, and the descriptor is
    what tells two overloads apart.
    """
    tokens = header.split()
    if len(tokens) < 2:
        return None
    last = tokens[-1]
    open_paren = last.find("(")
    if open_paren == -1:
        return None
    descriptor = last[open_paren:]
    if ")" not in descriptor:
        return None
    return last[:open_paren], descriptor


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


# ---------------------------------------------------------------------------
# The failure of the analysis, and its measurement
# ---------------------------------------------------------------------------


class AnalysisFailed(Exception):
    """The analysis did not complete.

    Raised when the analysis itself fails — a step raises, or the workspace
    cannot be written. A backend that cannot do its job is *not* this: that
    is recorded on the project and the run carries on without it.

    The failure is recorded on the project before this is raised, so the
    project is never left running and the reason is in the database as well
    as in the exception. The error it was recorded as travels with it, so a
    caller can report the same thing the report would say.
    """

    def __init__(self, error: ToolError) -> None:
        super().__init__(error.message)
        self.error = error
        """The failure, as it was recorded on the project."""


def analysis_duration(result: AnalysisResult) -> float | None:
    """How long the analysis took, in seconds — or ``None`` when it is unknown.

    The project's own measurement is the one the reports state: it is the
    number that was stored with the analysis, so a report exported later out
    of the workspace states the same number the report written at the time
    stated. The result's own value is the fallback for a result that was
    built by hand rather than read back out of a workspace.

    Zero is not a duration. An analysis takes time, so a run that reports
    none was never timed — a workspace written before the measurement was
    stored holds none — and the reports say that the time is unknown rather
    than print a number the run never produced.
    """
    stored = result.project.duration_seconds
    if stored is not None:
        return stored
    measured = result.duration_seconds
    return measured if measured else None


__all__ = [
    "AnalysisFailed",
    "AnalysisResult",
    "Analyzer",
    "ApkValidationError",
    "ToolErrorCode",
    "analysis_duration",
]
