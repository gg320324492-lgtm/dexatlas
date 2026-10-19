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

import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
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
    }


def _analyzer(samples: dict[str, object]) -> Analyzer:
    analyzer: Analyzer = samples["analyzer"]  # type: ignore[assignment]
    return analyzer


def _project_id(samples: dict[str, object], name: str) -> str:
    projects: dict[str, object] = samples["projects"]  # type: ignore[assignment]
    project = projects[name]
    return project.id  # type: ignore[union-attr]


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
