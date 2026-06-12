"""Generate local strategic theses from COD4X committee reports."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .opportunity_comparator import compare_selection
from .recommendation_builder import build_recommendation


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THESES_PATH = ROOT / "memory" / "thesis" / "theses.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_thesis_memory(path: str | Path = DEFAULT_THESES_PATH) -> dict[str, Any]:
    theses_path = Path(path)
    if not theses_path.exists():
        return empty_thesis_memory()
    return json.loads(theses_path.read_text(encoding="utf-8"))


def save_thesis_memory(payload: dict[str, Any], path: str | Path = DEFAULT_THESES_PATH) -> None:
    theses_path = Path(path)
    theses_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = theses_path.with_name(f"{theses_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(theses_path)


def generate_and_store_thesis(
    committee_report: dict[str, Any],
    path: str | Path = DEFAULT_THESES_PATH,
) -> dict[str, Any]:
    thesis = generate_thesis(committee_report)
    if thesis.get("status") == "missing_selection":
        return thesis

    memory = load_thesis_memory(path)
    theses = memory.setdefault("theses", [])
    theses.append(thesis)
    memory["version"] = 1
    memory["source_policy"] = "local_only"
    save_thesis_memory(memory, path)
    return thesis


def generate_thesis(committee_report: dict[str, Any]) -> dict[str, Any]:
    report = committee_report.get("report", committee_report)
    top = report.get("top_opportunity")
    if not top:
        return {
            "status": "missing_selection",
            "message": "Aucune opportunite retenue. Lancez d'abord: python src/agent.py committee-report",
            "source_policy": "local_only",
            "external_execution": False,
        }

    selection = report.get("selection", {})
    alternative_comparisons = compare_selection(selection)
    recommendation = build_recommendation(report)
    counter_arguments = build_counter_arguments(top, alternative_comparisons)
    generated_at = utc_now()

    thesis = {
        "id": f"thesis-{safe_id(top.get('id'))}-{generated_at.replace(':', '').replace('-', '')}",
        "date": generated_at,
        "opportunity": top.get("title"),
        "selected_opportunity": top.get("title"),
        "selected_opportunity_id": top.get("id"),
        "source_type": top.get("source_type"),
        "score": top.get("score"),
        "selection_score": top.get("selection_score"),
        "conviction": top.get("confidence_percent"),
        "decision": recommendation.get("decision"),
        "summary": executive_summary(top, recommendation),
        "executive_summary": executive_summary(top, recommendation),
        "hypotheses_principales": report.get("assumptions", []),
        "advantages": advantages(top),
        "disadvantages": disadvantages(top),
        "risks": build_risks(top, report),
        "resources_required": resources_required(top),
        "estimated_time": top.get("estimated_effort_hours"),
        "estimated_cost": top.get("estimated_cost_eur"),
        "estimated_potential": top.get("estimated_revenue_potential"),
        "reasons": reasons_for_choice(top, report),
        "justification": recommendation.get("justification"),
        "recommendation": recommendation,
        "alternative_comparisons": alternative_comparisons,
        "counter_arguments": counter_arguments,
        "contre_arguments": counter_arguments,
        "failure_scenarios": failure_scenarios(top),
        "fragile_assumptions": fragile_assumptions(top, report),
        "anti_bias_question": "Pourquoi cette decision pourrait etre mauvaise ?",
        "guardrails": report.get("guardrails", []),
        "external_execution": False,
    }
    return thesis


def executive_summary(top: dict[str, Any], recommendation: dict[str, Any]) -> str:
    return (
        f"COD4X retient '{top.get('title')}' avec une decision {recommendation.get('decision')} "
        f"car son score de selection ({top.get('selection_score')}/10), sa conviction "
        f"({top.get('confidence_percent')}%) et son rapport effort / potentiel sont les plus favorables "
        "parmi les opportunites locales analysees."
    )


def advantages(top: dict[str, Any]) -> list[str]:
    items = [
        f"Score initial de {top.get('score')}/10.",
        f"Score de selection de {top.get('selection_score')}/10.",
        f"Conviction locale de {top.get('confidence_percent')}%.",
    ]
    if int(top.get("risk_level", 10)) <= 3:
        items.append("Risque estime faible.")
    if float(top.get("estimated_cost_eur", 0)) <= 0:
        items.append("Cout estime nul ou tres faible.")
    if float(top.get("estimated_revenue_potential", 0)) > 0:
        items.append("Potentiel estime documente.")
    return items


def disadvantages(top: dict[str, Any]) -> list[str]:
    items = []
    if float(top.get("estimated_effort_hours", 0)) > 8:
        items.append("Effort humain non trivial.")
    if top.get("source_type") == "roblox_concept":
        items.append("Depend d'une tendance Roblox locale qui peut etre incomplete.")
    if not top.get("outcome_result"):
        items.append("Pas encore de resultat reel enregistre pour confirmer le score.")
    return items or ["Peu d'inconvenients visibles dans les donnees locales."]


def build_risks(top: dict[str, Any], report: dict[str, Any]) -> list[str]:
    risks = list(report.get("principal_risks", []))
    if int(top.get("risk_level", 0)) >= 5:
        risks.append("Risque estime a surveiller avant tout engagement humain.")
    if top.get("external_execution"):
        risks.append("Execution externe requise, donc bloquee par les garde-fous.")
    if not risks:
        risks.append("Le risque principal est le manque de donnees de resultat reel.")
    return risks


def resources_required(top: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_time_hours": top.get("estimated_effort_hours"),
        "cost_eur": top.get("estimated_cost_eur"),
        "validation": "Validation humaine obligatoire avant toute action reelle.",
        "local_assets": top.get("metadata", {}),
    }


def reasons_for_choice(top: dict[str, Any], report: dict[str, Any]) -> list[str]:
    reasons = [
        report.get("choice_justification", ""),
        "L'opportunite retenue presente le meilleur compromis local entre score, conviction, risque, effort et potentiel.",
    ]
    if float(top.get("estimated_cost_eur", 0)) <= 0:
        reasons.append("Le cout estime est nul ou tres faible.")
    if int(top.get("strategic_fit", 0)) >= 8:
        reasons.append("La coherence strategique est forte.")
    return [reason for reason in reasons if reason]


def build_counter_arguments(top: dict[str, Any], alternatives: list[dict[str, Any]]) -> list[str]:
    counters = [
        "Le score repose sur des donnees locales et peut manquer de signaux externes.",
        "Le potentiel estime peut etre surevalue faute de revenu reel mesure.",
    ]
    if alternatives:
        close = [
            item for item in alternatives
            if item.get("selection_score") is not None
            and float(top.get("selection_score", 0)) - float(item.get("selection_score", 0)) < 0.5
        ]
        if close:
            counters.append("Certaines alternatives sont proches du top et pourraient devenir meilleures avec peu de nouvelles donnees.")
    if top.get("source_type") == "roblox_concept":
        counters.append("Une tendance Roblox locale peut etre bruyante ou deja trop concurrentielle.")
    return counters


def failure_scenarios(top: dict[str, Any]) -> list[str]:
    scenarios = [
        "Le temps humain disponible est insuffisant pour valider correctement l'opportunite.",
        "La promesse est claire sur le papier mais ne produit pas de signal reel.",
        "Une alternative moins bien classee se revele plus simple a concretiser.",
    ]
    if top.get("source_type") == "roblox_concept":
        scenarios.append("La boucle de jeu inspiree par la tendance ne se differencie pas assez.")
    return scenarios


def fragile_assumptions(top: dict[str, Any], report: dict[str, Any]) -> list[str]:
    assumptions = [
        "Le potentiel estime est un proxy, pas une preuve de revenu.",
        "La conviction depend de la qualite des scores precedents.",
    ]
    if not report.get("selection", {}).get("blocked_opportunities"):
        assumptions.append("L'absence d'opportunite bloquee ne signifie pas absence de risque.")
    if float(top.get("estimated_cost_eur", 0)) == 0:
        assumptions.append("Le cout estime a zero ignore possiblement le cout d'opportunite du temps humain.")
    return assumptions


def empty_thesis_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "theses": [],
    }


def safe_id(value: Any) -> str:
    text = str(value or "unknown")
    return "".join(char if char.isalnum() else "-" for char in text.lower()).strip("-") or "unknown"
