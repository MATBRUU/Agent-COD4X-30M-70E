"""Generate local Roblox game concepts from stored trends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .scoring_engine import SCORE_THRESHOLD, average_score, keep_high_score_concepts, score_concepts
from .trend_analyzer import ROOT, list_trends, utc_now


DEFAULT_CONCEPTS_PATH = ROOT / "memory" / "roblox" / "concepts.json"


def load_concept_memory(path: str | Path = DEFAULT_CONCEPTS_PATH) -> dict[str, Any]:
    concept_path = Path(path)
    if not concept_path.exists():
        return {
            "version": 1,
            "updated_at": utc_now(),
            "source_policy": "local_only",
            "score_threshold": SCORE_THRESHOLD,
            "last_generation": {
                "generated_at": utc_now(),
                "candidate_count": 0,
                "kept_count": 0,
                "rejected_count": 0,
            },
            "concepts": [],
        }
    return json.loads(concept_path.read_text(encoding="utf-8"))


def save_concept_memory(payload: dict[str, Any], path: str | Path = DEFAULT_CONCEPTS_PATH) -> None:
    concept_path = Path(path)
    concept_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = concept_path.with_suffix(concept_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(concept_path)


def generate_concepts_from_trends(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate candidate concepts from local trend objects."""
    candidates: list[dict[str, Any]] = []
    for trend in trends:
        candidates.append(build_lean_concept(trend))
        candidates.append(build_social_challenge_concept(trend))

    if len(trends) >= 2:
        candidates.append(build_hybrid_concept(trends[0], trends[1]))

    return candidates


def generate_and_store_concepts(
    trends_path: str | Path | None = None,
    concepts_path: str | Path = DEFAULT_CONCEPTS_PATH,
    threshold: float = SCORE_THRESHOLD,
) -> dict[str, Any]:
    """Generate concepts, score them, and persist only concepts above threshold."""
    trends = list_trends(trends_path) if trends_path else list_trends()
    candidates = generate_concepts_from_trends(trends)
    scored_candidates = score_concepts(candidates)
    kept = keep_high_score_concepts(scored_candidates, threshold=threshold)

    existing_memory = load_concept_memory(concepts_path)
    existing_by_id = {concept.get("id"): concept for concept in existing_memory.get("concepts", [])}
    kept = [preserve_existing_metadata(concept, existing_by_id.get(concept.get("id"))) for concept in kept]

    memory = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "score_threshold": threshold,
        "last_generation": {
            "generated_at": utc_now(),
            "candidate_count": len(candidates),
            "kept_count": len(kept),
            "rejected_count": max(0, len(candidates) - len(kept)),
            "average_score": average_score(kept),
        },
        "concepts": kept,
    }
    save_concept_memory(memory, concepts_path)
    return memory


def build_lean_concept(trend: dict[str, Any]) -> dict[str, Any]:
    trend_id = str(trend.get("id", "roblox-trend"))
    title = f"{trend.get('name', 'Roblox trend')} MVP"
    return {
        "id": f"{trend_id}-mvp",
        "title": title,
        "source_trend_ids": [trend_id],
        "type": "lean_mvp",
        "pitch": (
            "Version reduite et testable de la tendance, centree sur une boucle jouable en moins de "
            "3 minutes et une progression visible."
        ),
        "core_loop": build_core_loop(trend, fallback="jouer, gagner une ressource, ameliorer un espace ou avatar"),
        "monetization": build_monetization(trend),
        "validation_steps": [
            "Definir une boucle de jeu testable localement",
            "Lister 5 assets minimum necessaires",
            "Faire valider le concept par un humain avant toute publication",
        ],
        "requires_human_validation": True,
        "external_action_required": False,
        "constraints": ["local_only", "no_publication", "no_spend", "no_wallet_write"],
        "score_inputs": {
            "viral_potential": min(10, int(trend.get("strength", 6)) + 1),
            "monetization_potential": monetization_score(trend),
            "development_difficulty": max(1, int(trend.get("development_complexity", 5)) - 2),
            "competition": max(1, int(trend.get("competition", 5)) - 2),
        },
        "generated_at": utc_now(),
    }


def build_social_challenge_concept(trend: dict[str, Any]) -> dict[str, Any]:
    trend_id = str(trend.get("id", "roblox-trend"))
    return {
        "id": f"{trend_id}-challenge",
        "title": f"Defi social {trend.get('name', 'Roblox')}",
        "source_trend_ids": [trend_id],
        "type": "social_challenge",
        "pitch": (
            "Concept axe sur des defis rejouables, faciles a filmer et a comparer entre amis, "
            "avec une monetisation cosmetique seulement."
        ),
        "core_loop": build_core_loop(trend, fallback="choisir un defi, tenter un score, partager le resultat"),
        "monetization": build_monetization(trend),
        "validation_steps": [
            "Ecrire 10 defis sans dependance externe",
            "Verifier que chaque defi produit un resultat visible",
            "Journaliser la decision humaine avant toute action externe",
        ],
        "requires_human_validation": True,
        "external_action_required": False,
        "constraints": ["local_only", "no_publication", "no_spend", "no_wallet_write"],
        "score_inputs": {
            "viral_potential": min(10, int(trend.get("strength", 6)) + 2),
            "monetization_potential": max(5, monetization_score(trend) - 1),
            "development_difficulty": max(1, int(trend.get("development_complexity", 5)) - 1),
            "competition": max(1, int(trend.get("competition", 5)) - 1),
        },
        "generated_at": utc_now(),
    }


def build_hybrid_concept(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    primary_id = str(primary.get("id", "roblox-primary"))
    secondary_id = str(secondary.get("id", "roblox-secondary"))
    return {
        "id": f"roblox-hybrid-{primary_id}-{secondary_id}",
        "title": f"Hybrid: {primary.get('name')} x {secondary.get('name')}",
        "source_trend_ids": [primary_id, secondary_id],
        "type": "hybrid",
        "pitch": (
            "Fusion locale de deux signaux forts pour trouver un angle moins frontalement concurrentiel "
            "qu'une copie directe de tendance."
        ),
        "core_loop": "; ".join(
            [
                build_core_loop(primary, fallback="boucle principale courte"),
                build_core_loop(secondary, fallback="meta progression cosmetique"),
            ]
        ),
        "monetization": sorted(set(build_monetization(primary) + build_monetization(secondary))),
        "validation_steps": [
            "Verifier que l'hybride tient en un prototype simple",
            "Retirer toute mecanique qui implique une publication ou une depense",
            "Obtenir une validation humaine avant tout test public",
        ],
        "requires_human_validation": True,
        "external_action_required": False,
        "constraints": ["local_only", "no_publication", "no_spend", "no_wallet_write"],
        "score_inputs": {
            "viral_potential": min(10, max(int(primary.get("strength", 6)), int(secondary.get("strength", 6))) + 1),
            "monetization_potential": min(10, max(monetization_score(primary), monetization_score(secondary)) + 1),
            "development_difficulty": max(
                1,
                round((int(primary.get("development_complexity", 5)) + int(secondary.get("development_complexity", 5))) / 2),
            ),
            "competition": max(1, min(int(primary.get("competition", 5)), int(secondary.get("competition", 5))) - 1),
        },
        "generated_at": utc_now(),
    }


def preserve_existing_metadata(concept: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return concept
    merged = dict(concept)
    merged["generated_at"] = existing.get("generated_at", concept.get("generated_at"))
    merged["last_scored_at"] = utc_now()
    return merged


def build_core_loop(trend: dict[str, Any], fallback: str) -> str:
    mechanics = trend.get("mechanics", [])
    if not mechanics:
        return fallback
    return " -> ".join(str(mechanic) for mechanic in mechanics[:3])


def build_monetization(trend: dict[str, Any]) -> list[str]:
    vectors = trend.get("monetization_vectors", [])
    if vectors:
        return [str(vector) for vector in vectors[:4]]
    return ["cosmetiques optionnels", "passes non essentiels"]


def monetization_score(trend: dict[str, Any]) -> int:
    vectors = trend.get("monetization_vectors", [])
    return min(10, 6 + len(vectors))
