"""End-to-end test against the bundled demo application.

The demo APK is committed so a stranger can run an analysis immediately after cloning.
Its sources are in ``examples/demo-app/`` and ``scripts/build-demo-apk.sh`` rebuilds it,
so it is not a mystery binary.

These assertions pin the numbers the README quotes. If they change, the README is wrong
and this test says so, rather than letting documentation drift from behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.androguard.adapter import androguard_available

pytestmark = pytest.mark.slow

DEMO_APK = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"

#: Methods and cross-references come from the DEX alone, so they hold whether or not a
#: decompiler is installed. The class count deliberately is not asserted as an exact
#: number: Androguard sees the 4 declared classes, and JADX adds synthetic ones such as
#: the generated R class when it is available.
EXPECTED_METHODS = 8
EXPECTED_REFERENCES = 23
MIN_CLASSES_FROM_DEX = 4


@pytest.fixture
def analyzer(settings: Settings) -> Analyzer:
    return Analyzer(settings)


@pytest.fixture
def demo_project(analyzer: Analyzer):
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")
    return analyzer.analyze(DEMO_APK)


@pytest.mark.skipif(not androguard_available(), reason="androguard not installed")
def test_demo_analysis_matches_the_documented_numbers(demo_project) -> None:
    project = demo_project.project

    assert project.method_count == EXPECTED_METHODS
    assert project.reference_count == EXPECTED_REFERENCES
    assert project.class_count >= MIN_CLASSES_FROM_DEX

    # A missing backend is reported, not fatal, so only a *parse* failure is a defect.
    fatal = [e for e in project.errors if e.code.value in {"parse_error", "exit_nonzero"}]
    assert not fatal, f"a backend failed to analyse the demo app: {fatal}"


def test_demo_yields_a_findable_call_chain(analyzer: Analyzer, demo_project) -> None:
    """The xref index must resolve a method id back to its caller.

    This is the property that broke when call targets were stored with Androguard's
    human-readable spacing: the index populated, the reports looked fine, and every
    lookup returned nothing.
    """
    method_id = (
        "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
    )
    callers = analyzer.store.get_method_references(demo_project.project.id, method_id)

    assert callers, "the demo app calls Crypto.sign from onCreate; no callers were found"
    assert any("MainActivity.onCreate" in caller.caller for caller in callers)


def test_demo_source_is_readable_when_a_decompiler_is_available(
    analyzer: Analyzer, demo_project
) -> None:
    source = analyzer.class_source(demo_project.project.id, "com.example.demo.Crypto")
    if source is None:
        pytest.skip("neither JADX nor Apktool installed")

    assert "class" in source
    assert "sign" in source or ".method" in source


def test_demo_report_is_self_consistent(demo_project) -> None:
    import json

    from dexatlas.reports.json_report import build_json_report

    report = build_json_report(demo_project)
    serialised = json.dumps(report)
    summary = json.loads(serialised)["summary"]

    assert json.loads(serialised)["schema_version"] == 1
    assert summary["methods"] == EXPECTED_METHODS
    assert summary["cross_references"] == EXPECTED_REFERENCES
    # Backend gaps are reported, not asserted away.
    assert not [e for e in report["errors"] if e["code"] in {"parse_error", "exit_nonzero"}]
