# Père Blaise

Assistant personnel local qui organise `Downloads` vers `Documents` et envoie
des fichiers depuis `Documents`. Telegram est son canal personnel additionnel ;
Slack est son canal d’équipe standard. Ce répertoire
est la source versionnable de l'agent. Il ne contient aucun secret ni état
d'exécution.

## Registre de décision

| Champ | Décision |
| --- | --- |
| Propriétaire | Clément — décisions de périmètre, coût et activation des canaux. |
| Mission / hors périmètre | Proposer et appliquer, après validation explicite, des classements `Downloads → Documents`. Hors périmètre : contenu des documents, Bureau, suppression définitive, modification autonome de Documents et sorties vers des tiers. |
| Slug | `pere-blaise`. Toutes les nouvelles identités de déploiement utilisent ce slug sans compatibilité implicite. |
| Audience | Canal Slack privé `#agent-pere-blaise` et application dédiée existants ; leurs secrets et leur connectivité doivent être revalidés dans le nouveau runtime. Membres explicitement autorisés seulement. Telegram : uniquement le chat privé de l’identifiant autorisé dans le runtime privé. |
| Modèle / abonnement | `openai-codex` via l’abonnement ChatGPT/Codex, modèle par défaut `gpt-5.4`, authentifié par OAuth dans le runtime privé. Le planificateur Hermes est joignable seulement sur `127.0.0.1:8643` ; aucun repli automatique n’est permis. |
| Mémoire | Mémoire Hermes générale désactivée. L’apprentissage local SQLite ne conserve que les corrections de classement, trois mois ; voir « Apprentissage local ». |
| Toolsets / écriture | Session API sans toolset. Le processus hôte n’écrit que via l’exécuteur vérifié, après `range`. |
| Montages, réseau et secrets | Conteneur sans bibliothèques, `$HOME`, sockets Docker/broker ou token Telegram. API publiée uniquement sur loopback. Le runtime privé est recréé sous la racine de déploiement autorisée, jamais dans Git. |
| Validation humaine | `range` est requis pour chaque déplacement ; recommandations de hiérarchie et apprentissages ne modifient jamais Documents. |
| Planification / alertes | Analyse hebdomadaire dimanche 18 h locale, créée en pause au premier démarrage. Alertes, sauvegarde et procédure d’arrêt sont documentées dans le runbook. |
| Exceptions / revue | Mémoire générale désactivée : approuvée par le propriétaire le 13 octobre 2026, revue le 13 janvier 2027. Le planificateur HTTP local est documenté dans [`docs/policy.md`](docs/policy.md) : aucun changement de fournisseur n’est impliqué. |

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
`~/Library/Application Support/HermesAgents/runtime/pere-blaise/`, avec permissions `0700`
pour le dossier et `0600` pour les fichiers : `broker.json`, `planner.env`,
`planner-auth.json`, `telegram.env`, `slack.env`, la base SQLite, le socket et
l'offset Telegram. La quarantaine est également hors du dépôt et n'est jamais purgée
automatiquement.

## Reconstruction après incident

Le runtime précédent a été volontairement détruit après un déploiement hors
périmètre. Il ne doit jamais être restauré ni référencé. Toute reconstruction
utilise uniquement la source `~/workspace/my-hermes/pere-blaise`, une racine de
déploiement explicitement approuvée et le slug `pere-blaise`.

## Installation depuis zéro

Les commandes ci-dessous installent une copie d'exécution distincte, afin que
le dépôt reste propre :

La racine approuvée est
`~/Library/Application Support/HermesAgents/deployments`. Le déploiement a
trois phases explicites : aperçu sans copie, staging testé, puis activation par
renommage atomique. Les commandes exactes et le volume annoncé doivent être
relus avant la phase suivante ; le script refuse toute autre racine, lien,
destination existante ou suppression.

Ensuite :

1. Créer un environnement virtuel dans `DEPLOY/.venv`, puis créer
   `broker.json` à partir de `config/broker.example.json` dans le runtime privé
   `~/Library/Application Support/HermesAgents/runtime/pere-blaise/`, en
   remplaçant les chemins, l'identifiant Telegram et l'exécuteur par ceux de
   `DEPLOY`.
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
| `com.local.pere-blaise` | broker local et exécuteur limité |
| `com.local.pere-blaise-telegram` | relais Telegram déterministe |
| `com.local.pere-blaise-slack` | relais Slack Socket Mode déterministe (si `slack.env` existe) |
| `com.local.pere-blaise-weekly-analysis` | analyse non destructive, dimanche 18 h — installée en pause au premier lancement |

Le projet, le conteneur et le volume Docker portent explicitement le nom
`hermes-pere-blaise`.

Les nouveaux plans reçoivent un identifiant de deux mots français, par exemple
`azuré-héron`. Les accents sont acceptés ; `detail` est aussi accepté à la place
de `détail` pour éviter d'imposer un clavier accentué. Les anciens identifiants
`P-…` restent valides jusqu'à leur expiration.

Après toute mise à jour, reprendre les trois phases de déploiement sans jamais
écraser la version active, exécuter les tests, regénérer les plist puis
redémarrer les deux services continus. L'analyse hebdomadaire reste en pause
jusqu’à une validation humaine séparée.

## Vérification locale

```sh
python3 -m unittest discover -s tests -v
```

Les tests sont sans dépendance externe et ne touchent ni les bibliothèques
personnelles, ni Telegram, ni Docker.
