"""The checkers have to finish on a console that cannot encode their output.

A finding quotes the line it is about, and that line may hold a character the
console cannot write: the execution report marks its findings with 🔴. A
console that cannot write it — GBK, cp1252 — would kill the script halfway
through its report, and the exit code it managed to give would be the one a
crash gives: 1, the same as the one a real finding gives. In the base mode
that exit code is wrong: the run has no new findings and says so.

The output is therefore UTF-8, and a character that cannot be written is
replaced rather than raised. These tests are the regression guard for that.
Pytest's own capture is always UTF-8, so the failure only ever shows up on a
console that is not — which is why it has to be simulated here.
"""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parent.parent
VERSION_SCRIPT = REPO_ROOT / "scripts" / "check-version-claims.py"
CITATION_SCRIPT = REPO_ROOT / "scripts" / "check-doc-citations.py"


def _has_release_tags() -> bool:
    """Whether this clone can answer questions about the project's releases.

    A clone without tags cannot: the checker refuses to report "nothing is
    wrong" from one, because a green check that checked nothing is the worst
    kind of answer. That refusal is right, so a test that needs the checker's
    answer skips here rather than failing — a source archive has no tags, and
    a failure there says nothing about the code.

    CI checks out with the tags, so the test runs there.
    """
    result = subprocess.run(
        ["git", "tag", "--list"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _load(path: Path, name: str) -> ModuleType:
    """Load a script as a module, the way the suite loads the other scripts."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The module has to be in ``sys.modules`` before it runs: its annotations
    # resolve through it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _checker() -> ModuleType:
    return _load(VERSION_SCRIPT, "dexatlas_version_claims")


def _citation_checker() -> ModuleType:
    return _load(CITATION_SCRIPT, "dexatlas_doc_citations")


def _gbk_console() -> io.TextIOWrapper:
    """A console that cannot write the character the report holds."""
    return io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")


def _written(stream: io.TextIOWrapper) -> str:
    """What the console was given, read back as the UTF-8 it now writes."""
    stream.flush()
    return stream.buffer.getvalue().decode("utf-8")


def test_the_output_survives_a_console_that_cannot_encode_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The output is UTF-8, and a character that cannot be written is replaced."""
    checker = _checker()
    stream = _gbk_console()
    monkeypatch.setattr(sys, "stdout", stream)

    checker.use_utf8_output()
    print("🔴 a line with a character GBK cannot write", file=stream)

    written = _written(stream)
    assert "🔴" in written


def test_the_version_claim_checker_answers_the_same_on_any_console(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A checker that behaves differently on another machine is worse than none.

    The exit code is the checker's answer, and it must not depend on what the
    console can encode.
    """
    if not _has_release_tags():
        pytest.skip("this clone has no tags, so the release state cannot be checked")

    checker = _checker()

    with_utf8 = checker.main(["--base", "HEAD"])
    capsys.readouterr()

    stream = _gbk_console()
    monkeypatch.setattr(sys, "stdout", stream)
    with_gbk = checker.main(["--base", "HEAD"])
    written = _written(stream)

    assert with_gbk == with_utf8
    assert "findings:" in written
    assert "Traceback" not in written


def test_the_citation_checker_finishes_on_a_console_that_cannot_encode_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The citation checker quotes the line it drifted in, and that line may
    hold a character the console cannot write.

    The citation it is given here drifts, and the line it drifted in carries
    the character — so the checker has to print it without dying.
    """
    checker = _citation_checker()
    document = tmp_path / "drifted.md"
    document.write_text(
        "The `Analyzer` class is at `src/dexatlas/core/pipeline.py:1-2` 🔴\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "DOCS", [document])

    stream = _gbk_console()
    monkeypatch.setattr(sys, "stdout", stream)
    assert checker.main() == 0

    written = _written(stream)
    assert "drifted: 1" in written
    assert "🔴" in written
    assert "Traceback" not in written
