"""The benchmark task set, and how to get at it.

The tasks are split by category, one module per group, because a reader who
wants to know what the benchmark asks about should be able to open the file
for one category and read it straight through.

Every task in every module carries the same four things: the question, the
answer it has to produce, the answer it must not produce, and the file in the
sample's own sources that establishes the expected answer.
"""

from __future__ import annotations

from benchmarks.model import Category, Task
from benchmarks.tasks import manifest, methods, multidex, partial, strings, xrefs


def components_tasks() -> tuple[Task, ...]:
    """The component-declaration tasks.

    They live in the manifest module because they are read out of the same
    file, but they are a category of their own: a component declaration and a
    manifest attribute are different questions.
    """
    return tuple(task for task in manifest.TASKS if task.category is Category.COMPONENTS)


#: Every task in the set, in a fixed order.
#:
#: The order is the order the categories are declared in, and within a
#: category the order the tasks are written in. A run's output therefore reads
#: the same way twice, which is what makes two runs comparable.
ALL_TASKS: tuple[Task, ...] = (
    *manifest.TASKS,
    *xrefs.TASKS,
    *strings.TASKS,
    *methods.TASKS,
    *multidex.TASKS,
    *partial.TASKS,
)


def tasks_in(category: Category) -> tuple[Task, ...]:
    """The tasks of one category, in order."""
    return tuple(task for task in ALL_TASKS if task.category is category)


def _check_ids_are_unique() -> None:
    """Refuse a task set with two tasks of the same name.

    A task's id is how a run's output is compared with another's, so two
    tasks with one id would make the numbers ambiguous.
    """
    seen: set[str] = set()
    for task in ALL_TASKS:
        if task.id in seen:
            raise ValueError(f"two tasks share the id {task.id!r}")
        seen.add(task.id)


_check_ids_are_unique()

__all__ = ["ALL_TASKS", "components_tasks", "tasks_in"]
