#!/usr/bin/env python3
"""Reconcile the local gates with the CI gates, and say which differences are legal.

    uv run --no-sync python scripts/check-platform-gates.py

The gap this closes
-------------------

The same gate can be asked the same question on two machines and answer two
different things.  A relative link whose target is three dots resolves on
Windows -- where the path is normalised to the parent directory -- and
resolves nowhere on Linux.  A launcher written as a batch file cannot be
built on a POSIX shell.  A measurement that reads its children's output
with the console's encoding decodes UTF-8 as GBK on one machine and
correctly on the other.

Every one of those was found the hard way: the CI run went red and the
local suite was green, and the difference was the whole story.  This
script is the method that makes the class visible *before* a push, and it
has two rules that matter more than the rest.

**The first rule is that no rule here counts anything.**  A test that
asserts "there are exactly ten CI jobs that redirect their temporary
directory" fails the moment a job is added -- including the moment a job
is added that does the right thing.  That test was fixed twice in two
days for that reason.  Every check below is a property: *this* job does
*this*, *every* test that declares a platform declares it in the
inventory, *every* declared difference carries a reason.  Adding a job
means answering one question in the inventory, not editing a number.

**The second rule is that a difference has to be named.**  A gate that
behaves differently on Windows and on Linux is not a defect -- a batch
file launcher is a Windows launcher.  It is a defect when nobody wrote
down that it was different.  So the inventory is the deliverable: each
platform-conditional test, each platform-sensitive line of a gate script
and each CI job carries what makes it different, whether the difference
is legitimate, and -- when it is not -- what will be done about it.

The inventory is ``scripts/platform-gates.json``; this script checks it
against the tree.  It reads the workflow as text (no PyYAML) and the test
suite with ``ast`` (no import of the test modules), so it can run without
the analysis backends and without the fixtures.

The exit code is 0 when every check holds and 1 when any of them does
not; every problem is printed with the file and the reason.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "scripts" / "platform-gates.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TESTS_DIR = REPO_ROOT / "tests"

#: The name a CI step carries when it moves the temporary directory into the
#: workspace.  A job that runs ``uv`` and does not carry it writes to
#: whatever the runner's system temporary directory is -- which on a full
#: system drive is a disk-space failure rather than a test failure.
TEMP_REDIRECT_MARKER = "Keep generated files in .scratch"

#: The two platform families this repository distinguishes.  "posix" covers
#: Linux and macOS; the difference that matters here is a batch file versus
#: a shell script, not the kernel.
WINDOWS = "windows"
POSIX = "posix"
BOTH = (WINDOWS, POSIX)

#: A script under ``scripts/`` named in a workflow or a test.
SCRIPT_REFERENCE = re.compile(r"scripts/[A-Za-z0-9_.-]+\.(?:py|sh)")

#: The values a parameterisation uses when it enumerates platforms.
PLATFORM_TOKENS = frozenset({"nt", "posix", "win32", "windows", "linux", "darwin"})


# ---------------------------------------------------------------------------
# What the tree says
# ---------------------------------------------------------------------------


@dataclass
class CiJob:
    """One job of ``.github/workflows/ci.yml``."""

    name: str
    runs_on: str
    body: str

    @property
    def runs_uv(self) -> bool:
        """Whether the job installs the project's dependencies with ``uv``."""
        return "uv sync" in self.body

    @property
    def redirects_temp(self) -> bool:
        """Whether the job moves its temporary directory into the workspace."""
        return TEMP_REDIRECT_MARKER in self.body

    @property
    def gate_scripts(self) -> list[str]:
        """The scripts the job names."""
        return sorted(set(SCRIPT_REFERENCE.findall(self.body)))


def read_ci_jobs(path: Path) -> dict[str, CiJob]:
    """The jobs of a workflow file, read as text.

    The file is read as text and the jobs are found by their indentation
    rather than by a YAML parser: the check then needs no dependency, and
    a job is a job whichever way the file is written.  ``on:`` and the
    filters under it are not jobs -- they are indented two spaces as well,
    so they are told apart by the keys they use.
    """
    if not path.is_file():
        return {}
    jobs: dict[str, CiJob] = {}
    current: str | None = None
    body: list[str] = []
    runs_on = ""
    in_jobs = False

    def flush() -> None:
        if current is not None:
            jobs[current] = CiJob(current, runs_on, "\n".join(body))

    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:\s*$", line):
            # A top-level key: only the one that holds the jobs is the jobs.
            in_jobs = line.strip() == "jobs:"
            continue
        job_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line) if in_jobs else None
        if job_match:
            flush()
            current = job_match.group(1)
            body = []
            runs_on = ""
            continue
        if current is None:
            continue
        if line.startswith("    "):
            body.append(line)
            runs_on_match = re.match(r"^    runs-on:\s*(\S+)\s*$", line)
            if runs_on_match:
                runs_on = runs_on_match.group(1)
    flush()
    return jobs


@dataclass
class PlatformTest:
    """A test whose execution, or whose verdict, depends on the platform."""

    node_id: str
    kind: str
    #: The platform families the test runs on.  ``None`` when the condition
    #: says more than a two-family model can hold (a ``startswith("linux")``
    #: skip also skips on macOS, and "not Linux" is not "Windows").
    platforms: set[str] | None
    #: The reason the skip carries, when the test declares one.
    reason: str
    #: Whether the body also branches on the platform.
    body_depends: bool = False


def _is_os_name(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "name"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_sys_platform(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "platform"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _mentions_platform(node: ast.AST) -> bool:
    """Whether the expression reads something the platform decides."""
    for sub in ast.walk(node):
        if _is_os_name(sub) or _is_sys_platform(sub):
            return True
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in {"system", "machine"}
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "platform"
        ):
            return True
    return False


def _resolve_platforms(node: ast.expr) -> set[str] | None:
    """Which platform families a test runs on, when its skip says so.

    ``None`` means the condition says something a two-family model cannot
    hold honestly; the inventory then has to state the platforms itself, and
    the check does not second-guess it.
    """
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
        return None
    op = node.ops[0]
    left, right = node.left, node.comparators[0]
    if not (isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant)):
        return None
    value = right.value
    if not isinstance(value, str):
        return None
    if _is_os_name(left):
        if value == "nt":
            # Skipped on Windows, so it runs on the other family.
            return {POSIX} if isinstance(op, ast.Eq) else {WINDOWS}
        if value == "posix":
            return {WINDOWS} if isinstance(op, ast.Eq) else {POSIX}
        return None
    if _is_sys_platform(left):
        if value == "win32":
            return {POSIX} if isinstance(op, ast.Eq) else {WINDOWS}
        return None
    return None


def _decorator_name(decorator: ast.expr) -> str:
    """The name of a decorator, whatever it is written as."""
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
        return decorator.func.attr
    if isinstance(decorator, ast.Name):
        return decorator.id
    return ""


def _parametrizes_platforms(decorator: ast.expr) -> bool:
    """Whether a parameterisation enumerates the platforms."""
    if not isinstance(decorator, ast.Call) or len(decorator.args) < 2:
        return False
    for sub in ast.walk(decorator.args[1]):
        if (
            isinstance(sub, ast.Constant)
            and isinstance(sub.value, str)
            and sub.value.lower() in PLATFORM_TOKENS
        ):
            return True
    return False


def scan_platform_tests(tests_dir: Path) -> dict[str, PlatformTest]:
    """Every test whose execution or verdict depends on the platform.

    Three shapes are recognised, and they are different problems:

    * ``skipped-on`` -- a skip whose condition reads the platform.  The test
      runs on one family and not on the other, so the two platforms run
      different numbers of tests.
    * ``branching`` -- the test runs everywhere but reads the platform in
      its body, so it asserts something different on each machine.
    * ``parameterised`` -- the test runs everywhere and asserts the rule for
      both platforms.  This is the shape that closes a gap instead of
      describing one.
    """
    found: dict[str, PlatformTest] = {}
    if not tests_dir.is_dir():
        return found
    for path in sorted(tests_dir.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(tests_dir.parent).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            node_id = f"{relative}::{node.name}"
            kind = ""
            platforms: set[str] | None = None
            reason = ""
            for decorator in node.decorator_list:
                name = _decorator_name(decorator)
                if name in {"skipif", "skip"} and isinstance(decorator, ast.Call):
                    condition = decorator.args[0] if decorator.args else None
                    if condition is None or not _mentions_platform(condition):
                        continue
                    kind = "skipped-on"
                    platforms = _resolve_platforms(condition)
                    for keyword in decorator.keywords:
                        if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant):
                            reason = str(keyword.value.value)
                elif name == "parametrize" and _parametrizes_platforms(decorator):
                    kind = "parameterised"
                    platforms = set(BOTH)
            body_depends = any(_mentions_platform(statement) for statement in node.body)
            if not kind:
                if not body_depends:
                    continue
                kind = "branching"
                platforms = set(BOTH)
            found[node_id] = PlatformTest(node_id, kind, platforms, reason, body_depends)
    return found


def scan_platform_constructs(scripts_dir: Path) -> dict[str, list[str]]:
    """Every place a script under ``scripts/`` reads the platform.

    The key is ``file::function`` -- or ``file::<module>`` for a module-level
    statement -- so that the inventory does not have to name a line number.
    A line number in an inventory is a line number that rots the next time
    anything above it moves.
    """
    found: dict[str, list[str]] = {}
    if not scripts_dir.is_dir():
        return found
    for path in sorted(scripts_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        relative = path.relative_to(scripts_dir.parent).as_posix()
        functions: dict[str, ast.AST] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.setdefault(node.name, node)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                constructs = _constructs_in(node)
                if constructs:
                    found[f"{relative}::{node.name}"] = sorted(constructs)
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr)):
                constructs = _constructs_in(node)
                if constructs:
                    found.setdefault(f"{relative}::<module>", []).extend(constructs)
    return {key: sorted(set(value)) for key, value in found.items()}


def _constructs_in(node: ast.AST) -> set[str]:
    """The platform constructs one statement or function reads."""
    constructs: set[str] = set()
    for sub in ast.walk(node):
        if _is_os_name(sub):
            constructs.add("os.name")
        elif _is_sys_platform(sub):
            constructs.add("sys.platform")
        elif (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in {"system", "machine"}
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "platform"
        ):
            constructs.add(f"platform.{sub.func.attr}")
        elif (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "gettempdir"
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "tempfile"
        ):
            constructs.add("tempfile.gettempdir")
        elif (
            isinstance(sub, ast.Attribute)
            and sub.attr == "uname"
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "os"
        ):
            constructs.add("os.uname")
    return constructs


def scripts_in_workflows(workflows_dir: Path) -> set[str]:
    """The scripts any workflow names."""
    found: set[str] = set()
    if not workflows_dir.is_dir():
        return found
    for workflow in sorted(workflows_dir.glob("*.yml")):
        found.update(SCRIPT_REFERENCE.findall(workflow.read_text(encoding="utf-8")))
    return found


def scripts_in_tests(tests_dir: Path) -> set[str]:
    """The scripts the test suite names."""
    found: set[str] = set()
    if not tests_dir.is_dir():
        return found
    for test in sorted(tests_dir.rglob("test_*.py")):
        found.update(SCRIPT_REFERENCE.findall(test.read_text(encoding="utf-8")))
    return found


# ---------------------------------------------------------------------------
# What the inventory says
# ---------------------------------------------------------------------------


@dataclass
class Inventory:
    """The declared inventory of the platform differences."""

    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ci_jobs(self) -> dict[str, Any]:
        jobs = self.data.get("ci_jobs", {})
        return jobs if isinstance(jobs, dict) else {}

    @property
    def platform_tests(self) -> dict[str, Any]:
        tests = self.data.get("platform_tests", {})
        return tests if isinstance(tests, dict) else {}

    @property
    def platform_code(self) -> dict[str, Any]:
        code = self.data.get("platform_sensitive_code", {})
        return code if isinstance(code, dict) else {}

    @property
    def coverage_gaps(self) -> dict[str, Any]:
        gaps = self.data.get("coverage_gaps", {})
        return gaps if isinstance(gaps, dict) else {}


def load_inventory(path: Path) -> Inventory:
    """Read the inventory; a missing or broken file is an empty one."""
    if not path.is_file():
        return Inventory({})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return Inventory({})
    return Inventory(data if isinstance(data, dict) else {})


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def check_ci_jobs(jobs: dict[str, CiJob], inventory: Inventory) -> list[str]:
    """Every job is declared, and every declaration is true.

    The temporary-directory rule is the one this script exists for.  A job
    that installs with ``uv`` writes to the runner's temporary directory
    unless it says otherwise; the inventory has to say which of the two it
    is, and say why when it is not the safe one.
    """
    problems: list[str] = []
    declared = inventory.ci_jobs
    for name in sorted(set(jobs) | set(declared)):
        job = jobs.get(name)
        entry = declared.get(name)
        if job is None:
            problems.append(f"the inventory declares a CI job {name!r} that ci.yml does not have")
            continue
        if entry is None:
            problems.append(f"the CI job {name!r} is not in the inventory")
            continue
        if not isinstance(entry, dict):
            problems.append(f"the inventory's entry for the CI job {name!r} is not an object")
            continue
        if entry.get("runs_on") != job.runs_on:
            problems.append(
                f"the CI job {name!r} runs on {job.runs_on!r}, "
                f"the inventory says {entry.get('runs_on')!r}"
            )
        claim = entry.get("temp_redirect")
        if job.redirects_temp:
            if claim != "yes":
                problems.append(
                    f"the CI job {name!r} redirects its temporary directory, "
                    f"the inventory says {claim!r}"
                )
        elif job.runs_uv:
            if claim not in {"exempt", "defect"}:
                problems.append(
                    f"the CI job {name!r} runs 'uv sync' without redirecting its "
                    f"temporary directory and the inventory says {claim!r}; "
                    f"say 'exempt' or 'defect' and give the reason"
                )
            elif not str(entry.get("reason", "")).strip():
                problems.append(
                    f"the CI job {name!r} does not redirect its temporary directory "
                    f"and the inventory gives no reason"
                )
        elif claim not in {"n/a", "exempt", "defect"}:
            problems.append(
                f"the CI job {name!r} installs nothing with 'uv' and the inventory "
                f"says {claim!r} about its temporary directory; say 'n/a'"
            )
        elif claim in {"exempt", "defect"} and not str(entry.get("reason", "")).strip():
            problems.append(
                f"the CI job {name!r} does not redirect its temporary directory "
                f"and the inventory gives no reason"
            )
        scripts = entry.get("gate_scripts")
        if isinstance(scripts, list) and sorted(scripts) != job.gate_scripts:
            problems.append(
                f"the CI job {name!r} runs {job.gate_scripts}, the inventory says {sorted(scripts)}"
            )
        if claim == "defect" and not str(entry.get("fix", "")).strip():
            problems.append(
                f"the inventory calls the CI job {name!r} a defect and gives no fix; "
                f"a defect without a plan is a smell, not a finding"
            )
    return problems


def check_platform_tests(found: dict[str, PlatformTest], inventory: Inventory) -> list[str]:
    """Every platform-dependent test is declared, and every declaration is real.

    The check is in both directions on purpose.  A test that starts
    branching on the platform without saying so is the failure mode worth
    catching; a declared test that has been renamed or deleted is a stale
    entry, which is how an inventory stops being believed.
    """
    problems: list[str] = []
    declared = inventory.platform_tests
    for node_id in sorted(set(found) | set(declared)):
        test = found.get(node_id)
        entry = declared.get(node_id)
        if test is None:
            problems.append(
                f"the inventory declares the platform-dependent test {node_id!r}, "
                f"which does not exist"
            )
            continue
        if entry is None:
            problems.append(
                f"the test {node_id!r} depends on the platform and is not in the inventory"
            )
            continue
        if not isinstance(entry, dict):
            problems.append(f"the inventory's entry for {node_id!r} is not an object")
            continue
        if entry.get("kind") != test.kind:
            problems.append(
                f"the test {node_id!r} is {test.kind!r} and the inventory says "
                f"{entry.get('kind')!r}"
            )
        if test.platforms is not None:
            said = entry.get("platforms")
            if not isinstance(said, list) or set(said) != test.platforms:
                problems.append(
                    f"the test {node_id!r} runs on {sorted(test.platforms)}, "
                    f"the inventory says {said!r}"
                )
        if not str(entry.get("reason", "")).strip():
            problems.append(f"the inventory gives no reason for the test {node_id!r}")
        problems.extend(check_verdict(node_id, entry))
    return problems


def check_verdict(key: str, entry: dict[str, Any]) -> list[str]:
    """A difference has to be judged, and a defect has to have a plan."""
    verdict = entry.get("verdict")
    if verdict not in {"legitimate", "defect"}:
        return [
            f"the inventory's entry for {key!r} has verdict {verdict!r}; "
            f"say 'legitimate' or 'defect'"
        ]
    if verdict == "defect" and not str(entry.get("fix", "")).strip():
        return [
            f"the inventory calls {key!r} a defect and gives no fix; "
            f"a defect without a plan is a smell, not a finding"
        ]
    return []


def check_platform_code(found: dict[str, list[str]], inventory: Inventory) -> list[str]:
    """Every platform-sensitive line of a script is declared."""
    problems: list[str] = []
    declared = inventory.platform_code
    for key in sorted(set(found) | set(declared)):
        constructs = found.get(key)
        entry = declared.get(key)
        if constructs is None:
            problems.append(
                f"the inventory declares the platform-sensitive code {key!r}, "
                f"which no longer reads the platform"
            )
            continue
        if entry is None:
            problems.append(
                f"the code {key!r} reads the platform ({', '.join(constructs)}) "
                f"and is not in the inventory"
            )
            continue
        if not isinstance(entry, dict):
            problems.append(f"the inventory's entry for {key!r} is not an object")
            continue
        said = entry.get("constructs")
        if isinstance(said, list) and sorted(said) != constructs:
            problems.append(
                f"the code {key!r} reads {constructs}, the inventory says {sorted(said)}"
            )
        if not str(entry.get("reason", "")).strip():
            problems.append(f"the inventory gives no reason for the code {key!r}")
        problems.extend(check_verdict(key, entry))
    return problems


def check_coverage_gaps(
    gaps: dict[str, Any], repo_root: Path, scripts_dir: Path, tests_dir: Path
) -> list[str]:
    """The claims about who runs what are claims about the tree.

    A "only in CI" entry that no workflow names is stale; a "only local"
    entry that a workflow does name is wrong.  Both are the kind of thing
    that makes a reader stop believing the table.
    """
    problems: list[str] = []
    workflows = repo_root / ".github" / "workflows"
    in_workflows = scripts_in_workflows(workflows)
    in_tests = scripts_in_tests(tests_dir)
    for name in gaps.get("ci_only", []) or []:
        if not isinstance(name, str):
            problems.append(f"the inventory's ci_only entry {name!r} is not a script name")
            continue
        if name not in in_workflows:
            problems.append(
                f"the inventory says {name!r} runs only in CI, but no workflow names it"
            )
    for name in gaps.get("local_only", []) or []:
        if not isinstance(name, str):
            problems.append(f"the inventory's local_only entry {name!r} is not a script name")
            continue
        if not (scripts_dir / Path(name).name).is_file():
            problems.append(f"the inventory says {name!r} runs only locally, but it is gone")
            continue
        if name in in_workflows:
            problems.append(
                f"the inventory says {name!r} runs only locally, but a workflow names it"
            )
        if name in in_tests:
            problems.append(
                f"the inventory says {name!r} runs only locally, but the test suite names it"
            )
    return problems


def find_problems(repo_root: Path, inventory: Inventory) -> list[str]:
    """Every way the tree and the inventory can disagree."""
    jobs = read_ci_jobs(repo_root / ".github" / "workflows" / "ci.yml")
    tests = scan_platform_tests(repo_root / "tests")
    code = scan_platform_constructs(repo_root / "scripts")
    problems: list[str] = []
    problems.extend(check_ci_jobs(jobs, inventory))
    problems.extend(check_platform_tests(tests, inventory))
    problems.extend(check_platform_code(code, inventory))
    problems.extend(
        check_coverage_gaps(
            inventory.coverage_gaps, repo_root, repo_root / "scripts", repo_root / "tests"
        )
    )
    return problems


def main() -> int:
    inventory = load_inventory(INVENTORY)
    if not inventory.data:
        print(f"FAIL the inventory is missing or unreadable: {INVENTORY}", file=sys.stderr)
        return 1
    problems = find_problems(REPO_ROOT, inventory)
    for problem in problems:
        print(f"  FAIL {problem}", file=sys.stderr)
    if problems:
        print(
            f"\n{len(problems)} difference(s) between the tree and the inventory are "
            f"not accounted for.",
            file=sys.stderr,
        )
        return 1
    jobs = read_ci_jobs(CI_WORKFLOW)
    tests = scan_platform_tests(TESTS_DIR)
    print(
        f"  PASS {len(jobs)} CI jobs are declared, "
        f"{len(tests)} platform-dependent tests are declared, "
        f"and every difference carries a reason"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
