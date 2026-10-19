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

    The id here is written out by hand, which is what made this test miss the second
    break of the same property: the method table spaced its descriptors and the
    cross-reference table did not, so the id a user could copy was the id that could
    not be looked up. ``test_demo_method_ids_resolve_to_their_callers`` covers the
    path a user actually takes.
    """
    method_id = (
        "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
    )
    callers = analyzer.store.get_method_references(demo_project.project.id, method_id)

    assert callers, "the demo app calls Crypto.sign from onCreate; no callers were found"
    assert any("MainActivity.onCreate" in caller.caller for caller in callers)


def _demo_methods(analyzer: Analyzer, project_id: str) -> dict[str, object]:
    return {m.qualified_name: m for m in analyzer.store.list_methods(project_id)}


def test_demo_method_ids_resolve_to_their_callers(analyzer: Analyzer, demo_project) -> None:
    """An id copied out of `dexatlas methods` must resolve in `dexatlas xrefs`.

    The id is taken from the method table, not written by hand: the whole point is
    that the two tables agree on how a method is spelled. A two-argument method is
    where they used to disagree, because a space after the argument separator is the
    only difference between the two spellings.
    """
    project_id = demo_project.project.id
    methods = _demo_methods(analyzer, project_id)

    sign = next(m for m in methods.values() if m.name == "sign")
    assert " " not in sign.qualified_name, (
        f"the method id carries whitespace and cannot match a stored callee: "
        f"{sign.qualified_name!r}"
    )

    callers = analyzer.store.get_method_references(project_id, sign.qualified_name)

    assert callers, "the demo app calls Crypto.sign from onCreate; no callers were found"
    assert any("MainActivity.onCreate" in caller.caller for caller in callers)


def test_a_single_argument_method_id_resolves_to_its_caller(
    analyzer: Analyzer, demo_project
) -> None:
    """A one-argument method has no separator, so it was never broken by the
    spacing — and it must keep resolving."""
    project_id = demo_project.project.id
    methods = _demo_methods(analyzer, project_id)

    describe = next(m for m in methods.values() if m.name == "describe")
    callers = analyzer.store.get_method_references(project_id, describe.qualified_name)

    assert callers, "the demo app calls MainActivity.describe from onCreate"
    assert any("MainActivity.onCreate" in caller.caller for caller in callers)


def test_every_declared_callee_is_findable_by_its_own_method_id(
    analyzer: Analyzer, demo_project
) -> None:
    """The method table and the cross-reference table must agree on one spelling.

    Every call whose target is a method this app declares has to be found by
    looking that method up with the id the method table prints. This is the
    general form of the property that broke: a cross-reference index that cannot be
    read back with the ids the tool hands out looks exactly like one that has
    nothing to report.
    """
    project_id = demo_project.project.id
    declared = {m.qualified_name for m in analyzer.store.list_methods(project_id)}

    with analyzer.store.transaction() as connection:
        rows = connection.execute(
            "SELECT caller, callee FROM xrefs WHERE project_id = ?", (project_id,)
        ).fetchall()
    calls = {(row["caller"], row["callee"]) for row in rows if row["callee"] in declared}

    assert calls, "the demo app has no calls into its own methods"

    for caller, callee in calls:
        found = analyzer.store.get_method_references(project_id, callee)
        assert any(ref.caller == caller for ref in found), (
            f"the call {caller} -> {callee} is not found under the callee's own id"
        )


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
