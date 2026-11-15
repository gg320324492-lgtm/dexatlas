"""The minimal evidence package — what a client takes away and checks offline.

The package is an *explicit selection*: nothing leaves the workspace unless
``dexatlas export`` asked for it. It carries the report in all three formats,
the evidence records, the source fragments the evidence cites, and a manifest
that hashes every file in the archive.

What is deliberately not in it: the client's APK (it is identified by its
SHA-256), the full decompiled source tree, and string constants no evidence
record cites. What is missing is named in the manifest as not included — a
package that implies more than it holds is the failure mode this exists to
prevent.

Every locator travels as ``<tool>:<relative place>``, never as a machine path:
the package must survive being copied to another machine, and a local absolute
path would name the machine that made it rather than the analysis.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from dexatlas.core.models import Evidence
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.html_report import render_html
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

#: The package manifest's own version. A reader checks this before it trusts
#: anything else in the file; a change to the manifest's shape moves it.
PACKAGE_SCHEMA_VERSION = 1

#: Where the packaged reports live, inside the archive.
_REPORT_PATHS = {
    "json": "reports/report.json",
    "markdown": "reports/report.md",
    "html": "reports/report.html",
}

#: The tree the package's own source fragments live under. Not the
#: decompiler's tree name: the package's tree is the package's own.
_SOURCES_PREFIX = "sources/"

#: What is deliberately absent, stated rather than implied.
NOT_INCLUDED = {
    "apk": "the analysed APK is not packaged; identify it by its SHA-256",
    "full_sources": "only the source fragments the evidence cites are packaged",
    "unrelated_strings": "string constants that no evidence record cites are not packaged",
}

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")

REPORT_ROLES = ("json", "markdown", "html")


class EvidencePackageError(ValueError):
    """The package is not what its manifest says it is.

    A reader that finds a hash mismatch, a path that climbs out of the
    archive, or a manifest bound to a different project is holding evidence
    that cannot be trusted, and the error says which check failed.
    """


def build_evidence_package(analyzer: Analyzer, project_id: str, target: Path) -> dict[str, Any]:
    """Write the minimal evidence package for one project to ``target``.

    The reports are rendered from the workspace's published snapshot — the
    same reconstruction the REST API's export uses — so the package's reports
    are the reports the API would have served, not a re-analysis.
    """
    from dexatlas.api.app import _rebuild_result

    result = _rebuild_result(analyzer, project_id)
    store = analyzer.store
    evidence = store.list_evidence(project_id)
    workspace = store.get_workspace(project_id)

    files: dict[str, bytes] = {}
    files[_REPORT_PATHS["json"]] = json.dumps(
        build_json_report(result), indent=2, ensure_ascii=False
    ).encode("utf-8")
    files[_REPORT_PATHS["markdown"]] = render_markdown(result).encode("utf-8")
    files[_REPORT_PATHS["html"]] = render_html(result).encode("utf-8")

    for path, content in _cited_sources(evidence, workspace).items():
        files[path] = content

    manifest: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "project_id": project_id,
        "apk_sha256": result.project.apk.sha256,
        "run_id": result.run.id if result.run else None,
        "package_generated_at": datetime.now(UTC).isoformat(),
        "tool_versions": result.project.tool_versions,
        "files": [
            {
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "role": _role_of(path),
            }
            for path, content in sorted(files.items())
        ],
        "not_included": NOT_INCLUDED,
    }
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            archive.writestr(path, content)
        archive.writestr("manifest.json", manifest_bytes)
    return manifest


def _role_of(path: str) -> str:
    """What one packaged file is, in the manifest's own words."""
    if path in _REPORT_PATHS.values():
        return "report"
    if path.startswith(_SOURCES_PREFIX):
        return "evidence_source"
    return "evidence"


def _cited_sources(evidence: list[Evidence], workspace: Path | None) -> dict[str, bytes]:
    """The source fragments the evidence cites, under the package's own tree.

    A ``jadx:sources/...`` locator names a file inside the analysis's JADX
    tree. The package copies that file — and only that file — under
    ``sources/``, so a reader can follow the citation without the workspace:
    the locator's relative place, read from the package's tree, is the same
    place it named inside the analysis.
    """
    if workspace is None:
        return {}
    packaged: dict[str, bytes] = {}
    for item in evidence:
        for provenance in item.provenance:
            tool, _, place = provenance.locator.partition(":")
            if tool != "jadx" or not place:
                continue
            place = place.partition("#")[0]
            if not _is_a_safe_relative_path(place):
                # A locator that climbs out of the tree is not packaged — the
                # resolver would refuse it inside the analysis too.
                continue
            inside_tree = place
            # The locator names a place inside the JADX tree
            # (``sources/...``); the package keeps only the part below it,
            # under its own ``sources/`` prefix.
            if inside_tree.startswith("sources/"):
                inside_tree = inside_tree[len("sources/") :]
            elif inside_tree.startswith("resources/"):
                inside_tree = inside_tree[len("resources/") :]
            if not inside_tree:
                continue
            source = workspace / "jadx" / place
            if not source.is_file():
                # A locator the analysis no longer backs is not silently
                # rewritten: it stays in the evidence, and the package simply
                # does not carry a file the analysis does not have.
                continue
            packaged[f"{_SOURCES_PREFIX}{inside_tree}"] = source.read_bytes()
    return packaged


def verify_package(package_path: Path) -> dict[str, Any]:
    """Check a package against its own manifest, and return the manifest.

    Every file is hashed, every name is checked for traversal, and the
    manifest's project binding is checked against the reports it carries.
    What passes here is a package a reader can rely on; what fails raises
    :class:`EvidencePackageError` with the check that failed.
    """
    with zipfile.ZipFile(package_path) as archive:
        names = archive.namelist()
        if "manifest.json" not in names:
            raise EvidencePackageError("the package carries no manifest.json")
        manifest: dict[str, Any] = json.loads(archive.read("manifest.json"))

        _check_schema(manifest)
        _check_names(names)
        _check_hashes(archive, manifest)
        _check_binding(archive, manifest)

    return manifest


def verify_citations(package_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Whether the packaged citations resolve against the package's own tree.

    This is the check the M7 acceptance names: copy the package to another
    directory, and the key citations still resolve — from the package's
    ``sources/`` tree, not from the machine that made it.
    """
    with zipfile.ZipFile(package_path) as archive:
        packaged = set(archive.namelist())
    report = json.loads(zipfile.ZipFile(package_path).read(_REPORT_PATHS["json"]))

    unresolved: list[str] = []
    resolved = 0
    for record in report.get("evidence", []):
        for provenance in record.get("provenance", []):
            tool, _, place = provenance.get("locator", "").partition(":")
            if tool != "jadx" or not place:
                # A DEX locator names a member of the APK, which the package
                # does not carry; a tool-error locator is its own fact. Both
                # are resolved by construction, not by a file here.
                resolved += 1
                continue
            place = place.partition("#")[0]
            # The locator's place already names its position inside the
            # JADX tree (``sources/...``), which is exactly where the
            # package keeps it: the package's ``sources/`` tree mirrors the
            # locator's own relative place, so the reader follows the
            # citation to the same relative path it named inside the
            # analysis.
            candidate = place
            if candidate in packaged:
                resolved += 1
            else:
                unresolved.append(provenance["locator"])

    total = resolved + len(unresolved)
    return {
        "citations_total": total,
        "citations_resolved": total > 0 and not unresolved,
        "citations_unresolved": unresolved,
        "apk_sha256": manifest["apk_sha256"],
    }


def load_manifest(package_path: Path) -> dict[str, Any]:
    """The manifest, after the package has passed verification."""
    return verify_package(package_path)


def _check_schema(manifest: dict[str, Any]) -> None:
    version = manifest.get("schema_version")
    if not isinstance(version, int):
        raise EvidencePackageError(f"manifest schema_version is not a number: {version!r}")
    if version != PACKAGE_SCHEMA_VERSION:
        raise EvidencePackageError(
            f"package schema {version} is not the schema this reader knows "
            f"({PACKAGE_SCHEMA_VERSION})"
        )
    for field in ("project_id", "apk_sha256", "files"):
        if field not in manifest:
            raise EvidencePackageError(f"manifest carries no {field!r}")


def _check_names(names: list[str]) -> None:
    """No entry climbs out of the archive, and none is absolute.

    The check runs before anything is read out by path: an archive whose
    names attack the reader is refused as a whole, not stripped entry by
    entry.
    """
    for name in names:
        if not name or name != name.strip():
            raise EvidencePackageError(f"package entry {name!r} is not a clean relative name")
        if "\\" in name or "\x00" in name or _WINDOWS_DRIVE.match(name):
            raise EvidencePackageError(f"package entry {name!r} is not a POSIX relative path")
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts:
            raise EvidencePackageError(
                f"package entry {name!r} traverses out of the package (path traversal)"
            )


def _check_hashes(archive: zipfile.ZipFile, manifest: dict[str, Any]) -> None:
    listed = {entry["path"]: entry for entry in manifest["files"]}
    names = set(archive.namelist()) - {"manifest.json"}
    if set(listed) != names:
        missing = sorted(names - set(listed))
        extra = sorted(set(listed) - names)
        raise EvidencePackageError(
            f"manifest and archive disagree: unlisted={missing} missing_from_archive={extra}"
        )
    for path, entry in listed.items():
        actual = hashlib.sha256(archive.read(path)).hexdigest()
        if actual != entry["sha256"]:
            raise EvidencePackageError(
                f"{path!r} does not match its manifest sha256 "
                f"({entry['sha256'][:12]}… -> {actual[:12]}…); the package has been "
                "altered since it was written"
            )


def _check_binding(archive: zipfile.ZipFile, manifest: dict[str, Any]) -> None:
    """The package's hash belongs to the project its reports describe.

    A package whose manifest names one APK while its reports describe
    another is worse than a broken package: it is a mislabeled one. The
    binding is checked against the report's own project block, so the
    manifest cannot drift from the evidence it introduces.
    """
    report = json.loads(archive.read(_REPORT_PATHS["json"]))
    report_sha = report.get("project", {}).get("apk", {}).get("sha256")
    report_project = report.get("project", {}).get("id")
    if report_sha is not None and report_sha != manifest["apk_sha256"]:
        raise EvidencePackageError(
            "the package is bound to a different sample than its reports describe: "
            f"manifest apk_sha256={manifest['apk_sha256'][:16]}…, "
            f"report apk_sha256={report_sha[:16]}…"
        )
    if report_project is not None and report_project != manifest["project_id"]:
        raise EvidencePackageError(
            f"the package names project {manifest['project_id']!r} but its report "
            f"describes {report_project!r}"
        )


def _is_a_safe_relative_path(path: str) -> bool:
    """Whether a path stays inside the tree it is relative to.

    The same rule the locator resolver applies, applied to a file the
    package is about to copy: a path that climbs out names something the
    analysis never wrote.
    """
    if not path or path != path.strip():
        return False
    if "\\" in path or "\x00" in path or _WINDOWS_DRIVE.match(path):
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute():
        return False
    return ".." not in pure.parts


__all__ = [
    "PACKAGE_SCHEMA_VERSION",
    "EvidencePackageError",
    "build_evidence_package",
    "load_manifest",
    "verify_citations",
    "verify_package",
]
