"""The first-party test applications.

The Phase 1 acceptance checklist calls for five test APKs **built by this project**,
each verifying the import and index pipeline. These are them, under ``examples/``,
with their smali sources committed beside them so none is a mystery binary:
``scripts/build-test-apks.sh`` rebuilds every one of them.

They are not interchangeable, and that is the point. A single sample would let a
pipeline that handles one layout look like a pipeline that handles them all:

- ``demo-app``       the general case
- ``multidex-app``   two dexes, so ``smali/`` and ``smali_classes2/`` both exist
- ``obfuscated-app`` one-letter packages, classes and methods, no source hints
- ``strings-app``    mostly string constants, for the search index
- ``wide-app``       an interface with two implementations and a factory
"""

from __future__ import annotations

import sqlite3
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    InvocationKind,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed"
    ),
]

EXAMPLES = Path(__file__).parent.parent / "examples"

#: Every sample, and the APK file inside it.
SAMPLE_APKS = {
    "demo-app": "demo.apk",
    "multidex-app": "multidex.apk",
    "obfuscated-app": "obfuscated.apk",
    "strings-app": "strings.apk",
    "wide-app": "wide.apk",
}

#: The multi-dex sample's classes, and the directory Apktool decodes each dex into.
MULTIDEX_CLASSES = [
    ("com.example.multidex.PrimaryHelper", "smali"),
    ("com.example.multidex.SharedConfig", "smali"),
    ("com.example.multidex.SecondaryHelper", "smali_classes2"),
    ("com.example.multidex.PayloadLoader", "smali_classes2"),
]


def _sample_apk(name: str) -> Path:
    return EXAMPLES / name / SAMPLE_APKS[name]


@pytest.fixture(scope="module")
def jadx_unavailable() -> Iterator[None]:
    """Make JADX report itself unavailable for every test in this module.

    Pointing ``settings.jadx_path`` at a directory that does not exist does not work:
    ``which_or_none`` falls back to a ``PATH`` lookup, so a JADX installed there is
    still found and the decompiler answers instead of the fallback being tested.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(JadxBackend, "resolve", lambda self: None)
        yield


@pytest.fixture(scope="module")
def samples(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Analyse every sample once and share the analyzer and the project ids.

    Each analysis decodes and decompiles a real APK, so doing it five times per test
    would be needlessly slow. The fixture owns its own settings because the
    repository's ``settings`` fixture is function-scoped.
    """
    workspace = tmp_path_factory.mktemp("first-party")
    settings = Settings(workspace=workspace)
    analyzer = Analyzer(settings)

    # Whether a decompiler was there to answer. The answer decides what the index
    # may claim, so it is recorded with the analysis rather than read off the
    # environment afterwards: a machine with JADX installed and a machine without
    # it are two configurations, and the analysis has to be right in both.
    jadx_available = JadxBackend(settings).resolve() is not None

    results: dict[str, object] = {}
    for name in SAMPLE_APKS:
        apk = _sample_apk(name)
        if not apk.is_file():
            pytest.skip(f"sample {name} is missing; run scripts/build-test-apks.sh")
        result = analyzer.analyze(apk)
        results[name] = result.project

    return {
        "analyzer": analyzer,
        "settings": settings,
        "projects": results,
        "jadx_available": jadx_available,
    }


@pytest.fixture(scope="module")
def demo_without_jadx(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Analyse the demo application again, with the decompiler taken away.

    The samples above share one analysis, run under whatever the machine happens
    to have installed. A missing decompiler is a configuration of its own — the
    one the Smali fallback exists for — so it is analysed here on every machine
    rather than only on the ones that happen to lack JADX.
    """
    apk = _sample_apk("demo-app")
    if not apk.is_file():
        pytest.skip("sample demo-app is missing; run scripts/build-test-apks.sh")

    workspace = tmp_path_factory.mktemp("first-party-no-jadx")
    settings = Settings(workspace=workspace)
    analyzer = Analyzer(settings)

    with pytest.MonkeyPatch.context() as patch:
        # Not a path that does not exist: ``which_or_none`` falls back to a
        # ``PATH`` lookup, so a JADX installed there would still be found and
        # the decompiler would answer instead of the fallback being tested.
        patch.setattr(JadxBackend, "resolve", lambda self: None)
        result = analyzer.analyze(apk)

    return {
        "analyzer": analyzer,
        "project_id": result.project.id,
        "evidence": analyzer.store.list_evidence(result.project.id),
    }


def _analyzer(samples: dict[str, object]) -> Analyzer:
    analyzer: Analyzer = samples["analyzer"]  # type: ignore[assignment]
    return analyzer


def _project_id(samples: dict[str, object], name: str) -> str:
    projects: dict[str, object] = samples["projects"]  # type: ignore[assignment]
    project = projects[name]
    return project.id  # type: ignore[union-attr]


def _decompiled_flags(analyzer: Analyzer, project_id: str) -> dict[str, bool]:
    """Every indexed method, by qualified name, with its ``decompiled`` flag."""
    return {
        method.qualified_name: method.decompiled
        for method in analyzer.store.list_methods(project_id)
    }


def _analyzer_of(fixture: dict[str, object]) -> Analyzer:
    analyzer: Analyzer = fixture["analyzer"]  # type: ignore[assignment]
    return analyzer


def _project_of(fixture: dict[str, object]) -> str:
    project_id: str = fixture["project_id"]  # type: ignore[assignment]
    return project_id


def _evidence_of(fixture: dict[str, object]) -> list[Evidence]:
    evidence: list[Evidence] = fixture["evidence"]  # type: ignore[assignment]
    return evidence


def _decompilation_coverage(evidence: list[Evidence]) -> dict[str, object] | None:
    """The coverage record an analysis left behind, if it left one."""
    for item in evidence:
        if "decompilation" in item.detail:
            return item.detail["decompilation"]
    return None


def _missing_backend_evidence(evidence: list[Evidence], tool: str) -> Evidence | None:
    """The record of a backend that never ran.

    Such a record cites the tool and cites no version — a tool that did not run
    has no version to quote — and points at the failure in its locator. Every
    locator names its backend, so the failure is addressed as
    ``<tool>:error/<code>``.
    """
    for item in evidence:
        for provenance in item.provenance:
            if provenance.tool == tool and provenance.locator.startswith(f"{tool}:error/"):
                return item
    return None


# -- the samples themselves ------------------------------------------------


@pytest.mark.parametrize("name", sorted(SAMPLE_APKS))
def test_every_sample_is_present_and_is_a_real_apk(name: str) -> None:
    """Each sample must exist, and must be an archive with Android markers.

    The samples are committed, so this fails loudly if one is lost rather than
    letting the tests below skip.
    """
    apk = _sample_apk(name)
    assert apk.is_file(), f"{name} is missing; run scripts/build-test-apks.sh"

    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
    assert "AndroidManifest.xml" in names
    assert any(entry.endswith(".dex") for entry in names)


@pytest.mark.parametrize("name", sorted(SAMPLE_APKS))
def test_every_sample_analyses_without_a_fatal_error(samples: dict[str, object], name: str) -> None:
    """Each sample must produce classes, methods and cross-references.

    A missing backend is recorded, not fatal — that is the architecture. A *parse*
    failure is a defect, and an empty index would mean the sample exercised nothing.
    """
    projects: dict[str, object] = samples["projects"]  # type: ignore[assignment]
    project = projects[name]

    assert project.status.value == "completed", project.errors
    assert project.class_count > 0, "no classes were indexed"
    assert project.method_count > 0, "no methods were indexed"

    fatal = [e for e in project.errors if e.code.value in {"parse_error", "exit_nonzero"}]
    assert not fatal, f"a backend failed on {name}: {fatal}"


@pytest.mark.parametrize("name", sorted(SAMPLE_APKS))
def test_every_sample_has_committed_sources(name: str) -> None:
    """A committed APK is only honest if the smali that produced it is committed too.

    ``scripts/build-test-apks.sh`` rebuilds from these sources, so a sample without
    them would be exactly the mystery binary the project refuses to ship.
    """
    sample_dir = EXAMPLES / name
    assert (sample_dir / "AndroidManifest.xml").is_file()
    assert (sample_dir / "apktool.yml").is_file()

    smali_dirs = [p for p in sample_dir.iterdir() if p.is_dir() and p.name.startswith("smali")]
    assert smali_dirs, f"{name} has no smali sources"

    sources = [p for d in smali_dirs for p in d.rglob("*.smali")]
    assert sources, f"{name} has no smali files"


# -- the multi-dex sample --------------------------------------------------


def test_the_multidex_sample_really_has_two_dexes() -> None:
    """Guard the fixture: the layout below is only meaningful with a second dex."""
    apk = _sample_apk("multidex-app")
    with zipfile.ZipFile(apk) as archive:
        dexes = sorted(n for n in archive.namelist() if n.endswith(".dex"))

    assert dexes == ["classes.dex", "classes2.dex"]


@pytest.mark.parametrize(("class_name", "expected_dir"), MULTIDEX_CLASSES)
def test_a_class_in_the_second_dex_is_found_in_the_right_directory(
    samples: dict[str, object], class_name: str, expected_dir: str
) -> None:
    """The second dex decodes to a *sibling* of ``smali/``, not a child of it.

    This is the layout that the Smali fallback got wrong: it searched for
    ``smali_classes2/`` inside ``smali/``, where it never existed.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "multidex-app")
    workspace = analyzer.store.get_workspace(project_id)
    assert workspace is not None

    path = ApktoolBackend(samples["settings"]).smali_path(class_name, workspace / "apktool")
    assert path is not None, f"{class_name} was not found in any smali directory"
    assert expected_dir in path.parts


def test_the_smali_fallback_reaches_the_second_dex_without_jadx(
    samples: dict[str, object], jadx_unavailable: None
) -> None:
    """With no decompiler, the class in classes2.dex must still be readable.

    This is the whole point of the fallback: an APK that defeats JADX still yields
    its bytecode, and a finding that cannot be read is not a finding.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "multidex-app")

    source = analyzer.class_source(project_id, "com.example.multidex.SecondaryHelper")
    assert source is not None, "the class in the second dex was not reachable"
    assert "Lcom/example/multidex/SecondaryHelper;" in source

    method = analyzer.method_source(
        project_id, "com.example.multidex.SecondaryHelper", "secondaryEndpoint"
    )
    assert method is not None, "the method in the second dex was not reachable"
    assert "https://secondary.example.com/api/v2/sync" in method

    described = analyzer.method_source(
        project_id, "com.example.multidex.SecondaryHelper", "describe"
    )
    assert described is not None
    assert "secondary-dex" in described


def test_a_duplicate_class_name_resolves_to_the_same_file_every_time(
    samples: dict[str, object],
) -> None:
    """``SharedConfig`` exists in both dexes. Whichever wins must win consistently."""
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "multidex-app")
    workspace = analyzer.store.get_workspace(project_id)
    assert workspace is not None

    backend = ApktoolBackend(samples["settings"])
    first = backend.smali_path("com.example.multidex.SharedConfig", workspace / "apktool")
    assert first is not None
    for _ in range(5):
        assert (
            backend.smali_path("com.example.multidex.SharedConfig", workspace / "apktool") == first
        )

    # The primary dex sorts first, so it is the one that wins.
    assert "smali" in first.parts
    assert "smali_classes2" not in first.parts


# -- the obfuscated sample -------------------------------------------------


def test_obfuscated_names_are_still_indexed_and_locatable(samples: dict[str, object]) -> None:
    """One-letter packages, classes and methods carry no information.

    A reader cannot guess them, which is why the tool has to hold the exact names
    and be able to hand them back.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "obfuscated-app")

    classes = {cls.name for cls in analyzer.store.list_classes(project_id)}
    assert "a.a.a" in classes
    assert "a.b.a" in classes

    source = analyzer.class_source(project_id, "a.a.a")
    assert source is not None
    assert "La/a/a;" in source


# -- the strings sample ----------------------------------------------------


def test_string_constants_are_searchable(samples: dict[str, object]) -> None:
    """The string index is where a hardcoded key would be found."""
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "strings-app")

    results = analyzer.search(project_id, "sk_live_PLACEHOLDER")
    assert results, "the API key string was not searchable"
    assert any("sk_live_PLACEHOLDER" in str(item["name"]) for item in results)


def test_a_search_term_with_no_match_returns_nothing(samples: dict[str, object]) -> None:
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "strings-app")

    assert analyzer.search(project_id, "no_such_symbol_anywhere_zzz") == []


# -- the wide sample -------------------------------------------------------


def test_an_interface_method_resolves_back_to_its_caller(samples: dict[str, object]) -> None:
    """The call must be traceable from the callee back to the code that makes it.

    The call site is an ``invoke-interface``, so the reference names the interface
    rather than either implementation — that is how the DEX encodes it.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "wide-app")

    method_id = "com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;"
    callers = analyzer.store.get_method_references(project_id, method_id)

    assert callers, "the interface method had no callers"
    assert any("HandlerFactory.dispatch" in caller.caller for caller in callers)


def test_a_constructor_call_resolves_back_to_its_caller(samples: dict[str, object]) -> None:
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "wide-app")

    method_id = "com.example.wide.JsonHandler.<init>()V"
    callers = analyzer.store.get_method_references(project_id, method_id)

    assert callers, "the constructor had no callers"
    assert any("HandlerFactory.create" in caller.caller for caller in callers)


# -- the numbers the report states ------------------------------------------


def _row_count(analyzer: Analyzer, table: str, project_id: str) -> int:
    with analyzer.store.transaction() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)
        ).fetchone()
    return int(row[0])


def test_the_reported_counts_are_the_rows_in_the_tables(samples: dict[str, object]) -> None:
    """The report's numbers must be the numbers a query returns.

    They used not to be. The method count was taken from the list of symbols
    before the table collapsed the duplicates, so a class defined in two dex
    files was counted twice in the report and once in the database — and
    ``dexatlas methods`` could not show the difference.
    """
    analyzer = _analyzer(samples)

    for name in sorted(SAMPLE_APKS):
        project_id = _project_id(samples, name)
        project = analyzer.store.get_project(project_id)
        assert project is not None, name

        assert project.class_count == len(analyzer.store.list_classes(project_id)), name
        assert project.method_count == len(analyzer.store.list_methods(project_id)), name
        assert project.reference_count == _row_count(analyzer, "xrefs", project_id), name


def test_a_class_row_counts_the_rows_its_own_table_holds(samples: dict[str, object]) -> None:
    """A class row and a method query must agree about the same class.

    The row used to hold the larger of the counts the backends reported. A
    backend reads one dex file, so a class split across two dex files is seen
    partly by each of them, and neither view is the class's total — the
    larger of the two is not either. A class that a query says has four
    methods was reported as having three.
    """
    analyzer = _analyzer(samples)

    for name in sorted(SAMPLE_APKS):
        project_id = _project_id(samples, name)
        with analyzer.store.transaction() as connection:
            rows = connection.execute(
                "SELECT c.name, c.method_count, c.field_count,"
                " (SELECT COUNT(*) FROM methods m"
                "  WHERE m.project_id = c.project_id AND m.class_name = c.name) methods,"
                " (SELECT COUNT(*) FROM fields f"
                "  WHERE f.project_id = c.project_id AND f.class_name = c.name) fields"
                " FROM classes c WHERE c.project_id = ?",
                (project_id,),
            ).fetchall()

        assert rows, name
        for row in rows:
            assert row["method_count"] == row["methods"], (name, row["name"])
            assert row["field_count"] == row["fields"], (name, row["name"])


def test_a_class_defined_in_two_dexes_is_one_method_with_two_sources(
    samples: dict[str, object],
) -> None:
    """``SharedConfig`` is defined in both dex files.

    It is one method with two sources, so it is one row, and the row has to say
    where it came from — otherwise "this method lives in classes2.dex" would
    hide the copy in classes.dex.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "multidex-app")

    methods = [
        method
        for method in analyzer.store.list_methods(project_id)
        if method.class_name == "com.example.multidex.SharedConfig"
    ]
    assert methods, "the duplicated class has no methods at all"

    for method in methods:
        locators = {provenance.locator for provenance in method.provenance}
        assert any("classes.dex" in locator for locator in locators), method.qualified_name
        assert any("classes2.dex" in locator for locator in locators), method.qualified_name


# -- a call says how it is made ---------------------------------------------


def _xref_rows(analyzer: Analyzer, project_id: str) -> list[sqlite3.Row]:
    with analyzer.store.transaction() as connection:
        return connection.execute(
            "SELECT caller, callee, kind FROM xrefs WHERE project_id = ?", (project_id,)
        ).fetchall()


def test_a_call_edge_says_how_the_call_is_made(samples: dict[str, object]) -> None:
    """A static call and a virtual call are different opcodes, and the edge says which.

    The kind used to be the same value on every row, so nothing in the index
    could tell a static call from a virtual one — and the field's own
    documentation promised a distinction it never made.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    rows = _xref_rows(analyzer, project_id)
    kinds = {row["kind"] for row in rows}

    assert "static" in kinds, "no static call was found in the demo app"
    assert "virtual" in kinds, "no virtual call was found in the demo app"
    assert "super" in kinds, "no super call was found in the demo app"

    by_callee = {row["callee"]: row["kind"] for row in rows}
    assert (
        by_callee[
            "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
        ]
        == "static"
    )
    assert by_callee["android.app.Activity.onCreate(Landroid/os/Bundle;)V"] == "super"


def test_an_interface_call_is_an_interface_call(samples: dict[str, object]) -> None:
    """The call site in the wide sample is an ``invoke-interface``.

    The reference names the interface rather than either implementation —
    that is how the DEX encodes it — and the edge has to say the call was an
    interface call.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "wide-app")

    rows = _xref_rows(analyzer, project_id)
    by_callee = {row["callee"]: row["kind"] for row in rows}

    assert by_callee["com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;"] == (
        "interface"
    )


def test_every_stored_call_kind_is_one_the_model_knows(samples: dict[str, object]) -> None:
    """The stored kinds and the model's vocabulary have to be the same list."""
    analyzer = _analyzer(samples)
    known = {kind.value for kind in InvocationKind}

    for name in sorted(SAMPLE_APKS):
        project_id = _project_id(samples, name)
        for row in _xref_rows(analyzer, project_id):
            assert row["kind"] in known, (name, row["kind"])


# -- a string constant points at the code that uses it ----------------------


def _string_rows(analyzer: Analyzer, project_id: str, value: str) -> list[sqlite3.Row]:
    with analyzer.store.transaction() as connection:
        return connection.execute(
            "SELECT value, class_name, method_name FROM strings WHERE project_id = ? AND value = ?",
            (project_id, value),
        ).fetchall()


def test_a_string_constant_points_at_the_method_that_uses_it(samples: dict[str, object]) -> None:
    """A hardcoded key has to lead back to the code that reads it.

    The index used to hold the string and nothing else, so a key found by a
    search could not be traced to the method that uses it. The two fields
    that were there to say so were never filled in.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    rows = _string_rows(analyzer, project_id, "sk_live_2f8a91c4e7b3")

    assert rows, "the hardcoded key is not in the string index"
    assert {(row["class_name"], row["method_name"]) for row in rows} == {
        ("com.example.demo.MainActivity", "onCreate")
    }


def test_a_constant_used_in_two_methods_is_a_row_for_each(samples: dict[str, object]) -> None:
    """A constant used in two places has two places to point at.

    One row per use site: a row that names one method cannot stand for a
    constant that two methods load.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "multidex-app")

    rows = _string_rows(analyzer, project_id, "primary-dex")

    assert len(rows) > 1, "the constant is used in two methods but was indexed once"
    for row in rows:
        assert row["class_name"] is not None
        assert row["method_name"] is not None


def test_a_pool_entry_no_method_loads_has_no_location(samples: dict[str, object]) -> None:
    """A type descriptor is in the pool, and no method loads it.

    The pool holds more than literals, and the row says so by having no
    method to point at.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    rows = _string_rows(analyzer, project_id, "Landroid/app/Activity;")

    assert rows, "the type descriptor is not in the string index"
    for row in rows:
        assert row["class_name"] is None
        assert row["method_name"] is None


def test_the_pool_holds_more_than_literals(samples: dict[str, object]) -> None:
    """Most of the pool is descriptors and member names, not text.

    This is why the model says "string pool" and not "string literal": in the
    demo app the great majority of the entries are type descriptors, member
    names and source-file names.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    with analyzer.store.transaction() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM strings WHERE project_id = ?", (project_id,)
        ).fetchone()[0]
        located = connection.execute(
            "SELECT COUNT(*) FROM strings WHERE project_id = ? AND class_name IS NOT NULL",
            (project_id,),
        ).fetchone()[0]

    assert total > 0
    assert located < total, "every pool entry was claimed to be a literal in the code"


# -- cross-references become evidence ---------------------------------------


def test_the_analysis_produces_cross_reference_evidence(samples: dict[str, object]) -> None:
    """A cross-reference is a conclusion about the code, so it has to be evidence.

    It used to be index data only: the method that records it had no caller in
    the pipeline, so an analysed APK produced no cross-reference record at all,
    and the report could not say who calls what.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    evidence = analyzer.store.list_evidence(project_id)
    cross = [item for item in evidence if item.kind == EvidenceKind.CROSS_REFERENCE]

    assert cross, "the analysis produced no cross-reference evidence"
    for item in cross:
        assert item.level == EvidenceLevel.VERIFIED
        assert item.detail["callers"], item.summary
        assert item.provenance, item.summary


def test_a_cross_reference_record_names_the_caller(samples: dict[str, object]) -> None:
    """The record has to point back at the code that makes the call."""
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    evidence = analyzer.store.list_evidence(project_id)
    sign = next(
        (
            item
            for item in evidence
            if item.kind == EvidenceKind.CROSS_REFERENCE and "Crypto.sign" in item.summary
        ),
        None,
    )

    assert sign is not None, "the demo app calls Crypto.sign; no record says so"
    assert any("MainActivity.onCreate" in caller for caller in sign.detail["callers"])


# -- the decompiler's own answer ---------------------------------------------


def test_the_index_says_which_methods_jadx_decompiled(
    samples: dict[str, object], demo_without_jadx: dict[str, object]
) -> None:
    """The ``decompiled`` flag has to be the decompiler's answer.

    It used to be Androguard's "this method has a code item", which is true of
    nearly every method in an APK — so the flag said nothing about whether the
    code could be read, and the name promised something the value did not.

    The answer depends on whether a decompiler was there to give one. With JADX
    installed it wrote Java for some methods and elided others, and the flag says
    which is which. With no JADX at all nobody decompiled anything, and the
    honest answer for every method is "no" — the index must not borrow the DEX's
    answer to fill the gap.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")
    methods = _decompiled_flags(analyzer, project_id)

    if samples["jadx_available"]:
        # JADX wrote both of these, in the file it wrote.
        assert (
            methods[
                "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
            ]
            is True
        )
        assert methods["com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V"] is True

        # The constructor is in the DEX, and JADX elided it: there is no decompiled
        # source for it, and the flag has to say so rather than claim one.
        assert methods["com.example.demo.MainActivity.<init>()V"] is False
    else:
        assert methods, "the DEX index is empty; the sample exercised nothing"
        flagged = [name for name, decompiled in methods.items() if decompiled]
        assert not flagged, f"methods were marked decompiled although no decompiler ran: {flagged}"

    # The same question, asked of an analysis that had no decompiler at all —
    # whichever configuration this machine happens to be in. The bytecode is
    # still there and still readable; nobody produced Java for it, and the flag
    # has to answer "no" rather than borrow the DEX's answer.
    without_jadx = _decompiled_flags(
        _analyzer_of(demo_without_jadx), _project_of(demo_without_jadx)
    )
    assert without_jadx, "the DEX index is empty; the sample exercised nothing"
    flagged = [name for name, decompiled in without_jadx.items() if decompiled]
    assert not flagged, f"methods were marked decompiled although no decompiler ran: {flagged}"


def test_the_analysis_records_the_decompilation_coverage(
    samples: dict[str, object], demo_without_jadx: dict[str, object]
) -> None:
    """How much of the APK the decompiler could read is a fact about the analysis.

    It used to be nowhere: the decompiler wrote no log file, so the only trace
    of a failure was a placeholder in the Java that nothing read.

    With no decompiler there is no coverage to report, and that is not the same
    as zero coverage: a record claiming "0 of 8 methods decompiled" would be a
    claim about a run that never happened. The analysis says nothing about
    coverage, and it says why — JADX never ran.
    """
    analyzer = _analyzer(samples)
    project_id = _project_id(samples, "demo-app")

    evidence = analyzer.store.list_evidence(project_id)
    coverage = _decompilation_coverage(evidence)

    if samples["jadx_available"]:
        assert coverage is not None, "the analysis said nothing about what JADX could read"

        methods = analyzer.store.list_methods(project_id)
        flagged = [method for method in methods if method.decompiled]
        assert coverage["methods_decompiled"] == len(flagged)
        assert coverage["methods_total"] == len(methods)
        assert 0 < len(flagged) < len(methods), "the demo application's methods are all readable"
    else:
        assert coverage is None, "coverage was reported although no decompiler ran"
        failure = _missing_backend_evidence(evidence, "jadx")
        assert failure is not None, "the analysis did not record that JADX never ran"

    # An analysis with no decompiler says nothing about coverage, and says why:
    # a reader who finds no decompiled source has to be able to tell "the code
    # could not be read" from "the decompiler was never installed".
    without_evidence = _evidence_of(demo_without_jadx)
    assert _decompilation_coverage(without_evidence) is None, (
        "coverage was reported although no decompiler ran"
    )

    failure = _missing_backend_evidence(without_evidence, "jadx")
    assert failure is not None, "the analysis did not record that JADX never ran"
    assert failure.kind == EvidenceKind.OBSERVATION
    assert failure.summary == "jadx did not complete: jadx is not installed or not on PATH"

    provenance = failure.provenance[0]
    assert provenance.tool == "jadx"
    assert provenance.tool_version is None, "a tool that never ran has no version"
    # Every locator names its backend, so a reader can tell which tool a location
    # belongs to without looking at the provenance's other fields.
    assert provenance.locator == "jadx:error/not_installed"
    assert failure.detail["error"]["code"] == "not_installed"
