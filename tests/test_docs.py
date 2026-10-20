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
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}

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
    return [
        path
        for path in REPO_ROOT.rglob("*.md")
        if not SKIP_DIRS & set(path.relative_to(REPO_ROOT).parts)
    ]


@pytest.mark.parametrize("doc", REQUIRED_DOCS)
def test_required_document_exists(doc: str) -> None:
    assert (REPO_ROOT / doc).is_file(), f"{doc} is missing"


def test_all_relative_links_resolve() -> None:
    broken: list[str] = []

    for markdown in _markdown_files():
        text = markdown.read_text(encoding="utf-8", errors="replace")
        for match in RELATIVE_LINK.finditer(text):
            target = match.group(1).split("#")[0]
            if not target:
                continue
            if not (markdown.parent / target).resolve().exists():
                relative = markdown.relative_to(REPO_ROOT)
                broken.append(f"{relative}: {target}")

    assert not broken, "broken relative links:\n" + "\n".join(sorted(set(broken)))


def test_readme_links_to_the_installation_guide() -> None:
    """The Phase 1 exit criterion is that a stranger can install from the README alone."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/install.md" in readme


def test_readme_does_not_overclaim() -> None:
    """The README must not describe unbuilt features as shipped.

    Phase 2 and Phase 3 capabilities are named in the roadmap table, which is fine;
    the Quick Start section must not tell a reader to use them.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    quick_start = readme.split("## Quick start", 1)[-1].split("\n## ", 1)[0]
    for unbuilt in ("mcp", "agent", "workbench"):
        assert unbuilt not in quick_start.lower(), (
            f"the Quick Start section references {unbuilt!r}, which is not built yet"
        )


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

    The exception is DexAtlas's own test applications. They are first-party, built from
    the smali sources committed beside them, and rebuildable with
    ``scripts/build-test-apks.sh``. The allowed set is derived from what is on disk
    rather than written out by hand, so a sample added without its sources — or a
    third-party APK slipped into ``examples/`` — fails here.
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

    examples = REPO_ROOT / "examples"
    allowed = {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for path in examples.rglob("*")
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
    the sum would make the sum smaller than the suite.
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
    )

    assert ran == total, (
        f"the report says {suite['passed']} passed, {suite['skipped']} skipped, "
        f"{suite['xfailed']} xfailed, {suite['failed']} failed and "
        f"{suite['xpassed']} xpassed, which is {ran} of the {total} tests in the tree"
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
        "<!--report-figures:" + json.dumps(record) + "-->\n"
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
) -> None:
    """Replace the script's slow measurements with instant ones.

    The self-checks are modelled the way the real ones behave: they fail while
    the report states a number the code does not have, and pass once it states
    the current one. That is the whole difference the refresh has to keep
    straight — a self-check that fails because the report is out of date is the
    refresh's own problem; a test that fails because the code is broken is not.
    """

    def collected_tests(marker: str) -> tuple[int, int]:
        return (fast, total) if marker == "not slow" else (slow, total)

    def measure_code_tests() -> Any:
        return script.Outcome(
            counts={
                "passed": total - FAKE_CHECKS - len(code_failures) - skipped,
                "failed": len(code_failures),
                "skipped": skipped,
                "xfailed": 0,
                "deselected": 0,
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

    A skipped test produces no coverage, so a run with skips measures a
    different tree. The refresh keeps the previous coverage and says what is
    missing instead of quietly publishing a lower number.
    """
    script = _figure_script()
    report = tmp_path / "phase1-execution-report.md"
    report.write_text(_fake_report(), encoding="utf-8")
    _install_fake_measurements(script, monkeypatch)

    def measure_code_tests() -> Any:
        outcome = script.Outcome(
            counts={"passed": 340, "failed": 0, "skipped": 6, "xfailed": 0, "deselected": 8},
            failures=(),
            skipped=tuple(f"tests.test_other::test_{index}" for index in range(6)),
        )
        return outcome

    monkeypatch.setattr(script, "measure_code_tests", measure_code_tests)

    assert script.main(["--report", str(report)]) == 0

    out = capsys.readouterr().out
    assert "partial" in out
    # The coverage figures describe a complete measurement, so the previous
    # ones stay rather than the partial measurement's.
    assert "<!--fig:coverage.pct-->55.0%<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_refresh_script_refuses_a_measurement_that_skipped_a_different_set_of_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same number of skips is not the same set of skips.

    Skipping and passing are different states, so the question "is this
    measurement complete" is about *which* tests sat out, not about how many.
    A measurement that skipped a different set of tests measured a different
    tree, and publishing its numbers as *the* numbers would be a small lie.

    The comparison this replaces was between the counts, and a count of one
    skip matched a count of one skip however different the two were.
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
    assert "partial" in out, "a measurement that skipped a different set was taken as complete"
    # The coverage figures describe a complete measurement, so the previous
    # ones stay rather than the partial measurement's.
    assert "<!--fig:coverage.pct-->55.0%<!--/fig-->" in report.read_text(encoding="utf-8")


def test_the_refresh_script_takes_a_measurement_that_skipped_the_same_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same set of skips is the same measurement, and it is complete.

    The rule above refuses a measurement that skipped a different set of
    tests. A measurement that skipped the same ones is the same measurement,
    and it must not be refused: a tree whose basis has not changed is still
    a tree whose basis has not changed.
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
