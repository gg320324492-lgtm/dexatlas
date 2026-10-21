"""Evidence construction.

Evidence ids are stable across re-analysis of the same APK: they are assigned in
sequence as observations are recorded, so ``E-0007`` in a report resolves back to the
same row in the database.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from dexatlas.core.models import (
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


@dataclass(slots=True)
class EvidenceBuilder:
    """Accumulates evidence for one project, assigning ids as it goes."""

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
        """
        evidence = Evidence(
            id=self._next_id(),
            kind=kind,
            level=level,
            summary=summary,
            detail=detail or {},
            provenance=list(provenance),
        )
        self.items.append(evidence)
        return evidence

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
                "call_count": len(callers),
                # The indexed cross-references are rows, one per call, and a
                # caller that calls the same method twice contributes two rows
                # and one call site. The report states this number beside the
                # number of indexed rows, so it has to be in the same unit.
                "edge_count": len(references),
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
