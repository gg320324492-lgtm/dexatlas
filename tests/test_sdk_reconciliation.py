"""The SDK levels are reconciled against the APK's binary manifest.

Apktool decodes a manifest without ``<uses-sdk>`` and writes its own rebuilt
levels into ``apktool.yml`` — numbers that are not what the APK declares
(``examples/wide-app/wide.apk`` says 24; Apktool writes 25). The pipeline
therefore reads the levels back from the binary manifest itself, by Androguard,
and fills only the fields the decoded manifest does not carry. The tests here
cover that reconciliation; the parse of the decoded manifest is covered by
:mod:`tests.test_manifest`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.config.settings import Settings
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import (
    ApkMetadata,
    EvidenceKind,
    EvidenceLevel,
    ManifestInfo,
    Project,
    Provenance,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.tools.androguard.adapter import AndroguardBackend, androguard_available

EXAMPLES = Path(__file__).parent.parent / "examples"
WIDE_APK = EXAMPLES / "wide-app" / "wide.apk"


class _FakeAndroguard:
    """Stands in for the backend the reconciliation asks: the binary-manifest reader.

    What is under test is how the pipeline treats the answer, not how Androguard
    produces it, so the answer is fixed here.
    """

    name = "androguard"

    def __init__(
        self,
        levels: tuple[str | None, str | None],
        *,
        error: ToolError | None = None,
        installed: bool = True,
    ) -> None:
        self._levels = levels
        self._error = error
        self._installed = installed

    def available(self) -> bool:
        return self._installed

    def read_sdk_levels(self, apk: Path) -> tuple[str | None, str | None, ToolError | None]:
        return (*self._levels, self._error)

    def provenance(self, apk_sha256: str, locator: str) -> Provenance:
        return Provenance(tool=self.name, tool_version=None, apk_sha256=apk_sha256, locator=locator)


@pytest.fixture
def analyzer(settings: Settings) -> Analyzer:
    return Analyzer(settings)


@pytest.fixture
def builder(settings: Settings) -> EvidenceBuilder:
    return EvidenceBuilder(
        project_id="reconciliation-tests",
        tool_versions={},
        apk_sha256="0" * 64,
        workspace=settings.workspace,
    )


def _manifest(min_sdk: str | None, target_sdk: str | None) -> ManifestInfo:
    return ManifestInfo(package="com.example.wide", min_sdk=min_sdk, target_sdk=target_sdk)


def _project_of(sha256: str) -> Project:
    return Project(
        id=sha256,
        apk=ApkMetadata(sha256=sha256, size_bytes=1024, path=EXAMPLES / "wide-app" / "wide.apk"),
    )


def test_missing_levels_are_filled_from_the_binary_manifest(
    analyzer: Analyzer, builder: EvidenceBuilder
) -> None:
    """A decoded manifest carries no ``<uses-sdk>``, so both fields come from the APK."""
    analyzer._androguard = _FakeAndroguard(("24", "34"))
    manifest = _manifest(None, None)

    errors = analyzer._reconcile_sdk_levels(_project_of("0" * 64), manifest, builder)

    assert errors == []
    assert manifest.min_sdk == "24"
    assert manifest.target_sdk == "34"
    assert [(r.kind, r.level) for r in builder.items] == [
        (EvidenceKind.DECLARATION, EvidenceLevel.VERIFIED)
    ]
    assert builder.items[0].provenance[0].tool == "androguard"


def test_only_the_missing_side_is_filled(analyzer: Analyzer, builder: EvidenceBuilder) -> None:
    """A field the decoded manifest carries is a transcription of the binary manifest.

    A future or older Apktool that keeps ``<uses-sdk>`` in place is trusted over
    anything else, and the reconciliation fills only what is missing.
    """
    analyzer._androguard = _FakeAndroguard(("21", "34"))
    manifest = _manifest("24", None)

    errors = analyzer._reconcile_sdk_levels(_project_of("0" * 64), manifest, builder)

    assert errors == []
    assert manifest.min_sdk == "24"
    assert manifest.target_sdk == "34"
    assert len(builder.items) == 1
    assert "targetSdk=34" in builder.items[0].summary
    assert "minSdk" not in builder.items[0].summary


def test_levels_present_on_both_sides_leave_no_record(
    analyzer: Analyzer, builder: EvidenceBuilder
) -> None:
    analyzer._androguard = _FakeAndroguard(("24", "34"))
    manifest = _manifest("24", "34")

    errors = analyzer._reconcile_sdk_levels(_project_of("0" * 64), manifest, builder)

    assert errors == []
    assert builder.items == []


def test_read_failure_is_recorded_and_levels_stay_absent(
    analyzer: Analyzer, builder: EvidenceBuilder
) -> None:
    """A manifest that cannot be read is an error value, not an empty reconciliation.

    The fields stay ``None`` — an absence the report can explain — rather than
    falling back to Apktool's ``sdkInfo``, which is not the APK's own answer.
    """
    failure = ToolError(
        tool="androguard",
        code=ToolErrorCode.PARSE_ERROR,
        message="the binary manifest would not parse",
    )
    analyzer._androguard = _FakeAndroguard((None, None), error=failure)
    manifest = _manifest(None, None)

    errors = analyzer._reconcile_sdk_levels(_project_of("0" * 64), manifest, builder)

    assert errors == [failure]
    assert manifest.min_sdk is None
    assert manifest.target_sdk is None


def test_without_androguard_the_levels_stay_absent_and_nothing_is_recorded(
    analyzer: Analyzer, builder: EvidenceBuilder
) -> None:
    """No reader, no value. The missing backend is recorded by the androguard step."""
    analyzer._androguard = _FakeAndroguard(("24", "34"), installed=False)
    manifest = _manifest(None, None)

    errors = analyzer._reconcile_sdk_levels(_project_of("0" * 64), manifest, builder)

    assert errors == []
    assert manifest.min_sdk is None
    assert manifest.target_sdk is None
    assert builder.items == []


@pytest.mark.slow
@pytest.mark.skipif(not androguard_available(), reason="androguard not installed")
def test_sdk_levels_read_from_the_wide_apk(tmp_path: Path) -> None:
    """The binary manifest of the first-party wide sample says 24, not 25.

    The 25 is what Apktool writes into ``apktool.yml`` for this sample, and what
    the analysis used to report. The APK's own bytes — read here by the same
    method the pipeline uses — are the answer.
    """
    backend = AndroguardBackend(Settings(workspace=tmp_path))
    min_sdk, target_sdk, error = backend.read_sdk_levels(WIDE_APK)

    assert error is None
    assert (min_sdk, target_sdk) == ("24", "34")
