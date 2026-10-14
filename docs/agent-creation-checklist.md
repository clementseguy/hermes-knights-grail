# Checklist de création d'un agent Hermes

Utiliser cette checklist avant d'implémenter puis avant d'activer un agent.
Une case n'est cochée qu'avec une décision et une preuve (fichier, commande,
test, capture non sensible ou lien vers le runbook). Les choix délibérément
différents de [la convention](../AGENTS.md) sont consignés comme exceptions.

## 1. Cadrage

- [ ] Le propriétaire humain, la mission, le public et la valeur attendue sont
  définis.
- [ ] Les entrées, sorties, systèmes tiers et données manipulées sont listés.
- [ ] Les actions autonomes, celles soumises à approbation et les interdits
  sont écrits dans la politique de l'agent.
- [ ] Les critères de succès, d'échec, de blocage et d'escalade vers un humain
  sont vérifiables.
- [ ] Les limites de coût, de durée, de fréquence et de concurrence sont
  décidées.
- [ ] Un choix existant est réutilisé quand il convient ; tout nouvel outil,
  connecteur, plugin ou script répond à un besoin non couvert démontré.

## 2. Identité et structure

- [ ] Un nom fonctionnel et un `slug` kebab-case ASCII unique sont réservés.
- [ ] Dossier, projet Compose, service, conteneur, volume, runtime/profil,
  application et canal Slack respectent la table de nommage d'`AGENTS.md`.
- [ ] Le dossier contient au minimum `README.md`, `compose.yaml`, `config/`,
  `skills/<slug>/`, les prompts/politiques nécessaires, scripts et tests.
- [ ] Le README explique la mission, les limites, le déploiement, l'arrêt, la
  réauthentification, les sorties et la reprise après incident.
- [ ] Le runtime, les secrets, les journaux et les livrables non versionnés
  sont ignorés par Git ; aucun secret ou état d'exécution n'est versionné.
- [ ] Le chemin physique de la source est sous
  `~/workspace/hermes-knights-grail/<slug>` et contient les fichiers attendus du projet ;
  il n'est ni une racine de volume, ni `$HOME`, ni un répertoire système ou
  l'un de leurs ancêtres.
- [ ] Le répertoire de déploiement est sous l'emplacement autorisé, porte le
  même `slug` et n'est pas le runtime actif à écraser.
- [ ] Avant toute copie récursive, un aperçu (`rsync --dry-run --stats` ou
  équivalent) a été relu et son volume est inférieur au budget déclaré.
- [ ] La copie ne suit aucun lien symbolique vers l'hôte (`--copy-links` / `-L`
  sont interdits) et les variables de source/destination font échouer le
  script si elles sont absentes, vides ou hors périmètre.
- [ ] Le déploiement passe par un répertoire de staging ; services arrêtés,
  démarrage et contrôles validés avant bascule vers la version active.
- [ ] Toute option `--delete` et toute suppression d'ancien déploiement ont
  reçu une validation humaine explicite après affichage des chemins et tailles.

## 3. Modèle et authentification

- [ ] Le fournisseur est `openai-codex` et le modèle par défaut est renseigné
  dans la configuration.
- [ ] L'authentification OpenAI par abonnement ChatGPT/Codex a été réalisée
  dans le runtime propre de l'agent, sans clé API.
- [ ] Le renouvellement OAuth, son responsable et un test de redémarrage sont
  documentés.
- [ ] La disponibilité, les limites d'usage et le comportement en cas de quota
  ou d'indisponibilité sont testés ; aucun repli de fournisseur n'est implicite.
- [ ] Toute exception au mode abonnement est approuvée et documentée (motif,
  coût, secret, réversibilité, date de revue).

## 4. Communication Slack

- [ ] Le canal `#agent-<slug>` existe, son objectif et ses membres autorisés
  sont définis.
- [ ] Une application Slack dédiée est créée avec le minimum de scopes, tokens
  stockés hors dépôt, événements nécessaires et URLs de redirection/événements
  documentées.
- [ ] Le chemin d'entrée réseau (URL publique, tunnel ou relais) est
  authentifié et testé ; aucune URL de développement n'est laissée ouverte.
- [ ] Les allowlists Hermes et Slack sont configurées ; `allow_all_users` est
  désactivé.
- [ ] Un test réel couvre mention dans le canal, réponse dans le bon fil,
  refus d'un utilisateur/canal non autorisé, puis erreur de livraison.
- [ ] DM, notifications proactives, messages inter-agents et publications
  externes sont soit désactivés, soit explicitement autorisés par la politique.

## 5. Apprentissage, mémoire et skills

- [ ] La mémoire persistante est activée pour l'agent et rattachée à son seul
  runtime/profil.
- [ ] La politique indique les catégories mémorisables, interdites, la durée
  de conservation et le mécanisme de correction/suppression.
- [ ] Le premier échange inclut la proposition d'apprentissage et demande la
  confirmation pour données sensibles ou ambiguës.
- [ ] Un test prouve qu'un fait autorisé mémorisé dans une session est retrouvé
  dans une nouvelle session du même agent ; un second prouve qu'il n'apparaît
  pas dans un autre agent.
- [ ] Les procédures répétables sont dans un skill versionné, avec un test ou
  un scénario de validation. La mémoire ne remplace pas un mode opératoire.
- [ ] Une mémoire de projet est nécessaire seulement si plusieurs agents ont
  réellement besoin de la même connaissance ; son fournisseur, propriétaire,
  ACL, rétention et test d'isolation sont alors définis.

## 6. Capacités, permissions et isolation

- [ ] Chaque toolset est justifié par une action de la mission ; les toolsets
  terminal, navigateur, MCP, GitHub et écriture sont explicitement revus.
- [ ] La matrice ressources × droits × justification × test de refus est
  écrite dans le README ou une politique liée.
- [ ] Le conteneur est non privilégié, sans socket Docker ; CPU, mémoire,
  processus et redémarrage sont bornés selon le besoin.
- [ ] Les entrées sont en lecture seule ; les sorties utilisent un volume ou
  répertoire dédié ; `HERMES_WRITE_SAFE_ROOT` est minimal.
- [ ] Le réseau, les ports écoutés, les domaines/services externes et les
  identités de service sont documentés et minimisés.
- [ ] Secrets, données personnelles, dépôts, production et environnements de
  test sont séparés. Aucun secret de production n'est exposé par défaut.
- [ ] Les actions irréversibles et externes demandent une validation humaine,
  ou font l'objet d'une exception approuvée et testée.

## 7. Exploitation et planification

- [ ] Journaux, état de santé, alertes, tableaux de suivi et destinataire des
  alertes sont définis.
- [ ] Les tâches planifiées ont fuseau, limite de durée, idempotence, sortie,
  alerte et procédure de pause. Elles sont d'abord créées désactivées et
  exécutées une fois manuellement.
- [ ] La sauvegarde/restauration du runtime, la rétention et la purge sont
  définies et un test de restauration est planifié ou exécuté.
- [ ] Les mises à jour de l'image Hermes, des skills et des dépendances ont un
  responsable, une cadence et un retour arrière.
- [ ] La révocation/rotation OAuth et Slack ainsi que l'arrêt définitif de
  l'agent sont documentés.

## 8. Validation finale

- [ ] Les tests unitaires, de configuration et de démarrage du conteneur sont
  verts.
- [ ] Un test de bout en bout couvre le canal Slack, le fournisseur OpenAI,
  une capacité autorisée, un refus de capacité interdite et une sortie
  attendue.
- [ ] Une revue humaine confirme le périmètre, les permissions, le coût et la
  politique d'apprentissage.
- [ ] L'agent est démarré avec des tâches planifiées en pause ; l'activation
  intervient seulement après validation de ce premier run.

## Registre minimal de décision

Ajouter cette section au README de chaque agent, complétée plutôt que copiée à
vide :

| Champ | Décision |
| --- | --- |
| Propriétaire | |
| Mission / hors périmètre | |
| Slug | |
| Canal Slack et audience autorisée | |
| Modèle OpenAI / abonnement | |
| Mémoire : catégories et rétention | |
| Mémoire projet éventuelle | |
| Toolsets et accès d'écriture | |
| Montages, réseau et secrets | |
| Actions nécessitant validation | |
| Tâches planifiées et alertes | |
| Sauvegarde, restauration et arrêt | |
| Exceptions, risque et date de revue | |
