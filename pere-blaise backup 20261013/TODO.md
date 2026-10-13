# TODO — conformité Père Blaise

Audit réalisé le 12 octobre 2026 contre [`../AGENTS.md`](../AGENTS.md) et la
[checklist de création](../docs/agent-creation-checklist.md). Les points ci-dessous
ne remettent pas en cause les garde-fous déjà présents du flux `analyse → détail →
range` ; ils sont nécessaires pour rendre l’agent pleinement exploitable et
auditable selon la convention de l’équipe.

## Priorités

- **P0 — bloquant** : à traiter avant toute validation formelle ou extension de
  périmètre.
- **P1 — sécurité/exploitation** : à traiter avant de considérer le runtime
  comme durable et autonome.
- **P2 — qualité de preuve** : nécessaire pour une couverture de validation
  complète, après les P0/P1.
- **P3 — cohérence documentaire** : à planifier ; n’augmente pas à elle seule
  le risque opérationnel.

## P0 — bloquants de conformité avant une validation formelle

- [x] Ajouter au `README.md` le registre minimal de décision demandé par la
  checklist : propriétaire, mission/hors périmètre, audience, modèle,
  mémoire, capacités, montages/réseau/secrets, validations humaines,
  planification/alertes, sauvegarde/arrêt et exceptions avec date de revue.
- [x] Mettre en place le canal Slack standard `#agent-pere-blaise`, son
  application dédiée, ses allowlists, son chemin d’événements authentifié et
  ses tests de refus. Telegram reste un canal personnel **additionnel** : le
  documenter comme tel avec son utilisateur autorisé, son chat privé obligatoire
  et ses règles de notification, sans le présenter comme une exception à Slack.
  Application dédiée, Socket Mode, allowlists, relais local et test E2E de
  mention réalisés le 13 octobre 2026.
- [x] Documenter et faire approuver l’exception **mémoire Hermes désactivée**
  dans `config/planner.config.yaml`. Décrire que l’apprentissage est une base
  SQLite locale spécialisée, ce qu’elle retient, sa rétention de 90 jours,
  `apprentissages` comme mécanisme de consultation et la procédure de purge.
  Ne pas activer la mémoire générale sans une décision explicite : elle serait
  incompatible avec la minimisation actuelle des métadonnées Documents.
- [x] Documenter et faire approuver l’exception **planificateur HTTP avec clé
  API interne** au lieu du flux `openai-codex`/abonnement prescrit : fournisseur
  réellement utilisé, modèle, coût, responsable de l’authentification,
  comportement lors de quota/indisponibilité et date de revue. Approuvée le 13
  octobre 2026 ; voir `POLICY.md`.
- [x] Corriger les identités techniques pour employer partout le seul slug
  `pere-blaise` : nom du package/projet de déploiement, chemins d’exemple,
  services macOS et répertoire de contrôle, ou documenter précisément chaque
  exception historique `hermes-file-control` et son plan de migration.

## P1 — sécurité et exploitation

- [x] Ajouter une politique versionnée définissant : actions autonomes
  (inventaire, proposition, suivi de `a_trier`), action soumise à validation
  (`range`), interdits (sortir de Downloads/Documents, lire le contenu hors
  empreinte locale, modifier Documents hors du plan), critères de succès,
  d’échec, de blocage et d’escalade.
- [x] Ajouter la matrice « ressource × droits × justification × test de refus »
  pour `Downloads`, `Documents`, quarantaine, SQLite, Telegram, API locale,
  Docker et LaunchAgents.
- [x] Ajouter un répertoire `skills/pere-blaise/` versionné pour la procédure
  répétable d’organisation et de déploiement, avec scénario de validation.
- [x] Ajouter un test de configuration Docker qui prouve : pas de socket
  Docker, pas de montage `Documents`/`Downloads`/`$HOME`, port lié à loopback,
  montages d’authentification et de configuration en lecture seule, limites
  CPU/mémoire/PID et nommage `hermes-pere-blaise`.
- [~] Durcir le conteneur après test explicite de compatibilité Docker Desktop :
  `cap_drop: [ALL]`, `security_opt: no-new-privileges:true` et, si l’image le
  permet, utilisateur non-root et système de fichiers en lecture seule avec
  répertoires temporaires dédiés. Validation Docker Desktop effectuée le 13
  octobre 2026 : `cap_drop: ALL`, `no-new-privileges` et loopback sont actifs.
  Le conteneur reste root et avec racine inscriptible car l’image Hermes actuelle
  nécessite son init sous `/run`; une image compatible est requise avant de
  fermer ce point.
- [x] Définir et tester les domaines réseau autorisés : Telegram depuis l’hôte,
  API du modèle depuis le planificateur, aucune autre sortie ; documenter les
  identités et le port local `8643`.
- [x] Rendre effectifs ou retirer les paramètres inemployés de `broker.json`
  (`plan_ttl_hours`, `retention_days`) afin que la configuration versionnée
  représente le comportement réel. Ajouter des tests de propagation.

## Exploitation, rétention et reprise

- [x] Écrire un runbook d’arrêt, reprise et incident : arrêt des trois
  LaunchAgents et du conteneur, vérification du socket, reprise sûre après une
  panne, et conduite à tenir si Telegram, le planificateur ou l’authentification
  échoue.
- [x] Définir les journaux, leur rétention, les alertes et leur destinataire.
  Ajouter un contrôle de santé du broker, du relais Telegram et du conteneur.
- [x] Définir une stratégie de sauvegarde/restauration testée pour SQLite et
  les secrets privés ; préciser la rétention et purge de la quarantaine, des
  plans, des exemples d’apprentissage et des journaux.
- [x] Documenter la rotation/révocation de la clé API interne et du token
  Telegram, le responsable de réauthentification et un test de redémarrage.
- [x] Revoir la tâche hebdomadaire : documenter fuseau, durée maximale,
  idempotence, sortie, alerte et pause. Pour la conformité stricte, la créer
  d’abord désactivée, exécuter un run manuel, puis enregistrer la validation
  avant activation.
- [x] Définir un processus d’upgrade/rollback de l’image Hermes et des
  dépendances Python : responsable, cadence, digest approuvé, test préalable
  et retour arrière.

## P2 — tests et preuves de validation

- [ ] Ajouter des tests de migration et de séparation de la base locale :
  apprentissages récupérés après redémarrage, expiration à 90 jours, purge et
  impossibilité de partage avec un autre runtime.
- [ ] Ajouter un test de démarrage Docker reproductible et un test d’absence
  des capacités interdites dans la session API du planificateur.
- [ ] Ajouter un E2E Telegram réel ou un environnement de test dédié :
  utilisateur autorisé/refusé, chat privé/groupe refusé, `analyse`, `détail`,
  `range` validé, `apprentissages`, échec de livraison et indisponibilité du
  planificateur. La checklist Slack est couverte par l’exception Telegram,
  pas par un test Slack fictif.
- [ ] Enregistrer une revue humaine finale : périmètre, permissions, coût,
  politique d’apprentissage et activation de la tâche hebdomadaire.

## P3 — cohérence documentaire et structure

- [ ] Décider et documenter l’absence d’outbox : l’agent ne produit pas de
  livrable persistant ; la quarantaine est son seul artefact de sortie.
- [ ] Aligner la documentation sur le comportement actuel : l’identifiant de
  plan à deux mots est en place, mais le README mentionne encore à un endroit
  `range P-XXXXXX` ; les suivis sortis de périmètre sont visibles via
  `apprentissages`, non `détail`.
