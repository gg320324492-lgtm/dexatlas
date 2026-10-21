"""The evidence table keeps the conclusions, and says that it is short.

The report's evidence table shows the first two hundred records and no more.
The records were recorded in the order the analysis found them — the
manifest's conclusions, then the cross-references, then a class declaration
per class, and last of all the decompilation coverage — so on an APK with
more than two hundred classes the coverage record was the one that fell off
the end. The metric row that states the coverage stayed in the report, and
the evidence behind it did not: the report claimed a number it no longer
showed the reader where it came from.

The order the analysis records its evidence in is the order the report shows,
so the fix is in the order: the conclusions are recorded first and the index
— the class declarations — last, because what is recorded last is what gets
dropped.

The second half of the defect is the report. A table that shows two hundred
of five hundred records has to say so *where the table is*, not in a note
underneath it that a reader who has already read the table never sees.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    DECOMPILATION_DETAIL,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    MethodRef,
    Provenance,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.markdown import render_markdown
from dexatlas.tools.base import ToolOutcome
from dexatlas.tools.jadx.adapter import ClassDecompilation

#: The size of the report's evidence table.
_TABLE_ROWS = 200

#: More classes than the table has rows, so that the table has to cut some.
_CLASSES = 250


def _provenance(tool: str = "androguard") -> list[Provenance]:
    return [
        Provenance(
            tool=tool,
            tool_version="4.1.4",
            apk_sha256="a" * 64,
            locator="classes.dex",
        )
    ]


def _fake_backends(analyzer: Analyzer, monkeypatch: pytest.MonkeyPatch, classes: int) -> None:
    """A DEX reader with many classes, and a decompiler that read one of them."""
    class_refs = [
        ClassRef(
            name=f"com.example.C{index}",
            kind=ClassKind.CLASS,
            provenance=_provenance(),
        )
        for index in range(classes)
    ]
    methods = [
        MethodRef(
            class_name="com.example.C0",
            name="work",
            descriptor="()V",
            provenance=_provenance(),
        )
    ]

    def extract(*args: object, **kwargs: object):
        return class_refs, methods, [], [], [], None

    monkeypatch.setattr(analyzer._androguard, "extract", extract)
    monkeypatch.setattr(analyzer._jadx, "available", lambda: True)
    monkeypatch.setattr(
        analyzer._jadx,
        "decompile",
        lambda *args, **kwargs: ToolOutcome(
            returncode=0, stdout="", stderr="", duration_seconds=0.0
        ),
    )
    monkeypatch.setattr(analyzer._jadx, "extract", lambda *args, **kwargs: ([], None))
    monkeypatch.setattr(
        analyzer._jadx,
        "decompilation_status",
        lambda *args, **kwargs: {
            "com.example.C0": ClassDecompilation(decompiled=frozenset({"work"}))
        },
    )


def _decompilation_records(evidence: list[Evidence]) -> list[Evidence]:
    return [item for item in evidence if DECOMPILATION_DETAIL in item.detail]


def _table_ids(report: str) -> list[str]:
    """The evidence ids the report's table shows, in the order it shows them."""
    ids: list[str] = []
    for line in report.splitlines():
        if line.startswith("| `E-"):
            ids.append(line.split("`")[1])
    return ids


# -- the order the analysis records its evidence in -------------------------


def test_the_decompilation_coverage_is_recorded_before_the_class_declarations(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record that fell off the end of the table was recorded last.

    The class declarations are the index of the APK, and there is one per
    class. The coverage is a conclusion about the whole APK, and it has to be
    recorded before the index or it is the first thing the report drops.
    """
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, _CLASSES)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    coverage = _decompilation_records(result.evidence)
    assert len(coverage) == 1, "the decompilation coverage was not recorded"
    declarations = [
        index
        for index, item in enumerate(result.evidence)
        if item.kind is EvidenceKind.DECLARATION and item.summary.startswith("Class ")
    ]
    assert declarations, "the class declarations were not recorded"
    assert result.evidence.index(coverage[0]) < declarations[0], (
        "the coverage is recorded after the class declarations, so it is the "
        "first record the report's cap drops"
    )


# -- the report's table ------------------------------------------------------


def test_the_decompilation_coverage_is_in_the_report_s_evidence_table(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The metric row is in the report, and so is the record behind it.

    The report promises that every row can be checked. A metric without the
    record that states it is a number the reader has to take on trust.
    """
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, _CLASSES)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    coverage = _decompilation_records(result.evidence)
    assert len(coverage) == 1
    record = coverage[0]

    report = render_markdown(result)

    assert "| Methods decompiled by JADX | 1 of 1 |" in report
    assert f"| `{record.id}` |" in report, "the record behind the metric is not in the table"
    assert record.summary in report


def test_the_table_is_the_window_the_report_actually_keeps(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The table holds the first records of the analysis, and no others.

    The window is the data's, not a constant's: the ids in the table are the
    ids of the records that come first.
    """
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, _CLASSES)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    report = render_markdown(result)
    shown = _table_ids(report)

    assert len(shown) == _TABLE_ROWS
    assert shown == [item.id for item in result.evidence[:_TABLE_ROWS]]


def test_the_report_says_how_many_records_it_left_out(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The omission is counted from the records, and stated."""
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, _CLASSES)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    report = render_markdown(result)
    omitted = len(result.evidence) - _TABLE_ROWS

    assert omitted > 0, "the fixture has to be big enough to overflow the table"
    assert f"{omitted} further evidence records omitted" in report


def test_the_report_says_it_is_truncated_where_the_table_is(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reader looking at the table has to know that the table is not all of it.

    The notice comes before the table, not under it: a note under a table of
    two hundred rows is a note that a reader who has read the table does not
    read.
    """
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, _CLASSES)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    report = render_markdown(result)

    assert "This table is truncated" in report
    assert report.index("This table is truncated") < report.index("| ID | Level | Kind |")
    # And it says what the omitted records were, so that a reader who knows
    # the APK has two thousand classes can tell what the table is missing.
    assert "class declarations" in report


def test_a_report_that_fits_says_nothing_about_truncation(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A note that is always there is a note nobody reads."""
    analyzer = Analyzer(settings)
    _fake_backends(analyzer, monkeypatch, 3)

    result = analyzer.analyze(minimal_apk, include_apktool=False)

    report = render_markdown(result)

    assert "This table is truncated" not in report
    assert "further evidence records omitted" not in report
    assert "| Methods decompiled by JADX | 1 of 1 |" in report
