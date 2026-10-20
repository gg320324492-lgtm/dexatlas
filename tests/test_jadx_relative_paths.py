"""A relative workspace must analyse an APK exactly like an absolute one.

The default workspace is relative — ``.dexatlas`` — and the decompiler was
handed that same relative path twice: once as ``--output-dir`` and once as the
working directory of the process it started. JADX resolves ``--output-dir``
against *its own* working directory, so the path was read twice against two
different bases and the Java sources landed in a doubly-nested copy of the tree
the index looks in:

    .dexatlas/projects/apk_XXX/jadx/.dexatlas/projects/apk_XXX/jadx/sources/...

The index found nothing there. The report was not wrong about any number it
printed — it simply never printed the decompilation coverage at all, because
the coverage is recorded from what the decompiler produced, and it produced
nothing that was found. The tool-version line still said ``jadx 1.5.2``.

No test caught it because the shared ``settings`` fixture builds its workspace
from ``tmp_path``, which is absolute. That is right for reproducibility, and
it is exactly why the default configuration was never exercised: the relative
case has to be constructed on purpose, and it is constructed here.

The tests below use a stand-in for the jadx command line rather than a real
decompiler. The stand-in reproduces the one behaviour that matters — it
resolves ``--output-dir`` against its own working directory, the way jadx
does — and writes real Java for the demo application's classes, so the index,
the source document and the coverage evidence all have something to hold.
That way the path plumbing is checked on every machine, with or without a
decompiler installed. The slow test at the end runs the real thing.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import SourceKind
from dexatlas.core.pipeline import AnalysisResult, Analyzer
from dexatlas.reports.coverage import decompilation_coverage
from dexatlas.tools.base import ToolInvocation, ToolOutcome
from dexatlas.tools.jadx.adapter import JadxBackend

#: The first-party demo application. It is committed to the repository, so
#: these tests need no download and no third-party APK.
DEMO_APK = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"

#: The Java the stand-in decompiler writes. The class names and the method
#: names are the ones the demo application really has, so the index holds
#: them, the source document finds them, and the coverage evidence counts
#: them.
STUB_SOURCES: dict[str, str] = {
    "com/example/demo/Crypto.java": """package com.example.demo;

public final class Crypto {
    public Crypto() {
    }

    public static String sign(String a, String b) {
        return a + b;
    }

    public static String obfuscate(String value) {
        return value;
    }

    public static String digestOf(String value) {
        return value;
    }
}
""",
    "com/example/demo/MainActivity.java": """package com.example.demo;

public class MainActivity extends android.app.Activity {
    public MainActivity() {
    }

    protected void onCreate(android.os.Bundle state) {
    }

    public static String describe(String value) {
        return value;
    }
}
""",
    "com/example/demo/NetworkClient.java": """package com.example.demo;

public final class NetworkClient {
    public static String post(String url, String body) {
        return body;
    }
}
""",
    "com/example/demo/SyncService.java": """package com.example.demo;

public class SyncService extends android.app.Service {
    public android.os.IBinder onBind(android.content.Intent intent) {
        return null;
    }
}
""",
    # The real jadx writes this one and the DEX does not hold it: the resource
    # table's identifiers. It is what makes the class count differ between a
    # run whose decompiler output was found and a run whose it was not.
    "com/example/demo/R.java": """package com.example.demo;

public final class R {
    public static final class string {
        public static final int app_name = 2131034112;
    }
}
""",
}

#: The class the source document is asked for.
CRYPTO = "com.example.demo.Crypto"

#: The stand-in decompiler. It answers ``--version``, and for a real
#: invocation it writes the sources under the output directory *as it was
#: given* — relative paths and all — which is how jadx behaves and how the
#: defect happened.
_STUB_SOURCE = '''"""A stand-in for the jadx command line."""

import json
import os
import sys


def main(argv):
    if "--version" in argv:
        print("1.5.2-stub")
        return 0

    output_dir = None
    for index, argument in enumerate(argv):
        if argument == "--output-dir" and index + 1 < len(argv):
            output_dir = argv[index + 1]
    if output_dir is None:
        print("no --output-dir given", file=sys.stderr)
        return 2

    spec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.json")
    with open(spec, encoding="utf-8") as handle:
        sources = json.load(handle)

    for relative, text in sources.items():
        target = os.path.join(output_dir, "sources", *relative.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def _write_stub(root: Path) -> Path:
    """Write the stand-in decompiler into ``root`` and return its launcher.

    The launcher is a shell script on POSIX and a batch file on Windows,
    because that is what the platform can execute. Both call the same Python
    program with an absolute path, so the launcher is found no matter what
    working directory the backend gives the child.
    """
    script = root / "jadx_stub.py"
    root.mkdir(parents=True, exist_ok=True)
    script.write_text(_STUB_SOURCE, encoding="utf-8")
    (root / "sources.json").write_text(json.dumps(STUB_SOURCES), encoding="utf-8")

    if os.name == "nt":
        launcher = root / "jadx.bat"
        launcher.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
        return launcher

    launcher = root / "jadx"
    launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    return launcher


@pytest.fixture
def stub_launcher(tmp_path: Path) -> Path:
    """The stand-in decompiler, on disk and ready to run."""
    return _write_stub(tmp_path / "bin")


@pytest.fixture
def demo_apk() -> Path:
    if not DEMO_APK.is_file():
        pytest.skip(f"{DEMO_APK} is not present")
    return DEMO_APK


def _analyze(workspace: Path, launcher: Path, apk: Path) -> tuple[Analyzer, AnalysisResult]:
    """Analyse the demo application with the stand-in decompiler."""
    settings = Settings(workspace=workspace, jadx_path=str(launcher))
    analyzer = Analyzer(settings)
    return analyzer, analyzer.analyze(apk)


def _workspace_of(analyzer: Analyzer, project_id: str) -> Path:
    workspace = analyzer.store.get_workspace(project_id)
    assert workspace is not None
    return workspace


# -- the workspace itself ---------------------------------------------------


def test_the_workspace_is_anchored_when_it_is_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative workspace names one directory, and keeps naming it.

    The settings are cached for the life of the process and the workspace is
    read long after it is configured, so a relative one would name whatever
    directory the reader happens to be in.
    """
    monkeypatch.chdir(tmp_path)

    settings = Settings(workspace=Path(".dexatlas"))
    expected = Path.cwd() / ".dexatlas"

    assert settings.workspace == expected
    assert settings.workspace.is_absolute()

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert settings.workspace == expected
    assert settings.database_path == expected / "dexatlas.db"
    assert settings.projects_dir == expected / "projects"


# -- the decompiler is told one directory -----------------------------------


def test_the_decompiler_is_told_one_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_launcher: Path, demo_apk: Path
) -> None:
    """Every path handed to the decompiler is absolute, and the output one is one path.

    The output directory is both the child's working directory and the
    argument that names its output. If the two are the same relative string,
    the child reads it against its own working directory and writes into a
    nested copy of the tree.
    """
    invocations: list[ToolInvocation] = []

    def fake_run(self: JadxBackend, invocation: ToolInvocation) -> ToolOutcome:
        invocations.append(invocation)
        return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)

    monkeypatch.setattr(JadxBackend, "run", fake_run)
    monkeypatch.chdir(tmp_path)

    # The launcher is pinned rather than discovered: a backend that is not
    # installed answers with an error instead of running, and the test would
    # then pass on a machine with jadx and fail on one without.
    backend = JadxBackend(Settings(workspace=tmp_path / "workspace", jadx_path=str(stub_launcher)))
    backend.decompile(demo_apk, Path("relative-output"))

    assert len(invocations) == 1
    invocation = invocations[0]
    argv = list(invocation.argv)

    output_dir = argv[argv.index("--output-dir") + 1]
    assert Path(output_dir).is_absolute()
    assert invocation.cwd is not None
    assert Path(invocation.cwd).is_absolute()
    assert output_dir == str(invocation.cwd)

    # The APK is read relative to the child's working directory too.
    assert Path(argv[-1]).is_absolute()
    # And so is the launcher, which is executed rather than read.
    assert Path(argv[0]).is_absolute()


def test_a_relative_launcher_path_is_still_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, demo_apk: Path
) -> None:
    """A launcher configured as a relative path is found, and runs.

    The launcher is executed with a working directory of its own, so a
    relative path would be looked up inside the output tree rather than the
    directory the operator named.
    """
    launcher = _write_stub(tmp_path / "bin")
    monkeypatch.chdir(tmp_path)

    relative = Path("bin") / launcher.name
    backend = JadxBackend(Settings(workspace=Path(".dexatlas"), jadx_path=str(relative)))

    resolved = backend.resolve()
    assert resolved is not None
    assert resolved.is_absolute()

    outcome = backend.decompile(demo_apk, Path("relative-output"))
    assert outcome.ok, outcome.error
    assert (tmp_path / "relative-output" / "sources" / "com" / "example" / "demo").is_dir()


# -- the whole analysis, under a relative workspace ------------------------


def test_a_relative_workspace_indexes_the_same_classes_as_an_absolute_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_launcher: Path, demo_apk: Path
) -> None:
    """The class count does not depend on how the workspace was spelled.

    The decompiler's classes were missing from the index under a relative
    workspace, and the count was the only number in the report that changed.
    """
    relative_root = tmp_path / "relative-root"
    absolute_root = tmp_path / "absolute-root"
    relative_root.mkdir()
    absolute_root.mkdir()

    monkeypatch.chdir(relative_root)
    _, relative = _analyze(Path(".dexatlas"), stub_launcher, demo_apk)

    monkeypatch.chdir(absolute_root)
    _, absolute = _analyze(absolute_root / ".dexatlas", stub_launcher, demo_apk)

    assert relative.project.class_count > 0
    assert relative.project.class_count == absolute.project.class_count
    assert relative.project.method_count == absolute.project.method_count
    assert relative.project.evidence_count == absolute.project.evidence_count


def test_a_relative_workspace_writes_the_decompiler_output_where_the_index_looks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_launcher: Path, demo_apk: Path
) -> None:
    """No nested copy of the output tree.

    The failure was invisible from the outside: the files existed, in a
    directory whose name repeated the path that led to it.
    """
    monkeypatch.chdir(tmp_path)

    analyzer, result = _analyze(Path(".dexatlas"), stub_launcher, demo_apk)
    workspace = _workspace_of(analyzer, result.project.id)
    jadx_dir = workspace / "jadx"

    java_files = sorted(jadx_dir.rglob("*.java"))
    assert java_files, "the decompiler wrote no Java at all"

    for path in java_files:
        relative = path.relative_to(jadx_dir)
        assert relative.parts[0] == "sources", f"{relative} is not directly under sources/"

    assert (jadx_dir / "sources" / "com" / "example" / "demo" / "Crypto.java").is_file()


def test_a_relative_workspace_serves_java_from_jadx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_launcher: Path, demo_apk: Path
) -> None:
    """The source is Java, and the provenance says which backend produced it.

    Under a relative workspace the decompiler's output was not found, so the
    source fell back to the Smali — and the fallback is a silent one: the
    text is still there, and only the provenance says which reading it is.
    """
    monkeypatch.chdir(tmp_path)

    analyzer, result = _analyze(Path(".dexatlas"), stub_launcher, demo_apk)

    document = analyzer.class_source_document(result.project.id, CRYPTO)

    assert document is not None
    assert document.kind is SourceKind.JAVA
    assert document.provenance[0].tool == "jadx"
    assert document.provenance[0].locator == "jadx:sources/com/example/demo/Crypto.java"


def test_a_relative_workspace_records_the_decompilation_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_launcher: Path, demo_apk: Path
) -> None:
    """The coverage evidence is recorded.

    The coverage is read out of what the decompiler produced, so a run whose
    output went somewhere else records no coverage at all — and the report
    then prints no coverage line, which reads as "there was nothing to
    report" rather than "the decompiler's output was lost".
    """
    monkeypatch.chdir(tmp_path)

    _, result = _analyze(Path(".dexatlas"), stub_launcher, demo_apk)

    coverage = decompilation_coverage(result.evidence)

    assert coverage is not None, "the analysis recorded no decompilation coverage"
    assert coverage["classes_with_source"] > 0
    assert coverage["classes_with_source"] == coverage["classes_total"]


# -- the same thing, against the real decompiler ----------------------------


@pytest.mark.slow
@pytest.mark.skipif(JadxBackend(Settings()).resolve() is None, reason="jadx is not installed")
def test_a_relative_workspace_decompiles_with_the_real_decompiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, demo_apk: Path
) -> None:
    """The default configuration, end to end, with jadx itself.

    The stand-in above reproduces jadx's path handling; this checks that the
    real decompiler agrees, and that the report's coverage line appears under
    a relative workspace.
    """
    monkeypatch.chdir(tmp_path)

    settings = Settings(workspace=Path(".dexatlas"))
    analyzer = Analyzer(settings)
    result = analyzer.analyze(demo_apk)

    assert result.succeeded
    workspace = _workspace_of(analyzer, result.project.id)
    jadx_dir = workspace / "jadx"

    java_files = sorted(jadx_dir.rglob("*.java"))
    assert java_files, "jadx wrote no Java at all"
    for path in java_files:
        assert path.relative_to(jadx_dir).parts[0] == "sources"

    document = analyzer.class_source_document(result.project.id, CRYPTO)
    assert document is not None
    assert document.kind is SourceKind.JAVA
    assert document.provenance[0].tool == "jadx"

    coverage = decompilation_coverage(result.evidence)
    assert coverage is not None
    assert coverage["methods_decompiled"] > 0
