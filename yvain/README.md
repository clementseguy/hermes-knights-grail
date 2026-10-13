# Yvain

Yvain est l'agent Hermes de recette QA de NexTarget. Il vit ici, séparé des
dépôts produit :

- `NexTarget-app` reste la source des US, du changelog et du cahier de recette ;
- `NexTarget-server` fournit le conteneur de staging ;
- ce dossier contient la politique de l'agent, son manifeste de scénarios et
  les scripts d'exécution sur le poste de recette.

Yvain n'apporte aucune modification à `NexTarget-server`. Lorsqu'un besoin de
staging, fixture, reset ou API est identifié, il le formule au développeur du
serveur puis vérifie le comportement livré.

## Déclenchement

Yvain ne planifie rien. Il est lancé soit à la demande depuis son canal de
discussion, soit par un événement GitHub de PR. Le point d'entrée hôte est :

```bash
bash scripts/run-recipe.sh <base-sha> <head-sha> [enforce] [NT-XXX]
```

La configuration locale est privée :

```bash
cp config/runner.env.example config/runner.env
# renseigner les chemins, l'AVD et le device adb
bash scripts/run-recipe.sh origin/main dev false NT-149
```

La comparaison suit toujours la direction de la PR, même si Git reçoit la
base avant la tête :

```bash
# Gate d'une nouvelle US apportée par une PR vers dev.
# Le type est vérifié : impossible d'utiliser une base main par erreur.
bash scripts/run-pr-gate.sh feature feature/NT-XXX-slug
bash scripts/run-pr-gate.sh fix fix/NT-XXX-slug

# Rapport de release : les US présentes sur dev et absentes de main.
# Tant que la dette de couverture historique existe, ce rapport est informatif.
bash scripts/run-release-report.sh
```

`enforce=true` fait échouer le script lorsqu'une US sélectionnée ne possède
pas de flux Maestro prêt. Ce code de sortie ne bloque une fusion que lorsqu'un
workflow GitHub le publie ensuite comme contrôle requis ; ce branchement est
une étape distincte.

Le script démarre le staging, réinitialise sa base SQLite de recette et y
réinstalle les fixtures déterministes, puis exécute les cas déclarés : tests Flutter
déterministes ou flux Maestro. Les tests Flutter sont des contrôles de
soutien : ils ne rendent jamais une recette QA valide sans au moins un flux
Maestro. Pour ces derniers, le script démarre l'AVD si nécessaire, construit
l'APK et remet les données locales à zéro entre les scénarios. Il produit un
rapport dans `reports/` et ne crée jamais d'issue GitHub sans validation humaine.

La remise à zéro locale peut aussi être demandée explicitement avant une
recette manuelle :

```bash
bash scripts/reset-local-app-data.sh
```

Elle utilise `adb pm clear` : Hive, préférences, cache et jetons éventuels
sont réellement effacés. Les fixtures visibles dans l'application sont
limitées au build `DEBUG` et ne figurent pas dans une release.

Les sélecteurs Flutter stables actuellement disponibles pour les scénarios
Maestro sont `qa.settings.default_hand`, `qa.settings.weapon_rack`,
`qa.settings.default_caliber` et `qa.debug.seed_coach_fixtures`. Les textes et
la position à l'écran restent des solutions de repli, jamais l'oracle
principal d'un parcours critique.

## Runtime Hermes

```bash
YVAIN_HOME="$HOME/.yvain" YVAIN_ANDROID_SDK="$HOME/Library/Android/sdk" \
  bash scripts/install-mobile-runtime.sh
curl -fsSL "https://get.maestro.mobile.dev" | bash
bash scripts/bootstrap.sh
docker compose --env-file config/runner.env up -d yvain
```

Le conteneur Hermes sert à la discussion, au triage et à la préparation du
rapport. Le script de recette s'exécute sur le macOS hôte afin d'accéder à
Android Emulator et Docker Desktop. Utiliser un compte et une machine dédiés :
une recette construit le code de la PR et ne doit pas recevoir de secrets de
production.

L'émulateur Android s'exécute nativement sur le Mac hôte : Docker Desktop ne
fournit pas la virtualisation imbriquée fiable nécessaire à l'émulateur sur
macOS. Le conteneur Hermes reste isolé et pilote le runner hôte par un
déclencheur contrôlé ; Maestro, `adb` et l'AVD appartiennent au poste de
recette.

## Contrat de couverture

Yvain lit les `NT-XXX` uniquement dans les lignes ajoutées à `CHANGELOG.md`.
Leur définition est recherchée dans le backlog actif puis dans les archives,
notamment `docs/backlog/archive/2026.md` pour les US déjà livrées.
Une nouvelle US app doit avoir un flux Maestro `ready` dans
`qa/manifest.json`; les tests unitaires associés ne sont que des preuves
complémentaires. Une US strictement serveur est marquée `out_of_scope`; une US
app+serveur reste recettée côté mobile. Le passage `dev -> main` rapporte la
dette existante sans la rendre bloquante ; une PR `feature/* -> dev` est bloquée
si elle introduit une US sans flux.
