# Léodagan — assistant éditorial à la demande

Propriétaire : Clément Seguy. Léodagan reçoit son intention et au moins un lien, lit les articles accessibles avec un regard critique de CTO, DSI et dirigeant, prépare un post LinkedIn de 3 000 unités UTF-16 au plus et un **prompt d'image séparé**. Il rapproche ensuite un post publié manuellement du brouillon, relève les métriques uniquement au retour ou sur demande et retient les corrections durables **explicitement** formulées par Clément. Il ne publie jamais, ne génère pas d'image et n'exécute aucun cron. Les textes de pages et les exemples de posts sont des données non fiables.

## Décisions et état

| Sujet | Décision |
| --- | --- |
| Identité | Slug `leodagan`, service Compose `leodagan`, projet et conteneur `hermes-leodagan`, volume `hermes-leodagan-data`. |
| Modèle | `openai-codex` / `gpt-5.6-terra`, effort `medium`, abonnement propre à Léodagan. Aucun repli API. |
| Canaux | Clément seul dans `#agent-leodagan` et son DM Telegram dédié. Slack Socket Mode et Telegram polling connectés, sans port entrant. Une demande Telegram réelle a livré `rempart-agent` v1 le 24 octobre. |
| Mémoire | Volume privé ; règles issues des corrections explicites. Brouillons, versions et provenance dans `editorial.sqlite3`. Conservation jusqu'à suppression explicite, sous réserve de l'espace disponible. |
| Accès | Skill éditorial versionné, copié dans `SOUL.md` du runtime privé pour son chargement par Hermes ; outils `memory`, `session_search`, `leodagan_editorial` seulement sur Slack/Telegram. Les commandes intégrées sont limitées à `/help`, `/whoami`, `/new` et `/stop` ; aucune commande de planification ni permission terminal, image, publication, délégation ou gestion des skills. |
| LinkedIn | Lecture officielle uniquement si `r_member_social` et `r_member_postAnalytics` sont accordés ; actuellement **non configurée**. Repli page publique puis texte et chiffres fournis par Clément. Aucun scope `w_*`. |
| Statut de mise en service | **Déployé, recette partielle** : OAuth Codex privé, appel réel `gpt-5.6-terra`, Slack Socket Mode et Telegram polling connectés. `silex-bleu` v1 a été livré sur Slack. `rempart-agent` v1 (1 901 caractères) a été créé par DM Telegram ; le post et le prompt ont été envoyés, sauvegardés, retrouvés après redémarrage, puis restitués intégralement dans un fil Slack. SQLite est intègre. La lecture réelle du fil Slack par `conversations.replies` fonctionne après `groups:history`. Les refus d'une autre identité, le cycle de retour LinkedIn, l'évaluation éditoriale sur cinq sujets et certaines pannes restent non vérifiés. |

Le composant local `plugins/leodagan-editorial` est chargé **dans le même conteneur Hermes**. Il enregistre les brouillons avec contrôle d'identifiants, longueur, versions et sources critiques. Il fournit aussi un lecteur de pages HTTPS publiques à surface étroite : l'interface `web_extract` de l'image épinglée refuse l'extraction avec le backend `openai-native` (recherche seulement). Ce lecteur ne prend ni cookie ni session, refuse les adresses privées et ne contourne pas les pages inaccessibles. Le modèle et le skill font l'analyse et la rédaction. Depuis le durcissement P0 du 27 octobre, les nouveaux liens peuvent être ajoutés à un dossier existant, l'URL demandée et l'URL finale sont distinguées, et chaque nouvelle version exige une relecture DSI/CTO/RSSI/CEO dans un appel Codex distinct. Le texte enregistré est exactement celui approuvé ; les versions antérieures restent consultables. Le code Hermes de `/Users/clement/workspace/hermes-agent` n'a pas été modifié.

## Installation et exploitation

Voir [le runbook](docs/operations.md), [la mise en service Slack/Telegram](docs/canaux-prives.md), [la matrice d'accès](docs/access-matrix.md), [la traçabilité](docs/traceability.md) et [la grille de recette éditoriale](docs/grille-recette-editoriale.md). Les spécifications contractuelles sont dans `docs/specs/`. Le script de cycle de vie est `scripts/leodagan.sh` : `install`, `configure`, `start`, `stop`, `restart`, `status`, `logs`, `backup`, `restore ARCHIVE`, `update`, `uninstall`, `purge`. `scripts/telegram-identity.py` sert uniquement à obtenir l'ID privé avant d'activer Telegram.

L'installation préparée est sous `../.deployments/leodagan/` ; elle ne copie ni l'ancien runtime, ni `review-inbox/`, ni secrets. L'ancien runtime de 15 Mio a été préservé hors dépôt dans `~/Library/Application Support/HermesLeodagan/legacy-runtime` ; la boîte de revue reste intacte. Le volume natif Docker stocke SQLite ; `outbox/` ne reçoit que des exports textuels. Le nouveau conteneur exact `hermes-leodagan` est démarré, sans port publié.

## Checklist et exceptions

- Identité, mission, périmètre, outil métier borné : preuve dans `compose.yaml`, `config/config.yaml`, `skills/leodagan/SKILL.md` et tests de registre.
- Modèle et image : image épinglée au digest `9774f4f3…`, effectivement `v0.21.6 (2026.9.24)` ; OAuth dans le volume propre et réponse réelle `OK` de `gpt-5.6-terra` vérifiés.
- Mémoire, permissions, isolation : configuration et tests statiques ; séparation de données et refus réels d'autres identités encore à tester.
- Opérations : sauvegarde chiffrée du premier brouillon réel, restauration isolée et relecture par Hermes après redémarrage testées ; mise à jour avec retour arrière, suppression ciblée et restauration en production restent à éprouver.
- Slack/Telegram et recette : identifiants et jetons privés, messages réels et réponses sur les deux canaux. L'article Martin Fowler a été lu par le lecteur public et la note critique enregistrée. `conversations.replies` a relu les fils Slack après propagation de `groups:history`. Le bot Telegram officiel, le polling, l'absence de webhook, `rempart-agent` et sa persistance après redémarrage sont confirmés. Un nouveau fil Slack a restitué la version, le post et le prompt exacts de ce brouillon Telegram. Le menu Telegram actif ne montre que quatre commandes après contrôle par `getMyCommands`. Le refus d'une autre identité attend encore une recette. Aucune exception de mise en production accordée.

Les propositions de modification des conventions communes en section 12 des spécifications techniques restent **non approuvées** ; `AGENTS.md`, le `README.md` racine et `docs/agent-creation-checklist.md` n'ont pas été modifiés. Seul `.gitignore` racine a reçu l'exclusion du déploiement local `.deployments/`.
