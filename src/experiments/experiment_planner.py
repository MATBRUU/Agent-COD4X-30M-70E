"""Plan local experiments from Reality Engine assumptions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .experiment_tracker import add_or_update_experiment, load_experiment_memory, save_experiment_memory, utc_now


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSUMPTIONS_PATH = ROOT / "memory" / "reality" / "assumptions.json"
DEFAULT_EVIDENCE_PATH = ROOT / "memory" / "reality" / "evidence.json"
DEFAULT_EXPERIMENTS_PATH = ROOT / "memory" / "experiments" / "experiments.json"

IMPORTANCE_SCORE = {
    "critical": 10,
    "high": 8,
    "medium": 5,
    "low": 2,
}


def generate_and_store_experiments(
    assumptions_path: str | Path = DEFAULT_ASSUMPTIONS_PATH,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
    experiments_path: str | Path = DEFAULT_EXPERIMENTS_PATH,
) -> dict[str, Any]:
    assumptions = load_json(assumptions_path, {"assumptions": []}).get("assumptions", [])
    evidence = load_json(evidence_path, {"evidence": []}).get("evidence", [])
    planned = plan_experiments(assumptions, evidence)
    for experiment in planned:
        add_or_update_experiment(experiment, experiments_path)

    memory = load_experiment_memory(experiments_path)
    experiments = prioritize_experiments(memory.get("experiments", []), assumptions, evidence)
    memory["experiments"] = experiments
    memory["version"] = 1
    memory["source_policy"] = "local_only"
    save_experiment_memory(memory, experiments_path)
    return memory


def plan_experiments(
    assumptions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_assumption = index_evidence(evidence)
    experiments = []
    for assumption in assumptions:
        if not should_generate_experiment(assumption):
            continue
        experiments.append(build_experiment(assumption, evidence_by_assumption.get(assumption.get("id"), [])))
    return prioritize_experiments(experiments, assumptions, evidence)


def prioritize_experiments(
    experiments: list[dict[str, Any]],
    assumptions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assumptions_by_id = {item.get("id"): item for item in assumptions}
    evidence_by_assumption = index_evidence(evidence)
    scored = []
    for experiment in experiments:
        assumption = assumptions_by_id.get(experiment.get("assumption_id"), {})
        evidence_count = len(evidence_by_assumption.get(experiment.get("assumption_id"), []))
        item = dict(experiment)
        priority_score, reasons = priority(experiment, assumption, evidence_count)
        item["priority_score"] = priority_score
        item["priority_reasons"] = reasons
        scored.append(item)
    return sorted(scored, key=lambda item: float(item.get("priority_score", 0)), reverse=True)


def build_experiment(assumption: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    hypothesis = str(assumption.get("hypothesis") or "Hypothese locale").strip()
    source_type = str(assumption.get("source_type") or "other")
    source_id = str(assumption.get("source_id") or "unknown")
    importance = str(assumption.get("importance") or "medium")
    effort = effort_for_assumption(assumption)

    return {
        "id": f"experiment-{assumption.get('id')}",
        "assumption_id": assumption.get("id"),
        "source_type": source_type,
        "source_id": source_id,
        "experiment_title": title_for(hypothesis),
        "objective": f"Verifier localement l'hypothese: {hypothesis}",
        "method": method_for(assumption, evidence),
        "expected_signal": expected_signal_for(assumption),
        "success_criteria": success_criteria_for(assumption),
        "failure_criteria": failure_criteria_for(assumption),
        "estimated_effort_hours": effort,
        "estimated_cost_eur": 0.0,
        "status": "planned",
        "result": "unknown",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "priority_score": 0.0,
        "priority_reasons": [
            f"importance={importance}",
            "preuve_absente" if not evidence else "preuve_deja_presente",
        ],
    }


def should_generate_experiment(assumption: dict[str, Any]) -> bool:
    status = str(assumption.get("status") or "unknown")
    importance = str(assumption.get("importance") or "medium")
    if status in {"validated", "invalidated"}:
        return False
    return importance == "critical" or status in {"unverified", "unknown", "weakened"}


def priority(
    experiment: dict[str, Any],
    assumption: dict[str, Any],
    evidence_count: int,
) -> tuple[float, list[str]]:
    importance = str(assumption.get("importance") or "medium")
    status = str(assumption.get("status") or "unknown")
    effort = float(experiment.get("estimated_effort_hours", 1.0))
    cost = float(experiment.get("estimated_cost_eur", 0.0))
    source_type = str(assumption.get("source_type") or "other")

    score = IMPORTANCE_SCORE.get(importance, 5) * 0.34
    score += status_component(status) * 0.24
    score += (10 if evidence_count == 0 else 3) * 0.18
    score += effort_component(effort) * 0.12
    score += cost_component(cost) * 0.04
    score += decision_impact_component(source_type, importance) * 0.08

    reasons = []
    if importance == "critical":
        reasons.append("hypothese_critique")
    if status in {"unverified", "unknown"}:
        reasons.append("non_verifiee")
    if status == "weakened":
        reasons.append("fragilisee")
    if evidence_count == 0:
        reasons.append("aucune_preuve_locale")
    if effort <= 1.5:
        reasons.append("test_rapide")
    if cost <= 0:
        reasons.append("cout_zero")
    if source_type in {"thesis", "opportunity"}:
        reasons.append("impact_decision")

    return round(max(0.0, min(10.0, score)), 2), reasons


def method_for(assumption: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    hypothesis = str(assumption.get("hypothesis") or "").lower()
    source_type = str(assumption.get("source_type") or "other")
    if "revenu" in hypothesis or "potentiel" in hypothesis:
        return (
            "Comparer l'estimation a la memoire locale: outcomes, cout reel, effort reel et revenu reel. "
            "Noter si une preuve locale soutient ou affaiblit l'hypothese."
        )
    if "temps humain" in hypothesis or "cout d'opportunite" in hypothesis:
        return (
            "Faire un test de cadrage de 30 minutes: decomposer la tache en blocs, estimer le temps reel "
            "et verifier si le test reste faisable sans action externe."
        )
    if source_type == "thesis":
        return (
            "Relire la these, isoler le passage lie a l'hypothese, puis produire une note locale avec "
            "un signal observable, une contradiction possible et une decision humaine proposee."
        )
    if evidence:
        return "Relire les preuves locales existantes, puis ajouter une observation complementaire si le signal reste faible."
    return "Effectuer une revue humaine locale et documenter le signal observe dans une note courte."


def expected_signal_for(assumption: dict[str, Any]) -> str:
    hypothesis = str(assumption.get("hypothesis") or "").lower()
    if "revenu" in hypothesis or "potentiel" in hypothesis:
        return "Un signal local mesurable relie a un revenu, un cout, un effort ou une intention humaine."
    if "temps humain" in hypothesis or "cout d'opportunite" in hypothesis:
        return "Une estimation de temps plus fiable que l'hypothese initiale."
    if "roblox" in hypothesis:
        return "Un signal local montrant si la proposition Roblox est differenciante ou trop bruyante."
    return "Une observation locale qui soutient ou contredit clairement l'hypothese."


def success_criteria_for(assumption: dict[str, Any]) -> str:
    importance = str(assumption.get("importance") or "medium")
    if importance == "critical":
        return "Une preuve locale medium ou strong permet de reduire l'incertitude critique."
    return "Une preuve locale clarifie si l'hypothese doit rester supportee, affaiblie ou invalidee."


def failure_criteria_for(assumption: dict[str, Any]) -> str:
    if str(assumption.get("importance") or "") == "critical":
        return "Aucun signal clair n'est trouve, ou le signal contredit l'hypothese critique."
    return "Le test ne produit aucun signal exploitable ou revele une contradiction forte."


def title_for(hypothesis: str) -> str:
    clean = " ".join(hypothesis.replace(":", " ").split())
    return f"Tester: {clean[:72]}"


def effort_for_assumption(assumption: dict[str, Any]) -> float:
    importance = str(assumption.get("importance") or "medium")
    source_type = str(assumption.get("source_type") or "other")
    effort = {
        "critical": 1.5,
        "high": 1.0,
        "medium": 0.75,
        "low": 0.5,
    }.get(importance, 1.0)
    if source_type in {"roblox_concept", "roblox_spec"}:
        effort += 0.5
    return round(effort, 2)


def status_component(status: str) -> int:
    return {
        "unverified": 10,
        "unknown": 10,
        "weakened": 8,
        "supported": 3,
        "validated": 0,
        "invalidated": 0,
    }.get(status, 5)


def effort_component(hours: float) -> float:
    if hours <= 0.5:
        return 10.0
    if hours >= 8:
        return 1.0
    return round(10 - hours, 2)


def cost_component(cost: float) -> float:
    if cost <= 0:
        return 10.0
    if cost >= 100:
        return 1.0
    return round(10 - cost / 12, 2)


def decision_impact_component(source_type: str, importance: str) -> int:
    if source_type in {"thesis", "opportunity"} and importance == "critical":
        return 10
    if source_type in {"thesis", "opportunity"}:
        return 8
    return 5


def index_evidence(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in evidence:
        grouped.setdefault(str(record.get("assumption_id", "")), []).append(record)
    return grouped


def load_json(path: str | Path, default: dict[str, Any]) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        return default
    return json.loads(json_path.read_text(encoding="utf-8"))
