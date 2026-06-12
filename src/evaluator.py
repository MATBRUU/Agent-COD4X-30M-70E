"""Action scoring utilities for COD4X."""

from __future__ import annotations

from typing import Any


RUBRIC_FIELDS = ("impact", "risk", "cost", "delay")


def clamp_rating(value: Any, default: int = 3) -> int:
    """Return an integer rating between 1 and 5."""
    try:
        rating = int(value)
    except (TypeError, ValueError):
        rating = default
    return max(1, min(5, rating))


def score_action(action: dict[str, Any]) -> dict[str, Any]:
    """Score one action on a 0-100 scale.

    Impact is positive. Risk, cost and delay are inverted because lower is better.
    """
    estimates = action.get("estimates", {})
    impact = clamp_rating(estimates.get("impact"), default=3)
    risk = clamp_rating(estimates.get("risk"), default=3)
    cost = clamp_rating(estimates.get("cost"), default=3)
    delay = clamp_rating(estimates.get("delay"), default=3)

    weighted = (
        impact * 0.40
        + (6 - risk) * 0.25
        + (6 - cost) * 0.20
        + (6 - delay) * 0.15
    )
    score = round((weighted / 5) * 100)

    scored = dict(action)
    scored["estimates"] = {
        "impact": impact,
        "risk": risk,
        "cost": cost,
        "delay": delay,
    }
    scored["score"] = score
    scored["rating"] = rating_label(score)
    return scored


def score_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score and rank actions from highest to lowest score."""
    return sorted((score_action(action) for action in actions), key=lambda item: item["score"], reverse=True)


def rating_label(score: int) -> str:
    if score >= 80:
        return "priority"
    if score >= 65:
        return "strong"
    if score >= 50:
        return "watch"
    return "low"
