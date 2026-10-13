# Léodagan

Léodagan est un agent Hermes isolé qui prépare des éditions LinkedIn à relire
sur l'IA agentique et la souveraineté européenne. Il ne se connecte pas à
LinkedIn et ne publie jamais.

Chaque édition est déposée dans `review-inbox/` et comprend la veille, les
sources vérifiées, les angles, un post, une accroche alternative et un prompt
visuel prêt à coller dans ChatGPT ou Gemini. Léodagan ne génère pas d'image.

## Garanties éditoriales

- Deux sources sont obligatoires : une primaire datée et une indépendante,
  reconnue, qui la corrobore ou en apporte le contexte.
- Sans ce niveau de preuve, l'édition est produite sous l'état `NON_PUBLIABLE`
  et ne contient ni post final ni image.
- L'agent traite France et Europe, pour des VP, CxO et directions techniques,
  avec une voix d'ingénieur critique et constructif.
- Les références visuelles restent locales dans `assets/` ; leur direction
  artistique est formalisée dans le prompt visuel. Elles ne sont pas montées
  dans le conteneur car Léodagan produit uniquement un prompt image.

## Registre de décision

| Champ | Décision |
| --- | --- |
| Propriétaire | Clément Seguy ; il valide toute reprise du cron et toute évolution de la politique. |
| Mission / hors périmètre | Veille France/Europe IA agentique et souveraineté, puis brouillon LinkedIn sourcé. Hors périmètre : publication, connexion à LinkedIn, message à un tiers, achat, modification d'un système externe et génération d'image. |
| Slug | `leodagan` ; projet et conteneur Docker `hermes-leodagan`. |
| Canal humain | La boîte de revue locale reste la source du contenu. Telegram doit notifier le propriétaire quand un brouillon est prêt ou qu'un incident survient ; Slack recevra la même notification quand son application dédiée sera configurée. Aucun canal ne reçoit le post complet et aucun ne permet de publier. |
| Modèle / abonnement | `openai-codex`, `gpt-6-luna`, abonnement ChatGPT/Codex. Aucun repli vers une API ou un autre fournisseur. En cas de quota ou d'indisponibilité, le run échoue et l'agent reste sans publication. |
| Réauthentification | Le propriétaire exécute `scripts/adopt-codex-auth.sh` depuis une session Codex valide, puis redémarre et teste l'agent. Le jeton ne quitte jamais `runtime/`. |
| Mémoire | Exception approuvée le 12 octobre 2026 : mémoire persistante désactivée. La veille n'apprend pas de faits non validés ; les décisions durables sont versionnées ici. Revue : avant d'ajouter une interaction humaine. |
| Toolsets et écritures | Terminal uniquement, pour consulter des sources publiques ; navigateur, messagerie et génération d'image ne sont pas activés. Écriture métier seulement dans `/review-inbox`; état Hermes seulement dans `/opt/data`. |
| Montages, réseau et secrets | Volumes locaux dédiés `runtime/` et `review-inbox/`; aucun socket Docker, répertoire personnel ou dépôt parent monté. Réseau Docker sortant par défaut, sans port publié ni écoute requise. OAuth est un secret privé dans `runtime/auth.json`. Exception technique : l'image Hermes doit modifier son utilisateur interne et superviser ses services au démarrage, donc sa racine ne peut pas être montée en lecture seule et ses seules capacités sont `CHOWN`, `DAC_OVERRIDE`, `SETGID` et `SETUID`; elles sont nécessaires au mappage UID/GID et au superviseur avant l'exécution du gateway sous l'utilisateur non privilégié. |
| Validation humaine | Toute publication, diffusion, modification externe, coût additionnel ou changement d'accès exige validation explicite de Clément Seguy. |
| Planification / alertes | Lundi et jeudi 21 h Europe/Paris, actuellement **en pause**. Chaque run crée un dossier unique. Une alerte locale de défaut est encore à finaliser avant reprise. |
| Sauvegarde, restauration et arrêt | À finaliser avant mise en production : rétention, sauvegarde/restauration testée, cadence de mise à jour et retour arrière. Arrêt immédiat : `docker compose stop leodagan`, puis pause du cron. |

## Installation

1. Vérifier que l'authentification ChatGPT/Codex de Père Blaise est active.
2. Lancer `./scripts/adopt-codex-auth.sh`. Il crée une copie privée du jeton
   dans le runtime de Léodagan afin que les renouvellements n'affectent jamais
   Père Blaise.
3. Lancer `./scripts/bootstrap.sh`.
4. Lancer `./scripts/test-edition.sh`. Le script crée puis déclenche une seule
   édition de test ; vérifier le dossier créé dans `review-inbox/`.
5. Si le résultat convient, lancer `./scripts/install-schedule.sh`. Il crée le
   job lundi et jeudi à 21:00, fuseau Europe/Paris, **en pause**. Vérifier son
   identifiant dans `cron list`, puis le reprendre manuellement avec
   `docker compose exec leodagan hermes cron resume <id>`.

## Exploitation

Le service Docker s'appelle `hermes-leodagan`; il possède son propre
`HERMES_HOME` dans `runtime/` et ne partage aucun état avec Père Blaise. Les
seuls montages utiles sont la boîte de revue en écriture et les références
visuelles en lecture seule.

Ses limites s'appliquent au seul conteneur Léodagan, jamais à Docker Desktop ni
à Père Blaise : 1 CPU, 768 Mio de mémoire et 64 processus. Elles sont adaptées
à une exécution sérielle ; les 768 Mio conservent une marge au-dessus de la
mémoire observée du gateway Hermes. L'image est épinglée à un digest validé :
une mise à jour passe impérativement par la procédure documentée.

Pour arrêter le service :

```sh
docker compose down
```

Pour consulter les sorties locales des jobs, utiliser `docker compose exec
leodagan hermes cron runs`. Pour les livrables, ouvrir directement
`review-inbox/` dans Finder.

Les procédures de contrôle de santé, sauvegarde, restauration, mise à jour et
révocation OAuth sont dans [docs/operations.md](docs/operations.md).

Les accès autorisés, leurs justifications et leurs contrôles de refus sont
décrits dans [docs/access-matrix.md](docs/access-matrix.md).

La préparation du bot de notification est dans
[docs/telegram-notifications.md](docs/telegram-notifications.md). Elle attend
la création manuelle du bot et la fourniture sécurisée du token et de l'ID
Telegram autorisé.

La même règle de notification, via un bot Slack sortant aux permissions
minimales, est détaillée dans
[docs/slack-notifications.md](docs/slack-notifications.md).
