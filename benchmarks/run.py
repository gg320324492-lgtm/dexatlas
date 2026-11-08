"""Run the M3 benchmark task set against DexAtlas and report the result.

Run it with::

    uv run --no-sync python benchmarks/run.py

What it does, in order: it analyses each sample once per backend
configuration the task set needs, asks every task's question of the analysis
through DexAtlas's own API, and checks the answer against what the task says
an answer has to contain.

The numbers are deterministic. The project id of an analysis is the APK's
SHA-256, so the same sample produces the same project every time; the task
order is fixed; and the workspace is rebuilt from scratch on every run, so
nothing a previous run left behind can change the result. The only thing
that is not reproducible is the wall-clock time, and that is not printed.

The exit code is 0 when every task passed and 1 otherwise, so the run can be
used as a gate.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

#: The repository root, so that ``python benchmarks/run.py`` finds the
#: ``benchmarks`` package whatever directory the run was started from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.model import (  # noqa: E402
    Answer,
    Category,
    CheckResult,
    Configuration,
    Context,
    Finding,
    Sample,
    Tally,
    Task,
    check,
)
from benchmarks.tasks import ALL_TASKS  # noqa: E402
from dexatlas.config.settings import Settings  # noqa: E402
from dexatlas.core.pipeline import AnalysisResult, Analyzer  # noqa: E402

#: The marker file that says a directory is a benchmark workspace and may be
#: deleted by a later run. Without it, a mistyped ``--workspace`` could point
#: at something the runner would then remove.
WORKSPACE_MARKER = ".dexatlas-benchmark-workspace"

#: The default workspace root: inside the project folder, because everything
#: this project writes belongs there and the system drive is nearly full.
DEFAULT_WORKSPACE = Path(__file__).resolve().parents[1] / ".scratch" / "tmp" / "benchmarks"


@dataclass(frozen=True, slots=True)
class _Analysis:
    """One sample, analysed in one configuration."""

    analyzer: Analyzer
    result: AnalysisResult


def _prepare_workspace(root: Path) -> Path:
    """Make a fresh workspace, refusing to touch one that is not ours.

    The workspace is rebuilt on every run so that the numbers cannot depend on
    what an earlier run left behind. That makes deleting it safe — but only
    if it is a workspace this runner made, which is what the marker file is
    for.
    """
    marker = root / WORKSPACE_MARKER
    if root.exists():
        if not marker.is_file():
            raise SystemExit(
                f"refusing to use {root}: it is not a benchmark workspace "
                f"(no {WORKSPACE_MARKER} in it). Choose another --workspace."
            )
        shutil.rmtree(root)
    root.mkdir(parents=True)
    marker.write_text("created by benchmarks/run.py\n", encoding="utf-8")
    return root


def _analyse(
    configuration: Configuration,
    samples: set[Sample],
    workspace_root: Path,
) -> dict[Sample, _Analysis]:
    """Analyse the samples a configuration is asked about."""
    analyses: dict[Sample, _Analysis] = {}
    for sample in sorted(samples, key=lambda item: item.value):
        settings = Settings(workspace=workspace_root, **configuration.environment)
        analyzer = Analyzer(settings)
        result = analyzer.analyze(sample.apk)
        analyses[sample] = _Analysis(analyzer=analyzer, result=result)
    return analyses


def _run_tasks(
    analyses: dict[tuple[Configuration, Sample], _Analysis],
    tasks: list[Task],
) -> Tally:
    """Ask every task's question and check the answer."""
    results: list[CheckResult] = []
    for task in tasks:
        analysis = analyses[(task.configuration, task.sample)]
        context = Context(
            analyzer=analysis.analyzer,
            project_id=analysis.result.project.id,
            project=analysis.result.project,
            sample=task.sample,
            configuration=task.configuration,
        )
        answer = task.probe(context)
        results.append(check(task, answer))
    return Tally(results=tuple(results))


def _self_check(tasks: list[Task]) -> list[str]:
    """The tasks that would accept an answer that is wrong.

    A task that cannot fail is not a task, and the tasks that matter most
    here are the ones whose answer is an absence: they are supposed to fail
    a system that confabulates, and that is only true if the rule really
    rejects the fabrication.

    So every task is checked against the answer that is wrong in the most
    obvious way — for a task that expects an absence, a piece of evidence and
    a sentence naming something; for a task that expects evidence, no
    evidence at all — and a task that passes its own wrong answer is
    reported.
    """
    problems: list[str] = []
    for task in tasks:
        if task.expect_empty:
            fabricated = Answer(
                findings=(Finding(text="a plausible but unfounded claim"),),
                text=" ".join(task.must_not_contain[:1]),
            )
        else:
            fabricated = Answer()
        if check(task, fabricated).passed:
            problems.append(task.id)
    return problems


def _report(tally: Tally, stream: TextIO) -> None:
    """Print what passed, what failed, and the per-category counts."""
    for result in tally.results:
        task = result.task
        mark = "PASS" if result.passed else "FAIL"
        print(f"  {mark}  {task.id}", file=stream)
        if not result.passed:
            print(f"        {result.reason}", file=stream)
            for finding in result.findings[:4]:
                text = " ".join(finding.text.split())
                print(f"        got: {text[:160]}", file=stream)
            if not result.findings:
                print("        got: (no evidence)", file=stream)

    print("", file=stream)
    print("Per-category tally", file=stream)
    for entry in tally.by_category():
        print(f"  {entry.category.value:<14} {entry.passed:>3}/{entry.total:<3}", file=stream)

    print("", file=stream)
    passed = tally.passed
    total = tally.total
    share = f"{100.0 * passed / total:.1f}%" if total else "n/a"
    print(f"Total: {passed}/{total} passed ({share})", file=stream)
    print(
        f"Self-check: every task rejects an answer that is wrong ({total} task(s) checked).",
        file=stream,
    )


def _json_report(tally: Tally) -> str:
    """The same result, as a JSON document."""
    document = {
        "total": tally.total,
        "passed": tally.passed,
        "categories": [
            {"category": entry.category.value, "passed": entry.passed, "total": entry.total}
            for entry in tally.by_category()
        ],
        "results": [
            {
                "id": result.task.id,
                "category": result.task.category.value,
                "sample": result.task.sample.value,
                "configuration": result.task.configuration.value,
                "question": result.task.question,
                "passed": result.passed,
                "reason": result.reason,
            }
            for result in tally.results
        ],
    }
    return json.dumps(document, indent=2, ensure_ascii=False)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="benchmarks/run.py",
        description="Run the M3 benchmark task set against DexAtlas.",
    )
    parser.add_argument(
        "--configuration",
        action="append",
        choices=[configuration.value for configuration in Configuration],
        help="Only run the tasks asked in this configuration. Repeatable; the default is "
        "all of them.",
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=[category.value for category in Category],
        help="Only run the tasks of this category. Repeatable.",
    )
    parser.add_argument(
        "--task",
        action="append",
        help="Only run the task whose id starts with this. Repeatable.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Where to build the analysis workspace. It is rebuilt on every run.",
    )
    parser.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Leave the workspace in place after the run, for inspection.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the tasks and their expectations without running anything.",
    )
    parser.add_argument(
        "--emit-questions",
        action="store_true",
        help="Print the questions without their expected answers, as JSON. This is what a "
        "system under test is given: a question, the sample it is about and the backend "
        "configuration — and nothing that says what the answer is.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as a JSON document instead of a report.",
    )
    return parser.parse_args(argv)


def _selected_tasks(args: argparse.Namespace) -> list[Task]:
    """The tasks the run is asked to cover."""
    tasks = list(ALL_TASKS)
    if args.category:
        wanted = set(args.category)
        tasks = [task for task in tasks if task.category.value in wanted]
    if args.task:
        prefixes = tuple(args.task)
        tasks = [task for task in tasks if task.id.startswith(prefixes)]
    return tasks


def _list_tasks(tasks: list[Task], stream: TextIO) -> None:
    """Print what the task set asks, without running it."""
    for task in tasks:
        print(f"{task.id}", file=stream)
        print(f"    category      {task.category.value}", file=stream)
        print(f"    sample        {task.sample.value}", file=stream)
        print(f"    configuration {task.configuration.value}", file=stream)
        print(f"    question      {task.question}", file=stream)
        print(f"    expects       {_expectation(task)}", file=stream)
        print(f"    source        {task.source}", file=stream)
        print(f"    note          {task.note}", file=stream)
        print("", file=stream)


def _expectation(task: Task) -> str:
    """One line saying what an answer has to look like."""
    if task.expect_empty:
        return "no evidence at all"
    parts: list[str] = []
    if task.must_contain:
        parts.append("contains " + ", ".join(repr(text) for text in task.must_contain))
    if task.must_not_contain:
        parts.append("never contains " + ", ".join(repr(text) for text in task.must_not_contain))
    if task.expect_count is not None:
        parts.append(f"exactly {task.expect_count} piece(s) of evidence")
    return "; ".join(parts)


def _questions_document(tasks: list[Task]) -> str:
    """The questions, without anything that says what the answer is.

    This is the document a system under test is given. It carries the
    question, the sample and the backend configuration, and a reference number
    in place of the task id — because several of the ids say what the answer
    is ("...has-no-callers"), and a system that reads them has been handed the
    marking scheme.

    The reference number is stable, so an answer can be matched back to a
    task without the task having said anything.
    """
    document = [
        {
            "reference": f"q{index:03d}",
            "question": task.question,
            "sample": task.sample.value,
            "configuration": task.configuration.value,
        }
        for index, task in enumerate(tasks, start=1)
    ]
    return json.dumps(document, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark and report. Returns the exit code."""
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    tasks = _selected_tasks(args)
    if not tasks:
        print("no tasks selected", file=sys.stderr)
        return 2

    # A task that cannot fail is not a task, and the tasks whose answer is
    # an absence are the ones that have to fail a confabulating system. That
    # is checked before anything is analysed, because a rule that has stopped
    # rejecting a wrong answer would make every number below meaningless.
    tolerant = _self_check(tasks)
    if tolerant:
        print(
            "self-check failed: these tasks accept an answer that is wrong: " + ", ".join(tolerant),
            file=sys.stderr,
        )
        return 2

    if args.list:
        _list_tasks(tasks, sys.stdout)
        return 0

    if args.emit_questions:
        print(_questions_document(tasks))
        return 0

    configurations = (
        {Configuration(value) for value in args.configuration}
        if args.configuration
        else set(Configuration)
    )
    analyses: dict[tuple[Configuration, Sample], _Analysis] = {}
    prepared: list[Path] = []
    for configuration in sorted(configurations, key=lambda item: item.value):
        needed = {task.sample for task in tasks if task.configuration is configuration}
        if not needed:
            continue
        workspace_root = _prepare_workspace(args.workspace / configuration.value)
        prepared.append(workspace_root)
        for sample, analysis in _analyse(configuration, needed, workspace_root).items():
            analyses[(configuration, sample)] = analysis

    tally = _run_tasks(analyses, tasks)

    # The workspace goes only after the questions have been asked: the
    # analysis reads its own database, and the answer to a question about a
    # class comes out of it.
    if not args.keep_workspace:
        for workspace_root in prepared:
            shutil.rmtree(workspace_root, ignore_errors=True)

    if args.json:
        print(_json_report(tally))
    else:
        print("DexAtlas M3 benchmark")
        print(
            f"Tasks: {tally.total}   configurations: {', '.join(sorted(c.value for c in configurations))}"
        )
        print("")
        _report(tally, sys.stdout)

    return 0 if tally.passed == tally.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
