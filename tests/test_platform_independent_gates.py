"""The gates answer the same question on every platform.

A gate whose verdict depends on the machine it runs on is worse than no
gate: a citation with the wrong case passes on Windows and fails on CI, a
placeholder link resolves on Windows and nowhere else, and a measurement
whose subprocess output is decoded with the console's encoding crashes here
and not there. These tests pin the rules that make the gates
platform-independent, in the scripts themselves.
"""

from __future__ import annotations

import importlib.util
import io
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CITATIONS = REPO_ROOT / "scripts" / "check-doc-citations.py"
REFRESH = REPO_ROOT / "scripts" / "refresh-report-figures.py"
VERSION_CLAIMS = REPO_ROOT / "scripts" / "check-version-claims.py"
VERIFY_CONTRACTS = REPO_ROOT / "scripts" / "verify-public-contracts.py"
SELFCHECK = REPO_ROOT / "scripts" / "m10_selfcheck.py"
PLATFORM_GATES = REPO_ROOT / "scripts" / "check-platform-gates.py"
PLATFORM_GATES_INVENTORY = REPO_ROOT / "scripts" / "platform-gates.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# D17 -- a citation whose path is spelled with the wrong case is a finding
# ---------------------------------------------------------------------------


def test_a_wrong_case_citation_fails_on_this_platform_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The file system must not answer the case question for the checker.

    Windows answers ``is_file()`` for any spelling of a name, so a citation
    that said ``SRC/dexatlas/core/models.py`` found ``src/dexatlas/core/models.py``
    and passed on Windows while CI reported it. The path is matched component
    by component against the directories' real entries, so the wrong-case
    citation fails wherever the suite runs -- and it is not rescued by the
    bare-name index, whose folded match is for bare names only.
    """
    checker = _load(CITATIONS, "dexatlas_citations_case")
    document = tmp_path / "doc.md"
    document.write_text(
        "The `Provenance` class is built at `SRC/dexatlas/core/models.py:1-2`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    assert "unresolved paths: 1" in capsys.readouterr().out


def test_a_wrong_case_file_name_is_not_rescued_by_the_bare_name_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A path that misses is a miss, even when the file name exists elsewhere.

    The old probe answered by asking the file system, which on Windows says
    yes to any spelling; the fallback index folds case by design. Neither
    may rescue a citation whose *path* is spelled wrong.
    """
    checker = _load(CITATIONS, "dexatlas_citations_case_index")
    document = tmp_path / "doc.md"
    document.write_text(
        "The `Provenance` class is built at `src/dexatlas/core/MODELS.py:1-2`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 1
    assert "unresolved paths: 1" in capsys.readouterr().out


def test_a_right_case_citation_still_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The exact-name probe still finds what an exact name names."""
    checker = _load(CITATIONS, "dexatlas_citations_case_ok")
    document = tmp_path / "doc.md"
    document.write_text(
        "See `src/dexatlas/core/models.py:1-2` for the module's own words.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    assert checker.main() == 0
    written = capsys.readouterr().out
    assert "unresolved paths: 0" in written
    assert "drifted: 0" in written


# ---------------------------------------------------------------------------
# D18 -- the file index does not depend on what the machine has fetched
# ---------------------------------------------------------------------------


def test_the_file_index_ignores_the_fetched_fixtures() -> None:
    """A downloaded sample must not become a citation's candidate.

    The fixtures are fetched, not committed. A checker that indexes them
    answers a question about whatever the machine happens to have downloaded,
    and two machines running the same commit can disagree.
    """
    checker = _load(CITATIONS, "dexatlas_citations_skip")
    assert "fixtures" in checker.SKIP_DIRECTORIES


def test_the_document_list_is_derived_from_the_checker() -> None:
    """The remapper re-derives exactly what the checker checks.

    A document the checker reads but the remapper does not is a document
    whose citations drift and are never moved back.
    """
    remap = _load(REPO_ROOT / "scripts" / "remap-citations.py", "dexatlas_remap_docs")
    checker = _load(CITATIONS, "dexatlas_citations_docs")
    assert tuple(remap._document_list()) == tuple(checker.DOCS)


# ---------------------------------------------------------------------------
# D19 -- a document with an upper-case extension is read on every platform
# ---------------------------------------------------------------------------


def test_the_document_list_uses_explicit_suffixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A document list built by explicit suffixes agrees across platforms.

    A glob pattern matches case-insensitively on Windows and
    case-sensitively on Linux, so a ``RELEASE.MD`` written in upper case was
    a document one platform checked and the other never read. The suffix is
    compared exactly, as git's own pathspec would, and the release notes are
    read wherever the tree has them.
    """
    checker = _load(CITATIONS, "dexatlas_citations_glob")
    releases = tmp_path / "docs" / "releases"
    reports = tmp_path / "docs" / "reports"
    releases.mkdir(parents=True)
    reports.mkdir(parents=True)
    (releases / "v0.1.0.md").write_text("notes\n", encoding="utf-8")
    (releases / "UPPER.MD").write_text("notes in upper case\n", encoding="utf-8")
    (reports / "v1.0.0-github-release-body.md").write_text("body\n", encoding="utf-8")

    listed = checker.release_documents(tmp_path)

    names = [path.name for path in listed]
    assert "v0.1.0.md" in names
    assert "v1.0.0-github-release-body.md" in names
    # The upper-case extension is outside the list on this platform too:
    # what matters is that the *same* list comes out everywhere.
    assert "UPPER.MD" not in names


# ---------------------------------------------------------------------------
# D20 -- the version checker's fallback walk finds the same documents
# ---------------------------------------------------------------------------


def test_the_markdown_walk_matches_the_document_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fallback walk reads the same markdown set either spelling gives.

    The walk stands in for git when there is no git; a document it missed on
    one platform was a claim that platform never checked. The files live in
    different directories because a case-insensitive file system cannot hold
    two spellings of one name side by side.
    """
    checker = _load(VERSION_CLAIMS, "dexatlas_version_claims_walk")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "status.md").write_text("lower\n", encoding="utf-8")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "STATUS.MD").write_text("upper\n", encoding="utf-8")
    monkeypatch.setattr(checker, "REPO", tmp_path)
    monkeypatch.setattr(checker, "git_optional", lambda *args: None)

    names = checker._markdown_files()

    assert "docs/status.md" in names
    assert "notes/STATUS.MD" not in names


def test_the_markdown_walk_sorts_before_the_skip_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The walk skips the tools' own directories and sorts what it keeps."""
    checker = _load(VERSION_CLAIMS, "dexatlas_version_claims_walk_skips")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "z.md").write_text("z\n", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text("a\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.md").write_text("hidden\n", encoding="utf-8")
    monkeypatch.setattr(checker, "REPO", tmp_path)
    monkeypatch.setattr(checker, "git_optional", lambda *args: None)

    names = checker._markdown_files()

    assert names == ["docs/a.md", "docs/z.md"]


# ---------------------------------------------------------------------------
# D29 -- the walk's order is the written order, not the platform's
# ---------------------------------------------------------------------------


def test_the_markdown_walk_sorts_as_posix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Paths sort as the POSIX spellings they are written as.

    Sorting ``Path`` objects compares the platform's normalisation, which
    folds case on Windows: the same set of files came out in two orders, and
    the checker's output order differed by platform.
    """
    checker = _load(VERSION_CLAIMS, "dexatlas_version_claims_sort")
    for name in ("A.md", "b.md", "C.md", "d.md"):
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(checker, "REPO", tmp_path)
    monkeypatch.setattr(checker, "git_optional", lambda *args: None)

    names = checker._markdown_files()

    assert names == ["A.md", "C.md", "b.md", "d.md"]


# ---------------------------------------------------------------------------
# D21 -- a machine without git is told what is missing, not handed a traceback
# ---------------------------------------------------------------------------


def test_git_functions_say_git_is_missing_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A machine without git on PATH gets the fallback, not a crash.

    Git for Windows often is not on the system PATH. The subprocess call
    used to raise ``FileNotFoundError``, whose exit code is the one a real
    finding gives -- so the crash and the finding were one answer.
    """
    checker = _load(VERSION_CLAIMS, "dexatlas_version_claims_nogit")

    def _no_git(name: str) -> str | None:
        return None if name == "git" else "/usr/bin/git"

    monkeypatch.setattr(checker.shutil, "which", _no_git)

    assert checker.git_succeeds("tag", "--list") is False
    assert checker.git_optional("tag", "--list") is None
    with pytest.raises(SystemExit, match="git is not available"):
        checker.git("tag", "--list")


# ---------------------------------------------------------------------------
# D6 -- the remapper writes the bytes git checks in
# ---------------------------------------------------------------------------


def test_the_remapper_writes_lf_line_endings(tmp_path: Path) -> None:
    """A rewritten document keeps the line endings git checks in.

    A text-mode write translates ``\\n`` into ``\\r\\n`` on Windows, and a
    commit normalises it back -- so the developer's ``git diff`` showed
    nothing at all while the file on disk had been wholly rewritten.
    """
    remap = _load(REPO_ROOT / "scripts" / "remap-citations.py", "dexatlas_remap_newlines")
    document = tmp_path / "doc.md"
    document.write_bytes(b"see `a.py:1`\n")

    remap._rewrite(remap._checker(), document)

    assert b"\r" not in document.read_bytes()


# ---------------------------------------------------------------------------
# D2 -- the measurement's subprocess output is UTF-8 on both sides
# ---------------------------------------------------------------------------


def test_the_measurement_decodes_its_children_as_utf8() -> None:
    """The measurement reads what its children wrote, not what the console is.

    The child runs under ``PYTHONUTF8=1`` and the parent decodes as UTF-8, so
    the two sides of the pipe agree on the bytes whatever the machine's code
    page is. A decoding failure used to surface as ``stdout is None`` further
    down -- a type error about a value that was never a string.
    """
    script = _load(REFRESH, "dexatlas_refresh_utf8")

    result = script.run(
        sys.executable, "-c", "print('中文 — em-dash — ok')", env={"PYTHONUTF8": "1"}
    )

    assert result.stdout is not None
    assert "中文" in result.stdout
    assert "em-dash" in result.stdout


def test_the_measurement_environment_pins_pythonutf8() -> None:
    """Every process the measurement starts writes UTF-8.

    The parent cannot know what a child will do with its output; the one
    thing it can pin is the child's encoding, and this is where it does.
    """
    script = _load(REFRESH, "dexatlas_refresh_env")

    env = script.measurement_env({"PATH": "/usr/bin"})

    assert env["PYTHONUTF8"] == "1"


# ---------------------------------------------------------------------------
# D4 -- a coverage file another run holds open stops the run with a message
# ---------------------------------------------------------------------------


def test_a_stale_coverage_file_that_cannot_be_deleted_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A measurement whose data file is held by another run must not race it.

    Windows refuses to delete an open file; deleting it anyway on a platform
    that allows it would destroy the other run's numbers. Either way the run
    has to stop with a message that names the likely cause.
    """
    script = _load(REFRESH, "dexatlas_refresh_unlink")
    stale = tmp_path / ".coverage.stale"
    stale.write_bytes(b"stale")
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)

    def _refuses(self: Path) -> None:
        raise PermissionError(f"the file is open: {self}")

    monkeypatch.setattr(Path, "unlink", _refuses)

    with pytest.raises(SystemExit, match="another measurement may be running"):
        script.discard_stale_coverage()


# ---------------------------------------------------------------------------
# D5 -- a ``.PY`` file enters the same fingerprint on every platform
# ---------------------------------------------------------------------------


def test_the_fingerprint_counts_the_same_suffixes_on_every_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fingerprint's file set does not follow the file system's case rules.

    A glob pattern matched a stray ``.PY`` file on Windows and not on Linux,
    so the two platforms hashed two different trees and the CI check declared
    the tree changed. The suffix is compared exactly, as git's own pathspec
    would be. The files live in different directories because a
    case-insensitive file system cannot hold two spellings of one name side
    by side.
    """
    script = _load(REFRESH, "dexatlas_refresh_fingerprint")
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "extra").mkdir()
    (tmp_path / "src" / "extra" / "UPPER.PY").write_text("y = 2\n", encoding="utf-8")
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(script, "SOURCE_ROOT", tmp_path / "src")
    monkeypatch.setattr(script, "TESTS_ROOT", tmp_path / "tests")
    monkeypatch.setattr(script, "FINGERPRINT_FILES", ())

    names = {path.name for path in script.fingerprint_files()}

    assert "mod.py" in names
    assert "UPPER.PY" not in names


# ---------------------------------------------------------------------------
# D28 -- a measurement with other tool versions does not describe the report
# ---------------------------------------------------------------------------


def test_a_tool_version_the_report_does_not_name_stops_the_measurement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The measurement refuses to describe a run the document does not.

    The provenance document pins the three tool versions. A machine with
    another version produces different numbers while the document keeps the
    old claim -- so the run says which version it found and stops.
    """
    script = _load(REFRESH, "dexatlas_refresh_versions")
    monkeypatch.setattr(script, "DOCUMENTED_TOOL_VERSIONS", {"jadx": "1.5.2"})
    monkeypatch.setattr(script, "_probe_tool_version", lambda tool: "1.5.3")

    assert script.documented_version_mismatches() == [
        "jadx: documented 1.5.2, this machine has 1.5.3"
    ]


def test_a_version_the_document_names_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pinned versions are not a finding."""
    script = _load(REFRESH, "dexatlas_refresh_versions_ok")
    monkeypatch.setattr(script, "DOCUMENTED_TOOL_VERSIONS", {"jadx": "1.5.2"})
    monkeypatch.setattr(script, "_probe_tool_version", lambda tool: "1.5.2")

    assert script.documented_version_mismatches() == []


def test_an_unprobeable_backend_is_not_a_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A backend that cannot be probed is absence, not a wrong version.

    Whether the machine has the backend at all is the completeness check's
    question; this check only guards the versions of what is there.
    """
    script = _load(REFRESH, "dexatlas_refresh_versions_none")
    monkeypatch.setattr(script, "DOCUMENTED_TOOL_VERSIONS", {"jadx": "1.5.2"})
    monkeypatch.setattr(script, "_probe_tool_version", lambda tool: None)

    assert script.documented_version_mismatches() == []


# ---------------------------------------------------------------------------
# D16 -- the self-check's link check does not normalise a path
# ---------------------------------------------------------------------------


def test_the_selfcheck_link_check_refuses_a_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link that names nothing is broken, on every platform.

    ``Path.resolve()`` on Windows turns ``...`` into the parent directory,
    which exists -- so a placeholder link passed on Windows and failed on
    CI. The check walks the path by name, as a file system does.
    """
    script = _load(SELFCHECK, "dexatlas_selfcheck_links")
    document = tmp_path / "doc.md"
    document.write_text("[a placeholder](...)\n", encoding="utf-8")

    outcomes: list[Any] = []

    class _Report:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    script._check_relative_links(document, _Report(), "TEST.links", "链接")

    assert outcomes[0].state == "fail", "a placeholder link was accepted as a link"
    assert "..." in outcomes[0].detail


def test_the_selfcheck_link_check_accepts_a_real_neighbour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link to a file that is there resolves on every platform."""
    script = _load(SELFCHECK, "dexatlas_selfcheck_links_ok")
    (tmp_path / "other.md").write_text("real\n", encoding="utf-8")
    document = tmp_path / "doc.md"
    document.write_text("[a neighbour](other.md)\n", encoding="utf-8")
    outcomes: list[Any] = []

    class _Report:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script._check_relative_links(document, _Report(), "TEST.links", "链接")

    assert outcomes[0].state == "pass"


# ---------------------------------------------------------------------------
# D35 -- the gate-command check reads the tree's venv, not the machine's PATH
# ---------------------------------------------------------------------------


def test_the_gate_check_answers_from_the_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A global install must not answer for a venv that does not have the tool.

    The venv is the tree's; the PATH is the machine's. A check that took
    either answer made a fresh worktree red on one machine and green on
    another -- and on CI, where PATH holds only the venv, green.
    """
    script = _load(SELFCHECK, "dexatlas_selfcheck_gates")
    venv = tmp_path / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "ruff").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/local/bin/ruff")
    outcomes: list[Any] = []

    class _Report:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script.GATE_COMMANDS = (("G.ruff", "ruff", ["ruff", "check", "."]),)
    script.check_gate_commands(_Report())

    assert outcomes[0].state == "pass"
    assert "venv" in outcomes[0].detail


def test_the_gate_check_reports_missing_from_the_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tool the venv lacks is a failure even when PATH has it."""
    script = _load(SELFCHECK, "dexatlas_selfcheck_gates_missing")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/local/bin/ruff")
    outcomes: list[Any] = []

    class _Report:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script.GATE_COMMANDS = (("G.ruff", "ruff", ["ruff", "check", "."]),)
    script.check_gate_commands(_Report())

    assert outcomes[0].state == "fail"


def test_the_gate_check_calls_a_venv_less_worktree_manual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A worktree without a venv is an unready environment, not a broken tree."""
    script = _load(SELFCHECK, "dexatlas_selfcheck_gates_manual")
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    outcomes: list[Any] = []

    class _Report:
        def add(self, outcome: Any) -> None:
            outcomes.append(outcome)

    script.GATE_COMMANDS = (("G.ruff", "ruff", ["ruff", "check", "."]),)
    script.check_gate_commands(_Report())

    assert outcomes[0].state == "manual"


# ---------------------------------------------------------------------------
# D15/D37 -- a check that cannot encode its report still finishes
# ---------------------------------------------------------------------------


def test_the_selfcheck_writes_its_report_through_a_gbk_console(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The M10 self-check's report survives a console that cannot encode it.

    The redirected ``--json`` output is the common case, and a GBK console
    used to kill the script halfway through -- with the exit code of a crash,
    which is the same 1 a finding gives.
    """
    script = _load(SELFCHECK, "dexatlas_selfcheck_utf8")
    stream = _gbk_stream()
    monkeypatch.setattr(sys, "stdout", stream)

    code = script.main([])

    stream.flush()
    written = stream.buffer.getvalue().decode("utf-8", errors="replace")
    assert "自动化判定" in written
    assert code == 0


def test_the_contract_check_writes_its_report_through_a_gbk_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live contract check's report survives a GBK console too."""
    script = _load(VERIFY_CONTRACTS, "dexatlas_verify_utf8")
    stream = _gbk_stream()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(script, "rest_checks", lambda: None)
    monkeypatch.setattr(script, "mcp_checks", lambda: None)
    monkeypatch.setattr(script, "cli_checks", lambda: None)

    code = script.main()

    stream.flush()
    written = stream.buffer.getvalue().decode("utf-8", errors="replace")
    assert "checks passed" in written
    assert code == 0


class _GbkStream:
    """A stdout that encodes as GBK, the way a Chinese Windows console does."""

    def __init__(self) -> None:
        self.buffer = io.BytesIO()
        self._text = io.TextIOWrapper(self.buffer, encoding="gbk", errors="strict")

    def reconfigure(self, **kwargs: Any) -> None:
        self._text.reconfigure(**kwargs)

    def write(self, text: str) -> int:
        return self._text.write(text)

    def flush(self) -> None:
        self._text.flush()

    @property
    def encoding(self) -> str:
        return self._text.encoding


def _gbk_stream() -> _GbkStream:
    return _GbkStream()


# ---------------------------------------------------------------------------
# D12 -- the contract check does not knock on a fixed port
# ---------------------------------------------------------------------------


def test_the_contract_check_picks_a_free_port() -> None:
    """Two runs do not fight over one port, and a stale server cannot answer.

    A fixed port collided with whatever else was running, and a server left
    over from an earlier run answered the health check meant for this one.
    """
    script = _load(VERIFY_CONTRACTS, "dexatlas_verify_port")
    first = script._free_port()
    second = script._free_port()

    assert first != second


# ---------------------------------------------------------------------------
# D8 -- a project that is not visible yet is not a finished analysis
# ---------------------------------------------------------------------------


def test_wait_for_analysis_reads_a_project_that_appears_later() -> None:
    """The loop keeps waiting while the project row does not exist yet."""
    script = _load(VERIFY_CONTRACTS, "dexatlas_verify_wait")
    answers: list[dict[str, str]] = [{}, {"status": "pending"}, {"status": "completed"}]

    class _Response:
        def __init__(self, payload: dict[str, str]) -> None:
            self._payload = payload

        def json(self) -> dict[str, str]:
            return self._payload

    class _Client:
        def get(self, path: str) -> _Response:
            return _Response(answers.pop(0) if answers else {"status": "completed"})

    assert script.wait_for_analysis(_Client(), "apk_x", attempts=5, pause=0) == {
        "status": "completed"
    }


# ---------------------------------------------------------------------------
# D14 -- a missing MCP SDK is one named failure, not a crash
# ---------------------------------------------------------------------------


def test_a_missing_mcp_sdk_is_named_not_mistaken_for_a_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An environment without the MCP extra is told what is missing.

    The SDK used to be imported at the top of the file, so an environment
    built the way the project's own instructions describe died on the import
    before a single check ran -- and a missing SDK looked like a broken
    contract. The import sits where it is used, and the absence says what to
    install instead of failing an unrelated check.
    """
    script = _load(VERIFY_CONTRACTS, "dexatlas_verify_mcp")
    monkeypatch.setattr(script, "section", lambda title: None)
    import builtins

    real_import = builtins.__import__

    def _refuse_mcp(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mcp.client" or name.startswith("mcp"):
            raise ImportError(f"refused for the test: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _refuse_mcp)

    with pytest.raises(SystemExit, match="uv sync --extra mcp"):
        script.mcp_checks()


# ---------------------------------------------------------------------------
# D10 -- the analysis budget follows the configuration, not the smallest one
# ---------------------------------------------------------------------------


def test_the_analysis_budget_grows_with_the_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """A run that decompiles gets the budget a decompiling run needs.

    The budget was written for a machine without the Java backends; the CI
    runner that did the most work was the one that timed out.
    """
    script = _load(VERIFY_CONTRACTS, "dexatlas_verify_budget")

    class _Client:
        def get(self, path: str) -> Any:
            class _R:
                def json(self) -> dict[str, str]:
                    return {"status": "pending"}

            return _R()

    monkeypatch.setattr(script, "_backends_installed", lambda: False)
    started = script.wait_for_analysis(_Client(), "apk_x", pause=0)
    assert started == {"status": "pending"}  # the loop ran its 240 attempts

    monkeypatch.setattr(script, "_backends_installed", lambda: True)
    script.wait_for_analysis(_Client(), "apk_x", pause=0)
    # A five-times-longer budget is not observable through the stubbed
    # client, so the constant is read directly.
    import inspect

    source = inspect.getsource(script.wait_for_analysis)
    assert "1200" in source


# ---------------------------------------------------------------------------
# D23 -- mypy answers about one platform, not the author's
# ---------------------------------------------------------------------------


def test_mypy_names_one_platform() -> None:
    """The mypy configuration names its platform, so the check is one check.

    mypy's default is the host's platform, and with unreachable warnings on,
    a ``sys.platform`` branch for the other system is dead code on one
    machine and live on another.
    """
    import tomllib

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    assert config["tool"]["mypy"].get("platform") == "linux"


# ---------------------------------------------------------------------------
# D31/D32 -- the setup instructions name the whole environment
# ---------------------------------------------------------------------------


def test_the_setup_command_installs_every_extra() -> None:
    """The project's own instructions install the extras the gates need.

    A reader who followed the old command got an environment without Pillow
    and without the MCP SDK: the measurement ran partial, the contract check
    died on its import, and both failures looked like code problems.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    command_line = next(line for line in text.splitlines() if line.startswith("uv sync"))

    assert "--frozen" in command_line
    assert "--all-extras" in command_line


def test_the_setup_notes_say_where_the_scratch_directory_is() -> None:
    """The scratch note names the directory the code actually uses.

    The note used to name a fixed drive path that only the main checkout's
    layout agrees with; a worktree writes its own ``.scratch`` and the note
    did not say so.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert ".scratch/tmp" in text
    assert "worktree" in text


# ---------------------------------------------------------------------------
# D27 -- the proof harness installs exactly the lockfile's versions
# ---------------------------------------------------------------------------


def test_the_proof_harness_does_not_move_the_lockfile() -> None:
    """``prove-red.sh`` builds its environment from the lockfile.

    A proof that quietly rewrote the lockfile changed the dependency set the
    red run measured, and the red it showed was not the red the fix explains.
    """
    text = (REPO_ROOT / "scripts" / "prove-red.sh").read_text(encoding="utf-8")

    assert "uv sync --frozen" in text


# ---------------------------------------------------------------------------
# D33 -- every CI job keeps its temporary files beside the workspace
# ---------------------------------------------------------------------------


def test_every_ci_job_redirects_its_temporary_directory() -> None:
    """A job that writes to the system temporary directory can run out of it.

    The system drive is nearly full on the machine this project is developed
    on, and the runner's is the workspace -- so every job that runs ``uv``
    gets the same redirection the test suite applies.

    This used to count: "exactly ten jobs redirect their temporary
    directory" and "exactly twelve steps install dependencies".  Adding a
    job turned the test red and the repair was to edit the number, twice in
    two days -- and a number that has to be edited when a correct job is
    added stops describing anything.  The rule is a property now: a job
    that installs with ``uv`` either moves its temporary directory into the
    workspace or says, in the platform-gate inventory, why it does not have
    to.  The inventory and the workflow are compared in both directions, so
    neither can drift from the other quietly.
    """
    module = _load(PLATFORM_GATES, "check_platform_gates")
    inventory = module.load_inventory(PLATFORM_GATES_INVENTORY)
    jobs = module.read_ci_jobs(CI_WORKFLOW)

    offenders: list[str] = []
    for name, job in jobs.items():
        if not job.runs_uv or job.redirects_temp:
            continue
        entry = inventory.ci_jobs.get(name, {})
        claim = entry.get("temp_redirect")
        if claim not in {"exempt", "defect"} or not str(entry.get("reason", "")).strip():
            offenders.append(name)

    assert not offenders, (
        "these CI jobs install with uv and neither redirect their temporary directory "
        f"nor say why they do not have to: {offenders}"
    )


# ---------------------------------------------------------------------------
# D26 -- the fixture fetch script states which files the suite reads
# ---------------------------------------------------------------------------


def test_the_fixture_script_fetches_exactly_what_the_suite_reads() -> None:
    """The fetch list and the suite's skip conditions cannot drift apart.

    A fixture fetched by nobody was a test that skipped everywhere except a
    developer's machine -- the worst outcome for a regression test.
    """
    text = (REPO_ROOT / "scripts" / "fetch-fixtures.sh").read_text(encoding="utf-8")

    assert '"TestActivity.apk"' in text
    assert '"multidex.apk"' in text
