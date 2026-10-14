# Installation et exploitation — Père Blaise

## Portée

Les commandes ci-dessous sont des procédures pour l'exploitant. Elles ne constituent pas une autorisation de production acquise. Les deux spécifications restent les critères de revue. Aucun test ne doit pointer vers les vrais `Downloads`/`Documents` tant que la recette sur arbres temporaires et les permissions macOS ne sont pas validées.

## Installation et configuration initiale

1. Vérifier la source physique `~/workspace/hermes-knights-grail/pere-blaise`, son slug, `README.md`, `compose.yaml`, `config/`, `src/`, `tests/`. La guideline commune actuellement présente autorise ce chemin ; le passage `my-hermes` dans la spécification est historique. Ne pas modifier les guidelines communes sans approbation explicite.
2. Prévisualiser puis staged avec `scripts/deploy-stage-safe.sh --deploy-root "$HOME/Library/Application Support/HermesAgents/deployments" --budget-kib 2048 --preview`. Relire chemins et octets. Passer `--stage --confirmed-total-bytes N` avec le N affiché, puis vérifier le staging. L'activation exige le chemin exact `--activate-stage PATH`. Pour une mise à jour, arrêter les services et utiliser `--replace-stage PATH --archive-current PATH --confirm-services-stopped` ; l'ancien code est archivé sans suppression.
3. Créer un répertoire privé 0700 hors dépôt, par exemple `~/Library/Application Support/HermesAgents/runtime/pere-blaise`. Y déposer `broker.json` fondé sur `config/broker.example.json`, avec les trois racines physiques et les limites. Les chemins doivent être `/downloads`, `/documents`, `/backups`, `/state` **dans le conteneur**. Les IDs Telegram/Slack, canal Slack et propriétaire hebdomadaire restent dans ce fichier privé. Garder `weekly_enabled: false`.
4. Créer des fichiers 0600 `telegram.token`, `slack-bot.token`, `slack-app.token` et `planner.env`. Ne jamais saisir leur valeur dans Git, commande de shell visible, log ou ticket. `planner.env` contient `PERE_BLAISE_API_KEY` pour le broker ; le fichier d'environnement privé du planificateur contient `API_SERVER_KEY` avec la même valeur. Prévoir `paths.env` privé pour `PB_PLANNER_ENV_FILE`, `PB_HERMES_CONFIG`, `PB_DOWNLOADS`, `PB_DOCUMENTS`, `PB_BACKUPS`, `PB_PRIVATE_DIR`. Les racines hôtes sont des répertoires déjà existants ; ne monter ni `$HOME` entier ni dépôt.
5. Vérifier Docker Desktop, le partage de ces trois chemins et les permissions macOS du propriétaire. L'OAuth `openai-codex` doit être initialisé **dans le volume Hermes privé** par le propriétaire, puis contrôlé après redémarrage. Vérifier que le modèle `gpt-5.4` et le volume d'automatisation sont autorisés par l'abonnement. Sans cela, laisser les services arrêtés.
6. Réutiliser le bot Telegram et l'app Slack existants après audit ; stopper l'ancien consommateur Telegram avant le nouveau. Vérifier le canal privé et les utilisateurs autorisés. Slack requiert `files:write` et, pour Socket Mode, un token `connections:write`.

`scripts/lifecycle.sh configure DOWNLOADS DOCUMENTS BACKUPS` crée les fichiers privés vides avec permissions strictes, sans afficher ni demander les tokens dans le dépôt. L'exploitant renseigne ensuite `broker.json`, les deux fichiers de clé interne identique et les tokens via son gestionnaire de secrets. `scripts/validate-private.py` refuse les allowlists absentes, les permissions trop larges et une tâche hebdomadaire activée sans `weekly-approval.json` privé portant `approved_by` et `manual_test_at`. `scripts/lifecycle.sh start|stop|restart|status|logs` utilise le même Compose ; `stop` conserve aussi les conteneurs et leurs logs.

## Commandes Docker contrôlées

Depuis la copie de déploiement, avec `--env-file "$PRIVATE/paths.env"` :

```sh
docker compose --env-file "$PRIVATE/paths.env" config --quiet
docker compose --env-file "$PRIVATE/paths.env" up -d --build
docker compose --env-file "$PRIVATE/paths.env" ps
docker compose --env-file "$PRIVATE/paths.env" logs --no-color --tail=100
docker compose --env-file "$PRIVATE/paths.env" restart
docker compose --env-file "$PRIVATE/paths.env" down
```

`down` ne reçoit jamais `--volumes`. Les deux volumes natifs sont `hermes-pere-blaise-data` et `hermes-pere-blaise-broker-data`. Les healthchecks doivent être `healthy` avant tout test de canal. Aucun port n'est publié. Une image s6 Hermes peut garder le conteneur en marche alors que le gateway est malade : vérifier également l'API authentifiée `/v1/toolsets` et un appel de planification de test, puis le modèle/OAuth. Vérifier qu'aucun toolset n'est activé et qu'un appel sans clé renvoie 401.

Pour corriger un apprentissage, arrêter le broker puis utiliser `docker compose ... run --rm --no-deps broker python /app/scripts/learning-admin.py --database /state/plans.sqlite3 --documents /documents list`, puis `correct --id N --directory DOSSIER` ou `delete --id N`. L'accès au volume et aux chemins privés est réservé à l'exploitant Docker local. Sauvegarder SQLite avant correction ; vérifier ensuite `apprentissages`. Cette commande n'efface jamais les backups ou documents.

## Tâche hebdomadaire

La configuration `weekly_enabled: false` est le défaut. Le déclencheur est dimanche 17 h `Europe/Paris`, sans rattrapage si le Mac est arrêté. Il revendique une clé unique par semaine dans SQLite, tente d'abord les deux notifications, exécute une analyse, puis tente les deux résultats. Il n'appelle jamais `range`. Tester manuellement `run_once` avec des transports de test, vérifier l'identité `weekly_owner` et le destinataire des deux canaux, puis demander la validation d'activation au propriétaire et seulement alors passer `weekly_enabled: true` avec redémarrage contrôlé. Un échec d'un canal n'empêche pas l'autre ; examiner le journal.

## Sauvegarde et restauration

Les backups de fichiers classés sont sous `PB_BACKUPS/<plan-id>` et ne sont jamais purgés automatiquement. Pour SQLite broker, `scripts/state-backup.py backup --source SOURCE --destination NOUVEAU.db` utilise l'API de backup SQLite, fait `integrity_check` et écrit un SHA-256. `restore --dry-run` affiche les chemins ; `restore` exige la source avec `.sha256`, une destination absente et un broker arrêté. Vérifier à nouveau `integrity_check`, puis démarrer le broker et vérifier `apprentissages` et les états de journal. Ne pas copier à chaud un `state.db` en WAL depuis un bind mount macOS. Le volume Hermes natif, sa configuration et son OAuth sont exportés à froid, chiffrés hors dépôt par le propriétaire ; la restauration de ce volume et des secrets **n'a pas encore de script validé**. Toute restauration réelle attend un exercice sur volume et secrets de test.

`scripts/lifecycle.sh backup --path "$HOME/Library/Application Support/HermesAgents/snapshots/pere-blaise/<id>" --dry-run` affiche le périmètre. Après contrôle, `--confirm --recipient age1...` crée une sauvegarde chiffrée `age` des deux volumes et de la configuration privée, avec manifeste SHA-256, après arrêt. `restore --path ... --dry-run`, puis `--confirm --identity /chemin/prive/identite` ne restaure que vers des volumes et un répertoire privé **absents**. Ces deux flux ne sont pas encore validés en exécution car `age` est absent de la machine ; l'identité de déchiffrement reste hors dépôt. Le dossier de backups de classement est inventorié séparément, sans purge ni copie automatique. La syntaxe `age` suit sa [documentation officielle](https://github.com/FiloSottile/age/blob/main/README.md).

## Mise à jour, migration et rollback

Relever le digest/version `docker image inspect` et `hermes --version` avant changement ; l'image de référence testée annonce v0.21.6/upstream `818c13be`. Ne pas remplacer un digest par un tag flottant. Arrêter broker/Hermes, sauvegarder SQLite via API et le volume Hermes à froid, créer un staging, exécuter tests, `docker compose config`, contrôler l'absence de journal `APPLYING`, puis démarrer une recette sur volumes et dossiers temporaires. En cas d'échec, conserver le déploiement courant et l'archive de code ; restaurer seulement une base de schéma compatible. Les évolutions de prompt/skill prennent effet à une nouvelle session. La migration de schéma versionnée et le rollback de volume Hermes restent à réaliser et tester avant mise à jour de production.

## Désinstallation et suppression complète

Désinstallation conservatrice : `scripts/lifecycle.sh uninstall --dry-run`, puis `--confirm-archive CHEMIN_EXACT` sous `.archive/pere-blaise-*`. Le script arrête les services, exporte leurs logs dans le runtime privé, retire les conteneurs **sans** `--volumes` et archive le code. Il conserve volumes, backups, secrets, journaux et les vrais `Downloads`/`Documents`. Ne pas employer `rsync --delete` ni supprimer l'ancien déploiement sans validation humaine explicite après aperçu.

Suppression complète : `scripts/lifecycle.sh purge --dry-run` affiche les chemins, tailles des volumes et archives éventuelles. Le flux d'exécution exige `--confirm "PURGE pere-blaise" --reviewed`, un terminal interactif et la recopie exacte des trois chemins ; il refuse toute archive restante et une racine de backup configurée hors du périmètre fixe. Les deux racines `Downloads` et `Documents` restent exclues. Ne jamais lancer ce flux sur le runtime existant sans revue humaine explicite du manifeste affiché.

## Incident

Un journal `APPLYING` est rapproché au démarrage. Si l'état est `BLOCKED_RECOVERY`, stopper les services, conserver backup, source et cible, comparer les hashes avec l'exploitant et ne pas relancer `range`. Un timeout Telegram/Slack après transmission est une livraison incertaine : vérifier côté canal avant toute nouvelle demande, afin d'éviter un doublon. Une erreur OAuth/quota bloque l'analyse sans fournisseur de repli. Révoquer les tokens seulement en cas de fuite ou d'impossibilité de stopper l'ancien consommateur, puis mettre à jour les fichiers privés 0600 et retester les deux canaux.
