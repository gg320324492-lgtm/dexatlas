"""Apktool backend — AndroidManifest.xml, resources and Smali.

Apktool is the Smali fallback. When JADX cannot reconstruct a method, the bytecode is
still there and still readable — this backend is what keeps a finding verifiable instead
of dropping it when decompilation fails.

The decoded manifest comes from an untrusted APK, so it is parsed with ``defusedxml``,
which refuses entity declarations and external references. A plain XML parser here is a
denial-of-service waiting to happen.
"""

from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

import yaml
from defusedxml.ElementTree import parse as safe_parse

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ManifestComponent,
    ManifestInfo,
    ManifestPermission,
    ToolError,
    ToolErrorCode,
)
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome, which_or_none

logger = logging.getLogger(__name__)

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ANDROID = f"{{{ANDROID_NS}}}"

_COMPONENT_TAGS = ("activity", "activity-alias", "service", "receiver", "provider")


class ApktoolBackend(Backend):
    """Wraps the ``apktool`` decoder."""

    name = "apktool"
    path_env_var = "DEXATLAS_APKTOOL_JAR"
    install_hint = (
        "Install Apktool and point DEXATLAS_APKTOOL_JAR at its jar, or put "
        "apktool on PATH: https://github.com/iBotPeaches/Apktool/releases"
    )

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._version: str | None = None
        self._version_probed = False

    def resolve(self) -> Path | None:
        return which_or_none(
            [self._settings.apktool_jar], names=("apktool", "apktool.jar", "apktool.bat")
        )

    def _argv(self, *args: str) -> list[str]:
        """Build an apktool invocation for whichever form is installed."""
        jar = self.resolve()
        if jar is None:
            return []
        if jar.suffix == ".jar":
            return ["java", "-jar", str(jar), *args]
        return [str(jar), *args]

    def version(self) -> str | None:
        if self._version_probed:
            return self._version
        self._version_probed = True
        argv = self._argv("--version")
        if not argv:
            return None
        outcome = self.run(ToolInvocation(argv=argv, timeout=120))
        first_line = outcome.stdout.strip().splitlines()
        self._version = first_line[0].strip() if outcome.ok and first_line else None
        return self._version

    # -- decoding ----------------------------------------------------------

    def decode(self, apk: Path, output_dir: Path) -> ToolOutcome:
        """Decode an APK into ``output_dir``: manifest, resources and Smali.

        Sources are decoded deliberately. Smali is the fallback for any method JADX
        cannot decompile, so skipping it would defeat the point of this backend.
        """
        argv = self._argv("d", "-f", "-o", str(output_dir), str(apk))
        if not argv:
            return ToolOutcome(
                returncode=-1,
                stdout="",
                stderr="",
                duration_seconds=0.0,
                error=self.missing_error(),
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        return self.run(ToolInvocation(argv=argv, timeout=self._settings.tool_timeout_seconds))

    # -- manifest ----------------------------------------------------------

    def read_manifest(self, output_dir: Path) -> tuple[ManifestInfo | None, ToolError | None]:
        """Parse the decoded ``AndroidManifest.xml``.

        Uses ``defusedxml``, which refuses entity declarations, DTDs and external
        references. A manifest that will not parse is an error worth recording — it
        usually means a packed or obfuscated APK — but never a reason to stop.
        """
        manifest_path = output_dir / "AndroidManifest.xml"
        if not manifest_path.is_file():
            return None, None

        try:
            root = safe_parse(manifest_path).getroot()
        except ParseError as exc:
            return None, ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"AndroidManifest.xml is not well-formed XML: {exc}",
                detail=str(manifest_path),
            )
        except OSError as exc:
            return None, ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"could not read AndroidManifest.xml: {exc}",
            )
        except ValueError as exc:
            return None, ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"AndroidManifest.xml was rejected as unsafe XML: {exc}",
            )

        if root is None:
            return None, ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message="AndroidManifest.xml has no root element",
                detail=str(manifest_path),
            )

        info = ManifestInfo(
            package=root.get("package"),
            shared_user_id=root.get(ANDROID + "sharedUserId"),
            # versionCode/versionName are declared on <manifest>, not <application>.
            version_code=root.get(ANDROID + "versionCode"),
            version_name=root.get(ANDROID + "versionName"),
        )

        uses_sdk = root.find("uses-sdk")
        if uses_sdk is not None:
            info.min_sdk = uses_sdk.get(ANDROID + "minSdkVersion")
            info.target_sdk = uses_sdk.get(ANDROID + "targetSdkVersion")

        # Apktool moves the version and SDK attributes out of the manifest and into
        # apktool.yml when it decodes. A manifest-only read therefore reports "—" for
        # every APK, which is both unhelpful and wrong. Fill the gaps from there.
        _merge_build_metadata(info, output_dir / "apktool.yml")

        for element in root.findall("uses-permission") + root.findall("uses-permission-sdk-23"):
            name = element.get(ANDROID + "name")
            if name:
                info.permissions.append(
                    ManifestPermission(
                        name=name, protection_level=element.get(ANDROID + "protectionLevel")
                    )
                )

        application = root.find("application")
        if application is not None:
            info.components.append(
                ManifestComponent(
                    kind="application",
                    name=application.get(ANDROID + "name") or info.package or "",
                    permission=application.get(ANDROID + "permission"),
                )
            )
            for tag in _COMPONENT_TAGS:
                for element in application.findall(tag):
                    name = element.get(ANDROID + "name")
                    if not name:
                        continue
                    info.components.append(
                        ManifestComponent(
                            kind=tag,
                            name=name,
                            exported=_parse_bool(element.get(ANDROID + "exported")),
                            permission=element.get(ANDROID + "permission"),
                            intent_filters=[
                                _describe_filter(f) for f in element.findall("intent-filter")
                            ],
                        )
                    )

        return info, None

    # -- smali -------------------------------------------------------------

    def smali_path(self, class_name: str, output_dir: Path) -> Path | None:
        """Locate a class's Smali file. ``com.foo.Bar`` → ``smali/com/foo/Bar.smali``."""
        smali_root = output_dir / "smali"
        if not smali_root.is_dir():
            return None
        relative = Path(*class_name.split(".")).with_suffix(".smali")
        for root in sorted(smali_root.glob("smali*")):
            candidate = root / relative
            if candidate.is_file():
                return candidate
        return None

    def read_smali(self, class_name: str, output_dir: Path) -> str | None:
        path = self.smali_path(class_name, output_dir)
        if path is None:
            return None
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() == "true"


def _merge_build_metadata(info: ManifestInfo, apktool_yml: Path) -> None:
    """Fill in version and SDK values that Apktool relocated to ``apktool.yml``.

    Apktool's decoded manifest omits ``versionCode``, ``versionName`` and the
    ``uses-sdk`` block, keeping them in its own build file instead. Values already
    present in the manifest win, so this only fills gaps.
    """
    if not apktool_yml.is_file():
        return

    try:
        data = yaml.safe_load(apktool_yml.read_text(encoding="utf-8", errors="replace"))
    except (OSError, yaml.YAMLError) as exc:
        logger.debug("apktool: could not read %s: %s", apktool_yml, exc)
        return

    if not isinstance(data, dict):
        return

    version = data.get("versionInfo")
    if isinstance(version, dict):
        if info.version_code is None:
            info.version_code = _as_text(version.get("versionCode"))
        if info.version_name is None:
            info.version_name = _as_text(version.get("versionName"))

    sdk = data.get("sdkInfo")
    if isinstance(sdk, dict):
        if info.min_sdk is None:
            info.min_sdk = _as_text(sdk.get("minSdkVersion"))
        if info.target_sdk is None:
            info.target_sdk = _as_text(sdk.get("targetSdkVersion"))


def _as_text(value: object) -> str | None:
    """Apktool writes some of these as ints and some as strings depending on version."""
    if value is None:
        return None
    return str(value)


def _describe_filter(element: Element) -> str:
    """Compact one-line description of an intent-filter, for the manifest summary."""
    actions = [a.get(ANDROID + "name", "") for a in element.findall("action")]
    categories = [c.get(ANDROID + "name", "") for c in element.findall("category")]
    parts: list[str] = []
    if actions:
        parts.append("actions=" + ",".join(filter(None, actions)))
    if categories:
        parts.append("categories=" + ",".join(filter(None, categories)))
    return "; ".join(parts)


__all__ = ["ANDROID_NS", "ApktoolBackend"]
