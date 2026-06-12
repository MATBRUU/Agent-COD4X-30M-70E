"""Local outcome tracking for COD4X ideas, actions and concepts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTCOMES_PATH = ROOT / "memory" / "learning" / "outcomes.json"

SOURCE_TYPES = {"action", "roblox_concept", "other"}
STATUSES = {"not_started", "in_progress", "completed", "abandoned"}
RESULTS = {"unknown", "success", "failure", "partial"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_outcome_memory(path: str | Path = DEFAULT_OUTCOMES_PATH) -> dict[str, Any]:
    outcome_path = Path(path)
    if not outcome_path.exists():
        return empty_outcome_memory()
    return json.loads(outcome_path.read_text(encoding="utf-8"))


def save_outcome_memory(payload: dict[str, Any], path: str | Path = DEFAULT_OUTCOMES_PATH) -> None:
    outcome_path = Path(path)
    outcome_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = outcome_path.with_suffix(outcome_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(outcome_path)


def list_outcomes(path: str | Path = DEFAULT_OUTCOMES_PATH) -> list[dict[str, Any]]:
    memory = load_outcome_memory(path)
    return sorted(memory.get("outcomes", []), key=lambda item: item.get("updated_at", ""), reverse=True)


def add_or_update_outcome(
    outcome: dict[str, Any],
    path: str | Path = DEFAULT_OUTCOMES_PATH,
) -> dict[str, Any]:
    """Create or update an outcome record using local JSON memory."""
    memory = load_outcome_memory(path)
    outcomes = memory.setdefault("outcomes", [])
    normalized = normalize_outcome(outcome)

    for index, existing in enumerate(outcomes):
        same_id = existing.get("id") == normalized["id"]
        same_source = (
            existing.get("source_type") == normalized["source_type"]
            and existing.get("source_id") == normalized["source_id"]
        )
        if same_id or same_source:
            merged = {**existing, **normalized}
            merged["id"] = existing.get("id", normalized["id"])
            merged["created_at"] = existing.get("created_at", normalized["created_at"])
            merged["updated_at"] = utc_now()
            outcomes[index] = merged
            save_outcome_memory(memory, path)
            return merged

    outcomes.append(normalized)
    save_outcome_memory(memory, path)
    return normalized


def normalize_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    source_type = normalize_choice(outcome.get("source_type"), SOURCE_TYPES, "other")
    source_id = str(outcome.get("source_id") or "manual").strip()
    status = normalize_choice(outcome.get("status"), STATUSES, "not_started")
    result = normalize_choice(outcome.get("result"), RESULTS, "unknown")
    now = utc_now()
    return {
        "id": str(outcome.get("id") or build_outcome_id(source_type, source_id)).strip(),
        "source_type": source_type,
        "source_id": source_id,
        "title": str(outcome.get("title") or source_id).strip(),
        "initial_score": to_float(outcome.get("initial_score"), default=0.0),
        "status": status,
        "result": result,
        "real_effort_hours": to_float(outcome.get("real_effort_hours"), default=0.0),
        "real_cost_eur": to_float(outcome.get("real_cost_eur"), default=0.0),
        "real_revenue_eur": to_float(outcome.get("real_revenue_eur"), default=0.0),
        "qualitative_feedback": str(outcome.get("qualitative_feedback") or "").strip(),
        "reason_if_abandoned": str(outcome.get("reason_if_abandoned") or "").strip(),
        "created_at": str(outcome.get("created_at") or now),
        "updated_at": str(outcome.get("updated_at") or now),
    }


def empty_outcome_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "outcomes": [],
    }


def build_outcome_id(source_type: str, source_id: str) -> str:
    return f"outcome-{source_type}-{slugify(source_id)}"


def normalize_choice(value: Any, choices: set[str], default: str) -> str:
    candidate = str(value or default).strip().lower()
    return candidate if candidate in choices else default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"
