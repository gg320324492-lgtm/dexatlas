"""The version fields Apktool rebuilds agree with the APK's own bytes.

Apktool writes SDK levels into ``apktool.yml`` that are not the levels in the
binary manifest, which is why the pipeline reads those from the APK instead.
``versionCode`` and ``versionName`` come from the same build file, so they need
their own check rather than an assumption that the whole file is trustworthy.

The authority here is :mod:`benchmarks.axmlreader`, an independent reader of
the binary XML inside each APK. These tests compare it with the checked-in
sources, the checked-in ``apktool.yml``, a real Apktool decode, and the
``ManifestInfo`` the adapter returns. A future Apktool that starts rewriting
a version field will turn one of these tests red.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element

import pytest
import yaml
from benchmarks.axmlreader import read_manifest
from defusedxml.ElementTree import parse as safe_parse

from dexatlas.config.settings import Settings
from dexatlas.tools.apktool.adapter import ApktoolBackend

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
ANDROID = "{http://schemas.android.com/apk/res/android}"

SAMPLE_APKS = (
    ("demo-app", "demo.apk"),
    ("multidex-app", "multidex.apk"),
    ("obfuscated-app", "obfuscated.apk"),
    ("strings-app", "strings.apk"),
    ("wide-app", "wide.apk"),
)

Versions = tuple[str | None, str | None]


def _text(value: object) -> str | None:
    """Normalise the integer/string spellings without turning absence into text."""
    return None if value is None else str(value)


def _apk_versions(apk: Path) -> Versions:
    """The values in the binary manifest, read independently of DexAtlas."""
    root = read_manifest(apk).root
    return _text(root.value("versionCode")), _text(root.value("versionName"))


def _xml_versions(path: Path) -> Versions:
    """The version attributes of a decoded or source manifest, if it has them."""
    root: Element = safe_parse(path).getroot()
    return _text(root.get(ANDROID + "versionCode")), _text(root.get(ANDROID + "versionName"))


def _yml_versions(path: Path) -> Versions:
    """The two values Apktool writes into its build file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None, None
    info = data.get("versionInfo")
    if not isinstance(info, dict):
        return None, None
    return _text(info.get("versionCode")), _text(info.get("versionName"))


@pytest.mark.parametrize(("sample", "apk_name"), SAMPLE_APKS)
def test_committed_version_fields_agree_with_apk_bytes(sample: str, apk_name: str) -> None:
    """The checked-in source XML and apktool.yml are both faithful to the APK."""
    directory = EXAMPLES / sample
    from_apk = _apk_versions(directory / apk_name)
    assert from_apk != (None, None), "the binary manifest must actually declare a version"
    assert _xml_versions(directory / "AndroidManifest.xml") == from_apk
    assert _yml_versions(directory / "apktool.yml") == from_apk


@pytest.mark.slow
@pytest.mark.skipif(ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed")
@pytest.mark.parametrize(("sample", "apk_name"), SAMPLE_APKS)
def test_decoded_version_fields_agree_with_apk_bytes(
    tmp_path: Path, sample: str, apk_name: str
) -> None:
    """A real Apktool decode, and the adapter's answer, agree with the APK's bytes.

    Apktool 2.11.1 strips both version attributes from some decoded manifests
    and keeps them in others; either form is fine as long as neither value has
    changed. The pipeline's gap-fill must produce the binary manifest's values
    in both cases.
    """
    apk = EXAMPLES / sample / apk_name
    backend = ApktoolBackend(Settings(workspace=tmp_path / "workspace"))
    output_dir = tmp_path / sample
    outcome = backend.decode(apk, output_dir)
    assert outcome.error is None and outcome.ok, (
        f"apktool could not decode {apk.name}: {outcome.error or outcome.stderr}"
    )

    from_apk = _apk_versions(apk)
    assert from_apk != (None, None)
    assert _yml_versions(output_dir / "apktool.yml") == from_apk

    decoded_xml = _xml_versions(output_dir / "AndroidManifest.xml")
    for present, expected in zip(decoded_xml, from_apk, strict=True):
        assert present is None or present == expected

    info, error = backend.read_manifest(output_dir)
    assert error is None
    assert info is not None
    assert (info.version_code, info.version_name) == from_apk
