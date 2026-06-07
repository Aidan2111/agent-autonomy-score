"""Autonomy scoring for feedback-driven coding agent pipelines."""

from .scoring import (
    GateResult,
    IntentScoreResult,
    ScoreResult,
    combine_intent_and_diff,
    score_change,
    score_intent,
)

__all__ = [
    "GateResult",
    "IntentScoreResult",
    "ScoreResult",
    "combine_intent_and_diff",
    "score_change",
    "score_intent",
]
__version__ = "0.2.0"
