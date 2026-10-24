# Matrice d'accès

| Ressource | Lecture | Écriture/exécution | Identité | Justification et refus |
| --- | --- | --- | --- | --- |
| Volume `hermes-leodagan-data` `/opt/data` | Oui | SQLite et état Hermes | utilisateur Hermes du conteneur | Aucun montage dans un autre agent ; contrôle `docker inspect` restant. |
| `/outbox` | Oui | Export textuel seulement | Hermes | Répertoire privé ; `HERMES_WRITE_SAFE_ROOT=/opt/data:/outbox`. |
| Articles HTTPS publics | Oui via `editorial_read_source` | Aucune | Léodagan | DNS et redirections contrôlés avant connexion ; 403/paywall signalé, jamais contourné. |
| OpenAI Codex | Inférence | OAuth privé | Léodagan | Aucun fournisseur de secours, pas de clé API. |
| Slack | Fil de `#agent-leodagan` | Réponse au fil demandé | Bot Léodagan | Un seul utilisateur et canal allowlistés, DM désactivé. |
| Telegram | DM dédié | Réponse au DM demandé | Bot Léodagan | Un seul ID autorisé, groupes interdits ; bot et polling activés le 24 octobre, réponse et refus encore à tester. |
| LinkedIn | Page publique ; API officielle conditionnelle | Aucune | Aucun jeton actuel | Aucun scope d'écriture et aucun outil de publication. |
| Hôte, autre agent, socket Docker | Aucun | Aucun | — | Aucun montage ni port hôte ; test d'isolation de recette restant. |

La configuration charge le skill par `SOUL.md` et expose sur Slack et Telegram `memory`, `session_search` et `leodagan_editorial`. Le toolset `web` a été retiré après deux refus réels de `web_extract` par son backend limité à la recherche ; `editorial_read_source` couvre les liens publics demandés. Une vérification sur l'image chargée a montré l'absence de `terminal`, `execute_code`, `cronjob_manage`, `image_generate`, `delegate_task`, `write_file`, `browser_navigate` et `send_message` de cette surface. Les commandes intégrées Hermes sont contrôlées séparément par `allow_admin_from`/`group_allow_admin_from` sans identité correspondante et les allowlists `/help`, `/whoami`, `/new`, `/stop` ; le menu Telegram est limité à ces quatre entrées. L'image épinglée a résolu ces politiques avec `cron_denied=True` sur les DM et les groupes des deux canaux avant déploiement. Les refus par identité et canal doivent encore être éprouvés avec de vrais comptes.
