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


def _decode_dir(tmp_path: Path, manifest: str, apktool_yml: str | None = None) -> Path:
    output = tmp_path / "decoded"
    output.mkdir(parents=True, exist_ok=True)
    (output / "AndroidManifest.xml").write_text(manifest, encoding="utf-8")
    if apktool_yml is not None:
        (output / "apktool.yml").write_text(apktool_yml, encoding="utf-8")
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


# -- apktool.yml relocation --------------------------------------------------

#: Apktool moves these out of the manifest when it decodes. A real decoded APK looks
#: exactly like this — the manifest carries a package and nothing else.
STRIPPED_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
          package="tests.androguard">
    <application android:label="@string/app_name" />
</manifest>
"""

APKTOOL_YML = """version: 3.0.3
apkFileName: TestActivity.apk
usesFramework:
  ids:
  - 1
sdkInfo:
  minSdkVersion: 9
  targetSdkVersion: 16
versionInfo:
  versionCode: 1
  versionName: 1.0
resourcesInfo:
  packageId: 127
"""


def test_version_is_recovered_from_apktool_yml(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """Apktool relocates versionCode/versionName into its own build file, so a
    manifest-only read reports nothing for every real APK."""
    manifest, error = apktool.read_manifest(_decode_dir(tmp_path, STRIPPED_MANIFEST, APKTOOL_YML))

    assert error is None
    assert manifest is not None
    assert manifest.package == "tests.androguard"
    assert manifest.version_code == "1"
    assert manifest.version_name == "1.0"


def test_sdk_levels_are_recovered_from_apktool_yml(apktool: ApktoolBackend, tmp_path: Path) -> None:
    manifest, _ = apktool.read_manifest(_decode_dir(tmp_path, STRIPPED_MANIFEST, APKTOOL_YML))

    assert manifest is not None
    assert manifest.min_sdk == "9"
    assert manifest.target_sdk == "16"


def test_manifest_values_win_over_apktool_yml(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """The merge only fills gaps; it must never overwrite what the manifest says."""
    _parse(apktool, tmp_path, MINIMAL_MANIFEST)
    (tmp_path / "decoded" / "apktool.yml").write_text(
        "versionInfo:\n  versionCode: 999\n  versionName: 9.9.9\n", encoding="utf-8"
    )

    manifest, _ = apktool.read_manifest(tmp_path / "decoded")

    assert manifest is not None
    assert manifest.version_code == "42"
    assert manifest.version_name == "1.4.2"


def test_unparseable_apktool_yml_is_ignored_not_raised(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    manifest, error = apktool.read_manifest(
        _decode_dir(tmp_path, STRIPPED_MANIFEST, "::: not yaml [[[")
    )

    assert error is None
    assert manifest is not None
    assert manifest.package == "tests.androguard"
    assert manifest.version_code is None
