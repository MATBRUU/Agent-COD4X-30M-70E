"""Strategic opportunity selection for COD4X."""

from __future__ import annotations

from typing import Any

from .opportunity_collector import utc_now


def select_opportunities(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    """Select one strategic opportunity from already existing opportunities."""
    analyzed = [score_selection(item) for item in opportunities]
    blocked = [item for item in analyzed if is_blocked(item)]
    eligible = [item for item in analyzed if not is_blocked(item)]

    ranked = sorted(eligible, key=lambda item: float(item.get("selection_score", 0)), reverse=True)
    top = ranked[0] if ranked else None
    watchlist = [item for item in ranked[1:] if should_watch(item)]
    rejected_pool = [item for item in ranked[1:] if item not in watchlist]

    return {
        "generated_at": utc_now(),
        "opportunities_analyzed": len(opportunities),
        "top_opportunity": top,
        "alternatives_rejected": [
            with_rejection_reason(item, top)
            for item in rejected_pool
        ],
        "watchlist": [
            with_watch_reason(item)
            for item in watchlist
        ],
        "blocked_opportunities": [
            with_block_reason(item)
            for item in blocked
        ],
    }


def score_selection(opportunity: dict[str, Any]) -> dict[str, Any]:
    score = float(opportunity.get("score", 0))
    confidence = float(opportunity.get("confidence_percent", 50)) / 10
    risk_inverse = 11 - float(opportunity.get("risk_level", 5))
    strategic_fit = float(opportunity.get("strategic_fit", 5))
    revenue = revenue_component(float(opportunity.get("estimated_revenue_potential", 0)))
    effort_inverse = effort_component(float(opportunity.get("estimated_effort_hours", 0)))
    cost_inverse = cost_component(float(opportunity.get("estimated_cost_eur", 0)))
    history = history_adjustment(opportunity)

    selection_score = (
        score * 0.28
        + confidence * 0.15
        + risk_inverse * 0.16
        + strategic_fit * 0.16
        + revenue * 0.10
        + effort_inverse * 0.08
        + cost_inverse * 0.07
        + history
    )

    selected = dict(opportunity)
    selected["selection_score"] = round(max(0.0, min(10.0, selection_score)), 2)
    selected["selection_factors"] = {
        "score_initial": score,
        "conviction": round(confidence, 1),
        "risk_inverse": round(risk_inverse, 1),
        "strategic_fit": round(strategic_fit, 1),
        "revenue_component": round(revenue, 1),
        "effort_component": round(effort_inverse, 1),
        "cost_component": round(cost_inverse, 1),
        "history_adjustment": round(history, 1),
    }
    return selected


def is_blocked(opportunity: dict[str, Any]) -> bool:
    if opportunity.get("external_execution"):
        return True
    if opportunity.get("requires_human_validation") is False:
        return True
    if opportunity.get("outcome_status") in {"completed", "abandoned"}:
        return True
    if opportunity.get("outcome_result") in {"success", "failure"}:
        return True
    return False


def should_watch(opportunity: dict[str, Any]) -> bool:
    selection_score = float(opportunity.get("selection_score", 0))
    if 6.0 <= selection_score < 7.5:
        return True
    if float(opportunity.get("risk_level", 0)) >= 7:
        return True
    if float(opportunity.get("estimated_effort_hours", 0)) >= 48:
        return True
    return False


def with_rejection_reason(opportunity: dict[str, Any], top: dict[str, Any] | None) -> dict[str, Any]:
    item = dict(opportunity)
    reasons = []
    if top:
        delta = float(top.get("selection_score", 0)) - float(opportunity.get("selection_score", 0))
        reasons.append(f"Score de selection inferieur de {round(delta, 2)} point(s) a l'opportunite retenue.")
    if float(opportunity.get("risk_level", 0)) > 6:
        reasons.append("Risque trop eleve pour devenir la priorite principale.")
    if float(opportunity.get("estimated_effort_hours", 0)) > 40:
        reasons.append("Effort estime trop important pour la priorite unique actuelle.")
    if not reasons:
        reasons.append("Bonne opportunite, mais moins prioritaire que le top actuel.")
    item["rejection_reason"] = reasons
    return item


def with_watch_reason(opportunity: dict[str, Any]) -> dict[str, Any]:
    item = dict(opportunity)
    reasons = []
    if 6 <= float(opportunity.get("selection_score", 0)) < 7.5:
        reasons.append("Score intermediaire : interessant, mais pas assez fort pour etre prioritaire.")
    if float(opportunity.get("risk_level", 0)) >= 7:
        reasons.append("Risque eleve a clarifier avant engagement.")
    if float(opportunity.get("estimated_effort_hours", 0)) >= 48:
        reasons.append("Effort eleve : attendre plus de preuves ou reduire le scope.")
    item["watch_reason"] = reasons or ["A garder en reserve."]
    return item


def with_block_reason(opportunity: dict[str, Any]) -> dict[str, Any]:
    item = dict(opportunity)
    reasons = []
    if opportunity.get("external_execution"):
        reasons.append("Execution externe requise, bloquee par les garde-fous.")
    if opportunity.get("requires_human_validation") is False:
        reasons.append("Validation humaine non declaree.")
    if opportunity.get("outcome_status") == "completed":
        reasons.append("Opportunite deja terminee.")
    if opportunity.get("outcome_status") == "abandoned":
        reasons.append("Opportunite deja abandonnee.")
    if opportunity.get("outcome_result") == "success":
        reasons.append("Resultat deja marque comme succes.")
    if opportunity.get("outcome_result") == "failure":
        reasons.append("Resultat deja marque comme echec.")
    item["block_reason"] = reasons or ["Bloquee par une contrainte locale."]
    return item


def revenue_component(value: float) -> float:
    if value <= 0:
        return 0.0
    if value >= 2000:
        return 10.0
    return round(value / 200, 2)


def effort_component(hours: float) -> float:
    if hours <= 0:
        return 5.0
    if hours <= 5:
        return 10.0
    if hours >= 80:
        return 1.0
    return round(10 - (hours / 10), 2)


def cost_component(cost: float) -> float:
    if cost <= 0:
        return 10.0
    if cost >= 500:
        return 1.0
    return round(10 - (cost / 55), 2)


def history_adjustment(opportunity: dict[str, Any]) -> float:
    result = opportunity.get("outcome_result")
    status = opportunity.get("outcome_status")
    if result == "partial":
        return 0.2
    if status == "in_progress":
        return -0.2
    if status == "abandoned" or result == "failure":
        return -2.0
    if result == "success":
        return -1.0
    return 0.0
