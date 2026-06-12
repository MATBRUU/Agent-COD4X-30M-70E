"""Generate a local non-financial committee report for COD4X."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .opportunity_collector import ROOT, utc_now, write_json_atomic
from .selection_engine import select_opportunities


DEFAULT_COMMITTEE_REPORT_PATH = ROOT / "memory" / "selection" / "committee_report.json"


def load_committee_report(path: str | Path = DEFAULT_COMMITTEE_REPORT_PATH) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return empty_committee_report()
    return json.loads(report_path.read_text(encoding="utf-8"))


def save_committee_report(payload: dict[str, Any], path: str | Path = DEFAULT_COMMITTEE_REPORT_PATH) -> None:
    write_json_atomic(path, payload)


def generate_and_store_committee_report(
    opportunities: list[dict[str, Any]],
    doctrine: str,
    path: str | Path = DEFAULT_COMMITTEE_REPORT_PATH,
) -> dict[str, Any]:
    selection = select_opportunities(opportunities)
    report = generate_committee_report(selection, doctrine)
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": report,
    }
    save_committee_report(payload, path)
    return payload


def generate_committee_report(selection: dict[str, Any], doctrine: str) -> dict[str, Any]:
    top = selection.get("top_opportunity")
    rejected = selection.get("alternatives_rejected", [])
    watchlist = selection.get("watchlist", [])
    blocked = selection.get("blocked_opportunities", [])

    report = {
        "generated_at": utc_now(),
        "opportunities_analyzed": selection.get("opportunities_analyzed", 0),
        "top_opportunity": top,
        "choice_justification": choice_justification(top),
        "alternatives_rejected": summarize_rejected(rejected),
        "principal_risks": principal_risks(top, watchlist, blocked),
        "assumptions": assumptions(doctrine),
        "recommended_human_actions": recommended_human_actions(top),
        "proposed_decision": proposed_decision(top),
        "guardrails": guardrails(),
        "selection": selection,
    }
    return report


def choice_justification(top: dict[str, Any] | None) -> str:
    if not top:
        return "Aucune opportunite eligible. Attendre ou enrichir les donnees locales."
    return (
        f"{top.get('title')} est retenue car elle combine un score de selection de "
        f"{top.get('selection_score')}/10, une conviction de {top.get('confidence_percent')}%, "
        f"un risque de {top.get('risk_level')}/10 et un effort estime a "
        f"{top.get('estimated_effort_hours')} heure(s)."
    )


def summarize_rejected(rejected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "selection_score": item.get("selection_score"),
            "rejection_reason": item.get("rejection_reason", []),
        }
        for item in rejected
    ]


def principal_risks(
    top: dict[str, Any] | None,
    watchlist: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
) -> list[str]:
    risks = []
    if top:
        if float(top.get("risk_level", 0)) >= 6:
            risks.append("Le top retenu garde un niveau de risque a surveiller.")
        if float(top.get("estimated_effort_hours", 0)) >= 24:
            risks.append("L'effort humain estime peut ralentir la validation.")
        if float(top.get("estimated_revenue_potential", 0)) <= 0:
            risks.append("Le potentiel de revenu reste non prouve.")
    if watchlist:
        risks.append("Certaines alternatives sont prometteuses mais demandent plus de preuves.")
    if blocked:
        risks.append("Des opportunites sont bloquees par les garde-fous ou par leur historique.")
    return risks or ["Aucun risque principal detecte dans les donnees locales."]


def assumptions(doctrine: str) -> list[str]:
    base = [
        "Les opportunites proviennent uniquement de memoires locales.",
        "La doctrine COD4X reste prioritaire sur le score brut.",
        "La selection propose une priorite, pas une execution.",
    ]
    if "validation humaine" in doctrine.lower():
        base.append("La validation humaine est obligatoire avant toute action reelle.")
    return base


def recommended_human_actions(top: dict[str, Any] | None) -> list[str]:
    if not top:
        return [
            "Lancer ou mettre a jour le plan d'actions local.",
            "Ajouter des outcomes reels pour mieux informer la selection.",
        ]
    return [
        f"Relire manuellement l'opportunite retenue : {top.get('title')}.",
        "Verifier le temps humain disponible avant de poursuivre.",
        "Definir un critere de succes local et mesurable.",
        "Ne lancer aucune action externe sans validation explicite.",
    ]


def proposed_decision(top: dict[str, Any] | None) -> str:
    if not top:
        return "wait"
    score = float(top.get("selection_score", 0))
    if score >= 7.5:
        return "pursue"
    if score >= 6:
        return "watch"
    return "wait"


def guardrails() -> list[str]:
    return [
        "Tout reste local.",
        "Aucune API externe.",
        "Aucun scraping.",
        "Aucun wallet.",
        "Aucune publication.",
        "Aucune action financiere.",
        "Aucune execution externe.",
        "Validation humaine obligatoire.",
    ]


def empty_committee_report() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": {
            "generated_at": utc_now(),
            "opportunities_analyzed": 0,
            "top_opportunity": None,
            "choice_justification": "Aucune opportunite analysee.",
            "alternatives_rejected": [],
            "principal_risks": [],
            "assumptions": [
                "Toutes les donnees sont locales.",
                "Aucune execution externe n'est autorisee.",
            ],
            "recommended_human_actions": [],
            "proposed_decision": "wait",
            "guardrails": guardrails(),
            "selection": {
                "top_opportunity": None,
                "alternatives_rejected": [],
                "watchlist": [],
                "blocked_opportunities": [],
            },
        },
    }
