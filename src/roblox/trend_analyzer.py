"""Local Roblox trend memory and reporting."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRENDS_PATH = ROOT / "memory" / "roblox" / "trends.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_trend_memory(path: str | Path = DEFAULT_TRENDS_PATH) -> dict[str, Any]:
    trend_path = Path(path)
    if not trend_path.exists():
        return {
            "version": 1,
            "updated_at": utc_now(),
            "source_policy": "local_only",
            "trends": [],
        }
    return json.loads(trend_path.read_text(encoding="utf-8"))


def save_trend_memory(payload: dict[str, Any], path: str | Path = DEFAULT_TRENDS_PATH) -> None:
    trend_path = Path(path)
    trend_path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    temp_path = trend_path.with_suffix(trend_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(trend_path)


def register_trend(trend: dict[str, Any], path: str | Path = DEFAULT_TRENDS_PATH) -> dict[str, Any]:
    """Create or update a Roblox trend in local memory."""
    memory = load_trend_memory(path)
    normalized = normalize_trend(trend)
    trends = memory.setdefault("trends", [])

    for index, existing in enumerate(trends):
        if existing.get("id") == normalized["id"]:
            merged = {**existing, **normalized, "updated_at": utc_now()}
            trends[index] = merged
            save_trend_memory(memory, path)
            return merged

    trends.append(normalized)
    save_trend_memory(memory, path)
    return normalized


def list_trends(path: str | Path = DEFAULT_TRENDS_PATH) -> list[dict[str, Any]]:
    memory = load_trend_memory(path)
    return sorted(memory.get("trends", []), key=lambda item: int(item.get("strength", 0)), reverse=True)


def normalize_trend(trend: dict[str, Any]) -> dict[str, Any]:
    name = str(trend.get("name", "Untitled Roblox trend")).strip()
    trend_id = str(trend.get("id") or slugify(name)).strip()
    return {
        "id": trend_id,
        "name": name,
        "source": str(trend.get("source", "manual_local")).strip(),
        "detected_at": str(trend.get("detected_at", utc_now())),
        "strength": clamp_int(trend.get("strength"), 1, 10, default=6),
        "competition": clamp_int(trend.get("competition"), 1, 10, default=5),
        "development_complexity": clamp_int(trend.get("development_complexity"), 1, 10, default=5),
        "signals": normalize_list(trend.get("signals")),
        "audience": normalize_list(trend.get("audience")),
        "mechanics": normalize_list(trend.get("mechanics")),
        "monetization_vectors": normalize_list(trend.get("monetization_vectors")),
        "virality_drivers": normalize_list(trend.get("virality_drivers")),
        "risk_notes": normalize_list(trend.get("risk_notes")),
    }


def weekly_report(
    trends: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    decisions: list[dict[str, Any]] | None = None,
) -> str:
    """Return a local weekly Roblox intelligence report in Markdown."""
    decisions = decisions or []
    roblox_decisions = [
        decision
        for decision in decisions
        if str(decision.get("action_id", "")).startswith("roblox-")
        or "roblox" in str(decision.get("action_title", "")).lower()
    ]
    average = 0.0
    if concepts:
        average = round(sum(float(concept.get("score", 0)) for concept in concepts) / len(concepts), 1)

    lines = [
        "# Rapport hebdomadaire Roblox COD4X",
        "",
        f"- Genere le : {utc_now()}",
        f"- Tendances detectees : {len(trends)}",
        f"- Concepts conserves : {len(concepts)}",
        f"- Score moyen : {average}/10",
        f"- Decisions Roblox journalisees : {len(roblox_decisions)}",
        "",
        "## Top concepts",
    ]

    if concepts:
        for concept in sorted(concepts, key=lambda item: float(item.get("score", 0)), reverse=True)[:5]:
            lines.append(f"- {concept.get('title')} ({concept.get('score')}/10) : {concept.get('pitch')}")
    else:
        lines.append("- Aucun concept au-dessus du seuil pour cette semaine.")

    lines.extend(["", "## Signaux de tendances"])
    if trends:
        for trend in trends[:5]:
            signals = "; ".join(trend.get("signals", [])[:3])
            lines.append(f"- {trend.get('name')} - force {trend.get('strength')}/10 : {signals}")
    else:
        lines.append("- Aucune tendance locale enregistree.")

    lines.extend(
        [
            "",
            "## Garde-fous",
            "- Rapport local uniquement.",
            "- Aucune publication automatique.",
            "- Aucune action financiere reelle.",
            "- Toute action externe exige une validation humaine explicite.",
        ]
    )
    return "\n".join(lines)


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return f"roblox-{slug or 'trend'}"
