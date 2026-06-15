"""Composable evaluation criteria framework.

Tasks define evaluation logic by returning a list of ``Criterion`` objects from
their ``criteria()`` method.  The framework evaluates each criterion and
aggregates the results automatically.

Combinators ``All`` and ``Any`` let you compose criteria into trees::

    All(
        SMSSent(to="+1505...", contains="OK", weight=0.3),
        CalendarEventExists(date="2025-10-17", start_hour=11, weight=0.7),
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from gma.evaluation.result import CriterionResult, EvalResult, aggregate_results


class Criterion(ABC):
    """Base class for a single evaluation check.

    Subclasses must implement ``evaluate()``.  The ``weight`` attribute controls
    how this criterion contributes to the aggregate score when used alongside
    other criteria.
    """

    def __init__(self, *, weight: float = 1.0):
        self.weight = weight

    @property
    def name(self) -> str:
        """Human-readable name, defaults to the class name."""
        return self.__class__.__name__

    @abstractmethod
    def evaluate(self, controller) -> CriterionResult:
        """Evaluate this criterion against the current device state.

        Args:
            controller: An ``AndroidController`` instance for querying device
                state (ADB, screenshots, databases, etc.).

        Returns:
            A ``CriterionResult`` with pass/fail, score, and reason.
        """
        ...

    def _pass(self, reason: str = "passed") -> CriterionResult:
        """Convenience: create a passing result."""
        return CriterionResult(
            name=self.name, passed=True, score=1.0, reason=reason, weight=self.weight
        )

    def _fail(self, reason: str) -> CriterionResult:
        """Convenience: create a failing result."""
        return CriterionResult(
            name=self.name, passed=False, score=0.0, reason=reason, weight=self.weight
        )

    def _partial(self, score: float, reason: str) -> CriterionResult:
        """Convenience: create a partial-score result."""
        return CriterionResult(
            name=self.name,
            passed=score >= 1.0,
            score=score,
            reason=reason,
            weight=self.weight,
        )


class All(Criterion):
    """All sub-criteria must pass.  Score = weighted average of sub-scores."""

    def __init__(self, *criteria: Criterion, weight: float = 1.0):
        super().__init__(weight=weight)
        if not criteria:
            raise ValueError("All() requires at least one criterion")
        self.criteria = list(criteria)

    @property
    def name(self) -> str:
        names = ", ".join(c.name for c in self.criteria)
        return f"All({names})"

    def evaluate(self, controller) -> CriterionResult:
        results = [c.evaluate(controller) for c in self.criteria]
        agg = aggregate_results(results)
        all_passed = all(r.passed for r in results)
        return CriterionResult(
            name=self.name,
            passed=all_passed,
            score=agg.score,
            reason=agg.summary,
            weight=self.weight,
        )


class Any(Criterion):
    """At least one sub-criterion must pass.  Score = max sub-score."""

    def __init__(self, *criteria: Criterion, weight: float = 1.0):
        super().__init__(weight=weight)
        if not criteria:
            raise ValueError("Any() requires at least one criterion")
        self.criteria = list(criteria)

    @property
    def name(self) -> str:
        names = ", ".join(c.name for c in self.criteria)
        return f"Any({names})"

    def evaluate(self, controller) -> CriterionResult:
        results = [c.evaluate(controller) for c in self.criteria]
        best = max(results, key=lambda r: r.score)
        any_passed = any(r.passed for r in results)
        return CriterionResult(
            name=self.name,
            passed=any_passed,
            score=best.score,
            reason=best.reason,
            weight=self.weight,
        )
