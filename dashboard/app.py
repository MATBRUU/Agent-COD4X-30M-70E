from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import Cod4xAgent  # noqa: E402


st.set_page_config(page_title="COD4X", page_icon="C4", layout="wide")

agent = Cod4xAgent(ROOT)
memory = agent.load_memory()
state = memory["state"]
metrics = state.get("metrics", {})

st.title("COD4X")
st.caption("Agent strategique local. Execution externe desactivee.")

policy = state.get("decision_policy", {})
if policy.get("requires_human_approval", True):
    st.warning("Validation humaine obligatoire avant toute action externe.", icon="!")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Idees revues", metrics.get("ideas_reviewed", 0))
col2.metric("Approuvees", metrics.get("actions_approved", 0))
col3.metric("Rejetees", metrics.get("actions_rejected", 0))
col4.metric("Differees", metrics.get("actions_deferred", 0))

tab_plan, tab_selection, tab_thesis, tab_reality, tab_experiments, tab_roblox, tab_learning, tab_memory, tab_log = st.tabs(
    ["Plan", "Selection", "Thesis Engine", "Reality Engine", "Experiments", "Roblox", "Learning", "Memoire", "Journal"]
)

with tab_plan:
    st.subheader("Actions hebdomadaires")
    actions = agent.propose_actions()

    for action in actions:
        with st.container(border=True):
            header_left, header_right = st.columns([4, 1])
            header_left.markdown(f"### {action['title']}")
            header_right.metric("Score", action["score"])

            st.write(action["rationale"])

            score_cols = st.columns(4)
            estimates = action["estimates"]
            score_cols[0].metric("Impact", estimates["impact"])
            score_cols[1].metric("Risque", estimates["risk"])
            score_cols[2].metric("Cout", estimates["cost"])
            score_cols[3].metric("Delai", estimates["delay"])

            st.write(f"**Prochaine etape locale :** {action['local_next_step']}")
            st.write(f"**Mesure de succes :** {action['success_metric']}")

            with st.form(key=f"decision-{action['id']}"):
                decision = st.selectbox(
                    "Decision",
                    options=["deferred", "approved", "rejected"],
                    format_func=lambda value: {
                        "approved": "Approuver",
                        "rejected": "Rejeter",
                        "deferred": "Differer",
                    }[value],
                )
                notes = st.text_area("Notes", placeholder="Contexte, conditions ou raison de la decision.")
                submitted = st.form_submit_button("Enregistrer")

                if submitted:
                    agent.log_decision(action=action, decision=decision, notes=notes)
                    st.success("Decision enregistree localement.")
                    st.rerun()

with tab_selection:
    st.subheader("Selection / Committee")
    st.caption("Priorisation strategique locale. Le module choisit une priorite, sans execution externe.")

    if st.button("Collecter les opportunites"):
        agent.collect_opportunities()
        st.success("Opportunites collectees depuis les memoires locales.")
        st.rerun()

    if st.button("Generer le rapport comite"):
        agent.generate_committee_report()
        st.success("Rapport comite genere localement.")
        st.rerun()

    selection_memory = agent.load_selection_memory()
    opportunities = selection_memory["opportunities"].get("opportunities", [])
    if not opportunities:
        opportunities = agent.collect_opportunities().get("opportunities", [])

    selection_result = agent.select_opportunity() if opportunities else {
        "top_opportunity": None,
        "alternatives_rejected": [],
        "watchlist": [],
        "blocked_opportunities": [],
    }
    top = selection_result.get("top_opportunity")

    st.markdown("### Top opportunity")
    if top:
        st.write(f"**{top.get('title')}**")
        metric_score, metric_conviction, metric_effort, metric_cost, metric_potential = st.columns(5)
        metric_score.metric("Score selection", top.get("selection_score"))
        metric_conviction.metric("Conviction", f"{top.get('confidence_percent')}%")
        metric_effort.metric("Effort estime", f"{top.get('estimated_effort_hours')} h")
        metric_cost.metric("Cout estime", f"{top.get('estimated_cost_eur')} EUR")
        metric_potential.metric("Potentiel", top.get("estimated_revenue_potential"))
        st.write(f"**Source :** {top.get('source_type')}")
        st.write(f"**Risque :** {top.get('risk_level')}/10")
        st.write(f"**Fit strategique :** {top.get('strategic_fit')}/10")
        st.warning("Validation humaine obligatoire avant toute action reelle.", icon="!")
    else:
        st.info("Aucune opportunite eligible. Lancez d'abord des actions ou enrichissez les memoires locales.")

    st.markdown("### Alternatives rejetees")
    rejected = selection_result.get("alternatives_rejected", [])
    if rejected:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "titre": item.get("title"),
                    "score_selection": item.get("selection_score"),
                    "risque": item.get("risk_level"),
                    "raison": " | ".join(item.get("rejection_reason", [])),
                }
                for item in rejected
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune alternative rejetee.")

    st.markdown("### Watchlist")
    watchlist = selection_result.get("watchlist", [])
    if watchlist:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "titre": item.get("title"),
                    "score_selection": item.get("selection_score"),
                    "effort": item.get("estimated_effort_hours"),
                    "raison": " | ".join(item.get("watch_reason", [])),
                }
                for item in watchlist
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune opportunite en surveillance.")

    st.markdown("### Blocked opportunities")
    blocked = selection_result.get("blocked_opportunities", [])
    if blocked:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "titre": item.get("title"),
                    "source": item.get("source_type"),
                    "raison": " | ".join(item.get("block_reason", [])),
                }
                for item in blocked
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune opportunite bloquee.")

    st.markdown("### Rapport comite")
    report = selection_memory["committee_report"].get("report", {})
    if report and report.get("opportunities_analyzed", 0):
        st.write(f"**Decision proposee :** {report.get('proposed_decision')}")
        st.write(report.get("choice_justification"))
        st.json(report)
    else:
        st.info("Aucun rapport comite genere pour l'instant.")

with tab_thesis:
    st.subheader("Thesis Engine")
    st.caption("Justification strategique locale. Le module explique une selection existante sans creer de concept.")

    if st.button("Generer une these"):
        thesis_result = agent.generate_thesis()
        if thesis_result.get("status") == "missing_selection":
            st.warning(thesis_result.get("message"))
        else:
            st.success("These generee et stockee localement.")
        st.rerun()

    thesis_memory = agent.load_thesis_memory()
    theses = thesis_memory.get("theses", [])
    latest_thesis = theses[-1] if theses else None

    if latest_thesis:
        st.markdown("### Opportunite retenue")
        st.write(f"**{latest_thesis.get('selected_opportunity')}**")
        thesis_score, thesis_decision, thesis_conviction = st.columns(3)
        thesis_score.metric("Score", latest_thesis.get("selection_score"))
        thesis_decision.metric("Decision", str(latest_thesis.get("decision", "")).upper())
        thesis_conviction.metric("Conviction", f"{latest_thesis.get('conviction')}%")

        st.markdown("### Resume executif")
        st.write(latest_thesis.get("executive_summary"))

        st.markdown("### Raisons du choix")
        for reason in latest_thesis.get("reasons", []):
            st.write(f"- {reason}")

        st.markdown("### Alternatives rejetees")
        alternatives = [
            item
            for item in latest_thesis.get("alternative_comparisons", [])
            if item.get("decision") == "rejected"
        ]
        if alternatives:
            st.dataframe(
                [
                    {
                        "titre": item.get("title"),
                        "score_selection": item.get("selection_score"),
                        "points_forts": " | ".join(item.get("points_forts", [])),
                        "points_faibles": " | ".join(item.get("points_faibles", [])),
                        "raison": " | ".join(item.get("raison_du_rejet", [])),
                    }
                    for item in alternatives
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Aucune alternative rejetee dans la derniere these.")

        st.markdown("### Pourquoi cette decision pourrait etre mauvaise ?")
        for counter in latest_thesis.get("counter_arguments", []):
            st.write(f"- {counter}")

        st.markdown("### Scenarios d'echec")
        for scenario in latest_thesis.get("failure_scenarios", []):
            st.write(f"- {scenario}")

        st.markdown("### Hypotheses fragiles")
        for assumption in latest_thesis.get("fragile_assumptions", []):
            st.write(f"- {assumption}")
    else:
        st.info("Aucune these generee. Lancez d'abord un rapport comite, puis genere une these.")

    st.markdown("### Historique des theses")
    if theses:
        st.dataframe(
            [
                {
                    "date": item.get("date"),
                    "opportunite": item.get("selected_opportunity"),
                    "decision": item.get("decision"),
                    "score": item.get("selection_score"),
                    "conviction": item.get("conviction"),
                }
                for item in theses
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Historique vide.")

with tab_reality:
    st.subheader("Reality Engine")
    st.caption("Qualification locale des croyances. Le module ne modifie ni scores, ni decisions.")

    if st.button("Actualiser le rapport Reality"):
        agent.generate_reality_report()
        st.success("Rapport Reality mis a jour localement.")
        st.rerun()

    reality_memory = agent.load_reality_memory()
    assumptions = reality_memory["assumptions"].get("assumptions", [])
    evidence_records = reality_memory["evidence"].get("evidence", [])
    reality_report = reality_memory["reality_report"].get("report", {})

    with st.expander("Ajouter une hypothese"):
        with st.form("reality-assumption-form"):
            source_type = st.selectbox(
                "Source",
                ["action", "roblox_concept", "roblox_spec", "thesis", "opportunity", "other"],
            )
            source_id = st.text_input("ID source")
            hypothesis = st.text_area("Hypothese")
            status = st.selectbox("Statut", ["unverified", "supported", "validated", "weakened", "invalidated", "unknown"])
            importance = st.selectbox("Importance", ["low", "medium", "high", "critical"], index=1)
            confidence = st.slider("Confiance", 0, 100, 50)
            submitted_assumption = st.form_submit_button("Enregistrer l'hypothese")

            if submitted_assumption:
                if not source_id.strip() or not hypothesis.strip():
                    st.error("ID source et hypothese sont obligatoires.")
                else:
                    agent.add_assumption(
                        {
                            "source_type": source_type,
                            "source_id": source_id,
                            "hypothesis": hypothesis,
                            "status": status,
                            "confidence_percent": confidence,
                            "importance": importance,
                        }
                    )
                    st.success("Hypothese enregistree localement.")
                    st.rerun()

    with st.expander("Ajouter une preuve locale"):
        assumption_options = [item.get("id") for item in assumptions]
        with st.form("reality-evidence-form"):
            if assumption_options:
                assumption_id = st.selectbox("Hypothese", assumption_options)
            else:
                assumption_id = st.text_input("ID hypothese")
            evidence_type = st.selectbox("Type de preuve", ["human_review", "local_test", "benchmark", "user_feedback", "metric", "note", "other"])
            strength = st.selectbox("Force", ["weak", "medium", "strong"], index=1)
            supports = st.checkbox("La preuve soutient l'hypothese", value=True)
            summary = st.text_area("Resume")
            submitted_evidence = st.form_submit_button("Enregistrer la preuve")

            if submitted_evidence:
                if not str(assumption_id).strip() or not summary.strip():
                    st.error("ID hypothese et resume sont obligatoires.")
                else:
                    agent.add_evidence(
                        {
                            "assumption_id": assumption_id,
                            "evidence_type": evidence_type,
                            "summary": summary,
                            "strength": strength,
                            "supports_hypothesis": supports,
                        }
                    )
                    st.success("Preuve enregistree localement.")
                    st.rerun()

    metric_total, metric_validated, metric_unverified, metric_invalidated, metric_reality = st.columns(5)
    metric_total.metric("Hypotheses", reality_report.get("total_assumptions", len(assumptions)))
    metric_validated.metric("Validees", reality_report.get("validated_assumptions", 0))
    metric_unverified.metric("Non verifiees", reality_report.get("unverified_assumptions", 0))
    metric_invalidated.metric("Invalidees", reality_report.get("invalidated_assumptions", 0))
    metric_reality.metric("Niveau", reality_report.get("global_reality_level", "unknown"))

    st.markdown("### Alertes")
    for alert in reality_report.get("alerts", ["Aucun rapport Reality genere."]):
        st.warning(alert, icon="!")

    st.markdown("### Hypotheses par statut")
    if assumptions:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "source": item.get("source_type"),
                    "source_id": item.get("source_id"),
                    "hypothese": item.get("hypothesis"),
                    "statut": item.get("status"),
                    "importance": item.get("importance"),
                    "confiance": item.get("confidence_percent"),
                }
                for item in assumptions
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune hypothese enregistree.")

    st.markdown("### Hypotheses critiques non verifiees")
    critical_unverified = reality_report.get("critical_unverified_assumptions", [])
    if critical_unverified:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "source_id": item.get("source_id"),
                    "hypothese": item.get("hypothesis"),
                    "confiance": item.get("confidence_percent"),
                }
                for item in critical_unverified
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Aucune hypothese critique non verifiee signalee.")

    st.markdown("### Preuves enregistrees")
    if evidence_records:
        st.dataframe(evidence_records, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune preuve locale enregistree.")

    st.markdown("### Decisions trop speculatives")
    speculative = reality_report.get("decisions_too_speculative", [])
    if speculative:
        st.dataframe(speculative, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune decision trop speculative detectee par le rapport actuel.")

    st.markdown("### Rapport Reality")
    st.json(reality_report)

with tab_experiments:
    st.subheader("Experiments")
    st.caption("Tests locaux des hypotheses fragiles. Les experiences produisent uniquement des preuves locales.")

    if st.button("Planifier les experiences"):
        agent.plan_experiments()
        st.success("Experiences locales generees depuis les hypotheses Reality.")
        st.rerun()

    if st.button("Actualiser le rapport experiments"):
        agent.generate_experiment_report()
        st.success("Rapport experiments mis a jour localement.")
        st.rerun()

    experiment_memory = agent.load_experiment_memory()
    experiments = experiment_memory["experiments"].get("experiments", [])
    experiment_report = experiment_memory["experiment_report"].get("report", {})
    assumptions_by_id = {
        item.get("id"): item
        for item in agent.load_reality_memory()["assumptions"].get("assumptions", [])
    }

    priority_experiments = experiment_report.get("priority_experiments", [])
    next_experiment = experiment_report.get("next_recommended_experiment")

    metric_plan, metric_done, metric_conclusive, metric_inconclusive, metric_untested = st.columns(5)
    metric_plan.metric("Planifiees", experiment_report.get("planned_experiments", 0))
    metric_done.metric("Terminees", experiment_report.get("completed_experiments", 0))
    metric_conclusive.metric("Concluantes", experiment_report.get("conclusive_experiments", 0))
    metric_inconclusive.metric("Non concluantes", experiment_report.get("inconclusive_experiments", 0))
    metric_untested.metric("Hypotheses non testees", len(experiment_report.get("untested_assumptions", [])))

    st.markdown("### Prochaine experience recommandee")
    if next_experiment:
        st.write(f"**{next_experiment.get('experiment_title')}**")
        st.write(next_experiment.get("objective"))
        cols_next = st.columns(4)
        cols_next[0].metric("Priorite", next_experiment.get("priority_score"))
        cols_next[1].metric("Effort", f"{next_experiment.get('estimated_effort_hours')} h")
        cols_next[2].metric("Cout", f"{next_experiment.get('estimated_cost_eur')} EUR")
        cols_next[3].metric("Statut", next_experiment.get("status"))
    else:
        st.info("Aucune experience recommandee. Lancez la planification ou ajoutez des hypotheses non verifiees.")

    st.markdown("### Experiences prioritaires")
    if priority_experiments:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "titre": item.get("experiment_title"),
                    "priorite": item.get("priority_score"),
                    "statut": item.get("status"),
                    "resultat": item.get("result"),
                    "effort": item.get("estimated_effort_hours"),
                    "cout": item.get("estimated_cost_eur"),
                    "hypothese": assumptions_by_id.get(item.get("assumption_id"), {}).get("hypothesis", item.get("assumption_id")),
                }
                for item in priority_experiments
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune experience prioritaire disponible.")

    st.markdown("### Toutes les experiences")
    if experiments:
        st.dataframe(
            [
                {
                    "id": item.get("id"),
                    "titre": item.get("experiment_title"),
                    "statut": item.get("status"),
                    "resultat": item.get("result"),
                    "priorite": item.get("priority_score"),
                    "effort": item.get("estimated_effort_hours"),
                    "cout": item.get("estimated_cost_eur"),
                    "hypothese": assumptions_by_id.get(item.get("assumption_id"), {}).get("hypothesis", item.get("assumption_id")),
                }
                for item in experiments
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune experience locale planifiee.")

    with st.expander("Mettre a jour une experience"):
        experiment_ids = [item.get("id") for item in experiments]
        with st.form("experiment-update-form"):
            if experiment_ids:
                experiment_id = st.selectbox("Experience", experiment_ids)
            else:
                experiment_id = st.text_input("ID experience")
            status = st.selectbox("Statut", ["planned", "in_progress", "completed", "abandoned"])
            result = st.selectbox("Resultat", ["unknown", "success", "failure", "inconclusive"])
            notes = st.text_area("Notes locales")
            submitted_experiment = st.form_submit_button("Enregistrer")

            if submitted_experiment:
                if not str(experiment_id).strip():
                    st.error("ID experience obligatoire.")
                else:
                    agent.update_experiment(
                        experiment_id=str(experiment_id),
                        updates={
                            "status": status,
                            "result": result,
                            "notes": notes,
                        },
                    )
                    if status == "completed":
                        st.success("Experience terminee, preuve locale creee et Reality regenere.")
                    else:
                        st.success("Experience mise a jour localement.")
                    st.rerun()

    st.markdown("### Rapport experiments")
    st.json(experiment_report)

with tab_roblox:
    st.subheader("Roblox Intelligence")
    st.caption("Analyse locale uniquement. Aucune publication ni automatisation externe.")

    roblox_memory = agent.load_roblox_memory()
    trends = roblox_memory["trends"].get("trends", [])
    concept_memory = roblox_memory["concepts"]
    concepts = concept_memory.get("concepts", [])
    if not concepts and trends:
        concept_memory = agent.generate_roblox_concepts()
        concepts = concept_memory.get("concepts", [])
    spec_memory = roblox_memory["specs"]
    specs = spec_memory.get("specs", [])
    if not specs and (concepts or trends):
        spec_memory = agent.generate_roblox_specs()
        specs = spec_memory.get("specs", [])

    average = 0.0
    if concepts:
        average = round(sum(float(concept.get("score", 0)) for concept in concepts) / len(concepts), 1)
    top_score = max((float(concept.get("score", 0)) for concept in concepts), default=0.0)

    metric_left, metric_mid, metric_specs, metric_right, metric_last = st.columns(5)
    metric_left.metric("Tendances", len(trends))
    metric_mid.metric("Concepts > 8/10", len(concepts))
    metric_specs.metric("Specs generees", len(specs))
    metric_right.metric("Score moyen", f"{average}/10")
    metric_last.metric("Top score", f"{top_score}/10")

    with st.expander("Enregistrer une tendance locale"):
        with st.form("roblox-trend-form"):
            trend_name = st.text_input("Nom de la tendance")
            trend_strength = st.slider("Force du signal", 1, 10, 7)
            trend_competition = st.slider("Concurrence", 1, 10, 5)
            trend_complexity = st.slider("Difficulte de developpement", 1, 10, 5)
            trend_signals = st.text_area("Signaux detectes", placeholder="Un signal par ligne.")
            trend_mechanics = st.text_area("Mecaniques", placeholder="Une mecanique par ligne.")
            trend_monetization = st.text_area("Pistes de monetisation", placeholder="Une piste locale par ligne.")
            trend_virality = st.text_area("Facteurs viraux", placeholder="Un facteur par ligne.")
            submitted_trend = st.form_submit_button("Enregistrer la tendance")

            if submitted_trend:
                if not trend_name.strip():
                    st.error("Le nom de la tendance est obligatoire.")
                else:
                    agent.register_roblox_trend(
                        {
                            "name": trend_name,
                            "strength": trend_strength,
                            "competition": trend_competition,
                            "development_complexity": trend_complexity,
                            "signals": trend_signals,
                            "mechanics": trend_mechanics,
                            "monetization_vectors": trend_monetization,
                            "virality_drivers": trend_virality,
                        }
                    )
                    agent.generate_roblox_concepts()
                    agent.generate_roblox_specs()
                    st.success("Tendance enregistree et concepts recalcules localement.")
                    st.rerun()

    if st.button("Regenerer les concepts Roblox"):
        agent.generate_roblox_concepts()
        agent.generate_roblox_specs()
        st.success("Concepts recalcules localement.")
        st.rerun()

    if st.button("Lancer le pipeline Roblox V2.2"):
        agent.run_roblox_pipeline()
        st.success("Pipeline local execute : tendances, concepts, scoring et specs.")
        st.rerun()

    st.markdown("### Tendances detectees")
    if trends:
        st.dataframe(
            [
                {
                    "nom": trend.get("name"),
                    "force": trend.get("strength"),
                    "concurrence": trend.get("competition"),
                    "difficulte": trend.get("development_complexity"),
                    "source": trend.get("source"),
                }
                for trend in trends
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune tendance Roblox locale enregistree.")

    st.markdown("### Concepts generes")
    if concepts:
        st.dataframe(
            [
                {
                    "titre": concept.get("title"),
                    "score": concept.get("score"),
                    "rating": concept.get("rating"),
                    "type": concept.get("type"),
                    "sources": ", ".join(concept.get("source_trend_ids", [])),
                }
                for concept in concepts
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucun concept ne depasse le seuil strict de 8/10.")

    st.markdown("### Top concepts")
    top_concepts = sorted(concepts, key=lambda item: float(item.get("score", 0)), reverse=True)[:3]
    if top_concepts:
        for concept in top_concepts:
            with st.container(border=True):
                top_left, top_right = st.columns([4, 1])
                top_left.markdown(f"#### {concept.get('title')}")
                top_right.metric("Score", concept.get("score"))
                st.write(concept.get("pitch"))
                st.write(f"**Boucle coeur :** {concept.get('core_loop')}")
                st.write(f"**Monetisation locale envisagee :** {', '.join(concept.get('monetization', []))}")

                inputs = concept.get("score_inputs", {})
                score_cols = st.columns(4)
                score_cols[0].metric("Viral", inputs.get("viral_potential"))
                score_cols[1].metric("Monetisation", inputs.get("monetization_potential"))
                score_cols[2].metric("Difficulte", inputs.get("development_difficulty"))
                score_cols[3].metric("Concurrence", inputs.get("competition"))

                with st.form(key=f"roblox-decision-{concept.get('id')}"):
                    decision = st.selectbox(
                        "Decision humaine",
                        options=["deferred", "approved", "rejected"],
                        format_func=lambda value: {
                            "approved": "Approuver",
                            "rejected": "Rejeter",
                            "deferred": "Differer",
                        }[value],
                    )
                    notes = st.text_area("Notes", key=f"roblox-notes-{concept.get('id')}")
                    submitted = st.form_submit_button("Journaliser")

                    if submitted:
                        agent.log_decision(action=concept, decision=decision, notes=notes)
                        st.success("Decision Roblox enregistree localement.")
                        st.rerun()
    else:
        st.info("Aucun top concept disponible.")

    st.markdown("### Roblox Specs")
    if specs:
        top_specs = sorted(specs, key=lambda item: float(item.get("score_final", 0)), reverse=True)
        top_spec = top_specs[0]
        st.write(f"**Top spec :** {top_spec.get('nom')} ({top_spec.get('score_final')}/10)")
        st.write(f"**Temps de developpement estime :** {top_spec.get('mvp', {}).get('temps_estime')}")
        st.write(f"**Scripts requis :** {', '.join(top_spec.get('mvp', {}).get('scripts_requis', []))}")

        monetisation = top_spec.get("monetisation", {})
        monetisation_rows = [
            {
                "type": "gamepasses",
                "propositions": ", ".join(monetisation.get("gamepasses", [])),
            },
            {
                "type": "dev_products",
                "propositions": ", ".join(monetisation.get("dev_products", [])),
            },
            {
                "type": "premium_benefits",
                "propositions": ", ".join(monetisation.get("premium_benefits", [])),
            },
        ]
        st.dataframe(monetisation_rows, use_container_width=True, hide_index=True)

        for spec in top_specs[:3]:
            with st.container(border=True):
                spec_left, spec_right = st.columns([4, 1])
                spec_left.markdown(f"#### {spec.get('nom')}")
                spec_right.metric("Score", spec.get("score_final"))
                st.write(f"**Genre :** {spec.get('genre')}")
                st.write(f"**Promesse joueur :** {spec.get('promesse_joueur')}")
                st.write(f"**Public cible :** {', '.join(spec.get('public_cible', []))}")
                st.write(f"**Core loop :** {spec.get('core_loop')}")
                st.write(f"**Meta progression :** {spec.get('meta_progression')}")
                st.write(f"**Premiere session :** {' | '.join(spec.get('premiere_session', []))}")
                st.write(f"**Retention J1 :** {' | '.join(spec.get('retention_j1', []))}")
                st.write(f"**Retention J7 :** {' | '.join(spec.get('retention_j7', []))}")
                st.write(f"**UI requise :** {', '.join(spec.get('mvp', {}).get('ui_requise', []))}")
                st.write(f"**Assets requis :** {', '.join(spec.get('mvp', {}).get('assets_requis', []))}")
                st.write(f"**Risques :** {' | '.join(spec.get('risques', []))}")
                st.write(f"**Concurrents :** {' | '.join(spec.get('concurrents', []))}")
    else:
        st.info("Aucune fiche de jeu generee.")

    st.markdown("### Rapport hebdomadaire")
    st.markdown(agent.build_roblox_report())

    st.markdown("### Historique des decisions")
    roblox_decisions = [
        decision
        for decision in agent.read_decisions()
        if str(decision.get("action_id", "")).startswith("roblox-")
        or "roblox" in str(decision.get("action_title", "")).lower()
    ]
    if roblox_decisions:
        st.dataframe(roblox_decisions, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune decision Roblox journalisee.")

with tab_learning:
    st.subheader("Learning")
    st.caption("Memoire locale des resultats et boucle d'apprentissage. Aucune action externe.")

    learning_memory = agent.load_learning_memory()
    outcomes = learning_memory["outcomes"].get("outcomes", [])
    report_payload = learning_memory["learning_report"]
    report = report_payload.get("report", {})
    rationales = learning_memory["score_rationales"].get("rationales", [])

    if st.button("Generer les convictions"):
        conviction_result = agent.generate_conviction_report()
        if conviction_result.get("status") == "missing_last_plan":
            st.warning(conviction_result.get("message"))
        else:
            st.success("Justifications de score generees localement.")
        st.rerun()

    if st.button("Actualiser le rapport learning"):
        agent.generate_learning_report()
        st.success("Rapport d'apprentissage mis a jour localement.")
        st.rerun()

    with st.expander("Enregistrer un resultat"):
        with st.form("learning-outcome-form"):
            source_type = st.selectbox("Type", ["action", "roblox_concept", "other"])
            source_id = st.text_input("ID source")
            title = st.text_input("Titre")
            initial_score = st.number_input("Score initial", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
            status = st.selectbox("Statut", ["not_started", "in_progress", "completed", "abandoned"])
            result = st.selectbox("Resultat", ["unknown", "success", "failure", "partial"])
            effort = st.number_input("Effort reel (heures)", min_value=0.0, value=0.0, step=0.5)
            cost = st.number_input("Cout reel (EUR)", min_value=0.0, value=0.0, step=1.0)
            revenue = st.number_input("Revenu reel (EUR)", min_value=0.0, value=0.0, step=1.0)
            feedback = st.text_area("Feedback qualitatif")
            reason_abandoned = st.text_area("Raison si abandon")
            submitted = st.form_submit_button("Enregistrer le resultat")

            if submitted:
                if not source_id.strip() or not title.strip():
                    st.error("ID source et titre sont obligatoires.")
                else:
                    agent.add_outcome(
                        {
                            "source_type": source_type,
                            "source_id": source_id,
                            "title": title,
                            "initial_score": initial_score,
                            "status": status,
                            "result": result,
                            "real_effort_hours": effort,
                            "real_cost_eur": cost,
                            "real_revenue_eur": revenue,
                            "qualitative_feedback": feedback,
                            "reason_if_abandoned": reason_abandoned,
                        }
                    )
                    agent.generate_learning_report()
                    st.success("Resultat enregistre localement.")
                    st.rerun()

    metric_a, metric_b, metric_c, metric_d, metric_e = st.columns(5)
    metric_a.metric("Idees suivies", report.get("ideas_tracked", len(outcomes)))
    metric_b.metric("Succes", report.get("success_count", 0))
    metric_c.metric("Echecs", report.get("failure_count", 0))
    metric_d.metric("Abandons", report.get("abandoned_count", 0))
    metric_e.metric("Effort total", f"{report.get('effort_total_hours', 0)} h")

    money_a, money_b, money_c = st.columns(3)
    money_a.metric("Cout total", f"{report.get('cost_total_eur', 0)} EUR")
    money_b.metric("Revenu total", f"{report.get('revenue_total_eur', 0)} EUR")
    money_c.metric("Taux de succes", f"{round(float(report.get('success_rate', 0)) * 100, 1)}%")

    st.markdown("### Outcomes enregistres")
    if outcomes:
        st.dataframe(outcomes, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun resultat enregistre pour l'instant.")

    st.markdown("### Score / resultat compare")
    comparisons = report.get("comparisons", [])
    if comparisons:
        st.dataframe(comparisons, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune comparaison disponible.")

    st.markdown("### Convictions de score")
    if rationales:
        st.dataframe(
            [
                {
                    "source_id": rationale.get("source_id"),
                    "score": rationale.get("score"),
                    "confidence": rationale.get("confidence_percent"),
                    "recommendation": rationale.get("recommendation"),
                    "positif": " | ".join(rationale.get("positive_factors", [])),
                    "negatif": " | ".join(rationale.get("negative_factors", [])),
                }
                for rationale in rationales
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune justification de score generee.")

    st.markdown("### Rapport d'apprentissage")
    st.json(report)

with tab_memory:
    st.subheader("Doctrine")
    st.markdown(memory["doctrine"])
    st.subheader("Etat")
    st.json(state)

with tab_log:
    st.subheader("Journal des decisions")
    decisions = agent.read_decisions()
    if decisions:
        st.dataframe(decisions, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune decision enregistree.")
