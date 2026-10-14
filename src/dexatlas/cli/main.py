"""DexAtlas CLI.

Every command delegates to :class:`~dexatlas.core.pipeline.Analyzer`. The CLI holds no
analysis logic of its own — the same code path backs the REST API, so the two cannot
drift apart.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dexatlas import __version__
from dexatlas.cli.console import ARROW, DASH, OK, WARN, make_console, mark
from dexatlas.config.settings import get_settings
from dexatlas.core.ingest import ApkValidationError
from dexatlas.core.pipeline import Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

app = typer.Typer(
    name="dexatlas",
    help="Evidence-first Android reverse engineering and analysis platform.",
    no_args_is_help=True,
    add_completion=False,
)
console = make_console()
err_console = make_console(stderr=True)

ExitCode = typer.Exit


@app.callback()
def _root(
    log_level: Annotated[
        str, typer.Option("--log-level", help="Python log level for this run.")
    ] = "WARNING",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Shortcut for -l DEBUG.")
    ] = False,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.WARNING),
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command()
def version() -> None:
    """Print the DexAtlas version."""
    console.print(f"dexatlas {__version__}")


@app.command()
def backends() -> None:
    """Show which analysis backends are installed and at what version."""
    analyzer = Analyzer()
    table = Table(title="Analysis backends", header_style="bold")
    table.add_column("Backend")
    table.add_column("Status", justify="right")
    table.add_column("Version")

    for backend in analyzer.backends.all():
        installed = backend.available()
        table.add_row(
            backend.name,
            "[green]available[/green]" if installed else "[yellow]not installed[/yellow]",
            backend.version() or mark(DASH),
        )
    console.print(table)

    missing = analyzer.backends.missing()
    if missing:
        err_console.print(
            f"[yellow]{len(missing)} backend(s) unavailable.[/yellow] Analysis continues "
            "with what is installed, and records the gap as evidence."
        )


@app.command()
def analyze(
    apk: Annotated[Path, typer.Argument(help="Path to the APK to analyse.", exists=True)],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the Markdown report here."),
    ] = None,
    json_output: Annotated[
        Path | None, typer.Option("--json", help="Write the JSON report here.")
    ] = None,
    workspace: Annotated[
        Path | None, typer.Option("--workspace", help="Override the analysis workspace root.")
    ] = None,
) -> None:
    """Analyse an APK and produce a report."""
    if workspace is not None:
        import os

        os.environ["DEXATLAS_WORKSPACE"] = str(workspace)
        get_settings.cache_clear()

    try:
        result = Analyzer().analyze(apk)
    except ApkValidationError as exc:
        err_console.print(f"[red]Not a usable APK:[/red] {exc}")
        raise ExitCode(code=2) from exc

    project = result.project
    console.print(
        f"[bold green]{mark(OK)}[/bold green] {project.id} {mark(DASH)} "
        f"{project.class_count:,} classes, {project.method_count:,} methods, "
        f"{project.reference_count:,} cross-references "
        f"([dim]{result.duration_seconds:.1f}s[/dim])"
    )

    for error in project.errors:
        err_console.print(f"[yellow]{mark(WARN)}[/yellow] {error}")

    if not result.succeeded:
        err_console.print(
            "[red]Analysis produced no symbols.[/red] Install at least one backend "
            "(`dexatlas backends`) and re-run."
        )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(result), encoding="utf-8")
        console.print(f"Markdown report {mark(ARROW)} [bold]{output}[/bold]")

    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(build_json_report(result), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(f"JSON report {mark(ARROW)} [bold]{json_output}[/bold]")

    raise ExitCode(code=0 if result.succeeded else 1)


@app.command()
def projects() -> None:
    """List every analysed project."""
    analyzer = Analyzer()
    rows = analyzer.store.list_projects()
    if not rows:
        console.print("[dim]No projects yet. Run `dexatlas analyze <apk>`.[/dim]")
        return

    table = Table(title=f"Projects ({len(rows)})", header_style="bold")
    table.add_column("ID")
    table.add_column("APK")
    table.add_column("Status", justify="right")
    table.add_column("Classes", justify="right")
    table.add_column("Methods", justify="right")

    for project in rows:
        table.add_row(
            project.id,
            project.apk.path.name,
            project.status.value,
            f"{project.class_count:,}",
            f"{project.method_count:,}",
        )
    console.print(table)


@app.command()
def classes(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. apk_1a2b3c4d5e6f7890")],
    prefix: Annotated[
        str | None, typer.Option("--prefix", help="Filter by package prefix.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum classes to list.")] = 50,
) -> None:
    """List the classes indexed for a project."""
    analyzer = Analyzer()
    rows = analyzer.store.list_classes(project_id, prefix=prefix)[:limit]
    if not rows:
        err_console.print("[yellow]No classes matched.[/yellow]")
        raise ExitCode(code=1)

    for cls in rows:
        console.print(f"[bold]{cls.name}[/bold] [dim]{cls.kind.value}[/dim]")
        for source in cls.provenance[:2]:
            console.print(f"  [dim]{source.ref()}[/dim]")


@app.command()
def methods(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[
        str | None, typer.Option("--class", help="Restrict to one class.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum methods to list.")] = 100,
) -> None:
    """List the methods indexed for a project."""
    analyzer = Analyzer()
    rows = analyzer.store.list_methods(project_id, class_name)[:limit]
    if not rows:
        err_console.print("[yellow]No methods matched.[/yellow]")
        raise ExitCode(code=1)

    table = Table(header_style="bold")
    table.add_column("Method")
    table.add_column("Flags")
    for method in rows:
        table.add_row(method.qualified_name, " ".join(method.access_flags))
    console.print(table)


@app.command()
def source(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[str, typer.Argument(help="Fully-qualified class name.")],
    method: Annotated[
        str | None, typer.Option("--method", help="Print one method instead of the class.")
    ] = None,
) -> None:
    """Print a class (or one method) as decompiled Java, falling back to Smali."""
    analyzer = Analyzer()
    text = (
        analyzer.method_source(project_id, class_name, method)
        if method
        else analyzer.class_source(project_id, class_name)
    )
    if text is None:
        err_console.print(
            f"[yellow]No source for {class_name}.[/yellow] "
            "JADX and Apktool must both be installed, and the APK re-analysed."
        )
        raise ExitCode(code=1)
    console.print(text, markup=False, highlight=False)


@app.command()
def search(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    keyword: Annotated[str, typer.Argument(help="Term to search for.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum results.")] = 50,
) -> None:
    """Full-text search across a project's indexed symbols."""
    analyzer = Analyzer()
    rows = analyzer.search(project_id, keyword, limit=limit)
    if not rows:
        err_console.print(f"[yellow]No matches for {keyword!r}.[/yellow]")
        raise ExitCode(code=1)

    table = Table(header_style="bold")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Excerpt")
    for row in rows:
        table.add_row(str(row["kind"]), str(row["name"]), str(row["excerpt"]))
    console.print(table)


@app.command()
def manifest(project_id: Annotated[str, typer.Argument(help="Project id.")]) -> None:
    """Show the parsed AndroidManifest.xml for a project."""
    analyzer = Analyzer()
    info = analyzer.store.get_manifest(project_id)
    if info is None:
        err_console.print("[yellow]No manifest recorded.[/yellow] Apktool may be unavailable.")
        raise ExitCode(code=1)

    console.print(f"[bold]{info.package or '(unknown package)'}[/bold]")
    console.print(
        f"  version    {info.version_name or mark(DASH)} ({info.version_code or mark(DASH)})"
    )
    console.print(
        f"  sdk        min {info.min_sdk or mark(DASH)} / target {info.target_sdk or mark(DASH)}"
    )
    console.print(f"  permissions {len(info.permissions)}")
    console.print(f"  components  {len(info.components)}")

    exported = info.exported_components
    if exported:
        console.print("\n[bold]Exported components[/bold]")
        for component in exported:
            guard = component.permission or "no permission guard"
            console.print(f"  {component.kind:<10} {component.name}  [dim]{guard}[/dim]")


@app.command()
def xrefs(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    method_id: Annotated[
        str,
        typer.Argument(help="Method id, e.g. com.example.Foo.bar(Ljava/lang/String;)V"),
    ],
) -> None:
    """List the callers of a method."""
    analyzer = Analyzer()
    rows = analyzer.store.get_method_references(project_id, method_id)
    if not rows:
        err_console.print(f"[yellow]No callers of {method_id}.[/yellow]")
        raise ExitCode(code=1)

    for row in rows:
        console.print(f"  [bold]{row.caller}[/bold]  {mark(ARROW)} [dim]{row.callee}[/dim]")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
