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
|   |-- reality/
|   |   |-- assumptions.json
|   |   |-- evidence.json
|   |   `-- reality_report.json
|   |-- selection/
|   |   |-- committee_report.json
|   |   `-- opportunities.json
|   |-- thesis/
|   |   `-- theses.json
|   `-- state.json
|-- src/
|   |-- agent.py
|   |-- evaluator.py
|   |-- learning/
|   |   |-- conviction_engine.py
|   |   |-- learning_loop.py
|   |   `-- outcome_tracker.py
|   |-- planner.py
|   |-- reality/
|   |   |-- assumption_tracker.py
|   |   |-- evidence_engine.py
|   |   `-- reality_report.py
|   |-- roblox/
|   |   |-- concept_generator.py
|   |   |-- spec_generator.py
|   |   |-- scoring_engine.py
|   |   `-- trend_analyzer.py
|   |-- selection/
|   |   |-- committee_report.py
|   |   |-- opportunity_collector.py
|   |   `-- selection_engine.py
|   `-- thesis/
|       |-- opportunity_comparator.py
|       |-- recommendation_builder.py
|       `-- thesis_engine.py
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

## Opportunity Selection Engine V1.2

COD4X V1.2 transforme les idees deja presentes en opportunites comparables. Le module ne cree aucun nouveau concept : il collecte uniquement ce qui existe deja dans les memoires locales, puis choisit une opportunite principale et explique pourquoi les autres sont ecartees.

Sources collectees :

- `memory/state.json` avec `last_plan` ;
- `memory/roblox/concepts.json` ;
- `memory/roblox/specs.json` si present ;
- `memory/learning/outcomes.json` ;
- `memory/learning/score_rationales.json` pour la conviction si disponible.

Chaque opportunite est normalisee avec un score, une conviction, un effort estime, un cout estime, un potentiel de revenu, un risque, un fit strategique, et des garde-fous d'execution.

### Logique du comite

Le moteur classe les opportunites selon :

- score initial ;
- conviction / confiance ;
- effort estime ;
- cout estime ;
- risque ;
- potentiel ;
- coherence avec la doctrine ;
- historique des outcomes similaires.

Il produit :

- une opportunite retenue ;
- des alternatives rejetees avec raisons ;
- une watchlist ;
- des opportunites bloquees.

Le rapport de comite est local et non financier. Il sert uniquement a repondre : quelle opportunite merite vraiment le temps humain disponible ?

Commandes :

```bash
python src/agent.py opportunities
python src/agent.py select-opportunity
python src/agent.py committee-report
```

Memoires :

- `memory/selection/opportunities.json`
- `memory/selection/committee_report.json`

Statut : experimental controle. Le module propose une priorite strategique, mais ne publie rien, ne contacte personne, ne connecte aucun wallet, ne declenche aucun paiement et n'execute aucune action externe.

## Thesis Engine V1.3

COD4X V1.3 transforme la selection V1.2 en these defendable. Le moteur ne choisit pas de nouvelles opportunites et ne cree aucun concept : il lit le rapport de comite existant, justifie l'opportunite retenue, compare les alternatives et produit une etape anti-biais obligatoire.

Le Thesis Engine produit :

- opportunite retenue ;
- score et conviction ;
- resume executif ;
- hypotheses principales ;
- avantages et inconvenients ;
- risques ;
- ressources necessaires ;
- temps, cout et potentiel estimes ;
- raisons du choix ;
- comparaison des alternatives rejetees, surveillees ou bloquees ;
- recommandation : pursue, watch, reject ou wait ;
- contre-arguments, scenarios d'echec et hypotheses fragiles.

Commandes :

```bash
python src/agent.py thesis
python src/agent.py thesis-history
```

Memoire :

- `memory/thesis/theses.json`

### Logique anti-biais

Chaque these doit repondre a la question : "Pourquoi cette decision pourrait etre mauvaise ?"

COD4X genere donc :

- arguments contre sa propre decision ;
- scenarios d'echec ;
- hypotheses fragiles.

Cette couche evite l'auto-confirmation : COD4X ne se contente pas de dire "je choisis ceci", il explique aussi ou son raisonnement peut casser.

Statut : experimental controle. Le module justifie uniquement des decisions existantes. Il ne lance aucune action externe, ne fait aucun scraping, n'appelle aucune API et ne genere aucun nouveau concept.

## Reality Engine V1.4

COD4X V1.4 ajoute une couche de verification des croyances. Le Reality Engine ne choisit pas a la place du comite et ne modifie pas les scores : il indique ce qui est prouve, suppose, inconnu, fragilise ou invalide.

Il sert a repondre a une question simple : sur quelles hypotheses repose la decision actuelle, et quelles preuves locales existent vraiment ?

### Hypothese, preuve et decision

- Une hypothese est une croyance a verifier, liee a une action, un concept Roblox, une spec, une opportunite ou une these.
- Une preuve est une observation locale : revue humaine, test local, benchmark, feedback, metrique ou note.
- Une decision reste une proposition strategique ou une validation humaine. Elle n'est pas modifiee automatiquement par le Reality Engine.

Quand une these est generee, COD4X extrait automatiquement des hypotheses depuis :

- les hypotheses fragiles ;
- les risques ;
- les arguments en faveur ;
- les contre-arguments ;
- les scenarios d'echec.

Ces hypotheses sont stockees dans `memory/reality/assumptions.json`. Les preuves sont stockees dans `memory/reality/evidence.json`. Le rapport global est stocke dans `memory/reality/reality_report.json`.

Commandes :

```bash
python src/agent.py assumptions
python src/agent.py assumption-add --source-type thesis --source-id thesis-local --hypothesis "Le potentiel estime doit etre confirme par un test local." --importance critical --confidence-percent 35
python src/agent.py evidence-add --assumption-id assumption-thesis-thesis-local-le-potentiel-estime-doit-etre-confirme-par-un-test-local --evidence-type human_review --summary "Revue humaine effectuee, preuve encore insuffisante." --strength weak --supports-hypothesis true
python src/agent.py reality-report
```

Le rapport Reality indique :

- nombre total d'hypotheses ;
- hypotheses validees, supportees, affaiblies, non verifiees et invalidees ;
- hypotheses critiques non verifiees ;
- preuves disponibles ;
- niveau de realite global : unknown, speculative, mixed, grounded ou fragile ;
- decisions qui reposent sur trop d'hypotheses non verifiees.

### Limites V1.4

- aucune API externe ;
- aucun scraping ;
- aucune publication ;
- aucune action financiere ;
- aucune execution externe ;
- aucun changement automatique des decisions ;
- aucun changement automatique des scores ;
- validation humaine obligatoire avant toute action reelle.

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
