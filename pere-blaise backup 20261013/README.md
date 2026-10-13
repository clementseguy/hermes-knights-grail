# Père Blaise

Assistant personnel local qui organise `Downloads` vers `Documents` et envoie
des fichiers depuis `Documents`. Telegram est son canal personnel additionnel ;
Slack est son canal d’équipe standard en cours de mise en service. Ce répertoire
est la source versionnable de l'agent. Il ne contient aucun secret ni état
d'exécution.

## Registre de décision

| Champ | Décision |
| --- | --- |
| Propriétaire | Clément — décisions de périmètre, coût et activation des canaux. |
| Mission / hors périmètre | Proposer et appliquer, après validation explicite, des classements `Downloads → Documents`. Hors périmètre : contenu des documents, Bureau, suppression définitive, modification autonome de Documents et sorties vers des tiers. |
| Slug | `pere-blaise`. Les identifiants historiques `hermes-file-control` sont une exception temporaire documentée ci-dessous. |
| Audience | Canal Slack privé `#agent-pere-blaise` créé le 13 octobre 2026 ; membres explicitement autorisés seulement, application dédiée encore à créer. Telegram : uniquement le chat privé de l’identifiant autorisé dans le runtime privé. |
| Modèle / abonnement | Planificateur Hermes local, joignable seulement sur `127.0.0.1:8643`. Le fournisseur, modèle, coût et responsable d’authentification doivent être confirmés dans le runtime privé avant validation formelle ; aucun repli automatique n’est permis. |
| Mémoire | Mémoire Hermes générale désactivée. L’apprentissage local SQLite ne conserve que les corrections de classement, trois mois ; voir « Apprentissage local ». |
| Toolsets / écriture | Session API sans toolset. Le processus hôte n’écrit que via l’exécuteur vérifié, après `range`. |
| Montages, réseau et secrets | Conteneur sans bibliothèques, `$HOME`, sockets Docker/broker ou token Telegram. API publiée uniquement sur loopback. Secrets sous `~/Library/Application Support/HermesFileControl/`, jamais dans Git. |
| Validation humaine | `range` est requis pour chaque déplacement ; recommandations de hiérarchie et apprentissages ne modifient jamais Documents. |
| Planification / alertes | Analyse hebdomadaire dimanche 18 h locale. Alertes, sauvegarde et procédure d’arrêt restent à compléter en P1. |
| Exceptions / revue | Mémoire générale désactivée : approuvée par le propriétaire le 13 octobre 2026, revue le 13 janvier 2027. Le planificateur HTTP local est documenté dans `POLICY.md` : aucun changement de fournisseur n’est impliqué. |

Le contrat Slack et sa procédure de mise en service sont dans
[`infra/slack/README.md`](infra/slack/README.md). Telegram ne remplace pas
Slack ; les deux canaux restent cloisonnés et soumis à leur allowlist propre.

## Fonctions

- `analyse` : lit les métadonnées de `Downloads` et `Documents`, rapproche les
  corrections manuelles sorties de `Documents/a_trier`, puis crée un plan à
  durée de vie limitée ; aucun fichier n'est modifié.
- `détail <adjectif-nom>` : affiche le plan complet, ses exclusions et d'éventuelles
  recommandations d'organisation, sans limiter la liste des actions.
- `apprentissages` : affiche séparément les exemples retenus, les suivis
  abandonnés et le nombre de fichiers en attente dans `a_trier`.
- `range <adjectif-nom>` : applique précisément ce plan, une seule fois, via
  l'exécuteur local vérifié.
- `envoie <recherche>` : cherche exclusivement dans `Documents`, envoie le
  seul résultat clair ou demande de choisir parmi une courte liste.
- une analyse hebdomadaire le dimanche à 18 h produit seulement un plan.

## Modèle de sécurité

Le planificateur Hermes reçoit les métadonnées des fichiers de `Downloads`, la
liste et des statistiques des répertoires de `Documents`, et des indices de
classement calculés localement. Il ne reçoit jamais les noms, chemins, tailles,
dates ou empreintes des fichiers déjà présents dans `Documents`. Il n'a ni
montage `Documents` ou `Downloads`, ni socket Docker, ni token Telegram. Son
unique rôle est de proposer des destinations et des recommandations non
opératives.

Chaque fichier appliqué dans `a_trier` est suivi localement par son identité de
système de fichiers. Lorsqu'il est ensuite déplacé manuellement dans
`Documents`, Père Blaise crée un exemple local conservé trois mois. Si le
fichier disparaît de `Documents`, le suivi est supprimé et
`apprentissages` permet de constater cet événement. Les noms historiques restent dans SQLite local : seul un indice de
destination pour le téléchargement courant atteint le planificateur. Un
SHA-256 peut être calculé localement pour départager des candidats ambigus ; il
n'est jamais transmis au planificateur.

### Apprentissage local

La mémoire générale Hermes est volontairement désactivée dans
`config/planner.config.yaml` : elle pourrait conserver des informations de
conversation inutiles au classement et élargir les métadonnées exposées au
planificateur. Père Blaise utilise à la place une mémoire locale, dédiée et
séparée par runtime : nom d’origine, extension, taille, dossier final et date
de correction. Les exemples expirent au bout de 90 jours. `apprentissages`
permet de les consulter ; l’expiration est automatique. Pour corriger ou
supprimer un apprentissage avant terme, le propriétaire arrête le service puis
supprime l’exemple concerné de la base SQLite privée selon le runbook P1 à
venir. Aucun secret, contenu de document ou donnée conversationnelle n’est
mémorisé.

Le processus hôte Telegram est déterministe. Il accepte seulement un chat privé
et les identifiants Telegram autorisés. Les commandes privilégiées sont
syntaxiquement strictes ; il n'exécute jamais une commande reçue de Telegram.

Le broker local conserve un plan lié à son propriétaire, valable au plus douze
heures et consommable une seule fois. Lors d'un `range`, il ne transmet que
l'identifiant du plan à l'exécuteur. L'exécuteur vérifie les chemins, les liens
symboliques, l'identité et le SHA-256 du fichier, copie vers `Documents`,
vérifie la copie puis déplace l'original vers `~/Hermes-Quarantine`. Il ne
supprime jamais définitivement un fichier. Les fichiers et dossiers cachés sont
hors périmètre.

`range` reste strictement limité à `Downloads → Documents`. Les recommandations
sur la hiérarchie de `Documents` ne déplacent, ne renomment et ne suppriment
jamais un document.

## Arborescence versionnée

- `src/` : broker Unix, registre SQLite, scanner, flux de planification et
  relais Telegram et Slack ;
- `scripts/` : exécuteur et générateur des LaunchAgents ;
- `prompts/` : contrat envoyé au planificateur ;
- `contracts/` : schéma du manifeste ;
- `config/` : exemples de configuration non sensibles ;
- `infra/docker/` : composition du planificateur Docker et son guide ;
- `tests/` : tests sans accès aux vrais documents.

Les fichiers privés suivants restent hors du dépôt, sous
`~/Library/Application Support/HermesFileControl/`, avec permissions `0700`
pour le dossier et `0600` pour les fichiers : `broker.json`, `planner.env`,
`planner-auth.json`, `telegram.env`, `slack.env`, la base SQLite, le socket et
l'offset Telegram. La quarantaine est également hors du dépôt et n'est jamais purgée
automatiquement.

### Exception d’identité historique

Le code Python, le répertoire de contrôle et les trois labels LaunchAgent
utilisent encore `hermes_file_control` / `HermesFileControl` /
`com.local.hermes-file-control`. Ils appartiennent à l’implémentation initiale,
avant la réservation du slug `pere-blaise`. Ils ne désignent aucun autre agent
et restent isolés. Le projet Compose, le conteneur et le volume ont déjà été
migrés vers `hermes-pere-blaise`. Le propriétaire décidera avant le 13 novembre
2026 entre une migration atomique des noms restants (avec sauvegarde et retour
arrière) et le maintien documenté de cette compatibilité interne.

## Installation depuis zéro

Les commandes ci-dessous installent une copie d'exécution distincte, afin que
le dépôt reste propre :

```sh
PROJECT="$HOME/workspace/my-hermes/pere-blaise"
DEPLOY="$HOME/Hermes-File-Operations/pere-blaise"
CONTROL="$HOME/Library/Application Support/HermesFileControl"

rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  "$PROJECT/" "$DEPLOY/"
cd "$DEPLOY"
python3 -m venv .venv
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Ensuite :

1. Créer `broker.json` à partir de `config/broker.example.json` dans le
   répertoire privé `CONTROL`, en remplaçant les chemins, l'identifiant Telegram
   et l'exécuteur par ceux de `DEPLOY`.
2. Créer `planner.env`, `planner-auth.json`, `telegram.env` et, pour Slack,
   `slack.env` dans ce même
   répertoire privé ; ne jamais les copier dans le dépôt. Les exemples Docker
   figurent dans `infra/docker/`.
3. Démarrer le planificateur Docker avec
   `infra/docker/docker-compose.planner.yml`, en gardant les accès aux
   bibliothèques absents du conteneur.
4. Générer les plist, les vérifier puis les installer avec `launchctl` :

```sh
python scripts/render-launchd-plists.py \
  --project "$DEPLOY" --control-dir "$CONTROL" \
  --output-dir "$CONTROL/launchd-preview"
plutil -lint "$CONTROL/launchd-preview"/*.plist
```

Le générateur lance l'interpréteur de l'environnement virtuel directement,
afin que les dépendances déclarées (dont Socket Mode) soient disponibles. C'est
ce binaire auquel macOS doit recevoir l'autorisation « Accès complet au disque »
pour que les services `launchd` lisent `Downloads` et `Documents`.

## Exploitation

Les services installés sont :

| Service | Rôle |
| --- | --- |
| `com.local.hermes-file-control` | broker local et exécuteur limité |
| `com.local.hermes-file-control-telegram` | relais Telegram déterministe |
| `com.local.hermes-file-control-slack` | relais Slack Socket Mode déterministe (si `slack.env` existe) |
| `com.local.hermes-file-control-weekly-analysis` | analyse non destructive, dimanche 18 h |

Le projet, le conteneur et le volume Docker portent explicitement le nom
`hermes-pere-blaise`.

Les nouveaux plans reçoivent un identifiant de deux mots français, par exemple
`azuré-héron`. Les accents sont acceptés ; `detail` est aussi accepté à la place
de `détail` pour éviter d'imposer un clavier accentué. Les anciens identifiants
`P-…` restent valides jusqu'à leur expiration.

Après toute mise à jour, recopier la source vers `DEPLOY`, exécuter les tests,
regénérer les plist puis redémarrer les deux services continus. L'analyse
hebdomadaire n'a pas besoin d'être redémarrée : `launchd` relira son plist à la
prochaine échéance après son rechargement explicite.

## Vérification locale

```sh
python3 -m unittest discover -s tests -v
```

Les tests sont sans dépendance externe et ne touchent ni les bibliothèques
personnelles, ni Telegram, ni Docker.
