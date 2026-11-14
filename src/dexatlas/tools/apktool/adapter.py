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
from xml.parsers import expat

import yaml
from defusedxml.ElementTree import parse as safe_parse

from dexatlas.config.settings import Settings
from dexatlas.core.models import (
    ManifestComponent,
    ManifestInfo,
    ManifestPermission,
    ResourceKind,
    ResourceString,
    ToolError,
    ToolErrorCode,
)
from dexatlas.core.paths import class_to_relative_path, is_inside
from dexatlas.tools.base import Backend, ToolInvocation, ToolOutcome, which_or_none

logger = logging.getLogger(__name__)

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ANDROID = f"{{{ANDROID_NS}}}"

_COMPONENT_TAGS = ("activity", "activity-alias", "service", "receiver", "provider")

#: Resource files that will not parse are recorded as errors. A hostile APK can
#: carry a resource table no parser can read, and a reader has to be able to
#: tell "the resource table was empty" from "the resource table was unreadable".
#: The number of files is capped so one broken APK cannot fill the report with
#: thousands of near-identical rows.
MAX_RESOURCE_ERRORS = 10

#: The resource elements that hold text a person reads. The other elements in a
#: values file — colours, dimensions, booleans, integers, styles — describe
#: how the app looks, not what it says, and a "string index" full of them would
#: answer no question a reader asked.
_TEXT_ELEMENTS = ("string", "string-array", "plurals")

#: The ``res/`` directories whose XML carries text *written into it* rather
#: than declared as a resource. A layout shows text on screen; a menu names
#: its actions; the ``xml/`` directory holds preferences and shortcuts whose
#: titles a user reads. A drawable is a picture, ``raw/`` is binary, and
#: neither says anything.
_TEXT_DIRECTORIES = ("layout", "menu", "xml")

#: The ``android:`` attributes whose value is text a person reads. Every other
#: attribute — a width, an id, a gravity — describes the view, not the words
#: on it, and indexing those would fill the string index with layout noise.
_TEXT_ATTRIBUTES = ("text", "hint", "contentDescription", "title", "summary", "label")

#: The XML namespace the platform's attributes live in, as ElementTree spells
#: it. A layout binds the prefix ``android`` to this namespace, but nothing
#: requires that spelling — what makes an attribute an Android one is the
#: namespace, not the prefix.
_ANDROID_NAMESPACE = "{http://schemas.android.com/apk/res/android}"


def source_locator(output_dir: Path, path: Path) -> str:
    """The locator for a file inside Apktool's output tree.

    The path is relative to the directory Apktool wrote into, for the same
    reason JADX's is: an absolute path names the machine that ran the analysis
    rather than the analysis itself, and a reader on another machine cannot
    follow it. The same file, at the same place inside the tree, is what any
    run of the same Apktool over the same APK produces.
    """
    return f"apktool:{path.relative_to(output_dir).as_posix()}"


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

        # The name of the file, not the path to it. The path is the server's
        # filesystem, and an error message is published to whoever asked for
        # the analysis.
        relative = _relative_to(manifest_path, output_dir)

        try:
            root = safe_parse(manifest_path).getroot()
        except ParseError as exc:
            return None, ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"AndroidManifest.xml is not well-formed XML: {exc}",
                detail=relative,
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
                detail=relative,
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

        # Apktool 2.11.1 strips the version attributes from some decoded manifests
        # and keeps them in others. It writes both into apktool.yml; unlike its
        # rebuilt sdkInfo, those two values agree with the APK's binary manifest in
        # all five first-party samples (tests/test_version_fields.py checks both the
        # checked-in and freshly decoded files). Fill only the gaps from that file.
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

    # -- resources ---------------------------------------------------------

    def read_resources(
        self, output_dir: Path, apk_sha256: str
    ) -> tuple[list[ResourceString], list[ToolError]]:
        """Read the text resources Apktool decoded into ``res/``.

        The resource table comes out of an untrusted APK, so the XML is parsed
        with ``defusedxml`` for the same reason the manifest is: a plain parser
        would honour entity declarations and external references, which is a
        denial-of-service waiting to happen.

        The ``values*`` directories are read for the text they *declare* —
        strings, string arrays, plurals. The layout, menu and xml directories
        are read for the text *written into them* — ``android:text`` and its
        siblings, which no resource table names but a reader still meets on
        the screen. A drawable is a picture and is not read. See the module
        docstring of :mod:`dexatlas.core.models` for what a row here means.

        A file that will not parse is recorded as an error and the rest are
        still read: one broken file in a hostile APK must not cost the whole
        resource table.
        """
        res_dir = output_dir / "res"
        if not res_dir.is_dir():
            return [], []

        found: list[ResourceString] = []
        errors: list[ToolError] = []
        for values_dir in sorted(p for p in res_dir.glob("values*") if p.is_dir()):
            qualifier = _values_qualifier(values_dir.name)
            for xml_file in sorted(values_dir.glob("*.xml")):
                rows, error = self._read_resource_file(xml_file, output_dir, apk_sha256, qualifier)
                found.extend(rows)
                if error is not None:
                    errors.append(error)
        for pattern in _TEXT_DIRECTORIES:
            for text_dir in sorted(p for p in res_dir.glob(f"{pattern}*") if p.is_dir()):
                for xml_file in sorted(text_dir.glob("*.xml")):
                    rows, error = self._read_layout_file(xml_file, output_dir, apk_sha256)
                    found.extend(rows)
                    if error is not None:
                        errors.append(error)

        if len(errors) > MAX_RESOURCE_ERRORS:
            hidden = len(errors) - MAX_RESOURCE_ERRORS
            errors = errors[:MAX_RESOURCE_ERRORS]
            errors.append(
                ToolError(
                    tool=self.name,
                    code=ToolErrorCode.PARSE_ERROR,
                    message=f"{hidden} further resource file(s) could not be parsed",
                )
            )
        return found, errors

    def _read_resource_file(
        self,
        path: Path,
        output_dir: Path,
        apk_sha256: str,
        qualifier: str | None,
    ) -> tuple[list[ResourceString], ToolError | None]:
        """Read one values file: the text it declares, and where it was declared."""
        relative = _relative_to(path, output_dir)
        try:
            root = safe_parse(path).getroot()
        except ParseError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} is not well-formed XML: {exc}",
                detail=relative,
            )
        except OSError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"could not read {relative}: {exc}",
                detail=relative,
            )
        except ValueError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} was rejected as unsafe XML: {exc}",
                detail=relative,
            )

        if root is None:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} has no root element",
                detail=relative,
            )

        provenance = [self.provenance(apk_sha256, source_locator(output_dir, path))]
        rows: list[ResourceString] = []
        for element in root:
            tag = _local_name(element.tag)
            name = element.get("name")
            if not name or tag not in _TEXT_ELEMENTS:
                continue

            if tag == "string":
                rows.append(
                    ResourceString(
                        name=name,
                        value=_text_of(element),
                        kind=ResourceKind.STRING,
                        qualifier=qualifier,
                        file=relative,
                        provenance=provenance,
                    )
                )
                continue

            kind = ResourceKind.STRING_ARRAY if tag == "string-array" else ResourceKind.PLURAL
            for position, item in enumerate(element):
                if _local_name(item.tag) != "item":
                    continue
                rows.append(
                    ResourceString(
                        name=name,
                        value=_text_of(item),
                        kind=kind,
                        quantity=item.get("quantity"),
                        position=position,
                        qualifier=qualifier,
                        file=relative,
                        provenance=provenance,
                    )
                )
        return rows, None

    def _read_layout_file(
        self,
        path: Path,
        output_dir: Path,
        apk_sha256: str,
    ) -> tuple[list[ResourceString], ToolError | None]:
        """Read one layout, menu or xml file: the text written into it.

        The values files are *declarations* — each string has a name the
        resource table knows. A layout carries literals instead: whatever was
        typed into ``android:text`` when the screen was written. Those have
        no name, so the row is named after the element that carries the
        attribute, and the locator points at the element's line so a reader
        lands on the view the words are written on.
        """
        relative = _relative_to(path, output_dir)
        try:
            root = safe_parse(path).getroot()
        except ParseError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} is not well-formed XML: {exc}",
                detail=relative,
            )
        except OSError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"could not read {relative}: {exc}",
                detail=relative,
            )
        except ValueError as exc:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} was rejected as unsafe XML: {exc}",
                detail=relative,
            )

        if root is None:
            return [], ToolError(
                tool=self.name,
                code=ToolErrorCode.PARSE_ERROR,
                message=f"{relative} has no root element",
                detail=relative,
            )

        # The safe parse above has already refused anything with a DTD or an
        # entity in it, so this second pass sees only the XML that survived.
        # It can still fail on a document that is well-formed under one
        # parser and not under another, and a failure there costs the line
        # numbers, not the text: the rows are written without positions.
        # Both walks go in document order, so the nth element of the tree is
        # the nth element expat announced.
        lines = _element_lines(path)

        qualifier = _layout_qualifier(path.parent.name)
        rows: list[ResourceString] = []
        for order, element in enumerate(root.iter(), start=1):
            tag = _local_name(element.tag)
            for attribute in _TEXT_ATTRIBUTES:
                value = element.get(f"{_ANDROID_NAMESPACE}{attribute}")
                if not value:
                    continue
                line = lines.get(order, 0)
                locator = source_locator(output_dir, path)
                if line:
                    locator = f"{locator}#line={line};{tag}"
                rows.append(
                    ResourceString(
                        name=tag,
                        value=value,
                        kind=ResourceKind.LAYOUT_TEXT,
                        position=line,
                        attribute=attribute,
                        qualifier=qualifier,
                        file=relative,
                        provenance=[self.provenance(apk_sha256, locator)],
                    )
                )
        return rows, None

    # -- smali -------------------------------------------------------------

    def smali_path(self, class_name: str, output_dir: Path) -> Path | None:
        """Locate a class's Smali file. ``com.foo.Bar`` → ``smali/com/foo/Bar.smali``.

        Apktool writes one directory per DEX, named after it: ``classes.dex`` becomes
        ``smali/``, ``classes2.dex`` becomes ``smali_classes2/``, and so on. They are
        siblings under the output directory, not nested — the previous version looked
        for them *inside* ``smali/``, which found nothing at all, so the Smali fallback
        never worked for any APK, single-dex included.

        Directories are searched in sorted order, so a class name that appears in two
        dexes resolves to the same file on every call.
        """
        relative = class_to_relative_path(class_name, ".smali")
        if relative is None:
            return None

        for root in _smali_directories(output_dir):
            candidate = root / relative
            if not candidate.is_file():
                continue
            # The name was checked; the file could still be a link out of the
            # tree. The last check is that the file really is inside it.
            if is_inside(root, candidate):
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


#: Directory names Apktool uses for decoded DEX sources.
_SMALI_DIR_PREFIX = "smali"


def _smali_directories(output_dir: Path) -> list[Path]:
    """Apktool's decoded smali roots, in sorted order.

    ``smali/`` sorts before ``smali_classes2/``, so the primary dex is always searched
    first and duplicate class names resolve deterministically.
    """
    if not output_dir.is_dir():
        return []
    return sorted(p for p in output_dir.glob(f"{_SMALI_DIR_PREFIX}*") if p.is_dir())


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() == "true"


def _merge_build_metadata(info: ManifestInfo, apktool_yml: Path) -> None:
    """Fill in version values that Apktool relocated to ``apktool.yml``.

    Some decoded manifests omit ``versionCode`` and ``versionName``, keeping them
    in Apktool's build file instead; others keep a faithful transcription of the
    binary manifest. Values already present win, so this only fills gaps. Unlike
    ``sdkInfo``, the ``versionInfo`` in the five first-party samples agrees with
    the APK's bytes — ``tests/test_version_fields.py`` pins that agreement.

    The SDK levels are deliberately not read from here. Apktool writes its own
    ``sdkInfo`` into that file, and what it writes is not what the APK's bytes
    say: decoding ``examples/wide-app/wide.apk`` — whose binary manifest carries
    ``minSdkVersion=24`` — produces an ``sdkInfo`` of 25. A value that is not the
    APK's own answer must not be merged into what the manifest "says". The levels
    are read from the binary manifest itself, by the Androguard backend, in the
    pipeline.
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


def _as_text(value: object) -> str | None:
    """Apktool writes some of these as ints and some as strings depending on version."""
    if value is None:
        return None
    return str(value)


def _values_qualifier(directory_name: str) -> str | None:
    """The qualifier of a values directory: ``values-zh`` → ``zh``.

    ``values/`` itself has none — it holds the default resource, the one every
    other qualified directory overrides.
    """
    if directory_name == "values":
        return None
    _, separator, qualifier = directory_name.partition("-")
    return qualifier if separator else None


def _layout_qualifier(directory_name: str) -> str | None:
    """The qualifier of a layout directory: ``layout-land`` → ``land``.

    ``layout/`` itself has none. The same word that separates a translated
    string from its default separates a landscape layout from its default,
    and a layout's text in two variants is two declarations for the same
    reason two languages are.
    """
    if directory_name == "layout":
        return None
    _, separator, qualifier = directory_name.partition("-")
    return qualifier if separator else None


def _element_lines(path: Path) -> dict[int, int]:
    """The source line each element of one XML file starts on.

    ElementTree stopped carrying ``sourceline`` in Python 3.8, so the lines
    come from a second pass with the expat parser underneath it: expat calls
    back with the line each ``StartElementHandler`` fires on, and the
    handler tags each element with a token that survives the round trip.
    Only the id-to-line map is returned — the parsed elements are discarded.

    A document whose DTD survived the safe parse above, or that expat reads
    differently from the safe parser, yields an empty map: the rows are then
    written without line numbers, which loses the precision of the pointer
    but not the fact itself. The safe parse has already refused every
    document this parser would read unsafely.
    """
    lines: dict[int, int] = {}
    token = 0
    parser = expat.ParserCreate()
    parser.buffer_text = True

    def start(name: str, _attrs: dict[str, str]) -> None:
        nonlocal token
        token += 1
        lines[token] = parser.CurrentLineNumber

    parser.StartElementHandler = start
    try:
        with path.open("rb") as handle:
            parser.ParseFile(handle)
    except (expat.ExpatError, OSError, ValueError):
        return {}
    return {token: line for token, line in lines.items() if token <= token}


def _relative_to(path: Path, root: Path) -> str:
    """A path relative to the tree it lives in, in the form a locator uses."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _local_name(tag: str) -> str:
    """An element's tag without its namespace.

    A values file normally declares no namespace, but nothing stops a decoded
    resource table from carrying one, and ``{http://…}string`` is still a
    ``<string>``.
    """
    return tag.rpartition("}")[2]


def _text_of(element: Element) -> str:
    """The text an element holds.

    A string resource may contain markup — ``<b>`` for bold — and the text of
    the whole element is what a reader sees. Surrounding whitespace is dropped
    because the Android resource compiler drops it too.
    """
    return "".join(element.itertext()).strip()


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


__all__ = ["ANDROID_NS", "MAX_RESOURCE_ERRORS", "ApktoolBackend", "source_locator"]
