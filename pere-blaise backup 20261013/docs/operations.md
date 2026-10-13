# Exploitation durable

Propriétaire : Clément. Les journaux launchd sont sous `~/Library/Logs/`; ils ne doivent contenir ni secrets ni chemins de documents et sont revus après incident. Les alertes sont envoyées au propriétaire dans le canal qui a subi l’échec.

La tâche hebdomadaire s’exécute dimanche à 18 h locale, sans `range`, est idempotente et peut être arrêtée en déchargeant son LaunchAgent. Toute mise à jour image/dépendance passe par : digest approuvé, tests locaux, sauvegarde SQLite, redéploiement, vérification Telegram et Slack ; le rollback restaure le digest et la copie SQLite précédents.

Rotation : le propriétaire révoque/remplace clé planificateur, token Telegram ou tokens Slack dans leurs consoles, met à jour les fichiers privés 0600, redémarre les relais et vérifie `apprentissages` sans effectuer de `range`.
