"""A decompiler that produced nothing has to say that it produced nothing.

The report used to list the decompiler's version among the tools that took
part in the analysis and say nothing at all about the fact that it had
produced no Java. A reader saw a decompiled count of zero next to a version
that said the tool was there, and had no way to tell an APK whose code could
not be read from one that had none: both look like the same report.

The difference is not a nicety. The decompiled flag on every method of the
index is false either way, so the count of zero is true in both cases -- and
it is true for a reason the reader is not told.

The backends are stood in for, so the test asks the same question on a
machine with a decompiler and on one without.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import ManifestInfo, ToolError, ToolErrorCode
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import ToolOutcome
from dexatlas.tools.jadx.adapter import ClassDecompilation, JadxBackend

#: The Java the stand-in decompiler writes when it writes anything at all.
DEMO_JAVA = """package com.example.demo;

public class Crypto {
    public static String sign(String a, String b) {
        return a + b;
    }
}
"""


def _stand_in_for_the_backends(
    monkeypatch: pytest.MonkeyPatch,
    *,
    jadx_produced_nothing: bool,
    jadx_failed: bool = False,
) -> None:
    """Put a decompiler in place of JADX, and a manifest reader in place of Apktool.

    The decompiler writes a class file unless it is told to write nothing.
    When ``jadx_failed`` is set it also fails, which is a different fact and
    is recorded as one.
    """

    def decompile(self, apk: Path, output_dir: Path, **kwargs: object) -> ToolOutcome:
        if not jadx_produced_nothing:
            source = output_dir / "sources" / "com" / "example" / "demo"
            source.mkdir(parents=True, exist_ok=True)
            (source / "Crypto.java").write_text(DEMO_JAVA, encoding="utf-8")
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    def extract(self, *args: object, **kwargs: object):
        if jadx_failed:
            return [], ToolError(
                tool="jadx",
                code=ToolErrorCode.PARSE_ERROR,
                message="jadx could not fully parse the APK",
            )
        return [], None

    def decompilation_status(self, output_dir: Path) -> dict[str, ClassDecompilation]:
        if jadx_produced_nothing:
            return {}
        return {
            "com.example.demo.Crypto": ClassDecompilation(
                decompiled=frozenset({"sign"}), failed=frozenset()
            )
        }

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
    monkeypatch.setattr(JadxBackend, "extract", extract)
    monkeypatch.setattr(JadxBackend, "decompilation_status", decompilation_status)


def _analyze(settings: Settings, apk: Path):
    """Analyse an APK whose decompiler is the stand-in above."""
    return Analyzer(settings).analyze(apk, include_androguard=False)


# -- the report says it ------------------------------------------------------


def test_a_decompiler_that_produced_nothing_is_recorded(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fact is recorded, so the report can state it.

    A reader has to be able to tell an APK whose code could not be read from
    one that had none. The decompiled count is zero in both cases, and the
    count alone cannot say which.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=True)

    result = _analyze(settings, minimal_apk)

    assert any("produced no Java" in item.summary for item in result.evidence), (
        "the decompiler that produced nothing was not recorded"
    )


def test_the_report_says_the_decompiler_produced_nothing(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report mentions it, and not only the database.

    The record has to reach the reader of the report: a fact that lives only
    in the evidence table is a fact the report does not state.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=True)

    result = _analyze(settings, minimal_apk)

    assert "produced no Java" in render_markdown(result)


def test_the_tool_version_is_still_listed(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The decompiler ran, so its version belongs in the report.

    The version is not the defect. The decompiler really was there and
    really was asked; what it did not do is produce any Java, and that is
    what had to be said as well.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=True)

    result = _analyze(settings, minimal_apk)

    assert "jadx 1.5.2" in render_markdown(result)


def test_the_json_report_carries_the_fact(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The machine-readable report says it too.

    A fact that is only in the Markdown form is a fact the other reader does
    not have, and the JSON report is the one a program reads.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=True)

    result = _analyze(settings, minimal_apk)

    summaries = [item["summary"] for item in build_json_report(result)["evidence"]]
    assert any("produced no Java" in summary for summary in summaries)


# -- a failure is a failure, and is not recorded twice -----------------------


def test_a_decompiler_that_failed_is_not_also_reported_as_producing_nothing(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure is already recorded as a failure.

    "jadx did not complete" and "jadx produced no Java" are two readings of
    the same run, and the report should give one of them rather than both:
    a reader who is told the decompiler failed is not left needing to be
    told that it also produced nothing.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=True, jadx_failed=True)

    result = _analyze(settings, minimal_apk)

    assert not any("produced no Java" in item.summary for item in result.evidence), (
        "a failed decompiler was reported twice, in two words"
    )
    assert any(error.code is ToolErrorCode.PARSE_ERROR for error in result.project.errors), (
        "the failure was not recorded on the project"
    )
    assert any("did not complete" in item.summary for item in result.evidence), (
        "the failure was not recorded in the evidence"
    )


def test_a_decompiler_that_produced_something_is_not_reported_as_producing_nothing(
    settings: Settings, minimal_apk: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record is about the decompiler producing nothing at all.

    A decompiler that wrote Java for some classes and not for others is
    already covered by the coverage record; this one is about the empty
    case, and it must not fire on a run that read something.
    """
    _stand_in_for_the_backends(monkeypatch, jadx_produced_nothing=False)

    result = _analyze(settings, minimal_apk)

    assert not any("produced no Java" in item.summary for item in result.evidence), (
        "a decompiler that produced Java was reported as producing none"
    )
