"""What a verified record has to be true of.

The report renders every ``verified`` record as "deterministically established
by an analysis tool", and a reader who believes that goes and looks at the
place the record names. If the place is not there, the report is not wrong in
a small way: it is a false sentence about an APK, and the reader acts on it.

So "verified" is not a label a caller chooses. It is a claim about a citation,
and these tests are about the claim holding up: the citation has to be there,
has to belong to this APK, and has to name something that is really in the
analysis. The negative cases are the point -- empty, stale, mismatched and
fabricated provenance, each of which must leave no verified record behind.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from dexatlas.core.evidence import (
    EvidenceBuilder,
    InvalidProvenanceError,
)
from dexatlas.core.models import (
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    Provenance,
)

APK_SHA = "a" * 64
OTHER_SHA = "b" * 64

JAVA_SOURCE = """package com.example.demo;

public final class Crypto {
    public static String sign(String key) {
        return key;
    }
}
"""

SMALI_SOURCE = """.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;

.method public static sign(Ljava/lang/String;)Ljava/lang/String;
    .locals 0
    return-object p0
.end method
"""

#: The citation that a real analysis of this APK would carry.
REAL_LOCATOR = "jadx:sources/com/example/demo/Crypto.java#sign"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace holding the class the citations below name."""
    java = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    java.mkdir(parents=True)
    (java / "Crypto.java").write_text(JAVA_SOURCE, encoding="utf-8")

    smali = tmp_path / "apktool" / "smali" / "com" / "example" / "demo"
    smali.mkdir(parents=True)
    (smali / "Crypto.smali").write_text(SMALI_SOURCE, encoding="utf-8")
    return tmp_path


def _provenance(locator: str, *, apk_sha256: str = APK_SHA, tool: str = "jadx") -> list[Provenance]:
    return [
        Provenance(
            tool=tool,
            tool_version="1.0",
            apk_sha256=apk_sha256,
            locator=locator,
        )
    ]


def _builder(workspace: Path | None = None, *, apk_sha256: str = APK_SHA) -> EvidenceBuilder:
    return EvidenceBuilder(
        project_id="apk_test",
        tool_versions={"jadx": "1.5.2", "apktool": "2.11.1"},
        apk_sha256=apk_sha256,
        workspace=workspace,
        dex_files=["classes.dex"],
    )


# -- the two contracts ------------------------------------------------------


def test_a_model_claim_is_a_lead_and_not_a_finding(workspace: Path) -> None:
    """A claim is what a model said, and a model saying it does not make it a fact."""
    builder = _builder(workspace)

    evidence = builder.add_claim(
        "the key may be sent over the network",
        _provenance(REAL_LOCATOR),
    )

    assert evidence.level is EvidenceLevel.LEAD
    assert evidence.kind is EvidenceKind.BEHAVIOUR


def test_a_model_claim_cannot_be_written_as_verified(workspace: Path) -> None:
    """The claim path refuses the level rather than trusting the caller not to use it."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add_claim(
            "the key may be sent over the network",
            _provenance(REAL_LOCATOR),
            level=EvidenceLevel.VERIFIED,
        )

    assert builder.items == []


def test_a_model_claim_under_a_code_kind_is_still_not_a_finding(workspace: Path) -> None:
    """A claim that names a place in the code is a lead, and only a lead.

    The kind says what the claim is about; the level says how much it is worth.
    A claim cannot buy itself a finding by naming a file.
    """
    builder = _builder(workspace)

    evidence = builder.add_claim(
        "the key may be sent over the network",
        _provenance(REAL_LOCATOR),
        kind=EvidenceKind.CODE_LOCATED,
    )

    assert evidence.kind is EvidenceKind.CODE_LOCATED
    assert evidence.level is EvidenceLevel.LEAD


def test_a_behaviour_record_cannot_be_verified_at_all() -> None:
    """The model refuses it as well, so there is no second way in."""
    with pytest.raises(ValidationError):
        Evidence(
            id="E-0001",
            kind=EvidenceKind.BEHAVIOUR,
            level=EvidenceLevel.VERIFIED,
            summary="the key may be sent over the network",
        )


# -- a verified finding needs a citation -------------------------------------


def test_a_verified_code_finding_with_no_provenance_is_refused(workspace: Path) -> None:
    """Verified means a tool established this, and the record has to say where."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            [],
        )

    assert builder.items == []


def test_a_verified_cross_reference_with_no_provenance_is_refused(workspace: Path) -> None:
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CROSS_REFERENCE,
            EvidenceLevel.VERIFIED,
            "com.example.demo.Crypto.sign is called from 1 location",
            [],
        )


def test_a_verified_code_finding_with_no_provenance_is_refused_by_the_model() -> None:
    """The shape of the record is checked wherever it is built, not only by the builder."""
    with pytest.raises(ValidationError):
        Evidence(
            id="E-0001",
            kind=EvidenceKind.CODE_LOCATED,
            level=EvidenceLevel.VERIFIED,
            summary="the key is sent over the network",
        )


def test_a_verified_code_finding_with_no_workspace_is_refused() -> None:
    """A code-located record has no meaning without somewhere to resolve its citation.

    There is no way to check a citation without the analysis it belongs to, so
    a record that claims to be verified is refused rather than believed on
    the strength of a string that looks right.
    """
    builder = _builder(None)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance(REAL_LOCATOR),
        )


def test_a_cross_reference_is_checked_against_the_analysis_when_there_is_one() -> None:
    """The check needs the analysis, and the analysis is an argument.

    A cross-reference is a fact about the index, and the index is the
    analysis's own artifact: the DEX reader read that edge out of the
    bytecode. So without a workspace there is nothing to resolve its citation
    against, and the record is written the way the index states it. This is
    the one limit of the rule, and it is written down rather than left to be
    discovered.
    """
    builder = _builder(None)

    evidence = builder.add(
        EvidenceKind.CROSS_REFERENCE,
        EvidenceLevel.VERIFIED,
        "com.example.demo.Crypto.sign is called from 1 location",
        _provenance(REAL_LOCATOR),
    )

    assert evidence.level is EvidenceLevel.VERIFIED


def test_a_cross_reference_with_an_unresolvable_citation_is_refused(workspace: Path) -> None:
    """Given the analysis, the cross-reference is held to the same rule."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CROSS_REFERENCE,
            EvidenceLevel.VERIFIED,
            "com.example.demo.Crypto.sign is called from 1 location",
            _provenance("jadx:sources/com/example/demo/Missing.java#sign"),
        )

    assert builder.items == []


def test_a_verified_code_finding_whose_citation_resolves_is_recorded(
    workspace: Path,
) -> None:
    builder = _builder(workspace)

    evidence = builder.add(
        EvidenceKind.CODE_LOCATED,
        EvidenceLevel.VERIFIED,
        "the key is sent over the network",
        _provenance(REAL_LOCATOR),
    )

    assert evidence.level is EvidenceLevel.VERIFIED
    assert evidence.provenance[0].locator == REAL_LOCATOR
    assert builder.items == [evidence]


# -- the negative cases -----------------------------------------------------


def test_provenance_that_is_empty_leaves_no_verified_record(workspace: Path) -> None:
    """Empty provenance: the empty case."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            [],
        )

    assert not [item for item in builder.items if item.level is EvidenceLevel.VERIFIED]


def test_provenance_that_names_another_apk_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation from another analysis: the stale case.

    The locator would resolve -- the file is right there -- but it is the file
    of a different APK, and following it would take the reader to a different
    analysis than the one the record is about.
    """
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance(REAL_LOCATOR, apk_sha256=OTHER_SHA),
        )

    assert builder.items == []


def test_provenance_that_names_a_file_of_another_analysis_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation into a tree this analysis does not hold: stale, in the other direction."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("jadx:sources/com/example/demo/Old.java#sign"),
        )

    assert builder.items == []


def test_provenance_whose_tool_does_not_match_the_tree_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation that climbs out of the tree it belongs to: the mismatched case."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("jadx:../../etc/passwd"),
        )

    assert builder.items == []


def test_provenance_naming_a_backend_that_did_not_run_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation of a backend this project does not read: mismatched as well."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("someother:sources/com/example/demo/Crypto.java"),
        )

    assert builder.items == []


def test_provenance_naming_a_dex_file_the_apk_does_not_have_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation of a dex file that is not in the APK: mismatched."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("androguard:classes9.dex#com.example.demo.Crypto", tool="androguard"),
        )

    assert builder.items == []


def test_provenance_naming_a_method_that_is_not_there_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation of a method the source does not declare: the fabricated case.

    The locator is well formed, the file is there, and the name is spelled the
    way the code spells it. It is still not a thing that exists.
    """
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("jadx:sources/com/example/demo/Crypto.java#encrypt"),
        )

    assert builder.items == []


def test_provenance_naming_a_class_that_is_not_in_the_dex_leaves_no_verified_record(
    workspace: Path,
) -> None:
    """A citation of a class the analysis never saw: fabricated."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("androguard:classes.dex#com.example.demo.NotAClass", tool="androguard"),
        )

    assert builder.items == []


def test_a_fabricated_citation_cannot_produce_a_verified_record(workspace: Path) -> None:
    """The one sentence the whole mechanism exists for."""
    builder = _builder(workspace)

    with pytest.raises(InvalidProvenanceError):
        builder.add(
            EvidenceKind.CODE_LOCATED,
            EvidenceLevel.VERIFIED,
            "the key is sent over the network",
            _provenance("jadx:sources/com/example/demo/Crypto.java#encrypt"),
        )

    assert not [item for item in builder.items if item.level is EvidenceLevel.VERIFIED]
    assert not [
        item
        for item in builder.items
        if item.provenance and item.provenance[0].locator.endswith("#encrypt")
    ]


# -- the records that are not findings ---------------------------------------


def test_a_class_declaration_keeps_working_without_a_citation(workspace: Path) -> None:
    """A declaration is the index, not a conclusion, and the index may be bare.

    A class that was read out of the DEX exists whether or not the analysis
    also decoded it into a file, and the record says the class exists.
    """
    builder = _builder(workspace)

    evidence = builder.add(
        EvidenceKind.DECLARATION,
        EvidenceLevel.VERIFIED,
        "Class com.example.demo.Crypto (class)",
        [],
    )

    assert evidence.level is EvidenceLevel.VERIFIED


def test_an_observation_about_the_analysis_keeps_working(workspace: Path) -> None:
    """A statement about the analysis points at the analysis, not at a place in the code."""
    builder = _builder(workspace)

    evidence = builder.add(
        EvidenceKind.OBSERVATION,
        EvidenceLevel.VERIFIED,
        "evidence covers 10 of 100 classes",
        [],
    )

    assert evidence.level is EvidenceLevel.VERIFIED


def test_a_lead_about_code_is_not_checked(workspace: Path) -> None:
    """A lead is not a finding, so a citation that does not resolve does not stop it.

    The record still says what it says, and the reader is told by the level
    that it is a risk indicator rather than a confirmed issue.
    """
    builder = _builder(workspace)

    evidence = builder.add(
        EvidenceKind.CODE_LOCATED,
        EvidenceLevel.LEAD,
        "the key may be sent over the network",
        _provenance("jadx:sources/com/example/demo/Crypto.java#encrypt"),
    )

    assert evidence.level is EvidenceLevel.LEAD
