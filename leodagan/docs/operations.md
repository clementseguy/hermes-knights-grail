# Exploitation locale de Léodagan

## Prérequis et configuration privée

Exécuter depuis la racine du dépôt :

```sh
./leodagan/scripts/leodagan.sh install
./leodagan/scripts/leodagan.sh configure
```

`install` affiche chemins physiques, aperçu `rsync --dry-run --stats`, contrôle le budget de 50 Mio et prépare une release sous `.deployments/leodagan/releases/`. Un second appel avec la même source retourne « Release déjà identique » sans modifier le service ; ce comportement a été testé avec le conteneur arrêté puis actif. Il ne copie pas l'ancien runtime ni la boîte de revue. `configure` crée `~/Library/Application Support/HermesLeodagan/channels.env` en mode 600, **hors du dépôt**. Les jetons Slack restent dans les fichiers séparés `slack-leodagan-bot.token` et `slack-leodagan-app.token` (mode 600) du même dossier ; le script les charge en mémoire au démarrage sans les recopier dans `channels.env`. Renseigner dans ce dernier `SLACK_ALLOWED_USERS` (ID de Clément) et `SLACK_ALLOWED_CHANNELS` (ID de `#agent-leodagan`). Vérifier Socket Mode avec `connections:write`, `app_mentions:read`, `chat:write`, `channels:history` et, d'après l'appel réel du 24 octobre, `groups:history` pour la lecture du contexte des fils ; ne demander aucun scope LinkedIn en écriture. Vérifier qu'un seul consommateur Socket Mode est actif et que le bot est invité au canal. L'ancien `runtime/.env` comporte un jeton bot, mais **pas** de jeton d'app ni d'allowlists ; le script ne le copie pas.

Le skill versionné `skills/leodagan/SKILL.md` est copié dans le `SOUL.md` privé de Hermes par `configure` et lors de l'installation initiale. La version épinglée de Hermes ne charge `skills.auto_load` que lorsque le toolset `skills` est exposé ; ce toolset inclurait la gestion des skills, qui dépasse la mission. Après toute mise à jour du skill, arrêter le service, exécuter `install` puis `configure`, et redémarrer pour ouvrir une nouvelle session.

Les commandes `/...` intégrées Hermes ont une autorisation distincte des toolsets. `config/config.yaml` active la restriction des commandes en définissant une liste d'administrateurs sans ID correspondant, puis n'autorise pour Clément que `/help`, `/whoami`, `/new` et `/stop` sur Slack/Telegram. Le menu Telegram n'affiche que ces quatre commandes. Vérifier dans l'image réellement utilisée que `/cron`, `/loop`, `/model`, `/sethome` et toute commande d'extension sont refusées ; les messages ordinaires restent admis. Le `SOUL.md` seul ne suffit pas à ce contrôle.

Pour les clics exacts dans le portail Slack et la création/test du bot Telegram, suivre [la procédure des canaux privés](canaux-prives.md). Le jeton Telegram est conservé dans un fichier séparé `telegram-leodagan-bot.token` (mode 600) et seul l'ID numérique de Clément est inscrit dans `channels.env`. Activer `telegram.enabled: true` dans la configuration versionnée puis redéployer uniquement après ce provisionnement. Aucun groupe ou autre utilisateur.

Authentifier le compte ChatGPT/Codex **dans le volume propre de Léodagan** avec `hermes auth add openai-codex` dans un conteneur interactif Léodagan (`docker compose run --rm --no-deps --entrypoint hermes leodagan auth add openai-codex`, avec `LEODAGAN_OUTBOX` défini et le fichier Compose de la release). Le flux par défaut est le code d'appareil ; vérifier `hermes auth add --help` dans l'image avant l'opération. Ne copier aucun `auth.json` de Père Blaise ou d'un autre agent. Vérifier le renouvellement et le quota du modèle choisi par un run contrôlé. Le service doit rester arrêté si ce point échoue.

## Démarrage et diagnostic

Après contrôle des allowlists, scopes, stockage, sauvegarde et refus, utiliser :

```sh
./leodagan/scripts/leodagan.sh start
./leodagan/scripts/leodagan.sh status
./leodagan/scripts/leodagan.sh logs 100
./leodagan/scripts/leodagan.sh stop
./leodagan/scripts/leodagan.sh restart
```

`start` refuse les paramètres Slack absents et n'installe aucun job. Vérifier ensuite `docker inspect hermes-leodagan` : nom, santé, volumes, ports publiés vides, capabilities, et absence de socket Docker. La santé Docker peut précéder de quelques secondes la reconnexion Socket Mode ; confirmer `✓ slack connected` et `✓ telegram connected` dans le journal gateway avant une recette. Tester une mention dans le canal autorisé, une réponse dans le même fil, un autre canal et une autre identité (refus), ainsi qu'une erreur de livraison. Pour Telegram, envoyer une nouvelle demande de brouillon après la connexion du polling. Le message de recette doit livrer le post entier et le prompt, puis `editorial_get` doit les retrouver après redémarrage. Les recettes réussies sont `silex-bleu` v1 sur Slack le 15 octobre et `rempart-agent` v1 sur Telegram le 24 octobre. Après propagation de `groups:history`, `conversations.replies` a relu trois messages du fil Slack ; le jeton `xoxb-` n'a pas changé. Hermes peut envoyer au premier DM un avis « No home channel is set for Telegram » : aucune tâche planifiée n'est activée, et ce réglage d'accueil reste absent pour conserver le fonctionnement à la demande.

## Sauvegarde et restauration

Créer `~/Library/Application Support/HermesLeodagan/backup.pass` (mode 600) et conserver une copie sûre hors du poste. `backup` arrête Léodagan, chiffre un tar du volume natif avec AES-256-CBC/PBKDF2, vérifie sa lisibilité et crée une somme SHA-256 ; il **ne redémarre pas** le service. Le fichier chiffré contient potentiellement secrets, conversations et brouillons. La restauration `restore ARCHIVE` refuse un conteneur ou volume actif et restaure uniquement vers un volume neuf après contrôle de la somme, des chemins et de la taille décompressée. Vérifier la base, le brouillon et la règle mémoire avant `start`. Le 18 octobre, l'archive contenant `silex-bleu` a été restaurée dans un volume isolé ; intégrité SQLite et empreintes du post/prompt identiques au volume principal. Le volume de test a été retiré et le service relancé. La restauration en production et celle d'une règle mémoire réelle ne l'ont pas été. La sauvegarde ne contient pas les fichiers de jetons et la phrase secrète du répertoire privé ; les conserver séparément, ainsi que la release/configuration correspondante, pour un retour complet.

## Mise à jour, arrêt et retrait

`update` prépare une nouvelle release et reconfigure le service. **Ne pas l'employer comme migration automatique de production à ce stade** : retour arrière image/config et migration du volume doivent encore être éprouvés. Pour un changement contrôlé, arrêter, sauvegarder, conserver le digest et la release précédents, vérifier le plugin et Compose en staging, puis démarrer et tester avant de retenir la nouvelle release. Si la migration échoue, laisser arrêté et restaurer la sauvegarde vers un volume neuf.

`uninstall` retire le conteneur et son réseau mais conserve le volume, les secrets, l'outbox et les sauvegardes. `purge` affiche les chemins, le volume et leurs tailles, puis exige la saisie exacte `PURGER hermes-leodagan` ; aucune purge n'a été faite. L'ancien runtime de 15 Mio est conservé dans `~/Library/Application Support/HermesLeodagan/legacy-runtime`, hors dépôt ; `review-inbox/` (16 Kio) reste dans le dépôt pour récupération. La suppression d'un ancien déploiement ou une copie avec `--delete` exigent une validation ciblée après affichage des chemins et tailles.

En cas de perte de canal ou de quota, arrêter le service si nécessaire, conserver les brouillons, corriger l'accès et reprendre par le même identifiant ; aucun fournisseur de repli. Faire tourner les tokens Slack/Telegram dans le portail correspondant puis mettre à jour le fichier privé ; réauthentifier Codex uniquement dans le volume Léodagan. Les journaux sont dans `/opt/data/logs` ; éviter d'en exporter les corps privés et conserver leur rétention jusqu'à décision explicite de purge.

L'image épinglée journalise parfois `Previous gateway life ... exited UNCLEANLY` après un `compose stop` ou une recréation, même quand la commande s'achève et que SQLite retrouve son intégrité après redémarrage. Le mécanisme exact d'arrêt du gateway reste à examiner séparément dans Hermes avant de considérer ce signal comme résolu ; ne pas supprimer les données à cause de cet avertissement seul.
