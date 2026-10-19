"""The Smali fallback end to end, against a real multi-DEX APK.

Marked ``slow``: this decodes a real APK with Apktool and needs that tool installed.

The bug this file pins down was not a missing feature. ``smali_path`` looked for
``smali_classes2/`` *inside* ``smali/``, where Apktool never puts it, so the glob matched
nothing and the fallback failed for **every** APK — single-dex included. The symptom was
a command that printed "No source" while the decoded Smali sat right there on disk.

So the tests here deliberately run with JADX pointed at a path that does not exist: that
is the only configuration in which the Smali fallback is actually the thing under test.
"""

from __future__ import annotations

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

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "apk"
FIXTURE_APK = "multidex.apk"

#: The fixture holds two dexes. Apktool decodes the first into ``smali/`` and the
#: second into ``smali_classes2/`` — siblings, which is what the old code got wrong.
MULTIDEX_CLASSES = [
    ("com.foobar.foo.Foobar", "smali", "somemethod"),
    ("com.blafoo.bar.Blafoo", "smali_classes2", "othermethod"),
]


@pytest.fixture(scope="module", autouse=True)
def jadx_unavailable() -> Iterator[None]:
    """Make JADX report itself unavailable for every test in this module.

    Not done by pointing ``settings.jadx_path`` at a directory that does not exist.
    ``which_or_none`` falls back to a ``PATH`` lookup when the configured path is
    missing, so a JADX installed on ``PATH`` — which is exactly the case in CI —
    would still be found, and the decompiler would answer instead of the fallback
    being tested. The first version of this file made that mistake: it passed on a
    developer machine and failed in CI for the same reason.

    Patching the resolution itself is the only statement of intent that does not
    depend on what happens to be installed on the machine running the tests.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(JadxBackend, "resolve", lambda self: None)
        yield


@pytest.fixture(scope="module")
def decoded(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Analyse the multi-DEX fixture once with JADX absent, and share the result.

    Decoding is the expensive part; sharing it keeps this module to one Apktool run.
    """
    fixture = FIXTURE_DIR / FIXTURE_APK
    if not fixture.is_file():
        pytest.skip("fixture not present; run scripts/fetch-fixtures.sh")

    workspace = tmp_path_factory.mktemp("smali-fallback")
    settings = Settings(workspace=workspace)
    analyzer = Analyzer(settings)
    result = analyzer.analyze(fixture)

    # Constructed directly rather than fetched from the registry, which types them as
    # the Backend base class and would hide the methods these tests call.
    assert not JadxBackend(settings).available(), "JADX must be unavailable for these tests"
    assert ApktoolBackend(settings).available(), "Apktool must be available"
    assert result.succeeded

    output = analyzer.store.get_workspace(result.project.id)
    assert output is not None
    return {
        "analyzer": analyzer,
        "settings": settings,
        "project_id": result.project.id,
        "workspace": output,
    }


def _analyzer(decoded: dict[str, object]) -> Analyzer:
    analyzer: Analyzer = decoded["analyzer"]  # type: ignore[assignment]
    return analyzer


def test_apktool_produced_both_smali_directories(decoded: dict[str, object]) -> None:
    """Sanity check on the fixture: the layout the fix depends on really exists.

    Without this, every test below could pass against a fixture that has no second dex,
    which would make the whole file meaningless.
    """
    workspace: Path = decoded["workspace"]  # type: ignore[assignment]
    apktool_out = workspace / "apktool"
    directories = sorted(p.name for p in apktool_out.glob("smali*") if p.is_dir())

    assert "smali" in directories
    assert "smali_classes2" in directories


@pytest.mark.parametrize(("class_name", "expected_dir", "method_name"), MULTIDEX_CLASSES)
def test_class_source_falls_back_to_smali_for_every_dex(
    decoded: dict[str, object], class_name: str, expected_dir: str, method_name: str
) -> None:
    """The class is found, and it is found in the directory its dex decodes to.

    Asserting the directory is the point: a fix that flattened everything into ``smali/``
    would make the class lookup succeed while being wrong about multi-dex.
    """
    analyzer = _analyzer(decoded)
    project_id: str = decoded["project_id"]  # type: ignore[assignment]
    workspace: Path = decoded["workspace"]  # type: ignore[assignment]

    path = ApktoolBackend(decoded["settings"]).smali_path(class_name, workspace / "apktool")
    assert path is not None, f"{class_name} was not located in any smali directory"
    assert expected_dir in path.parts

    source = analyzer.class_source(project_id, class_name)
    assert source is not None, f"{class_name}: no source despite a decoded smali file"
    assert f"L{class_name.replace('.', '/')};" in source


@pytest.mark.parametrize(("class_name", "expected_dir", "method_name"), MULTIDEX_CLASSES)
def test_method_source_extracts_the_requested_block(
    decoded: dict[str, object], class_name: str, expected_dir: str, method_name: str
) -> None:
    """One method's block, from the dex it lives in.

    Method names are the ones this fixture actually declares — an invented name would
    pass for the wrong reason, by returning None on a broken extractor.
    """
    analyzer = _analyzer(decoded)
    project_id: str = decoded["project_id"]  # type: ignore[assignment]

    source = analyzer.method_source(project_id, class_name, method_name)

    assert source is not None
    assert source.startswith(".method")
    assert ".end method" in source
    assert method_name in source.splitlines()[0]


def test_smali_constructor_names_resolve(decoded: dict[str, object]) -> None:
    """``<init>`` is a real Smali method name, not a placeholder to be rejected."""
    analyzer = _analyzer(decoded)
    project_id: str = decoded["project_id"]  # type: ignore[assignment]

    source = analyzer.method_source(project_id, "com.foobar.foo.Foobar", "<init>")

    assert source is not None
    assert "constructor <init>" in source.splitlines()[0]


def test_a_method_that_does_not_exist_returns_none(decoded: dict[str, object]) -> None:
    """A miss is a clean None, never a neighbouring method's block."""
    analyzer = _analyzer(decoded)
    project_id: str = decoded["project_id"]  # type: ignore[assignment]

    assert analyzer.method_source(project_id, "com.foobar.foo.Foobar", "foo") is None
    assert analyzer.method_source(project_id, "com.foobar.foo.Foobar", "somemetho") is None
    # Method lookup is case-sensitive; a different case must not match.
    assert analyzer.method_source(project_id, "com.foobar.foo.Foobar", "SOMEMETHOD") is None


def test_a_class_that_does_not_exist_returns_none(decoded: dict[str, object]) -> None:
    analyzer = _analyzer(decoded)
    project_id: str = decoded["project_id"]  # type: ignore[assignment]

    assert analyzer.class_source(project_id, "com.nope.Missing") is None
