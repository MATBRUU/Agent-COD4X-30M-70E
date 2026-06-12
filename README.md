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
|-- dashboard/
|   `-- app.py
|-- logs/
|   `-- decisions.jsonl
|-- memory/
|   |-- doctrine.md
|   |-- learning/
|   |   |-- learning_report.json
|   |   |-- outcomes.json
|   |   `-- score_rationales.json
|   |-- roblox/
|   |   |-- concepts.json
|   |   |-- specs.json
|   |   `-- trends.json
|   `-- state.json
|-- src/
|   |-- agent.py
|   |-- evaluator.py
|   |-- learning/
|   |   |-- conviction_engine.py
|   |   |-- learning_loop.py
|   |   `-- outcome_tracker.py
|   |-- planner.py
|   `-- roblox/
|       |-- concept_generator.py
|       |-- spec_generator.py
|       |-- scoring_engine.py
|       `-- trend_analyzer.py
|-- README.md
`-- requirements.txt
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

## Learning V1.1

COD4X V1.1 ajoute une memoire des resultats et une boucle d'apprentissage locale. L'objectif est de ne plus seulement generer des idees, mais aussi de suivre ce qui se passe apres une decision humaine : effort reel, cout reel, revenu reel, succes, echec, abandon ou resultat partiel.

### Stabilisation V1.1.1

V1.1.1 stabilise le coeur Learning avant les extensions V2.2. Le rapport de conviction lit uniquement le dernier plan sauvegarde dans `memory/state.json` (`last_plan`) et ne regenere pas les actions. Si aucun plan n'existe encore, lancer d'abord :

```bash
python src/agent.py actions
```

Cette separation evite qu'un simple rapport modifie `state.json`.

### Memoire des resultats

Les resultats sont stockes dans `memory/learning/outcomes.json`.

Chaque outcome contient :

- id ;
- source_type : action, roblox_concept ou other ;
- source_id ;
- title ;
- initial_score ;
- status : not_started, in_progress, completed ou abandoned ;
- result : unknown, success, failure ou partial ;
- real_effort_hours ;
- real_cost_eur ;
- real_revenue_eur ;
- qualitative_feedback ;
- reason_if_abandoned ;
- created_at et updated_at.

Ajouter ou mettre a jour un resultat :

```bash
python src/agent.py outcome-add --source-type action --source-id cod4x-weekly-offer-map --title "Cartographier une micro-offre numerique" --initial-score 9.7 --status completed --result partial --real-effort-hours 2 --real-cost-eur 0 --real-revenue-eur 0 --qualitative-feedback "Fiche creee, validation marche a faire."
```

Lister les resultats :

```bash
python src/agent.py outcome-list
```

### Systeme de conviction

Les justifications de score sont stockees dans `memory/learning/score_rationales.json`. Elles expliquent pourquoi une action ou un concept obtient son score.

Chaque rationale contient :

- source_id ;
- score ;
- confidence_percent ;
- positive_factors ;
- negative_factors ;
- assumptions ;
- risk_notes ;
- recommendation : pursue, watch ou reject ;
- generated_at.

Generer les justifications :

```bash
python src/agent.py conviction-report
```

Afficher toute la memoire Learning :

```bash
python src/agent.py learning-memory
```

### Boucle d'apprentissage

Le rapport local est stocke dans `memory/learning/learning_report.json`. Il compare :

- score initial ;
- decision humaine ;
- resultat reel ;
- effort reel ;
- cout reel ;
- revenu reel.

Le rapport produit :

- nombre d'idees suivies ;
- taux de succes ;
- taux d'abandon ;
- revenu total ;
- cout total ;
- effort total ;
- erreurs de scoring probables ;
- recommandations pour ajuster les futurs scores.

Generer le rapport :

```bash
python src/agent.py learning-report
```

Cette boucle ne modifie aucun compte externe. Elle prepare seulement une amelioration progressive du raisonnement de COD4X a partir de donnees locales et validees humainement.

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
python src/agent.py roblox-specs
python src/agent.py roblox-pipeline
python src/agent.py roblox-report
```

Ajouter une tendance locale :

```bash
python src/agent.py roblox-trend --name "Obby narratif court" --strength 8 --competition 4 --development-complexity 4 --signal "Sessions courtes" --mechanic "parcours a choix" --monetization "cosmetiques" --virality "fins partageables"
```

### Roblox Game Spec Generator V2.2 Preview

Le generateur de specs Roblox existe dans ce depot comme preview experimentale V2.2. Il n'appartient pas au coeur Learning V1.1/V1.1.1. La stabilisation V1.1.1 porte sur les outcomes, convictions et rapports d'apprentissage ; Roblox Specs reste une couche separee et locale.

Les fiches de jeux sont generees depuis les concepts conserves dans `memory/roblox/concepts.json` avec un score strictement superieur a `8/10`. Si aucun concept n'existe encore, le generateur utilise une donnee de demonstration locale afin de garder le dashboard exploitable.

Chaque fiche stockee dans `memory/roblox/specs.json` contient :

- nom, genre, public cible et promesse joueur ;
- core loop, meta progression, premiere session, retention J1 et retention J7 ;
- monetisation proposee : gamepasses, dev products et benefits premium ;
- MVP : temps estime, scripts requis, UI requise et assets requis ;
- risques, concurrents et score final.

Le pipeline complet local execute :

1. analyse des tendances locales ;
2. generation des concepts ;
3. scoring des concepts ;
4. generation des fiches de jeux.

## Politique d'action

COD4X produit uniquement des analyses, propositions, scores, rapports, resultats suivis et journaux locaux. Toute action qui toucherait a un compte, une publication, une transaction, un wallet, une API externe, du scraping ou une depense doit rester hors perimetre tant qu'une validation humaine explicite et une couche d'execution separee n'ont pas ete definies.

Limites de securite :

- aucune API externe ;
- aucun wallet ;
- aucune publication ;
- aucune action financiere ;
- aucun scraping ;
- aucune automatisation externe ;
- validation humaine obligatoire avant toute action reelle.
