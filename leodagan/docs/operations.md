# Exploitation de Léodagan

## État et diagnostic

Le conteneur et le cron sont volontairement arrêtés tant que le `TODO.md` n'est
pas validé. Lorsqu'ils sont activés, vérifier leur état avec :

```sh
./scripts/check-health.sh
docker compose logs --tail 200 leodagan
docker compose exec leodagan hermes cron list --all
```

Le healthcheck Docker vérifie rapidement que le heartbeat du gateway a moins
de deux minutes. Le script `check-health.sh` est plus complet et sert au
diagnostic manuel ; il ne doit pas être utilisé comme healthcheck Docker.

Un échec de santé impose la pause du cron avant investigation :

```sh
docker compose exec leodagan hermes cron pause ecc666ceb1cb
```

Les limites du conteneur concernent seulement Léodagan : 1 CPU, 768 Mio et 64
processus. Lors de leur validation, le gateway consommait environ 210 Mio et
19 processus au repos. Le conteneur est ensuite arrêté tant que le cron reste
en pause ; un statut Docker `unhealthy` après cet arrêt est attendu, car aucun
heartbeat ne peut alors être produit.

## Sauvegarde et restauration

Le runtime contient le jeton OAuth et ne doit pas être copié dans un dépôt ni
vers un stockage non chiffré. Avant une mise à jour, le propriétaire réalise
une sauvegarde chiffrée du répertoire `runtime/` selon la politique de
sauvegarde de son poste, puis vérifie qu'elle est lisible hors du dépôt.

La restauration s'effectue conteneur arrêté : restaurer `runtime/` depuis la
sauvegarde chiffrée, vérifier les permissions de `runtime/auth.json`, démarrer
le conteneur, puis exécuter `./scripts/check-health.sh`. Ne jamais restaurer
un runtime provenant d'un autre agent Hermes.

Les livrables de `review-inbox/` sont des documents de travail : leur durée de
conservation et leur emplacement de sauvegarde restent à approuver par le
propriétaire avant réactivation.

## Mise à jour et retour arrière

1. Mettre le cron en pause et arrêter le conteneur.
2. Sauvegarder le runtime chiffré.
3. Tester intentionnellement une nouvelle image via `HERMES_IMAGE`, puis lancer
   les contrôles statiques et une édition de test.
4. Si elle est validée, relever son digest avec `docker image inspect`, le
   consigner dans `compose.yaml`, puis redéployer le conteneur.
5. En cas d'échec, revenir au digest précédemment validé dans `compose.yaml`,
   restaurer le runtime si nécessaire, et garder le cron en pause.

## Révocation OAuth et arrêt définitif

En cas de compromission, arrêter le conteneur, révoquer la session Codex dans
le compte associé, puis supprimer le fichier `runtime/auth.json` de manière
récupérable selon la politique du poste. Une nouvelle authentification passe
par `scripts/adopt-codex-auth.sh` et un test contrôlé.

Pour un arrêt définitif, mettre le cron en pause, arrêter le conteneur,
sauvegarder ou purger les livrables selon la décision du propriétaire, puis
archiver le runtime privé séparément de tout autre agent.
