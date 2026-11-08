"""The shape of a benchmark task, and how one is checked.

A task is a question a reader of a report would ask, together with what an
answer has to contain, what it must not contain, and where in the sample's own
sources the answer comes from. The last part is what makes the task worth
anything: an expectation that was collected by running the tool under test
records the tool's current behaviour and calls it truth, and a bug in the tool
would then be recorded as the correct answer.

So an expectation here is written against the sample's sources — the manifest
next to the APK, the Smali tree beside it, the string resources — and the
readers in :mod:`benchmarks.axmlreader` and :mod:`benchmarks.dexreader` exist
so that a second person can check it against the APK's bytes without running
anything at all.

The categories are the ones the Phase 2 plan names for M3. The last of them —
questions that cannot be answered — is the one that catches a system that
confabulates, so its tasks are *scored* rather than merely present: an
unanswerable task has an answer that must be absent, and a system that answers
it anyway fails.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TypedDict

from dexatlas.core.models import Project
from dexatlas.core.pipeline import Analyzer


class Category(StrEnum):
    """What a task is about.

    The names follow the Phase 2 plan's list for M3, so a reader can match a
    category here against the milestone it comes from.
    """

    MANIFEST = "manifest"
    """Reading a manifest: what the APK declares about itself."""

    COMPONENTS = "components"
    """The components a manifest declares, and whether they are exported."""

    XREFS = "xrefs"
    """Tracing a call from its callee back to its callers."""

    STRINGS = "strings"
    """Finding a string or a resource, and where it was declared."""

    OVERLOADS = "overloads"
    """Telling methods apart when a name is not enough."""

    MULTIDEX = "multidex"
    """Reading an APK whose classes are spread over more than one DEX."""

    AMBIGUITY = "ambiguity"
    """Reading code that does not say plainly what it does."""

    PARTIAL = "partial"
    """What the analysis says when a backend is not there."""

    PROVENANCE = "provenance"
    """Checking where a piece of evidence says it came from."""

    UNANSWERABLE = "unanswerable"
    """A question the analysis cannot answer, and must not pretend to."""


class _BackendOverrides(TypedDict, total=False):
    """The backend settings one configuration turns off.

    A typed mapping rather than a plain one, so that the settings a
    configuration produces are checked against the settings object they are
    spread into.
    """

    jadx_path: str
    apktool_jar: str


class Configuration(StrEnum):
    """Which backends are installed when a task is asked.

    The three configurations are the ones this project's CI runs, and the ones
    a reader of a report can be in: every backend, the decompiler missing, and
    the APK reader missing. A task that is asked in a configuration where the
    backend that holds the answer is absent has a different right answer, and
    the task says which configuration it is asked in.
    """

    FULL = "full"
    """Every backend installed: the decompiler, the APK reader and the DEX reader."""

    NO_JADX = "no-jadx"
    """JADX absent: the code is still readable as Smali, but there is no Java."""

    NO_APKTOOL = "no-apktool"
    """Apktool absent: no manifest, no resources and no Smali."""

    @property
    def environment(self) -> _BackendOverrides:
        """The backend settings this configuration stands for.

        An empty string disables a backend outright — it is not looked up on
        ``PATH`` — which is how this project's own "Apktool only" CI job turns
        the decompiler off.
        """
        if self is Configuration.NO_JADX:
            return {"jadx_path": ""}
        if self is Configuration.NO_APKTOOL:
            return {"apktool_jar": ""}
        return {}


class Sample(StrEnum):
    """One of the first-party applications in ``examples/``.

    Every sample is committed with the sources it was built from, so an
    expectation can be read out of the repository rather than collected from a
    run.
    """

    DEMO = "demo-app"
    MULTIDEX = "multidex-app"
    OBFUSCATED = "obfuscated-app"
    STRINGS = "strings-app"
    WIDE = "wide-app"

    @property
    def apk(self) -> Path:
        """The APK this sample is, inside the repository."""
        root = Path(__file__).resolve().parents[1]
        return root / "examples" / self.value / f"{self.value.split('-')[0]}.apk"

    @property
    def source_directory(self) -> Path:
        """The directory holding the APK and the sources it was built from."""
        root = Path(__file__).resolve().parents[1]
        return root / "examples" / self.value


@dataclass(frozen=True, slots=True)
class Finding:
    """One piece of evidence the analysis returned."""

    text: str
    """What a reader would look at: a name, an excerpt, a call site's caller."""

    locator: str = ""
    """Where the evidence says it came from, when it says anything."""


@dataclass(frozen=True, slots=True)
class Answer:
    """What the analysis returned for one question.

    An answer with no findings is not a failed query — it is the answer to a
    question the analysis cannot answer, and several tasks are exactly about
    that case.

    The answer is a *list of evidence*, not a paragraph. A system that answers
    in prose has to turn its prose into that list before it can be checked,
    and the runner for M3's three configurations is where that happens. The
    :attr:`text` field is here for the case where a prose answer is the
    evidence in its own right — a single quoted source, say — and it is
    checked the same way the findings are.
    """

    findings: tuple[Finding, ...] = ()
    note: str = ""
    """A short account of what the query did, for a reader of the run's log.

    The note is never checked against a task. It is the runner's own account
    of what it did, and a phrase in it — "no callers of Crypto.digestOf" — is
    the opposite of a claim.
    """

    text: str = ""
    """A prose answer, for a system that answers in prose.

    Empty for DexAtlas's own API, whose answers are lists of evidence.
    """


@dataclass(frozen=True, slots=True)
class Context:
    """What a probe is given when it asks the analysis a question."""

    analyzer: Analyzer
    project_id: str
    project: Project
    sample: Sample
    configuration: Configuration


#: A probe asks the analysis one question and reports what came back.
Probe = Callable[[Context], Answer]


@dataclass(frozen=True, slots=True)
class Task:
    """One question, and what an answer to it has to look like."""

    id: str
    """A stable name, so a run's output can be compared with another's."""

    category: Category
    """What the question is about."""

    question: str
    """The question, in the words a reader of a report would use."""

    sample: Sample
    """Which application the question is about."""

    probe: Probe
    """How the question is put to DexAtlas."""

    source: str
    """Where in the sample's own sources the expected answer comes from.

    This is the sentence that makes the task auditable: it points at the file
    — a Smali file, the checked-in manifest, the checked-in ``strings.xml`` —
    that a second person can read to confirm the expectation without running
    the analysis.
    """

    configuration: Configuration = Configuration.FULL
    """Which backends are installed when the question is asked."""

    must_contain: tuple[str, ...] = ()
    """Text every answer has to contain, at least in one finding.

    Matched case-insensitively, as a substring. The text is the analysis's own
    — a method's qualified name, a component's name, a search hit's excerpt —
    so a task states what has to be in it rather than how it is phrased.
    """

    must_not_contain: tuple[str, ...] = ()
    """Text no answer may contain, in any finding.

    This is where a wrong answer's *shape* is caught. A question about a
    method with no callers fails if the answer names a caller, even if the
    rest of the answer is perfect.

    The note is not checked: it is the runner's own account of what the query
    did, and a phrase in it — "no callers of Crypto.digestOf" — says the
    opposite of a claim. The note says how the answer was arrived at; the
    findings are the answer.

    On a task whose answer is an absence, this list means something else: it
    names the things a confabulating system would reach for, and a prose
    answer that mentions one of them fails. It is empty on those tasks when
    the question is about existence rather than about a named symbol — there,
    any marker would also appear in a correct answer that says "there is
    none".
    """

    expect_count: int | None = None
    """How many findings the answer has to hold.

    A count is checked, not merely a substring: a question about how many
    components an APK declares is answered by the number, and an answer that
    lists three of four has not answered it.
    """

    expect_empty: bool = False
    """Whether the right answer is that there is nothing.

    The tasks in the :attr:`Category.UNANSWERABLE` category set this. It is
    checked as an absence, so a system that confabulates fails the task
    rather than passing it by saying nothing useful.
    """

    note: str = ""
    """Why this task is in the set, in one line. Shown by the runner."""

    def __post_init__(self) -> None:
        """Refuse a task whose checks contradict each other."""
        if self.expect_empty and self.expect_count is not None:
            raise ValueError(
                f"task {self.id!r} expects an empty answer and a count of "
                f"{self.expect_count}; those are two different answers"
            )
        if self.expect_empty and self.must_contain:
            raise ValueError(
                f"task {self.id!r} expects an empty answer and text in it; "
                "those are two different answers"
            )
        if (
            not self.expect_empty
            and not self.must_contain
            and self.expect_count is None
            and not self.must_not_contain
        ):
            raise ValueError(
                f"task {self.id!r} checks nothing: give it text to contain, "
                "a count, or an empty answer"
            )


@dataclass(frozen=True, slots=True)
class CheckResult:
    """The verdict on one task."""

    task: Task
    passed: bool
    reason: str = ""
    """Why it failed, in a sentence a reader can act on."""

    findings: tuple[Finding, ...] = ()
    """What the analysis returned, for a reader who wants to see it."""

    @property
    def answer_text(self) -> str:
        """The answer as one block of text."""
        lines = [finding.text for finding in self.findings]
        if self.task.probe is not None and not lines:
            lines.append("")
        return "\n".join(lines)


def _contains(haystack: str, needle: str) -> bool:
    """Whether ``needle`` appears in ``haystack``, ignoring case."""
    return needle.casefold() in haystack.casefold()


def check(task: Task, answer: Answer) -> CheckResult:
    """Decide whether an answer satisfies a task.

    The order matters: a task that expects nothing is decided by the absence
    of evidence first, and only then by what the answer says. A system that
    answers an unanswerable question is wrong whichever way it words it.
    """
    texts = [finding.text for finding in answer.findings]
    joined = "\n".join(texts)
    said = f"{joined}\n{answer.text}"

    if task.expect_empty:
        if answer.findings:
            names = ", ".join(finding.text for finding in answer.findings[:3])
            return CheckResult(
                task=task,
                passed=False,
                reason=f"the right answer is that there is nothing, but {len(answer.findings)} "
                f"piece(s) of evidence came back: {names}",
                findings=answer.findings,
            )
        for unwanted in task.must_not_contain:
            if _contains(answer.text, unwanted):
                return CheckResult(
                    task=task,
                    passed=False,
                    reason=f"the answer names {unwanted!r}, which is the kind of thing this "
                    "question cannot be answered with",
                    findings=answer.findings,
                )
        return CheckResult(task=task, passed=True, findings=answer.findings)

    for wanted in task.must_contain:
        if not any(_contains(text, wanted) for text in texts) and not _contains(
            answer.text, wanted
        ):
            return CheckResult(
                task=task,
                passed=False,
                reason=f"no evidence contains {wanted!r}",
                findings=answer.findings,
            )

    for unwanted in task.must_not_contain:
        if _contains(said, unwanted):
            return CheckResult(
                task=task,
                passed=False,
                reason=f"the evidence contains {unwanted!r}, which the answer must not say",
                findings=answer.findings,
            )

    if (
        not task.must_contain
        and task.expect_count is None
        and not answer.findings
        and not answer.text
    ):
        # A task that only forbids something checks nothing when the answer is
        # empty: "the evidence does not say X" is true of no evidence at all.
        # So a task of this shape has to have produced something to be wrong
        # about.
        return CheckResult(
            task=task,
            passed=False,
            reason="the answer is empty, so there is nothing for the check to look at",
            findings=answer.findings,
        )

    if task.expect_count is not None and len(answer.findings) != task.expect_count:
        return CheckResult(
            task=task,
            passed=False,
            reason=f"expected {task.expect_count} piece(s) of evidence, got {len(answer.findings)}",
            findings=answer.findings,
        )

    return CheckResult(task=task, passed=True, findings=answer.findings)


@dataclass(frozen=True, slots=True)
class CategoryTally:
    """How one category went."""

    category: Category
    passed: int
    total: int

    @property
    def ratio(self) -> float:
        """The fraction that passed, as a number between 0 and 1."""
        return self.passed / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class Tally:
    """How the whole run went, and how each category went."""

    results: tuple[CheckResult, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    def by_category(self) -> list[CategoryTally]:
        """The per-category counts, in the order the categories are declared."""
        counts: dict[Category, list[int]] = {}
        for result in self.results:
            bucket = counts.setdefault(result.task.category, [0, 0])
            bucket[1] += 1
            if result.passed:
                bucket[0] += 1
        return [
            CategoryTally(category=category, passed=counts[category][0], total=counts[category][1])
            for category in Category
            if category in counts
        ]

    def failures(self) -> Sequence[CheckResult]:
        """The results that did not pass."""
        return [result for result in self.results if not result.passed]
