"""Generate local Roblox game specs from high-scoring concepts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .concept_generator import DEFAULT_CONCEPTS_PATH, load_concept_memory
from .scoring_engine import SCORE_THRESHOLD
from .trend_analyzer import ROOT, utc_now


DEFAULT_SPECS_PATH = ROOT / "memory" / "roblox" / "specs.json"


def load_spec_memory(path: str | Path = DEFAULT_SPECS_PATH) -> dict[str, Any]:
    specs_path = Path(path)
    if not specs_path.exists():
        return empty_spec_memory()
    return json.loads(specs_path.read_text(encoding="utf-8"))


def save_spec_memory(payload: dict[str, Any], path: str | Path = DEFAULT_SPECS_PATH) -> None:
    specs_path = Path(path)
    specs_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = specs_path.with_suffix(specs_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(specs_path)


def generate_and_store_specs(
    concepts_path: str | Path = DEFAULT_CONCEPTS_PATH,
    specs_path: str | Path = DEFAULT_SPECS_PATH,
) -> dict[str, Any]:
    """Generate complete Roblox game specs from concepts above 8/10."""
    concept_memory = load_concept_memory(concepts_path)
    concepts = high_score_concepts(concept_memory.get("concepts", []))
    used_demo_data = False

    if not concepts:
        concepts = demo_concepts()
        used_demo_data = True

    specs = [generate_spec(concept) for concept in concepts]
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "last_generation": {
            "generated_at": utc_now(),
            "source_concept_count": len(concepts),
            "spec_count": len(specs),
            "used_demo_data": used_demo_data,
        },
        "specs": specs,
    }
    save_spec_memory(payload, specs_path)
    return payload


def generate_spec(concept: dict[str, Any]) -> dict[str, Any]:
    """Generate one full game spec from a scored concept."""
    concept_id = str(concept.get("id", "roblox-concept"))
    title = str(concept.get("title", "Roblox Concept"))
    concept_type = str(concept.get("type", "lean_mvp"))
    score = float(concept.get("score", 8.1))
    inputs = concept.get("score_inputs", {})
    difficulty = int(inputs.get("development_difficulty", 5))
    competition = int(inputs.get("competition", 5))
    monetization = normalize_list(concept.get("monetization")) or ["cosmetiques optionnels"]

    return {
        "id": f"spec-{concept_id}",
        "concept_id": concept_id,
        "generated_at": utc_now(),
        "nom": clean_game_name(title),
        "genre": infer_genre(concept),
        "public_cible": infer_audience(concept),
        "promesse_joueur": build_player_promise(concept),
        "core_loop": concept.get("core_loop", "jouer -> progresser -> personnaliser -> recommencer"),
        "meta_progression": build_meta_progression(concept_type),
        "premiere_session": build_first_session(concept),
        "retention_j1": build_retention_j1(concept),
        "retention_j7": build_retention_j7(concept),
        "monetisation": {
            "gamepasses": build_gamepasses(monetization),
            "dev_products": build_dev_products(concept_type),
            "premium_benefits": build_premium_benefits(concept_type),
        },
        "mvp": {
            "temps_estime": estimate_development_time(difficulty),
            "scripts_requis": build_required_scripts(concept_type),
            "ui_requise": build_required_ui(concept_type),
            "assets_requis": build_required_assets(concept),
        },
        "risques": build_risks(concept, difficulty),
        "concurrents": build_competitor_notes(concept, competition),
        "score_final": round(score, 1),
        "requires_human_validation": True,
        "external_action_required": False,
        "constraints": ["local_only", "no_publication", "no_roblox_api", "no_payment", "no_wallet"],
    }


def high_score_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept = [concept for concept in concepts if float(concept.get("score", 0)) > SCORE_THRESHOLD]
    return sorted(kept, key=lambda concept: float(concept.get("score", 0)), reverse=True)


def empty_spec_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "last_generation": {
            "generated_at": utc_now(),
            "source_concept_count": 0,
            "spec_count": 0,
            "used_demo_data": False,
        },
        "specs": [],
    }


def demo_concepts() -> list[dict[str, Any]]:
    return [
        {
            "id": "roblox-demo-cozy-challenge",
            "title": "Cozy Room Challenge MVP",
            "type": "social_challenge",
            "pitch": "Defis de decoration rapides avec resultat partageable et progression cosmetique.",
            "core_loop": "choisir un theme -> decorer une piece -> recevoir un score -> debloquer un objet",
            "monetization": ["packs cosmetiques", "themes saisonniers", "emplacements de sauvegarde"],
            "source_trend_ids": ["demo-local"],
            "score_inputs": {
                "viral_potential": 9,
                "monetization_potential": 8,
                "development_difficulty": 3,
                "competition": 4,
            },
            "score": 8.6,
        }
    ]


def clean_game_name(title: str) -> str:
    for suffix in (" MVP", " - MVP"):
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


def infer_genre(concept: dict[str, Any]) -> str:
    concept_type = str(concept.get("type", "lean_mvp"))
    title = str(concept.get("title", "")).lower()
    if "tycoon" in title:
        return "Tycoon / collection"
    if "roleplay" in title or "cozy" in title:
        return "Roleplay cozy / social"
    if "anime" in title or "battleground" in title:
        return "Arena combat casual"
    if concept_type == "social_challenge":
        return "Defi social rejouable"
    if concept_type == "hybrid":
        return "Hybride progression / social"
    return "Experience Roblox casual"


def infer_audience(concept: dict[str, Any]) -> list[str]:
    title = str(concept.get("title", "")).lower()
    if "anime" in title or "battleground" in title:
        return ["joueurs competitifs casual", "fans anime", "createurs de clips courts"]
    if "cozy" in title or "roleplay" in title:
        return ["joueurs casual", "fans de decoration", "communautes roleplay"]
    if "tycoon" in title:
        return ["joueurs tycoon", "collectionneurs", "joueurs orientes avatar"]
    return ["joueurs Roblox casual", "amis en petit groupe", "testeurs de nouveautes"]


def build_player_promise(concept: dict[str, Any]) -> str:
    pitch = str(concept.get("pitch", "")).strip()
    if pitch:
        return pitch
    return "Entrer vite dans une boucle fun, progresser en quelques minutes et obtenir un resultat visible."


def build_meta_progression(concept_type: str) -> str:
    if concept_type == "social_challenge":
        return "Saisons de defis, badges locaux, cosmetiques debloquables et classement hebdomadaire non public en V2.2."
    if concept_type == "hybrid":
        return "Double progression : maitrise de la boucle principale et collection cosmetique liee aux objectifs."
    return "Niveaux de compte, objets cosmetiques, objectifs quotidiens et upgrades non pay-to-win."


def build_first_session(concept: dict[str, Any]) -> list[str]:
    return [
        "Arrivee dans un lobby simple avec une promesse claire.",
        "Tutoriel interactif de moins de 90 secondes.",
        f"Premiere boucle : {concept.get('core_loop', 'jouer -> progresser -> recommencer')}.",
        "Recompense cosmetique locale et invitation a rejouer une seconde manche.",
    ]


def build_retention_j1(concept: dict[str, Any]) -> list[str]:
    return [
        "Bonus de retour non financier.",
        "Objectif quotidien court lie au core loop.",
        "Nouveau cosmetique ou badge local a debloquer.",
    ]


def build_retention_j7(concept: dict[str, Any]) -> list[str]:
    return [
        "Mini-saison hebdomadaire avec 5 objectifs.",
        "Variation de theme pour renouveler la boucle.",
        "Recompense de statut visible mais non pay-to-win.",
    ]


def build_gamepasses(monetization: list[str]) -> list[str]:
    passes = ["Pack cosmetique fondateur", "Emplacements de sauvegarde supplementaires"]
    if any("theme" in item.lower() for item in monetization):
        passes.append("Themes premium visuels")
    if any("emote" in item.lower() for item in monetization):
        passes.append("Pack emotes cosmetiques")
    return dedupe(passes)


def build_dev_products(concept_type: str) -> list[str]:
    products = ["Boost cosmetique temporaire", "Pack monnaie soft limitee"]
    if concept_type == "social_challenge":
        products.append("Relance de defi bonus")
    if concept_type == "hybrid":
        products.append("Pack progression cosmetique hybride")
    return products


def build_premium_benefits(concept_type: str) -> list[str]:
    benefits = ["Bonus quotidien cosmetique", "Tag premium discret dans le lobby"]
    if concept_type == "lean_mvp":
        benefits.append("Slot de sauvegarde visuelle bonus")
    return benefits


def estimate_development_time(difficulty: int) -> str:
    if difficulty <= 3:
        return "2-3 semaines"
    if difficulty <= 5:
        return "4-6 semaines"
    return "6-8 semaines"


def build_required_scripts(concept_type: str) -> list[str]:
    scripts = [
        "GameLoop.server.lua",
        "PlayerData.server.lua",
        "RewardService.server.lua",
        "SessionTutorial.client.lua",
    ]
    if concept_type == "social_challenge":
        scripts.extend(["ChallengeService.server.lua", "ScoreDisplay.client.lua"])
    elif concept_type == "hybrid":
        scripts.extend(["HybridProgression.server.lua", "CollectionService.server.lua"])
    else:
        scripts.append("ProgressionService.server.lua")
    return scripts


def build_required_ui(concept_type: str) -> list[str]:
    ui = ["Lobby HUD", "Objectif courant", "Ecran recompense", "Menu progression"]
    if concept_type == "social_challenge":
        ui.append("Panneau defis")
    if concept_type == "hybrid":
        ui.append("Inventaire collection")
    return ui


def build_required_assets(concept: dict[str, Any]) -> list[str]:
    title = str(concept.get("title", "")).lower()
    assets = ["Lobby simple", "Icones UI", "Effets de recompense", "Objets cosmetiques de base"]
    if "anime" in title or "battleground" in title:
        assets.extend(["Arena compacte", "Effets de competences", "Animations combat basiques"])
    if "cozy" in title or "roleplay" in title:
        assets.extend(["Pieces decorables", "Mobilier modulaire", "Palette de themes"])
    if "tycoon" in title:
        assets.extend(["Stations de production", "Vitrines d'objets", "Props de collection"])
    return dedupe(assets)


def build_risks(concept: dict[str, Any], difficulty: int) -> list[str]:
    risks = [
        "Risque de scope creep si le contenu cosmetique grandit trop vite.",
        "Validation humaine requise avant tout test public.",
    ]
    if difficulty >= 6:
        risks.append("Complexite technique elevee pour une premiere version.")
    if float(concept.get("score", 0)) < 8.5:
        risks.append("Score proche du seuil : verifier la promesse avant production.")
    return risks


def build_competitor_notes(concept: dict[str, Any], competition: int) -> list[str]:
    title = str(concept.get("title", "concept Roblox"))
    notes = [f"Comparer localement le positionnement de '{title}' avec les jeux Roblox du meme genre avant publication."]
    if competition >= 7:
        notes.append("Concurrence forte : chercher un angle de niche ou une execution plus simple.")
    elif competition <= 4:
        notes.append("Concurrence moderee : potentiel d'angle differenciant si la boucle est lisible.")
    else:
        notes.append("Concurrence moyenne : eviter la copie directe des formats dominants.")
    return notes


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
