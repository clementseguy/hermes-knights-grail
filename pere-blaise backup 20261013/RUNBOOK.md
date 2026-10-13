# Runbook

Arrêt : décharger les relais Slack et Telegram, puis le broker ; arrêter ensuite le conteneur. Reprise : démarrer le conteneur, attendre son API loopback, démarrer broker puis relais, vérifier le socket et envoyer `apprentissages` sur chaque canal.

Incident d’authentification/quota/indisponibilité : aucun repli fournisseur, aucun `range` ; conserver les fichiers, relever uniquement le code d’erreur local, faire renouveler le secret par le propriétaire puis redémarrer et tester une analyse non destructive.

Sauvegarde : arrêter le broker avant copie cohérente de SQLite et secrets chiffrés hors dépôt ; restaurer dans un répertoire privé 0700, vérifier les permissions 0600 et exécuter un test `détail` sans `range`. Quarantaine : purge uniquement par décision explicite du propriétaire.
