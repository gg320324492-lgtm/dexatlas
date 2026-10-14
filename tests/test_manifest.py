"""AndroidManifest.xml parsing.

Includes the hostile-input cases, because the manifest comes from an untrusted APK and
the parser is the most exposed code in the ingestion path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.models import ManifestInfo, ToolError, ToolErrorCode
from dexatlas.tools.apktool.adapter import ApktoolBackend
from tests.conftest import MINIMAL_MANIFEST

#: An XXE / billion-laughs payload. The parser must refuse it, not expand it.
HOSTILE_MANIFEST = """<?xml version="1.0"?>
<!DOCTYPE manifest [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
          package="&lol1;"/>
"""


def _decode_dir(tmp_path: Path, manifest: str) -> Path:
    output = tmp_path / "decoded"
    output.mkdir(parents=True, exist_ok=True)
    (output / "AndroidManifest.xml").write_text(manifest, encoding="utf-8")
    return output


def _parse(
    backend: ApktoolBackend, tmp_path: Path, manifest: str = MINIMAL_MANIFEST
) -> tuple[ManifestInfo | None, ToolError | None]:
    return backend.read_manifest(_decode_dir(tmp_path, manifest))


def test_parses_package_and_versions(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, error = _parse(apktool, tmp_path)

    assert error is None
    assert manifest is not None
    assert manifest.package == "com.example.demo"
    assert manifest.version_code == "42"
    assert manifest.version_name == "1.4.2"
    assert manifest.min_sdk == "24"
    assert manifest.target_sdk == "34"


def test_parses_permissions(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, _ = _parse(apktool, tmp_path)

    assert manifest is not None
    assert [p.name for p in manifest.permissions] == [
        "android.permission.INTERNET",
        "android.permission.ACCESS_FINE_LOCATION",
    ]


def test_parses_all_component_kinds(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, _ = _parse(apktool, tmp_path)

    assert manifest is not None
    kinds = {c.kind for c in manifest.components}
    assert {"application", "activity", "service", "receiver", "provider"} <= kinds


def test_exported_components_are_identified(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, _ = _parse(apktool, tmp_path)

    assert manifest is not None
    exported = {c.name for c in manifest.exported_components}
    assert exported == {"com.example.demo.MainActivity", "com.example.demo.SyncService"}


def test_absent_exported_attribute_is_not_treated_as_exported(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """Android pre-12 required an explicit intent filter to export. Absence is unknown,
    and reporting unknown as exported would overstate the attack surface."""
    manifest, _ = _parse(apktool, tmp_path)

    assert manifest is not None
    receiver = next(c for c in manifest.components if c.kind == "receiver")
    assert receiver.exported is None
    assert receiver not in manifest.exported_components


def test_records_intent_filters(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, _ = _parse(apktool, tmp_path)

    assert manifest is not None
    activity = next(c for c in manifest.components if c.name.endswith("MainActivity"))
    assert any("android.intent.action.MAIN" in f for f in activity.intent_filters)


def test_missing_manifest_is_not_an_error(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, error = apktool.read_manifest(tmp_path / "does-not-exist")

    assert manifest is None
    assert error is None


def test_malformed_manifest_is_recorded_not_raised(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """A manifest that will not parse is recorded, never raised — the analysis of the
    rest of the APK still has value."""
    manifest, error = _parse(apktool, tmp_path, "<manifest><unclosed>")

    assert manifest is None
    assert error is not None
    assert error.code == ToolErrorCode.PARSE_ERROR


def test_rejects_entity_declaration(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, error = _parse(apktool, tmp_path, HOSTILE_MANIFEST)

    assert manifest is None
    assert error is not None
    assert error.code == ToolErrorCode.PARSE_ERROR


@pytest.mark.parametrize(
    "manifest_text",
    [
        "",
        "not xml at all",
        "<manifest>",
        '<manifest package="com.x" ',
    ],
)
def test_junk_never_raises(apktool: ApktoolBackend, tmp_path: Path, manifest_text: str) -> None:
    """Whatever the manifest contains, the parser yields a value: either a parsed
    manifest or a recorded error — never both absent, never an exception."""
    manifest, error = _parse(apktool, tmp_path, manifest_text)

    assert manifest is not None or error is not None
