"""COD4X local strategic agent."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .evaluator import score_actions
    from .planner import propose_weekly_actions
    from .roblox.concept_generator import generate_and_store_concepts, load_concept_memory
    from .roblox.trend_analyzer import load_trend_memory, register_trend, weekly_report
except ImportError:  # Allows `python src/agent.py`.
    from evaluator import score_actions
    from planner import propose_weekly_actions
    from roblox.concept_generator import generate_and_store_concepts, load_concept_memory
    from roblox.trend_analyzer import load_trend_memory, register_trend, weekly_report


VALID_DECISIONS = {"approved", "rejected", "deferred"}


class Cod4xAgent:
    """Local-only agent facade for memory, planning, scoring and decisions."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        self.base_path = Path(base_path) if base_path else Path(__file__).resolve().parents[1]
        self.memory_dir = self.base_path / "memory"
        self.logs_dir = self.base_path / "logs"
        self.doctrine_path = self.memory_dir / "doctrine.md"
        self.state_path = self.memory_dir / "state.json"
        self.decisions_path = self.logs_dir / "decisions.jsonl"
        self.roblox_memory_dir = self.memory_dir / "roblox"
        self.roblox_trends_path = self.roblox_memory_dir / "trends.json"
        self.roblox_concepts_path = self.roblox_memory_dir / "concepts.json"

    def load_memory(self) -> dict[str, Any]:
        """Read persistent local memory."""
        return {
            "doctrine": self.doctrine_path.read_text(encoding="utf-8"),
            "state": self._read_json(self.state_path),
            "decisions": self.read_decisions(),
        }

    def propose_actions(self) -> list[dict[str, Any]]:
        """Create and score three weekly local-only actions."""
        memory = self.load_memory()
        actions = propose_weekly_actions(memory["state"], memory["doctrine"])
        scored_actions = score_actions(actions)
        state = memory["state"]
        state["last_plan"] = scored_actions
        state["updated_at"] = utc_now()
        self._write_json(self.state_path, state)
        return scored_actions

    def load_roblox_memory(self) -> dict[str, Any]:
        """Read Roblox trend and concept memory."""
        return {
            "trends": load_trend_memory(self.roblox_trends_path),
            "concepts": load_concept_memory(self.roblox_concepts_path),
        }

    def register_roblox_trend(self, trend: dict[str, Any]) -> dict[str, Any]:
        """Register one Roblox trend locally."""
        return register_trend(trend, self.roblox_trends_path)

    def generate_roblox_concepts(self) -> dict[str, Any]:
        """Generate, score and persist Roblox concepts above 8/10."""
        return generate_and_store_concepts(
            trends_path=self.roblox_trends_path,
            concepts_path=self.roblox_concepts_path,
        )

    def build_roblox_report(self) -> str:
        """Build a local weekly Roblox report."""
        memory = self.load_roblox_memory()
        return weekly_report(
            trends=memory["trends"].get("trends", []),
            concepts=memory["concepts"].get("concepts", []),
            decisions=self.read_decisions(),
        )

    def read_decisions(self) -> list[dict[str, Any]]:
        """Read the JSONL decision journal."""
        if not self.decisions_path.exists():
            return []

        decisions: list[dict[str, Any]] = []
        for line_number, line in enumerate(self.decisions_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                decisions.append(json.loads(line))
            except json.JSONDecodeError:
                decisions.append(
                    {
                        "timestamp": utc_now(),
                        "decision": "parse_error",
                        "line_number": line_number,
                        "raw": line,
                        "external_execution": False,
                    }
                )
        return decisions

    def log_decision(
        self,
        action: dict[str, Any],
        decision: str,
        notes: str = "",
        actor: str = "human",
    ) -> dict[str, Any]:
        """Append a human decision to the local journal and update metrics."""
        normalized_decision = decision.strip().lower()
        if normalized_decision not in VALID_DECISIONS:
            valid = ", ".join(sorted(VALID_DECISIONS))
            raise ValueError(f"Invalid decision '{decision}'. Expected one of: {valid}.")

        record = {
            "timestamp": utc_now(),
            "actor": actor,
            "decision": normalized_decision,
            "action_id": action.get("id", "unknown"),
            "action_title": action.get("title", "Unknown action"),
            "score": action.get("score"),
            "notes": notes,
            "requires_human_validation": True,
            "external_execution": False,
        }

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        with self.decisions_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._update_decision_metrics(normalized_decision)
        return record

    def _update_decision_metrics(self, decision: str) -> None:
        state = self._read_json(self.state_path)
        metrics = state.setdefault("metrics", {})
        metrics["ideas_reviewed"] = int(metrics.get("ideas_reviewed", 0)) + 1
        metric_name = f"actions_{decision}"
        metrics[metric_name] = int(metrics.get(metric_name, 0)) + 1
        state["last_decision_at"] = utc_now()
        state["updated_at"] = utc_now()
        self._write_json(self.state_path, state)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp_path.replace(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="COD4X local strategic agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("memory", help="Read local memory")
    subparsers.add_parser("actions", help="Propose and score weekly actions")
    subparsers.add_parser("roblox-memory", help="Read local Roblox memory")
    subparsers.add_parser("roblox-generate", help="Generate and score Roblox concepts")
    subparsers.add_parser("roblox-report", help="Print the weekly Roblox report")

    roblox_trend_parser = subparsers.add_parser("roblox-trend", help="Register a local Roblox trend")
    roblox_trend_parser.add_argument("--name", required=True)
    roblox_trend_parser.add_argument("--strength", type=int, default=6)
    roblox_trend_parser.add_argument("--competition", type=int, default=5)
    roblox_trend_parser.add_argument("--development-complexity", type=int, default=5)
    roblox_trend_parser.add_argument("--signal", action="append", default=[])
    roblox_trend_parser.add_argument("--mechanic", action="append", default=[])
    roblox_trend_parser.add_argument("--monetization", action="append", default=[])
    roblox_trend_parser.add_argument("--virality", action="append", default=[])

    decide_parser = subparsers.add_parser("decide", help="Log a human decision")
    decide_parser.add_argument("--action-id", required=True)
    decide_parser.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS))
    decide_parser.add_argument("--notes", default="")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    agent = Cod4xAgent()

    if args.command == "memory":
        print(json.dumps(agent.load_memory(), indent=2, ensure_ascii=False))
        return

    if args.command == "actions":
        actions = agent.propose_actions()
        print(json.dumps(actions, indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-memory":
        print(json.dumps(agent.load_roblox_memory(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-generate":
        print(json.dumps(agent.generate_roblox_concepts(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-report":
        print(agent.build_roblox_report())
        return

    if args.command == "roblox-trend":
        trend = agent.register_roblox_trend(
            {
                "name": args.name,
                "strength": args.strength,
                "competition": args.competition,
                "development_complexity": args.development_complexity,
                "signals": args.signal,
                "mechanics": args.mechanic,
                "monetization_vectors": args.monetization,
                "virality_drivers": args.virality,
            }
        )
        print(json.dumps(trend, indent=2, ensure_ascii=False))
        return

    if args.command == "decide":
        actions = agent.propose_actions()
        action = next((item for item in actions if item["id"] == args.action_id), {"id": args.action_id})
        record = agent.log_decision(action=action, decision=args.decision, notes=args.notes)
        print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
