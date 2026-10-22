"""DexAtlas CLI.

Every command delegates to :class:`~dexatlas.core.pipeline.Analyzer`. The CLI holds no
analysis logic of its own — the same code path backs the REST API, so the two cannot
drift apart.

Three kinds of "nothing" are kept apart, because they mean different things to
whoever reads the output:

* the request was wrong — the project id names nothing, or the input is not an APK.
  That is exit code :data:`EXIT_BAD_REQUEST`.
* the request was fine and the answer is empty — the project has no classes, no
  callers, no source for that class. That is exit code :data:`EXIT_EMPTY`.
* the analysis itself failed — a step raised, or the workspace could not be
  written. That is exit code :data:`EXIT_FAILED`, and it says what failed
  rather than printing a traceback: a caller that only reads the exit code can
  tell "this APK is not analysable" from "this analysis broke".

And a fourth answer that is not "nothing" at all: the request named a method
that exists several times over, and the answer is several bodies. That is exit
code :data:`EXIT_AMBIGUOUS`, and it names the candidates rather than choosing
one — the body of the wrong overload reads like evidence, and a caller that
pipes it into a report would be citing the wrong method.

A limit is a bound on what is shown, never a way to get a wrong answer. ``--limit 0``
and ``--limit -1`` are refused rather than quietly listing nothing — or, worse,
listing everything but the last row, because a negative index counts from the end.
A listing that was cut short says how many rows it left out.
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
from dexatlas.core.methods import AmbiguousMethodError, is_descriptor
from dexatlas.core.models import Project, ResourceKind, SourceDocument, canonical_method_id
from dexatlas.core.pipeline import AnalysisFailed, Analyzer
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

app = typer.Typer(
    name="dexatlas",
    help="Evidence-first Android reverse engineering and analysis platform.",
    epilog=(
        "Exit codes: 0 the command did what was asked; 1 the answer is empty; "
        "2 the request was wrong (no such project, or an input that is not an APK); "
        "3 the analysis itself failed; 4 the request was right and the answer is "
        "ambiguous (the method name matches several overloads)."
    ),
    no_args_is_help=True,
    add_completion=False,
)
console = make_console()
err_console = make_console(stderr=True)

ExitCode = typer.Exit

#: The mark for elided output. ``mark`` spells it safely on a legacy code page.
ELLIPSIS = "…"

#: The request itself was wrong: no such project, or an input that is not an APK.
EXIT_BAD_REQUEST = 2

#: The request was fine and the answer is empty: no classes matched, no callers, no
#: source for that class.
EXIT_EMPTY = 1

#: The analysis itself failed: a step raised, or the workspace could not be written.
#:
#: A failure of the analysis is not an empty answer and not a wrong request, and
#: a caller that reads only the exit code has to be able to tell the three apart:
#: "this APK has nothing in it" and "this run broke" call for different
#: responses.
EXIT_FAILED = 3

#: The request was fine and the answer is several things: the method name asked
#: for matches more than one overload, and the caller did not say which.
#:
#: This is neither an empty answer nor a wrong request, and a caller that reads
#: only the exit code has to be able to tell the three apart. "There is nothing
#: there" and "there are three things there, and only you know which one you
#: meant" call for different responses: the first is finished, the second is
#: answered again with a descriptor.
EXIT_AMBIGUOUS = 4

#: What a project id looks like, for the message that says "there is no such project".
PROJECT_ID_SHAPE = "apk_0123456789abcdef"


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


def _require_project(analyzer: Analyzer, project_id: str) -> Project:
    """Fail with a clear message when the project id names nothing.

    "No classes matched" and "there is no such project" are answers to different
    questions, and a reader told the first when the truth is the second goes
    looking for a class that was never indexed. The shape of an id is given,
    because a mistyped id is the usual cause.
    """
    project = analyzer.store.get_project(project_id)
    if project is None:
        err_console.print(
            f"[red]No such project:[/red] {project_id}\n"
            f"Project ids look like [bold]{PROJECT_ID_SHAPE}[/bold] — 'apk_' "
            "followed by the first 16 hex characters of the APK's SHA-256.\n"
            "Run `dexatlas projects` to list the projects in this workspace."
        )
        raise ExitCode(code=EXIT_BAD_REQUEST)
    return project


def _not_shown(hidden: int, singular: str, plural: str | None = None) -> str:
    """The line that says a listing was cut short, and by how much."""
    return (
        f"[dim]{mark(ELLIPSIS)} {_more(hidden, singular, plural)} not shown "
        "(use --limit to see more)[/dim]"
    )


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
        raise ExitCode(code=EXIT_BAD_REQUEST) from exc
    except AnalysisFailed as exc:
        # The analysis broke. The reason was recorded on the project before the
        # exception was raised, so it is in the database as well as here -- and
        # it is said here rather than as a traceback, because a caller that
        # reads the output wants to know what failed, not where in the code it
        # failed. The message is the recorded error's own, so the two say the
        # same thing.
        err_console.print(f"[red]{exc.error.message}[/red]")
        raise ExitCode(code=EXIT_FAILED) from exc

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

    raise ExitCode(code=0 if result.succeeded else EXIT_EMPTY)


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
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum classes to list. 1 or more; the CLI applies no upper bound.",
        ),
    ] = 50,
    provenance_limit: Annotated[
        int,
        typer.Option(
            "--provenance-limit",
            min=0,
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
    _require_project(analyzer, project_id)
    indexed = analyzer.store.list_classes(project_id, prefix=prefix)
    if not indexed:
        err_console.print("[yellow]No classes matched.[/yellow]")
        raise ExitCode(code=EXIT_EMPTY)

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
        console.print(_not_shown(hidden_classes, "class", "classes"))


@app.command()
def methods(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[
        str | None, typer.Option("--class", help="Restrict to one class.")
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum methods to list. 1 or more; the CLI applies no upper bound.",
        ),
    ] = 100,
) -> None:
    """List the methods indexed for a project.

    The ``Decompiled`` column is the decompiler's own answer: it says whether
    JADX produced Java for the method, so ``no`` means there is no decompiled
    source to read.
    """
    analyzer = Analyzer()
    _require_project(analyzer, project_id)
    indexed = analyzer.store.list_methods(project_id, class_name)
    if not indexed:
        err_console.print("[yellow]No methods matched.[/yellow]")
        raise ExitCode(code=EXIT_EMPTY)

    rows = indexed[:limit]
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

    # A capped listing that does not say so is a listing that looks complete.
    # The other two listings already admitted it; this one did not, and a
    # project with thousands of methods is exactly where the difference shows.
    hidden = len(indexed) - len(rows)
    if hidden > 0:
        console.print(_not_shown(hidden, "method"))


@app.command()
def source(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    class_name: Annotated[str, typer.Argument(help="Fully-qualified class name.")],
    method: Annotated[
        str | None, typer.Option("--method", help="Print one method instead of the class.")
    ] = None,
    descriptor: Annotated[
        str | None,
        typer.Option(
            "--descriptor",
            help="The method's DEX descriptor, e.g. '(Ljava/lang/String;)V'. "
            "Picks one overload out of several.",
        ),
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

    The source is Java or Smali, and the two are not interchangeable. Which one
    it is, and where it came from, are printed on stderr, so stdout carries the
    source and nothing else and can be piped into a file unchanged;
    ``--format json`` carries the same information in the document itself.

    A method name that matches several overloads is not answered by picking one
    of them: the candidates are named, and the exit code says the request was
    ambiguous. ``--descriptor`` says which overload is meant.
    """
    analyzer = Analyzer()
    _require_project(analyzer, project_id)
    if descriptor is not None and not is_descriptor(descriptor):
        err_console.print(
            f"[red]Not a DEX descriptor:[/red] {descriptor}\n"
            "A descriptor looks like '(Ljava/lang/String;)V' — an argument list "
            "in brackets, and a return type."
        )
        raise ExitCode(code=EXIT_BAD_REQUEST)
    try:
        document = (
            analyzer.method_source_document(project_id, class_name, method, descriptor)
            if method or descriptor
            else analyzer.class_source_document(project_id, class_name)
        )
    except AmbiguousMethodError as exc:
        err_console.print(f"[red]Ambiguous method:[/red] {exc}")
        for candidate in exc.candidates:
            err_console.print(f"  {candidate.signature}")
        if any(candidate.descriptor for candidate in exc.candidates):
            err_console.print(
                "Ask again with --descriptor and the descriptor of the one you meant."
            )
        else:
            err_console.print(
                "The symbol index does not hold this method, so it cannot say which "
                "descriptor each overload has."
            )
        raise ExitCode(code=EXIT_AMBIGUOUS) from None
    if document is None:
        what = f"{class_name}.{method}" if method else class_name
        err_console.print(
            f"[yellow]No source for {what}.[/yellow] "
            "JADX and Apktool must both be installed, and the APK re-analysed."
        )
        raise ExitCode(code=EXIT_EMPTY)

    # The kind travels beside the source, never inside it. The text form is
    # meant to be redirected into a file unchanged, and a first line saying
    # "java" would be a line of the file that is not code. stderr is the same
    # bargain the REST API strikes with its ``X-DexAtlas-Source-Kind`` header:
    # the body stays the source, and the answer to "is this Java or Smali?"
    # sits beside it.
    err_console.print(f"[dim]source kind: {document.kind.value}[/dim]")
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
    project_id: str,
    class_name: str,
    method: str | None,
    document: SourceDocument,
) -> dict[str, object]:
    """The JSON form of a source: the text, and where it came from.

    The descriptor travels with it, because a document that says which method
    it holds is worth more than one that says only the name — and two
    overloads share the name. It is the descriptor the document holds, not the
    one that was asked for: a request that named only a method still says
    which of the overloads it got.
    """
    return {
        "project_id": project_id,
        "class_name": class_name,
        "method": method,
        "descriptor": document.descriptor,
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
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum resources to list. 1 or more; the CLI applies no upper bound.",
        ),
    ] = 100,
) -> None:
    """List the resource strings indexed for a project.

    These are the strings the APK's resource table declares — the ones in
    ``res/values/strings.xml`` and its siblings. Each row names the file it was
    declared in, so a value found here can be traced back to its declaration.
    """
    analyzer = Analyzer()
    _require_project(analyzer, project_id)
    rows = analyzer.resources(project_id, name=name)
    if not rows:
        err_console.print(
            "[yellow]No resources matched.[/yellow] "
            "The Apktool backend reads them; it may not have been installed."
        )
        raise ExitCode(code=EXIT_EMPTY)

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
        console.print(_not_shown(hidden, "resource"))


@app.command()
def search(
    project_id: Annotated[str, typer.Argument(help="Project id.")],
    keyword: Annotated[str, typer.Argument(help="Term to search for.")],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum results. 1 or more; the CLI applies no upper bound.",
        ),
    ] = 50,
) -> None:
    """Full-text search across a project's indexed symbols."""
    analyzer = Analyzer()
    _require_project(analyzer, project_id)
    # One row more than was asked for: the extra row is how the command knows
    # there is something left to show. The search is answered inside SQLite,
    # which returns the rows and no total, so the number of rows left out is
    # not known here — the message says that more exist without claiming how
    # many.
    found = analyzer.search(project_id, keyword, limit=limit + 1)
    if not found:
        err_console.print(f"[yellow]No matches for {keyword!r}.[/yellow]")
        raise ExitCode(code=EXIT_EMPTY)

    rows = found[:limit]
    table = Table(header_style="bold")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Excerpt")
    for row in rows:
        table.add_row(str(row["kind"]), str(row["name"]), str(row["excerpt"]))
    console.print(table)

    if len(found) > limit:
        console.print(
            f"[dim]{mark(ELLIPSIS)} more results not shown (use --limit to see more)[/dim]"
        )


@app.command()
def manifest(project_id: Annotated[str, typer.Argument(help="Project id.")]) -> None:
    """Show the parsed AndroidManifest.xml for a project."""
    analyzer = Analyzer()
    _require_project(analyzer, project_id)
    info = analyzer.store.get_manifest(project_id)
    if info is None:
        err_console.print("[yellow]No manifest recorded.[/yellow] Apktool may be unavailable.")
        raise ExitCode(code=EXIT_EMPTY)

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
    _require_project(analyzer, project_id)
    # Canonicalise before the lookup, so the id echoed back on failure is the one
    # that was actually searched for — and can be pasted again.
    method_id = canonical_method_id(method_id)
    rows = analyzer.store.get_method_references(project_id, method_id)
    if not rows:
        err_console.print(f"[yellow]No callers of {method_id}.[/yellow]")
        raise ExitCode(code=EXIT_EMPTY)

    for row in rows:
        console.print(f"  [bold]{row.caller}[/bold]  {mark(ARROW)} [dim]{row.callee}[/dim]")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
