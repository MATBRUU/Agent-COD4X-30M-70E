"""Store local evidence linked to COD4X assumptions."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_PATH = ROOT / "memory" / "reality" / "evidence.json"

EVIDENCE_TYPES = {"human_review", "local_test", "benchmark", "user_feedback", "metric", "note", "other"}
STRENGTHS = {"weak", "medium", "strong"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_evidence_memory(path: str | Path = DEFAULT_EVIDENCE_PATH) -> dict[str, Any]:
    evidence_path = Path(path)
    if not evidence_path.exists():
        return empty_evidence_memory()
    return json.loads(evidence_path.read_text(encoding="utf-8"))


def save_evidence_memory(payload: dict[str, Any], path: str | Path = DEFAULT_EVIDENCE_PATH) -> None:
    evidence_path = Path(path)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = evidence_path.with_name(f"{evidence_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(evidence_path)


def list_evidence(path: str | Path = DEFAULT_EVIDENCE_PATH) -> list[dict[str, Any]]:
    memory = load_evidence_memory(path)
    return sorted(memory.get("evidence", []), key=lambda item: item.get("created_at", ""), reverse=True)


def add_evidence(
    evidence: dict[str, Any],
    path: str | Path = DEFAULT_EVIDENCE_PATH,
) -> dict[str, Any]:
    """Append one local evidence record."""
    memory = load_evidence_memory(path)
    records = memory.setdefault("evidence", [])
    normalized = normalize_evidence(evidence)
    records.append(normalized)
    save_evidence_memory(memory, path)
    return normalized


def evidence_index(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("assumption_id", "")), []).append(record)
    return grouped


def normalize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    assumption_id = str(evidence.get("assumption_id") or "").strip()
    summary = str(evidence.get("summary") or "").strip()
    if not assumption_id:
        raise ValueError("assumption_id est obligatoire.")
    if not summary:
        raise ValueError("summary est obligatoire.")

    evidence_type = normalize_choice(evidence.get("evidence_type"), EVIDENCE_TYPES, "note")
    strength = normalize_choice(evidence.get("strength"), STRENGTHS, "medium")
    created_at = str(evidence.get("created_at") or utc_now())
    return {
        "id": str(evidence.get("id") or build_evidence_id(assumption_id, created_at, summary)).strip(),
        "assumption_id": assumption_id,
        "evidence_type": evidence_type,
        "summary": summary,
        "strength": strength,
        "supports_hypothesis": to_bool(evidence.get("supports_hypothesis"), default=True),
        "created_at": created_at,
    }


def empty_evidence_memory() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": utc_now(),
        "source_policy": "local_only",
        "evidence": [],
    }


def build_evidence_id(assumption_id: str, created_at: str, summary: str) -> str:
    stamp = created_at.replace(":", "").replace("-", "").replace(".", "")
    return f"evidence-{slugify(assumption_id)[:48]}-{stamp}-{slugify(summary)[:24]}"


def normalize_choice(value: Any, choices: set[str], default: str) -> str:
    candidate = str(value or default).strip().lower()
    return candidate if candidate in choices else default


def to_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "oui", "support", "supports"}


def slugify(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "item"
