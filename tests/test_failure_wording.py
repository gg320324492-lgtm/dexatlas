"""A backend that was stopped part-way says so — and says what it left behind.

The M10 reader rehearsal (gap M-2, recorded in
``docs/reports/evidence-incomplete-backend-wording.md``; the rehearsal
document itself was removed in the 2026-11-21 de-platformisation cleanup)
recorded a report that carried two ``verified`` records about the same backend,
wording that contradicted each other:

    E-0007 │ jadx did not complete: jadx exceeded its 1s timeout and was terminated
    E-0008 │ jadx produced real Java for 7 of 8 methods in 5 of 5 classes

Both were true. A backend that did not finish is not a backend that produced
nothing: JADX was killed after it had written Java for seven of the eight
methods, and that output was in the evidence. The old wording said only that
the step did not complete, which a reader reads as "this tool delivered
nothing" — and then the two records look like a broken evidence chain, which
is the one conclusion the rehearsal reader must not reach.

These tests hold two things:

* the wording keeps "this step did not finish" and "what it delivered before it
  stopped" apart, so the reader can tell the two records are about different
  things;
* the level did not move. The level is the contract face of the evidence, and
  "change the wording" must not quietly become "change the level too" — so a
  test stands guard over it, because nothing else would notice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    EvidenceKind,
    EvidenceLevel,
    ManifestInfo,
    MethodRef,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown
from dexatlas.tools.androguard.adapter import AndroguardBackend
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import ToolOutcome
from dexatlas.tools.jadx.adapter import ClassDecompilation, JadxBackend

#: The five classes the DEX reader saw.
_CLASSES = ("Alpha", "Bravo", "Charlie", "Delta", "Echo")

#: The methods in them: eight methods in five classes.
_METHODS: dict[str, tuple[str, ...]] = {
    "Alpha": ("a1", "a2"),
    "Bravo": ("b1", "b2"),
    "Charlie": ("c1",),
    "Delta": ("d1", "d2"),
    "Echo": ("e1",),
}

#: The methods JADX wrote Java for before it was stopped. ``Echo.e1`` is the one
#: it never reached — which is why the coverage is 7 of 8 and not 8 of 8.
_DECOMPILED: dict[str, frozenset[str]] = {
    "Alpha": frozenset({"a1", "a2"}),
    "Bravo": frozenset({"b1", "b2"}),
    "Charlie": frozenset({"c1"}),
    "Delta": frozenset({"d1", "d2"}),
    "Echo": frozenset(),
}

#: The Java the stand-in decompiler writes before it is stopped.
_DEMO_JAVA = """package com.example.demo;

public class Alpha {
    public static String sign(String a, String b) {
        return a + b;
    }
}
"""


def _builder() -> EvidenceBuilder:
    return EvidenceBuilder(
        project_id="apk_test",
        tool_versions={"jadx": "1.5.2"},
        apk_sha256="b" * 64,
    )


def _timeout_error() -> ToolError:
    return ToolError(
        tool="jadx",
        code=ToolErrorCode.TIMEOUT,
        message="jadx exceeded its 1s timeout and was terminated",
    )


def _missing_error() -> ToolError:
    return ToolError(
        tool="jadx",
        code=ToolErrorCode.NOT_INSTALLED,
        message="jadx is not installed or not on PATH",
    )


# -- the wording -------------------------------------------------------------


def test_a_stopped_backend_says_it_stopped_part_way() -> None:
    """The record says the step did not finish, and says it was part-way.

    "Did not complete" alone reads as "delivered nothing", which is not what
    happened and not what the record is about.
    """
    record = _builder().add_error(_timeout_error())

    assert "did not complete in this run" in record.summary
    assert "stopped part-way" in record.summary


def test_a_stopped_backend_says_what_it_left_behind() -> None:
    """The record says the output it had produced is recorded separately.

    This is the sentence that keeps the failure record and the coverage record
    from reading as a contradiction.
    """
    record = _builder().add_error(_timeout_error())

    assert "recorded separately, not withheld" in record.summary


def test_a_stopped_backend_does_not_say_it_produced_nothing() -> None:
    """It had produced something, and the record may not deny it.

    The claim is about the step, not about the output — and the sentence that
    would deny the output is the one that made the two records contradict each
    other.
    """
    record = _builder().add_error(_timeout_error())

    assert "produced nothing" not in record.summary


def test_a_backend_that_never_ran_says_it_produced_nothing() -> None:
    """A tool that was never run has no output, and the record says so.

    The other case is the opposite one, and keeping it apart is the point: the
    reader has to be able to tell "stopped part-way" from "never ran".
    """
    record = _builder().add_error(_missing_error())

    assert "did not complete in this run" in record.summary
    assert "never ran" in record.summary
    assert "produced nothing" in record.summary


# -- the level did not move --------------------------------------------------


@pytest.mark.parametrize("error", [_timeout_error(), _missing_error()])
def test_a_failure_record_is_still_verified(error: ToolError) -> None:
    """The level of a failure record is the contract, and it did not change.

    The wording was changed because a reader drew the wrong conclusion from
    it. The level was left alone on purpose: what "verified" means is the
    public contract, and a change to it is a different decision with a
    different kind of review. A test stands here so that nobody changes it by
    accident, in the belief that the wording fix went further than it did.
    """
    record = _builder().add_error(error)

    assert record.level is EvidenceLevel.VERIFIED
    assert record.kind is EvidenceKind.OBSERVATION


# -- the report a reader gets ------------------------------------------------


def _stand_in_for_the_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """A decompiler that was stopped part-way, and a DEX reader that saw the APK.

    The decompiler writes some Java and is then terminated: the shape of the
    timeout the rehearsal report recorded, and the shape that puts a failure
    record and a coverage record next to each other in one report.
    """

    def decompile(self, apk: Path, output_dir: Path, **kwargs: object) -> ToolOutcome:
        source = output_dir / "sources" / "com" / "example" / "demo"
        source.mkdir(parents=True, exist_ok=True)
        (source / "Alpha.java").write_text(_DEMO_JAVA, encoding="utf-8")
        return ToolOutcome(
            returncode=-1,
            stdout="",
            stderr="jadx exceeded its 1s timeout and was terminated",
            duration_seconds=1.0,
            error=_timeout_error(),
        )

    def jadx_extract(self, apk_sha256: str, output_dir: Path, outcome: ToolOutcome):
        classes = [
            _class_ref(name, "jadx", f"jadx:sources/com/example/demo/{name}.java")
            for name in _CLASSES
        ]
        return classes, outcome.error

    def decompilation_status(self, output_dir: Path) -> dict[str, ClassDecompilation]:
        return {
            f"com.example.demo.{name}": ClassDecompilation(decompiled=_DECOMPILED[name])
            for name in _CLASSES
        }

    def androguard_extract(self, apk: Path, apk_sha256: str):
        classes = [_class_ref(name, "androguard", "androguard:classes.dex") for name in _CLASSES]
        methods = [
            MethodRef(
                class_name=f"com.example.demo.{class_name}",
                name=method_name,
                descriptor="()V",
                provenance=[
                    Provenance(
                        tool="androguard",
                        tool_version=None,
                        apk_sha256=apk_sha256,
                        locator="androguard:classes.dex",
                    )
                ],
            )
            for class_name, method_names in _METHODS.items()
            for method_name in method_names
        ]
        return classes, methods, [], [], [], None

    monkeypatch.setattr(ApktoolBackend, "resolve", lambda self: Path("/fake/apktool.jar"))
    monkeypatch.setattr(ApktoolBackend, "version", lambda self: "2.9.3")
    monkeypatch.setattr(
        ApktoolBackend,
        "decode",
        lambda self, apk, output_dir: ToolOutcome(
            returncode=0, stdout="", stderr="", duration_seconds=0.0
        ),
    )
    monkeypatch.setattr(
        ApktoolBackend,
        "read_manifest",
        lambda self, output_dir: (
            ManifestInfo(package="com.example.demo", version_name="1.0"),
            None,
        ),
    )
    monkeypatch.setattr(ApktoolBackend, "read_resources", lambda self, output_dir, sha: ([], []))

    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("/fake/jadx"))
    monkeypatch.setattr(JadxBackend, "version", lambda self: "1.5.2")
    monkeypatch.setattr(JadxBackend, "decompile", decompile)
    monkeypatch.setattr(JadxBackend, "extract", jadx_extract)
    monkeypatch.setattr(JadxBackend, "decompilation_status", decompilation_status)

    monkeypatch.setattr(AndroguardBackend, "extract", androguard_extract)


def _class_ref(name: str, tool: str, locator: str) -> ClassRef:
    return ClassRef(
        name=f"com.example.demo.{name}",
        kind=ClassKind.CLASS,
        provenance=[
            Provenance(
                tool=tool,
                tool_version=None,
                apk_sha256="b" * 64,
                locator=locator,
            )
        ],
    )


def _analyze(settings: Settings, apk: Path):
    return Analyzer(settings).analyze(apk)


def test_the_failure_record_and_the_coverage_record_are_not_a_contradiction(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both records are in the report, and they say different things.

    This is the rehearsal report's gap, reproduced: one report, one backend,
    two ``verified`` records. The failure record is about the step; the
    coverage record is about the output. A reader who draws both has to be
    able to see that they are about different things.
    """
    _stand_in_for_the_backends(monkeypatch)

    result = _analyze(settings, minimal_apk)

    failures = [item for item in result.evidence if "did not complete" in item.summary]
    coverage = [item for item in result.evidence if "produced real Java" in item.summary]

    assert failures, "the stopped decompiler was not recorded"
    assert coverage, "the output it had produced was not recorded"
    assert all(item.level is EvidenceLevel.VERIFIED for item in failures + coverage)
    assert "recorded separately, not withheld" in failures[0].summary
    assert "produced nothing" not in failures[0].summary


def test_the_counts_the_report_gives_are_the_ones_the_analysis_made(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wording changed; the counts did not.

    Seven of eight methods and five of five classes are what the analysis
    found, and the record has to keep saying so: a fix to the wording that
    moved a number would be a different change, with a different review.
    """
    _stand_in_for_the_backends(monkeypatch)

    result = _analyze(settings, minimal_apk)

    coverage = next(item for item in result.evidence if "produced real Java" in item.summary)
    assert "7 of 8 methods in 5 of 5 classes" in coverage.summary
    detail = coverage.detail["decompilation"]
    assert detail["methods_decompiled"] == 7
    assert detail["methods_total"] == 8
    assert detail["methods_jadx_failed"] == []


def test_the_report_and_the_json_report_carry_the_wording(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader is the one who has to be able to tell them apart.

    A wording that only lives in the database is a wording no reader sees,
    and the reader is who the change was for.
    """
    _stand_in_for_the_backends(monkeypatch)

    result = _analyze(settings, minimal_apk)

    assert "recorded separately, not withheld" in render_markdown(result)
    summaries = [item["summary"] for item in build_json_report(result)["evidence"]]
    assert any("recorded separately, not withheld" in summary for summary in summaries)
