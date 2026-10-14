# Père Blaise — état de réalisation

Père Blaise propose un classement des fichiers réguliers visibles de `Downloads` vers des dossiers existants de `Documents`, puis applique **uniquement** `range <ID>` demandé par l'auteur du plan. Il recherche un fichier par son seul basename et peut l'envoyer en pièce jointe Telegram ou Slack. L'exploitant est Clément. L'activation réelle reste en attente de la recette et des identités/secrets privés.

Les contrats de référence sont [SPECIFICATIONS_FONCTIONNELLES.md](SPECIFICATIONS_FONCTIONNELLES.md) et [SPECIFICATIONS_TECHNIQUES.md](SPECIFICATIONS_TECHNIQUES.md). La convention commune est [../AGENTS.md](../AGENTS.md). La révision locale Hermes lue est `bd0affe5` ; l'image présente sous le digest de `compose.yaml` annonce **v0.21.6, upstream `818c13be`**. Le digest est épinglé, mais une authentification OAuth de test et un appel modèle restent à vérifier avant activation.

## Commandes

- `analyse` : plan complet, aucun mouvement ; un nouveau plan invalide l'ancien ; échéance 30 minutes.
- `détaille <ID>` : actions, raison de chaque destination, pourcentage `a_trier`, échéance.
- `range <ID>` : accord final de l'auteur ; backups vérifiés avant mouvement, journal, rollback/récupération.
- `envoie <nom>` : recherche insensible à la casse et aux accents sur les basenames ; zéro, un ou tous les résultats. Après plusieurs résultats, répondre avec le numéro choisi.
- `apprentissages` : observations et suivis locaux, ainsi que chemin du backup ; correction/effacement par l'exploitant hors ligne.

Les identités sont `(plateforme, ID)` : `telegram:...` et `slack:...` restent distinctes, sauf association explicite dans `identity_map` privé après vérification humaine. Telegram n'accepte que le chat privé du compte autorisé. Slack n'accepte que les mentions dans le canal privé configuré et répond dans le fil. Les API de livraison sont natives ; aucun document n'est transmis au modèle. Les membres du canal Slack privé peuvent voir les noms et pièces jointes du canal.

## Décisions d'architecture

Le service Compose `pere-blaise` exécute Hermes comme planificateur avec `openai-codex`, mémoire générale désactivée et `platform_toolsets.api_server: []`. Le service `broker` est le seul à monter `Downloads`, `Documents`, backups et son volume SQLite privé. Les tokens de canal restent hors dépôt dans un dossier privé monté en lecture seule. Aucun socket Docker, dépôt entier, `$HOME` ni dossier personnel supplémentaire n'est monté dans Hermes. Le broker n'expose aucun port public. Le réseau Compose sortant n'impose pas encore une allowlist de domaines vérifiée : point bloquant de la revue d'isolation.

Le modèle ne reçoit que les noms et métadonnées minimales des téléchargements, les dossiers existants de Documents et les indices d'apprentissage. Il ne reçoit ni noms des fichiers déjà classés, ni hash, ni octets. Le broker reconstruit le manifeste à partir de l'inventaire local et rejette une action absente, en double, renommée, hors dossier ou en collision. Seul `a_trier` peut être créé. Le classement est `High` si zéro `a_trier` sans nom opaque ; `Medium` si strictement moins de 20 % vers `a_trier` sans nom opaque ; `Low` sinon.

L'exception de mémoire Hermes désactivée, approuvée le 13 octobre 2026 dans l'existant, est conservée. Les apprentissages spécialisés sont dans SQLite privé pendant 90 jours ; les cas non résolus restent jusqu'à correction/effacement. Le propriétaire doit confirmer cette exception à la revue finale. Le fournisseur de modèle ne bascule jamais vers une API payante. Le coût et la limite de l'abonnement doivent être contrôlés avant l'activation.

## État des preuves

`python3 -m unittest discover -s pere-blaise/tests -v` : 36 tests locaux passés le 14 octobre 2026. `docker compose config --quiet` : passé avec chemins temporaires. Une composition Docker entièrement isolée a démarré avec Hermes et broker `healthy`, deux volumes natifs de test et trois montages métier sous `/tmp` ; un mouvement réel et son backup ont été vérifiés dans le broker UID 10000. Hermes n'avait pas de montage Downloads/Documents ; `/v1/toolsets` a renvoyé zéro toolset activé et un appel sans clé a reçu 401. Les volumes/conteneurs de test ont été retirés. Aucun bot, app ou vrai fichier personnel n'a été utilisé dans ces tests.

## Activation et exploitation

Lire [docs/runbook.md](docs/runbook.md), [docs/policy.md](docs/policy.md), [docs/access-matrix.md](docs/access-matrix.md) et [TRACEABILITY.md](TRACEABILITY.md). La tâche du dimanche 17 h `Europe/Paris` est désactivée par défaut. Son déclenchement manuel de test puis l'accord de l'exploitant sont nécessaires pour la mettre en service. Les backups de documents ne sont jamais purgés automatiquement.
