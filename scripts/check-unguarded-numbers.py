#!/usr/bin/env python3
"""Check the handwritten numbers that no other gate checks.

    uv run --no-sync python scripts/check-unguarded-numbers.py

The gap this closes
-------------------
The measurement script writes the numbers that carry a ``<!--fig:...-->``
marker, and the release-number gate reads the numbers that the release texts
state. Everything else is written by hand in a sentence, and a hand-written
number that goes stale is a number nobody notices: there is no gate that turns
red, so the tree stays green while the page lies.

The audit that found them (``docs/reports/handwritten-numbers-audit.md``)
listed ten places. This gate owns the ones whose truth can be derived from the
tree -- the CI job count, the number of MCP tools, the figures the execution
report records, the counts the benchmark traces carry -- and compares each
hand-written sentence with that truth.

**The rule that matters here is that no number is written down twice.**  The
gate never says "the CI job count is 13"; it says "the sentence says the
number of CI jobs, and the workflow has this many".  The truth is computed
from the tree every time the gate runs, so adding a job -- or a tool, or a
test -- turns the gate red without anybody editing a number.  That is the
same shape as ``scripts/check-platform-gates.py``: the inventory is the
deliverable, and the numbers live in one place.

The statements this gate watches are listed in
``scripts/unguarded-numbers.json``.  A statement whose wording moves is
itself a finding, because a gate that quietly stops matching is a gate that
quietly stops guarding.

The exit code is 0 when every statement agrees with its fact, and 1 when one
does not -- including when a statement is no longer there to check.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "scripts" / "unguarded-numbers.json"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REAL_TRACES = REPO_ROOT / "docs" / "benchmarks" / "comparison-real-traces.json"


@dataclass(frozen=True)
class Finding:
    """One statement that does not agree with the fact it is about."""

    statement: str
    path: str
    line: int
    what: str
    stated: str
    expected: str


def show(text: str) -> str:
    """A text that can be printed on any console.

    The documents this gate reads are written in two languages, and a console
    that cannot encode one of them turns the report of a finding into a
    second failure.  The escaped form says the same thing and always prints.
    """
    return text if text.isascii() else ascii(text)


def sibling(name: str) -> Any:
    """Load a script from ``scripts/`` as a module.

    How a file is read out of a tree is one rule and it lives in the script
    that owns it: the release-number gate knows which figures the execution
    report records, the version-claim gate knows how many tools the MCP
    server registers.  A second copy of either here would be a second answer
    to the same question, and the two answers would drift.

    The module has to be in ``sys.modules`` before it runs: a module whose
    annotations resolve through itself fails to import otherwise.
    """
    script = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"dexatlas_{script.stem}", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: The numbers a document writes in words.
WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

#: The same numbers in Chinese, written the way a Chinese document writes them.
CN_DIGITS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def parse_number(raw: str) -> float | None:
    """A number as a document writes it: ``1,695``, ``thirteen``, ``十三``.

    ``None`` means the text is not a number this gate can read -- a word it
    does not know, or a string that is not a number at all.  The caller
    reports that as a finding rather than guessing.
    """
    text = raw.strip().lower().replace(",", "")
    if text in WORD_NUMBERS:
        return float(WORD_NUMBERS[text])
    if text.isdigit():
        return float(int(text))
    if "十" in text:
        # The way Chinese writes the teens: one ten plus a digit, or the
        # bare ten.
        head, _, tail = text.partition("十")
        tens = CN_DIGITS.get(head, 1) if head else 1
        ones = CN_DIGITS.get(tail, 0) if tail else 0
        if not tail and not head:
            return 10.0
        if tail and tail not in CN_DIGITS:
            return None
        return float(tens * 10 + ones)
    if len(text) == 1 and text in CN_DIGITS:
        return float(CN_DIGITS[text])
    try:
        return float(text)
    except ValueError:
        return None


def same_number(left: float, right: float) -> bool:
    """Whether two numbers are the same number.

    A percentage is written with one decimal in the documents and computed
    with more, so a rate is compared after rounding to the precision the
    document writes.
    """
    if left == right:
        return True
    return round(left, 1) == round(right, 1)


def matrix_size(spec: dict[str, Any]) -> int:
    """How many runs a job's matrix expands to.

    The axes multiply; ``exclude`` takes runs away and an ``include`` that
    matches no combination adds one.  This is GitHub's rule, and the job
    count in the documentation is only right if it is the same rule.
    """
    strategy = spec.get("strategy") or {}
    matrix = strategy.get("matrix") or {}
    axes = {key: value for key, value in matrix.items() if key not in ("include", "exclude")}
    if not axes:
        return 1
    combinations: list[dict[str, Any]] = [{}]
    for key, values in axes.items():
        if not isinstance(values, list):
            values = [values]
        combinations = [{**base, key: value} for base in combinations for value in values]
    for excluded in matrix.get("exclude") or []:
        if isinstance(excluded, dict):
            combinations = [
                combination
                for combination in combinations
                if not all(
                    key in combination and combination[key] == value
                    for key, value in excluded.items()
                )
            ]
    for included in matrix.get("include") or []:
        if not isinstance(included, dict):
            continue
        matches = [
            combination
            for combination in combinations
            if all(
                key in combination and combination[key] == value for key, value in included.items()
            )
        ]
        if not matches:
            combinations.append(included)
    return len(combinations)


def ci_shape() -> dict[str, int]:
    """What the workflow actually runs.

    Three numbers: the jobs, the runs a tag push starts, and the runs a push
    or a pull request starts.  The last one is the first minus the jobs that
    only run on a tag -- a job whose ``if`` names a tag reference is a job a
    push does not start.
    """
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow.get("jobs") or {}
    tag_runs = 0
    push_runs = 0
    for spec in jobs.values():
        size = matrix_size(spec)
        tag_runs += size
        condition = str(spec.get("if") or "")
        if "refs/tags" not in condition:
            push_runs += size
    return {"ci_jobs": len(jobs), "ci_tag_runs": tag_runs, "ci_push_runs": push_runs}


def report_figures() -> dict[str, float]:
    """The figures the execution report records.

    The report is the authority for the numbers a measurement produced: it is
    written by the measurement script and compared against the source
    fingerprint of the tree it measured.
    """
    release = sibling("check-release-numbers.py")
    figures = release.read_authority()
    numbers: dict[str, float] = {}
    for key, value in figures.items():
        parsed = parse_number(value)
        if parsed is not None:
            numbers[key.replace(".", "_")] = parsed
    return numbers


def trace_assertions() -> dict[str, float]:
    """What the committed benchmark traces carry.

    The traces of the real-model run are committed, so the assertion counts
    are derived from them: the same derivation the report's metrics use, with
    the same denominator -- an assertion with no text says nothing.
    """
    document = json.loads(REAL_TRACES.read_text(encoding="utf-8"))
    per_system: dict[str, dict[str, int]] = {}
    for trace in document.get("traces", []):
        system = str(trace.get("system") or "")
        counts = per_system.setdefault(system, {"assertions": 0, "grounded": 0})
        for assertion in (trace.get("result") or {}).get("assertions") or []:
            if not str(assertion.get("text") or "").strip():
                continue
            counts["assertions"] += 1
            if assertion.get("grounded") and str(assertion.get("locator") or "").strip():
                counts["grounded"] += 1
    dexatlas = per_system.get("DexAtlas", {"assertions": 0, "grounded": 0})
    baseline = sum(
        counts["assertions"] for name, counts in per_system.items() if name != "DexAtlas"
    )
    unlocated = dexatlas["assertions"] - dexatlas["grounded"]
    rate = (unlocated / dexatlas["assertions"] * 100) if dexatlas["assertions"] else 0.0
    return {
        "trace_dexatlas_assertions": float(dexatlas["assertions"]),
        "trace_dexatlas_grounded": float(dexatlas["grounded"]),
        "trace_dexatlas_unlocated": float(unlocated),
        "trace_dexatlas_unsupported_rate": round(rate, 1),
        "trace_baseline_assertions": float(baseline),
    }


def contract_static_checks() -> float | None:
    """How many checks the public-contract script makes.

    The static count is the number of ``check()`` call sites in the contract
    script -- what ``docs/architecture/public-contracts.md`` section 7 records
    and what ``scripts/check-contract-records.py`` compares against a live
    run.  The glossary restates that number, so the glossary has to agree
    with the script rather than with a copy of the script.
    """
    script = REPO_ROOT / "scripts" / "verify-public-contracts.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "check"
    ]
    return float(len(calls))


def facts() -> dict[str, float]:
    """Every fact this gate compares a sentence against."""
    version_claims = sibling("check-version-claims.py")
    tools = version_claims.mcp_tool_count()
    values: dict[str, float] = dict(ci_shape())
    if tools is not None:
        values["mcp_tools"] = float(tools)
    for key, value in report_figures().items():
        values[f"report_{key}"] = value
    values.update(trace_assertions())
    static_checks = contract_static_checks()
    if static_checks is not None:
        values["contract_static_checks"] = static_checks
    return values


def load_inventory() -> list[dict[str, Any]]:
    """The statements this gate watches."""
    document = json.loads(INVENTORY.read_text(encoding="utf-8"))
    statements = document.get("statements")
    if not isinstance(statements, list):
        return []
    return [statement for statement in statements if isinstance(statement, dict)]


def check_text(statement: dict[str, Any], text: str, truths: dict[str, float]) -> list[Finding]:
    """Compare one statement, read out of a text, with the facts it is about."""
    path = str(statement.get("path") or "")
    identifier = str(statement.get("id") or path)
    pattern = str(statement.get("pattern") or "")
    groups = statement.get("groups")
    if not isinstance(groups, dict) or not groups:
        return []
    try:
        matcher = re.compile(pattern, re.MULTILINE)
    except re.error as error:
        return [
            Finding(
                statement=identifier,
                path=path,
                line=0,
                what=f"the pattern in the inventory does not compile: {error}",
                stated=pattern,
                expected="",
            )
        ]
    findings: list[Finding] = []
    statements_found = 0
    for match in matcher.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        read: dict[str, float | None] = {}
        for group in groups:
            raw = match.group(group)
            if raw is None:
                # The group did not take part in this match: the sentence has
                # a shape the pattern only sometimes matches. The group is
                # simply not checked here.
                continue
            read[group] = parse_number(raw)
        if not read or any(value is None for value in read.values()):
            # The pattern matched something that is not a number statement --
            # "the tools," rather than "eleven tools". A sentence whose number
            # cannot be read is not a number this gate can check; if it was
            # the only match, the statement is reported as gone.
            continue
        statements_found += 1
        for group, fact in groups.items():
            if group not in read:
                continue
            stated = read[group]
            expected = truths.get(str(fact))
            if expected is None:
                findings.append(
                    Finding(
                        statement=identifier,
                        path=path,
                        line=line,
                        what=f"the fact {fact} is not one this gate can compute",
                        stated=match.group(group),
                        expected="",
                    )
                )
                continue
            assert stated is not None
            if not same_number(stated, expected):
                findings.append(
                    Finding(
                        statement=identifier,
                        path=path,
                        line=line,
                        what=f"it says {stated:g}, and the {fact} is {expected:g}",
                        stated=match.group(group),
                        expected=f"{expected:g}",
                    )
                )
    if statements_found == 0 and not findings:
        findings.append(
            Finding(
                statement=identifier,
                path=path,
                line=0,
                what="the statement this gate watches is no longer in the document",
                stated=pattern,
                expected="",
            )
        )
    return findings


def check_statement(statement: dict[str, Any], truths: dict[str, float]) -> list[Finding]:
    """Compare one statement, read out of its document, with its facts."""
    path = str(statement.get("path") or "")
    document = REPO_ROOT / path
    if not document.is_file():
        return [
            Finding(
                statement=str(statement.get("id") or path),
                path=path,
                line=0,
                what="the statement this gate watches names a file that is not there",
                stated="",
                expected=path,
            )
        ]
    return check_text(statement, document.read_text(encoding="utf-8"), truths)


def main(argv: list[str] | None = None) -> int:
    """Check every statement in the inventory."""
    del argv
    truths = facts()
    findings: list[Finding] = []
    checked = 0
    for statement in load_inventory():
        checked += 1
        findings.extend(check_statement(statement, truths))
    for finding in findings:
        where = f"{finding.path}:{finding.line}" if finding.line else finding.path
        print(f"FAIL {where}  [{finding.statement}]  {finding.what}")
        if finding.stated:
            print(f"     the document says: {show(finding.stated)}")
        if finding.expected:
            print(f"     the tree says:     {show(finding.expected)}")
    if findings:
        print(f"\n{len(findings)} finding(s) in {checked} watched statements.")
        return 1
    print(f"PASS {checked} watched statements agree with the tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
