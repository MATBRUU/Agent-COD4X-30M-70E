"""Generate score rationales for COD4X scored ideas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .outcome_tracker import utc_now


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RATIONALES_PATH = ROOT / "memory" / "learning" / "score_rationales.json"


def load_rationale_memory(path: str | Path = DEFAULT_RATIONALES_PATH) -> dict[str, Any]:
    rationale_path = Path(path)
    if not rationale_path.exists():
        return empty_rationale_memory()
    return json.loads(rationale_path.read_text(encoding="utf-8"))


def save_rationale_memory(payload: dict[str, Any], path: str | Path = DEFAULT_RATIONALES_PATH) -> None:
    rationale_path = Path(path)
    rationale_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = rationale_path.with_suffix(rationale_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(rationale_path)


def generate_and_store_rationales(
    sources: list[dict[str, Any]],
    path: str | Path = DEFAULT_RATIONALES_PATH,
) -> dict[str, Any]:
    rationales = [generate_rationale(source) for source in sources]
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "rationales": rationales,
    }
    save_rationale_memory(payload, path)
    return payload


def generate_rationale(source: dict[str, Any]) -> dict[str, Any]:
    source_type = str(source.get("source_type") or infer_source_type(source))
    source_id = str(source.get("id") or source.get("source_id") or "unknown")
    score = normalize_score(source.get("score", source.get("score_final", 0)))
    positive_factors = build_positive_factors(source, source_type)
    negative_factors = build_negative_factors(source, source_type)
    assumptions = build_assumptions(source, source_type)
    risk_notes = build_risk_notes(source, source_type)
    confidence = confidence_percent(source, positive_factors, negative_factors)

    return {
        "source_id": source_id,
        "source_type": source_type,
        "title": source.get("title") or source.get("nom") or source_id,
        "score": score,
        "confidence_percent": confidence,
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "assumptions": assumptions,
        "risk_notes": risk_notes,
        "recommendation": recommendation(score),
        "generated_at": utc_now(),
    }


def collect_scored_sources(
    actions: list[dict[str, Any]] | None = None,
    roblox_concepts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for action in actions or []:
        item = dict(action)
        item["source_type"] = "action"
        sources.append(item)
    for concept in roblox_concepts or []:
        item = dict(concept)
        item["source_type"] = "roblox_concept"
        sources.append(item)
    return sources


def empty_rationale_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "rationales": [],
    }


def infer_source_type(source: dict[str, Any]) -> str:
    source_id = str(source.get("id", ""))
    if source_id.startswith("roblox-"):
        return "roblox_concept"
    return "action"


def normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 10:
        return round(score / 10, 1)
    return round(score, 1)


def build_positive_factors(source: dict[str, Any], source_type: str) -> list[str]:
    if source_type == "roblox_concept":
        inputs = source.get("score_inputs", {})
        factors = []
        if int(inputs.get("viral_potential", 0)) >= 8:
            factors.append("Potentiel viral eleve.")
        if int(inputs.get("monetization_potential", 0)) >= 8:
            factors.append("Potentiel de monetisation solide.")
        if float(source.get("score", 0)) > 8:
            factors.append("Concept conserve au-dessus du seuil de 8/10.")
        return factors or ["Concept suffisamment structure pour etre surveille."]

    estimates = source.get("estimates", {})
    factors = []
    if int(estimates.get("impact", 0)) >= 4:
        factors.append("Impact attendu eleve.")
    if int(estimates.get("risk", 5)) <= 2:
        factors.append("Risque estime bas.")
    if int(estimates.get("cost", 5)) <= 2:
        factors.append("Cout estime bas.")
    if int(estimates.get("delay", 5)) <= 2:
        factors.append("Delai court.")
    return factors or ["Action lisible et compatible avec une evaluation locale."]


def build_negative_factors(source: dict[str, Any], source_type: str) -> list[str]:
    if source_type == "roblox_concept":
        inputs = source.get("score_inputs", {})
        factors = []
        if int(inputs.get("development_difficulty", 0)) >= 6:
            factors.append("Difficulte de developpement elevee.")
        if int(inputs.get("competition", 0)) >= 6:
            factors.append("Concurrence elevee.")
        return factors or ["Peu de facteurs negatifs visibles dans les donnees locales."]

    estimates = source.get("estimates", {})
    factors = []
    if int(estimates.get("risk", 0)) >= 4:
        factors.append("Risque estime eleve.")
    if int(estimates.get("cost", 0)) >= 4:
        factors.append("Cout estime eleve.")
    if int(estimates.get("delay", 0)) >= 4:
        factors.append("Delai estime long.")
    return factors or ["Peu de facteurs negatifs visibles dans les donnees locales."]


def build_assumptions(source: dict[str, Any], source_type: str) -> list[str]:
    assumptions = [
        "Les donnees utilisees sont locales et peuvent etre incompletes.",
        "Aucune action externe n'est executee automatiquement.",
    ]
    if source_type == "roblox_concept":
        assumptions.append("Le score Roblox depend des tendances enregistrees manuellement.")
    else:
        assumptions.append("Le score de l'action depend des estimations impact, risque, cout et delai.")
    return assumptions


def build_risk_notes(source: dict[str, Any], source_type: str) -> list[str]:
    notes = []
    if source.get("external_action_required"):
        notes.append("Une action externe serait necessaire et doit rester bloquee sans validation humaine.")
    constraints = source.get("constraints", [])
    if constraints:
        notes.append(f"Contraintes declarees : {', '.join(str(item) for item in constraints)}.")
    if source_type == "roblox_concept":
        notes.append("Pas de publication Roblox, pas d'API Roblox et pas de paiement en V1.1.")
    return notes or ["Aucun risque bloquant detecte dans la memoire locale."]


def confidence_percent(source: dict[str, Any], positive: list[str], negative: list[str]) -> int:
    base = 55 + len(positive) * 8 - max(0, len(negative) - 1) * 5
    if source.get("score_inputs") or source.get("estimates"):
        base += 10
    if source.get("success_metric") or source.get("validation_steps"):
        base += 5
    return max(30, min(90, base))


def recommendation(score: float) -> str:
    if score >= 8.0:
        return "pursue"
    if score >= 6.0:
        return "watch"
    return "reject"
