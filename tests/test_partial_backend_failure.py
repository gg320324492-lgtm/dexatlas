"""A backend that fails on part of an APK does not erase the rest of the evidence.

Androguard reads an APK's DEX files one at a time. A DEX file that cannot be
parsed is a gap in the index — the classes and the call edges it holds are
missing — and it says nothing at all about the DEX files that were read.

The pipeline used to treat the failure as a reason to draw no conclusion from
the whole APK: one unparseable DEX file and the class declarations and the
cross-references of every *other* DEX file were dropped, while the symbols
were still written to the database. The report then showed a clean index and
"0 cross-references with evidence", which reads as a conclusion — that the app
has no internal calls — about an APK whose other DEX file was never read.

The second half of the defect is the report. An index that is short must say
so, next to the numbers it makes short, and say why.

Both fixtures are built in a temporary directory out of the project's own
first-party samples: no third-party APK enters this repository, and none is
needed here. They are analysed with only the DEX reader enabled, so the test
is the same on a machine with a decompiler and on one without.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import EvidenceKind, ToolErrorCode
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

EXAMPLES = Path(__file__).parent.parent / "examples"

#: Bytes that are not a DEX file. Androguard refuses them with a parse error.
NOT_A_DEX = b"this is not a dex file at all" * 8


def _break_one_dex(source: Path, target: Path, dex_name: str) -> Path:
    """A copy of ``source`` whose ``dex_name`` cannot be parsed.

    The rest of the archive is copied byte for byte, so the DEX files that are
    left are exactly the ones the sample was built with.
    """
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        assert dex_name in names, f"{source.name} has no {dex_name}"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
            for info in archive.infolist():
                payload = archive.read(info.filename)
                if info.filename == dex_name:
                    payload = NOT_A_DEX
                out.writestr(info, payload)
    return target


def _analyze(settings: Settings, apk: Path):
    """Analyse an APK with the DEX reader alone.

    The decompiler and the resource reader are left out on purpose: the defect
    is in the DEX index, and a test that depends on which external tools a
    machine happens to have is a test that answers a different question on a
    different machine.
    """
    return Analyzer(settings).analyze(apk, include_jadx=False, include_apktool=False)


@pytest.fixture
def broken_multidex(settings: Settings, tmp_path: Path) -> Path:
    """The multi-dex sample with its second DEX file replaced by noise."""
    return _break_one_dex(
        EXAMPLES / "multidex-app" / "multidex.apk",
        tmp_path / "broken-multidex.apk",
        "classes2.dex",
    )


@pytest.fixture
def broken_demo(settings: Settings, tmp_path: Path) -> Path:
    """A single-DEX sample with a second, unparseable DEX file added.

    The demo application calls one of its own methods, so its surviving DEX
    file has an internal call in it — a call edge that has to survive as
    evidence.
    """
    source = EXAMPLES / "demo-app" / "demo.apk"
    target = tmp_path / "broken-demo.apk"
    with (
        zipfile.ZipFile(source) as archive,
        zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out,
    ):
        for info in archive.infolist():
            out.writestr(info, archive.read(info.filename))
        out.writestr("classes2.dex", NOT_A_DEX)
    return target


# -- the evidence of the DEX files that were read is not thrown away --------


def test_the_surviving_dex_keeps_its_class_declarations(
    settings: Settings, broken_multidex: Path
) -> None:
    """The classes of the DEX file that parsed are facts, and they are recorded.

    The failure of one DEX file used to take the class declarations of every
    other DEX file with it: the index held the symbols, and the evidence table
    held no declaration of any of them.
    """
    result = _analyze(settings, broken_multidex)

    declarations = {
        item.summary
        for item in result.evidence
        if item.kind == EvidenceKind.DECLARATION and item.summary.startswith("Class ")
    }

    assert "Class com.example.multidex.PrimaryHelper (class)" in declarations
    assert "Class com.example.multidex.SharedConfig (class)" in declarations


def test_the_surviving_dex_keeps_its_cross_references(
    settings: Settings, broken_demo: Path
) -> None:
    """A call edge that was read out of the bytecode is a fact, and it is recorded.

    This is the conclusion the report used to get wrong. "0 cross-references
    with evidence" reads as "this APK has no internal calls", and the reason
    there were none was that the DEX reader was told to say nothing at all.
    """
    result = _analyze(settings, broken_demo)

    cross_references = [
        item for item in result.evidence if item.kind == EvidenceKind.CROSS_REFERENCE
    ]

    assert cross_references, "the call edges of the DEX file that parsed were dropped"
    assert any("Crypto.sign" in item.summary for item in cross_references)
    for item in cross_references:
        assert item.detail["callers"], item.summary
        assert item.provenance, item.summary


def test_the_index_still_holds_the_symbols_of_the_dex_that_parsed(
    settings: Settings, broken_multidex: Path
) -> None:
    """The symbols were in the database all along; the evidence was what was lost."""
    result = _analyze(settings, broken_multidex)

    assert result.project.class_count == 2
    assert result.project.method_count == 6
    assert result.project.reference_count == 6


# -- the failure is recorded once, and it is found -----------------------


def test_the_parse_failure_is_recorded_on_the_project(
    settings: Settings, broken_multidex: Path
) -> None:
    result = _analyze(settings, broken_multidex)

    failures = [error for error in result.project.errors if error.code is ToolErrorCode.PARSE_ERROR]

    assert failures, "the parse failure was not recorded"
    assert "classes2.dex" in failures[0].message


def test_the_parse_failure_is_recorded_once(settings: Settings, broken_multidex: Path) -> None:
    """The error is in ``project.errors`` and in the evidence table. It is not
    recorded a third time as a second, redundant error."""
    result = _analyze(settings, broken_multidex)

    parse_failures = [
        error for error in result.project.errors if error.code is ToolErrorCode.PARSE_ERROR
    ]
    assert len(parse_failures) == 1

    recorded = [
        item
        for item in result.evidence
        if any(
            provenance.locator == "androguard:error/parse_error" for provenance in item.provenance
        )
    ]
    assert len(recorded) == 1, "the failure was recorded more than once"


# -- the report says the index is short, and why --------------------------


def test_the_report_says_the_index_is_incomplete(settings: Settings, broken_multidex: Path) -> None:
    """A count of what was indexed reads as a count of what the APK holds.

    The reader has to be told, next to the numbers, that the index is short —
    and told which file could not be read, or the report has not said why.
    """
    result = _analyze(settings, broken_multidex)

    report = render_markdown(result)

    assert "| Index completeness | incomplete: androguard could not parse classes2.dex |" in report
    # The note is a block quote: a line that starts with the marker, so that it
    # is read as a note about the numbers above it and not as another table.
    assert any(
        line.startswith("> **This index is incomplete.**") for line in report.splitlines()
    ), "the note about the incomplete index is not a block quote"
    # It has to reach the reader before the evidence table does: the numbers
    # it qualifies are above it, and the reader has to meet the qualification
    # first.
    assert report.index("This index is incomplete") < report.index("## Evidence levels")


def test_the_json_report_says_the_index_is_incomplete(
    settings: Settings, broken_multidex: Path
) -> None:
    result = _analyze(settings, broken_multidex)

    summary = build_json_report(result)["summary"]

    assert summary["index_complete"] is False
    assert [gap["tool"] for gap in summary["index_gaps"]] == ["androguard"]
    assert "classes2.dex" in summary["index_gaps"][0]["message"]


def test_a_complete_index_says_so(settings: Settings, tmp_path: Path) -> None:
    """An index that covers the whole APK is not announced as broken."""
    source = EXAMPLES / "multidex-app" / "multidex.apk"
    target = tmp_path / "intact.apk"
    target.write_bytes(source.read_bytes())

    result = _analyze(settings, target)

    report = render_markdown(result)
    assert "| Index completeness | complete |" in report
    assert "This index is incomplete" not in report
    assert build_json_report(result)["summary"]["index_complete"] is True


def test_a_failure_that_leaves_the_index_whole_does_not_say_otherwise(
    settings: Settings, tmp_path: Path
) -> None:
    """A missing decompiler is a gap in the *source*, not in the index.

    The index is the DEX reader's work. A decompiler that is not installed
    leaves the index exactly as complete as it was, and saying "incomplete"
    would be a different kind of lie.
    """
    from dexatlas.core.models import ToolError

    source = EXAMPLES / "multidex-app" / "multidex.apk"
    target = tmp_path / "intact.apk"
    target.write_bytes(source.read_bytes())

    result = _analyze(settings, target)
    result.project.errors.append(
        ToolError(
            tool="jadx",
            code=ToolErrorCode.NOT_INSTALLED,
            message="jadx is not installed or not on PATH",
        )
    )

    report = render_markdown(result)

    assert "| Index completeness | complete |" in report
    assert build_json_report(result)["summary"]["index_complete"] is True


def test_every_unparsed_dex_file_is_named(settings: Settings, tmp_path: Path) -> None:
    """Two broken DEX files are two gaps, and the report has to name both.

    Naming only the first would make the index look more complete than it is:
    the reader would conclude that one file is missing from an APK that is
    missing two.
    """
    source = EXAMPLES / "multidex-app" / "multidex.apk"
    target = tmp_path / "twice-broken.apk"
    with (
        zipfile.ZipFile(source) as archive,
        zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out,
    ):
        for info in archive.infolist():
            payload = archive.read(info.filename)
            if info.filename.endswith(".dex"):
                payload = NOT_A_DEX
            out.writestr(info, payload)

    result = _analyze(settings, target)

    report = render_markdown(result)
    assert "classes.dex" in report
    assert "classes2.dex" in report
    assert "| Index completeness | incomplete:" in report


# -- a run that found less does not keep what the earlier run found --------


def test_a_re_analysis_replaces_the_evidence_of_the_earlier_run(
    settings: Settings, tmp_path: Path
) -> None:
    """The evidence table holds the records of the last run, and only those.

    The project id is derived from the APK's hash, so analysing the same APK
    again replaces its index rather than adding to it. The evidence table did
    not: the records of the first run stayed behind, so the report counted the
    records of the second run while the database held the records of both. A
    reader who followed an evidence id from the report into the database
    arrived at a row that the report never mentioned.
    """
    source = EXAMPLES / "multidex-app" / "multidex.apk"
    apk = tmp_path / "multidex.apk"
    apk.write_bytes(source.read_bytes())

    analyzer = Analyzer(settings)
    first = analyzer.analyze(apk)
    first_records = len(first.evidence)
    assert first_records > 0

    # The second run does less: it leaves out the backends that read the
    # manifest and the source. Whatever it finds is the whole of its evidence.
    second = analyzer.analyze(apk, include_jadx=False, include_apktool=False)

    stored = analyzer.store.list_evidence(second.project.id)
    assert len(stored) == len(second.evidence), (
        "the database holds records that this run did not produce"
    )
    assert second.project.evidence_count == len(stored), (
        "the report counts records the database does not hold"
    )
    assert {item.summary for item in stored} == {item.summary for item in second.evidence}
    assert len(second.evidence) < first_records, "the second run found as much as the first"

    report = render_markdown(second)
    assert f"| Evidence records | {second.project.evidence_count} |" in report
