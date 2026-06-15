"""Composable evaluation framework."""

from gma.evaluation.checks import (
    AnswerContains,
    AnswerEquals,
    AnswerMatches,
    AssetDeleted,
    AssetExists,
    AssetMissing,
    AssetModified,
    asset_deleted,
    asset_exists,
    asset_missing,
    asset_modified,
    asset_probe,
)
from gma.evaluation.criteria import All, Any, Criterion
from gma.evaluation.result import CriterionResult, EvalResult, aggregate_results

__all__ = [
    "Criterion",
    "All",
    "Any",
    "AssetExists",
    "AssetMissing",
    "AssetModified",
    "AssetDeleted",
    "AnswerEquals",
    "AnswerContains",
    "AnswerMatches",
    "asset_probe",
    "asset_exists",
    "asset_missing",
    "asset_modified",
    "asset_deleted",
    "CriterionResult",
    "EvalResult",
    "aggregate_results",
]
