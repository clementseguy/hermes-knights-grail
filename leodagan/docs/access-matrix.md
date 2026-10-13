# Matrice d'accès de Léodagan

| Ressource | Accès | Identité | Justification | Refus / contrôle |
| --- | --- | --- | --- | --- |
| `/opt/data` | Lecture/écriture | utilisateur `hermes` | État Hermes, OAuth et journaux privés | `HERMES_WRITE_SAFE_ROOT` ; aucun montage partagé avec Père Blaise. |
| `/review-inbox` | Lecture/écriture | utilisateur `hermes` | Livrables prêts à relire | Dossier unique par run ; refus d'écrasement ; aucun autre répertoire métier monté. |
| `assets/` | Aucun accès conteneur | — | Le style visuel est déjà transcrit en prompt | Aucun montage Docker. |
| Internet HTTPS sortant | Lecture | réseau Docker isolé | Consultation de sources publiques reconnues | Aucun port publié ; pas de réseau hôte ; pas d'identifiant tiers, de connexion ou de contournement de paywall. |
| OpenAI/Codex | Inférence OAuth | abonnement du propriétaire | Recherche et rédaction | Jeton isolé dans `runtime/auth.json`; aucun repli API implicite. |
| Terminal | Commandes courtes de lecture | utilisateur `hermes` | `curl` explicite de sources publiques | Navigateur et `execute_code` interdits par le skill ; écriture via `write_file` seulement. |
| LinkedIn | Aucun | — | Hors périmètre | Le skill interdit connexion, publication et programmation. |
| Docker | Aucun accès depuis le conteneur | — | Le conteneur ne s'administre pas lui-même | Aucun socket Docker monté ; capacités Linux réduites. |
| Telegram | Notification sortante future | bot dédié | Avertir le propriétaire d'un brouillon ou d'un incident | Token hors dépôt ; ID utilisateur unique ; aucun contenu de post ou commande métier. |
| Slack | Notification sortante future | application dédiée | Même alerte lorsqu'elle sera configurée | Pas de token, canal ni socket configuré avant validation humaine. |
