"""Compare selected COD4X opportunities against alternatives."""

from __future__ import annotations

from typing import Any


def compare_selection(selection: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare top opportunity with rejected, watchlisted and blocked alternatives."""
    top = selection.get("top_opportunity")
    comparisons: list[dict[str, Any]] = []

    for alternative in selection.get("alternatives_rejected", []):
        comparisons.append(compare_alternative(top, alternative, decision="rejected"))

    for alternative in selection.get("watchlist", []):
        comparisons.append(compare_alternative(top, alternative, decision="watch"))

    for alternative in selection.get("blocked_opportunities", []):
        comparisons.append(compare_alternative(top, alternative, decision="blocked"))

    return comparisons


def compare_alternative(
    top: dict[str, Any] | None,
    alternative: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    return {
        "id": alternative.get("id"),
        "title": alternative.get("title"),
        "source_type": alternative.get("source_type"),
        "decision": decision,
        "score": alternative.get("score"),
        "selection_score": alternative.get("selection_score"),
        "points_forts": strengths(alternative),
        "points_faibles": weaknesses(top, alternative),
        "raison_du_rejet": rejection_reason(alternative, decision),
    }


def strengths(opportunity: dict[str, Any]) -> list[str]:
    items = []
    if float(opportunity.get("score", 0)) >= 8:
        items.append("Score initial eleve.")
    if int(opportunity.get("confidence_percent", 0)) >= 75:
        items.append("Conviction locale forte.")
    if float(opportunity.get("estimated_cost_eur", 0)) <= 0:
        items.append("Cout estime nul ou tres faible.")
    if float(opportunity.get("estimated_revenue_potential", 0)) >= 1000:
        items.append("Potentiel estime important.")
    if int(opportunity.get("strategic_fit", 0)) >= 8:
        items.append("Bonne coherence avec la doctrine locale.")
    if int(opportunity.get("risk_level", 10)) <= 3:
        items.append("Risque estime faible.")
    return items or ["Atout specifique non documente dans les donnees locales."]


def weaknesses(top: dict[str, Any] | None, opportunity: dict[str, Any]) -> list[str]:
    items = []
    if top:
        delta = float(top.get("selection_score", 0)) - float(opportunity.get("selection_score", 0))
        if delta > 0:
            items.append(f"Score de selection inferieur de {round(delta, 2)} point(s) au top.")
    if int(opportunity.get("risk_level", 0)) >= 6:
        items.append("Risque superieur au niveau ideal.")
    if float(opportunity.get("estimated_effort_hours", 0)) >= 24:
        items.append("Effort humain estime important.")
    if int(opportunity.get("confidence_percent", 100)) < 75:
        items.append("Conviction plus faible que les meilleures opportunites.")
    if opportunity.get("external_execution"):
        items.append("Execution externe requise, donc bloquee.")
    return items or ["Moins prioritaire que l'opportunite retenue."]


def rejection_reason(opportunity: dict[str, Any], decision: str) -> list[str]:
    if decision == "rejected":
        return opportunity.get("rejection_reason", ["Rejetee au profit d'une opportunite plus forte."])
    if decision == "watch":
        return opportunity.get("watch_reason", ["A garder en surveillance, pas a poursuivre maintenant."])
    if decision == "blocked":
        return opportunity.get("block_reason", ["Bloquee par une contrainte locale."])
    return ["Decision non documentee."]
