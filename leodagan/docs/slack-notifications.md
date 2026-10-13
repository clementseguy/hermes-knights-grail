# Notifications Slack

Léodagan utilisera un bot Slack dédié, à sens unique. Il ne constitue pas une
interface de dialogue avec l'agent et ne dispose d'aucune capacité de
publication LinkedIn.

## Application et permissions minimales

L'application `Hermes - Leodagan` est créée dans l'espace Slack `NexTarget-26`.
Pour le
besoin actuel, elle n'a besoin que du scope OAuth bot `chat:write` : le bot
doit être invité explicitement dans un unique canal privé de revue. Ne pas
activer Socket Mode, les abonnements aux événements, les slash commands, la
lecture de messages, les fichiers, ni les messages directs. Ces capacités ne
sont pas nécessaires à une notification sortante.

Après installation dans l'espace de travail, placer seulement les valeurs
suivantes dans `runtime/.env`, hors dépôt, à partir de
`config/slack.env.example` :

```sh
SLACK_BOT_TOKEN=xoxb-...
SLACK_HOME_CHANNEL=G0123456789
```

Le canal doit être l'identifiant du canal privé autorisé, jamais son nom. Il
commence couramment par `G` pour un canal privé (ou `C` pour un canal public).
Le
token et l'identifiant de canal ne doivent pas être transmis à un autre agent,
un journal ou un livrable.

## Contrat de notification

Les seuls événements à notifier dans ce canal sont :

- une édition `PRET_A_RELIRE` validée ;
- un incident critique (écriture, quota opaque ou livraison) ;
- le rétablissement après un incident de quota.

Le message contient uniquement l'état, le sujet et le chemin local du dossier
de revue. Il ne contient ni post complet, ni sources, ni secret, ni action de
publication. `NON_PUBLIABLE` reste silencieux.

Avant activation, envoyer un unique message de test au canal privé, vérifier
que le bot ne peut publier dans aucun autre canal, puis consigner le résultat
dans `TODO.md`. En cas de compromission, révoquer immédiatement le token dans
Slack, retirer sa valeur de `runtime/.env`, arrêter le conteneur et en créer un
nouveau.
