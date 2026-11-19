"""Documentation integrity.

A broken link in a README is invisible until someone follows it, which is usually
someone deciding whether this project is worth their time. These checks are cheap.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent

#: Markdown links, excluding external URLs, anchors and mailto.
RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)\s]+)")

#: Directories whose contents are generated or third-party.
#: The project's own local state lives in ``.scratch``: the analysis backends,
#: the helper scripts, the temporary files and the packages uv has fetched.
#: It is not part of the project, and a checker that walked it would be
#: reading copies of the documents rather than the documents.
SKIP_DIRS = {
    ".git",
    ".venv",
    ".scratch",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

#: Paths that are local working state, not part of the checked-out project.
#:
#: Everything under ``.claude/`` is ignored (``.gitignore`` line 83) because a
#: worktree parked there is a *second* copy of the whole repository, and the
#: relative links inside it were never written to resolve from where they sit.
#: Walking into it makes every parallel session look broken while main is fine,
#: so the walker stops at the directory instead of filtering its files.
LOCAL_STATE_PATHS = {
    ".claude",
}

#: Suffixes that mark a file as an analysis artefact rather than source.
#:
#: The list is longer than the five the rule started with, because an APK is not
#: the only way to carry one: a split APK is ``.apks``, an XAPK is a bundle of
#: APKs, an expansion file is ``.obb``, and a ``.vdex``/``.odex`` is a DEX
#: container — the very thing Androguard reads. A rule that only knew five
#: spellings would let the same binary in under a different name.
_ANALYSIS_ARTIFACT_SUFFIXES = {
    ".apk",
    ".apks",
    ".apkm",
    ".xapk",
    ".aab",
    ".dex",
    ".odex",
    ".vdex",
    ".obb",
    ".so",
    ".jar",
    ".zip",
}

#: Documents that must exist for a reader to get started.
REQUIRED_DOCS = [
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "LICENSE",
    "docs/install.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/README.md",
]


def _markdown_files() -> list[Path]:
    """Every markdown file that is part of the checked-out project.

    A plain ``rglob`` would descend into the local working state too — into
    ``.claude/worktrees/``, where another session's checkout is parked with
    links that only resolve from its own directories. Those are not this
    tree's documents, so the walk prunes those directories instead of
    filtering their files afterwards, the way ``check-doc-citations.py``
    prunes its own walk.
    """
    found: list[Path] = []
    for root, directories, files in os.walk(REPO_ROOT):
        directories[:] = [
            name for name in directories if name not in SKIP_DIRS and name not in LOCAL_STATE_PATHS
        ]
        found.extend(Path(root) / name for name in files if name.lower().endswith(".md"))
    return found


@pytest.mark.parametrize("doc", REQUIRED_DOCS)
def test_required_document_exists(doc: str) -> None:
    assert (REPO_ROOT / doc).is_file(), f"{doc} is missing"


def _resolves_literally(base: Path, target: str) -> bool:
    """Whether ``target`` names something, checked component by component.

    ``Path.resolve()`` normalises the way Windows does: there, three dots
    mean "the parent directory", so a placeholder link written as ``(...)``
    resolved to a directory that exists and **passed** the check on Windows --
    while CI, on Linux, saw a directory named ``...`` that does not exist and
    failed. The names in a path are checked literally instead, which is what
    a file system does on every platform.
    """
    current = base
    for part in target.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return current.exists()


def test_all_relative_links_resolve() -> None:
    broken: list[str] = []

    for markdown in _markdown_files():
        text = markdown.read_text(encoding="utf-8", errors="replace")
        for match in RELATIVE_LINK.finditer(text):
            target = match.group(1).split("#")[0]
            if not target:
                continue
            if not _resolves_literally(markdown.parent, target):
                relative = markdown.relative_to(REPO_ROOT)
                broken.append(f"{relative}: {target}")

    assert not broken, "broken relative links:\n" + "\n".join(sorted(set(broken)))


def test_the_link_check_does_not_accept_a_placeholder(tmp_path: Path) -> None:
    """A placeholder target is a broken link, on every platform.

    Windows normalises ``...`` to the parent directory, so a document that
    wrote ``(...)`` where a URL should be passed the link check locally and
    failed it in CI: the local gate was weaker than the one it stood in for,
    and the difference only showed up when the tree was pushed.
    """
    (tmp_path / "here.md").write_text("x")

    assert not _resolves_literally(tmp_path, "...")
    assert not _resolves_literally(tmp_path, "nope.md")
    assert not _resolves_literally(tmp_path, "here.md/nope")
    assert _resolves_literally(tmp_path, "here.md")


def test_link_check_ignores_the_local_working_state(tmp_path: Path) -> None:
    """A worktree parked under ``.claude/`` is not this tree's documentation.

    Another session's checkout carries links written to resolve from *its*
    directories. When this checker walked into them, every parallel session
    looked broken while the project's own documents were fine. The walk must
    stop at ``.claude/`` — but still find the project's own documents, which
    is what the planted file below asserts: a doc outside the ignored path is
    always in the sweep, and a broken link inside it always fails this test.
    """
    nested = tmp_path / ".claude" / "worktrees" / "some-session"
    nested.mkdir(parents=True)
    (nested / "not-checked.md").write_text("[nowhere](.github/no-such-file.md)")

    monkeypatched_root = tmp_path
    monkeypatched_root.joinpath("README.md").write_text("[install](docs/install.md)")
    (monkeypatched_root / "docs").mkdir(exist_ok=True)
    (monkeypatched_root / "docs" / "install.md").write_text("install guide")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("tests.test_docs.REPO_ROOT", monkeypatched_root)
        files = _markdown_files()

    names = sorted(path.relative_to(monkeypatched_root).as_posix() for path in files)
    assert names == ["README.md", "docs/install.md"]


def test_readme_links_to_the_installation_guide() -> None:
    """The Phase 1 exit criterion is that a stranger can install from the README alone."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/install.md" in readme


def test_readme_does_not_overclaim() -> None:
    """The README must not describe unbuilt features as shipped.

    The Quick Start section tells a reader what they can do now, so it may
    only name what is built. The roadmap table may name the rest, which is
    fine: a plan is not a claim.

    The list below is the milestone list as it stands: the MCP server, the
    agent, and the workbench's project dashboard and single-method
    cross-reference view have landed. A whole-workspace call graph browser has
    not — the screen built here answers one method at a time — so it stays on
    this side of the test. When something else is built, it moves out of this
    list and into the other side of the same test, which is the point of
    keeping the test: it says which of the two it is at any moment.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    quick_start = readme.split("## Quick start", 1)[-1].split("\n## ", 1)[0]
    for unbuilt in ("upload and analysis progress", "call graph viewer"):
        assert unbuilt not in quick_start.lower(), (
            f"the Quick Start section references {unbuilt!r}, which is not built yet"
        )


def test_the_quick_start_names_the_workbench_because_it_is_built() -> None:
    """The other side of the same claim: what is built is named.

    Two workbench screens exist, so the Quick Start has to name the command
    that runs them and the views they serve, rather than describing the whole
    screen set as delivered or naming only one of the two.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quick_start = readme.split("## Quick start", 1)[-1].split("\n## ", 1)[0]

    assert "dexatlas-workbench" in quick_start, (
        "the workbench is built and the Quick Start does not say how to run it"
    )
    assert (REPO_ROOT / "src" / "dexatlas" / "workbench" / "app.py").is_file()
    # The cross-reference view is a claim about a screen, so it has to be
    # backed by the endpoints that screen reads.
    assert "cross-reference" in quick_start.lower(), (
        "the workbench's cross-reference view is built and the README does not name it"
    )
    app_source = (REPO_ROOT / "src" / "dexatlas" / "workbench" / "app.py").read_text(
        encoding="utf-8"
    )
    for route in ("/callers", "/callees"):
        assert route in app_source, f"the workbench serves no {route} endpoint"


def test_the_quick_start_names_the_mcp_server_because_it_is_built() -> None:
    """The other side of the same claim: what is built is named.

    A check that only forbids things would be satisfied by a README that
    mentions nothing at all. The MCP server is built and the Quick Start
    names it, and this says so.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quick_start = readme.split("## Quick start", 1)[-1].split("\n## ", 1)[0]

    assert "mcp" in quick_start.lower(), (
        "the MCP server is built and the Quick Start does not mention it"
    )
    assert (REPO_ROOT / "src" / "dexatlas" / "mcp" / "server.py").is_file()


def test_the_quick_start_names_the_agent_because_it_is_built() -> None:
    """The same claim, one milestone on: the agent is built and named.

    The agent is a library rather than a command, so the Quick Start says
    that too — a reader who is told the agent exists and not that it has no
    entry point will look for a command that is not there.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quick_start = readme.split("## Quick start", 1)[-1].split("\n## ", 1)[0]

    assert "agent" in quick_start.lower(), (
        "the agent is built and the Quick Start does not mention it"
    )
    assert (REPO_ROOT / "src" / "dexatlas" / "agent" / "orchestrator.py").is_file()


def test_readme_marks_the_project_as_in_development() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "early development" in readme.lower()


def test_install_guide_documents_every_configuration_variable() -> None:
    """Every DEXATLAS_ setting must be discoverable from the installation guide."""
    import re as _re

    settings_source = (REPO_ROOT / "src/dexatlas/config/settings.py").read_text(encoding="utf-8")
    declared = set(_re.findall(r"^\s{4}(\w+):\s", settings_source, _re.MULTILINE))

    install = (REPO_ROOT / "docs/install.md").read_text(encoding="utf-8")

    missing = [
        name
        for name in sorted(declared)
        if name not in {"model_config", "workspace"} and f"DEXATLAS_{name.upper()}" not in install
    ]
    assert not missing, f"settings not documented in docs/install.md: {missing}"


def test_license_is_apache() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "Apache License" in license_text
    assert "Version 2.0" in license_text


def test_no_third_party_apk_or_binary_is_committed() -> None:
    """The repository must not carry analysable binaries from other people's apps.

    ``.gitignore`` excludes them, but an ignore rule is only a claim — this checks what
    git actually tracks.

    The exceptions are DexAtlas's own test applications — first-party, built from the
    smali sources committed beside them, rebuildable with ``scripts/build-test-apks.sh``
    — and the case-study delivery packages under ``docs/case-studies/attachments/``,
    which are generated from those same first-party samples by the documented
    ``analyze --html`` / ``export`` commands and whose manifest hashes every file
    they carry. The allowed set is derived from what is on disk rather than written
    out by hand, so a sample added without its sources — or a third-party APK slipped
    into either directory — fails here.
    """
    import subprocess

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")

    first_party_dirs = [REPO_ROOT / "examples", REPO_ROOT / "docs" / "case-studies" / "attachments"]
    allowed = {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for directory in first_party_dirs
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in _ANALYSIS_ARTIFACT_SUFFIXES
    }
    assert allowed, "no first-party sample was found under examples/"

    tracked_bad = [
        name
        for name in result.stdout.splitlines()
        if Path(name).suffix.lower() in _ANALYSIS_ARTIFACT_SUFFIXES and name not in allowed
    ]
    assert not tracked_bad, f"third-party analysis artifacts are tracked: {tracked_bad}"


def test_every_committed_sample_has_its_sources_beside_it() -> None:
    """A committed APK is only honest if the sources that produced it are committed.

    Otherwise the repository carries a binary nobody can explain, which is the one
    thing this project's sample policy exists to prevent.
    """
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "examples"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")

    tracked = result.stdout.splitlines()
    apks = [name for name in tracked if name.endswith(".apk")]
    assert apks, "no sample APK is committed"

    for apk in apks:
        # git always reports paths with forward slashes; Path renders them with the
        # platform separator, so the prefix is normalised before comparing.
        directory = str(Path(apk).parent).replace("\\", "/")
        assert (REPO_ROOT / directory / "AndroidManifest.xml").is_file(), (
            f"{apk} has no manifest beside it"
        )
        sources = [
            name
            for name in tracked
            if name.startswith(f"{directory}/smali") and name.endswith(".smali")
        ]
        assert sources, f"{apk} has no smali sources beside it"


def test_every_integration_fixture_the_fetch_script_declares_is_one_a_test_uses() -> None:
    """The fetch script and the integration tests must agree on the fixture list.

    ``scripts/fetch-fixtures.sh`` downloads what the ``slow`` suite needs. If a test
    starts using a fixture the script does not fetch, that test skips on every machine
    that ran the script — CI included — and a regression guard disappears without
    anything turning red. That is the same silent failure the Smali fallback bug was.

    The check runs in both directions: an un-fetched fixture fails, and so does a
    fetched one that no test reads any more.
    """
    script = (REPO_ROOT / "scripts" / "fetch-fixtures.sh").read_text(encoding="utf-8")
    declared = set(re.findall(r'^\s*"([^"]+\.apk)"\s*$', script, re.MULTILINE))
    assert declared, "no .apk entries found in scripts/fetch-fixtures.sh"

    used: set[str] = set()
    for test_file in (REPO_ROOT / "tests").glob("test_*.py"):
        text = test_file.read_text(encoding="utf-8")
        # Only .apk values: `FIXTURE_APK` is also used for a SHA-256 placeholder,
        # which is not a file name.
        used.update(re.findall(r'FIXTURE_DIR\s*/\s*"([^"]+\.apk)"', text))
        used.update(re.findall(r'FIXTURE_APK\s*=\s*"([^"]+\.apk)"', text))

    assert declared == used, (
        "scripts/fetch-fixtures.sh and the integration tests disagree about fixtures: "
        f"fetched but unused={sorted(declared - used)}, used but not fetched={sorted(used - declared)}"
    )


def test_the_bundled_demo_app_is_first_party_and_reproducible() -> None:
    """The exception above must stay justified: sources present, rebuild script present."""
    demo = REPO_ROOT / "examples" / "demo-app"

    assert (demo / "demo.apk").is_file(), "the bundled demo APK is missing"
    assert (demo / "AndroidManifest.xml").is_file()
    assert (demo / "apktool.yml").is_file()
    assert list((demo / "smali").rglob("*.smali")), "no smali sources for the demo app"
    assert (REPO_ROOT / "scripts" / "build-demo-apk.sh").is_file()
    assert (REPO_ROOT / "scripts" / "build-test-apks.sh").is_file()


def test_the_build_script_covers_every_sample() -> None:
    """Every sample on disk must be buildable by the script, and vice versa.

    The script's list and the directories under ``examples/`` are two statements of
    the same thing. When they drift, a sample is silently unbuildable — the APK
    stays in the repository but nobody can regenerate it.
    """
    script = (REPO_ROOT / "scripts" / "build-test-apks.sh").read_text(encoding="utf-8")
    declared = set(re.findall(r'"([a-z0-9-]+):([a-z0-9]+\.apk)"', script))
    assert declared, "no samples are declared in scripts/build-test-apks.sh"

    on_disk = {
        path.name
        for path in (REPO_ROOT / "examples").iterdir()
        if path.is_dir() and list(path.glob("*.apk"))
    }
    assert on_disk, "no sample directories under examples/"

    assert {name for name, _ in declared} == on_disk, (
        "scripts/build-test-apks.sh and examples/ disagree about the samples: "
        f"declared={sorted(name for name, _ in declared)} on disk={sorted(on_disk)}"
    )


# -- demo assets -----------------------------------------------------------


def test_demo_gifs_exist_and_are_valid() -> None:
    """The README embeds these; a missing or corrupt file shows as a broken image.

    The deep check needs Pillow, which lives in the optional `demo` extra. When it is
    absent the files are still checked for existence and plausibility — a corrupt GIF
    should fail CI, but a missing optional dependency should not.
    """
    assets = REPO_ROOT / "docs" / "assets"
    for name in ("demo.gif", "demo-quick.gif"):
        path = assets / name
        assert path.is_file(), f"{name} is missing — run scripts/render-demo.py"
        assert path.stat().st_size > 20_000, f"{name} is suspiciously small"
        # A GIF always starts with this magic; checking it needs no dependency.
        assert path.read_bytes()[:3] == b"GIF", f"{name} is not a GIF"

    pytest.importorskip("PIL", reason="the demo extra installs Pillow for deep checks")

    from PIL import Image

    for name in ("demo.gif", "demo-quick.gif"):
        with Image.open(assets / name) as image:
            assert image.format == "GIF"
            assert image.n_frames > 10, f"{name} has too few frames to show a session"
            assert image.width >= 800, f"{name} is too narrow to read"


def test_readme_embeds_the_demo_gifs() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/assets/demo-quick.gif" in readme
    assert "docs/assets/demo.gif" in readme


def test_the_demo_video_exists_and_is_a_playable_mp4() -> None:
    """The Phase 1 checklist asks for a demo video, and the README links it.

    Checked without ffprobe, which is not a dependency: an MP4 carries the ``ftyp``
    box at the start of the file, and its size is a reasonable proxy for "a recording
    rather than a stub". The deep check below uses ffmpeg when it is available.
    """
    path = REPO_ROOT / "docs" / "assets" / "demo.mp4"
    assert path.is_file(), "demo.mp4 is missing — run scripts/render-demo.py"
    assert path.stat().st_size > 20_000, "demo.mp4 is suspiciously small"

    header = path.read_bytes()[:12]
    assert header[4:8] == b"ftyp", "demo.mp4 does not start with an MP4 file-type box"


def test_the_demo_video_decodes_when_ffmpeg_is_available() -> None:
    """A truncated or unplayable file would satisfy the header check above."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")

    path = REPO_ROOT / "docs" / "assets" / "demo.mp4"
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"demo.mp4 does not decode: {result.stderr[-400:]}"
    assert not result.stderr.strip(), f"demo.mp4 decoded with errors: {result.stderr[-400:]}"


def test_every_embedded_image_resolves() -> None:
    """An <img src> pointing at a missing file is a broken image on the front page."""
    broken = []

    for markdown in _markdown_files():
        text = markdown.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'<img[^>]+src="([^"]+)"', text):
            target = match.group(1)
            if target.startswith(("http://", "https://")):
                continue
            if not (markdown.parent / target).exists():
                relative = markdown.relative_to(REPO_ROOT)
                broken.append(f"{relative}: {target}")

    assert not broken, "missing images:\n" + "\n".join(sorted(set(broken)))


def test_demo_capture_script_reports_a_real_project_id() -> None:
    """The recording must never show a hard-coded project id.

    Project ids are content-addressed, so a stale literal in the capture script would put
    a value on screen that no reader could reproduce. Matching the ``apk_`` *prefix* is
    how the script reads the id back out, so that is allowed; a full id is not.
    """
    capture = (REPO_ROOT / "scripts" / "capture-demo.sh").read_text(encoding="utf-8")

    assert "project_id()" in capture, "the capture script should read the id it produced"

    literals = re.findall(r"apk_[0-9a-f]{8,}", capture)
    assert not literals, f"hard-coded project id(s) in the capture script: {literals}"


# -- execution report -------------------------------------------------------

#: The report the self-checks below read. ``scripts/refresh-report-figures.py``
#: points this at a *candidate* copy while it measures itself, so a self-check
#: never sees a report that is half-refreshed and the report on disk is only
#: ever replaced whole.
REPORT = Path(
    os.environ.get(
        "DEXATLAS_REPORT_PATH",
        REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md",
    )
)

#: The script that owns the report's generated numbers.
FIGURE_SCRIPT = REPO_ROOT / "scripts" / "refresh-report-figures.py"

#: Every figure the report has to state. A figure that quietly disappears is as
#: wrong as one that states the wrong value.
REQUIRED_FIGURES = (
    "cli.commands",
    "api.endpoints",
    "samples.apks",
    "tests.total",
    "tests.fast",
    "tests.slow",
    "suite.passed",
    "suite.skipped",
    "suite.xfailed",
    "coverage.pct",
    "coverage.covered",
    "coverage.total",
    "coverage.weak_modules",
    "history.v0.1.0.tests",
    "history.v0.1.1.tests",
    "history.v0.1.2.tests",
)


def _figure_script() -> ModuleType:
    """The script that writes the figures; the tests read its rules, not a copy."""
    spec = spec_from_file_location("dexatlas_report_figures", FIGURE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: the script's
    # dataclasses resolve their annotations through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stated_figures() -> dict[str, list[str]]:
    """Every figure the report states, with every value it states it as."""
    script = _figure_script()
    stated: dict[str, list[str]] = {}
    for key, value in script.FIGURE.findall(REPORT.read_text(encoding="utf-8")):
        stated.setdefault(key, []).append(value)
    return stated


def _recorded_measurement() -> dict[str, Any]:
    """The measurement the report recorded the last time it was refreshed."""
    return _figure_script().read_record(REPORT.read_text(encoding="utf-8"))


def _collected(marker: str) -> tuple[int, int]:
    """How many tests pytest's collector selects for a marker expression.

    The collector is used rather than a count of ``@pytest.mark.slow``
    decorators, so the figure cannot drift from what actually runs.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            marker,
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"(\d+)/(\d+) tests collected", result.stdout)
    assert match, f"could not read pytest's collection count: {result.stdout[-500:]}"
    return int(match.group(1)), int(match.group(2))


@pytest.fixture(scope="module")
def collected() -> tuple[int, int]:
    """How many tests the collector finds, and how many the suite holds.

    The collection is asked for once and shared: it costs a pytest start-up
    per call, and every check below needs the same answer.
    """
    return _collected("not slow")


def test_execution_report_exists() -> None:
    assert REPORT.is_file(), "the Phase 1 execution report is missing"


def test_execution_report_numbers_match_the_code(collected: tuple[int, int]) -> None:
    """Every number the report states about the code must be the number the code has.

    The old check looked for a literal such as ``| 196 |`` in the report. That
    could not say what was wrong when the formatting changed, and it did not
    notice a number that had been deleted. This one recomputes each figure and
    names the ones that disagree.
    """
    stated = _stated_figures()
    fast, total = collected
    slow, _ = _collected("slow")

    cli = (REPO_ROOT / "src/dexatlas/cli/main.py").read_text(encoding="utf-8")
    api = (REPO_ROOT / "src/dexatlas/api/app.py").read_text(encoding="utf-8")
    expected = {
        "tests.total": total,
        "tests.fast": fast,
        "tests.slow": slow,
        "cli.commands": cli.count("@app.command()"),
        "api.endpoints": len(re.findall(r"@app\.(get|post|delete|put)\(", api)),
        "samples.apks": len(list((REPO_ROOT / "examples").rglob("*.apk"))),
    }

    problems = []
    for key, actual in expected.items():
        values = sorted(set(stated.get(key, [])))
        if values != [str(actual)]:
            problems.append(
                f"{key}: the report says {values or ['nothing']}, the code has {actual}"
            )

    assert not problems, "the execution report disagrees with the code:\n" + "\n".join(problems)


def test_execution_report_states_each_figure_one_way() -> None:
    """The same figure must not appear twice with two different values."""
    stated = _stated_figures()
    inconsistent = {
        key: sorted(set(values)) for key, values in stated.items() if len(set(values)) > 1
    }
    assert not inconsistent, (
        "the report states the same figure in two different ways: "
        + "; ".join(f"{key}: {values}" for key, values in sorted(inconsistent.items()))
    )


def test_execution_report_states_every_generated_figure() -> None:
    """A figure that disappeared from the report must not disappear silently."""
    stated = _stated_figures()
    missing = [key for key in REQUIRED_FIGURES if key not in stated]
    assert not missing, "the report no longer states: " + ", ".join(missing)


def test_execution_report_coverage_figures_describe_the_current_code() -> None:
    """The coverage figures must describe the code that is in the tree now.

    Re-measuring coverage takes a couple of minutes, so the report carries the
    fingerprint of the source tree it was measured on. Change the code and the
    fingerprint changes with it, which declares the figures stale instead of
    letting them go on passing for the present.
    """
    script = _figure_script()
    record = _recorded_measurement()
    stated = _stated_figures()

    assert record, "the report carries no measurement record; run scripts/refresh-report-figures.py"

    fingerprint = script.source_fingerprint()
    assert record["source_fingerprint"] == fingerprint, (
        "the coverage figures were measured on a different source tree "
        f"({record['source_fingerprint']} -> {fingerprint}); "
        "run scripts/refresh-report-figures.py to measure the current code"
    )

    coverage = record["coverage"]
    assert coverage["statements"] == sum(s for s, _ in coverage["files"].values()), (
        "the per-module statements do not add up to the total"
    )
    assert coverage["missing"] == sum(m for _, m in coverage["files"].values()), (
        "the per-module missing lines do not add up to the total"
    )

    values = script.render_figures(record)
    wrong = [
        f"{key}: the report says {sorted(set(stated[key]))}, the measurement says {values[key]}"
        for key in sorted(stated)
        if key in values and set(stated[key]) != {values[key]}
    ]
    assert not wrong, "the execution report disagrees with its own measurement:\n" + "\n".join(
        wrong
    )


def test_execution_report_suite_figures_add_up_to_the_tests_that_exist(
    collected: tuple[int, int],
) -> None:
    """The pass/skip split has to be the split of a suite that exists.

    The number of tests in the tree is measured again here, so the report's
    own numbers are checked against the suite rather than against the record
    they were written next to. A record that says 999 tests passed when the
    suite holds 718 is caught; before, the record only had to agree with
    itself, and writing 999 into it changed nothing anybody could see.

    Every test that ran has exactly one outcome, so the outcomes add up to
    the number of tests. The failures are counted too: a measurement in
    which a test failed still ran that test, and leaving the failure out of
    the sum would make the sum smaller than the suite. A measurement may
    also deselect tests (a marker expression that does not match every
    test), and the deselected count is part of the record: ran + deselected
    is the whole suite.
    """
    record = _recorded_measurement()
    assert record, "the report carries no measurement record"

    suite = record["suite"]
    total = collected[1]
    ran = (
        suite["passed"]
        + suite["skipped"]
        + suite["xfailed"]
        + suite.get("failed", 0)
        + suite.get("xpassed", 0)
        + suite.get("deselected", 0)
    )

    assert ran == total, (
        f"the report says {suite['passed']} passed, {suite['skipped']} skipped, "
        f"{suite['xfailed']} xfailed, {suite['failed']} failed, "
        f"{suite['xpassed']} xpassed and {suite.get('deselected', 0)} deselected, "
        f"which is {ran} of the {total} tests in the tree"
    )


def test_execution_report_recorded_skips_are_the_tests_the_record_names() -> None:
    """A count and the names of the tests it counts have to agree.

    The record says how many tests sat out and which ones. A count that does
    not match the names is a count of nothing: it says a measurement was
    partial without saying what was missing, which is the state in which an
    incomplete measurement can be published as a complete one.
    """
    record = _recorded_measurement()
    assert record, "the report carries no measurement record"

    suite = record["suite"]
    skipped_tests = suite.get("skipped_tests", [])
    xfailed_tests = suite.get("xfailed_tests", [])
    assert len(skipped_tests) == suite["skipped"], (
        f"the record says {suite['skipped']} tests skipped and names {len(skipped_tests)} of them"
    )
    assert len(xfailed_tests) == suite["xfailed"], (
        f"the record says {suite['xfailed']} tests xfailed and names {len(xfailed_tests)} of them"
    )


def test_execution_report_coverage_figures_describe_the_statements_in_the_tree() -> None:
    """The coverage denominator has to be the one the tree has.

    The number of statements is measured again here, with coverage's own
    parser, so the report's coverage is checked against the code and not
    against the record the last refresh wrote beside it. A record that
    claims a different number of statements is caught.
    """
    script = _figure_script()
    record = _recorded_measurement()
    assert record, "the report carries no measurement record"

    measured = script.source_statements()
    recorded = record["coverage"]["files"]

    assert set(recorded) == set(measured), (
        "the measurement covers a different set of modules: "
        f"only in the record: {sorted(set(recorded) - set(measured))}; "
        f"only in the tree: {sorted(set(measured) - set(recorded))}"
    )
    wrong = {
        module: (values[0], measured[module])
        for module, values in recorded.items()
        if values[0] != measured[module]
    }
    assert not wrong, "the recorded statement counts are not the tree's:\n" + "\n".join(
        f"{module}: the record says {was}, the tree has {now}"
        for module, (was, now) in sorted(wrong.items())
    )
    assert record["coverage"]["statements"] == sum(measured.values()), (
        "the recorded total is not the sum of the tree's modules"
    )


def test_the_fingerprint_covers_the_code_and_the_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fingerprint has to describe everything the measurement describes.

    The pass/skip split the report states is a property of the suite as much
    as of the code: a test that is added changes the number of tests that
    ran, and the number the report states has to change with it. A
    fingerprint that covered only the code let a test be added without the
    report noticing, and the report went on claiming a split nobody had run.
    """
    script = _figure_script()
    source = tmp_path / "src"
    tests = tmp_path / "tests"
    source.mkdir()
    tests.mkdir()
    (source / "mod.py").write_bytes(b"def f():\n    return 1\n")
    (tests / "test_mod.py").write_bytes(b"def test_f():\n    assert True\n")

    monkeypatch.setattr(script, "SOURCE_ROOT", source)
    monkeypatch.setattr(script, "TESTS_ROOT", tests)
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    before = script.source_fingerprint()

    (tests / "test_mod.py").write_bytes(b"def test_f():\n    assert False\n")
    after_a_test = script.source_fingerprint()
    assert after_a_test != before, "a changed test did not make the figures stale"

    (source / "mod.py").write_bytes(b"def f():\n    return 2\n")
    assert script.source_fingerprint() != after_a_test, (
        "a changed module did not make the figures stale"
    )


def test_execution_report_discloses_every_weak_module() -> None:
    """A module below the disclosure threshold has to be listed in the report.

    The report promises to show where it is weak. A module that falls below the
    threshold and is not mentioned is a gap in that promise, and the table of
    weak modules is the first thing a reviewer reads.

    The table is generated, so the weak modules are derived from the
    measurement rather than written out by hand -- and the report has to name
    exactly those, no more and no fewer. A module above the threshold in the
    table is as much a mistake as a weak module missing from it: the table
    claims to be the weak list, and a reader who finds a 100% module in it has
    learned to distrust the whole table.
    """
    script = _figure_script()
    record = _recorded_measurement()
    stated = _stated_figures()

    assert record, "the report carries no measurement record"

    weak = script.weak_modules(record["coverage"]["files"])
    listed = script.listed_modules(REPORT.read_text(encoding="utf-8"))

    assert listed == weak, (
        f"the report's weak-module table names {listed} but the measurement says {weak}"
    )
    assert "coverage.weak_modules" in stated, "the report states no weak-module table"


def test_execution_report_history_figures_match_the_released_tags() -> None:
    """The historical test counts must be the counts those tags actually have.

    These numbers describe a released version, not the current tree, so they
    are measured in an archive of the tag itself. A hand-copied number is
    exactly the kind of figure that goes stale: it was wrong once already, and
    nothing but a measurement would have said so.
    """
    script = _figure_script()
    stated = _stated_figures()

    for tag in script.HISTORY_TAGS:
        count = script.collected_at_tag(tag)
        if count is None:
            pytest.skip(f"{tag} could not be measured here")
        values = sorted(set(stated.get(f"history.{tag}.tests", [])))
        assert values == [str(count)], (
            f"history.{tag}.tests: the report says {values or ['nothing']}, "
            f"the tag has {count} tests"
        )


def test_execution_report_lists_every_test_file() -> None:
    """The test-file table has to list every file the suite is made of.

    It is the reader's map from the report's claims to the code that backs
    them, and a row missing from it is a place the reader is not sent. The
    table was two files short once, and nothing noticed: the numbers in the
    table are checked, the rows in it are not.
    """
    report = REPORT.read_text(encoding="utf-8")
    assert "### 2.1" in report, "the report has no 2.1 section to hold the test-file table"
    section = report.split("### 2.1", 1)[-1].split("\n### ", 1)[0]
    listed = set(re.findall(r"\| `(test_[A-Za-z0-9_]+\.py)` \|", section))
    on_disk = {path.name for path in (REPO_ROOT / "tests").glob("test_*.py")}

    assert listed == on_disk, (
        f"the report's test-file table lists {sorted(listed)} "
        f"but the suite is made of {sorted(on_disk)}"
    )


def test_execution_report_does_not_claim_unbuilt_features() -> None:
    """The report must not describe Phase 2 as delivered."""
    report = REPORT.read_text(encoding="utf-8")

    for claim in (
        "MCP server is shipped",
        "agent orchestration works",
        "web workbench is available",
    ):
        assert claim not in report.lower()

    # It should say plainly that the review has not happened yet.
    assert "评审" in report or "review" in report.lower()


# -- the refresh script's convergence ---------------------------------------

#: How many self-checks the fake measurement reports.
FAKE_CHECKS = 8


def _test_file_table() -> str:
    """The report's test-file table, as the real report has it.

    The fake report stands in for the real one, and the real one's table
    lists every test file. A stand-in that did not would be refused by the
    refresh script for a reason the test using it is not about.
    """
    names = sorted(path.name for path in (REPO_ROOT / "tests").glob("test_*.py"))
    rows = "\n".join(f"| `{name}` | |" for name in names)
    return f"\n### 2.1 分层策略\n\n| 文件 | 覆盖内容 |\n|------|----------|\n{rows}\n"


def _fake_report(*, skipped: int = 0, skipped_tests: list[str] | None = None) -> str:
    """A report small enough to read, with the figures the refresh script owns.

    The record it carries describes an earlier measurement, so the script has
    something to keep when a new measurement turns out to be partial.
    """
    record = {
        "schema": 4,
        "code": {"api_endpoints": 15, "cli_commands": 10, "sample_apks": 5},
        "coverage": {"files": {"cli/main.py": [100, 45]}, "missing": 45, "statements": 100},
        "source_fingerprint": "sha256:stale",
        "suite": {
            "passed": 1,
            "skipped": skipped,
            "xfailed": 0,
            "failed": 0,
            "xpassed": 0,
            "skipped_tests": skipped_tests or [],
            "xfailed_tests": [],
        },
        "tests": {"fast": 1, "slow": 1, "total": 1},
    }
    return (
        "# A report\n\n"
        "Tests: <!--fig:tests.total-->1<!--/fig--> "
        "(<!--fig:tests.fast-->1<!--/fig--> fast + <!--fig:tests.slow-->1<!--/fig--> slow)\n\n"
        "Suite: <!--fig:suite.passed-->1<!--/fig--> passed, "
        "<!--fig:suite.skipped-->0<!--/fig--> skipped, "
        "<!--fig:suite.xfailed-->0<!--/fig--> xfailed\n\n"
        "Coverage: <!--fig:coverage.pct-->55.0%<!--/fig--> "
        "(<!--fig:coverage.covered-->55<!--/fig-->/<!--fig:coverage.total-->100<!--/fig-->)\n\n"
        + _test_file_table()
        + "\n<!--report-figures:"
        + json.dumps(record)
        + "-->\n"
    )


def _install_fake_measurements(
    script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    total: int = 354,
    fast: int = 271,
    slow: int = 83,
    code_failures: tuple[str, ...] = (),
    checks_failures: tuple[str, ...] = (),
    skipped: int = 0,
    skipped_tests: tuple[str, ...] = (),
    unaccounted: int = 0,
    prerequisites: tuple[str, ...] = (),
) -> None:
    """Replace the script's slow measurements with instant ones.

    The self-checks are modelled the way the real ones behave: they fail while
    the report states a number the code does not have, and pass once it states
    the current one. That is the whole difference the refresh has to keep
    straight — a self-check that fails because the report is out of date is the
    refresh's own problem; a test that fails because the code is broken is not.

    ``prerequisites`` says what this machine is missing, which is what makes a
    measurement partial: the suite's own skips say which machine ran, not
    whether the tree was measured.
    """

    def collected_tests(marker: str) -> tuple[int, int]:
        return (fast, total) if marker == "not slow" else (slow, total)

    def measure_code_tests() -> Any:
        return script.Outcome(
            counts={
                "passed": total - FAKE_CHECKS - len(code_failures) - skipped - unaccounted,
                "failed": len(code_failures),
                "skipped": skipped,
                "xfailed": 0,
                # The code run leaves the report's own self-checks out and they
                # are measured on their own, so the run that measured the tree
                # accounted for them by leaving them out.
                "deselected": FAKE_CHECKS,
            },
            failures=code_failures,
            skipped=skipped_tests,
        )

    def measure_report_checks(candidate: str, report_path: Path) -> Any:
        if checks_failures:
            return script.Outcome(
                counts={
                    "passed": FAKE_CHECKS - len(checks_failures),
                    "failed": len(checks_failures),
                    "skipped": 0,
                    "xfailed": 0,
                },
                failures=checks_failures,
            )
        stated = dict(script.FIGURE.findall(candidate))
        if stated.get("tests.total") != str(total):
            return script.Outcome(
                counts={"passed": FAKE_CHECKS - 1, "failed": 1, "skipped": 0, "xfailed": 0},
                failures=(
                    "tests/test_docs.py::test_execution_report_numbers_match_the_code"
                    " - AssertionError: the report disagrees with the code",
                ),
            )
        return script.Outcome(
            counts={"passed": FAKE_CHECKS, "failed": 0, "skipped": 0, "xfailed": 0},
            failures=(),
        )

    def read_coverage() -> Any:
        # ``cli/main.py`` sits exactly on the disclosure threshold, so the fake
        # measurement does not provoke a disclosure warning.
        return script.Coverage(files={"cli/main.py": [100, 10]}, statements=100, missing=10)

    def collected_at_tag(tag: str) -> int | None:
        # The third slow measurement. Without this the refresh really did
        # archive every released tag and really did run pytest's collector
        # inside each of them: nineteen seconds a run, and a run that failed
        # whenever the machine was busy. The real measurement has its own
        # test, in ``test_execution_report_history_figures_match_the_released_tags``.
        return 100

    monkeypatch.setattr(script, "collected_tests", collected_tests)
    monkeypatch.setattr(script, "measure_code_tests", measure_code_tests)
    monkeypatch.setattr(script, "measure_report_checks", measure_report_checks)
    monkeypatch.setattr(script, "read_coverage", read_coverage)
    monkeypatch.setattr(script, "collected_at_tag", collected_at_tag)
    monkeypatch.setattr(script, "missing_prerequisites", lambda: list(prerequisites))


def test_the_refresh_script_corrects_a_wrong_figure_in_one_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One run of the refresh must leave a report the self-checks pass.

    The report's numbers decide whether the self-checks pass, so a refresh that
    measured once and wrote once recorded the *failing* state of the self-checks
    — the state they are in precisely because the numbers are stale — and a
    second run was needed to correct it. The refresh now measures the
    self-checks against a report that is already consistent, so one run is
    enough, and a second run must change nothing at all.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 0

    refreshed = report.read_text(encoding="utf-8")
    assert "<!--fig:tests.total-->354<!--/fig-->" in refreshed
    assert "<!--fig:suite.passed-->354<!--/fig-->" in refreshed
    assert "<!--fig:coverage.pct-->90.0%<!--/fig-->" in refreshed

    # Running it again must find nothing left to change.
    assert script.main(["--report", str(report)]) == 0
    assert report.read_text(encoding="utf-8") == refreshed


def test_the_refresh_script_reports_a_real_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A test that fails for its own reasons must be reported, not swallowed.

    The refresh has to tell two things apart: a self-check that fails because
    the report is out of date, and a test that fails because the code is
    broken. Reporting only a count would hide which one it was, so the failing
    test is named.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report()
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(
        script,
        monkeypatch,
        code_failures=("tests/test_api.py::test_list_projects - AssertionError: boom",),
    )

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "tests/test_api.py::test_list_projects" in out
    assert "does not pass its own tests" in out
    # The report was left alone: its figures describe a run in which every test
    # passed, and this run was not one.
    assert report.read_text(encoding="utf-8") == original


def test_the_refresh_script_reports_a_self_check_it_cannot_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A self-check that still fails after the refresh needs a hand, not a rerun.

    The refresh can put the numbers right; it cannot add a row to a table a
    human wrote. When that happens the failure has to stay visible rather than
    being folded into the numbers.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    _install_fake_measurements(
        script,
        monkeypatch,
        checks_failures=(
            "tests/test_docs.py::test_execution_report_discloses_every_weak_module"
            " - AssertionError: a weak module is not disclosed",
        ),
    )

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "test_execution_report_discloses_every_weak_module" in out
    assert "needs a hand" in out
    # The numbers themselves are right, so they were written.
    assert "<!--fig:tests.total-->354<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_refresh_script_check_mode_names_the_figures_that_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--check must say which numbers are wrong, and must not write anything."""
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report()
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report), "--check"]) == 1

    out = capsys.readouterr().out
    assert "tests.total: 1 -> 354" in out
    assert "does not match a fresh measurement" in out
    assert report.read_text(encoding="utf-8") == original


def test_the_refresh_script_leaves_the_report_alone_when_the_measurement_is_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A partial measurement must not be written as if it were a complete one.

    A skipped test produces no coverage, so a run without the backends and
    the fixtures measures less than the report is about. The refresh keeps
    the previous coverage and says what is missing instead of quietly
    publishing a lower number -- and it reports the run as the failure it
    is, because a gate that cannot fail is not a gate.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    _install_fake_measurements(
        script,
        monkeypatch,
        prerequisites=("JADX (bash scripts/install-backends.sh)",),
    )

    def measure_code_tests() -> Any:
        outcome = script.Outcome(
            counts={"passed": 340, "failed": 0, "skipped": 6, "xfailed": 0, "deselected": 8},
            failures=(),
            skipped=tuple(f"tests.test_other::test_{index}" for index in range(6)),
        )
        return outcome

    monkeypatch.setattr(script, "measure_code_tests", measure_code_tests)

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "partial" in out
    # The coverage figures describe a complete measurement, so the previous
    # ones stay rather than the partial measurement's.
    assert "<!--fig:coverage.pct-->55.0%<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_refresh_script_takes_a_measurement_that_skipped_a_different_set_of_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A different set of skips is a different machine, not a different tree.

    The Windows-only tests skip on Linux and nowhere else, so a run whose
    skips differ from the recorded ones did not measure a different tree: it
    measured this tree on a different machine. Refusing the measurement for
    that reason threw it away -- the CI job that asks whether the report's
    figures describe the tagged tree kept the recorded figures and reported
    success without looking.

    What two machines cannot be compared on is the coverage: it describes the
    code the machine left unexercised, and the other machine exercised
    different code.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(
        _fake_report(skipped=1, skipped_tests=["tests.test_other::test_recorded"]),
        encoding="utf-8",
    )
    _install_fake_measurements(
        script,
        monkeypatch,
        skipped=1,
        skipped_tests=("tests.test_other::test_measured",),
    )

    assert script.main(["--report", str(report)]) == 0

    out = capsys.readouterr().out
    assert "partial" not in out, "a measurement of this tree was refused for the machine's sake"
    # The measurement was taken, so its coverage is the one the report states.
    assert "<!--fig:coverage.pct-->90.0%<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_refresh_script_takes_a_measurement_that_skipped_the_same_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same set of skips is the same measurement, and it is comparable.

    Two measurements that left the same tests unexercised measured the same
    code, so their coverage figures describe the same thing and the check
    compares them. A measurement that skipped the same ones is the same
    measurement, and it must not be refused: a tree whose basis has not
    changed is still a tree whose basis has not changed.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(
        _fake_report(skipped=1, skipped_tests=["tests.test_other::test_recorded"]),
        encoding="utf-8",
    )
    _install_fake_measurements(
        script,
        monkeypatch,
        skipped=1,
        skipped_tests=("tests.test_other::test_recorded",),
    )

    assert script.main(["--report", str(report)]) == 0

    out = capsys.readouterr().out
    assert "partial" not in out
    assert "<!--fig:coverage.pct-->90.0%<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_source_fingerprint_ignores_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same source must fingerprint the same on Windows and on Linux.

    Git checks out CRLF on Windows and LF on Linux. Hashing the raw bytes gave
    the same code two different fingerprints, and the report was declared stale
    on every platform except the one it was measured on -- which is how a
    fingerprint meant to catch drift ends up failing CI for a reason that has
    nothing to do with drift.
    """
    script = _figure_script()
    source_root = tmp_path / "pkg"
    tests_root = tmp_path / "tests"
    source_root.mkdir()
    tests_root.mkdir()
    (source_root / "mod.py").write_bytes(b"def f():\n    return 1\n")

    monkeypatch.setattr(script, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(script, "TESTS_ROOT", tests_root)
    # The fingerprint names files relative to the repository root, so the
    # stand-in root moves with the stand-in source.
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    lf_fingerprint = script.source_fingerprint()

    (source_root / "mod.py").write_bytes(b"def f():\r\n    return 1\r\n")
    crlf_fingerprint = script.source_fingerprint()

    assert lf_fingerprint == crlf_fingerprint

    # And a real change still moves the fingerprint, which is the whole point.
    (source_root / "mod.py").write_bytes(b"def f():\n    return 2\n")
    assert script.source_fingerprint() != lf_fingerprint


# -- the readme badges --------------------------------------------------------


def test_the_readme_badge_states_the_measured_numbers() -> None:
    """The badge is a measurement, not a number someone typed.

    A badge is a URL, so it cannot hold the report's markers -- and the
    number in it was written by hand, which is why the badge that shipped
    with v0.1.2 said 275 tests when the project had 444. The number is
    written from the same measurement the report is written from, so the
    two cannot drift apart.
    """
    script = _figure_script()
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    stated = script.apply_badges(readme, {"tests.passing": "801", "coverage.pct": "94.2%"})

    assert "badge/tests-801%20passing" in stated
    # The percent sign is spelled "%25" in a URL, and only once: a badge
    # that says "%%25" shows two percent signs.
    assert "badge/coverage-94.2%25-brightgreen" in stated
    assert "%%25" not in stated


def test_writing_the_badge_again_changes_nothing() -> None:
    """Refreshing a badge that is already right must leave it alone."""
    script = _figure_script()
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    values = {"tests.passing": "801", "coverage.pct": "94.2%"}

    once = script.apply_badges(readme, values)

    assert script.apply_badges(once, values) == once


def test_a_readme_without_the_badge_is_left_alone() -> None:
    """Not every readme carries a badge, and one that does not is not stale."""
    script = _figure_script()
    text = "# A readme\n\nNo badge here.\n"

    assert script.apply_badges(text, {"tests.passing": "801", "coverage.pct": "94.2%"}) == text


def test_a_badge_with_no_measurement_keeps_its_number() -> None:
    """A partial measurement measures neither figure, so neither is written.

    A badge with an empty number in it says nothing at all, which is worse
    than a badge with a stale one: a stale number can be checked, and an
    empty one cannot. The run that measured nothing leaves the badge alone.
    """
    script = _figure_script()
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for values in ({}, {"tests.passing": "", "coverage.pct": ""}):
        assert script.apply_badges(readme, values) == readme


def test_the_badge_states_the_numbers_the_report_states() -> None:
    """The badge and the report are one measurement, not two copies of it.

    The badge is written from the same values the report is written from --
    the same function, the same record -- so they cannot disagree. An earlier
    version read a key the record does not have, and every refresh wrote a
    badge with no coverage number in it: an empty number says nothing at all,
    which is worse than a stale one, because a stale number can be checked.
    """
    script = _figure_script()
    report = REPORT.read_text(encoding="utf-8")
    record = json.loads(script.RECORD.findall(report)[0])
    values = script.render_figures(record)

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    stated = script.apply_badges(
        readme,
        {"tests.passing": values["suite.passed"], "coverage.pct": values["coverage.pct"]},
    )

    assert f"badge/tests-{values['suite.passed']}%20passing" in stated
    assert f"badge/coverage-{values['coverage.pct'].rstrip('%')}%25" in stated


def test_the_refresh_script_refuses_a_measurement_that_missed_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that did not account for every test describes a smaller tree.

    A badge once said "353 passing" on a tree of 885 tests: the run had
    stopped early, and the numbers of a run that does not cover the tree are
    numbers about part of it. The script has to refuse such a measurement
    rather than publish it.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report()
    report.write_text(original, encoding="utf-8")
    # The run accounts for 300 fewer tests than the tree holds.
    _install_fake_measurements(script, monkeypatch, unaccounted=300)

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "did not account for every test" in out
    assert "Nothing was written" in out
    assert report.read_text(encoding="utf-8") == original


def test_the_refresh_script_refuses_a_report_whose_table_misses_a_test_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The table's rows are checked, not only the numbers in them.

    The table is the reader's map from the report's claims to the code that
    backs them, and its rows are written by hand. A file added to the suite
    without a row in the table left the table quietly short of one file, and
    the refresh wrote the new numbers into that table all the same: it read
    the numbers the table carries and never the files the table names.

    So the two sets are compared before anything is measured, and a table
    that does not describe the suite is refused rather than written over.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    # The row for one test file of the suite is not there any more.
    original = _fake_report().replace("| `test_docs.py` | |\n", "")
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "does not describe the suite" in out
    assert "test_docs.py" in out
    assert "Nothing was written" in out
    # The refusal writes the table's audit into the record -- the fact the
    # run refused about -- and nothing else: the figures are not written.
    refreshed = report.read_text(encoding="utf-8")
    script_figures = _figure_script().FIGURE
    original_figures = list(script_figures.findall(original))
    refreshed_figures = list(script_figures.findall(refreshed))
    assert refreshed_figures == original_figures
    record = script.read_record(refreshed)
    assert record["table"]["missing_rows"] == ["test_docs.py"]
    assert record["table"]["stale_rows"] == []
    # The record's other facts are the previous measurement's, untouched.
    assert record["source_fingerprint"] == "sha256:stale"
    assert record["tests"] == {"fast": 1, "slow": 1, "total": 1}


def test_the_refresh_script_refuses_a_report_whose_table_names_a_file_that_is_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A row for a file the suite does not have is as wrong as a missing one.

    The reader is sent to a file that is not there, which is the same defect
    as not being sent to a file that is.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report().replace("| `test_docs.py` | |", "| `test_gone.py` | |")
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 1

    out = capsys.readouterr().out
    assert "does not describe the suite" in out
    assert "test_gone.py" in out
    record = script.read_record(report.read_text(encoding="utf-8"))
    assert record["table"]["stale_rows"] == ["test_gone.py"]
    # The table names one file fewer than the suite has, too: the row that
    # was replaced was the row for a file the suite really has.
    assert record["table"]["missing_rows"] == ["test_docs.py"]
    # The refusal wrote the audit into the record and nothing else: the
    # figures the document states are the ones it stated before.
    refreshed = report.read_text(encoding="utf-8")
    script_figures = _figure_script().FIGURE
    assert list(script_figures.findall(refreshed)) == list(script_figures.findall(original))


def test_the_record_names_the_rows_the_table_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A table the refresh refused is a fact the measurement carries.

    The refusal prints the missing rows and stops -- and before this, that
    print was the only trace: the report on disk still described a table
    that was short, and nothing beside it said so. The record the report
    carries now states the audit -- which rows the table is missing, which
    rows it names that are gone -- so a reader (and a check) can see the
    disagreement without rerunning the two-second comparison. The audit is
    written even though the run refuses: a fact about the report is a fact
    about the report, whether or not the numbers got written.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report().replace("| `test_docs.py` | |\n", "")
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 1
    capsys.readouterr()

    record = script.read_record(report.read_text(encoding="utf-8"))
    audit = record.get("table", {})
    assert audit.get("missing_rows") == ["test_docs.py"], audit
    assert audit.get("stale_rows") == [], audit


def test_the_record_reports_a_complete_table_with_empty_lists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A table that names every file is recorded as naming every file.

    The audit is stated either way. A key that only appears when something
    is wrong is a key a reader cannot check the absence of: an empty
    ``missing_rows`` is the claim that the table is complete, and it is
    checkable precisely because it is always there.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 0

    record = script.read_record(report.read_text(encoding="utf-8"))
    audit = record.get("table", {})
    assert audit.get("missing_rows") == [], audit
    assert audit.get("stale_rows") == [], audit


def test_the_table_audit_counts_as_a_generated_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale row named in the record is caught by the record's own reader.

    The audit lives in the record; a record that says the table is missing
    a file, beside a table that still misses it, is a report nobody should
    trust. This check reads the audit and the table and compares them, the
    way the refresh's refusal does -- so a table fixed by hand while the
    record still names it (or the other way round) is a red test, not a
    quiet disagreement between two facts.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    original = _fake_report().replace("| `test_docs.py` | |\n", "")
    report.write_text(original, encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    assert script.main(["--report", str(report)]) == 1

    record = script.read_record(report.read_text(encoding="utf-8"))
    mismatch = script.test_file_table(report.read_text(encoding="utf-8"))
    assert mismatch is not None
    missing, stale = mismatch
    assert record["table"]["missing_rows"] == missing
    assert record["table"]["stale_rows"] == stale


def test_the_refresh_script_does_not_write_the_readme_when_it_is_pointed_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refresh of a copy must not touch the project's own readme.

    The script writes the badge into the readme, and the test suite runs the
    script against a copy of the report with measurements it made up. A
    script that wrote the readme in that case put "353 passing" on the
    project's front page -- and the suite did it on every run, so the number
    in the badge was whatever the last test had measured.

    The readme is written only when the real report is the one being
    refreshed, exactly as the status page is.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    readme = REPO_ROOT / "README.md"
    before = readme.read_bytes()

    _install_fake_measurements(script, monkeypatch)

    script.main(["--report", str(report)])

    assert readme.read_bytes() == before, "the refresh wrote to the project's readme"


def test_the_two_copies_of_the_project_rules_are_the_same() -> None:
    """The rules are written down twice, and the two copies have to agree.

    ``CLAUDE.md`` is what Claude Code reads; ``AGENTS.md`` is the same file
    under the name the other agent tools read. Two copies of one set of rules
    are two things that can drift apart, and a rule that one tool sees and
    the other does not is a rule nobody can rely on.
    """
    agents = REPO_ROOT / "AGENTS.md"
    if not agents.exists():
        pytest.skip("this checkout has no AGENTS.md")

    def read(path: Path) -> str:
        # The line endings are normalised: git checks the files out with the
        # platform's, and a difference in them is not a difference in the rules.
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")

    assert read(agents) == read(REPO_ROOT / "CLAUDE.md"), (
        "AGENTS.md and CLAUDE.md have drifted apart: they are the same file "
        "under two names, and a tool that reads one must read the other"
    )


# -- what the source fingerprint covers ---------------------------------------

#: The markers around the paragraph that says what the fingerprint covers.
FINGERPRINT_SECTION = ("<!--fingerprint-coverage-->", "<!--/fingerprint-coverage-->")


def _the_fingerprint_section(report: str) -> str:
    """The paragraph of the report that says what the fingerprint covers."""
    start, end = FINGERPRINT_SECTION
    assert start in report, "the report does not say what the fingerprint covers"
    body = report.split(start, 1)[1].split(end, 1)[0]
    return body


def test_the_report_states_what_the_source_fingerprint_covers() -> None:
    """The report says which files the fingerprint covers, and which it does not.

    The fingerprint is the hash of the files the measurement read. A file
    that is not in it can change without the report noticing — and the
    release materials repeat a number that comes from a script under
    ``scripts/``, so "not in the fingerprint" has to be said out loud rather
    than left to be discovered.
    """
    script = _figure_script()
    report = REPORT.read_text(encoding="utf-8")
    section = _the_fingerprint_section(report)

    for name in script.FINGERPRINT_FILES:
        assert name in section, f"the report does not say the fingerprint covers {name}"
    for root in ("src/dexatlas", "tests"):
        assert root in section, f"the report does not say the fingerprint covers {root}"
    for name in ("scripts/verify-public-contracts.py", "scripts/m10_selfcheck.py"):
        assert name in section, f"the report does not say the fingerprint does not cover {name}"


def test_the_readmes_state_what_the_source_fingerprint_covers() -> None:
    """The readmes say it too: the number a reader sees is the measured one.

    The badge in the readme is the measured test count. What it was measured
    on has to be stated where the badge is, or the number is a claim with
    nothing behind it.
    """
    for name in ("README.md", "README.zh-CN.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        for covered in (
            "src/dexatlas",
            "tests",
            "pyproject.toml",
            "scripts/refresh-report-figures.py",
        ):
            assert covered in text, f"{name} does not say the fingerprint covers {covered}"
        for excluded in ("scripts/verify-public-contracts.py", "scripts/m10_selfcheck.py"):
            assert excluded in text, (
                f"{name} does not say the fingerprint does not cover {excluded}"
            )


# -- the readme first screen --------------------------------------------------

#: The front page's header block ends here. Everything above it is what a
#: visitor reads before they scroll.
FIRST_SCREEN_END = "</div>"

#: Any digit at all. The alt text names a picture; the numbers *on* the
#: picture belong to the reports that hold them. A number written into an alt
#: text goes stale more quietly than any other number in the repository, and
#: ``docs/reports/social-preview-howto.md`` has said so since the card was
#: drawn: "alt 文本里不写数字".
A_DIGIT = re.compile(r"\d")

#: A run of three or more digits. One and two digit numbers are dates,
#: versions and section numbers ("v1.0.0", "M10", "Phase 3"); three or more
#: are counts -- "1612 tests", "1,690", "7135/7650 lines".
MANY_DIGITS = re.compile(r"\d{3,}")

#: A percentage. The coverage figure is "93.3%": its digits sit on either
#: side of the point, so a rule about digit runs cannot see it.
A_PERCENTAGE = re.compile(r"\d+(?:\.\d+)?\s*%")

#: A number counting something the measurement measures: "1612 tests",
#: "27 skips", "1612 个测试". A two digit count is a count too -- the unit it
#: is counted in is what tells it apart from a version or a date.
A_COUNTED_QUANTITY = re.compile(
    r"\d+\s*(?:个\s*)?(?:tests?|skips?|checks?|测试|跳过|检查)",
    re.IGNORECASE,
)


def _first_screen(text: str) -> str:
    """The header block of a front page: everything above its closing ``</div>``."""
    end = text.find(FIRST_SCREEN_END)
    if end < 0:
        raise AssertionError("the readme's header block has no closing </div>")
    return text[:end]


def _visible_text(line: str) -> str:
    """What a reader of one line actually sees.

    Markup is not text and an address is not text either: the width of a
    picture ("900") and the measured numbers inside a badge's URL are numbers
    no reader reads as a measurement -- the badge is written from the
    measurement, so it cannot go stale.
    """
    without_tags = re.sub(r"<[^>]*>", " ", line)
    return re.sub(r"\]\([^)]*\)", "]", without_tags)


def _alt_texts(line: str) -> list[str]:
    """The alt text of every image in a line, in HTML and in Markdown."""
    return re.findall(r'alt="([^"]*)"', line) + re.findall(r"!\[([^\]]*)\]", line)


def _stated_measurements(region: str) -> list[str]:
    """The numbers the front screen puts in front of its reader.

    Every number a reader can see in the header block: in the text, or in the
    alt text of a picture. The badge URLs carry the measured numbers as well,
    and they are left alone -- ``apply_badges`` writes them from the
    measurement, so they cannot go stale.
    """
    stated: list[str] = []
    for line in region.splitlines():
        for alt in _alt_texts(line):
            if A_DIGIT.search(alt):
                stated.append(alt)
        visible = _visible_text(line)
        stated.extend(MANY_DIGITS.findall(visible))
        stated.extend(A_PERCENTAGE.findall(visible))
        stated.extend(A_COUNTED_QUANTITY.findall(visible))
    return stated


def test_the_readme_first_screen_states_no_measurement() -> None:
    """The front page must not restate the measurement.

    The card's numbers change on every re-measurement, and the front page is
    the one page nobody diffs: the badges are written by the measurement
    script, and everything around them is written by hand. When the sentence
    under the badges used to say what had been measured -- "one measurement of
    the whole tree (1612 tests, 0 skipped)" -- and the alt text of the card
    used to repeat it ("93.3% first-party code coverage, 1612 tests, 49 public
    contract checks"), each of those numbers was a second copy of the
    measurement, kept in step by hand, and this release cycle is what proved
    it is not kept in step: they went stale and nothing said so.

    The fix is not a second place to update. It is no number at all: the
    front page points at the report, and the report holds the numbers. This
    test is what keeps it that way -- it fails the moment a number is written
    back into the header block, in the text or in an alt attribute.
    """
    for name in ("README.md", "README.zh-CN.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        stated = _stated_measurements(_first_screen(text))
        assert stated == [], f"{name} states {stated} in its first screen"


def test_the_gate_catches_the_alt_text_that_used_to_carry_the_measurement() -> None:
    """The gate has to bite on the wording that was there before.

    This is the alt text the card carried until it was written out by hand:
    three measured numbers, none of them written by the measurement script.
    """
    alt = (
        "DexAtlas — From APK to Evidence: 93.3% first-party code coverage, "
        "1612 tests, 49 public contract checks"
    )
    line = f'  <img src=".github/social-preview.png" alt="{alt}" width="900">'

    assert _stated_measurements(line) == [alt]


def test_the_gate_catches_the_sentence_that_used_to_state_the_measurement() -> None:
    """The same for the sentence under the badges.

    The old wording was in Chinese in both readmes, and it stated the test
    count, the number of skipped tests, and the number of missing samples.
    """
    line = (
        "> 徽章是**完整环境下**的一次测量（1612 个测试、0 跳过）。"  # noqa: RUF001
        "在没抓第三方样本的机器上，`pytest` 会显示 27 个 skip"  # noqa: RUF001
    )
    stated = _stated_measurements(line)

    assert "1612" in stated
    assert "0 跳过" in stated
    assert "27 个 skip" in stated


def test_the_gate_leaves_the_written_badges_alone() -> None:
    """The badge carries the measured numbers, and they are not a fault.

    The badge's URL is written from the measurement by ``apply_badges``, so it
    cannot go stale. A checker that read the raw line instead of what a reader
    sees would fail on every badge, and would be turned off.
    """
    line = (
        "[![Tests](https://img.shields.io/badge/tests-1689%20passing-brightgreen.svg)]"
        "(docs/reports/phase1-execution-report.md)"
    )

    assert _stated_measurements(line) == []
