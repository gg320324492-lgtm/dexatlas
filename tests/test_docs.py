"""Documentation integrity.

A broken link in a README is invisible until someone follows it, which is usually
someone deciding whether this project is worth their time. These checks are cheap.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

#: Markdown links, excluding external URLs, anchors and mailto.
RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)\s]+)")

#: Directories whose contents are generated or third-party.
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}

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
    git actually tracks. DexAtlas's own demo application is the single exception: it is
    first-party, built from the smali sources in ``examples/demo-app/``, and rebuildable.
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

    allowed = {"examples/demo-app/demo.apk"}
    tracked_bad = [
        name
        for name in result.stdout.splitlines()
        if Path(name).suffix.lower() in {".apk", ".dex", ".aab", ".so", ".jar"}
        and name not in allowed
    ]
    assert not tracked_bad, f"third-party analysis artifacts are tracked: {tracked_bad}"


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


REPORT = REPO_ROOT / "docs" / "reports" / "phase1-execution-report.md"


def test_execution_report_exists() -> None:
    assert REPORT.is_file(), "the Phase 1 execution report is missing"


def test_execution_report_numbers_match_the_code() -> None:
    """A report whose numbers drifted from the code is worse than no report.

    The review this feeds reads claims like "10 CLI commands" and "88% coverage".
    If those stop being true the reviewer is reading fiction.
    """
    report = REPORT.read_text(encoding="utf-8")

    cli = (REPO_ROOT / "src/dexatlas/cli/main.py").read_text(encoding="utf-8")
    commands = cli.count("@app.command()")
    # Fullwidth parentheses are deliberate here: the report is written in Chinese,
    # where they are the correct form and halfwidth ones read as machine output.
    assert f"CLI（{commands} 个命令）" in report, (  # noqa: RUF001
        f"the report does not state the current CLI command count ({commands})"
    )

    api = (REPO_ROOT / "src/dexatlas/api/app.py").read_text(encoding="utf-8")
    endpoints = len(re.findall(r"@app\.(get|post|delete|put)\(", api))
    assert f"REST API（{endpoints} 个端点）" in report, (  # noqa: RUF001
        f"the report does not state the current endpoint count ({endpoints})"
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


def test_execution_report_layer_counts_match_pytest() -> None:
    """The report states 163 fast / 44 slow tests. Those must be the real numbers.

    Checked by running pytest's own collector rather than counting markers in the source,
    so the figure in the report cannot drift from what actually runs.
    """
    import subprocess

    report = REPORT.read_text(encoding="utf-8")

    counts = {}
    for label, marker in (("fast", "not slow"), ("slow", "slow")):
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
        counts[label] = int(match.group(1))

    assert f"| {counts['fast']} |" in report, (
        f"the report does not state the current fast-suite size ({counts['fast']})"
    )
    assert f"| {counts['slow']} |" in report, (
        f"the report does not state the current slow-suite size ({counts['slow']})"
    )
