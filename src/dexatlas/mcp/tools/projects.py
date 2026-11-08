"""The tools that answer questions about the projects in this workspace."""

from __future__ import annotations

from dexatlas.core.models import Project, ToolErrorCode
from dexatlas.core.paths import display_path
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.runs import AnalysisRun
from dexatlas.mcp.errors import unknown_project
from dexatlas.mcp.schemas import (
    Completeness,
    ComponentView,
    ManifestView,
    PermissionView,
    ProjectList,
    ProjectStatus,
    ProjectSummary,
    RunSummary,
    UntrustedText,
)


def missing_backends(project: Project) -> list[str]:
    """The backends that did not take part in this analysis.

    A backend that is absent is not a backend that found nothing, and the
    difference decides what the numbers mean.
    """
    return sorted(name for name, version in project.tool_versions.items() if version is None)


def was_truncated(project: Project) -> bool:
    """Whether a limit stopped this analysis short.

    The rows that were written hold; the ones that were not are not there.
    """
    return any(error.code is ToolErrorCode.OUTPUT_TRUNCATED for error in project.errors)


def summary(project: Project) -> ProjectSummary:
    """One project, as a reader would want to know it."""
    return ProjectSummary(
        id=project.id,
        apk_name=display_path(project.apk.path),
        apk_sha256=project.apk.sha256,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        class_count=project.class_count,
        method_count=project.method_count,
        call_site_count=project.reference_count,
        call_edge_count=project.call_edge_count,
        evidence_count=project.evidence_count,
        missing_backends=missing_backends(project),
        truncated=was_truncated(project),
    )


def run_summary(run: AnalysisRun) -> RunSummary:
    """One attempt at analysing an APK."""
    return RunSummary(
        id=run.id,
        status=run.status.value,
        completeness=run.completeness.value,
        tool_versions=dict(run.tool_versions),
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        duration_seconds=run.duration_seconds,
    )


def list_projects(analyzer: Analyzer, *, limit: int, offset: int) -> ProjectList:
    """A page of the projects in this workspace, newest first."""
    projects = sorted(
        analyzer.store.list_projects(),
        key=lambda project: (project.created_at, project.id),
        reverse=True,
    )
    page = projects[offset : offset + limit]
    return ProjectList(
        projects=[summary(project) for project in page],
        total=len(projects),
        offset=offset,
        limit=limit,
    )


def project_status(analyzer: Analyzer, project_id: str) -> ProjectStatus:
    """Everything one project is, and how much of it there is."""
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise unknown_project(project_id)

    absent = missing_backends(project)
    truncated = was_truncated(project)
    published = analyzer.store.get_published_run(project_id)
    runs = analyzer.store.list_runs(project_id)

    return ProjectStatus(
        project=summary(project),
        completeness=Completeness(
            complete=not absent and not truncated and not project.errors,
            missing_backends=absent,
            truncated=truncated,
            errors=[f"{error.tool}: {error.message}" for error in project.errors],
        ),
        published_run=run_summary(published) if published is not None else None,
        runs=[run_summary(run) for run in runs],
    )


def manifest(analyzer: Analyzer, project_id: str) -> ManifestView:
    """What the manifest says about the APK."""
    project = analyzer.store.get_project(project_id)
    if project is None:
        raise unknown_project(project_id)

    info = analyzer.store.get_manifest(project_id)
    if info is None:
        raise unknown_project(project_id)

    return ManifestView(
        package=info.package or "",
        version_name=info.version_name,
        version_code=_as_int(info.version_code),
        min_sdk=_as_int(info.min_sdk),
        target_sdk=_as_int(info.target_sdk),
        permissions=[
            PermissionView(
                name=UntrustedText(text=permission.name),
                protection_level=(
                    UntrustedText(text=permission.protection_level)
                    if permission.protection_level
                    else None
                ),
            )
            for permission in info.permissions
        ],
        components=[
            ComponentView(kind=component.kind, name=component.name, exported=component.exported)
            for component in info.components
        ],
    )


def _as_int(value: str | None) -> int | None:
    """A number the manifest wrote, or nothing when it is not one."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


__all__ = [
    "list_projects",
    "manifest",
    "missing_backends",
    "project_status",
    "run_summary",
    "summary",
    "was_truncated",
]
