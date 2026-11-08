"""Checking that a conclusion has evidence behind it.

This is where the line between a lead and a finding is drawn, and it is drawn
by the machinery that already existed: :class:`~dexatlas.core.evidence.EvidenceBuilder`.
The orchestration does not invent a second path to a finding — it routes the
model's conclusions through the same builder that the analysis uses, so the
rules that already hold hold here too.

The rules are two, and they are not the same rule:

* **A conclusion is never a fact.** The model says things; the tools
  establish things. So a conclusion the model made is recorded through
  :meth:`~dexatlas.core.evidence.EvidenceBuilder.add_claim`, which cannot
  write a verified record — it refuses the attempt. A conclusion the tools
  later confirm is not that conclusion promoted: it is the tools' own record,
  recorded separately.

* **A conclusion that names nothing is not a lead.** A lead is a risk
  indicator *and* it points at what makes it a lead. So a conclusion has to
  cite evidence the task actually recorded, or a locator that resolves inside
  the analysis. A conclusion that cites nothing, or that cites only things
  which are not there, is recorded as *insufficient evidence*: not enough
  evidence either way, and it needs a human.

The difference between the two is the whole point of the project. A report
that says "established" when the tool established nothing is worse than a
report that says nothing, because the first one looks like a finding.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import Evidence, EvidenceKind, EvidenceLevel, Provenance

#: How much of an answer that is not a conclusion is kept.
MAX_QUOTED_ANSWER = 400

#: The key in a record's detail that says whether the record is an
#: observation of the thing the task is about, or a note about the analysis
#: itself.
#:
#: "The analysis is incomplete: apktool did not take part" is true, and it
#: is worth recording — but it says nothing about the question that was
#: asked. A conclusion that rests on it has nothing behind it, and the
#: difference between the two is the difference between a lead and a
#: sentence that happens to be true.
SUPPORTS_CLAIMS = "supports_claims"


def _supports_claims(record: Evidence) -> bool:
    """Whether a record can carry a conclusion.

    Two things are asked of a record. It has to establish something — a
    record that says the evidence was insufficient establishes that there
    was not enough, and cannot be the ground a conclusion stands on. And it
    has to be an observation of the thing the task is about rather than a
    note about the analysis that made the observation.
    """
    if record.level is not EvidenceLevel.VERIFIED:
        return False
    return bool(record.detail.get(SUPPORTS_CLAIMS, True))


@dataclass(frozen=True, slots=True)
class Conclusion:
    """One thing the model says it found."""

    statement: str
    evidence_ids: tuple[str, ...] = ()
    """The evidence records the conclusion rests on."""

    locators: tuple[str, ...] = ()
    """The places the conclusion rests on, named directly."""

    confidence: str = ""
    """The model's own opinion of how sure it is.

    It is carried, and it is not acted on. The level of a record is decided
    by what backs it, not by how sure the model sounded.
    """


@dataclass(frozen=True, slots=True)
class ParsedAnswer:
    """What the model answered: some conclusions, and what it could not settle."""

    conclusions: tuple[Conclusion, ...]
    limitations: tuple[str, ...] = ()
    unparsed: str = ""
    """The answer, when it was not the shape that was asked for."""


def parse_answer(content: str) -> ParsedAnswer:
    """Read the model's answer.

    The answer is asked for as JSON: a list of conclusions and the things that
    could not be settled. An answer that is not that shape is not thrown away
    — it is kept, and it is recorded as a conclusion with nothing behind it,
    because "the model said something and it named no evidence" is a fact
    about the task that a reader is entitled to.
    """
    text = content.strip()
    if not text:
        return ParsedAnswer(conclusions=(), unparsed="")

    document: Any = None
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return ParsedAnswer(
            conclusions=(
                Conclusion(
                    statement=(
                        "the model answered without naming any evidence: "
                        f"{text[:MAX_QUOTED_ANSWER]}"
                    )
                ),
            ),
            unparsed=text,
        )

    if not isinstance(document, dict):
        return ParsedAnswer(
            conclusions=(
                Conclusion(
                    statement=(
                        "the model answered with a document that is not an object: "
                        f"{text[:MAX_QUOTED_ANSWER]}"
                    )
                ),
            ),
            unparsed=text,
        )

    raw = document.get("conclusions")
    if not isinstance(raw, list):
        return ParsedAnswer(
            conclusions=(
                Conclusion(
                    statement=(
                        "the model answered without naming any evidence: "
                        f"{text[:MAX_QUOTED_ANSWER]}"
                    )
                ),
            ),
            unparsed=text,
        )

    limitations = document.get("limitations")
    return ParsedAnswer(
        conclusions=tuple(_conclusion(entry) for entry in raw),
        limitations=tuple(str(item) for item in limitations)
        if isinstance(limitations, list)
        else (),
    )


def _conclusion(entry: Any) -> Conclusion:
    """One entry of the answer, as a conclusion."""
    if not isinstance(entry, dict):
        return Conclusion(statement=str(entry))
    return Conclusion(
        statement=str(entry.get("statement", "")),
        evidence_ids=_strings(entry.get("evidence_ids")),
        locators=_strings(entry.get("locators")),
        confidence=str(entry.get("confidence", "")),
    )


def _strings(value: Any) -> tuple[str, ...]:
    """A list of strings, or nothing."""
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, (str, int)))


class EvidenceVerifier:
    """Checks conclusions against the evidence the task recorded.

    The verifier is given the builder the task writes through, the records the
    task has recorded so far, and the means to ask the analysis whether a
    locator resolves. It answers one question: does this conclusion have
    something behind it?
    """

    def __init__(
        self,
        builder: EvidenceBuilder,
        *,
        record_for: Callable[[str], Evidence | None],
        resolves: Callable[[str], bool],
    ) -> None:
        self._builder = builder
        self._record_for = record_for
        """The record with this id, if the task recorded one."""

        self._resolves = resolves
        """Whether a locator resolves inside the analysis."""

    def verify(self, conclusion: Conclusion) -> Evidence:
        """Record one conclusion, at the level its evidence supports.

        A conclusion with something behind it is a **lead**: the tools
        established the facts, and the model connected them. A conclusion with
        nothing behind it is **insufficient evidence**: the report says so
        rather than passing an unsupported sentence off as a finding.
        """
        supported: list[str] = []
        unsupported: list[str] = []
        provenance: list[Provenance] = []

        for evidence_id in conclusion.evidence_ids:
            record = self._record_for(evidence_id)
            if record is None:
                unsupported.append(f"{evidence_id} (no such record in this task)")
                continue
            if not _supports_claims(record):
                unsupported.append(
                    f"{evidence_id} (it is a note about the analysis, not an observation of it)"
                )
                continue
            if self._record_holds(record):
                supported.append(evidence_id)
                provenance.extend(record.provenance)
            else:
                unsupported.append(f"{evidence_id} (its citation does not resolve)")

        for locator in conclusion.locators:
            if self._resolves(locator):
                supported.append(locator)
                provenance.append(self._provenance_for(locator))
            else:
                unsupported.append(f"{locator} (it does not resolve in this analysis)")

        level = EvidenceLevel.LEAD if supported else EvidenceLevel.INSUFFICIENT
        detail: dict[str, Any] = {
            "evidence_ids": list(conclusion.evidence_ids),
            "locators": list(conclusion.locators),
            "supported_by": supported,
            "unsupported": unsupported,
            "source": "the model",
        }
        if conclusion.confidence:
            detail["model_confidence"] = conclusion.confidence

        summary = conclusion.statement
        if not supported:
            because = "; ".join(unsupported) if unsupported else "it names no evidence"
            summary = f"{summary} (no evidence behind it: {because})"

        return self._builder.add_claim(
            summary,
            provenance,
            kind=EvidenceKind.BEHAVIOUR,
            level=level,
            detail=detail,
        )

    def _record_holds(self, record: Evidence) -> bool:
        """Whether a record's citation holds inside the analysis.

        A record that names no place stands on the tool that wrote it: it is
        an observation about the analysis itself, and there is nothing to
        resolve. A record that names a place has to name one that is there —
        a citation that does not resolve is a citation to nowhere.
        """
        if not record.provenance:
            return True
        return any(self._resolves(entry.locator) for entry in record.provenance)

    def _provenance_for(self, locator: str) -> Provenance:
        """The provenance of a locator the model named itself."""
        tool = locator.split(":", 1)[0] if ":" in locator else "mcp"
        return Provenance(
            tool=tool,
            tool_version=self._builder.tool_versions.get(tool),
            apk_sha256=self._builder.apk_sha256,
            locator=locator,
        )


__all__ = [
    "MAX_QUOTED_ANSWER",
    "Conclusion",
    "EvidenceVerifier",
    "ParsedAnswer",
    "parse_answer",
]
