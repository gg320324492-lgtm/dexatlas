"""Evidence construction and the evidence-level discipline.

The level field is the mechanism that stops an unverified claim from being reported as a
finding, so it gets tested directly.
"""

from __future__ import annotations

from dexatlas.core.evidence import (
    MAX_EVIDENCE_CALLED_METHODS,
    MAX_LISTED_CALLERS,
    EvidenceBuilder,
)
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    EvidenceKind,
    EvidenceLevel,
    ManifestComponent,
    MethodRef,
    MethodReference,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import (
    _extract_smali_method,
    _merge_classes,
    _merge_fields,
    _merge_methods,
    _smali_declares,
)


def _provenance(tool: str = "androguard") -> list[Provenance]:
    return [Provenance(tool=tool, tool_version="1.0", apk_sha256="b" * 64, locator=f"{tool}:x")]


def _builder() -> EvidenceBuilder:
    return EvidenceBuilder(project_id="apk_test", apk_sha256="b" * 64)


def _method(name: str = "m", class_name: str = "com.a.C") -> MethodRef:
    return MethodRef(class_name=class_name, name=name, descriptor="()V", provenance=_provenance())


def _reference(caller: str, callee: str, locator: str = "androguard:x") -> MethodReference:
    """A call edge, with the locator that says where the call was seen."""
    return MethodReference(
        caller=caller,
        callee=callee,
        provenance=[
            Provenance(tool="androguard", tool_version="1.0", apk_sha256="b" * 64, locator=locator)
        ],
    )


# -- ids --------------------------------------------------------------------


def test_evidence_ids_are_sequential_and_stable() -> None:
    builder = _builder()

    ids = [
        builder.add(EvidenceKind.OBSERVATION, EvidenceLevel.VERIFIED, f"n{i}", []).id
        for i in range(3)
    ]

    assert ids == ["E-0001", "E-0002", "E-0003"]


def test_ids_pad_to_a_constant_width() -> None:
    builder = _builder()

    for _ in range(12):
        builder.add(EvidenceKind.OBSERVATION, EvidenceLevel.VERIFIED, "x", [])

    assert builder.items[-1].id == "E-0012"


# -- levels -----------------------------------------------------------------


def test_a_backend_error_is_verified_evidence() -> None:
    """A failure that is on the record is a fact, not a suspicion."""
    builder = _builder()
    error = ToolError(tool="jadx", code=ToolErrorCode.TIMEOUT, message="timed out")

    evidence = builder.add_error(error)

    assert evidence.level == EvidenceLevel.VERIFIED
    assert "jadx" in evidence.summary


def test_model_supplied_claims_are_leads_not_verified() -> None:
    builder = _builder()

    evidence = builder.add(
        EvidenceKind.BEHAVIOUR,
        EvidenceLevel.LEAD,
        "model suggests this may exfiltrate data",
        [],
    )

    assert evidence.level == EvidenceLevel.LEAD


def test_level_is_never_inferred_from_the_wording() -> None:
    """A confidently-worded lead stays a lead. Level is the caller's, not the text's."""
    builder = _builder()

    evidence = builder.add(
        EvidenceKind.BEHAVIOUR,
        EvidenceLevel.LEAD,
        "CONFIRMED VULNERABILITY: hardcoded credential",
        [],
    )

    assert evidence.level == EvidenceLevel.LEAD


# -- provenance -------------------------------------------------------------


def test_every_evidence_record_carries_provenance() -> None:
    builder = _builder()

    builder.add_classes([ClassRef(name="com.a.B", kind=ClassKind.CLASS, provenance=_provenance())])

    assert builder.items[0].provenance[0].tool == "androguard"


def test_exported_components_provenance_points_at_the_declaration() -> None:
    builder = _builder()

    builder.add_exported_components(
        [
            ManifestComponent(kind="activity", name="com.a.Main", exported=True),
            ManifestComponent(kind="activity", name="com.a.Hidden", exported=False),
        ]
    )

    evidence = builder.items[0]
    assert len(evidence.detail["components"]) == 1
    assert evidence.provenance[0].locator == "AndroidManifest.xml#/application"


def test_no_exported_components_records_nothing() -> None:
    builder = _builder()

    builder.add_exported_components([ManifestComponent(kind="activity", name="a", exported=False)])

    assert builder.items == []


def test_caller_list_is_truncated() -> None:
    builder = _builder()
    method = MethodRef(
        class_name="com.a.C",
        name="m",
        descriptor="()V",
        provenance=_provenance(),
    )
    references = [
        MethodReference(
            caller=f"com.a.Caller{i}.run()V", callee=method.qualified_name, provenance=_provenance()
        )
        for i in range(MAX_LISTED_CALLERS + 20)
    ]

    builder.add_method_references(method, references)

    evidence = builder.items[0]
    assert evidence.detail["truncated"] is True
    assert len(evidence.detail["callers"]) == MAX_LISTED_CALLERS


def test_no_references_records_nothing() -> None:
    builder = _builder()

    builder.add_method_references(
        MethodRef(class_name="a.B", name="m", descriptor="()V", provenance=_provenance()), []
    )

    assert builder.items == []


# -- cross-references -------------------------------------------------------


def test_a_called_method_produces_one_cross_reference_record() -> None:
    """The unit of evidence is the called method, not the call."""
    builder = _builder()
    method = _method()

    builder.add_cross_references(
        [method], [_reference("com.a.Caller.run()V", method.qualified_name)]
    )

    assert len(builder.items) == 1
    evidence = builder.items[0]
    assert evidence.kind == EvidenceKind.CROSS_REFERENCE
    assert evidence.level == EvidenceLevel.VERIFIED
    assert "com.a.C.m()V" in evidence.summary
    assert evidence.detail["callers"] == ["com.a.Caller.run()V"]


def test_a_call_to_a_method_outside_the_apk_is_not_a_record() -> None:
    """A call to ``java.lang.StringBuilder.append`` is a fact about the JDK.

    It says nothing about the app under analysis, and a report full of those
    would say nothing about it either.
    """
    builder = _builder()
    library = "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"

    builder.add_cross_references([_method()], [_reference("com.a.Caller.run()V", library)])

    assert builder.items == []


def test_the_provenance_points_at_the_call_site() -> None:
    """The claim is about the call, so the locator is the call site.

    The method's own provenance is kept as well, so a reader can also find
    where the callee is defined.
    """
    builder = _builder()
    method = _method()
    reference = _reference(
        "com.a.Caller.run()V", method.qualified_name, locator="androguard:classes.dex#run->m"
    )

    builder.add_cross_references([method], [reference])

    evidence = builder.items[0]
    assert evidence.provenance[0].locator == "androguard:classes.dex#run->m"
    assert evidence.provenance[-1].locator == "androguard:x"


def test_the_most_called_method_is_recorded_first() -> None:
    """The order a reader wants is the order the records take."""
    builder = _builder()
    quiet = _method("quiet")
    busy = _method("busy")

    builder.add_cross_references(
        [quiet, busy],
        [
            _reference("com.a.Caller.run()V", busy.qualified_name),
            _reference("com.a.Other.run()V", busy.qualified_name),
        ],
    )

    assert builder.items[0].summary.startswith("com.a.C.busy()V")


def test_the_number_of_records_is_capped() -> None:
    """An app has thousands of called methods; the report has room for a sample."""
    builder = _builder()
    methods = [_method(f"m{index}") for index in range(MAX_EVIDENCE_CALLED_METHODS + 10)]
    references = [
        _reference(f"com.a.Caller{index}.run()V", method.qualified_name)
        for index, method in enumerate(methods)
    ]

    builder.add_cross_references(methods, references)

    assert len(builder.items) == MAX_EVIDENCE_CALLED_METHODS


def test_the_caller_count_is_stated_even_when_the_list_is_truncated() -> None:
    """A truncated list must not read as "these are all of them"."""
    builder = _builder()
    method = _method()
    references = [
        _reference(f"com.a.Caller{index}.run()V", method.qualified_name)
        for index in range(MAX_LISTED_CALLERS + 5)
    ]

    builder.add_cross_references([method], references)

    evidence = builder.items[0]
    assert evidence.detail["truncated"] is True
    assert evidence.detail["call_count"] == MAX_LISTED_CALLERS + 5
    assert len(evidence.detail["callers"]) == MAX_LISTED_CALLERS


def test_no_references_produces_no_record() -> None:
    builder = _builder()

    builder.add_cross_references([_method()], [])

    assert builder.items == []


# -- merging definitions of one symbol --------------------------------------


def test_a_method_defined_in_two_dexes_keeps_both_sources() -> None:
    """The method table keys on the method id, so the second definition replaces
    the first — and takes its provenance with it."""
    first = _method()
    second = _method()
    second.provenance = [
        Provenance(
            tool="androguard", tool_version="1.0", apk_sha256="b" * 64, locator="androguard:y"
        )
    ]

    merged = _merge_methods([first, second])

    assert len(merged) == 1
    assert {p.locator for p in merged[0].provenance} == {"androguard:x", "androguard:y"}


def test_merging_methods_keeps_a_body_found_in_either_dex() -> None:
    without_body = _method()
    without_body.decompiled = False
    with_body = _method()
    with_body.decompiled = True

    merged = _merge_methods([without_body, with_body])

    assert merged[0].decompiled is True


def test_merging_methods_unions_the_access_flags() -> None:
    public = _method()
    public.access_flags = ["public"]
    final = _method()
    final.access_flags = ["final"]

    merged = _merge_methods([public, final])

    assert merged[0].access_flags == ["final", "public"]


def test_a_field_defined_in_two_dexes_keeps_both_sources() -> None:
    from dexatlas.core.models import FieldRef

    first = FieldRef(
        class_name="com.a.C", name="KEY", descriptor="Ljava/lang/String;", provenance=_provenance()
    )
    second = FieldRef(class_name="com.a.C", name="KEY", descriptor="Ljava/lang/String;")
    second.provenance = [
        Provenance(
            tool="androguard", tool_version="1.0", apk_sha256="b" * 64, locator="androguard:y"
        )
    ]

    merged = _merge_fields([first, second])

    assert len(merged) == 1
    assert {p.locator for p in merged[0].provenance} == {"androguard:x", "androguard:y"}


# -- class merging ----------------------------------------------------------


def test_merge_keeps_every_provenance_entry() -> None:
    """Two backends seeing one class must produce one index entry citing both."""
    jadx_view = ClassRef(name="com.a.B", kind=ClassKind.CLASS, provenance=_provenance("jadx"))
    androguard_view = ClassRef(
        name="com.a.B",
        kind=ClassKind.INTERFACE,
        superclass="java.lang.Object",
        provenance=_provenance("androguard"),
    )

    merged = _merge_classes([jadx_view, androguard_view])

    assert len(merged) == 1
    assert {p.tool for p in merged[0].provenance} == {"jadx", "androguard"}


def test_merge_prefers_the_more_specific_kind() -> None:
    merged = _merge_classes(
        [
            ClassRef(name="com.a.B", kind=ClassKind.CLASS, provenance=_provenance("jadx")),
            ClassRef(
                name="com.a.B", kind=ClassKind.INTERFACE, provenance=_provenance("androguard")
            ),
        ]
    )

    assert merged[0].kind == ClassKind.INTERFACE


def test_merge_unions_flags_and_interfaces() -> None:
    merged = _merge_classes(
        [
            ClassRef(
                name="com.a.B",
                kind=ClassKind.CLASS,
                access_flags=["public"],
                interfaces=["com.a.I"],
                provenance=_provenance("jadx"),
            ),
            ClassRef(
                name="com.a.B",
                kind=ClassKind.CLASS,
                access_flags=["final"],
                interfaces=["com.a.J"],
                provenance=_provenance("androguard"),
            ),
        ]
    )

    assert merged[0].access_flags == ["final", "public"]
    assert merged[0].interfaces == ["com.a.I", "com.a.J"]


def test_merge_sorts_deterministically() -> None:
    merged = _merge_classes(
        [
            ClassRef(name="com.a.Z", provenance=_provenance()),
            ClassRef(name="com.a.A", provenance=_provenance()),
        ]
    )

    assert [c.name for c in merged] == ["com.a.A", "com.a.Z"]


# -- Smali fallback ---------------------------------------------------------

SMALI = """.class public Lcom/example/Demo;
.super Ljava/lang/Object;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static compute(Ljava/lang/String;)Ljava/lang/String;
    .locals 1
    const-string v0, "secret"
    return-object v0
.end method
"""


def test_extracts_a_smali_method() -> None:
    body = _extract_smali_method(SMALI, "compute")

    assert body is not None
    assert body.startswith(".method public static compute")
    assert body.endswith(".end method")
    assert "secret" in body


def test_smali_methods_do_not_leak_into_each_other() -> None:
    body = _extract_smali_method(SMALI, "compute")

    assert body is not None
    assert "constructor" not in body


def test_extracts_a_constructor() -> None:
    body = _extract_smali_method(SMALI, "<init>")

    assert body is not None
    assert body.endswith(".end method")


def test_unknown_smali_method_is_none() -> None:
    assert _extract_smali_method(SMALI, "nope") is None


def test_truncated_smali_does_not_return_a_partial_body() -> None:
    truncated = ".method public static broken()V\n    .locals 0\n"

    assert _extract_smali_method(truncated, "broken") is None


def test_smali_header_name_matching() -> None:
    assert _smali_declares(
        ".method public static compute(Ljava/lang/String;)Ljava/lang/String;", "compute"
    )
    assert _smali_declares(".method public constructor <init>()V", "<init>")
    assert not _smali_declares(".method public static compute()V", "different")
