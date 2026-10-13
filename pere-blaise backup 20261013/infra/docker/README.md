# Conteneur planificateur : règles de déploiement

Ce fragment est intentionnellement un modèle, pas un fichier à lancer. Avant activation, il faut :

1. construire une image Hermes exactement épinglée par digest ;
2. injecter `HERMES_PLANNER_API_KEY` depuis un fichier hôte privé, jamais depuis Git ;
3. vérifier que `platform_toolsets.api_server: []` produit bien une session sans terminal, fichiers,
   navigateur, web, cron, code ou délégation ;
4. conserver le système de fichiers racine éphémère et non monté depuis l’hôte : l’image s6 actuelle
   n’est pas compatible avec `read_only` sur Docker Desktop, car elle exécute son init sous `/run` ;
   durcir les capacités Linux seulement après un test de démarrage explicite ;
5. ne publier que `127.0.0.1:8643:8642`.

`docker-compose.planner.yml` crée un volume neuf et ne reçoit de l’agent existant que `auth.json`,
monté en lecture seule. Le fichier privé `planner.env` fournit la clé de l’API interne et les deux chemins
hôte ; il ne doit jamais être placé dans ce répertoire versionnable.

Le conteneur reçoit déjà le contexte réduit par l’API. Il n’a aucune raison de monter la bibliothèque
personnelle, le socket Docker, le broker local ou le token Telegram.

Ce compromis ne donne aucun accès hôte supplémentaire : les seules surfaces montées restent le volume neuf
`/opt/data`, la configuration et l’authentification en lecture seule.

Validation Docker Desktop du 13 octobre 2026 : `cap_drop: [ALL]`,
`no-new-privileges:true` et la publication loopback ont été constatés sur le
conteneur en cours d’exécution. L’image actuelle reste root avec une racine
inscriptible : son init requiert `/run`; ne pas activer `read_only` ou un
utilisateur non-root sans une image explicitement validée.
