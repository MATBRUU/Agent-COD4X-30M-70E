"""Generate local Reality reports for COD4X."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assumption_tracker import load_assumption_memory
from .evidence_engine import evidence_index, load_evidence_memory


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSUMPTIONS_PATH = ROOT / "memory" / "reality" / "assumptions.json"
DEFAULT_EVIDENCE_PATH = ROOT / "memory" / "reality" / "evidence.json"
DEFAULT_THESES_PATH = ROOT / "memory" / "thesis" / "theses.json"
DEFAULT_REALITY_REPORT_PATH = ROOT / "memory" / "reality" / "reality_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_reality_report(path: str | Path = DEFAULT_REALITY_REPORT_PATH) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return empty_reality_report()
    return json.loads(report_path.read_text(encoding="utf-8"))


def save_reality_report(payload: dict[str, Any], path: str | Path = DEFAULT_REALITY_REPORT_PATH) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = report_path.with_name(f"{report_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(report_path)


def generate_and_store_reality_report(
    assumptions_path: str | Path = DEFAULT_ASSUMPTIONS_PATH,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
    theses_path: str | Path = DEFAULT_THESES_PATH,
    report_path: str | Path = DEFAULT_REALITY_REPORT_PATH,
) -> dict[str, Any]:
    assumptions = load_assumption_memory(assumptions_path).get("assumptions", [])
    evidence = load_evidence_memory(evidence_path).get("evidence", [])
    theses = load_json(theses_path, {"theses": []}).get("theses", [])
    report = build_reality_report(assumptions, evidence, theses)
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": report,
    }
    save_reality_report(payload, report_path)
    return payload


def build_reality_report(
    assumptions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    theses: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(assumptions)
    by_status = count_by(assumptions, "status")
    by_importance = count_by(assumptions, "importance")
    grouped_evidence = evidence_index(evidence)
    critical_unverified = [
        item for item in assumptions
        if item.get("importance") == "critical" and item.get("status") in {"unverified", "unknown"}
    ]
    invalidated = [item for item in assumptions if item.get("status") == "invalidated"]
    unsupported = [
        item for item in assumptions
        if item.get("status") in {"unverified", "unknown", "weakened"}
    ]
    supported_or_validated = [
        item for item in assumptions
        if item.get("status") in {"supported", "validated"}
    ]
    decisions_at_risk = speculative_decisions(assumptions, theses, grouped_evidence)
    reality_level = global_reality_level(
        total=total,
        supported_count=len(supported_or_validated),
        unsupported_count=len(unsupported),
        critical_unverified_count=len(critical_unverified),
        invalidated_count=len(invalidated),
        evidence_count=len(evidence),
    )

    return {
        "generated_at": utc_now(),
        "total_assumptions": total,
        "validated_assumptions": by_status.get("validated", 0),
        "supported_assumptions": by_status.get("supported", 0),
        "unverified_assumptions": by_status.get("unverified", 0) + by_status.get("unknown", 0),
        "invalidated_assumptions": by_status.get("invalidated", 0),
        "weakened_assumptions": by_status.get("weakened", 0),
        "critical_unverified_assumptions": critical_unverified,
        "evidence_available": len(evidence),
        "assumptions_with_evidence": len([item for item in assumptions if grouped_evidence.get(item.get("id"))]),
        "status_breakdown": by_status,
        "importance_breakdown": by_importance,
        "global_reality_level": reality_level,
        "decisions_too_speculative": decisions_at_risk,
        "alerts": build_alerts(critical_unverified, invalidated, decisions_at_risk, total),
        "guardrails": [
            "Tout reste local.",
            "Aucune API externe.",
            "Aucun scraping.",
            "Aucune publication.",
            "Aucune action financiere.",
            "Aucune execution externe.",
            "Le Reality Engine ne modifie pas les scores ni les decisions.",
            "Validation humaine obligatoire avant toute action reelle.",
        ],
    }


def speculative_decisions(
    assumptions: list[dict[str, Any]],
    theses: list[dict[str, Any]],
    grouped_evidence: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    thesis_index = {str(thesis.get("id")): thesis for thesis in theses}
    alerts: list[dict[str, Any]] = []
    assumptions_by_source: dict[str, list[dict[str, Any]]] = {}
    for item in assumptions:
        if item.get("source_type") != "thesis":
            continue
        assumptions_by_source.setdefault(str(item.get("source_id")), []).append(item)

    for thesis_id, items in assumptions_by_source.items():
        weak_items = [
            item for item in items
            if item.get("status") in {"unverified", "unknown", "weakened"}
        ]
        critical_items = [
            item for item in items
            if item.get("importance") == "critical" and item.get("status") in {"unverified", "unknown"}
        ]
        evidence_count = sum(len(grouped_evidence.get(item.get("id"), [])) for item in items)
        if len(weak_items) >= 5 or len(critical_items) >= 2:
            thesis = thesis_index.get(thesis_id, {})
            alerts.append(
                {
                    "source_type": "thesis",
                    "source_id": thesis_id,
                    "decision": thesis.get("decision", "unknown"),
                    "opportunity": thesis.get("selected_opportunity", thesis.get("opportunity", thesis_id)),
                    "unverified_or_weakened_count": len(weak_items),
                    "critical_unverified_count": len(critical_items),
                    "evidence_count": evidence_count,
                    "reason": "Decision fondee sur trop d'hypotheses non verifiees ou critiques.",
                }
            )
    return alerts


def global_reality_level(
    total: int,
    supported_count: int,
    unsupported_count: int,
    critical_unverified_count: int,
    invalidated_count: int,
    evidence_count: int,
) -> str:
    if total == 0:
        return "unknown"
    if invalidated_count > 0 or critical_unverified_count >= 2:
        return "fragile"
    if unsupported_count / total >= 0.6:
        return "speculative"
    if supported_count / total >= 0.6 and evidence_count >= max(1, total // 3):
        return "grounded"
    return "mixed"


def build_alerts(
    critical_unverified: list[dict[str, Any]],
    invalidated: list[dict[str, Any]],
    decisions_at_risk: list[dict[str, Any]],
    total: int,
) -> list[str]:
    alerts = []
    if total == 0:
        alerts.append("Aucune hypothese enregistree : niveau de realite inconnu.")
    if critical_unverified:
        alerts.append(f"{len(critical_unverified)} hypothese(s) critique(s) non verifiee(s).")
    if invalidated:
        alerts.append(f"{len(invalidated)} hypothese(s) invalidee(s) a traiter avant de poursuivre.")
    if decisions_at_risk:
        alerts.append(f"{len(decisions_at_risk)} decision(s) reposent sur trop d'hypotheses fragiles.")
    return alerts or ["Aucune alerte majeure dans la memoire locale."]


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def load_json(path: str | Path, default: dict[str, Any]) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        return default
    return json.loads(json_path.read_text(encoding="utf-8"))


def empty_reality_report() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": {
            "generated_at": utc_now(),
            "total_assumptions": 0,
            "validated_assumptions": 0,
            "supported_assumptions": 0,
            "unverified_assumptions": 0,
            "invalidated_assumptions": 0,
            "weakened_assumptions": 0,
            "critical_unverified_assumptions": [],
            "evidence_available": 0,
            "assumptions_with_evidence": 0,
            "status_breakdown": {},
            "importance_breakdown": {},
            "global_reality_level": "unknown",
            "decisions_too_speculative": [],
            "alerts": ["Aucune hypothese enregistree : niveau de realite inconnu."],
            "guardrails": [
                "Tout reste local.",
                "Le Reality Engine ne modifie pas les scores ni les decisions.",
            ],
        },
    }
