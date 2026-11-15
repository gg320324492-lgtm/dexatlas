"""The budget a first-time user gets.

The defaults are a public promise: a task started without any environment
variable runs under exactly these numbers. They were raised after the M4
re-verification measured the old ones — every task in that run stopped at
``budget_exhausted`` with the model still reading — and the numbers below are
the configuration that run completed tasks under, with the iteration ceiling
raised to the point the longest recorded run actually reached.

The environment is still the override, and it replaces the defaults rather
than adding to them.
"""

from __future__ import annotations

import pytest

from dexatlas.agent.planner import DEFAULT_MAX_STEPS, Planner
from dexatlas.agent.state import Budget
from dexatlas.workbench.agent_tasks import (
    AGENT_MAX_ITERATIONS_ENV,
    AGENT_MAX_SECONDS_ENV,
    AGENT_MAX_STEPS_ENV,
    AGENT_MAX_TOKENS_ENV,
    budget_from_env,
    max_steps_from_env,
)


def test_the_default_budget_is_the_measured_configuration() -> None:
    """The numbers the M4 re-verification completed tasks under."""
    limits = Budget()
    assert limits.max_tokens == 120_000
    assert limits.max_iterations == 16
    assert limits.max_seconds == 120.0
    assert Planner().max_steps == 40
    assert DEFAULT_MAX_STEPS == 40


def test_the_step_budget_leaves_room_for_the_plan_and_the_verifier() -> None:
    """One model tool call spends one iteration; the plan and verifier spend steps too.

    A step budget at or below the iteration budget could only ever be reached
    by the calls the model did not choose, so it would be a limit on the
    wrong thing.
    """
    limits = Budget()
    assert Planner().max_steps > limits.max_iterations + 2


def test_every_default_is_still_overridable_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An operator can put the numbers back, or set their own."""
    monkeypatch.setenv(AGENT_MAX_TOKENS_ENV, "9000")
    monkeypatch.setenv(AGENT_MAX_ITERATIONS_ENV, "3")
    monkeypatch.setenv(AGENT_MAX_SECONDS_ENV, "7.5")
    monkeypatch.setenv(AGENT_MAX_STEPS_ENV, "25")

    assert budget_from_env() == Budget(max_tokens=9000, max_iterations=3, max_seconds=7.5)
    assert max_steps_from_env() == 25


def test_no_variable_means_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        AGENT_MAX_TOKENS_ENV,
        AGENT_MAX_ITERATIONS_ENV,
        AGENT_MAX_SECONDS_ENV,
        AGENT_MAX_STEPS_ENV,
    ):
        monkeypatch.delenv(name, raising=False)

    assert budget_from_env() == Budget()
    assert max_steps_from_env() == DEFAULT_MAX_STEPS
