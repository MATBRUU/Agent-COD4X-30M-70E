"""Weekly action planning for COD4X."""

from __future__ import annotations

from typing import Any


def propose_weekly_actions(state: dict[str, Any], doctrine: str) -> list[dict[str, Any]]:
    """Return three local-only weekly actions.

    The V1 planner is deterministic by design: it keeps the system auditable and
    avoids hidden autonomy while the doctrine and state model are still young.
    """
    weekly_context = state.get("weekly_context", {})
    focus = weekly_context.get(
        "focus",
        "Identifier une piste de revenu numerique a faible risque.",
    )
    available_hours = weekly_context.get("available_hours", 5)
    budget_eur = weekly_context.get("budget_eur", 0)

    return [
        {
            "id": "cod4x-weekly-offer-map",
            "title": "Cartographier une micro-offre numerique",
            "category": "offer_design",
            "rationale": (
                "Transformer le focus hebdomadaire en une offre concrete, avec cible, probleme, "
                "promesse, livrable et prix indicatif sans publication."
            ),
            "local_next_step": "Rediger une fiche d'offre dans un document local.",
            "success_metric": "Une fiche d'offre complete et relue.",
            "requires_human_validation": true_value(),
            "external_action_required": False,
            "constraints": ["local_only", "no_publication", "no_spend"],
            "context": {
                "focus": focus,
                "available_hours": available_hours,
                "budget_eur": budget_eur,
            },
            "estimates": {
                "impact": 5,
                "risk": 1,
                "cost": 1,
                "delay": 2,
            },
        },
        {
            "id": "cod4x-weekly-asset-inventory",
            "title": "Inventorier les actifs monetisables",
            "category": "asset_audit",
            "rationale": (
                "Lister les scripts, templates, savoir-faire et workflows deja disponibles afin "
                "de choisir une piste monnayable sans construire trop tot."
            ),
            "local_next_step": "Creer une liste locale avec actif, public cible, douleur et format vendable.",
            "success_metric": "Au moins 10 actifs ou competences classes.",
            "requires_human_validation": true_value(),
            "external_action_required": False,
            "constraints": ["local_only", "no_publication", "no_spend"],
            "context": {
                "focus": focus,
                "available_hours": available_hours,
                "budget_eur": budget_eur,
            },
            "estimates": {
                "impact": 4,
                "risk": 1,
                "cost": 1,
                "delay": 1,
            },
        },
        {
            "id": "cod4x-weekly-validation-plan",
            "title": "Preparer un protocole de validation humaine",
            "category": "validation",
            "rationale": (
                "Definir comment une future action externe serait validee par un humain : objectif, "
                "risques, preuves attendues, seuil de go/no-go et journalisation."
            ),
            "local_next_step": "Ecrire une checklist de validation avant toute action externe.",
            "success_metric": "Une checklist go/no-go utilisable avant publication ou contact.",
            "requires_human_validation": true_value(),
            "external_action_required": False,
            "constraints": ["local_only", "no_publication", "no_spend"],
            "context": {
                "focus": focus,
                "available_hours": available_hours,
                "budget_eur": budget_eur,
            },
            "estimates": {
                "impact": 4,
                "risk": 2,
                "cost": 1,
                "delay": 2,
            },
        },
    ]


def true_value() -> bool:
    """Keep validation flags explicit for future policy checks."""
    return True
