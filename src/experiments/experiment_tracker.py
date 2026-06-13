"""Track local COD4X experiments generated from Reality assumptions."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPERIMENTS_PATH = ROOT / "memory" / "experiments" / "experiments.json"

STATUSES = {"planned", "in_progress", "completed", "abandoned"}
RESULTS = {"unknown", "success", "failure", "inconclusive"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_experiment_memory(path: str | Path = DEFAULT_EXPERIMENTS_PATH) -> dict[str, Any]:
    experiments_path = Path(path)
    if not experiments_path.exists():
        return empty_experiment_memory()
    return json.loads(experiments_path.read_text(encoding="utf-8"))


def save_experiment_memory(payload: dict[str, Any], path: str | Path = DEFAULT_EXPERIMENTS_PATH) -> None:
    experiments_path = Path(path)
    experiments_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = experiments_path.with_name(f"{experiments_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(experiments_path)


def list_experiments(path: str | Path = DEFAULT_EXPERIMENTS_PATH) -> list[dict[str, Any]]:
    memory = load_experiment_memory(path)
    return sorted(
        memory.get("experiments", []),
        key=lambda item: (float(item.get("priority_score", 0)), item.get("updated_at", "")),
        reverse=True,
    )


def add_or_update_experiment(
    experiment: dict[str, Any],
    path: str | Path = DEFAULT_EXPERIMENTS_PATH,
) -> dict[str, Any]:
    memory = load_experiment_memory(path)
    experiments = memory.setdefault("experiments", [])
    normalized = normalize_experiment(experiment)

    for index, existing in enumerate(experiments):
        same_id = existing.get("id") == normalized["id"]
        same_assumption = existing.get("assumption_id") == normalized["assumption_id"]
        if same_id or same_assumption:
            merged = {**existing, **normalized}
            merged["id"] = existing.get("id", normalized["id"])
            merged["created_at"] = existing.get("created_at", normalized["created_at"])
            merged["status"] = existing.get("status", normalized["status"])
            merged["result"] = existing.get("result", normalized["result"])
            merged["updated_at"] = utc_now()
            experiments[index] = merged
            save_experiment_memory(memory, path)
            return merged

    experiments.append(normalized)
    save_experiment_memory(memory, path)
    return normalized


def update_experiment(
    experiment_id: str,
    updates: dict[str, Any],
    path: str | Path = DEFAULT_EXPERIMENTS_PATH,
) -> dict[str, Any]:
    memory = load_experiment_memory(path)
    experiments = memory.setdefault("experiments", [])
    for index, existing in enumerate(experiments):
        if existing.get("id") != experiment_id:
            continue
        updated = dict(existing)
        if updates.get("status") is not None:
            updated["status"] = normalize_choice(updates.get("status"), STATUSES, existing.get("status", "planned"))
        if updates.get("result") is not None:
            updated["result"] = normalize_choice(updates.get("result"), RESULTS, existing.get("result", "unknown"))
        if updates.get("notes") is not None:
            updated["notes"] = str(updates.get("notes") or "").strip()
        updated["updated_at"] = utc_now()
        experiments[index] = updated
        save_experiment_memory(memory, path)
        return updated
    raise ValueError(f"Experiment not found: {experiment_id}")


def evidence_from_completed_experiment(experiment: dict[str, Any]) -> dict[str, Any] | None:
    if experiment.get("status") != "completed":
        return None

    result = str(experiment.get("result") or "unknown")
    strength = "strong" if result in {"success", "failure"} else "weak"
    supports_hypothesis = result == "success"
    notes = str(experiment.get("notes") or "").strip()
    summary = (
        f"Experience terminee: {experiment.get('experiment_title')} | "
        f"resultat={result} | signal attendu={experiment.get('expected_signal')}."
    )
    if notes:
        summary = f"{summary} Notes: {notes}"

    return {
        "id": f"evidence-experiment-{experiment.get('id')}",
        "assumption_id": experiment.get("assumption_id"),
        "evidence_type": "local_test",
        "summary": summary,
        "strength": strength,
        "supports_hypothesis": supports_hypothesis,
    }


def normalize_experiment(experiment: dict[str, Any]) -> dict[str, Any]:
    assumption_id = str(experiment.get("assumption_id") or "").strip()
    if not assumption_id:
        raise ValueError("assumption_id est obligatoire.")

    now = utc_now()
    return {
        "id": str(experiment.get("id") or build_experiment_id(assumption_id)).strip(),
        "assumption_id": assumption_id,
        "source_type": str(experiment.get("source_type") or "other").strip(),
        "source_id": str(experiment.get("source_id") or "manual").strip(),
        "experiment_title": str(experiment.get("experiment_title") or "Tester une hypothese locale").strip(),
        "objective": str(experiment.get("objective") or "").strip(),
        "method": str(experiment.get("method") or "").strip(),
        "expected_signal": str(experiment.get("expected_signal") or "").strip(),
        "success_criteria": str(experiment.get("success_criteria") or "").strip(),
        "failure_criteria": str(experiment.get("failure_criteria") or "").strip(),
        "estimated_effort_hours": round(to_float(experiment.get("estimated_effort_hours"), 1.0), 2),
        "estimated_cost_eur": round(to_float(experiment.get("estimated_cost_eur"), 0.0), 2),
        "status": normalize_choice(experiment.get("status"), STATUSES, "planned"),
        "result": normalize_choice(experiment.get("result"), RESULTS, "unknown"),
        "priority_score": round(to_float(experiment.get("priority_score"), 0.0), 2),
        "priority_reasons": list(experiment.get("priority_reasons", [])),
        "created_at": str(experiment.get("created_at") or now),
        "updated_at": str(experiment.get("updated_at") or now),
    }


def empty_experiment_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "experiments": [],
    }


def build_experiment_id(assumption_id: str) -> str:
    return f"experiment-{slugify(assumption_id)}"


def normalize_choice(value: Any, choices: set[str], default: str) -> str:
    candidate = str(value or default).strip().lower()
    return candidate if candidate in choices else default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def slugify(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "item"
