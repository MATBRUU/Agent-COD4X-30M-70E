# COD4X MVP

COD4X est un agent strategique local oriente creation de revenus numeriques. Cette V1 ne publie rien, ne connecte aucun wallet en ecriture, ne declenche aucune action financiere reelle et exige une validation humaine avant toute action externe.

## Objectif

Construire un socle minimal pour :

- lire une memoire persistante locale ;
- proposer 3 actions hebdomadaires ;
- scorer ces actions selon impact, risque, cout et delai ;
- enregistrer les decisions humaines ;
- afficher un dashboard local simple.

## Garde-fous V1

- Aucune action financiere reelle.
- Aucune publication automatique.
- Aucune connexion wallet en ecriture.
- Aucune execution externe autonome.
- Les decisions sont journalisees localement dans `logs/decisions.jsonl`.
- La memoire est stockee dans `memory/` sous forme Markdown et JSON, donc versionnable.

## Structure

```text
.
├── dashboard/
│   └── app.py
├── logs/
│   └── decisions.jsonl
├── memory/
│   ├── doctrine.md
│   └── state.json
├── src/
│   ├── agent.py
│   ├── evaluator.py
│   └── planner.py
├── README.md
└── requirements.txt
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancer le dashboard

```bash
streamlit run dashboard/app.py
```

## Utilisation en ligne de commande

Afficher la memoire :

```bash
python src/agent.py memory
```

Proposer et scorer les actions hebdomadaires :

```bash
python src/agent.py actions
```

Enregistrer une decision humaine :

```bash
python src/agent.py decide --action-id cod4x-weekly-offer-map --decision approved --notes "Validation locale uniquement."
```

## Politique d'action

COD4X V1 produit uniquement des analyses, propositions, scores et journaux locaux. Toute action qui toucherait a un compte, une publication, une transaction, un wallet, une API externe ou une depense doit rester hors perimetre tant qu'une validation humaine explicite et une couche d'execution separee n'ont pas ete definies.
