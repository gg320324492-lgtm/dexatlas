"""DexAtlas CLI.

Every command delegates to :class:`~dexatlas.core.pipeline.Analyzer`. The CLI holds no
analysis logic of its own — the same code path backs the REST API, so the two cannot
drift apart.
"""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dexatlas import __version__
from dexatlas.cli.console import ARROW, DASH, OK, WARN, make_console, mark
from dexatlas.config.settings import get_settings
from dexatlas.core.ingest import ApkValidationError
from dexatlas.core.models import ResourceKind, SourceDocument, canonical_method_id
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

#: The mark for elided output. ``mark`` spells it safely on a legacy code page.
ELLIPSIS = "…"


class SourceFormat(StrEnum):
    """What ``dexatlas source`` prints."""

    TEXT = "text"
    """The source text on stdout, and where it came from on stderr."""

    JSON = "json"
    """One JSON document carrying the source and its provenance."""


def _more(count: int, singular: str, plural: str | None = None) -> str:
    """``1 more source`` / ``2 more sources`` — a count and the noun that fits it."""
    return f"{count} more {singular if count == 1 else (plural or singular + 's')}"


def _resource_word(count: int) -> str:
    """``resource string`` or ``resource strings``, to fit the count."""
    return "resource string" if count == 1 else "resource strings"


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
        f"{project.reference_count:,} cross-references, "
        f"{project.resource_count:,} {_resource_word(project.resource_count)} "
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
    provenance_limit: Annotated[
        int,
        typer.Option(
            "--provenance-limit",
            help="How many sources to show per class. 0 shows none.",
        ),
    ] = 2,
    all_sources: Annotated[
        bool, typer.Option("--all", help="Show every source of every class.")
    ] = False,
) -> None:
    """List the classes indexed for a project.

    A class can have several sources — one per backend that saw it, and one per
    dex file that defines it. The listing shows the first two and says how many
    it left out; ``--all`` shows them all, and the REST API returns them all.
    """
    analyzer = Analyzer()
    indexed = analyzer.store.list_classes(project_id, prefix=prefix)
    if not indexed:
        err_console.print("[yellow]No classes matched.[/yellow]")
        raise ExitCode(code=1)

    rows = indexed[:limit]
    for cls in rows:
        console.print(f"[bold]{cls.name}[/bold] [dim]{cls.kind.value}[/dim]")
        sources = cls.provenance if all_sources else cls.provenance[:provenance_limit]
        for source in sources:
            console.print(f"  [dim]{source.ref()}[/dim]")
        hidden = len(cls.provenance) - len(sources)
        if hidden > 0:
            console.print(
                f"  [dim]{mark(ELLIPSIS)} {_more(hidden, 'source')} not shown "
                f"(use --all to see all {len(cls.provenance)})[/dim]"
            )

    hidden_classes = len(indexed) - len(rows)
    if hidden_classes > 0:
        console.print(
            f"[dim]{mark(ELLIPSIS)} {_more(hidden_classes, 'class', 'classes')} not shown "
            f"(use --limit to see more)[/dim]"
        )


@app.command()
def methods(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[
        str | None, typer.Option("--class", help="Restrict to one class.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum methods to list.")] = 100,
) -> None:
    """List the methods indexed for a project.

    The ``Decompiled`` column is the decompiler's own answer: it says whether
    JADX produced Java for the method, so ``no`` means there is no decompiled
    source to read.
    """
    analyzer = Analyzer()
    rows = analyzer.store.list_methods(project_id, class_name)[:limit]
    if not rows:
        err_console.print("[yellow]No methods matched.[/yellow]")
        raise ExitCode(code=1)

    table = Table(header_style="bold")
    table.add_column("Method")
    table.add_column("Flags")
    table.add_column("Decompiled")
    for method in rows:
        table.add_row(
            method.qualified_name,
            " ".join(method.access_flags),
            "yes" if method.decompiled else "no",
        )
    console.print(table)


@app.command()
def source(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[str, typer.Argument(help="Fully-qualified class name.")],
    method: Annotated[
        str | None, typer.Option("--method", help="Print one method instead of the class.")
    ] = None,
    output_format: Annotated[
        SourceFormat,
        typer.Option(
            "--format",
            help="Print the source text, or a JSON document carrying its provenance.",
        ),
    ] = SourceFormat.TEXT,
) -> None:
    """Print a class (or one method) as decompiled Java, falling back to Smali.

    The source is Java or Smali, and the two are not interchangeable. Where it
    came from is printed on stderr, so stdout carries the source and nothing
    else and can be piped into a file unchanged; ``--format json`` carries the
    same information in the document itself.
    """
    analyzer = Analyzer()
    document = (
        analyzer.method_source_document(project_id, class_name, method)
        if method
        else analyzer.class_source_document(project_id, class_name)
    )
    if document is None:
        err_console.print(
            f"[yellow]No source for {class_name}.[/yellow] "
            "JADX and Apktool must both be installed, and the APK re-analysed."
        )
        raise ExitCode(code=1)

    for source in document.provenance:
        err_console.print(f"[dim]{source.ref()}[/dim]")

    if output_format is SourceFormat.JSON:
        # Printed as text: a JSON document is full of square brackets, and Rich
        # would read them as markup and corrupt the document.
        console.print(
            json.dumps(
                _source_payload(project_id, class_name, method, document),
                indent=2,
                ensure_ascii=False,
            ),
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
        return
    # ``soft_wrap`` keeps the console from re-flowing the source: a line longer
    # than the terminal is still one line of code, and a command whose output is
    # piped into a file has to put the file in it unchanged.
    console.print(document.text, markup=False, highlight=False, soft_wrap=True)


def _source_payload(
    project_id: str, class_name: str, method: str | None, document: SourceDocument
) -> dict[str, object]:
    """The JSON form of a source: the text, and where it came from."""
    return {
        "project_id": project_id,
        "class_name": class_name,
        "method": method,
        "kind": document.kind.value,
        "provenance": [p.model_dump(mode="json") for p in document.provenance],
        "text": document.text,
    }


@app.command()
def resources(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    name: Annotated[
        str | None, typer.Option("--name", help="Show one resource, by its exact name.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum resources to list.")] = 100,
) -> None:
    """List the resource strings indexed for a project.

    These are the strings the APK's resource table declares — the ones in
    ``res/values/strings.xml`` and its siblings. Each row names the file it was
    declared in, so a value found here can be traced back to its declaration.
    """
    analyzer = Analyzer()
    rows = analyzer.resources(project_id, name=name)
    if not rows:
        err_console.print(
            "[yellow]No resources matched.[/yellow] "
            "The Apktool backend reads them; it may not have been installed."
        )
        raise ExitCode(code=1)

    table = Table(header_style="bold")
    table.add_column("Resource")
    table.add_column("Value")
    table.add_column("Kind")
    table.add_column("File")
    table.add_column("Source")
    for row in rows[:limit]:
        label = row.qualified_name
        if row.quantity:
            label = f"{label} [{row.quantity}]"
        elif row.kind is ResourceKind.STRING_ARRAY:
            # The items of one array share a name; the position is what tells
            # them apart.
            label = f"{label} [{row.position}]"
        source = row.provenance[0].ref() if row.provenance else "-"
        table.add_row(label, row.value, row.kind.value, row.file, f"[dim]{source}[/dim]")
    console.print(table)

    hidden = len(rows) - len(rows[:limit])
    if hidden > 0:
        console.print(
            f"[dim]{mark(ELLIPSIS)} {_more(hidden, 'resource')} not shown "
            f"(use --limit to see more)[/dim]"
        )


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
    # Canonicalise before the lookup, so the id echoed back on failure is the one
    # that was actually searched for — and can be pasted again.
    method_id = canonical_method_id(method_id)
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
