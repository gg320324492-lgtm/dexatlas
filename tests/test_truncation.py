"""An index that stops early has to say so, and a version is asked for once.

The limits in the DEX reader exist so that a hostile or enormous APK cannot
cost an unbounded amount of work. Before the truncation was recorded, a run
that hit a limit produced a clean-looking report: the numbers in the report
matched the database exactly, because the database held the shortened index,
and nothing anywhere said that the APK held more than that.

The second thing this file pins is quieter. Every symbol the backend indexes
carries a provenance record, and every record asks the backend which version
produced it. Asking the package index once per symbol is a run dominated by
bookkeeping — on a large APK the bookkeeping was the whole run.

The DEX here is a stand-in rather than a real APK: the limits are parameters,
so a limit can be reached in a test without a large file. The fake answers the
same calls the real library answers.

The walk those tests drive is the adapter's own, called directly rather than
through the public entry point. The public entry point parses the DEX in a
worker process, and a monkeypatch into the library cannot cross a process
boundary — so the stand-in would never be seen. The worker is checked against
a real APK instead, in ``tests/test_androguard_isolation.py``: that the walk it
runs produces the same index, and that a truncation still says so when it comes
back over the boundary.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import zipfile
from pathlib import Path
from typing import Any

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ClassKind,
    ClassRef,
    MethodRef,
    MethodReference,
    Provenance,
    ToolErrorCode,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.androguard import adapter as androguard_adapter
from dexatlas.tools.androguard.adapter import AndroguardBackend, androguard_available

FAKE_SHA256 = "c" * 64


def _citation(apk: Path, locator: str) -> list[Provenance]:
    """A citation that names where the symbol really is.

    The symbols these tests hand the pipeline are made up, but the citation
    that points at them has to be one the analysis can follow: a locator that
    names another APK, or a string that is not a locator at all, is refused.
    A test that fabricated one was asking the analysis to believe it — and
    the rule that refuses it is the whole point of the citation being
    checked.
    """
    return [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),
            locator=locator,
        )
    ]


def _write_minimal_apk(path: Path) -> Path:
    """A ZIP that passes the APK check and holds no real bytecode.

    The DEX inside is never read: the backend is given the stand-in below. The
    archive only has to look like an Android package to the ingest check.
    """
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", "<manifest/>")
        archive.writestr("classes.dex", b"not a real dex")
    return path


# -- a DEX that is small enough to hit every limit ---------------------------


class _FakeInstruction:
    """One instruction: a ``const-string`` that loads a value."""

    def __init__(self, value: str) -> None:
        self._value = value

    def get_name(self) -> str:
        return "const-string"

    def get_operands(self) -> list[tuple[int, int, str]]:
        return [(0x1, 1, self._value)]

    def get_output(self) -> str:
        return f"const-string v0, {self._value!r}"


class _FakeMethod:
    def __init__(self, name: str, value: str) -> None:
        self._name = name
        self._value = value

    def get_name(self) -> str:
        return self._name

    def get_descriptor(self) -> str:
        return "(Ljava/lang/String;)V"

    def get_access_flags_string(self) -> str:
        return "public"

    def get_code(self) -> object:
        return object()

    def get_instructions(self) -> list[_FakeInstruction]:
        return [_FakeInstruction(self._value)]


class _FakeClass:
    def __init__(self, name: str, methods: int) -> None:
        self._name = name
        self._methods = [
            _FakeMethod(f"m{index}", f"value-{name}-{index}") for index in range(methods)
        ]

    def get_name(self) -> str:
        return self._name

    def get_superclassname(self) -> str:
        return "Ljava/lang/Object;"

    def get_interfaces(self) -> list[str]:
        return []

    def get_access_flags_string(self) -> str:
        return "public"

    def get_fields(self) -> list[Any]:
        return []

    def get_methods(self) -> list[_FakeMethod]:
        return self._methods


class _FakeDex:
    """A DEX with two classes, each holding two methods."""

    def __init__(self, blob: bytes) -> None:
        self._blob = blob

    def get_classes(self) -> list[_FakeClass]:
        return [
            _FakeClass("Lcom/example/First;", 2),
            _FakeClass("Lcom/example/Second;", 2),
        ]

    def get_strings(self) -> list[str]:
        return ["alpha", "beta", "gamma"]


class _FakeApk:
    """The archive: dex files, named the way real ones are."""

    #: How many DEX files the archive holds. A test can raise it to check that
    #: a budget is one budget per APK rather than one per DEX file.
    dex_count = 1

    def __init__(self, path: str) -> None:
        self.path = path

    def get_dex_names(self) -> list[str]:
        return ["classes.dex"] + [f"classes{index}.dex" for index in range(2, self.dex_count + 1)]

    def get_all_dex(self) -> list[bytes]:
        return [b"fake-dex"] * self.dex_count


@pytest.fixture
def fake_dex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the backend read the stand-in DEX instead of a real one."""
    monkeypatch.setattr("androguard.core.apk.APK", _FakeApk)
    monkeypatch.setattr("androguard.core.dex.DEX", _FakeDex)


@pytest.fixture
def backend(settings: Settings) -> AndroguardBackend:
    return AndroguardBackend(settings)


# -- the limits say so --------------------------------------------------------


def test_the_method_limit_says_the_index_is_incomplete(
    backend: AndroguardBackend, fake_dex: None, tmp_path: Path
) -> None:
    """Two methods are indexed; the other two are not, and the error says how many."""
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    *_, error = backend._extract_symbols(apk, FAKE_SHA256, method_limit=2)

    assert error is not None
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "method limit 2 reached" in error.message
    assert "the index is incomplete" in error.message
    assert "2 methods in this file were not indexed" in error.message


def test_the_instruction_limit_says_the_index_is_incomplete(
    backend: AndroguardBackend, fake_dex: None, tmp_path: Path
) -> None:
    """The instruction limit stops the walk too, and it says what it cost."""
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    *_, error = backend._extract_symbols(apk, FAKE_SHA256, instruction_limit=0)

    assert error is not None
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "instruction limit 0 reached" in error.message
    assert "the index is incomplete" in error.message
    # The dex holds two classes of two methods each, and the budget is spent
    # before the first of them, so all four are missing.
    assert "4 methods in this file were not indexed" in error.message


def test_the_string_limit_says_the_index_is_incomplete(
    backend: AndroguardBackend, fake_dex: None, tmp_path: Path
) -> None:
    """A truncated string index is an index that cannot be searched for
    everything the APK holds."""
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    *_, error = backend._extract_symbols(apk, FAKE_SHA256, string_limit=1)

    assert error is not None
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "string limit 1 reached" in error.message
    assert "the index is incomplete" in error.message
    # The pool holds three entries and one was read before the limit.
    assert "2 entries of this DEX file's string pool were not indexed" in error.message


# -- one budget per analysis, not one per DEX file ----------------------------


def test_the_string_budget_is_one_per_apk_not_one_per_dex(
    backend: AndroguardBackend, fake_dex: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Four DEX files must not mean four times the allowance.

    The limits cap the work of one analysis. A budget that resets for every
    DEX file hands a multi-dex APK N times the allowance, which is exactly
    backwards: the bigger the APK, the more it needs a ceiling.
    """
    monkeypatch.setattr(_FakeApk, "dex_count", 4)
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    *_, strings, error = backend._extract_symbols(apk, FAKE_SHA256, string_limit=3)

    assert len(strings) == 3, "each DEX file got a budget of its own"
    assert error is not None
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "string limit 3 reached" in error.message


def test_the_instruction_budget_is_one_per_apk_not_one_per_dex(
    backend: AndroguardBackend, fake_dex: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The bytecode budget is spent once, and the walk does not resume in the
    next DEX file."""
    monkeypatch.setattr(_FakeApk, "dex_count", 4)
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    classes, methods, _fields, _refs, _strings, error = backend._extract_symbols(
        apk, FAKE_SHA256, instruction_limit=2
    )

    # The first DEX file spends the budget on its first two methods; the other
    # three files are not walked at all, so they contribute nothing.
    assert len(methods) == 2, "the instruction budget was spent more than once"
    assert len(classes) == 2, "a DEX file after the budget was spent was walked anyway"
    assert error is not None
    assert error.code is ToolErrorCode.OUTPUT_TRUNCATED
    assert "instruction limit 2 reached" in error.message


def test_a_budget_that_is_spent_is_not_reported_again_per_dex(
    backend: AndroguardBackend, fake_dex: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One limit reached four times is one problem, not four."""
    monkeypatch.setattr(_FakeApk, "dex_count", 4)
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    *_, error = backend._extract_symbols(apk, FAKE_SHA256, string_limit=1)

    assert error is not None
    assert error.message.count("string limit") == 1


def test_a_run_that_hit_no_limit_reports_no_truncation(
    backend: AndroguardBackend, fake_dex: None, tmp_path: Path
) -> None:
    """The limits are limits, not a permanent condition."""
    apk = _write_minimal_apk(tmp_path / "fake.apk")

    classes, methods, _fields, _refs, strings, error = backend._extract_symbols(apk, FAKE_SHA256)

    assert error is None
    assert len(classes) == 2
    assert len(methods) == 4
    assert [s.value for s in strings] == ["alpha", "beta", "gamma"]


# -- the pipeline keeps the evidence, and records the gap --------------------


def test_a_truncated_index_still_gives_its_evidence(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A shortened index is incomplete, not wrong.

    The rows that were written were read out of the bytecode and they hold, so
    the conclusions drawn from them hold too. The gap is recorded alongside
    them rather than instead of them.
    """
    analyzer = Analyzer(settings)
    apk = _write_minimal_apk(tmp_path / "fake.apk")
    classes = [
        ClassRef(
            name="com.example.First",
            kind=ClassKind.CLASS,
            provenance=_citation(apk, "androguard:classes.dex#com.example.First"),
        )
    ]
    methods = [
        MethodRef(
            class_name="com.example.First",
            name="m0",
            descriptor="()V",
            provenance=_citation(
                apk, "androguard:classes.dex#com.example.First#com.example.First.m0()V"
            ),
        )
    ]
    references = [
        MethodReference(
            caller="com.example.First.m0()V",
            callee="com.example.First.m0()V",
            provenance=_citation(
                apk,
                "androguard:classes.dex#com.example.First.m0()V->com.example.First.m0()V",
            ),
        )
    ]
    truncation = androguard_adapter.ToolError(
        tool="androguard",
        code=ToolErrorCode.OUTPUT_TRUNCATED,
        message="method limit 1 reached: the index is incomplete — 1 methods were not indexed",
    )

    def fake_extract(*args: Any, **kwargs: Any):
        return classes, methods, [], references, [], truncation

    monkeypatch.setattr(analyzer._androguard, "extract", fake_extract)

    result = analyzer.analyze(apk, include_jadx=False, include_apktool=False)

    assert result.project.errors, "the truncation was not recorded on the project"
    assert result.project.errors[0].code is ToolErrorCode.OUTPUT_TRUNCATED
    summaries = " ".join(item.summary for item in result.evidence)
    assert "the index is incomplete" in summaries
    # The cross-reference evidence survives a truncation.
    assert any("is called from" in item.summary for item in result.evidence)


# -- the version is asked for once -------------------------------------------


def test_the_version_is_asked_for_once(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every symbol carries a provenance record, and every record asks for the
    version. The answer is looked up once and remembered."""
    asked: list[str] = []

    def fake_version(name: str) -> str:
        asked.append(name)
        return "4.1.3"

    monkeypatch.setattr(androguard_adapter, "androguard_available", lambda: True)
    monkeypatch.setattr(importlib.metadata, "version", fake_version)

    backend = AndroguardBackend(settings)
    assert backend.version() == "4.1.3"

    def exploding_version(name: str) -> str:
        raise AssertionError("the installed distribution was scanned again")

    monkeypatch.setattr(importlib.metadata, "version", exploding_version)

    assert backend.version() == "4.1.3"
    assert asked == ["androguard"], "the version was looked up more than once"


def test_the_version_is_asked_for_once_for_the_whole_index(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every symbol carries a provenance record, and every record names the
    version — so the version is asked for once, not once per symbol.

    A version cannot change while an analysis runs, and the backend that has
    to consult the package index to answer was paying for that question on
    every symbol it indexed.
    """
    asked = 0
    backend = AndroguardBackend(settings)

    def counting() -> str | None:
        nonlocal asked
        asked += 1
        return "4.1.3"

    monkeypatch.setattr(backend, "version", counting)

    for index in range(10):
        record = backend.provenance("a" * 64, f"androguard:classes.dex#C{index}")
        assert record.tool_version == "4.1.3"

    assert asked == 1, f"the version was asked for {asked} times for ten symbols"


def test_a_backend_without_androguard_still_reports_no_version(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caching the answer does not change what the answer is."""
    monkeypatch.setattr(androguard_adapter, "androguard_available", lambda: False)

    backend = AndroguardBackend(settings)

    assert backend.version() is None
    assert backend.version() is None


@pytest.mark.skipif(not androguard_available(), reason="androguard not installed")
def test_the_real_version_is_the_installed_one(settings: Settings) -> None:
    """The cached answer is the installed distribution's, not a constant."""
    backend = AndroguardBackend(settings)

    assert backend.version() == importlib.metadata.version("androguard")
