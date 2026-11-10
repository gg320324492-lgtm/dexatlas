"""M3 三配置对比 harness,也是八项指标的唯一再生入口.

两种用法:

* ``python benchmarks/comparison/run.py`` — 跑三个配置,写 trace 与报告;
* ``python benchmarks/comparison/run.py --input <trace.json> --metrics`` —
  不重跑,只从已有 trace 重算指标. §5 要求"每个报告数字都能由仓库里的
  脚本再生",靠的就是后一种.

判分与被测系统严格隔离:只有 :func:`_score` 读 ``ALL_TASKS``;每个系统
只拿到 ``emit_questions()`` 给出的 reference / question / sample /
configuration. task id 和期望答案在判分之后才写进 trace.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.comparison.adapters import (  # noqa: E402
    answer_from_result,
    is_empty,
)
from benchmarks.comparison.metrics import METRIC_NAMES, compare, format_value  # noqa: E402
from benchmarks.comparison.model import Question, TaskTrace  # noqa: E402
from benchmarks.comparison.systems import (  # noqa: E402
    AgentSystem,
    SourceTextSystem,
    StructuredSystem,
    System,
    scripted_agent_provider,
)
from benchmarks.model import Configuration, Sample, check  # noqa: E402
from benchmarks.run import (  # noqa: E402
    _analyse,
    _prepare_workspace,
    _questions_document,
    _self_check,
)
from benchmarks.tasks import ALL_TASKS  # noqa: E402

DEFAULT_OUTPUT = REPOSITORY_ROOT / ".scratch" / "comparison"
WORKSPACE_MARKER = ".benchmark-comparison-workspace"


@dataclass(frozen=True, slots=True)
class ComparisonRun:
    """一次运行的全部可再生数据."""

    traces: tuple[TaskTrace, ...]
    metrics: dict[str, dict[str, float | int | None]]
    providers: dict[str, str]
    models: dict[str, str]
    budget: int
    task_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "m3_comparison",
            "task_count": self.task_count,
            "budget": self.budget,
            "providers": self.providers,
            "models": self.models,
            "metrics": self.metrics,
            "traces": [trace.to_dict() for trace in self.traces],
        }


def _questions() -> tuple[Question, ...]:
    """被测系统能看到的全部输入."""
    return tuple(
        Question(
            reference=str(item["reference"]),
            question=str(item["question"]),
            sample=str(item["sample"]),
            configuration=str(item["configuration"]),
        )
        for item in json.loads(_questions_document(list(ALL_TASKS)))
    )


def _score(question: Question, trace: TaskTrace) -> TaskTrace:
    """判分器:唯一允许读 marking scheme 的地方."""
    index = int(question.reference.removeprefix("q")) - 1
    task = ALL_TASKS[index]
    answer = answer_from_result(trace.result)
    result = check(task, answer)
    return TaskTrace(
        reference=trace.reference,
        task_id=task.id,
        system=trace.system,
        provider=trace.provider,
        model=trace.model,
        max_tokens=trace.max_tokens,
        question=trace.question,
        passed=result.passed,
        answer_is_empty=is_empty(answer),
        expects_absence=task.expect_empty,
        result=trace.result,
    )


def _analyse_samples(
    workspace: Path, *, samples: set[Sample]
) -> tuple[Any, dict[str, Any], dict[str, str]]:
    """分析 81 道题用到的样本,三配置共用同一份工作区.

    只用 ``Configuration.FULL``:A 读样本自带源码,B/D 读同一份结构化索引.
    """
    from dexatlas.config.settings import Settings

    root = workspace / "full"
    _prepare_workspace(root)
    analyses = _analyse(Configuration.FULL, samples, root)
    settings = Settings(workspace=root)
    analyzer = type(next(iter(analyses.values())).analyzer)(settings)
    project_ids = {
        sample.value: analysis.result.project.id for sample, analysis in analyses.items()
    }
    by_name = {sample.value: analysis for sample, analysis in analyses.items()}
    return analyzer, by_name, project_ids


def _sources() -> dict[str, Path]:
    return {sample.value: sample.source_directory for sample in Sample}


def _systems(
    *, analyzer: Any, analyses: dict[str, Any], workspace: Path, budget: int
) -> tuple[System, ...]:
    """三个配置,同一预算,同一 provider 接口."""
    project_ids = {name: analysis.result.project.id for name, analysis in analyses.items()}
    return (
        SourceTextSystem(sources=_sources(), max_tokens=budget),
        StructuredSystem(analyzer=analyzer, project_ids=project_ids, max_tokens=budget),
        AgentSystem(
            analyzer=analyzer,
            analyses=analyses,
            provider_factory=scripted_agent_provider,
            store_root=workspace / "agent-states",
            max_tokens=budget,
        ),
    )


def run_comparison(*, workspace: Path, budget: int = 2048, limit: int = 0) -> ComparisonRun:
    """跑一次完整对比,返回可序列化的全部数据.

    ``limit`` 只用于冒烟:它截断的是被问的题,不会改变 reference 与题号的
    对应关系,也不改变判分规则.正式报告的数字必须来自 ``limit=0``.
    """
    tasks = list(ALL_TASKS)
    tolerant = _self_check(tasks)
    if tolerant:
        raise SystemExit(
            "self-check failed: these tasks accept an answer that is wrong: " + ", ".join(tolerant)
        )

    questions = _questions()
    selected = questions[:limit] if limit > 0 else questions
    needed_samples = {Sample(value) for value in {question.sample for question in selected}}
    analyzer, analyses, _ = _analyse_samples(workspace, samples=needed_samples)
    systems = _systems(analyzer=analyzer, analyses=analyses, workspace=workspace, budget=budget)

    traces: list[TaskTrace] = []
    for system in systems:
        for question in selected:
            result = system.answer(question)
            raw = TaskTrace(
                reference=question.reference,
                system=system.kind,
                provider=system.provider_name,
                model=system.model_name,
                max_tokens=system.max_tokens,
                question=question.question,
                result=result,
            )
            traces.append(_score(question, raw))

    return ComparisonRun(
        traces=tuple(traces),
        metrics=compare(traces),
        providers={system.kind.value: system.provider_name for system in systems},
        models={system.kind.value: system.model_name for system in systems},
        budget=budget,
        task_count=len(selected),
    )


def _disclosure(run: ComparisonRun, stream: TextIO) -> None:
    """把"这不是模型基线"写在报告最前面."""
    scripted = [name for name, provider in run.providers.items() if provider == "scripted"]
    if scripted:
        print(
            "DISCLOSURE: configurations "
            + ", ".join(scripted)
            + " were measured with the scripted provider. This proves the "
            "comparison machinery runs; it is NOT a model baseline and no "
            "difference between these configurations is a claim about model "
            "quality.",
            file=stream,
        )
    print(
        f"Tasks: {run.task_count}. Budget: {run.budget} max_tokens per task, "
        "shared by all three configurations.",
        file=stream,
    )
    print(
        "The systems saw only reference/question/sample/configuration; "
        "the marking scheme was held by the scorer.",
        file=stream,
    )


def _render(run: ComparisonRun, stream: TextIO) -> None:
    _disclosure(run, stream)
    print("", file=stream)
    header = f"{'metric':<32}" + "".join(f"{name:>16}" for name in run.metrics)
    print(header, file=stream)
    print("-" * len(header), file=stream)
    for metric in METRIC_NAMES:
        row = f"{metric:<32}" + "".join(
            f"{format_value(metric, values[metric]):>16}" for values in run.metrics.values()
        )
        print(row, file=stream)

    # §5: tool-execution success 的 95% 目标,没达到就写出来,不藏.
    print("", file=stream)
    for name, values in run.metrics.items():
        success = values["tool_call_success_rate"]
        if success is None:
            print(f"{name}: tool-call success n/a (no tool calls recorded)", file=stream)
        elif isinstance(success, (int, float)) and success < 0.95:
            print(
                f"{name}: tool-call success {format_value('tool_call_success_rate', success)} "
                "is below the 95% target (shortfall disclosed)",
                file=stream,
            )
    print("", file=stream)
    print(
        "No improvement is claimed: a difference between configurations on a "
        "scripted provider measures the harness, not the models.",
        file=stream,
    )


def _markdown(run: ComparisonRun) -> str:
    """Render the report with no hand-written numbers.

    Every figure in the table comes from ``run.metrics``, which comes from the
    traces. Regenerate this file with ``--report``; do not edit a number.
    """
    lines = [
        "# M3 baseline comparison",
        "",
        "Generated by `python benchmarks/comparison/run.py --report <path>`. "
        "Every figure below is derived from the traces in "
        "`comparison.json`; regenerate it, do not edit a number.",
        "",
        "## What this measurement is",
        "",
    ]
    scripted = [name for name, provider in run.providers.items() if provider == "scripted"]
    if scripted:
        lines += [
            f"Configurations {', '.join(scripted)} were measured with the "
            "**scripted provider**. This proves the comparison machinery runs "
            "on every task; it is **not a model baseline**. No difference "
            "between these configurations is a claim about model quality, and "
            "none is reported as an improvement.",
            "",
        ]
    lines += [
        f"Task count: {run.task_count}. Budget: {run.budget} `max_tokens` per task, "
        "identical for all three configurations. Each system saw only "
        "`reference`, `question`, `sample` and `configuration`; the scorer "
        "alone read `benchmarks/tasks/`.",
        "",
        "| Configuration | Provider | Model |",
        "|---|---|---|",
    ]
    for name in sorted(run.providers):
        lines.append(f"| {name} | {run.providers[name]} | {run.models[name] or 'n/a'} |")
    lines += [
        "",
        "## The eight metrics",
        "",
        f"| Metric |{'|'.join(f' {name} ' for name in run.metrics)}|",
        f"|---|{'|'.join('---:' for _ in run.metrics)}|",
    ]
    for metric in METRIC_NAMES:
        cells = "".join(
            f" {format_value(metric, values[metric])} |" for values in run.metrics.values()
        )
        lines.append(f"| `{metric}` |{cells}")
    lines += ["", "## Disclosures", ""]
    for name, values in run.metrics.items():
        success = values["tool_call_success_rate"]
        if success is None:
            lines.append(f"- {name}: tool-call success is n/a (no tool calls recorded).")
        elif isinstance(success, (int, float)) and success < 0.95:
            lines.append(
                f"- {name}: tool-call success is "
                f"{format_value('tool_call_success_rate', success)}, below the "
                "95% target; the shortfall is disclosed."
            )
    lines += [
        "- `n/a` means the denominator was zero. It is not a 0% result.",
        "- A comparison never claims an improvement the measurements do not "
        "support. With a scripted provider, the numbers measure the harness.",
        "",
        "## Regenerating",
        "",
        "```bash",
        "uv run --no-sync python benchmarks/comparison/run.py --input "
        "docs/benchmarks/comparison-traces.json --metrics",
        "uv run --no-sync python benchmarks/comparison/run.py --report "
        "docs/benchmarks/comparison.md",
        "```",
        "",
    ]
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Regenerate metrics from a saved trace JSON.")
    parser.add_argument("--metrics", action="store_true", help="Only print the metrics.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--budget", type=int, default=2048)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Smoke-test only: ask the first N questions. A reported measurement needs 0.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        help="Write a Markdown report whose figures all come from this run.",
    )
    return parser.parse_args(argv if argv is not None else sys.argv[1:])


def _run_from_document(document: dict[str, Any]) -> ComparisonRun:
    """Rebuild a run from saved traces, without re-running any analysis."""
    traces = tuple(TaskTrace.from_dict(item) for item in document["traces"])
    providers: dict[str, str] = {}
    models: dict[str, str] = {}
    for trace in traces:
        providers.setdefault(trace.system.value, trace.provider)
        models.setdefault(trace.system.value, trace.model)
    return ComparisonRun(
        traces=traces,
        metrics=compare(traces),
        providers=providers,
        models=models,
        budget=max((trace.max_tokens for trace in traces), default=0),
        task_count=len({trace.reference for trace in traces}),
    )


#: The measurement evidence committed to the repository. Regenerating the
#: report reads this file, so a reader does not need this machine's scratch.
COMMITTED_TRACES = REPOSITORY_ROOT / "docs" / "benchmarks" / "comparison-traces.json"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    # ``--report`` alone regenerates the checked-in report from the checked-in
    # traces. It must not silently re-run the analysis: a report that changed
    # because of a fresh run would no longer describe the evidence beside it.
    if args.report and not args.input and COMMITTED_TRACES.is_file():
        args.input = COMMITTED_TRACES
    if args.input:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        run = _run_from_document(document)
        if args.metrics:
            print(json.dumps(run.metrics, indent=2, ensure_ascii=False))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(_markdown(run), encoding="utf-8")
        if not args.metrics and not args.report:
            _render(run, sys.stdout)
        return 0

    workspace = args.workspace or args.output / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    run = run_comparison(workspace=workspace, budget=args.budget, limit=args.limit)
    args.output.mkdir(parents=True, exist_ok=True)
    document = run.to_dict()
    (args.output / "comparison.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output / "traces.json").write_text(
        json.dumps({"traces": document["traces"]}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(_markdown(run), encoding="utf-8")
    if args.json:
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        _render(run, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
