"""The cross-reference numbers in a report are about two different things.

A cross-reference index holds two kinds of number, and they are not the same
number: the **call sites** (the places in the bytecode where a call happens)
and the **call edges** (the relationships between two methods). One method
that calls the same target twice is one edge and two sites, and a report that
printed one of the numbers under the other's name would let a reader read a
ratio out of them that is not there.

The numbers the report states now are:

* ``call_sites`` — the call sites the index holds;
* ``call_edges`` — the call edges the index holds;
* ``call_sites_with_evidence`` — the call sites a cross-reference record
  covers; one record is made per called method of this APK and it covers every
  call site of that method, so the sites add up to more than the records;
* ``call_edges_with_evidence`` — the call edges those records cover;
* ``cross_reference_records`` — the number of those records.

The expected numbers in these tests are counted from the call sites
themselves. A test that computed the expectation with the same measure the
report uses would pass whatever the report said.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.calls import CallSite
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    EvidenceKind,
    InvocationKind,
    MethodRef,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

#: The APK the analysis is given. Its content does not matter: the DEX reader
#: is replaced by one that returns the symbols the test needs.
_FAN_IN = 3

_CALLEE = "com.example.Crypto.sign([Ljava/lang/String;)Ljava/lang/String;"


def _hash_of(apk: Path) -> str:
    """The hash of the APK under analysis.

    A citation that names another APK is stale, and a stale citation is
    refused: the record would point at a different analysis than the one it
    belongs to.
    """
    return hashlib.sha256(apk.read_bytes()).hexdigest()


def _provenance(apk_sha256: str, locator: str) -> list[Provenance]:
    """A citation that names where the symbol really is.

    The symbols these tests hand the pipeline are made up, but the citation
    that points at them has to be one the analysis can follow: a locator that
    names another APK, or a string that is not a locator at all, is refused.
    A test that fabricated one was asking the analysis to believe it — and
    the rule that refuses it is the whole point of the citation being
    checked.
    """
    return [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256=apk_sha256,
            locator=locator,
        )
    ]


def _caller(apk_sha256: str, index: int) -> MethodRef:
    """One calling method of this APK."""
    return MethodRef(
        class_name=f"com.example.Caller{index}",
        name="call",
        descriptor="()V",
        provenance=_provenance(
            apk_sha256,
            f"androguard:classes.dex#com.example.Caller{index}#com.example.Caller{index}.call()V",
        ),
    )


def _site(apk_sha256: str, caller: MethodRef, offset: int, callee: str = _CALLEE) -> CallSite:
    """One call site: a place in the bytecode where a call happens."""
    return CallSite(
        caller=caller.qualified_name,
        callee=callee,
        kind=InvocationKind.STATIC,
        dex_name="classes.dex",
        instruction_offset=offset,
        provenance=_provenance(
            apk_sha256,
            f"androguard:classes.dex#{caller.class_name}#{caller.qualified_name}",
        ),
    )


def _fan_in(
    apk_sha256: str, callers: int
) -> tuple[list[ClassRef], list[MethodRef], list[CallSite]]:
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
        provenance=_provenance(
            apk_sha256,
            "androguard:classes.dex#com.example.Crypto#com.example.Crypto.sign"
            "([Ljava/lang/String;)Ljava/lang/String;",
        ),
    )
    methods = [callee]
    sites: list[CallSite] = []
    for index in range(callers):
        caller = _caller(apk_sha256, index)
        methods.append(caller)
        sites.append(_site(apk_sha256, caller, offset=4 * index))
    classes = [
        ClassRef(
            name=method.class_name,
            kind=ClassKind.CLASS,
            provenance=_provenance(apk_sha256, f"androguard:classes.dex#{method.class_name}"),
        )
        for method in methods
    ]
    return classes, methods, sites


def _analyse(settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch, callers: int):
    """Analyse an APK whose DEX reader returns a method with a known fan-in."""
    classes, methods, sites = _fan_in(_hash_of(minimal_apk), callers)
    analyzer = Analyzer(settings)

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], sites, [], None

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
    # And one row per call site: three of them, because each caller calls
    # once.
    assert result.call_site_count == _FAN_IN

    report = render_markdown(result)

    assert f"| Call sites indexed | {_FAN_IN} |" in report
    assert f"| Call edges indexed | {_FAN_IN} |" in report
    assert f"| Call sites with evidence | {_FAN_IN} |" in report
    assert f"| Call edges with evidence | {_FAN_IN} |" in report
    # And the records themselves: one per called method of this APK.
    assert "| Cross-reference records | 1 |" in report


def test_the_json_report_counts_the_same_thing(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two reports used to count the same thing twice, separately."""
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == _FAN_IN
    assert summary["call_edges"] == _FAN_IN
    assert summary["call_sites"] == _FAN_IN
    assert summary["call_sites_with_evidence"] == _FAN_IN
    assert summary["call_edges_with_evidence"] == _FAN_IN
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

    assert f"| Call sites with evidence | {summary['call_sites_with_evidence']} |" in report
    assert f"| Call edges with evidence | {summary['call_edges_with_evidence']} |" in report
    assert f"| Cross-reference records | {summary['cross_reference_records']} |" in report


def test_the_number_never_exceeds_the_number_of_indexed_cross_references(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two numbers can be compared, which is the point of fixing them."""
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    summary = build_json_report(result)["summary"]

    assert summary["call_sites_with_evidence"] <= summary["call_sites"]
    assert summary["call_edges_with_evidence"] <= summary["call_edges"]
    assert summary["cross_reference_records"] <= summary["call_edges_with_evidence"]


def test_a_method_called_once_is_one_call_site(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary case: one edge, one record, one site."""
    result = _analyse(settings, minimal_apk, monkeypatch, 1)

    summary = build_json_report(result)["summary"]

    assert summary["cross_references"] == 1
    assert summary["call_sites"] == 1
    assert summary["call_sites_with_evidence"] == 1
    assert summary["call_edges_with_evidence"] == 1
    assert summary["cross_reference_records"] == 1


def test_the_report_says_what_the_numbers_count(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The numbers are printed next to each other, so the units are stated too.

    Numbers about two different things, side by side, is exactly the place a
    reader takes a ratio that is not there.
    """
    result = _analyse(settings, minimal_apk, monkeypatch, _FAN_IN)

    report = render_markdown(result)

    assert "call **sites**" in report
    assert "call **edges**" in report
    # The note qualifies the numbers above it, so it has to reach the reader
    # before the report moves on to the next thing.
    assert report.index("| Call sites indexed |") < report.index(
        "The cross-reference counts are numbers about two different things"
    )
    assert report.index(
        "The cross-reference counts are numbers about two different things"
    ) < report.index("## Evidence levels")


def test_only_the_calls_of_this_apps_own_methods_are_counted(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A call into the JDK is indexed but is not evidence.

    The two numbers differ on purpose: an indexed call into library code is a
    fact about the JDK, not a conclusion about this app.
    """
    analyzer = Analyzer(settings)
    digest = _hash_of(minimal_apk)
    classes, methods, sites = _fan_in(digest, _FAN_IN)
    library_site = _site(
        digest,
        _caller(digest, 0),
        offset=64,
        callee="java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;",
    )

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], [*sites, library_site], [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    summary = build_json_report(result)["summary"]

    # The index holds the call into the library too.
    assert summary["cross_references"] == _FAN_IN + 1
    # The records cover this app's own method only.
    assert summary["call_sites_with_evidence"] == _FAN_IN
    assert summary["call_edges_with_evidence"] == _FAN_IN
    assert summary["cross_reference_records"] == 1
    records = [item for item in result.evidence if item.kind is EvidenceKind.CROSS_REFERENCE]
    assert len(records) == 1


# -- one caller, two calls ----------------------------------------------------


def _one_caller_twice(
    apk_sha256: str,
) -> tuple[list[ClassRef], list[MethodRef], list[CallSite]]:
    """One caller that calls the same method twice.

    This is the case the two numbers exist for: one edge, two call sites. The
    record covers both calls and names the caller once, so the number of call
    sites is two and the number of call edges is one. A report that printed
    one of them under the other's name would say "two callers" where it meant
    "one caller, two places".
    """
    callee = MethodRef(
        class_name="com.example.Crypto",
        name="sign",
        descriptor="([Ljava/lang/String;)Ljava/lang/String;",
        provenance=_provenance(
            apk_sha256,
            "androguard:classes.dex#com.example.Crypto#com.example.Crypto.sign"
            "([Ljava/lang/String;)Ljava/lang/String;",
        ),
    )
    caller = _caller(apk_sha256, 0)
    sites = [_site(apk_sha256, caller, offset=4), _site(apk_sha256, caller, offset=12)]
    classes = [
        ClassRef(
            name=method.class_name,
            kind=ClassKind.CLASS,
            provenance=_provenance(apk_sha256, f"androguard:classes.dex#{method.class_name}"),
        )
        for method in (callee, caller)
    ]
    return classes, [callee, caller], sites


def test_the_two_numbers_tell_a_repeated_call_apart(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One caller, two calls: two call sites and one call edge.

    The record names the caller once, so the number of callers is one while
    the number of call sites is two. The two numbers have to be stated
    separately, or the reader is told "one place" where the code makes the
    call twice.
    """
    classes, methods, sites = _one_caller_twice(_hash_of(minimal_apk))
    analyzer = Analyzer(settings)

    def extract(*args: object, **kwargs: object):
        return classes, methods, [], sites, [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    result = analyzer.analyze(minimal_apk, include_jadx=False, include_apktool=False)

    summary = build_json_report(result)["summary"]

    assert summary["call_sites"] == 2, "the two calls are two places in the bytecode"
    assert summary["call_edges"] == 1, "the two calls are one relationship"
    assert summary["call_sites_with_evidence"] == 2
    assert summary["call_edges_with_evidence"] == 1
    assert summary["cross_reference_records"] == 1

    report = render_markdown(result)
    assert "| Call sites indexed | 2 |" in report
    assert "| Call edges indexed | 1 |" in report
