# TODO — mise en conformité de Léodagan

Date de l'audit : 12 octobre 2026  
Statut : **planification désactivée** (`ecc666ceb1cb`) jusqu'à validation des
points bloquants ci-dessous.

Ce document transforme l'audit de conformité réalisé au regard de
`../AGENTS.md` et de `../docs/agent-creation-checklist.md` en plan d'action.
Une tâche n'est terminée qu'avec une preuve : fichier versionné, commande de
vérification ou test reproductible.

## Bloquants avant réactivation

- [x] Rendre la création d'édition idempotente.
  - Une exécution ne doit jamais réutiliser ni modifier un dossier de revue
    existant.
  - Le nom doit être unique par run, par exemple
    `YYYY-MM-DDTHHMMSS-<slug>-<run-id>`.
  - Si l'écriture d'un livrable échoue, le job doit échouer explicitement
    (`[CRON_FAILURE]`) et ne jamais être considéré comme une édition réussie.
  - Contrôle statique ajouté dans `tests/verify-config.sh`. Le test de deux
    exécutions réelles reste requis avant réactivation.

- [ ] Définir une alerte exploitable pour les échecs de cron.
  - Le dernier run du 12 octobre est marqué `ok` par le scheduler alors que
    l'agent signale deux écritures refusées : cette incohérence doit être
    détectée et remontée.
  - Destinations retenues : Telegram dès configuration du bot, puis Slack
    lorsqu'une application et un canal dédiés seront configurés. Notifier le
    premier échec de quota, une erreur d'écriture ou de livraison, puis le
    rétablissement ; ne pas notifier toutes les heures.
  - Tester un échec réel et le refus depuis une identité Telegram non autorisée.

- [ ] Gérer explicitement l'épuisement de quota Codex (`HTTP 429`).
  - Utiliser le mécanisme natif `quota_hold` d'Hermes : lorsque Codex fournit
    `retry after <durée>`, le job récurrent est suspendu jusqu'à la fenêtre de
    reprise, sans modifier les interfaces Hermes et sans sondage horaire.
  - Pour un `429` sans durée de reprise, ne pas déduire un reset ni lancer de
    boucle horaire aveugle : enregistrer l'incident et notifier Telegram, puis
    Slack lorsqu'il sera disponible. La reprise manuelle reste nécessaire.
  - Ne pas appliquer cette reprise à une erreur d'authentification, de modèle,
    de source ou d'écriture : ces cas exigent une intervention humaine.
  - Test : simuler un 429, constater une seule reprise horaire, puis vérifier
    son arrêt après un run concluant.
  - Analyse réalisée : Hermes sait déjà mettre un job récurrent en attente
    jusqu'au reset lorsque Codex fournit `retry after <durée>`, ce qui est plus
    précis qu'une relance horaire. Le 429 observé ne contient pas cette durée ;
    la méthode retenue est donc l'alerte puis la reprise manuelle, sans
    évolution du scheduler ni superviseur externe.

- [ ] Créer un test de bout en bout avant toute reprise de la planification.
  - Authentification Codex après redémarrage du conteneur.
  - Recherche avec deux sources recevables ou sortie `NON_PUBLIABLE`.
  - Création des fichiers attendus dans un nouveau dossier de revue.
  - Refus vérifié de l'écrasement d'une édition antérieure.
  - Absence vérifiée de connexion/publication LinkedIn et de génération
    automatique d'image.
  - Le validateur de livrable `tests/verify-review-bundle.sh` et l'attente de
    résultat dans `scripts/test-edition.sh` sont créés. Le script attend aussi
    un scheduler prêt avant de lancer son job ; exécution réelle en cours de
    validation.
  - Blocage constaté le 12 octobre 2026 : l'abonnement Codex a refusé les deux
    essais réels par `HTTP 429: usage limit reached`. Reprendre seulement après
    rétablissement de la limite, puis conserver la preuve du run.
  - Preuve partielle observée : une édition `NON_PUBLIABLE` unique a été créée
    le 12 octobre, mais son nom de dossier omettait le `Z` UTC obligatoire.
    L'instruction a été renforcée ; le validateur doit passer sur un nouveau
    run avant toute réactivation.

## Durcissement du conteneur et des accès

- [x] Supprimer ou justifier précisément `network_mode: host`.
  - Préférer un réseau Docker dédié sans port publié si Hermes n'a besoin que
    de sorties HTTPS de veille.
  - Réseau Docker dédié, sans port publié. Les accès nécessaires figurent dans
    `docs/access-matrix.md`.

- [x] Réduire les privilèges Docker.
  - Ajouter les protections compatibles avec l'image Hermes :
    `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, limites CPU,
    mémoire et processus, et système de fichiers en lecture seule si possible
    avec volumes temporaires ciblés.
  - Limites CPU, mémoire et processus, réseau Docker isolé, `cap_drop` et
    `no-new-privileges` sont configurés. L'image Hermes ne démarre pas avec
    une racine en lecture seule car son entrypoint modifie l'utilisateur
    interne ; cette exception est documentée dans le README.
  - Démarrage et healthcheck validés avec l'image actuelle. Le test d'édition
    reste séparément bloqué par le quota Codex.

- [x] Écrire la matrice ressources × droits × justification × test de refus.
  - Inclure `/opt/data`, `/review-inbox`, Internet, OAuth Codex, terminal,
    navigateur, LinkedIn et Docker.
  - Confirmer que seul `/review-inbox` est une sortie métier et que
    `HERMES_WRITE_SAFE_ROOT` reste minimal.

- [x] Réviser les toolsets.
  - Le navigateur est déclaré dans `config/config.yaml` mais indisponible et
    interdit dans le job planifié : le retirer ou documenter ce besoin.
  - Justifier le terminal, seul outil nécessaire à la consultation des sources
    publiques, et borner les commandes autorisées autant que Hermes le permet.

## Contrat, documentation et décisions

- [x] Initialiser un dépôt Git pour versionner la source de configuration.
  - Versionner `README.md`, `compose.yaml`, `config/`, `prompts/`,
    `skills/`, `scripts/`, `TODO.md` et les tests.
  - Vérifier que `runtime/`, secrets, journaux et `review-inbox/` généré
    restent ignorés.

- [x] Ajouter au README le registre de décision imposé par la checklist.
  - Propriétaire humain et responsable d'exploitation.
  - Mission, hors périmètre, audience et critères de succès/échec.
  - Modèle, abonnement Codex, responsable de réauthentification OAuth et
    comportement en cas de quota ou indisponibilité.
  - Toolsets, écritures, montages, réseau, secrets et validations humaines.
  - Tâches planifiées, durée maximale, coût/concurrence, idempotence, sortie,
    alertes et procédure de pause.
  - Sauvegarde, restauration, rétention, mise à jour, retour arrière,
    révocation OAuth et arrêt définitif.

- [x] Documenter les exceptions à la convention.
  - **Canal Slack** : l'agent utilise volontairement une boîte de revue locale
    et ne dialogue avec personne. Indiquer la raison, le risque accepté, la
    compensation, le propriétaire et une date de revue.
  - **Mémoire persistante** : elle est désactivée. Indiquer pourquoi cette
    veille ne doit pas apprendre automatiquement, ce qui remplace la mémoire
    et quand cette décision sera revue.

- [x] Corriger l'incohérence documentaire sur les assets.
  - Le README indique que les références visuelles sont montées en lecture
    seule, mais `compose.yaml` ne monte pas `assets/`.
  - Soit ajouter un montage réellement utile et en lecture seule, soit retirer
    cette affirmation du README.

## Exploitation et cycle de vie

- [x] Réduire les ressources du conteneur sans affecter Docker Desktop ni
  Père-Blaise.
  - Léodagan est limité à 1 CPU, 768 Mio et 64 processus. 500 Mio serait trop
    proche de la mémoire observée du gateway Hermes (environ 300--360 Mio)
    pour absorber une recherche et un appel modèle.
  - Démarrage vérifié sous ces limites : gateway prêt, environ 210 Mio et 19
    processus au repos. Le conteneur a été de nouveau arrêté ; le cron demeure
    en pause.

- [x] Épingler l'image Hermes testée et documenter la mise à jour / retour
  arrière par digest.
  - Digest validé : `sha256:9774f4f39a9bb8c2f68ce728ed5e99ddbad282163be56764afacf88ed952b784`.

- [ ] Créer une application Slack dédiée à Léodagan, calquée sur le besoin de
  notification de Père-Blaise.
  - Père-Blaise ne contient aucune configuration Slack réutilisable : aucun
    token, canal ou paramètre Slack n'est copié.
  - Autoriser seulement une notification sortante `PRET_A_RELIRE` ou incident,
    sans contenu de post, sources ni commande de publication.
  - Stocker le secret Slack uniquement dans `runtime/`, hors dépôt ; documenter
    scopes, canal autorisé, rotation/révocation et test de refus.
  - Application créée et installée dans `NexTarget-26` : `Hermes - Leodagan`.
    Sa seule portée OAuth bot est `chat:write`; Socket Mode, abonnements aux
    événements, commandes, lecture de messages et accès aux fichiers restent
    désactivés.
  - Préparation livrée : `config/slack.env.example` et
    `docs/slack-notifications.md`. Restent à fournir et tester hors dépôt : le
    jeton bot privé et l'identifiant d'un canal privé dans lequel le bot aura
    été invité.

- [ ] Créer un bot Telegram dédié à Léodagan pour notifier le propriétaire
  lorsqu'une édition `PRET_A_RELIRE` est déposée dans `review-inbox/`.
  - Créer le bot et stocker son token uniquement dans le runtime privé, hors
    dépôt et avec permissions restrictives.
  - Définir l'identifiant Telegram autorisé de Clément Seguy ; ignorer tout
    autre utilisateur et désactiver les commandes non indispensables.
  - La notification doit contenir uniquement l'état, le titre/sujet et le
    chemin local du dossier de revue ; elle ne doit ni envoyer le post complet,
    ni exposer les sources, ni permettre une publication LinkedIn.
  - Envoyer une notification seulement après vérification de l'existence de
    tous les livrables attendus. Les éditions `NON_PUBLIABLE` et les échecs
    suivent une règle de notification à décider explicitement.
  - Documenter les scopes, le chemin réseau, la rotation/révocation du token,
    la politique de confidentialité et un test de refus d'un chat non autorisé.
  - Préparation livrée : `config/telegram.env.example` et
    `docs/telegram-notifications.md`. La création réelle attend le token du
    bot et l'identifiant numérique Telegram autorisé.

- [ ] Définir journaux, indicateur de santé et procédure de diagnostic.
- [x] Définir un contrôle de santé local.
  - `scripts/check-health.sh` vérifie le conteneur et le scheduler ; il sera
    la sonde locale avant l'intégration de la notification Telegram.
- [ ] Définir rétention et purge des livrables, sorties cron et journaux.
  - `scripts/archive-review-inbox.sh` est volontairement non destructif : il
    affiche les éditions en dry-run et refuse tout archivage tant que la durée
    de conservation et le stockage chiffré ne sont pas approuvés.
- [x] Définir la sauvegarde, restauration, mise à jour, retour arrière,
  révocation OAuth et arrêt définitif.
  - Procédure initiale dans `docs/operations.md`; le test de restauration et
    la décision de rétention restent à réaliser.
- [ ] Nettoyer, après conservation des preuves utiles, les jobs de test et
  sorties d'échec historiques du runtime.

## Conditions de reprise

Ne reprendre le job `Léodagan LinkedIn` qu'après :

1. résolution et test de l'idempotence des livrables ;
2. test de bout en bout concluant, y compris un refus attendu ;
3. décision documentée sur réseau, alertes, mémoire et absence de Slack ;
4. revue humaine des permissions, du coût et du contrat éditorial.

Commande de reprise, uniquement après validation :

```sh
docker compose exec leodagan hermes cron resume ecc666ceb1cb
```
