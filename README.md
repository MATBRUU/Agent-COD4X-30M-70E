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
│   ├── roblox/
│   │   ├── concepts.json
│   │   └── trends.json
│   └── state.json
├── src/
│   ├── agent.py
│   ├── evaluator.py
│   ├── planner.py
│   └── roblox/
│       ├── concept_generator.py
│       ├── scoring_engine.py
│       └── trend_analyzer.py
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

## Roblox Intelligence V2.1

Le module Roblox analyse uniquement des donnees locales stockees dans `memory/roblox/`. Il ne scrape pas, ne publie pas et ne lance aucune action externe.

Fonctions :

- enregistrer des tendances Roblox locales ;
- generer des concepts inspires des tendances ;
- scorer les concepts selon potentiel viral, monetisation, difficulte de developpement et concurrence ;
- conserver uniquement les concepts ayant un score strictement superieur a 8/10 ;
- produire un rapport hebdomadaire local.

Commandes utiles :

```bash
python src/agent.py roblox-memory
python src/agent.py roblox-generate
python src/agent.py roblox-report
```

Ajouter une tendance locale :

```bash
python src/agent.py roblox-trend --name "Obby narratif court" --strength 8 --competition 4 --development-complexity 4 --signal "Sessions courtes" --mechanic "parcours a choix" --monetization "cosmetiques" --virality "fins partageables"
```

## Politique d'action

COD4X produit uniquement des analyses, propositions, scores, rapports et journaux locaux. Toute action qui toucherait a un compte, une publication, une transaction, un wallet, une API externe ou une depense doit rester hors perimetre tant qu'une validation humaine explicite et une couche d'execution separee n'ont pas ete definies.
