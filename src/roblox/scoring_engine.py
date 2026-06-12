"""Scoring engine for local Roblox game concepts."""

from __future__ import annotations

from typing import Any


SCORE_THRESHOLD = 8.0
SCORING_FIELDS = (
    "viral_potential",
    "monetization_potential",
    "development_difficulty",
    "competition",
)


def clamp_rating(value: Any, default: int = 5) -> int:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        rating = default
    return max(1, min(10, rating))


def score_concept(concept: dict[str, Any]) -> dict[str, Any]:
    """Score one concept on a 1-10 scale.

    Viral and monetization potential are positive. Development difficulty and
    competition are inverted because lower values are better for an MVP.
    """
    inputs = concept.get("score_inputs", {})
    viral = clamp_rating(inputs.get("viral_potential"), default=6)
    monetization = clamp_rating(inputs.get("monetization_potential"), default=6)
    difficulty = clamp_rating(inputs.get("development_difficulty"), default=5)
    competition = clamp_rating(inputs.get("competition"), default=5)

    score = (
        viral * 0.35
        + monetization * 0.30
        + (11 - difficulty) * 0.20
        + (11 - competition) * 0.15
    )

    scored = dict(concept)
    scored["score_inputs"] = {
        "viral_potential": viral,
        "monetization_potential": monetization,
        "development_difficulty": difficulty,
        "competition": competition,
    }
    scored["score"] = round(score, 1)
    scored["rating"] = rating_label(scored["score"])
    return scored


def score_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((score_concept(concept) for concept in concepts), key=lambda item: item["score"], reverse=True)


def keep_high_score_concepts(
    concepts: list[dict[str, Any]],
    threshold: float = SCORE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Keep only concepts strictly above the configured score threshold."""
    return [concept for concept in score_concepts(concepts) if float(concept["score"]) > threshold]


def average_score(concepts: list[dict[str, Any]]) -> float:
    if not concepts:
        return 0.0
    return round(sum(float(concept.get("score", 0)) for concept in concepts) / len(concepts), 1)


def rating_label(score: float) -> str:
    if score >= 9.0:
        return "elite"
    if score > SCORE_THRESHOLD:
        return "top"
    if score >= 7.0:
        return "watch"
    return "reject"
