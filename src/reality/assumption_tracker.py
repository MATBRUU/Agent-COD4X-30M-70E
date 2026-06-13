"""Track local assumptions behind COD4X decisions and theses."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSUMPTIONS_PATH = ROOT / "memory" / "reality" / "assumptions.json"

SOURCE_TYPES = {"action", "roblox_concept", "roblox_spec", "thesis", "opportunity", "other"}
STATUSES = {"unverified", "supported", "validated", "weakened", "invalidated", "unknown"}
IMPORTANCE_LEVELS = {"low", "medium", "high", "critical"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_assumption_memory(path: str | Path = DEFAULT_ASSUMPTIONS_PATH) -> dict[str, Any]:
    assumptions_path = Path(path)
    if not assumptions_path.exists():
        return empty_assumption_memory()
    return json.loads(assumptions_path.read_text(encoding="utf-8"))


def save_assumption_memory(payload: dict[str, Any], path: str | Path = DEFAULT_ASSUMPTIONS_PATH) -> None:
    assumptions_path = Path(path)
    assumptions_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = assumptions_path.with_name(f"{assumptions_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(assumptions_path)


def list_assumptions(path: str | Path = DEFAULT_ASSUMPTIONS_PATH) -> list[dict[str, Any]]:
    memory = load_assumption_memory(path)
    return sorted(memory.get("assumptions", []), key=lambda item: item.get("updated_at", ""), reverse=True)


def add_or_update_assumption(
    assumption: dict[str, Any],
    path: str | Path = DEFAULT_ASSUMPTIONS_PATH,
) -> dict[str, Any]:
    """Create or update a local assumption record."""
    memory = load_assumption_memory(path)
    assumptions = memory.setdefault("assumptions", [])
    normalized = normalize_assumption(assumption)

    for index, existing in enumerate(assumptions):
        same_id = existing.get("id") == normalized["id"]
        same_source = (
            existing.get("source_type") == normalized["source_type"]
            and existing.get("source_id") == normalized["source_id"]
            and normalize_text(existing.get("hypothesis")) == normalize_text(normalized["hypothesis"])
        )
        if same_id or same_source:
            merged = {**existing, **normalized}
            merged["id"] = existing.get("id", normalized["id"])
            merged["created_at"] = existing.get("created_at", normalized["created_at"])
            merged["updated_at"] = utc_now()
            assumptions[index] = merged
            save_assumption_memory(memory, path)
            return merged

    assumptions.append(normalized)
    save_assumption_memory(memory, path)
    return normalized


def extract_assumptions_from_thesis(
    thesis: dict[str, Any],
    path: str | Path = DEFAULT_ASSUMPTIONS_PATH,
) -> dict[str, Any]:
    """Extract thesis beliefs into Reality memory without changing thesis scores."""
    if not thesis or thesis.get("status") == "missing_selection":
        return {
            "status": "missing_thesis",
            "message": "Aucune these exploitable pour creer des hypotheses.",
            "created": 0,
            "updated": 0,
            "assumptions": [],
        }

    candidates = build_thesis_assumption_candidates(thesis)
    before = {item.get("id") for item in load_assumption_memory(path).get("assumptions", [])}
    stored = [add_or_update_assumption(candidate, path) for candidate in candidates]
    after_created = [item for item in stored if item.get("id") not in before]
    return {
        "status": "ok",
        "source_policy": "local_only",
        "external_execution": False,
        "source_thesis_id": thesis.get("id"),
        "created": len(after_created),
        "updated": len(stored) - len(after_created),
        "assumptions": stored,
    }


def build_thesis_assumption_candidates(thesis: dict[str, Any]) -> list[dict[str, Any]]:
    source_id = str(thesis.get("id") or thesis.get("selected_opportunity_id") or "latest-thesis")
    candidates: list[dict[str, Any]] = []

    def add_many(items: list[Any], status: str, importance: str, confidence: int, prefix: str = "") -> None:
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            hypothesis = f"{prefix}{text}" if prefix else text
            candidates.append(
                {
                    "source_type": "thesis",
                    "source_id": source_id,
                    "hypothesis": hypothesis,
                    "status": status,
                    "confidence_percent": confidence,
                    "importance": importance,
                }
            )

    add_many(thesis.get("hypotheses_principales", []), "unverified", "high", 50)
    add_many(thesis.get("fragile_assumptions", []), "unverified", "critical", 35)
    add_many(thesis.get("risks", []), "unverified", "high", 40, "Risque a verifier : ")
    add_many(thesis.get("advantages", []), "supported", "medium", 60, "Argument favorable a verifier : ")
    add_many(thesis.get("reasons", []), "supported", "high", 60, "Raison du choix a verifier : ")
    add_many(thesis.get("counter_arguments", thesis.get("contre_arguments", [])), "weakened", "high", 45)
    add_many(thesis.get("failure_scenarios", []), "unverified", "high", 40, "Scenario d'echec possible : ")

    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = normalize_text(candidate.get("hypothesis"))
        if key and key not in unique:
            unique[key] = candidate
    return list(unique.values())


def normalize_assumption(assumption: dict[str, Any]) -> dict[str, Any]:
    source_type = normalize_choice(assumption.get("source_type"), SOURCE_TYPES, "other")
    source_id = str(assumption.get("source_id") or "manual").strip()
    hypothesis = str(assumption.get("hypothesis") or "").strip()
    status = normalize_choice(assumption.get("status"), STATUSES, "unverified")
    importance = normalize_choice(assumption.get("importance"), IMPORTANCE_LEVELS, "medium")
    now = utc_now()

    if not hypothesis:
        raise ValueError("Une hypothese non vide est obligatoire.")

    return {
        "id": str(assumption.get("id") or build_assumption_id(source_type, source_id, hypothesis)).strip(),
        "source_type": source_type,
        "source_id": source_id,
        "hypothesis": hypothesis,
        "status": status,
        "confidence_percent": clamp_int(assumption.get("confidence_percent"), 0, 100, 50),
        "importance": importance,
        "created_at": str(assumption.get("created_at") or now),
        "updated_at": str(assumption.get("updated_at") or now),
    }


def empty_assumption_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "assumptions": [],
    }


def build_assumption_id(source_type: str, source_id: str, hypothesis: str) -> str:
    return f"assumption-{source_type}-{slugify(source_id)}-{slugify(hypothesis)[:54]}"


def normalize_choice(value: Any, choices: set[str], default: str) -> str:
    candidate = str(value or default).strip().lower()
    return candidate if candidate in choices else default


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def slugify(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "item"
