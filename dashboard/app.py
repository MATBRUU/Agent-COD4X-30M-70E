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

tab_plan, tab_roblox, tab_learning, tab_memory, tab_log = st.tabs(["Plan", "Roblox", "Learning", "Memoire", "Journal"])

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
