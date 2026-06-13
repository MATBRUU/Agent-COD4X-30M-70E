"""Generate local reports for COD4X experiments."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPERIMENTS_PATH = ROOT / "memory" / "experiments" / "experiments.json"
DEFAULT_ASSUMPTIONS_PATH = ROOT / "memory" / "reality" / "assumptions.json"
DEFAULT_REPORT_PATH = ROOT / "memory" / "experiments" / "experiment_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_experiment_report(path: str | Path = DEFAULT_REPORT_PATH) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return empty_experiment_report()
    return json.loads(report_path.read_text(encoding="utf-8"))


def save_experiment_report(payload: dict[str, Any], path: str | Path = DEFAULT_REPORT_PATH) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = report_path.with_name(f"{report_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(report_path)


def generate_and_store_experiment_report(
    experiments_path: str | Path = DEFAULT_EXPERIMENTS_PATH,
    assumptions_path: str | Path = DEFAULT_ASSUMPTIONS_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    experiments = load_json(experiments_path, {"experiments": []}).get("experiments", [])
    assumptions = load_json(assumptions_path, {"assumptions": []}).get("assumptions", [])
    report = build_experiment_report(experiments, assumptions)
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": report,
    }
    save_experiment_report(payload, report_path)
    return payload


def build_experiment_report(
    experiments: list[dict[str, Any]],
    assumptions: list[dict[str, Any]],
) -> dict[str, Any]:
    priority = priority_experiments(experiments)
    completed = [item for item in experiments if item.get("status") == "completed"]
    conclusive = [item for item in completed if item.get("result") in {"success", "failure"}]
    inconclusive = [item for item in completed if item.get("result") == "inconclusive"]
    untested_assumptions = assumptions_without_completed_test(assumptions, experiments)
    next_experiment = next_recommended_experiment(experiments)

    return {
        "generated_at": utc_now(),
        "planned_experiments": len([item for item in experiments if item.get("status") == "planned"]),
        "priority_experiments": priority[:3],
        "completed_experiments": len(completed),
        "conclusive_experiments": len(conclusive),
        "inconclusive_experiments": len(inconclusive),
        "untested_assumptions": untested_assumptions,
        "next_recommended_experiment": next_experiment,
        "status_breakdown": count_by(experiments, "status"),
        "result_breakdown": count_by(experiments, "result"),
        "guardrails": [
            "Tout reste local.",
            "Aucune API externe.",
            "Aucun scraping.",
            "Aucune publication.",
            "Aucune action financiere.",
            "Aucune execution externe.",
            "Les experiences produisent uniquement des preuves locales.",
            "Le module ne modifie pas les scores.",
        ],
    }


def priority_experiments(experiments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = [
        item for item in experiments
        if item.get("status") not in {"completed", "abandoned"}
    ]
    return sorted(active, key=lambda item: float(item.get("priority_score", 0)), reverse=True)


def next_recommended_experiment(experiments: list[dict[str, Any]]) -> dict[str, Any] | None:
    priority = priority_experiments(experiments)
    return priority[0] if priority else None


def assumptions_without_completed_test(
    assumptions: list[dict[str, Any]],
    experiments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    completed_assumption_ids = {
        item.get("assumption_id")
        for item in experiments
        if item.get("status") == "completed"
    }
    return [
        {
            "id": item.get("id"),
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "hypothesis": item.get("hypothesis"),
            "status": item.get("status"),
            "importance": item.get("importance"),
        }
        for item in assumptions
        if item.get("id") not in completed_assumption_ids
        and (
            item.get("importance") == "critical"
            or item.get("status") in {"unverified", "unknown", "weakened"}
        )
    ]


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


def empty_experiment_report() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "report": {
            "generated_at": utc_now(),
            "planned_experiments": 0,
            "priority_experiments": [],
            "completed_experiments": 0,
            "conclusive_experiments": 0,
            "inconclusive_experiments": 0,
            "untested_assumptions": [],
            "next_recommended_experiment": None,
            "status_breakdown": {},
            "result_breakdown": {},
            "guardrails": [
                "Tout reste local.",
                "Les experiences produisent uniquement des preuves locales.",
            ],
        },
    }
