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

tab_plan, tab_memory, tab_log = st.tabs(["Plan", "Memoire", "Journal"])

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
