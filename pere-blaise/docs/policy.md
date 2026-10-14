# Politique opérationnelle — Père Blaise

**Autonome :** inventorier les seuls fichiers réguliers visibles de `Downloads`, proposer un plan, rechercher par nom sous `Documents`, rapprocher localement un fichier suivi dans `a_trier`, notifier une analyse hebdomadaire une fois activée. Aucune de ces opérations ne déplace de fichier. La première interaction doit proposer : « Je peux retenir les préférences et décisions durables de cet agent/projet ; confirmez ce que je dois conserver. » Ici seules les corrections locales confirmées sont conservées ; aucune mémoire libre Hermes n'est activée.

**Validé par une commande de l'auteur :** `range <ID>` est l'accord final pour le plan exact de 30 minutes. `envoie` est l'accord explicite pour envoyer un fichier par l'API du canal d'origine ; plusieurs résultats exigent un choix non ambigu. Le propriétaire seul, hors ligne, peut corriger ou supprimer un apprentissage.

**Interdit :** lire le contenu par le modèle, lui fournir hash ou nom de document déjà classé, déplacer sans `range`, modifier/supprimer un document préexistant, créer un dossier autre que `a_trier`, écraser une cible, envoyer à un autre canal ou DM Slack, partager runtime/secrets entre agents, purger automatiquement les backups. Les fichiers cachés, symlinks et objets non réguliers sont exclus ; un inventaire inaccessible ou trop grand échoue en bloc.

**Incident :** la transaction conserve ses backups et son journal. Un échec entraîne rollback limité aux artefacts du plan ; si une édition concurrente empêche un retour sûr, état `BLOCKED_RECOVERY`, arrêt des nouveaux `range`, intervention de l'exploitant. Un timeout d'API de livraison est incertain et ne doit pas déclencher de répétition automatique. Les rétentions par défaut sont 30 jours pour plans/journaux techniques, 90 jours pour apprentissages et événements ; backups sans purge. L'application des durées n'est pas automatisée pour tous les journaux : à vérifier en revue d'exploitation.

Le modèle `openai-codex` utilise OAuth propre au volume Hermes. Aucun repli API ou fournisseur. L'exception de mémoire libre désactivée du 13 octobre 2026 doit être reconfirmée à la revue finale.
