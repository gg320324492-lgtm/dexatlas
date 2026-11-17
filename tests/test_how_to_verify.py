"""The page that tells a reader how to check the project's claims.

``docs/how-to-verify.md`` gives a reader the commands to run and the output
they should see. The numbers in that output were written by hand, and nothing
compared them with what the suite prints: a reader who saw a different number
had no way of telling whether the page or their own machine was wrong.

The check runs the two collection commands the page names and compares their
summary lines with the ones the page states. The suite is the thing the page
is about, so the suite is what answers.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

#: The pages that state the expected output.
DOCUMENTS = ("docs/how-to-verify.md", "docs/how-to-verify.zh-CN.md")

#: The marker filters the page names.
MARKERS = ("not slow", "slow")

#: The summary pytest prints when it collects the suite:
#: "1457/1604 tests collected (147 deselected)".
COLLECTED = re.compile(r"\d+/\d+ tests collected \(\d+ deselected\)")

#: The three numbers the page states in prose: the total, the fast half and
#: the integration half, each of them in bold.
STATED_NUMBERS = re.compile(
    r"\*\*(?P<total>\d+)\*\*（\*\*(?P<fast>\d+)\*\* 快 \+ \*\*(?P<slow>\d+)\*\* 集成）"  # noqa: RUF001
)


def _collect(marker: str) -> str:
    """The summary line pytest prints for a marker filter."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", marker],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summaries = COLLECTED.findall(result.stdout)
    assert summaries, f"pytest printed no collection summary:\n{result.stdout}"
    return summaries[-1]


@pytest.fixture(scope="module")
def collected() -> dict[str, str]:
    """What the suite prints when it collects it, by marker filter."""
    return {marker: _collect(marker) for marker in MARKERS}


def _the_expected_output(document: str, marker: str) -> str:
    """The output the page says the collection of a marker filter prints."""
    for line in document.splitlines():
        if f'--collect-only -q -m "{marker}"' not in line:
            continue
        found = COLLECTED.findall(line)
        if found:
            return found[-1]
    raise AssertionError(f"the page does not state the output of the {marker} collection")


def _the_stated_numbers(document: str) -> tuple[str, str, str]:
    """The three numbers the page states in prose."""
    for line in document.splitlines():
        found = STATED_NUMBERS.search(line)
        if found:
            return found.group("total"), found.group("fast"), found.group("slow")
    raise AssertionError("the page states no numbers in prose")


def _the_counts(summary: str) -> tuple[str, str]:
    """The collected and deselected counts of a collection summary."""
    match = re.search(
        r"(?P<collected>\d+)/(?P<total>\d+) tests collected \((?P<deselected>\d+)", summary
    )
    assert match is not None, summary
    return match.group("collected"), match.group("total")


@pytest.mark.parametrize("name", DOCUMENTS)
@pytest.mark.parametrize("marker", MARKERS)
def test_the_expected_output_of_the_collect_command_is_what_the_suite_prints(
    name: str, marker: str, collected: dict[str, str]
) -> None:
    """The page's expected output is the output the suite gives.

    The page tells a reader to run two commands and shows what they should
    print. The numbers in that output were written by hand: a reader who saw
    a different number had no way of telling whether the page or their own
    machine was wrong.
    """
    document = (REPO_ROOT / name).read_text(encoding="utf-8")
    expected = _the_expected_output(document, marker)

    assert expected == collected[marker], (
        f"{name} says the {marker} collection prints {expected}, "
        f"the suite prints {collected[marker]}"
    )


@pytest.mark.parametrize("name", DOCUMENTS)
def test_the_page_states_the_numbers_the_suite_has(name: str, collected: dict[str, str]) -> None:
    """The three numbers the page states in prose are the ones the suite has.

    The total, the fast half and the integration half. The two commands
    above state the same three numbers as output; this one states them as
    prose, and a page that says 1588 in one place and 1604 in another is a
    page a reader cannot use.
    """
    document = (REPO_ROOT / name).read_text(encoding="utf-8")
    total, fast, slow = _the_stated_numbers(document)
    collected_fast, collected_total = _the_counts(collected["not slow"])
    collected_slow, _ = _the_counts(collected["slow"])

    assert total == collected_total, (
        f"{name} says the suite has {total} tests, it has {collected_total}"
    )
    assert fast == collected_fast, f"{name} says {fast} tests are fast, {collected_fast} are"
    assert slow == collected_slow, f"{name} says {slow} tests are integration, {collected_slow} are"
