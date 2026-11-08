"""Filling in the report format the project already has.

The report format is the deliverable, and it was written for Phase 1:
``reports/markdown.py`` and ``reports/json_report.py`` know how a reader is
to be shown evidence, and this module does not invent a second way. The
agent's report is the same shape — the same evidence model, the same table,
the same wording about what the levels mean — with the agent's findings in
it and, when there is one, the analysis report it was drawn from.

The three sections are the ones the milestone asks for, and they are three
sections rather than one list because a reader has to be able to tell them
apart:

* **Established facts** are what a tool read. Each one carries a citation
  that resolves inside the analysis.
* **Leads** are what the model concluded from those facts. They are risk
  indicators, and they are not confirmed issues.
* **Insufficient evidence** is what could not be settled either way.

A report that put all three in one table would be asking the reader to
work out which is which — and the whole point of the levels is that they do
not have to.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from dexatlas.agent.state import Budget, BudgetUsage, TaskEvent, TaskStatus
from dexatlas.agent.tool_executor import ToolCallRecord
from dexatlas.core.models import Evidence, EvidenceKind, EvidenceLevel
from dexatlas.core.pipeline import AnalysisResult
from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import _LEVEL_NOTE

#: The version of the agent report document.
#:
#: The agent report is its own document — it describes a task, not an
#: analysis — so it carries its own version. The analysis report it embeds
#: keeps the version that report has always had.
AGENT_REPORT_SCHEMA_VERSION = 1

#: The header of the evidence table. It is the header the analysis report
#: uses, so a reader who has seen one knows how to read the other.
EVIDENCE_TABLE_HEADER = "| ID | Level | Kind | Summary | Source |"


@dataclass(frozen=True, slots=True)
class AgentReport:
    """What one task found, and what it could not settle."""

    task_id: str
    question: str
    status: TaskStatus
    project_id: str | None = None
    run_id: str | None = None
    findings: tuple[Evidence, ...] = ()
    tool_calls: tuple[ToolCallRecord, ...] = ()
    usage: BudgetUsage = field(default_factory=BudgetUsage)
    limits: Budget = field(default_factory=Budget)
    events: tuple[TaskEvent, ...] = ()
    limitations: tuple[str, ...] = ()
    error: str | None = None
    analysis: AnalysisResult | None = None
    """The analysis the task was about, when the report carries one."""

    @property
    def established(self) -> tuple[Evidence, ...]:
        """The findings a tool established."""
        return tuple(
            item
            for item in self.findings
            if item.level is EvidenceLevel.VERIFIED and item.kind is not EvidenceKind.BEHAVIOUR
        )

    @property
    def leads(self) -> tuple[Evidence, ...]:
        """The findings that are leads and nothing more."""
        return tuple(item for item in self.findings if item.level is EvidenceLevel.LEAD)

    @property
    def insufficient(self) -> tuple[Evidence, ...]:
        """The findings that could not be settled either way."""
        return tuple(item for item in self.findings if item.level is EvidenceLevel.INSUFFICIENT)


def build_agent_json(report: AgentReport) -> dict[str, Any]:
    """The agent's report, as a JSON document.

    The findings are the project's own evidence records, in the shape the
    analysis report uses, so a reader that can read one can read the other.
    """
    return {
        "schema_version": AGENT_REPORT_SCHEMA_VERSION,
        "kind": "agent_report",
        "generated_at": datetime.now(UTC).isoformat(),
        "task": {
            "id": report.task_id,
            "question": report.question,
            "status": report.status.value,
            "project_id": report.project_id,
            "run_id": report.run_id,
        },
        "findings": [item.model_dump(mode="json") for item in report.findings],
        "findings_by_level": dict(
            sorted(Counter(item.level.value for item in report.findings).items())
        ),
        "tool_calls": [record.as_dict() for record in report.tool_calls],
        "budget": {
            "used": report.usage.as_dict(),
            "limits": {
                "max_tokens": report.limits.max_tokens,
                "max_iterations": report.limits.max_iterations,
                "max_seconds": report.limits.max_seconds,
            },
        },
        "limitations": list(report.limitations),
        "events": [event.as_dict() for event in report.events],
        "error": report.error,
        # The analysis the task was about, in the analysis report's own shape.
        # It is nested rather than merged, so the analysis document keeps the
        # contract it has always had.
        "analysis": build_json_report(report.analysis) if report.analysis is not None else None,
    }


def render_agent_markdown(report: AgentReport) -> str:
    """The agent's report, as Markdown."""
    lines: list[str] = [
        "# DexAtlas agent report",
        "",
        f"**Task:** `{report.task_id}`  ",
        f"**Question:** {_inline(report.question)}  ",
        f"**Status:** {_status_line(report)}  ",
    ]
    if report.project_id:
        lines.append(f"**Project:** `{report.project_id}`  ")
    if report.run_id:
        lines.append(f"**Run:** `{report.run_id}`  ")
    lines += [
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Established facts | {len(report.established)} |",
        f"| Leads | {len(report.leads)} |",
        f"| Insufficient evidence | {len(report.insufficient)} |",
        f"| Tool calls | {len(report.tool_calls)} |",
        f"| Tokens used | {report.usage.tokens} of {report.limits.max_tokens} |",
        f"| Iterations used | {report.usage.iterations} of {report.limits.max_iterations} |",
        f"| Seconds used | {report.usage.seconds:.1f} of {report.limits.max_seconds:.0f} |",
        "",
        "## Evidence levels",
        "",
        "| Level | Count | Meaning |",
        "| --- | ---: | --- |",
    ]
    counts = Counter(item.level.value for item in report.findings)
    for level, meaning in _LEVEL_NOTE.items():
        lines.append(f"| `{level.value}` | {counts.get(level.value, 0)} | {meaning} |")

    lines += _findings_section("Established facts", report.established)
    lines += _findings_section("Leads", report.leads)
    lines += _findings_section("Insufficient evidence", report.insufficient)

    lines += _tool_section(report.tool_calls)

    if report.limitations:
        lines += ["", "## Limitations", ""]
        lines += [f"- {item}" for item in report.limitations]

    if report.error:
        lines += ["", "## What went wrong", "", f"> {report.error}"]

    if report.analysis is not None:
        lines += [
            "",
            "---",
            "",
            "## The analysis this task was about",
            "",
            "The report below is the project's own analysis report, for the run the",
            "task was about. The findings above were drawn from it through the tools.",
            "",
        ]
        from dexatlas.reports.markdown import render_markdown

        lines += render_markdown(report.analysis).splitlines()

    lines += [
        "",
        "---",
        "",
        "Generated by [DexAtlas](https://github.com/gg320324492-lgtm/dexatlas) - "
        "an evidence-first Android analysis platform.",
        "",
        "This report describes what the analysis tools established, and what the "
        "model concluded from it. An established fact carries a citation that "
        "resolves inside the analysis. A lead is a risk indicator and not a "
        "confirmed issue, and an item marked `insufficient` was not settled "
        "either way.",
        "",
    ]
    return "\n".join(lines)


def _status_line(report: AgentReport) -> str:
    """What the task's status means for a reader.

    A task that did not finish says so. "Completed" is only ever said about a
    task that answered, and a task that ran out of budget says that it ran
    out of budget rather than that it found nothing.
    """
    if report.status is TaskStatus.COMPLETED:
        return "completed"
    if report.status is TaskStatus.BUDGET_EXHAUSTED:
        return "**did not finish** — the task ran out of budget"
    if report.status is TaskStatus.FAILED:
        return "**did not finish** — the task failed"
    if report.status is TaskStatus.INTERRUPTED:
        return "**did not finish** — the task was interrupted and can be resumed"
    if report.status is TaskStatus.AWAITING_CONFIRMATION:
        return "**did not finish** — the task is waiting for a confirmation"
    return f"**did not finish** — the task is `{report.status.value}`"


def _findings_section(title: str, findings: tuple[Evidence, ...]) -> list[str]:
    """One section of findings, in the project's own evidence table."""
    lines = ["", f"## {title}", ""]
    if not findings:
        lines.append("_None._")
        return lines
    lines += [
        EVIDENCE_TABLE_HEADER,
        "| --- | --- | --- | --- | --- |",
    ]
    for item in findings:
        source = item.provenance[0].ref() if item.provenance else "-"
        lines.append(
            f"| `{item.id}` | `{item.level.value}` | {item.kind.value} | "
            f"{_inline(item.summary)} | `{source}` |"
        )
    return lines


def _tool_section(tool_calls: tuple[ToolCallRecord, ...]) -> list[str]:
    """The tool log: every call, with what it was asked and how it ended.

    The arguments are in it because a reader who wants to reproduce a
    conclusion has to know what the agent asked: "which query?" and "which
    method?" are the difference between a check and a guess.
    """
    lines = ["", "## What the agent did", ""]
    if not tool_calls:
        lines.append("_No tool was called._")
        return lines
    lines += [
        "| Tool | Arguments | Outcome | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for record in tool_calls:
        outcome = "ok" if record.ok else (record.error_kind or "failed")
        detail = "" if record.ok else (record.error or "")
        arguments = ", ".join(
            f"{name}={value!r}" for name, value in sorted(record.arguments.items())
        )
        lines.append(f"| `{record.tool}` | {_inline(arguments)} | {outcome} | {_inline(detail)} |")
    return lines


def _inline(text: str) -> str:
    """Text that has to survive a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


__all__ = [
    "AGENT_REPORT_SCHEMA_VERSION",
    "EVIDENCE_TABLE_HEADER",
    "AgentReport",
    "build_agent_json",
    "render_agent_markdown",
]
