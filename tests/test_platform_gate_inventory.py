"""The local gates and the CI gates have to be reconciled, not assumed equal.

The same gate, asked the same question on Windows and on Linux, has given
two different answers in this repository more than once: a relative link
whose target is three dots resolves on Windows and nowhere on Linux, and a
launcher written as a batch file cannot be built on a POSIX shell.  Both
were found the same way -- the CI run went red and the local suite was
green, and the difference was the whole story.

The method this file pins has three parts, and the third one is the one
that keeps the other two honest:

1. a **list** -- ``scripts/platform-gates.json`` says which CI jobs exist,
   which tests are platform-dependent, which lines of a gate script read the
   platform, and which scripts run in only one of the two places;
2. a **mechanism** -- ``scripts/check-platform-gates.py`` compares that list
   with the tree and fails when they disagree;
3. a **record** -- ``docs/reports/platform-gate-inventory.md`` says how the
   method is used and what is still unexplained.

The rule that matters is that **nothing here counts**.  The rule this
replaces counted: "exactly ten jobs redirect their temporary directory" and
"exactly twelve steps install dependencies".  Adding a CI job that does the
right thing turned that test red, and the repair was to edit a number --
twice, in two days.  Every check below is a property, so adding a job means
answering one question in the list, not editing a number.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "scripts" / "check-platform-gates.py"
INVENTORY = REPO_ROOT / "scripts" / "platform-gates.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _checker() -> ModuleType:
    """Load the checker as a module, the way the suite loads the other scripts."""
    spec = importlib.util.spec_from_file_location("dexatlas_platform_gates", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _inventory() -> dict[str, object]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The mechanism holds on this tree
# ---------------------------------------------------------------------------


def test_the_platform_gate_checker_exists() -> None:
    assert CHECKER.is_file(), "scripts/check-platform-gates.py is missing"
    assert INVENTORY.is_file(), "scripts/platform-gates.json is missing"


def test_every_difference_the_tree_has_is_accounted_for(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The list and the tree agree.

    This is the whole method in one assertion: the checker reads the
    workflow and the test suite, compares them with the list, and fails on
    any difference nobody wrote down.  A checker that always answers 0 is a
    gate that never opens, so the exit code is asserted as well as the
    output.
    """
    checker = _checker()

    code = checker.main()
    written = capsys.readouterr().out + capsys.readouterr().err

    assert code == 0, f"the platform gate check found something:\n{written}"
    assert "PASS" in written


def test_the_known_platform_differences_are_listed_as_they_are() -> None:
    """The two launcher tests are the reason the platforms report different counts.

    One runs on Windows and one on POSIX, and neither is a defect: a batch
    file is a Windows launcher.  They are listed, with the reason, so that
    a reader who sees 1689 against 1694 has an answer.
    """
    inventory = _inventory()
    tests = inventory["platform_tests"]
    assert isinstance(tests, dict)

    windows = tests[
        "tests/test_backend_timeout.py::test_a_windows_launcher_is_stopped_with_its_work"
    ]
    posix = tests[
        "tests/test_backend_timeout.py::test_a_posix_launcher_that_spawns_work_is_stopped_with_its_work"
    ]

    assert windows["platforms"] == ["windows"]
    assert posix["platforms"] == ["posix"]
    assert windows["verdict"] == "legitimate"
    assert posix["verdict"] == "legitimate"
    assert windows["reason"].strip()
    assert posix["reason"].strip()


def test_a_declared_difference_without_a_reason_is_found() -> None:
    """A difference nobody explained is not a difference, it is a surprise.

    The check that makes the list worth reading: an entry that says nothing
    about why the two platforms differ is not an entry, it is a name.
    """
    checker = _checker()
    inventory = checker.Inventory(
        {
            "ci_jobs": {
                "a-job": {
                    "runs_on": "ubuntu-latest",
                    "gate_scripts": [],
                    "temp_redirect": "yes",
                }
            },
            "platform_tests": {
                "tests/test_x.py::test_y": {
                    "kind": "skipped-on",
                    "platforms": ["windows"],
                    "verdict": "legitimate",
                }
            },
        }
    )
    problems = checker.check_platform_tests(
        {
            "tests/test_x.py::test_y": checker.PlatformTest(
                "tests/test_x.py::test_y", "skipped-on", {"windows"}, ""
            )
        },
        inventory,
    )

    assert any("gives no reason" in problem for problem in problems), problems


def test_a_defect_without_a_plan_is_found() -> None:
    """A defect without a fix is a smell; the check says so."""
    checker = _checker()
    problems = checker.check_verdict("tests/test_x.py::test_y", {"verdict": "defect"})

    assert any("gives no fix" in problem for problem in problems), problems


# ---------------------------------------------------------------------------
# The mechanism catches what the count-based rule could not
# ---------------------------------------------------------------------------


def _tree(root: Path, workflow: str, inventory: dict[str, object]) -> Path:
    """A copy of the repository's scripts and tests, with a given workflow and list.

    The copy is faithful so that the only difference between the tree the
    check is run on and the tree in the repository is the one the test
    makes -- otherwise a difference nobody declared would hide behind the
    copy's own omissions.
    """
    shutil.copytree(REPO_ROOT / "scripts", root / "scripts")
    shutil.copytree(REPO_ROOT / "tests", root / "tests")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text(workflow, encoding="utf-8")
    (root / "scripts" / "platform-gates.json").write_text(json.dumps(inventory), encoding="utf-8")
    return root


def test_a_job_that_installs_without_the_redirect_is_found(tmp_path: Path) -> None:
    """The job that installs and does not move its temporary directory is a finding.

    A runner's system temporary directory is small and shared.  The old rule
    counted the jobs that redirect and the jobs that install and compared
    the two totals, so a job that installs and does *not* redirect was
    invisible as long as some other job did both.  This is the property
    instead: the job that installs has to say, one way or the other, what it
    does about its temporary directory.
    """
    checker = _checker()
    workflow = (
        "jobs:\n"
        "  good:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Keep generated files in .scratch\n"
        "        run: mkdir -p .scratch/tmp\n"
        "      - name: Install dependencies\n"
        "        run: uv sync --frozen\n"
        "  quiet:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Install dependencies\n"
        "        run: uv sync --frozen\n"
    )
    inventory = {
        "ci_jobs": {
            "good": {
                "runs_on": "ubuntu-latest",
                "gate_scripts": [],
                "temp_redirect": "yes",
            },
            "quiet": {
                "runs_on": "ubuntu-latest",
                "gate_scripts": [],
                "temp_redirect": "yes",
            },
        }
    }
    root = _tree(tmp_path, workflow, inventory)

    problems = checker.find_problems(
        root, checker.load_inventory(root / "scripts" / "platform-gates.json")
    )

    assert any("'quiet'" in problem for problem in problems), problems


def test_adding_a_correct_job_does_not_turn_the_check_red(tmp_path: Path) -> None:
    """A job added tomorrow must not need a number edited.

    This is the case that made the old rule unusable.  It counted two
    totals -- the jobs that redirect their temporary directory and the jobs
    that install with ``uv`` -- and required both to be a fixed number.  A
    new job that installs *and* redirects is exactly what the rule was for,
    and it turned the test red; the repair was to edit the number, which is
    how a number stops describing anything.

    The property below asks a different question -- does this job do the
    right thing -- and so a correct job added to the workflow costs one
    entry in the list and nothing else.
    """
    checker = _checker()
    original = CI_WORKFLOW.read_text(encoding="utf-8")
    added = (
        "\n  a-new-job:\n"
        "    name: A new job that does the right thing\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Keep generated files in .scratch\n"
        "        run: mkdir -p .scratch/tmp\n"
        "      - name: Install dependencies\n"
        "        run: uv sync --frozen\n"
    )
    workflow = original + added
    inventory = _inventory()
    root = _tree(tmp_path, workflow, inventory)

    problems = checker.find_problems(
        root, checker.load_inventory(root / "scripts" / "platform-gates.json")
    )

    # The new job is not in the list yet, so the check says so -- and says
    # nothing about the jobs that were already there.
    assert any("a-new-job" in problem for problem in problems), problems
    assert not any("redirect" in problem and "a-new-job" not in problem for problem in problems), (
        problems
    )

    # Answer the one question the list asks about the new job, and the
    # check is green: the cost of a new job is one entry, not an edit to a
    # number that appears in no other file.
    jobs = inventory["ci_jobs"]
    assert isinstance(jobs, dict)
    jobs["a-new-job"] = {
        "runs_on": "ubuntu-latest",
        "gate_scripts": [],
        "temp_redirect": "yes",
    }
    root = _tree(tmp_path / "declared", workflow, inventory)
    problems = checker.find_problems(
        root, checker.load_inventory(root / "scripts" / "platform-gates.json")
    )

    assert problems == [], problems

    # The rule that was replaced compared two totals with two frozen
    # numbers.  Adding a job that redirects moves both totals, so the old
    # verdict changed even though nothing about the new job was wrong.
    assert workflow.count("Keep generated files in .scratch") != original.count(
        "Keep generated files in .scratch"
    )
    assert workflow.count("uv sync") != original.count("uv sync")


def test_a_platform_conditional_test_that_is_not_declared_is_found(tmp_path: Path) -> None:
    """A test that starts branching on the platform without saying so is found.

    The test suite is where a platform difference usually arrives: somebody
    writes a test that only makes sense on one machine, or that asserts
    something different on each.  The list is where that has to be written
    down, and this is the check that makes the list hold.
    """
    checker = _checker()
    workflow = "jobs:\n  only:\n    runs-on: ubuntu-latest\n    steps: []\n"
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(workflow, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "platform-gates.json").write_text(
        json.dumps(
            {
                "ci_jobs": {
                    "only": {"runs_on": "ubuntu-latest", "gate_scripts": [], "temp_redirect": "n/a"}
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_something.py").write_text(
        "import os\n"
        "\n"
        "import pytest\n"
        "\n"
        "\n"
        '@pytest.mark.skipif(os.name == "nt", reason="a Windows launcher")\n'
        "def test_a_windows_only_thing() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    problems = checker.find_problems(
        tmp_path, checker.load_inventory(tmp_path / "scripts" / "platform-gates.json")
    )

    assert any("test_something.py::test_a_windows_only_thing" in problem for problem in problems), (
        problems
    )


def test_a_declared_test_that_is_gone_is_found(tmp_path: Path) -> None:
    """A list entry for a test that no longer exists is stale, and stale is wrong.

    An inventory that keeps entries for tests that were deleted is how a
    reader stops believing it: the difference it names is not a difference
    any more, and the one that replaced it is not there.
    """
    checker = _checker()
    workflow = "jobs:\n  only:\n    runs-on: ubuntu-latest\n    steps: []\n"
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(workflow, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "platform-gates.json").write_text(
        json.dumps(
            {
                "ci_jobs": {
                    "only": {"runs_on": "ubuntu-latest", "gate_scripts": [], "temp_redirect": "n/a"}
                },
                "platform_tests": {
                    "tests/test_gone.py::test_that_is_gone": {
                        "kind": "skipped-on",
                        "platforms": ["windows"],
                        "reason": "it used to be here",
                        "verdict": "legitimate",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()

    problems = checker.find_problems(
        tmp_path, checker.load_inventory(tmp_path / "scripts" / "platform-gates.json")
    )

    assert any("does not exist" in problem for problem in problems), problems


def test_a_claim_about_a_script_that_no_workflow_runs_is_found(tmp_path: Path) -> None:
    """The coverage list is a claim about the tree, and the tree says otherwise.

    "This script runs only in CI" is a sentence a reader will act on.  If
    no workflow names the script any more, the sentence is a lie and
    somebody will skip a gate that is still being run.
    """
    checker = _checker()
    workflow = "jobs:\n  only:\n    runs-on: ubuntu-latest\n    steps: []\n"
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(workflow, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "platform-gates.json").write_text(
        json.dumps(
            {
                "ci_jobs": {
                    "only": {"runs_on": "ubuntu-latest", "gate_scripts": [], "temp_redirect": "n/a"}
                },
                "coverage_gaps": {"ci_only": ["scripts/never-mentioned.py"]},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()

    problems = checker.find_problems(
        tmp_path, checker.load_inventory(tmp_path / "scripts" / "platform-gates.json")
    )

    assert any("no workflow names it" in problem for problem in problems), problems
