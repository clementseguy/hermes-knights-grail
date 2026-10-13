# Réseau et identités

- Hôte : Telegram et Slack sortants uniquement, pour les relais déterministes.
- Hôte → planificateur : `127.0.0.1:8643` uniquement.
- Conteneur : fournisseur de modèle configuré dans `auth.json` privé uniquement ; aucun accès à l’hôte, aux bibliothèques ou aux sockets.
- Toute nouvelle destination réseau exige une revue du propriétaire et un test de refus.
