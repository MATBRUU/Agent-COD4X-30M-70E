"""COD4X local strategic agent."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .evaluator import score_actions
    from .experiments.experiment_planner import generate_and_store_experiments
    from .experiments.experiment_report import generate_and_store_experiment_report, load_experiment_report
    from .experiments.experiment_tracker import evidence_from_completed_experiment, list_experiments, load_experiment_memory, update_experiment
    from .learning.conviction_engine import collect_scored_sources, generate_and_store_rationales, load_rationale_memory
    from .learning.learning_loop import generate_learning_report, load_learning_report
    from .learning.outcome_tracker import add_or_update_outcome, list_outcomes, load_outcome_memory
    from .planner import propose_weekly_actions
    from .reality.assumption_tracker import add_or_update_assumption, extract_assumptions_from_thesis, list_assumptions, load_assumption_memory
    from .reality.evidence_engine import add_evidence, add_or_update_evidence, list_evidence, load_evidence_memory
    from .reality.reality_report import generate_and_store_reality_report, load_reality_report
    from .roblox.concept_generator import generate_and_store_concepts, load_concept_memory
    from .roblox.spec_generator import generate_and_store_specs, load_spec_memory
    from .roblox.trend_analyzer import load_trend_memory, register_trend, weekly_report
    from .selection.committee_report import generate_and_store_committee_report, load_committee_report
    from .selection.opportunity_collector import collect_and_store_opportunities, load_opportunity_memory
    from .selection.selection_engine import select_opportunities
    from .thesis.thesis_engine import generate_and_store_thesis, load_thesis_memory
except ImportError:  # Allows `python src/agent.py`.
    from evaluator import score_actions
    from experiments.experiment_planner import generate_and_store_experiments
    from experiments.experiment_report import generate_and_store_experiment_report, load_experiment_report
    from experiments.experiment_tracker import evidence_from_completed_experiment, list_experiments, load_experiment_memory, update_experiment
    from learning.conviction_engine import collect_scored_sources, generate_and_store_rationales, load_rationale_memory
    from learning.learning_loop import generate_learning_report, load_learning_report
    from learning.outcome_tracker import add_or_update_outcome, list_outcomes, load_outcome_memory
    from planner import propose_weekly_actions
    from reality.assumption_tracker import add_or_update_assumption, extract_assumptions_from_thesis, list_assumptions, load_assumption_memory
    from reality.evidence_engine import add_evidence, add_or_update_evidence, list_evidence, load_evidence_memory
    from reality.reality_report import generate_and_store_reality_report, load_reality_report
    from roblox.concept_generator import generate_and_store_concepts, load_concept_memory
    from roblox.spec_generator import generate_and_store_specs, load_spec_memory
    from roblox.trend_analyzer import load_trend_memory, register_trend, weekly_report
    from selection.committee_report import generate_and_store_committee_report, load_committee_report
    from selection.opportunity_collector import collect_and_store_opportunities, load_opportunity_memory
    from selection.selection_engine import select_opportunities
    from thesis.thesis_engine import generate_and_store_thesis, load_thesis_memory


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
        self.roblox_specs_path = self.roblox_memory_dir / "specs.json"
        self.learning_memory_dir = self.memory_dir / "learning"
        self.outcomes_path = self.learning_memory_dir / "outcomes.json"
        self.score_rationales_path = self.learning_memory_dir / "score_rationales.json"
        self.learning_report_path = self.learning_memory_dir / "learning_report.json"
        self.selection_memory_dir = self.memory_dir / "selection"
        self.opportunities_path = self.selection_memory_dir / "opportunities.json"
        self.committee_report_path = self.selection_memory_dir / "committee_report.json"
        self.thesis_memory_dir = self.memory_dir / "thesis"
        self.theses_path = self.thesis_memory_dir / "theses.json"
        self.reality_memory_dir = self.memory_dir / "reality"
        self.assumptions_path = self.reality_memory_dir / "assumptions.json"
        self.evidence_path = self.reality_memory_dir / "evidence.json"
        self.reality_report_path = self.reality_memory_dir / "reality_report.json"
        self.experiments_memory_dir = self.memory_dir / "experiments"
        self.experiments_path = self.experiments_memory_dir / "experiments.json"
        self.experiment_report_path = self.experiments_memory_dir / "experiment_report.json"

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
            "specs": load_spec_memory(self.roblox_specs_path),
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

    def generate_roblox_specs(self) -> dict[str, Any]:
        """Generate Roblox game specs from high-scoring concepts."""
        return generate_and_store_specs(
            concepts_path=self.roblox_concepts_path,
            specs_path=self.roblox_specs_path,
        )

    def run_roblox_pipeline(self) -> dict[str, Any]:
        """Run the full local Roblox V2.2 pipeline."""
        trends = load_trend_memory(self.roblox_trends_path)
        concepts = self.generate_roblox_concepts()
        specs = self.generate_roblox_specs()
        return {
            "source_policy": "local_only",
            "external_execution": False,
            "steps": [
                "analyse_tendances_locales",
                "generation_concepts",
                "scoring_concepts",
                "generation_specs",
            ],
            "trends": trends,
            "concepts": concepts,
            "specs": specs,
        }

    def build_roblox_report(self) -> str:
        """Build a local weekly Roblox report."""
        memory = self.load_roblox_memory()
        return weekly_report(
            trends=memory["trends"].get("trends", []),
            concepts=memory["concepts"].get("concepts", []),
            decisions=self.read_decisions(),
        )

    def load_learning_memory(self) -> dict[str, Any]:
        """Read local learning memory."""
        return {
            "outcomes": load_outcome_memory(self.outcomes_path),
            "score_rationales": load_rationale_memory(self.score_rationales_path),
            "learning_report": load_learning_report(self.learning_report_path),
        }

    def add_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """Add or update one local outcome record."""
        return add_or_update_outcome(outcome, self.outcomes_path)

    def list_outcomes(self) -> list[dict[str, Any]]:
        """List local outcome records."""
        return list_outcomes(self.outcomes_path)

    def generate_conviction_report(self) -> dict[str, Any]:
        """Generate rationales from the last saved plan and Roblox concepts."""
        state = self._read_json(self.state_path)
        actions = state.get("last_plan", [])
        if not actions:
            return {
                "status": "missing_last_plan",
                "message": "Aucun last_plan disponible. Lancez d'abord: python src/agent.py actions",
                "source_policy": "local_only",
                "external_execution": False,
                "rationales": [],
            }
        roblox_memory = self.load_roblox_memory()
        concepts = roblox_memory["concepts"].get("concepts", [])
        sources = collect_scored_sources(actions=actions, roblox_concepts=concepts)
        return generate_and_store_rationales(sources, self.score_rationales_path)

    def generate_learning_report(self) -> dict[str, Any]:
        """Generate a local report comparing scores, decisions and outcomes."""
        return generate_learning_report(
            outcomes_path=self.outcomes_path,
            decisions=self.read_decisions(),
            report_path=self.learning_report_path,
        )

    def load_selection_memory(self) -> dict[str, Any]:
        """Read local opportunity selection memory."""
        return {
            "opportunities": load_opportunity_memory(self.opportunities_path),
            "committee_report": load_committee_report(self.committee_report_path),
        }

    def collect_opportunities(self) -> dict[str, Any]:
        """Collect existing opportunities without creating new concepts."""
        return collect_and_store_opportunities(
            state_path=self.state_path,
            concepts_path=self.roblox_concepts_path,
            specs_path=self.roblox_specs_path,
            outcomes_path=self.outcomes_path,
            rationales_path=self.score_rationales_path,
            opportunities_path=self.opportunities_path,
        )

    def select_opportunity(self) -> dict[str, Any]:
        """Select one top opportunity from the current local opportunity memory."""
        opportunities = self.collect_opportunities().get("opportunities", [])
        return select_opportunities(opportunities)

    def generate_committee_report(self) -> dict[str, Any]:
        """Generate a local non-financial committee report."""
        opportunities = self.collect_opportunities().get("opportunities", [])
        doctrine = self.doctrine_path.read_text(encoding="utf-8")
        return generate_and_store_committee_report(
            opportunities=opportunities,
            doctrine=doctrine,
            path=self.committee_report_path,
        )

    def load_thesis_memory(self) -> dict[str, Any]:
        """Read local thesis history."""
        return load_thesis_memory(self.theses_path)

    def generate_thesis(self) -> dict[str, Any]:
        """Generate a thesis from the current committee report."""
        committee_report = load_committee_report(self.committee_report_path)
        thesis = generate_and_store_thesis(
            committee_report=committee_report,
            path=self.theses_path,
        )
        if thesis.get("status") != "missing_selection":
            extract_assumptions_from_thesis(thesis, self.assumptions_path)
            self.generate_reality_report()
        return thesis

    def load_reality_memory(self) -> dict[str, Any]:
        """Read local Reality Engine memory."""
        return {
            "assumptions": load_assumption_memory(self.assumptions_path),
            "evidence": load_evidence_memory(self.evidence_path),
            "reality_report": load_reality_report(self.reality_report_path),
        }

    def list_assumptions(self) -> list[dict[str, Any]]:
        """List local assumptions."""
        return list_assumptions(self.assumptions_path)

    def list_evidence(self) -> list[dict[str, Any]]:
        """List local evidence records."""
        return list_evidence(self.evidence_path)

    def add_assumption(self, assumption: dict[str, Any]) -> dict[str, Any]:
        """Add or update one local assumption."""
        record = add_or_update_assumption(assumption, self.assumptions_path)
        self.generate_reality_report()
        return record

    def add_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Add one local evidence record."""
        record = add_evidence(evidence, self.evidence_path)
        self.generate_reality_report()
        return record

    def generate_reality_report(self) -> dict[str, Any]:
        """Generate a local report about assumption solidity."""
        return generate_and_store_reality_report(
            assumptions_path=self.assumptions_path,
            evidence_path=self.evidence_path,
            theses_path=self.theses_path,
            report_path=self.reality_report_path,
        )

    def load_experiment_memory(self) -> dict[str, Any]:
        """Read local experiment memory."""
        return {
            "experiments": load_experiment_memory(self.experiments_path),
            "experiment_report": load_experiment_report(self.experiment_report_path),
        }

    def list_experiments(self) -> list[dict[str, Any]]:
        """List local experiments."""
        return list_experiments(self.experiments_path)

    def plan_experiments(self) -> dict[str, Any]:
        """Generate local experiments from fragile Reality assumptions."""
        experiments = generate_and_store_experiments(
            assumptions_path=self.assumptions_path,
            evidence_path=self.evidence_path,
            experiments_path=self.experiments_path,
        )
        self.generate_experiment_report()
        return experiments

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update one experiment and create evidence when it is completed."""
        experiment = update_experiment(experiment_id, updates, self.experiments_path)
        evidence = evidence_from_completed_experiment(experiment)
        if evidence:
            add_or_update_evidence(evidence, self.evidence_path)
            self.generate_reality_report()
        self.generate_experiment_report()
        return experiment

    def generate_experiment_report(self) -> dict[str, Any]:
        """Generate the local experiment report."""
        return generate_and_store_experiment_report(
            experiments_path=self.experiments_path,
            assumptions_path=self.assumptions_path,
            report_path=self.experiment_report_path,
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
    subparsers.add_parser("opportunities", help="Collect local opportunities")
    subparsers.add_parser("select-opportunity", help="Select one strategic opportunity")
    subparsers.add_parser("committee-report", help="Generate the local committee report")
    subparsers.add_parser("thesis", help="Generate a strategic thesis from the current committee report")
    subparsers.add_parser("thesis-history", help="Read local thesis history")
    subparsers.add_parser("assumptions", help="List local assumptions")
    subparsers.add_parser("reality-report", help="Generate the local Reality report")
    subparsers.add_parser("experiments", help="List local experiments")
    subparsers.add_parser("experiment-plan", help="Generate local experiments from Reality assumptions")
    subparsers.add_parser("experiment-report", help="Generate the local experiment report")
    subparsers.add_parser("outcome-list", help="List tracked outcomes")
    subparsers.add_parser("conviction-report", help="Generate score rationales")
    subparsers.add_parser("learning-report", help="Generate the local learning report")
    subparsers.add_parser("learning-memory", help="Read local learning memory")
    subparsers.add_parser("roblox-memory", help="Read local Roblox memory")
    subparsers.add_parser("roblox-generate", help="Generate and score Roblox concepts")
    subparsers.add_parser("roblox-specs", help="Generate Roblox game specs")
    subparsers.add_parser("roblox-pipeline", help="Run local Roblox trend, concept and spec pipeline")
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

    outcome_parser = subparsers.add_parser("outcome-add", help="Add or update one tracked outcome")
    outcome_parser.add_argument("--source-type", required=True, choices=["action", "roblox_concept", "other"])
    outcome_parser.add_argument("--source-id", required=True)
    outcome_parser.add_argument("--title", required=True)
    outcome_parser.add_argument("--initial-score", type=float, default=0.0)
    outcome_parser.add_argument("--status", choices=["not_started", "in_progress", "completed", "abandoned"], default="not_started")
    outcome_parser.add_argument("--result", choices=["unknown", "success", "failure", "partial"], default="unknown")
    outcome_parser.add_argument("--real-effort-hours", type=float, default=0.0)
    outcome_parser.add_argument("--real-cost-eur", type=float, default=0.0)
    outcome_parser.add_argument("--real-revenue-eur", type=float, default=0.0)
    outcome_parser.add_argument("--qualitative-feedback", default="")
    outcome_parser.add_argument("--reason-if-abandoned", default="")

    assumption_parser = subparsers.add_parser("assumption-add", help="Add or update one local assumption")
    assumption_parser.add_argument("--source-type", required=True, choices=["action", "roblox_concept", "roblox_spec", "thesis", "opportunity", "other"])
    assumption_parser.add_argument("--source-id", required=True)
    assumption_parser.add_argument("--hypothesis", required=True)
    assumption_parser.add_argument("--status", choices=["unverified", "supported", "validated", "weakened", "invalidated", "unknown"], default="unverified")
    assumption_parser.add_argument("--confidence-percent", type=int, default=50)
    assumption_parser.add_argument("--importance", choices=["low", "medium", "high", "critical"], default="medium")

    evidence_parser = subparsers.add_parser("evidence-add", help="Add local evidence for one assumption")
    evidence_parser.add_argument("--assumption-id", required=True)
    evidence_parser.add_argument("--evidence-type", choices=["human_review", "local_test", "benchmark", "user_feedback", "metric", "note", "other"], default="note")
    evidence_parser.add_argument("--summary", required=True)
    evidence_parser.add_argument("--strength", choices=["weak", "medium", "strong"], default="medium")
    evidence_parser.add_argument("--supports-hypothesis", choices=["true", "false"], default="true")

    experiment_update_parser = subparsers.add_parser("experiment-update", help="Update one local experiment")
    experiment_update_parser.add_argument("--experiment-id", required=True)
    experiment_update_parser.add_argument("--status", choices=["planned", "in_progress", "completed", "abandoned"])
    experiment_update_parser.add_argument("--result", choices=["unknown", "success", "failure", "inconclusive"])
    experiment_update_parser.add_argument("--notes", default=None)
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

    if args.command == "opportunities":
        print(json.dumps(agent.collect_opportunities(), indent=2, ensure_ascii=False))
        return

    if args.command == "select-opportunity":
        print(json.dumps(agent.select_opportunity(), indent=2, ensure_ascii=False))
        return

    if args.command == "committee-report":
        print(json.dumps(agent.generate_committee_report(), indent=2, ensure_ascii=False))
        return

    if args.command == "thesis":
        print(json.dumps(agent.generate_thesis(), indent=2, ensure_ascii=False))
        return

    if args.command == "thesis-history":
        print(json.dumps(agent.load_thesis_memory(), indent=2, ensure_ascii=False))
        return

    if args.command == "assumptions":
        print(json.dumps(agent.list_assumptions(), indent=2, ensure_ascii=False))
        return

    if args.command == "assumption-add":
        assumption = agent.add_assumption(
            {
                "source_type": args.source_type,
                "source_id": args.source_id,
                "hypothesis": args.hypothesis,
                "status": args.status,
                "confidence_percent": args.confidence_percent,
                "importance": args.importance,
            }
        )
        print(json.dumps(assumption, indent=2, ensure_ascii=False))
        return

    if args.command == "evidence-add":
        evidence = agent.add_evidence(
            {
                "assumption_id": args.assumption_id,
                "evidence_type": args.evidence_type,
                "summary": args.summary,
                "strength": args.strength,
                "supports_hypothesis": args.supports_hypothesis == "true",
            }
        )
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return

    if args.command == "reality-report":
        print(json.dumps(agent.generate_reality_report(), indent=2, ensure_ascii=False))
        return

    if args.command == "experiments":
        print(json.dumps(agent.list_experiments(), indent=2, ensure_ascii=False))
        return

    if args.command == "experiment-plan":
        print(json.dumps(agent.plan_experiments(), indent=2, ensure_ascii=False))
        return

    if args.command == "experiment-update":
        experiment = agent.update_experiment(
            experiment_id=args.experiment_id,
            updates={
                "status": args.status,
                "result": args.result,
                "notes": args.notes,
            },
        )
        print(json.dumps(experiment, indent=2, ensure_ascii=False))
        return

    if args.command == "experiment-report":
        print(json.dumps(agent.generate_experiment_report(), indent=2, ensure_ascii=False))
        return

    if args.command == "outcome-list":
        print(json.dumps(agent.list_outcomes(), indent=2, ensure_ascii=False))
        return

    if args.command == "outcome-add":
        outcome = agent.add_outcome(
            {
                "source_type": args.source_type,
                "source_id": args.source_id,
                "title": args.title,
                "initial_score": args.initial_score,
                "status": args.status,
                "result": args.result,
                "real_effort_hours": args.real_effort_hours,
                "real_cost_eur": args.real_cost_eur,
                "real_revenue_eur": args.real_revenue_eur,
                "qualitative_feedback": args.qualitative_feedback,
                "reason_if_abandoned": args.reason_if_abandoned,
            }
        )
        agent.generate_learning_report()
        print(json.dumps(outcome, indent=2, ensure_ascii=False))
        return

    if args.command == "conviction-report":
        print(json.dumps(agent.generate_conviction_report(), indent=2, ensure_ascii=False))
        return

    if args.command == "learning-report":
        print(json.dumps(agent.generate_learning_report(), indent=2, ensure_ascii=False))
        return

    if args.command == "learning-memory":
        print(json.dumps(agent.load_learning_memory(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-memory":
        print(json.dumps(agent.load_roblox_memory(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-generate":
        print(json.dumps(agent.generate_roblox_concepts(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-specs":
        print(json.dumps(agent.generate_roblox_specs(), indent=2, ensure_ascii=False))
        return

    if args.command == "roblox-pipeline":
        print(json.dumps(agent.run_roblox_pipeline(), indent=2, ensure_ascii=False))
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
