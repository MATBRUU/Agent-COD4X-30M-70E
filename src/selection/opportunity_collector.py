"""Collect and normalize local COD4X opportunities."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPPORTUNITIES_PATH = ROOT / "memory" / "selection" / "opportunities.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: str | Path, default: dict[str, Any]) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        return default
    return json.loads(json_path.read_text(encoding="utf-8"))


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = json_path.with_name(f"{json_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(json_path)


def load_opportunity_memory(path: str | Path = DEFAULT_OPPORTUNITIES_PATH) -> dict[str, Any]:
    return load_json(path, empty_opportunity_memory())


def save_opportunity_memory(payload: dict[str, Any], path: str | Path = DEFAULT_OPPORTUNITIES_PATH) -> None:
    write_json_atomic(path, payload)


def collect_and_store_opportunities(
    state_path: str | Path,
    concepts_path: str | Path,
    specs_path: str | Path,
    outcomes_path: str | Path,
    rationales_path: str | Path,
    opportunities_path: str | Path = DEFAULT_OPPORTUNITIES_PATH,
) -> dict[str, Any]:
    opportunities = collect_opportunities(
        state_path=state_path,
        concepts_path=concepts_path,
        specs_path=specs_path,
        outcomes_path=outcomes_path,
        rationales_path=rationales_path,
    )
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "opportunities": opportunities,
    }
    save_opportunity_memory(payload, opportunities_path)
    return payload


def collect_opportunities(
    state_path: str | Path,
    concepts_path: str | Path,
    specs_path: str | Path,
    outcomes_path: str | Path,
    rationales_path: str | Path,
) -> list[dict[str, Any]]:
    state = load_json(state_path, {"last_plan": []})
    concepts_memory = load_json(concepts_path, {"concepts": []})
    specs_memory = load_json(specs_path, {"specs": []})
    outcomes_memory = load_json(outcomes_path, {"outcomes": []})
    rationales_memory = load_json(rationales_path, {"rationales": []})

    rationales = {
        str(rationale.get("source_id")): rationale
        for rationale in rationales_memory.get("rationales", [])
    }
    outcome_index = index_outcomes(outcomes_memory.get("outcomes", []))

    opportunities: dict[str, dict[str, Any]] = {}

    for action in state.get("last_plan", []):
        opportunity = normalize_action(action, rationales.get(str(action.get("id"))))
        merge_outcome(opportunity, outcome_index)
        opportunities[opportunity["id"]] = opportunity

    for concept in concepts_memory.get("concepts", []):
        opportunity = normalize_roblox_concept(concept, rationales.get(str(concept.get("id"))))
        merge_outcome(opportunity, outcome_index)
        opportunities[opportunity["id"]] = opportunity

    for spec in specs_memory.get("specs", []):
        opportunity = normalize_roblox_spec(spec)
        merge_outcome(opportunity, outcome_index)
        opportunities[opportunity["id"]] = opportunity

    for outcome in outcomes_memory.get("outcomes", []):
        source_id = str(outcome.get("source_id", ""))
        existing = opportunities.get(source_id)
        if existing:
            apply_outcome(existing, outcome)
            continue
        opportunity = normalize_outcome_opportunity(outcome)
        opportunities[opportunity["id"]] = opportunity

    return sorted(opportunities.values(), key=lambda item: float(item.get("score", 0)), reverse=True)


def normalize_action(action: dict[str, Any], rationale: dict[str, Any] | None) -> dict[str, Any]:
    estimates = action.get("estimates", {})
    score = normalize_score(action.get("score", 0))
    effort = float(action.get("context", {}).get("available_hours") or max(1, int(estimates.get("delay", 2)) * 2))
    cost = estimated_cost_from_rating(estimates.get("cost", 1))
    risk = clamp_int(int(estimates.get("risk", 3)) * 2, 1, 10)
    impact = clamp_int(int(estimates.get("impact", 3)) * 2, 1, 10)
    return base_opportunity(
        opportunity_id=str(action.get("id", "unknown-action")),
        source_type="action",
        title=str(action.get("title", "Untitled action")),
        score=score,
        confidence_percent=confidence_from_rationale(rationale, score),
        estimated_effort_hours=effort,
        estimated_cost_eur=cost,
        estimated_revenue_potential=impact * 100,
        risk_level=risk,
        strategic_fit=clamp_int(impact + (2 if cost == 0 else 0), 1, 10),
        requires_human_validation=bool(action.get("requires_human_validation", True)),
        external_execution=bool(action.get("external_action_required", False)),
        created_at=str(action.get("generated_at") or utc_now()),
        metadata={
            "category": action.get("category"),
            "success_metric": action.get("success_metric"),
            "constraints": action.get("constraints", []),
        },
    )


def normalize_roblox_concept(concept: dict[str, Any], rationale: dict[str, Any] | None) -> dict[str, Any]:
    inputs = concept.get("score_inputs", {})
    difficulty = clamp_int(int(inputs.get("development_difficulty", 5)), 1, 10)
    competition = clamp_int(int(inputs.get("competition", 5)), 1, 10)
    monetization = clamp_int(int(inputs.get("monetization_potential", 6)), 1, 10)
    viral = clamp_int(int(inputs.get("viral_potential", 6)), 1, 10)
    return base_opportunity(
        opportunity_id=str(concept.get("id", "unknown-concept")),
        source_type="roblox_concept",
        title=str(concept.get("title", "Untitled Roblox concept")),
        score=normalize_score(concept.get("score", 0)),
        confidence_percent=confidence_from_rationale(rationale, normalize_score(concept.get("score", 0))),
        estimated_effort_hours=max(4.0, difficulty * 4.0),
        estimated_cost_eur=0.0,
        estimated_revenue_potential=float((monetization + viral) * 120),
        risk_level=clamp_int(round((difficulty + competition) / 2), 1, 10),
        strategic_fit=clamp_int(viral + 1, 1, 10),
        requires_human_validation=bool(concept.get("requires_human_validation", True)),
        external_execution=bool(concept.get("external_action_required", False)),
        created_at=str(concept.get("generated_at") or utc_now()),
        metadata={
            "type": concept.get("type"),
            "source_trend_ids": concept.get("source_trend_ids", []),
            "constraints": concept.get("constraints", []),
        },
    )


def normalize_roblox_spec(spec: dict[str, Any]) -> dict[str, Any]:
    mvp = spec.get("mvp", {})
    effort = effort_from_time_estimate(str(mvp.get("temps_estime", "")))
    risks = spec.get("risques", [])
    monetisation = spec.get("monetisation", {})
    monetisation_count = sum(len(monetisation.get(key, [])) for key in ("gamepasses", "dev_products", "premium_benefits"))
    return base_opportunity(
        opportunity_id=str(spec.get("id", "unknown-spec")),
        source_type="roblox_spec",
        title=str(spec.get("nom", "Untitled Roblox spec")),
        score=normalize_score(spec.get("score_final", 0)),
        confidence_percent=max(55, min(85, int(normalize_score(spec.get("score_final", 0)) * 9))),
        estimated_effort_hours=effort,
        estimated_cost_eur=0.0,
        estimated_revenue_potential=float(max(1, monetisation_count) * 180),
        risk_level=clamp_int(4 + len(risks), 1, 10),
        strategic_fit=8 if not spec.get("external_action_required", False) else 3,
        requires_human_validation=bool(spec.get("requires_human_validation", True)),
        external_execution=bool(spec.get("external_action_required", False)),
        created_at=str(spec.get("generated_at") or utc_now()),
        metadata={
            "concept_id": spec.get("concept_id"),
            "genre": spec.get("genre"),
            "constraints": spec.get("constraints", []),
            "mvp": mvp,
        },
    )


def normalize_outcome_opportunity(outcome: dict[str, Any]) -> dict[str, Any]:
    source_type = str(outcome.get("source_type", "other"))
    if source_type not in {"action", "roblox_concept", "roblox_spec"}:
        source_type = "other"
    opportunity = base_opportunity(
        opportunity_id=str(outcome.get("source_id") or outcome.get("id") or "unknown-outcome"),
        source_type=source_type,
        title=str(outcome.get("title", "Outcome opportunity")),
        score=normalize_score(outcome.get("initial_score", 0)),
        confidence_percent=50,
        estimated_effort_hours=float(outcome.get("real_effort_hours", 0) or 0),
        estimated_cost_eur=float(outcome.get("real_cost_eur", 0) or 0),
        estimated_revenue_potential=float(outcome.get("real_revenue_eur", 0) or 0),
        risk_level=risk_from_outcome(outcome),
        strategic_fit=5,
        requires_human_validation=True,
        external_execution=False,
        created_at=str(outcome.get("created_at") or utc_now()),
        metadata={"outcome_id": outcome.get("id")},
    )
    apply_outcome(opportunity, outcome)
    return opportunity


def base_opportunity(
    opportunity_id: str,
    source_type: str,
    title: str,
    score: float,
    confidence_percent: int,
    estimated_effort_hours: float,
    estimated_cost_eur: float,
    estimated_revenue_potential: float,
    risk_level: int,
    strategic_fit: int,
    requires_human_validation: bool,
    external_execution: bool,
    created_at: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": opportunity_id,
        "source_type": source_type,
        "title": title,
        "score": score,
        "confidence_percent": confidence_percent,
        "estimated_effort_hours": round(float(estimated_effort_hours), 2),
        "estimated_cost_eur": round(float(estimated_cost_eur), 2),
        "estimated_revenue_potential": round(float(estimated_revenue_potential), 2),
        "risk_level": clamp_int(risk_level, 1, 10),
        "strategic_fit": clamp_int(strategic_fit, 1, 10),
        "requires_human_validation": requires_human_validation,
        "external_execution": external_execution,
        "created_at": created_at,
        "metadata": metadata or {},
    }


def index_outcomes(outcomes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(outcome.get("source_id", "")): outcome for outcome in outcomes if outcome.get("source_id")}


def merge_outcome(opportunity: dict[str, Any], outcomes: dict[str, dict[str, Any]]) -> None:
    outcome = outcomes.get(str(opportunity.get("id")))
    if outcome:
        apply_outcome(opportunity, outcome)


def apply_outcome(opportunity: dict[str, Any], outcome: dict[str, Any]) -> None:
    opportunity["outcome_status"] = outcome.get("status", "not_started")
    opportunity["outcome_result"] = outcome.get("result", "unknown")
    opportunity["real_effort_hours"] = float(outcome.get("real_effort_hours", 0) or 0)
    opportunity["real_cost_eur"] = float(outcome.get("real_cost_eur", 0) or 0)
    opportunity["real_revenue_eur"] = float(outcome.get("real_revenue_eur", 0) or 0)
    opportunity["qualitative_feedback"] = outcome.get("qualitative_feedback", "")
    opportunity["reason_if_abandoned"] = outcome.get("reason_if_abandoned", "")


def confidence_from_rationale(rationale: dict[str, Any] | None, score: float) -> int:
    if rationale:
        return clamp_int(int(rationale.get("confidence_percent", 60)), 1, 100)
    return clamp_int(round(45 + score * 4), 1, 85)


def estimated_cost_from_rating(value: Any) -> float:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        rating = 3
    if rating <= 1:
        return 0.0
    return float((rating - 1) * 50)


def effort_from_time_estimate(value: str) -> float:
    if "2-3" in value:
        return 24.0
    if "4-6" in value:
        return 48.0
    if "6-8" in value:
        return 72.0
    return 32.0


def risk_from_outcome(outcome: dict[str, Any]) -> int:
    if outcome.get("status") == "abandoned" or outcome.get("result") == "failure":
        return 9
    if outcome.get("result") == "partial":
        return 6
    if outcome.get("result") == "success":
        return 3
    return 5


def normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 10:
        return round(score / 10, 1)
    return round(score, 1)


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def empty_opportunity_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "opportunities": [],
    }
