"""How a question is put to DexAtlas.

Each probe is a small function that asks the analysis one question through its
own API and reports what came back. The API is used rather than the command
line because it is the same code path the command line and the REST API use —
``dexatlas.cli.main`` says so at the top of its module — and because it returns
the analysis's own objects instead of a table drawn for a terminal, which keeps
the checks free of anything to do with rendering.

A probe returns an :class:`~benchmarks.model.Answer`, and an answer with no
findings is a real answer: "there is nothing here" is what several of the
tasks are about, and the difference between that and a probe that failed to
run has to stay visible. So a probe that could not answer says so in its
note, and the note is never mistaken for evidence.
"""

from __future__ import annotations

from collections.abc import Sequence

from benchmarks.model import Answer, Context, Finding, Probe
from dexatlas.core.methods import AmbiguousMethodError
from dexatlas.core.models import ManifestInfo, MethodRef


def _manifest(ctx: Context) -> ManifestInfo | None:
    """The manifest the analysis recorded, or ``None`` when it recorded none."""
    return ctx.analyzer.store.get_manifest(ctx.project_id)


def manifest_value(attribute: str) -> Probe:
    """Ask the manifest for one of its own values.

    The attribute names are the ones :class:`~dexatlas.core.models.ManifestInfo`
    holds: ``package``, ``version_code``, ``version_name``, ``min_sdk`` and
    ``target_sdk``.
    """

    def probe(ctx: Context) -> Answer:
        info = _manifest(ctx)
        if info is None:
            return Answer(note="the analysis recorded no manifest")
        value = getattr(info, attribute, None)
        if value is None:
            return Answer(note=f"the manifest records no {attribute}")
        return Answer(findings=(Finding(text=f"{attribute}={value}"),))

    return probe


def manifest_permissions() -> Probe:
    """Ask the manifest for the permissions it declares."""

    def probe(ctx: Context) -> Answer:
        info = _manifest(ctx)
        if info is None:
            return Answer(note="the analysis recorded no manifest")
        findings = tuple(
            Finding(text=f"permission {permission.name}") for permission in info.permissions
        )
        return Answer(findings=findings, note=f"{len(findings)} permission(s) declared")

    return probe


def manifest_components(kind: str | None = None) -> Probe:
    """Ask the manifest for the components it declares.

    ``kind`` narrows the answer to one kind of component — ``activity``,
    ``service``, ``receiver`` — which is how a question like "does this APK
    declare a broadcast receiver?" is put.
    """

    def probe(ctx: Context) -> Answer:
        info = _manifest(ctx)
        if info is None:
            return Answer(note="the analysis recorded no manifest")
        components = info.components
        if kind is not None:
            components = [component for component in components if component.kind == kind]
        findings = tuple(
            Finding(
                text=(
                    f"{component.kind} {component.name} "
                    f"exported={component.exported} permission={component.permission}"
                ),
                locator=component.name,
            )
            for component in components
        )
        return Answer(findings=findings, note=f"{len(findings)} component(s) declared")

    return probe


def manifest_exported_components() -> Probe:
    """Ask the manifest for the components it exports."""

    def probe(ctx: Context) -> Answer:
        info = _manifest(ctx)
        if info is None:
            return Answer(note="the analysis recorded no manifest")
        findings = tuple(
            Finding(
                text=(
                    f"{component.kind} {component.name} "
                    f"permission={component.permission or 'no permission guard'}"
                ),
                locator=component.name,
            )
            for component in info.exported_components
        )
        return Answer(findings=findings, note=f"{len(findings)} exported component(s)")

    return probe


def callers(method_id: str) -> Probe:
    """Ask the cross-reference index who calls a method.

    The method id is the qualified name the index holds: the class, the name
    and the DEX descriptor. One finding is one call site, so a method called
    twice from the same place is two findings — which is the difference
    between a call site and a call edge.
    """

    def probe(ctx: Context) -> Answer:
        rows = ctx.analyzer.store.get_method_references(ctx.project_id, method_id)
        findings = tuple(
            Finding(
                text=(
                    f"{row.caller} -> {row.callee} "
                    f"({row.kind.value}, {row.dex_name or '-'}, offset {row.instruction_offset})"
                ),
                locator=row.provenance[0].locator if row.provenance else "",
            )
            for row in rows
        )
        return Answer(
            findings=findings,
            note=f"{len(findings)} call site(s) of {method_id}",
        )

    return probe


def search_results(keyword: str) -> Probe:
    """Ask the search index for a term."""

    def probe(ctx: Context) -> Answer:
        rows = ctx.analyzer.search(ctx.project_id, keyword)
        findings = tuple(
            Finding(text=f"{row['kind']} {row['name']} :: {row['excerpt']}") for row in rows
        )
        return Answer(
            findings=findings,
            note=f"{len(findings)} hit(s) for {keyword!r}",
        )

    return probe


def resource_rows(name: str | None = None) -> Probe:
    """Ask the resource index for the strings the APK's resource table declares."""

    def probe(ctx: Context) -> Answer:
        rows = ctx.analyzer.resources(ctx.project_id, name=name)
        findings = tuple(
            Finding(
                text=f"{row.qualified_name}={row.value!r} kind={row.kind.value} file={row.file}",
                locator=row.provenance[0].locator if row.provenance else "",
            )
            for row in rows
        )
        return Answer(findings=findings, note=f"{len(findings)} resource string(s)")

    return probe


def indexed_classes() -> Probe:
    """Ask the symbol index for the classes it holds.

    The text carries every source the class has, so that a question about
    which DEX file a class came from can be asked of the index.
    """

    def probe(ctx: Context) -> Answer:
        rows = ctx.analyzer.store.list_classes(ctx.project_id)
        findings = tuple(
            Finding(
                text=(
                    f"{row.name} kind={row.kind.value} methods={row.method_count} "
                    f"sources={';'.join(source.locator for source in row.provenance) or '-'}"
                ),
                locator=row.provenance[0].locator if row.provenance else "",
            )
            for row in rows
        )
        return Answer(findings=findings, note=f"{len(findings)} indexed class(es)")

    return probe


def classes_from_dex(dex_name: str) -> Probe:
    """Ask which classes the index holds that came from one DEX file.

    A class defined in two DEX files is reported twice — once for each DEX it
    was found in — because "which classes are in classes2.dex" and "which
    classes are in the APK" are different questions.
    """

    def probe(ctx: Context) -> Answer:
        findings = tuple(
            Finding(text=f"{row.name} from {dex_name}", locator=source.locator)
            for row in ctx.analyzer.store.list_classes(ctx.project_id)
            for source in row.provenance
            if dex_name in source.locator
        )
        return Answer(findings=findings, note=f"{len(findings)} class record(s) from {dex_name}")

    return probe


def indexed_methods(class_name: str | None = None) -> Probe:
    """Ask the symbol index for the methods it holds."""

    def probe(ctx: Context) -> Answer:
        rows = ctx.analyzer.store.list_methods(ctx.project_id, class_name)
        findings = tuple(
            Finding(
                text=(
                    f"{row.qualified_name} decompiled={row.decompiled} "
                    f"flags={','.join(row.access_flags) or '-'}"
                ),
                locator=row.provenance[0].locator if row.provenance else "",
            )
            for row in rows
        )
        return Answer(findings=findings, note=f"{len(findings)} indexed method(s)")

    return probe


def class_provenance(class_name: str) -> Probe:
    """Ask which backends and which files a class's record came from.

    The version is left out of the text on purpose: a task that quoted a
    version would fail the day the tool is upgraded, and what the tasks are
    about is *where* a record came from.
    """

    def probe(ctx: Context) -> Answer:
        row = ctx.analyzer.store.get_class(ctx.project_id, class_name)
        if row is None:
            return Answer(note=f"the index holds no class {class_name}")
        findings = tuple(
            Finding(text=f"{source.tool} -> {source.locator}", locator=source.locator)
            for source in row.provenance
        )
        return Answer(
            findings=findings,
            note=f"{len(findings)} source(s) for {class_name}",
        )

    return probe


def provenance_digests(class_name: str) -> Probe:
    """Ask which APK a class's records were made against.

    The digest is the one thing every provenance record carries: a record
    that names a different APK than the one being analysed is a record of
    something else.
    """

    def probe(ctx: Context) -> Answer:
        row = ctx.analyzer.store.get_class(ctx.project_id, class_name)
        if row is None:
            return Answer(note=f"the index holds no class {class_name}")
        findings = tuple(
            Finding(text=f"apk_sha256={source.apk_sha256}", locator=source.locator)
            for source in row.provenance
        )
        return Answer(
            findings=findings,
            note=f"{len(findings)} record(s) for {class_name}, apk {ctx.project.apk.sha256}",
        )

    return probe


def recorded_tool_versions() -> Probe:
    """Ask which versions of the backends the analysis ran."""

    def probe(ctx: Context) -> Answer:
        findings = tuple(
            Finding(text=f"{tool}={version or '-'}")
            for tool, version in sorted(ctx.project.tool_versions.items())
        )
        return Answer(findings=findings, note=f"{len(findings)} tool version(s) recorded")

    return probe


def method_provenance(class_name: str, method_name: str) -> Probe:
    """Ask which DEX files and tools a method's record came from.

    The version is left out of the text, as in :func:`class_provenance`: a
    task that quoted a version would fail the day the tool is upgraded.
    """

    def probe(ctx: Context) -> Answer:
        rows: Sequence[MethodRef] = ctx.analyzer.store.list_methods(ctx.project_id, class_name)
        matching = [row for row in rows if row.name == method_name]
        findings = tuple(
            Finding(text=f"{source.tool} -> {source.locator}", locator=source.locator)
            for row in matching
            for source in row.provenance
        )
        return Answer(
            findings=findings,
            note=f"{len(findings)} source(s) for {class_name}.{method_name}",
        )

    return probe


def class_source(class_name: str) -> Probe:
    """Ask for a class's source, and which representation it came back as."""

    def probe(ctx: Context) -> Answer:
        try:
            document = ctx.analyzer.class_source_document(ctx.project_id, class_name)
        except AmbiguousMethodError as exc:
            return Answer(note=f"ambiguous: {exc.describe()}")
        if document is None:
            return Answer(note="no source was found for the class")
        findings = tuple(
            Finding(
                text=f"kind={document.kind.value} locator={source.locator}", locator=source.locator
            )
            for source in document.provenance
        )
        body = Finding(
            text=document.text,
            locator=document.provenance[0].locator if document.provenance else "",
        )
        return Answer(
            findings=(*findings, body),
            note=f"{class_name} read as {document.kind.value}",
        )

    return probe


def method_source(class_name: str, method_name: str, descriptor: str | None = None) -> Probe:
    """Ask for one method's source, and which representation it came back as.

    The descriptor picks one overload out of several. Without it, a name that
    matches more than one method is an error rather than a choice — the
    probe reports that in its note instead of picking one.
    """

    def probe(ctx: Context) -> Answer:
        try:
            document = ctx.analyzer.method_source_document(
                ctx.project_id, class_name, method_name, descriptor
            )
        except AmbiguousMethodError as exc:
            candidates = ", ".join(candidate.signature for candidate in exc.candidates)
            return Answer(note=f"ambiguous: {exc.describe()}; candidates: {candidates}")
        if document is None:
            return Answer(note="no source was found for the method")
        findings = tuple(
            Finding(
                text=f"kind={document.kind.value} descriptor={document.descriptor} "
                f"locator={source.locator}",
                locator=source.locator,
            )
            for source in document.provenance
        )
        body = Finding(
            text=document.text,
            locator=document.provenance[0].locator if document.provenance else "",
        )
        return Answer(
            findings=(*findings, body),
            note=f"{class_name}.{method_name} read as {document.kind.value}",
        )

    return probe


def dex_files() -> Probe:
    """Ask which DEX files the APK holds."""

    def probe(ctx: Context) -> Answer:
        findings = tuple(Finding(text=name) for name in ctx.project.apk.dex_files)
        return Answer(findings=findings, note=f"{len(findings)} DEX file(s)")

    return probe


def recorded_errors() -> Probe:
    """Ask which backend failures the analysis recorded."""

    def probe(ctx: Context) -> Answer:
        findings = tuple(
            Finding(text=f"{error.tool}/{error.code.value}: {error.message}")
            for error in ctx.project.errors
        )
        return Answer(findings=findings, note=f"{len(findings)} recorded failure(s)")

    return probe


def apk_certificate() -> Probe:
    """Ask who signed the APK.

    An APK that carries no signing certificate has nobody to name, and the
    right answer to "who signed this?" is that the analysis holds no such
    record — not a guess.
    """

    def probe(ctx: Context) -> Answer:
        if not ctx.project.apk.has_signed_certificate:
            return Answer(note="the APK carries no signing certificate")
        return Answer(
            findings=(Finding(text="the APK carries a signing certificate"),),
            note="the analysis records that the APK is signed, but not who signed it",
        )

    return probe
