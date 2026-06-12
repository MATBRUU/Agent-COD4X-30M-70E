"""Build detailed COD4X strategic recommendations."""

from __future__ import annotations

from typing import Any


def build_recommendation(report: dict[str, Any]) -> dict[str, Any]:
    top = report.get("top_opportunity")
    decision = str(report.get("proposed_decision", "wait"))

    if not top:
        return {
            "decision": "wait",
            "confidence_percent": 0,
            "justification": "Aucune opportunite retenue par le comite V1.2.",
            "human_next_steps": [
                "Generer un rapport comite avant de produire une these.",
                "Verifier que des opportunites existent dans les memoires locales.",
            ],
        }

    confidence = recommendation_confidence(top, decision)
    return {
        "decision": decision,
        "confidence_percent": confidence,
        "justification": detailed_justification(top, decision),
        "human_next_steps": report.get("recommended_human_actions", []),
    }


def recommendation_confidence(top: dict[str, Any], decision: str) -> int:
    base = int(top.get("confidence_percent", 50))
    selection_score = float(top.get("selection_score", 0))
    risk = int(top.get("risk_level", 5))

    if decision == "pursue":
        base += 5
    if selection_score >= 9:
        base += 5
    if risk <= 3:
        base += 5
    if float(top.get("estimated_effort_hours", 0)) >= 24:
        base -= 10
    return max(30, min(95, base))


def detailed_justification(top: dict[str, Any], decision: str) -> str:
    if decision == "pursue":
        prefix = "Le rapport effort / potentiel est superieur aux autres opportunites disponibles."
    elif decision == "watch":
        prefix = "L'opportunite est prometteuse, mais demande plus de preuves avant engagement."
    elif decision == "reject":
        prefix = "L'opportunite ne justifie pas le temps humain disponible actuellement."
    else:
        prefix = "Les donnees disponibles ne justifient pas encore une action prioritaire."

    return (
        f"{prefix} Score de selection: {top.get('selection_score')}/10, "
        f"conviction: {top.get('confidence_percent')}%, "
        f"effort estime: {top.get('estimated_effort_hours')} heure(s), "
        f"cout estime: {top.get('estimated_cost_eur')} EUR, "
        f"risque: {top.get('risk_level')}/10."
    )
