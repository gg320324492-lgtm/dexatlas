"""The cross-reference numbers in a report are about three different things.

The report prints the number of indexed cross-references beside the number
of cross-references that have an evidence record, and the two used to be
counted in different units: the index holds one row per call *edge*, and a
record is made per *called method*. A method called from three places is
three edges and one record, so the report said "1" next to "3" — and a reader
who took that as "one of the three calls is backed by evidence" was reading a
ratio that was never there.

The numbers the report states now are:

* ``cross_references`` — the call edges the index holds;
* ``cross_references_with_evidence`` — the call sites a record covers; one
  record is made per called method of this APK and it covers every call site
  of that method, so the sites add up to more than the records;
* ``cross_reference_records`` — the number of those records.

The expected numbers in these tests are counted from the call edges
themselves. A test that computed the expectation with the same measure the
report uses would pass whatever the report said.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    EvidenceKind,
    InvocationKind,
    MethodRef,
    MethodReference,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

#: The APK the analysis is given. Its content does not matter: the DEX reader
#: is replaced by one that returns the symbols the test needs.
_FAN_IN = 3


def _provenance() -> list[Provenance]:
    return [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256="a" * 64,
            locator="classes.dex",
        )
    ]


def _fan_in(callers: int) -> tuple[list[ClassRef], list[MethodRef], list[MethodReference]]:
    """One method of this APK, called from ``callers`` places.

    Every edge is a separate caller, so the number of edges and the number of
    call sites are the same number here — which is what makes the expected
    value in the tests a fact about the edges rather than a fact about the
    records.
    """
    callee = MethodRef(
        class_name="com.example.Crypto",
        name="sign",
        descriptor="([Ljava/lang/String;)Ljava/lang/String;",
        provenance=_provenance(),
    )
    methods = [callee]
    edges: list[MethodReference] = []
    for index in range(callers):
        caller = MethodRef(
            class_name=f"com.example.Caller{index}",
            name="call",
            descriptor="()V",
            provenance=_provenance(),
        )
        methods.append(caller)
        edges.append(
            MethodReference(
                caller=caller.qualified_name,
                callee=callee.qualified_name,
                kind=InvocationKind.STATIC,
                provenance=_provenance(),
            )
        )
    classes = [
        ClassRef(
            name=method.class_name,
            kind=ClassKind.CLASS,
            provenance=_provenance(),
        )
        for method in methods
    ]
    return classes, methods, edges


def _analyse(settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch, callers: int):
    """Analyse an APK whose DEX reader returns a method with a known fan-in."""
    classes, methods, edges = _fan_in(callers)
    analyzer = Analyzer(settings)

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], edges, [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    return analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)


# -- the number is the number of call sites the records cover ---------------


def test_the_report_counts_the_call_sites_the_records_cover(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A method called from three places is three call sites and one record.

    The report said "one cross-reference with evidence" — the number of
    records — beside "three cross-references indexed", and the two were read
    as the same kind of thing.
    """
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    # The index holds one row per call edge: three of them.
    assert result.project.reference_count == _FAN_IN

    report = render_markdown(result)

    assert f"| Cross-references indexed | {_FAN_IN} |" in report
    assert f"| Cross-references with evidence | {_FAN_IN} |" in report
    # And the records themselves: one per called method of this APK.
    assert "| Cross-reference records | 1 |" in report


def test_the_json_report_counts_the_same_thing(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two reports used to count the same thing twice, separately."""
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == _FAN_IN
    assert summary["cross_references_with_evidence"] == _FAN_IN
    assert summary["cross_reference_records"] == 1


def test_the_two_reports_state_the_same_number(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One measurement, stated in two places.

    The Markdown report and the JSON report are two forms of the same
    document, and a reader who compares them must not find two different
    answers.
    """
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    summary = build_json_report(result)["summary"]
    report = render_markdown(result)

    assert (
        f"| Cross-references with evidence | {summary['cross_references_with_evidence']} |"
        in report
    )
    assert f"| Cross-reference records | {summary['cross_reference_records']} |" in report


def test_the_number_never_exceeds_the_number_of_indexed_cross_references(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two numbers can be compared, which is the point of fixing them."""
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    summary = build_json_report(result)["summary"]

    assert summary["cross_references_with_evidence"] <= summary["cross_references"]
    assert summary["cross_reference_records"] <= summary["cross_references_with_evidence"]


def test_a_method_called_once_is_one_call_site(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary case: one edge, one record, one site."""
    result = _analyse(settings, minimal_apk, monkeypatch, 1)

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == 1
    assert summary["cross_references_with_evidence"] == 1
    assert summary["cross_reference_records"] == 1


def test_the_report_says_what_the_three_numbers_count(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The numbers are printed next to each other, so the units are stated too.

    Three numbers about three things, side by side, is exactly the place a
    reader takes a ratio that is not there.
    """
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    report = render_markdown(result)

    assert "call edges the index holds" in report
    assert "call sites a cross-reference record covers" in report
    # The note qualifies the numbers above it, so it has to reach the reader
    # before the report moves on to the next thing.
    assert report.index("| Cross-references indexed |") < report.index(
        "The cross-reference counts are three numbers"
    )
    assert report.index("The cross-reference counts are three numbers") < report.index(
        "## Evidence levels"
    )


def test_only_the_calls_of_this_apps_own_methods_are_counted(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A call into the JDK is indexed but is not evidence.

    The two numbers differ on purpose: an indexed call into library code is a
    fact about the JDK, not a conclusion about this app.
    """
    analyzer = Analyzer(settings)
    classes, methods, edges = _fan_in(_FAN_IN)
    library_edge = MethodReference(
        caller="com.example.Caller0.call()V",
        callee="java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;",
        kind=InvocationKind.VIRTUAL,
        provenance=_provenance(),
    )

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], [*edges, library_edge], [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    summary = build_json_report(result)["summary"]

    # The index holds the call into the library too.
    assert summary["cross_references"] == _FAN_IN + 1
    # The records cover this app's own method only.
    assert summary["cross_references_with_evidence"] == _FAN_IN
    assert summary["cross_reference_records"] == 1
    records = [item for item in result.evidence if item.kind is EvidenceKind.CROSS_REFERENCE]
    assert len(records) == 1


# -- one caller, two calls ----------------------------------------------------


def _one_caller_twice() -> tuple[list[ClassRef], list[MethodRef], list[MethodReference]]:
    """One caller that calls the same method twice.

    The index holds one row per call, so this is two rows and one caller.
    A record covers both calls and names the caller once. The number the
    report states beside the number of indexed rows has to be in the unit
    of rows -- otherwise the two numbers beside each other are in different
    units, which is what the review found.
    """
    callee = MethodRef(
        class_name="com.example.Crypto",
        name="sign",
        descriptor="([Ljava/lang/String;)Ljava/lang/String;",
        provenance=_provenance(),
    )
    caller = MethodRef(
        class_name="com.example.Caller",
        name="call",
        descriptor="()V",
        provenance=_provenance(),
    )
    edges = [
        MethodReference(
            caller=caller.qualified_name,
            callee=callee.qualified_name,
            kind=InvocationKind.STATIC,
            provenance=_provenance(),
        )
        for _ in range(2)
    ]
    classes = [
        ClassRef(name=method.class_name, kind=ClassKind.CLASS, provenance=_provenance())
        for method in (callee, caller)
    ]
    return classes, [callee, caller], edges


def test_the_number_beside_the_indexed_rows_counts_rows(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One caller, two calls: two indexed rows, and a number that says so.

    The record names the caller once, so the number of call sites is one
    while the number of indexed rows is two. The report states the number
    that can be compared with the rows -- the edges -- and the rows it
    covers must not exceed them.
    """
    classes, methods, edges = _one_caller_twice()
    analyzer = Analyzer(settings)

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], edges, [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    assert result.project.reference_count == 2, "the index should hold one row per call"

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == 2
    assert summary["cross_references_with_evidence"] == 2
    assert summary["cross_reference_records"] == 1
