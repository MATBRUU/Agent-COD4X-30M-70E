"""Local learning report generation for COD4X."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .outcome_tracker import DEFAULT_OUTCOMES_PATH, load_outcome_memory, utc_now


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEARNING_REPORT_PATH = ROOT / "memory" / "learning" / "learning_report.json"


def load_learning_report(path: str | Path = DEFAULT_LEARNING_REPORT_PATH) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return empty_learning_report()
    return json.loads(report_path.read_text(encoding="utf-8"))


def save_learning_report(payload: dict[str, Any], path: str | Path = DEFAULT_LEARNING_REPORT_PATH) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = report_path.with_suffix(report_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(report_path)


def generate_learning_report(
    outcomes_path: str | Path = DEFAULT_OUTCOMES_PATH,
    decisions: list[dict[str, Any]] | None = None,
    report_path: str | Path = DEFAULT_LEARNING_REPORT_PATH,
) -> dict[str, Any]:
    outcomes = load_outcome_memory(outcomes_path).get("outcomes", [])
    decisions = decisions or []
    comparisons = [compare_outcome(outcome, decisions) for outcome in outcomes]

    ideas_tracked = len(outcomes)
    known_results = [outcome for outcome in outcomes if outcome.get("result") != "unknown"]
    successes = [outcome for outcome in outcomes if outcome.get("result") == "success"]
    abandoned = [outcome for outcome in outcomes if outcome.get("status") == "abandoned"]
    failures = [outcome for outcome in outcomes if outcome.get("result") == "failure"]
    partials = [outcome for outcome in outcomes if outcome.get("result") == "partial"]

    revenue_total = round(sum(to_float(item.get("real_revenue_eur")) for item in outcomes), 2)
    cost_total = round(sum(to_float(item.get("real_cost_eur")) for item in outcomes), 2)
    effort_total = round(sum(to_float(item.get("real_effort_hours")) for item in outcomes), 2)
    scoring_errors = probable_scoring_errors(comparisons)

    report = {
        "generated_at": utc_now(),
        "ideas_tracked": ideas_tracked,
        "success_rate": rate(len(successes), len(known_results)),
        "abandon_rate": rate(len(abandoned), ideas_tracked),
        "success_count": len(successes),
        "failure_count": len(failures),
        "partial_count": len(partials),
        "abandoned_count": len(abandoned),
        "revenue_total_eur": revenue_total,
        "cost_total_eur": cost_total,
        "effort_total_hours": effort_total,
        "probable_scoring_errors": scoring_errors,
        "recommendations": recommendations(comparisons, revenue_total, cost_total, effort_total),
        "comparisons": comparisons,
    }
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": report,
    }
    save_learning_report(payload, report_path)
    return payload


def compare_outcome(outcome: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    decision = find_decision(outcome, decisions)
    initial_score = normalize_score(outcome.get("initial_score"))
    result = str(outcome.get("result", "unknown"))
    status = str(outcome.get("status", "not_started"))
    revenue = to_float(outcome.get("real_revenue_eur"))
    cost = to_float(outcome.get("real_cost_eur"))
    effort = to_float(outcome.get("real_effort_hours"))
    net_revenue = round(revenue - cost, 2)

    return {
        "outcome_id": outcome.get("id"),
        "source_type": outcome.get("source_type"),
        "source_id": outcome.get("source_id"),
        "title": outcome.get("title"),
        "initial_score": initial_score,
        "human_decision": decision.get("decision", "unknown") if decision else "unknown",
        "result": result,
        "status": status,
        "real_effort_hours": effort,
        "real_cost_eur": cost,
        "real_revenue_eur": revenue,
        "net_revenue_eur": net_revenue,
        "learning_signal": learning_signal(initial_score, result, status, net_revenue, effort),
    }


def find_decision(outcome: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    source_id = str(outcome.get("source_id", ""))
    matches = [decision for decision in decisions if str(decision.get("action_id", "")) == source_id]
    if matches:
        return matches[-1]
    title = str(outcome.get("title", "")).lower()
    if title:
        title_matches = [
            decision
            for decision in decisions
            if str(decision.get("action_title", "")).lower() == title
        ]
        if title_matches:
            return title_matches[-1]
    return None


def probable_scoring_errors(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors = []
    for item in comparisons:
        score = float(item.get("initial_score", 0))
        result = item.get("result")
        status = item.get("status")
        if score >= 8 and (result == "failure" or status == "abandoned"):
            errors.append({**item, "error_type": "high_score_bad_outcome"})
        elif 0 < score <= 5 and result == "success":
            errors.append({**item, "error_type": "low_score_good_outcome"})
        elif score >= 8 and item.get("net_revenue_eur", 0) < 0 and result != "success":
            errors.append({**item, "error_type": "high_score_negative_net"})
    return errors


def recommendations(
    comparisons: list[dict[str, Any]],
    revenue_total: float,
    cost_total: float,
    effort_total: float,
) -> list[str]:
    if not comparisons:
        return ["Commencer par enregistrer les resultats reels des actions et concepts suivis."]

    recs = []
    errors = probable_scoring_errors(comparisons)
    if errors:
        recs.append("Revoir les poids de scoring pour les idees avec score eleve mais resultat faible.")
    if cost_total > revenue_total:
        recs.append("Penaliser davantage les couts reels dans les prochains scores.")
    if effort_total > 0:
        high_effort_failures = [
            item
            for item in comparisons
            if item.get("result") in {"failure", "partial"} and float(item.get("real_effort_hours", 0)) >= 5
        ]
        if high_effort_failures:
            recs.append("Augmenter la penalite de difficulte ou de delai pour les idees longues a valider.")
    if not recs:
        recs.append("Continuer a suivre les resultats pour confirmer les signaux avant d'automatiser.")
    recs.append("Maintenir la validation humaine avant toute action externe.")
    return recs


def learning_signal(
    initial_score: float,
    result: str,
    status: str,
    net_revenue: float,
    effort: float,
) -> str:
    if result == "success" and net_revenue >= 0:
        return "score_supported"
    if initial_score >= 8 and (result == "failure" or status == "abandoned"):
        return "score_too_optimistic"
    if initial_score <= 5 and result == "success":
        return "score_too_pessimistic"
    if effort >= 5 and result in {"failure", "partial"}:
        return "effort_underestimated"
    return "needs_more_data"


def empty_learning_report() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": {
            "generated_at": utc_now(),
            "ideas_tracked": 0,
            "success_rate": 0.0,
            "abandon_rate": 0.0,
            "revenue_total_eur": 0.0,
            "cost_total_eur": 0.0,
            "effort_total_hours": 0.0,
            "probable_scoring_errors": [],
            "recommendations": [
                "Enregistrer des resultats reels pour activer la boucle d'apprentissage."
            ],
            "comparisons": [],
        },
    }


def normalize_score(value: Any) -> float:
    score = to_float(value)
    if score > 10:
        return round(score / 10, 1)
    return round(score, 1)


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 3)
