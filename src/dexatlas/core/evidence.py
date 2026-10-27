"""Evidence construction.

Evidence ids are stable across re-analysis of the same APK: they are assigned in
sequence as observations are recorded, so ``E-0007`` in a report resolves back to the
same row in the database.

There are two ways in here, and they are kept apart on purpose: one for what a tool
read, and one for what a model said. The builder's own docstring says how.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dexatlas.core.locators import (
    InvalidLocatorError,
    LocatorResolver,
    parse_locator,
)
from dexatlas.core.models import (
    CODE_FINDING_KINDS,
    CROSS_REFERENCE_EDGE_COUNT,
    CROSS_REFERENCE_SITE_COUNT,
    LOCATED_FINDING_KIND,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    ManifestComponent,
    MethodRef,
    MethodReference,
    Provenance,
    Sourced,
    ToolError,
)

#: References listed in evidence detail before truncating.
MAX_LISTED_CALLERS = 50

#: Called methods that get an evidence record. A large app calls thousands of its
#: own methods, and one record each would bury the findings under index data.
#: The report's evidence table shows 200 rows, so this leaves room for the class
#: declarations in the same table.
MAX_EVIDENCE_CALLED_METHODS = 100


class InvalidProvenanceError(ValueError):
    """The provenance does not support the record it is attached to.

    Raised when a record claims to be ``VERIFIED`` and its provenance cannot back
    that claim: no provenance at all, provenance that names another APK, a
    locator that is not a locator, or a locator that does not resolve inside
    the analysis the record belongs to.

    The error is the mechanism. A record that says "a tool established this" and
    cites nothing, or cites something that is not there, puts a false sentence
    in the report -- and a reader who believes it acts on a guess.
    """


@dataclass(slots=True)
class EvidenceBuilder:
    """Accumulates evidence for one project, assigning ids as it goes.

    There are two ways in here, and they are kept apart on purpose.

    :meth:`add` is the way a **tool** records what it read. Its level is passed
    explicitly and never inferred from the wording, and the top level means the
    record's provenance backs it: the citation has to name a place that is
    really there inside the analysis. :meth:`add_claim` is the way a **model**
    records what it said, and it cannot write a record at the top level at all.

    The separation is the mechanism behind "a model's output is never a
    finding". It is not a naming convention: the claim path has no level to
    get wrong, and the tool path refuses a record whose provenance does not
    resolve.
    """

    project_id: str
    tool_versions: dict[str, str | None]
    """The version of each tool that took part in the analysis.

    Evidence names the tool that produced it, and a tool without a version
    cannot be reproduced: a reader cannot tell "this tool has no version" from
    "nobody filled this in". The versions are therefore a constructor argument
    rather than something to be remembered later — an evidence record cannot be
    written without them.
    """

    apk_sha256: str = ""
    workspace: Path | None = None
    """The workspace of the analysis these records belong to.

    The workspace is where the backends wrote what they read, so it is also
    what a locator is resolved against: a citation that names a file the
    analysis never wrote names nothing, and a record that cites it cannot be
    verified.

    It is an argument rather than something derived from the project id,
    because the workspace moves. A published run lives in a versioned
    directory of its own, and a builder that computed the path from the id
    would look in the wrong place the moment that changed.
    """

    dex_files: Sequence[str] = ()
    """The dex files of the analysed APK, by name.

    The DEX reader's locators name a member of the APK rather than a file in
    the workspace, and this is the list that says which members the APK has.
    """

    items: list[Evidence] = field(default_factory=list)

    def _next_id(self) -> str:
        return f"E-{len(self.items) + 1:04d}"

    def _version(self, tool: str) -> str | None:
        """The version of one tool, if the analysis knew it.

        ``None`` means the tool never ran — it was not installed, or it was
        left out of the run. That is a fact about the tool, not a gap in the
        record.
        """
        return self.tool_versions.get(tool)

    def resolver(self) -> LocatorResolver | None:
        """The resolver for this analysis, when the analysis knows where it is.

        ``None`` when the builder was not told which workspace the records
        belong to. A citation cannot be checked against an analysis the
        builder knows nothing about, so a record that is nothing but its place
        is refused rather than believed, and a record about the index is
        written the way the index states it.
        """
        if self.workspace is None:
            return None
        return LocatorResolver(self.workspace, dex_files=self.dex_files)

    def add(
        self,
        kind: EvidenceKind,
        level: EvidenceLevel,
        summary: str,
        provenance: Sequence[Provenance],
        detail: dict[str, object] | None = None,
    ) -> Evidence:
        """Record one traceable observation.

        ``level`` is always passed explicitly, never inferred from the wording. Only a
        deterministic tool run produces ``VERIFIED``; anything a model suggests is a
        ``LEAD`` until a human or a tool confirms it.

        A ``VERIFIED`` record about a place in the code is checked before it is
        written: its provenance has to be there, has to belong to this APK, and
        has to name a place that is really inside this analysis. A record that
        fails is refused rather than written and believed.
        """
        provenance = list(provenance)
        if level is EvidenceLevel.VERIFIED and kind in CODE_FINDING_KINDS:
            self._check_the_provenance(provenance, kind)
        evidence = Evidence(
            id=self._next_id(),
            kind=kind,
            level=level,
            summary=summary,
            detail=detail or {},
            provenance=provenance,
        )
        self.items.append(evidence)
        return evidence

    def add_claim(
        self,
        summary: str,
        provenance: Sequence[Provenance],
        *,
        kind: EvidenceKind = EvidenceKind.BEHAVIOUR,
        level: EvidenceLevel = EvidenceLevel.LEAD,
        detail: dict[str, object] | None = None,
    ) -> Evidence:
        """Record a claim a model made.

        A claim is not a fact. Whatever the model says, and however sure it
        sounds, the record is a ``LEAD``: the level is not an argument here,
        because a caller that could pass ``VERIFIED`` could pass it by mistake
        as easily as on purpose. The level is offered so that a caller can say
        that it is not even a lead, and it is refused when it is ``VERIFIED``.

        A claim that a tool later confirms is not this claim promoted: it is
        the tool's own record, recorded through :meth:`add`.
        """
        if level is EvidenceLevel.VERIFIED:
            raise InvalidProvenanceError(
                "a model's claim is not a fact: it cannot be recorded as verified. "
                "Record the tool's confirmation as its own evidence."
            )
        return self.add(kind, level, summary, provenance, detail)

    def _check_the_provenance(self, provenance: list[Provenance], kind: EvidenceKind) -> None:
        """Refuse a verified finding about code whose provenance does not back it.

        A **located** finding is nothing but its place: it says "here is the
        thing, in this file, at this method". So it is always checked, and it
        is checked against the analysis. Without an analysis there is nothing
        to check it against, and a record that cannot be checked is refused
        rather than believed on the strength of a string that looks right.

        A **cross-reference** is a fact about the index, and the index is the
        analysis's own artifact: the DEX reader read that edge out of the
        bytecode. It is checked the same way when there is an analysis to
        check it against.

        Three things are checked, in the order a reader would hit them.

        There has to be provenance: a verified finding with no citation names
        no place, and the report renders it as established by a tool.

        The citation has to belong to this APK: a locator that names another
        APK is stale, and following it would take the reader to a different
        analysis than the one the record is about.

        And the citation has to be a locator at all, and it has to resolve: the
        file it names has to be in the analysis, the class has to be in the
        dex, the method has to be declared in the source. A locator that
        *looks* right is not a resolution, and "looks right" is exactly what a
        fabricated citation manages.
        """
        if kind not in CODE_FINDING_KINDS:
            return
        resolver = self.resolver()
        if resolver is None:
            if kind is LOCATED_FINDING_KIND:
                raise InvalidProvenanceError(
                    "a code-located record cannot be verified without the workspace of the "
                    "analysis: there is nothing to resolve its citation against"
                )
            return
        if not provenance:
            raise InvalidProvenanceError(
                f"a {kind.value} record cannot be verified with no provenance: verified means "
                "a tool established this, and the record has to name the place it did"
            )
        for entry in provenance:
            if self.apk_sha256 and entry.apk_sha256 != self.apk_sha256:
                raise InvalidProvenanceError(
                    f"the provenance names another APK ({entry.apk_sha256[:12]}...), not the "
                    f"one under analysis ({self.apk_sha256[:12]}...): the citation is stale"
                )
            try:
                parse_locator(entry.locator)
            except InvalidLocatorError as exc:
                raise InvalidProvenanceError(
                    f"{entry.locator!r} is not a locator this project can follow: {exc}"
                ) from exc

        failures: list[str] = []
        for entry in provenance:
            resolution = resolver.resolve(entry.locator)
            if resolution.ok:
                return
            failures.append(f"{entry.locator} ({resolution.reason.value}: {resolution.detail})")
        raise InvalidProvenanceError(
            "no provenance of this record resolves inside the analysis: " + "; ".join(failures)
        )

    def add_sourced(
        self,
        kind: EvidenceKind,
        level: EvidenceLevel,
        summary: str,
        source: Sourced,
        detail: dict[str, object] | None = None,
    ) -> Evidence:
        return self.add(kind, level, summary, source.provenance, detail)

    def add_error(self, error: ToolError) -> Evidence:
        """A backend failure is itself evidence — it is why a result may be missing."""
        return self.add(
            kind=EvidenceKind.OBSERVATION,
            level=EvidenceLevel.VERIFIED,
            summary=f"{error.tool} did not complete: {error.message}",
            provenance=[
                Provenance(
                    tool=error.tool,
                    tool_version=self._version(error.tool),
                    apk_sha256=self.apk_sha256,
                    locator=f"{error.tool}:error/{error.code}",
                )
            ],
            detail={"error": error.model_dump(mode="json")},
        )

    def add_classes(self, classes: Sequence[ClassRef], limit: int | None = None) -> None:
        """Record one evidence row per class, up to a limit.

        An APK can hold hundreds of thousands of classes, and the evidence table
        has room for a sample of them. A sample that does not say it is a sample
        reads as the whole: a reader who sees 500 class declarations concludes
        the APK has 500 classes. So when the limit bites, one more row says how
        many classes there were and how many got a row of their own.

        That row is about the analysis rather than about a place in the code, so
        it carries no locator: there is no file the reader could open to see the
        classes that were left out.
        """
        covered = classes if limit is None else classes[:limit]
        for cls in covered:
            self.add_sourced(
                kind=EvidenceKind.DECLARATION,
                level=EvidenceLevel.VERIFIED,
                summary=f"Class {cls.name} ({cls.kind})",
                source=cls,
                detail={"superclass": cls.superclass, "interfaces": cls.interfaces},
            )
        if len(covered) < len(classes):
            self.add(
                kind=EvidenceKind.OBSERVATION,
                level=EvidenceLevel.VERIFIED,
                summary=(
                    f"evidence covers {len(covered)} of {len(classes)} classes; "
                    f"the other {len(classes) - len(covered)} have no record"
                ),
                provenance=[],
                detail={
                    "truncated": True,
                    "classes_covered": len(covered),
                    "classes_total": len(classes),
                },
            )

    def add_exported_components(self, components: Sequence[ManifestComponent]) -> None:
        """Record exported components — the highest-signal manifest observation.

        The manifest has no code location, so provenance points at the declaration in
        AndroidManifest.xml rather than at a method.
        """
        exported = [c for c in components if c.exported is True]
        if not exported:
            return
        self.add(
            kind=EvidenceKind.DECLARATION,
            level=EvidenceLevel.VERIFIED,
            summary=f"{len(exported)} component(s) are explicitly exported",
            provenance=[
                Provenance(
                    tool="apktool",
                    tool_version=self._version("apktool"),
                    apk_sha256=self.apk_sha256,
                    locator="apktool:AndroidManifest.xml#/application",
                )
            ],
            detail={
                "components": [
                    {"kind": c.kind, "name": c.name, "permission": c.permission} for c in exported
                ]
            },
        )

    def add_method_references(
        self, method: MethodRef, references: Sequence[MethodReference]
    ) -> None:
        """Record that a method is called, and the call sites that prove it.

        The claim is about the call sites, so the provenance points at them: the
        bytecode scan that found the edge is the evidence for it. The method's own
        provenance is kept as well, so a reader can also find where the callee is
        defined — for a method defined in two dex files, that is both of them.
        """
        if not references:
            return
        callers = sorted({r.caller for r in references})
        # Two numbers, because the record is about two different things. The
        # *call sites* are the places in the bytecode where the call happens:
        # a caller that calls the same method twice contributes two of them.
        # The *call edges* are the relationships the sites make: the same
        # caller contributes one, however many times it calls. A record that
        # stated only one of them would be stating half of what it knows, and
        # the report cannot put two numbers side by side when one of them
        # does not say which it is.
        sites = len(references)
        edges = len({(r.caller, r.kind) for r in references})
        self.add(
            kind=EvidenceKind.CROSS_REFERENCE,
            # A call edge is read out of the bytecode by a deterministic tool and
            # points at a code location, which is what VERIFIED means here.
            level=EvidenceLevel.VERIFIED,
            summary=f"{method.qualified_name} is called from {len(callers)} location(s)",
            provenance=[*_call_site_provenance(references), *method.provenance],
            detail={
                "callers": callers[:MAX_LISTED_CALLERS],
                "truncated": len(callers) > MAX_LISTED_CALLERS,
                CROSS_REFERENCE_SITE_COUNT: sites,
                CROSS_REFERENCE_EDGE_COUNT: edges,
            },
        )

    def add_cross_references(
        self, methods: Sequence[MethodRef], references: Sequence[MethodReference]
    ) -> None:
        """Record one observation per method that this APK calls.

        The unit of evidence is the called method, not the call. A method with
        fifty callers is one conclusion — "this is called from fifty places" —
        and fifty conclusions about one method would bury everything else.

        Only callees that are methods of this APK get a record. A call to
        ``java.lang.StringBuilder.append`` is a fact about the JDK; a report full
        of those says nothing about the app under analysis. The calls themselves
        stay queryable in the cross-reference table either way.
        """
        if not references:
            return

        index = {method.qualified_name: method for method in methods}
        by_callee: dict[str, list[MethodReference]] = {}
        for reference in references:
            by_callee.setdefault(reference.callee, []).append(reference)

        called = [(index[callee], edges) for callee, edges in by_callee.items() if callee in index]
        # Most-called first: that is the order a reader wants, and it is the same
        # order every run over the same APK produces, so the evidence ids stay
        # stable.
        called.sort(key=lambda item: (-_distinct_callers(item[1]), item[0].qualified_name))

        for method, edges in called[:MAX_EVIDENCE_CALLED_METHODS]:
            self.add_method_references(method, edges)

    def build(self) -> list[Evidence]:
        return list(self.items)


def _distinct_callers(references: Sequence[MethodReference]) -> int:
    """How many distinct methods call the callee.

    A caller that appears in two dex files is one caller, not two: the same
    method, indexed twice.
    """
    return len({reference.caller for reference in references})


def _call_site_provenance(references: Sequence[MethodReference]) -> list[Provenance]:
    """The locators that prove the calls, one per call site.

    The locator is what tells two calls apart — the same caller in two dex
    files, the same callee reached from two places — so each distinct locator
    is kept once.
    """
    by_locator: dict[str, Provenance] = {}
    for reference in references:
        for provenance in reference.provenance:
            by_locator.setdefault(provenance.locator, provenance)
    return list(by_locator.values())[:MAX_LISTED_CALLERS]


__all__ = [
    "MAX_EVIDENCE_CALLED_METHODS",
    "MAX_LISTED_CALLERS",
    "EvidenceBuilder",
]
