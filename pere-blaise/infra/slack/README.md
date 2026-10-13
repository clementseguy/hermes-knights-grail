# Slack — Père Blaise

Slack complète Telegram : il ne le remplace pas. Le canal et l’application
dédiée existent ; cette procédure décrit leur raccordement à un runtime neuf
après l’incident, sans réutiliser aucune donnée locale détruite.

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

1. Vérifier le canal privé `#agent-pere-blaise`, l’application `Hermes — Père
   Blaise` et les membres autorisés ; ne pas créer de doublon. Si l’un manque,
   obtenir une décision du propriétaire avant de le recréer à partir de
   [`app-manifest.json`](app-manifest.json).
2. Vérifier que l’application ne demande que `app_mentions:read` et
   `chat:write`, puis choisir Socket Mode afin d’éviter une URL publique.
3. Créer ou récupérer des tokens neufs dans le gestionnaire de secrets du
   propriétaire, puis les stocker dans
   le runtime privé avec permissions `0600`, jamais dans ce dépôt ni dans Docker.
4. Créer un token d’application Socket Mode (`connections:write`) et installer
   l’application dans le workspace pour obtenir son token bot. Copier
   [`slack.env.example`](slack.env.example) vers le répertoire privé, avec le
   canal `C0C8URDEBGC` et l’utilisateur autorisé ; la valeur réelle reste hors
   dépôt.
5. Configurer les allowlists de l’application : canal et membres validés ;
   désactiver les DM et tout canal non listé.
6. Inviter l’application dans le canal privé, puis régénérer et charger le
   plist `com.local.pere-blaise-slack`. Il partage le broker local, non
   les secrets Telegram ni le conteneur planificateur.
7. Exécuter et consigner les tests : mention autorisée, utilisateur refusé,
   autre canal refusé, réponse dans le bon fil, refus de `range` sans plan et
   échec de livraison.

## Réactivation après incident

Les secrets locaux ont été détruits volontairement. Avant de charger le relais,
le propriétaire fournit les tokens Slack dans un nouveau `slack.env` privé et
confirme l’identifiant du canal et l’utilisateur autorisé. Aucun message
initial n’est publié sans décision du propriétaire. La validation se termine
par une mention autorisée sur Slack et un échange Telegram, puis les refus
utilisateur/canal sont vérifiés.
