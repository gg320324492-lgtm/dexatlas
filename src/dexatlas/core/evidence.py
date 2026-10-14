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


@dataclass(slots=True)
class EvidenceBuilder:
    """Accumulates evidence for one project, assigning ids as it goes."""

    project_id: str
    apk_sha256: str = ""
    items: list[Evidence] = field(default_factory=list)

    def _next_id(self) -> str:
        return f"E-{len(self.items) + 1:04d}"

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
                    tool_version=None,
                    apk_sha256=self.apk_sha256,
                    locator=f"error/{error.code}",
                )
            ],
            detail={"error": error.model_dump(mode="json")},
        )

    def add_classes(self, classes: Sequence[ClassRef]) -> None:
        for cls in classes:
            self.add_sourced(
                kind=EvidenceKind.DECLARATION,
                level=EvidenceLevel.VERIFIED,
                summary=f"Class {cls.name} ({cls.kind})",
                source=cls,
                detail={"superclass": cls.superclass, "interfaces": cls.interfaces},
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
                    tool_version=None,
                    apk_sha256=self.apk_sha256,
                    locator="AndroidManifest.xml#/application",
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
        if not references:
            return
        callers = sorted({r.caller for r in references})
        self.add_sourced(
            kind=EvidenceKind.CROSS_REFERENCE,
            level=EvidenceLevel.VERIFIED,
            summary=f"{method.qualified_name} is called from {len(callers)} location(s)",
            source=method,
            detail={
                "callers": callers[:MAX_LISTED_CALLERS],
                "truncated": len(callers) > MAX_LISTED_CALLERS,
            },
        )

    def build(self) -> list[Evidence]:
        return list(self.items)


__all__ = ["MAX_LISTED_CALLERS", "EvidenceBuilder"]
