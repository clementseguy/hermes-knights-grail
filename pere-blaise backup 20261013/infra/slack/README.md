# Slack — Père Blaise

Slack complète Telegram : il ne le remplace pas. Cette procédure est prête à
être exécutée dès que le workspace Slack est connecté et que le propriétaire a
confirmé les membres du canal.

## Contrat

- Application : `Hermes — Père Blaise`.
- Canal unique : `#agent-pere-blaise`.
- Réponses : uniquement dans le fil du message qui mentionne l’agent ; aucun
  DM, aucune publication vers un autre canal, aucune notification proactive.
- Autorisations : allowlist de canal et d’utilisateurs explicite ; jamais
  `allow_all_users`.
- Capacités : reprendre exclusivement les commandes déterministes de Telegram
  (`analyse`, `détail`, `range`, `apprentissages`). L’envoi de fichiers reste
  volontairement limité à Telegram : Slack n’a donc pas le scope `files:write`.
  `range` reste une validation humaine par identifiant de plan.

## Mise en service à exécuter

1. Créer le canal privé `#agent-pere-blaise` et confirmer ses membres autorisés
   avec le propriétaire.
2. Créer l’application Slack dédiée en important
   [`app-manifest.json`](app-manifest.json), avec le nom ci-dessus et des tokens
   distincts de tout autre agent. Le manifeste ne demande que
   `app_mentions:read` et `chat:write`.
3. Choisir Socket Mode afin d’éviter une URL publique ; stocker les tokens dans
   le runtime privé avec permissions `0600`, jamais dans ce dépôt ni dans Docker.
4. Créer un token d’application Socket Mode (`connections:write`) et installer
   l’application dans le workspace pour obtenir son token bot. Copier
   [`slack.env.example`](slack.env.example) vers le répertoire privé, avec le
   canal `C0C8URDEBGC` et l’utilisateur autorisé ; la valeur réelle reste hors
   dépôt.
5. Configurer les allowlists de l’application : canal et membres validés ;
   désactiver les DM et tout canal non listé.
6. Inviter l’application dans le canal privé, puis régénérer et charger le
   plist `com.local.hermes-file-control-slack`. Il partage le broker local, non
   les secrets Telegram ni le conteneur planificateur.
7. Exécuter et consigner les tests : mention autorisée, utilisateur refusé,
   autre canal refusé, réponse dans le bon fil, refus de `range` sans plan et
   échec de livraison.

## Blocage actuel

Le canal privé `#agent-pere-blaise` a été créé le 13 octobre 2026 avec
l’identité connectée uniquement. L’application Slack dédiée, ses tokens, ses
scopes, les membres supplémentaires, le relais local et les tests d’entrée
restent à réaliser. Aucun message initial n’est publié sans décision du
propriétaire.
