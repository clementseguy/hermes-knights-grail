# Conteneur planificateur : règles de déploiement

Ce fragment est intentionnellement un modèle, pas un fichier à lancer. Avant activation, il faut :

1. construire une image Hermes exactement épinglée par digest ;
2. injecter `PERE_BLAISE_API_KEY` depuis un fichier hôte privé, jamais depuis Git ;
   l’authentification OAuth Codex est créée une fois dans le volume Docker privé
   `hermes-pere-blaise-data` et n’est jamais montée depuis l’hôte ;
3. vérifier que `platform_toolsets.api_server: []` produit bien une session sans terminal, fichiers,
   navigateur, web, cron, code ou délégation ;
4. conserver le système de fichiers racine éphémère et non monté depuis l’hôte : l’image s6 actuelle
   n’est pas compatible avec `read_only` sur Docker Desktop, car elle exécute son init sous `/run` ;
   elle ne démarre pas non plus avec `cap_drop: [ALL]`. `no-new-privileges:true` reste actif ;
   ne réintroduire un durcissement de capacités qu’après un test de démarrage explicite ;
5. ne publier que `127.0.0.1:8643:8642`.

`docker-compose.planner.yml` attend un volume neuf déjà initialisé par le flux
OAuth. Le fichier privé `planner.env` fournit la clé de l’API interne et le
chemin de la configuration hôte ; il ne doit jamais être placé dans ce
répertoire versionnable.

Le conteneur reçoit déjà le contexte réduit par l’API. Il n’a aucune raison de monter la bibliothèque
personnelle, le socket Docker, le broker local ou le token Telegram.

Ce compromis ne donne aucun accès hôte supplémentaire : les seules surfaces montées restent le volume neuf
`/opt/data`, la configuration et l’authentification en lecture seule.

L’image actuelle reste root avec une racine inscriptible : son init requiert
`/run` et des capacités d’initialisation. Ne pas activer `read_only`, un
utilisateur non-root ou `cap_drop: [ALL]` sans une image explicitement validée.
