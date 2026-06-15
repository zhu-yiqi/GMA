"""Evaluation result models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""

    name: str
    passed: bool
    score: float  # 0.0–1.0
    reason: str
    weight: float = 1.0

    def __post_init__(self):
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")
        if self.weight < 0:
            raise ValueError(f"weight must be non-negative, got {self.weight}")


@dataclass
class EvalResult:
    """Aggregated evaluation result for a task."""

    score: float  # 0.0–1.0
    criterion_results: list[CriterionResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score >= 1.0

    @property
    def summary(self) -> str:
        """Human-readable summary of all criteria."""
        if not self.criterion_results:
            return f"score={self.score:.2f} (no criteria)"
        lines = [f"score={self.score:.2f}"]
        for cr in self.criterion_results:
            status = "PASS" if cr.passed else "FAIL"
            lines.append(f"  [{status}] {cr.name} ({cr.score:.2f}, w={cr.weight}): {cr.reason}")
        return "\n".join(lines)


def aggregate_results(results: list[CriterionResult]) -> EvalResult:
    """Aggregate criterion results into an EvalResult using weighted average."""
    if not results:
        return EvalResult(score=0.0)
    total_weight = sum(r.weight for r in results)
    if total_weight == 0:
        return EvalResult(score=0.0, criterion_results=results)
    weighted_score = sum(r.score * r.weight for r in results) / total_weight
    return EvalResult(score=weighted_score, criterion_results=results)
