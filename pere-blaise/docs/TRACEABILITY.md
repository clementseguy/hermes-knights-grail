# Traçabilité F-001…F-018 — vérification des 14 et 15 octobre 2026

« Local » signifie tests sur arbres temporaires, « Docker jetable » une composition avec fausses identités et secrets sous `/private/tmp`. Une autre composition d'essai a utilisé les vrais canaux mais uniquement des dossiers fictifs sous `/private/tmp` ; ses résultats ne valent pas validation des dossiers personnels. Un ancien conteneur Hermes réel découvert actif a été arrêté sans supprimer son volume. Après staging et recette sur données fictives, la nouvelle copie a été activée. Clément a ensuite exercé lui-même `envoie` sur un document personnel ; le développement n'a ouvert ni classé de document personnel. La tâche est activée après validation finale explicite de Clément ; sa première exécution automatique reste à observer. **Correction de traçabilité du 15 octobre :** l'état `healthy` ne prouve pas les racines montées. L'inspection du broker actif a révélé des montages fictifs alors que les notes précédentes parlaient de service réel ; les résultats `PB-DL-EMPTY` obtenus dans cet état ne prouvaient rien sur les Downloads personnels.

| ID | Code / preuve | État exact |
| --- | --- | --- |
| F-001 | `telegram_gateway.py`, `slack_gateway.py`, tests de refus Slack et propriétaire | Local passé ; Clément autorisé a obtenu un plan par Telegram privé et par mention humaine dans Slack privé ; un `1` humain sans mention dans le fil Slack est resté muet ; dans le broker Docker avec clients factices, ID Telegram inconnu, groupe, canal et utilisateur Slack inconnus restent muets ; essai depuis un vrai compte tiers non fait |
| F-002 | `scanner.py`, `workflow.py`, tests de minimisation et bibliothèque Documents au-delà des limites Downloads | Local passé sur données fictives ; analyse complète via les deux canaux sur un fichier fictif et modèle Codex réussie. L'incident `PB-PLAN-INVALID` `901ac3f311ba` a motivé le correctif des limites Documents, testé localement et déployé le 15 octobre. `PB-DL-EMPTY` `b436770f921a` ne prouve pas l'état des vrais Downloads ; lors des incidents plus récents, les montages fictifs ont été vérifiés. Après correction des montages, contrôle en lecture seule : deux fichiers visibles depuis le broker. Aucun nouveau plan personnel complet constaté |
| F-003 | `broker.py`, `_detail`, tests propriétaire | Détails des plans fictifs `vif-grue` puis `léger-café` reçus par Clément sur Telegram : source, destination, raison, certitude, confiance et expiration ; `vif-grue` a été invalidé avant tout `range` |
| F-004 | `store.py`, `workflow.py`, tests expiration/invalidation | Local passé ; dans la recette réelle sur fichiers fictifs, les anciens plans dont `vif-grue` ont été invalidés par une nouvelle analyse ; `léger-café` est proposé avec signature d'inventaire courante ; expiration réelle et redémarrage du service final non vérifiés |
| F-005 | `contracts.py`, `store.py`, tests IDs | Local passé ; collision sous charge non vérifiée |
| F-006 | `broker.py`, `executor.py`, `test_apply_backups_and_owner` | `range léger-café` demandé une fois par Clément sur Telegram, appliqué sur un fichier fictif seulement après détail ; source absente et cible présente après redémarrage ; aucune autre commande n'a provoqué de mouvement |
| F-007 | `executor.py`, tests backup/espace | Backup fictif vérifié présent avant déplacement selon le journal ; après application, backup et cible ont taille/empreinte identiques à la source initiale, manifeste marqué vérifié et conservé ; sous broker Docker UID 10000, manque d'espace injecté dans un tmpfs fictif : refus avant journal, backup ou mouvement |
| F-008 | `executor.py`, reprise/rollback/blocage et arrêt brutal de processus testés | Local passé ; coupure électrique réelle exclue par décision du propriétaire, voir README ; rollback inchangé |
| F-009 | `planning.py`, `executor.py`, collision Docker jetable et tests au-delà des limites Downloads | Cible existante refusée avant mouvement dans l'essai antérieur ; après `range` réel sur arbre fictif, les deux documents fictifs préexistants gardent taille et empreinte identiques. Le traitement local choisit le dossier existant `a_trier/doublons` si la cible proposée est occupée, et refuse si le dossier manque ou si ce repli est occupé ; tests avec collision normalisée et conservation du document existant. Aucune tentative de classement personnel |
| F-010 | `planning.py`, `executor.py`, tests de dossier absent/`a_trier` | Local passé ; `range léger-café` a créé `Documents/a_trier` dans l'arbre fictif et y a déplacé l'unique source à confiance Low, backup conservé |
| F-011 | `file_delivery.py`, gateways, tests 0/1/N, choix et fil Slack | Local passé ; Telegram : une tentative « introuvable », puis pièce jointe fictive et confirmation reçues par le propriétaire ; Slack : upload réel de 60 octets, puis deux résultats proposés et choix 1 avec mention dans le même fil donnant uniquement le fichier fictif de 70 octets. Le 14 octobre, Clément a lui-même sélectionné et reçu un document personnel sur Telegram ; le développement n'en a pas lu les octets. La recherche `envoie facture GCU` était sans correspondance. L'incident `PB-SEND-NOTFOUND` `78fb0d880f35` sur `invoice GPU` provenait des montages fictifs ; après correction, une recherche locale en lecture seule trouve exactement le PDF attendu. Aucun nouvel envoi réel déclenché par ce diagnostic. Limites de taille des plateformes réelles non poussées |
| F-012 | `planning.py`, tests absence de hash/nom classé, `/v1/toolsets` zéro | Frontière locale et Docker passée : avec deux documents fictifs classés, le contexte construit dans le broker exclut leurs noms et les champs hash/inode/mtime ; l'appel réel au modèle a produit un plan, mais aucune capture réseau de sa requête n'a été faite |
| F-013 | `store.py`, `workflow.py`, tests non-collecte et conservation | **Reportée par décision du propriétaire ; jamais validée** |
| F-014 | `router.py`, gateways, outil admin retiré, tests refus | **Reportée par décision du propriétaire ; jamais validée** |
| F-015 | `scheduler.py`, `app.py`, `scripts/manual-weekly.py`, tests fuseau/DST/lundi 9 h/limite 24 h/redémarrage/canaux | Local passé ; tâche manuelle réelle sur dossiers fictifs : aucun échec API, départ et résultat reçus sur Telegram et Slack à 19 h 43 selon Clément ; aucun mouvement. Après validation finale explicite de Clément, tâche activée dans le runtime privé et broker réel redémarré healthy ; mercredi non dû, `weekly_runs=0`, premier dimanche réel pas encore observé |
| F-016 | `errors.py`, gateways, `executor.py`, tests catalogue/ID/log sans contenu | Local passé pour les familles couvertes ; injection E2E de chaque panne non vérifiée |
| F-017 | `executor.py`, `store.py`, `migrate-state.py`, `state-backup.py`, `volume-backup.sh`, `ingress_ledger.py` | Reprise locale, migration 1→2→1 locale et sauvegarde/restauration chiffrée sur volumes factices passées ; après transaction fictive réelle, redémarrage du broker healthy, plan/journal `APPLIED`, un backup et une cible conservés sans rejeu ; Hermes redémarré healthy puis appel court Luna/Codex réussi via son volume OAuth ; restauration chiffrée du volume OAuth réel et renouvellement ultérieur du jeton non vérifiés |
| F-018 | `infra/slack/app-manifest.json`, `ingress_ledger.py`, runbook ; recherche Slack en lecture seule ; `check-channel-credentials.py` | Bot et app existants réutilisés ; canal privé, scopes bot et Socket Mode requis présents ; mention humaine Slack et commande Telegram reçues après reconstruction, événements terminés dans le journal ; un `analyse` est resté en attente plus de trois minutes pendant l'arrêt du seul broker repéré, sans réponse nouvelle, puis le nouvel essai a été traité par ce broker : aucun autre consommateur actif observé durant cette fenêtre ; seconde personne Slack absente |

## Commandes et observations de cette passe

```text
python3 -m unittest discover -s tests -q (depuis pere-blaise)
  43 tests OK, dont doublon Telegram/Slack après redémarrage et format d'upload Slack
bash -n pere-blaise/scripts/*.sh ; compileall -q src scripts ; git diff --check
  OK
brew install age
  échec : trois répertoires Homebrew globaux non accessibles en écriture ; aucun chown réalisé
curl release officielle age v1.3.2 darwin-amd64 vers /private/tmp
  SHA-256 1d1e4bc66e1427edad7739ae7616157de0e79db8b6d2a1497d7d9925fb06a539 vérifié ; age --version v1.3.2
install -m 755 age et age-keygen dans ~/Library/Application Support/HermesAgents/bin
  installation par utilisateur, v1.3.2 vérifiée ; aucun chown global Homebrew
docker compose ... config --quiet (paths.env factice sous /private/tmp)
  OK
docker build -f pere-blaise/Dockerfile.broker -t pb-test-broker:20261014 pere-blaise
  OK après retrait de learning-admin.py du Dockerfile
volume-backup.sh backup --disposable ... --confirm --recipient [clé publique de test]
volume-backup.sh restore --disposable ... --confirm --identity [fichier privé de test]
  snapshot2 chiffré, manifest SHA-256 vérifié, volumes source/cible distincts,
  SQLite integrity_check OK, données factices et permissions 0700/0600 vérifiées
  premier essai de restauration échoué (extracteur Python hôte sans filter=) ;
  correction, nouvel essai sur nouvelles cibles réussi ; cibles partielles conservées pour inspection
  essai snapshot3 avec transaction APPLIED : première restauration aux UID 0 impropres,
  correction de la propriété 0/10000, restauration sur nouvelles cibles et redémarrage
  broker UID 10000 réussis ; plan appliqué conservé, backup intact, rejeu refusé
docker compose -p pb-test-20261014-compose ... up -d --no-build --wait
  premier essai : healthcheck Hermes 10 s trop court ; après timeout 30 s, deux services healthy
  premier essai de clé API interne répétitive : API refusée malgré healthcheck healthy ;
  après clé factice aléatoire : /v1/toolsets sans clé 401 ; 28 entrées, zéro enabled
  healthcheck corrigé vers GET /health puis relancé : Hermes et broker healthy
docker inspect ... ; docker exec ...
  broker UID 10000, trois seuls bind mounts métier et secrets privés ro ;
  Hermes aucun montage métier, SQLite sur volumes natifs ; aucun port publié ;
  /root refusé, symlink exclu, traversal refusé, UID 10001 refusé sur /state,
  cible préexistante refusée avant mouvement
docker compose -p pb-test-20261014-compose ... down
  conteneurs de test arrêtés ; volumes et snapshots factices conservés, aucune donnée réelle touchée
docker inspect hermes-pere-blaise ; docker stop hermes-pere-blaise
  ancien conteneur du projet réel trouvé actif, port 127.0.0.1:8643 publié ;
  arrêté sans suppression, volume hermes-pere-blaise-data préservé ;
  runtime privé trouvé sans broker.json, donc aucun broker réel configuré
Slack connecté : list_workspaces, search_channels, list_channel_members (lecture seule)
  workspace NexTarget-26 ; canal privé #agent-pere-blaise présent, deux membres
  dont l'app Hermes existante ; scopes et token Socket Mode non vérifiés
python3 scripts/check-channel-credentials.py [runtime privé]
  getMe : bot Telegram attendu ; getWebhookInfo : aucun webhook, zéro update en attente
  Slack auth.test : token bot valide, app_mentions:read et chat:write ; files:write absent
  apps.connections.open : token app valide, connections:write, wss-primary.slack.com
  aucune valeur de token, URL de socket ou contenu de message affiché
Slack connecté : search_users, list_user_channels (lecture seule)
  ID de Clément et ID du canal privé trouvés ; compte Élise absent
bash scripts/lifecycle.sh configure [trois chemins fictifs sous /private/tmp]
  configuration privée créée sans écraser les tokens, weekly_enabled false
  broker.json : seul l'ID Slack de Clément et le canal privé renseignés ; ID Telegram en attente
  clé interne préexistante forte recopiée vers planner-api.env sans affichage
docker compose --env-file [paths.env privé fictif] config --quiet
  OK, aucun service démarré
python3 scripts/check-channel-credentials.py [runtime privé] (après réinstallation Slack)
  getMe attendu, webhook absent ; Slack bot app_mentions:read, chat:write,
  files:write ; app connections:write, WebSocket wss-primary.slack.com
getUpdates sans offset, limité à la mise à jour privée /start récente
  un seul ID personnel extrait et écrit dans broker.json privé sans l'afficher ;
  mise à jour non confirmée par cette lecture
docker compose -f compose.yaml -f [override jetable] up -d --build --wait
  Hermes et broker healthy ; aucun port publié ; Hermes seulement volume OAuth
  et config privée ; broker trois montages métier fictifs et secrets ro
docker exec pb-realchannel-hermes ... /v1/toolsets
  28 entrées, zéro activée
docker compose ... exec -T broker python /app/scripts/manual-weekly.py
  code 0, channel_failures=[] ; départ et résultat visibles dans Slack ;
  API Telegram a accepté les envois, Clément a confirmé avoir reçu les deux
  notifications Telegram et Slack à 19 h 43 ;
  source fictive intacte, cible absente, weekly_enabled false, weekly_runs vide
docker compose ... stop broker
  broker d'essai arrêté sans supprimer conteneur ni état pour isoler un
  possible second consommateur du bot Telegram ; diagnostic encore incertain
getUpdates sans offset pendant l'arrêt du broker
  un message privé analyse est resté en attente plus de trois minutes ;
  le bref accusé reçu par le propriétaire pouvait venir de la demande précédente
docker compose ... up -d --no-deps --wait broker
  broker redémarré sur dossiers fictifs ; healthchecks healthy ;
  le compteur de mises à jour Telegram en attente est passé de 1 à 0 ;
  réponse humaine et résultat de l'analyse encore à confirmer
docker compose ... build broker ; docker compose ... up -d --no-deps --force-recreate --wait broker
  nouvelle image avec ingress_ledger construite et démarrée ; deux services healthy,
  aucun port publié ; /state/ingress.sqlite3 présent en mode 0600
mention humaine de l'app suivie de analyse dans #agent-pere-blaise
  accusé dans le même fil, puis plan béni-forêt pour un fichier fictif ;
  SQLite : propriétaire Slack, événement terminé, source intacte, cible vide,
  weekly_enabled false ; aucun range lancé
docker exec broker : Gateway/SlackGateway avec configuration réelle et clients factices
  ID Telegram inconnu, groupe Telegram, canal Slack inconnu et utilisateur Slack
  inconnu : aucune réponse ni appel réseau ; aucune valeur d'identité affichée
docker exec broker : scan /downloads et /documents fictifs puis planner_context
  deux documents déjà classés ; leurs noms et les champs hash/inode/mtime
  absents du contexte ; aucun contenu ni hash affiché
nouvelle commande analyse envoyée par Clément en privé Telegram
  accusé puis plan vif-grue reçu par le propriétaire ; SQLite : propriétaire
  Telegram, événement terminé, source fictive présente, cible absente ;
  aucun range et aucune exécution hebdomadaire automatique
bash scripts/deploy-stage-safe.sh --deploy-root [racine autorisée] --budget-kib 2048 --preview
  source physique : /Users/clement/workspace/hermes-knights-grail/pere-blaise ;
  destination physique : /Users/clement/Library/Application Support/HermesAgents/deployments/pere-blaise ;
  67 fichiers, 270539 octets au total, budget 2097152 octets ; destination existante (288 KiB) ;
  aperçu uniquement, aucune copie ni suppression ; relecture du propriétaire encore requise
mention humaine Slack : envoie preuve-essai.txt sur un document de 60 octets sous /private/tmp
  accusé puis PB-SEND-FAILED, incident corrélé ; appel files.getUploadURLExternal
  rejeté invalid_arguments avant upload ; ticket obtenu avec formulaire URL-encoded
  selon la documentation officielle Slack ; code corrigé, 43 tests locaux OK,
  broker reconstruit et healthy ; nouvel essai humain à faire
seconde mention humaine Slack : envoie preuve-essai.txt
  pièce jointe de 60 octets visible dans le fil d'origine, puis confirmation
  « Fichier envoyé » ; aucun autre canal visé
Documents fictifs : second preuve-essai.txt dans Archives ; nouvelle mention Slack envoie
  PB-SEND-AMBIGUOUS avec deux chemins ; réponse 1 sans mention ignorée ;
  réponse <@bot> 1 dans le même fil : pièce jointe de 70 octets et confirmation ;
  aucune pièce jointe de 60 octets répétée dans ce fil
détaille vif-grue sur Telegram
  réponse reçue par Clément avec source, destination, raison, certitude et expiration ;
  ajout ultérieur du dossier Archives fictif : signature d'inventaire du plan
  devenue périmée, plan toujours proposé mais application refusée par le code ;
  nouveau plan demandé avant tout déplacement
nouveau analyse Telegram après stabilisation des dossiers fictifs
  plan léger-café proposé, vif-grue invalidé, signature courante ;
  un fichier fictif vers Documents/a_trier, confiance Low, aucune action exécutée
détaille léger-café sur Telegram
  Clément a reçu la source, la destination a_trier, la raison du classement
  incertain, la confiance Low et l'expiration ; avant range, la source fictive
  était présente, la cible et le backup absents, signature d'inventaire courante,
  weekly_enabled false
range léger-café une fois sur Telegram, puis docker compose ... restart broker
  accusé puis plan appliqué reçu par Clément ; journal et registre APPLIED,
  backup préalable vérifié et conservé (un fichier), cible et backup égaux en
  taille/empreinte à la source initiale ; source absente, deux documents fictifs
  préexistants inchangés ; après redémarrage broker healthy, même état,
  weekly_runs 0, weekly_enabled false, aucune répétition du mouvement
docker compose ... restart pere-blaise ; docker exec ... hermes --provider openai-codex -m gpt-6-luna --reasoning low -z [sentinelle fictive]
  Hermes healthy puis appel réel court réussi après redémarrage avec l'OAuth
  du volume existant ; sortie filtrée, aucun secret affiché
docker exec -i broker python - [essai isolé sous /tmp avec disk_usage.free=0]
  UID 10000 : backup space insufficient ; source intacte, destination,
  backup et journal absents ; aucun arbre hôte touché
stat des chemins réels désignés par Clément ; docker run --rm --read-only --user 10000:10000 avec montages ciblés
  Downloads=/Users/clement/Downloads et Documents=/Users/clement/Documents :
  chemins physiques, dossiers non-symlink, mode hôte 0700 ; Docker Desktop les
  monte et os.access R/W/X réussit pour UID 10000, sans lister ni ouvrir de
  document et sans créer de fichier ; Backup-pere-blaise existe, vide, mode
  0700 après chmod, montage et os.access R/W/X réussis ; ce contrôle de
  métadonnées ne prouve pas encore un accès effectif macOS à des fichiers
  personnels, qui ne doivent pas servir de test
python3 scripts/validate-private.py [runtime privé] ; docker compose --env-file [paths.real.env privé] config --quiet
  configuration privée et permissions OK ; composition finale valide, sans
  démarrage ; paths.real.env 0600 préparé avec les trois chemins approuvés,
  paths.env d'essai inchangé
bash scripts/deploy-stage-safe.sh --deploy-root [racine approuvée] --budget-kib 2048 --stage --confirmed-total-bytes 280735
  après relecture de Clément et nouvel aperçu (67 fichiers, 280735 octets),
  copie vers .staging/pere-blaise-20261014T182932Z, 43 tests OK ; aucune
  suppression et aucun lien symbolique suivi
docker compose depuis le staging avec override et secrets/dossiers factices, up -d --build --wait puis stop
  Hermes et broker healthy, aucun port publié, volumes natifs séparés, seul
  broker UID 10000 détient les trois montages métier fictifs ; arrêt sans purge
bash scripts/deploy-stage-safe.sh --replace-stage [staging validé] --archive-current [archive exacte] --confirm-services-stopped
  ancien code 288 KiB archivé par renommage, staging activé ; ancien conteneur
  réel arrêté, aucune suppression ni activation de service par ce script
docker compose ... stop (composition d'essai vrais canaux), puis docker compose depuis le déploiement actif avec paths.real.env up -d --build --wait
  composition d'essai arrêtée pour éviter deux consommateurs ; Hermes et
  broker réels healthy ; aucun port publié ; Hermes volume OAuth et config ro
  seulement ; broker UID 10000, trois montages métier approuvés, volume SQLite
  natif et runtime privé ro ; SQLite integrity_check ok, plans 0,
  weekly_runs 0, weekly_enabled false ; aucun classement personnel lancé
accord final explicite de Clément ; docker compose ... stop broker ; écriture atomique du runtime privé ; validate-private.py ; docker compose ... up -d --no-deps --wait broker
  copie de l'ancienne configuration conservée, weekly-approval.json 0600 avec
  propriétaire et preuve de tâche manuelle, weekly_enabled true ; validation
  privée OK, broker healthy, due_now false le mercredi 14 octobre, weekly_runs 0,
  plans 0, integrity_check ok ; seuls Hermes et broker réels tournent, aucun
  des deux couples d'essai ne tourne, aucun document personnel essayé
docker compose run --rm --no-deps ... hermes --provider openai-codex -m gpt-6-luna --reasoning low -z [texte fictif]
  code 0, sentinelle attendue reçue ; sortie filtrée, aucun secret affiché ;
  volume Hermes privé existant utilisé, aucune clé API OpenAI dans Compose
Codex get_usage_limits (compte de l'application, lecture seule)
  forfait Plus, 10 % du créneau 5 h et 42 % du créneau 7 jours consommés ;
  aucun crédit additionnel ; lien d'identité avec l'OAuth du volume non prouvé
python3 pere-blaise/scripts/validate-private.py /private/tmp/pb-test-20261014-compose/private
  configuration factice, permissions et clé interne aléatoire : OK
docker run --read-only --mount hermes-pere-blaise-data:ro ... (lecture seule)
  ancien volume Hermes contient des fichiers candidats d'authentification ;
  aucune valeur lue, validité OAuth et modèle non vérifiées
```

## Correctif et déploiement du 15 octobre

```text
docker logs hermes-pere-blaise-broker (sortie filtrée par ID d'incident)
  901ac3f311ba : PB-PLAN-INVALID, analyse, ValueError ;
  a74790a03ad9 : PB-SEND-NOTFOUND, send, sans exception
docker exec hermes-pere-blaise-broker python -c [compteurs de métadonnées]
  Documents : 7 156 fichiers, 221 dossiers, 2 fichiers > 1 Gio ;
  Downloads : 4 fichiers ; aucun nom, octet ou hash de document affiché
docker exec hermes-pere-blaise-broker python -c [comptage de correspondances]
  0 nom ou chemin contient à la fois « facture » et « gcu » ; aucun envoi lancé
python3 -m unittest discover -s tests -v (depuis pere-blaise)
  45 tests OK ; nouveaux tests : grande bibliothèque Documents, absence de fuite
  vers le modèle, application fictive, collision normalisée et protection source
deploy-stage-safe.sh --preview puis --stage --confirmed-total-bytes 289506
  67 fichiers, 289 506 octets sous budget 2 Mio ; staging validé par 45 tests
docker build -q -f [Dockerfile du staging] [staging]
  image construite ; essai docker run --rm sans montage : 1 002 Documents fictifs,
  dont un fichier creux de 2 Gio, inventoriés ; limite Downloads maintenue
docker compose --project-directory [staging] --env-file [privé] config --quiet
  OK ; aucun secret affiché
docker exec hermes-pere-blaise-broker python /app/scripts/state-backup.py backup
  instantanés cohérents plans et ingress dans le volume privé ; SHA-256 et
  integrity_check vérifiés ; aucune donnée ni aucun volume supprimé
lifecycle.sh stop ; deploy-stage-safe.sh --replace-stage [staging]
  --archive-current [archive] --confirm-services-stopped ; lifecycle.sh start
  ancien code conservé sous .archive/pere-blaise-20261015-pre-inventory-fix ;
  Hermes et broker redémarrés healthy sans port publié
docker inspect [deux conteneurs] ; docker exec [broker] python -c [état filtré]
  Hermes : /opt/data et config ro seulement ; broker : Downloads, Documents,
  backups, runtime privé ro et volume /state ; deux SQLite integrity_check ok ;
  weekly_enabled true. Aucune nouvelle analyse sur données personnelles lancée
  par le développement.
mention Slack humaine « analyse » à 6 h 14 après déploiement
  PB-DL-EMPTY incident b436770f921a ; comptage sans noms, octets ni hashes :
  zéro fichier régulier visible dans Downloads, aucune erreur d'accès ;
  aucun plan ni mouvement. Ancienne erreur d'inventaire Documents non répétée.
```

## Points encore ouverts en exploitation

### Collision de destination du 15 octobre

```text
docker logs --since 3h hermes-pere-blaise-broker (filtre de l'ID d'incident)
  a20bcda5460c : PB-PLAN-COLLISION, analyse, ValueError
docker exec broker : inventaires de métadonnées et clés normalisées uniquement
  deux fichiers Downloads de noms distincts ; aucun doublon de dossier Documents ;
  un des deux basenames Downloads occupe déjà une destination sous Documents ;
  a_trier est libre pour les deux noms ; aucun nom ni contenu affiché
python3 -m unittest discover -s tests -q
  48 tests OK ; cible occupée réorientée vers a_trier, document préexistant
  intact après application fictive, échec maintenu si a_trier est aussi occupé
deploy-stage-safe.sh --preview puis --stage --confirmed-total-bytes 304862
  67 fichiers, 304862 octets sous budget 2 Mio ; 48 tests du staging OK
lifecycle.sh stop ; deploy-stage-safe.sh --replace-stage ; lifecycle.sh start
  aucun plan applying ; ancien code archivé sous
  .archive/pere-blaise-20261015-pre-collision-fix ; broker reconstruit ;
  Hermes et broker healthy avec les trois montages personnels approuvés
docker exec broker : proposition contrôlée sur l'inventaire réel, sans registre
  deux sources ; une cible proposée occupée ; deux actions sûres vers a_trier ;
  aucune destination finale occupée ; aucun nom, hash ou contenu affiché ;
  aucun plan créé, fichier déplacé ni pièce jointe envoyée
```

Le modèle ne reçoit pas les noms des documents classés. La réorientation
locale produit un plan à examiner ; elle ne déplace aucun fichier lors de
`analyse` et n'autorise toujours qu'un `range` explicite de l'auteur.

Décision ultérieure du propriétaire : utiliser le sous-répertoire existant
`Documents/a_trier/doublons` pour les conflits de nom. Vérification en lecture
seule depuis le broker : ce chemin est un répertoire et non un lien symbolique.
La détection reste fondée sur le nom normalisé, sans comparaison de contenu.
Les tests couvrent sa présence, son absence, une cible déjà occupée dans ce
sous-répertoire, le compte `a_trier` et la conservation du fichier préexistant.
`python3 -m unittest discover -s tests -q` : 49 tests OK sur arbres fictifs.
Le staging contrôlé de 308058 octets a passé ces 49 tests, puis l'ancien code a
été archivé sous `.archive/pere-blaise-20261015-pre-duplicates-folder` avant
redémarrage des deux services `healthy`. Un contrôle du broker en lecture seule
sur l'inventaire réel, qui comptait alors trois sources, a détecté une cible
occupée et placé exactement cette action dans `a_trier/doublons` ; toutes les
destinations finales étaient libres. Aucun plan n'a été enregistré ni appliqué.

### Diagnostic des montages du 15 octobre

```text
docker inspect hermes-pere-blaise-broker (Mounts et labels Compose uniquement)
  projet hermes-pere-blaise ; déploiement actif sous deployments/pere-blaise ;
  fichier d'environnement effectif paths.env ; trois montages métier sous
  /private/tmp/pb-realchannel.ZNsEDz, malgré l'état healthy
docker logs --since 2h hermes-pere-blaise-broker (filtre des deux IDs)
  665ffbff51b1 : PB-DL-EMPTY, analyse, ValueError
  78fb0d880f35 : PB-SEND-NOTFOUND, send, sans exception
comptage hôte des entrées visibles, sans lecture d'octets
  /Users/clement/Downloads : deux fichiers réguliers visibles ; Downloads fictif : zéro
paths.env privé sauvegardé dans paths.test.env ; chemins réels de paths.real.env
  transférés atomiquement dans paths.env après contrôle des trois racines approuvées
validate-private.py ; docker compose config --quiet ; docker compose up -d --no-build --wait broker
  configuration valide ; broker recréé et healthy ; aucun volume effacé
docker exec broker : scanner et recherche locale en lecture seule
  /downloads : deux fichiers réguliers visibles ; /documents : une seule
  correspondance « invoice GPU », au chemin attendu ; aucun octet ouvert,
  aucune pièce jointe envoyée, aucun plan créé et aucun range exécuté
python3 -m unittest discover -s tests -q ; bash -n scripts/lifecycle.sh ; git diff --check
  46 tests OK ; garde contre les montages temporaires testée ; contrôles OK
deploy-stage-safe.sh --preview puis --stage --confirmed-total-bytes 299416
  67 fichiers, 299416 octets sous budget 2 Mio ; 46 tests du staging OK
lifecycle.sh stop ; deploy-stage-safe.sh --replace-stage ; lifecycle.sh start
  ancien code archivé sous .archive/pere-blaise-20261015-pre-mount-guard ;
  staging activé par renommage ; deux services redémarrés healthy ;
  aucun ancien déploiement ou volume supprimé
docker exec broker : scan complet Downloads et inventaire Documents, lecture seule
  deux sources avec empreintes locales calculées, 221 dossiers Documents ;
  contexte planificateur construit pour deux fichiers ; aucun nom, hash ou
  contenu affiché ; aucun appel au modèle et aucun plan créé
docker inspect : montages effectifs après redémarrage
  /downloads=/Users/clement/Downloads ; /documents=/Users/clement/Documents ;
  /backups=/Users/clement/Backup-pere-blaise ; broker et Hermes healthy
```

- Comptes : les trois tokens sont dans le runtime privé 0700, fichiers 0600. L'API Telegram confirme le bot attendu et aucun webhook ; l'ID privé de Clément a été relevé sans affichage et placé dans `broker.json`. Les tokens Slack actifs possèdent `app_mentions:read`, `chat:write`, `files:write` et `connections:write` ; l'hôte WebSocket est sous `.slack.com`. La clé interne est configurée hors dépôt et un appel réel Codex sur texte fictif a réussi. Un message Telegram était encore en attente lors du diagnostic broker arrêté : l'unicité du consommateur reste à établir. Le compte Slack d'Élise reste à créer avant son ajout à l'allowlist. Aucun secret n'a été fourni dans le chat ni journalisé.
- Modèle : choix du propriétaire `openai-codex` / `gpt-6-luna` / `low` ; l'image épinglée reconnaît le modèle et un appel réel court sur texte fictif a réussi via l'OAuth du volume avant et après redémarrage. Le planificateur complet a produit les plans de la recette sur fichiers fictifs. Le renouvellement ultérieur du jeton et les limites de l'abonnement associé à ce volume restent à vérifier, sans repli payant.
- macOS : les trois vrais chemins choisis par Clément existent et Docker Desktop peut les monter ; UID 10000 y voit R/W/X dans le conteneur. Le développement n'a ouvert aucun document personnel, mais Clément a lui-même utilisé `envoie` sur l'un d'eux. Des compteurs de métadonnées ont servi au diagnostic du 15 octobre ; ils ne prouvent pas toutes les opérations sur fichiers protégés par macOS. Si une alerte apparaît, accorder seulement les droits Fichiers et dossiers ciblés Downloads/Documents, sans Accès complet au disque par défaut. Aucune autorisation manquante n'a été constatée.
- E2E sur arbres fictifs avec les vrais canaux : la tâche manuelle a retourné zéro échec API et Clément a reçu ses deux messages sur Telegram et Slack, sans mouvement ; une mention humaine Slack a obtenu accusé et plan complet dans le même fil ; une nouvelle commande Telegram a obtenu accusé et plan complet. Clément a aussi reçu une pièce jointe personnelle via Telegram. Les scénarios d'échec et limites non exercés restent listés par exigence dans le tableau ; la validation finale pour l'activation hebdomadaire a déjà été donnée.
- Exploitation : purge chronologique des journaux techniques non validée ; migration hors ligne 1→2→1 testée localement, mais mise à jour d'image et retour arrière des vrais volumes/OAuth non exercés. Backups de documents conservés sans purge.
- Déploiement réel : chemins, budget et aperçu de copie relus par Clément ; premier staging démarré healthy sur données fictives, ancien code archivé sans suppression. Le correctif du 15 octobre a suivi un second staging, un essai Docker jetable et l'archivage de la version précédente. Services healthy avec montages approuvés, aucun port publié ; `weekly_enabled` reste true. Clément a testé un envoi personnel ; aucun classement personnel n'a été lancé. Sa nouvelle `analyse` a atteint le cas Downloads vide sans l'erreur Documents antérieure ; un plan complet après correctif et le premier dimanche réel restent à observer.
