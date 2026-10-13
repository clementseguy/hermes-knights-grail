# Convention d'exploitation des agents Hermes

Ce dépôt est le référentiel de conception et d'exploitation des agents Hermes
de l'équipe. Cette convention s'applique à tout nouvel agent et à toute
évolution substantielle d'un agent existant. Elle complète la documentation
Hermes : elle ne remplace pas une vérification de la version réellement
installée.

## Décision par défaut

- Un agent est un produit identifiable, avec une mission bornée, un propriétaire
  humain, un dépôt de configuration versionné et un runtime isolé.
- Le LLM par défaut est **OpenAI via l'abonnement ChatGPT/Codex**, configuré
  dans Hermes avec `provider: openai-codex`. Une clé API OpenAI n'est ni une
  condition de création ni une solution de repli implicite. Une exception
  (API, autre fournisseur ou modèle) est une décision documentée dans le
  `README.md` de l'agent avec son motif, son coût et son propriétaire.
- Le canal de discussion standard est **Slack**. Tout agent destiné à dialoguer
  avec des personnes possède un canal Slack, sauf exception explicitement
  justifiée (agent purement interne, canal réglementaire, interface locale,
  etc.).
- Un agent dispose de sa **mémoire persistante propre**, activée par défaut.
  Les sessions, le `HERMES_HOME`, les skills et les secrets ne sont jamais
  partagés entre agents.
- L'exécution est autonome à l'intérieur d'un conteneur isolé et borné. Les
  privilèges, montages et accès externes partent de zéro et ne sont ajoutés que
  pour une capacité nommée et vérifiable.

La création ne commence pas par un `compose.yaml`. Elle commence par la
checklist [docs/agent-creation-checklist.md](docs/agent-creation-checklist.md).
Les décisions qu'elle demande doivent être visibles dans le `README.md` de
l'agent, sa configuration versionnée et, le cas échéant, sa politique/skill.

## Architecture répétable

Chaque agent suit la même séparation :

1. **Source versionnée** : `README.md`, `compose.yaml`, `config/`,
   `prompts/`, `skills/<slug>/`, scripts et tests.
2. **Runtime privé** : mémoire, sessions, base d'état, journaux, jetons OAuth,
   clés Slack et sorties temporaires. Il n'est jamais commité ni copié entre
   agents.
3. **Entrées et sorties explicites** : seuls les répertoires nécessaires sont
   montés ; les entrées sont en lecture seule par défaut ; les livrables ont un
   répertoire de sortie dédié.
4. **Contrat de mission** : la politique indique les actions autonomes, les
   actions qui exigent une validation humaine et celles qui sont interdites.

Un blueprint complet serait prématuré : les trois agents existants ont des
surfaces très différentes. En revanche, cette structure, la checklist et les
conventions de nommage sont obligatoires. Un template de fichiers ne sera créé
qu'après plusieurs créations ayant démontré des champs identiques et stables.

## Déploiements locaux : périmètre et volume

Un déploiement copie uniquement la source versionnée de l'agent vers son
répertoire de déploiement dédié. Il ne copie jamais une racine de volume, le
répertoire personnel, une arborescence système ou un dépôt voisin.

Avant toute commande récursive (`rsync`, `cp -R`, `ditto`, extraction
d'archive) :

1. Résoudre et afficher les chemins physiques de source et de destination.
2. Refuser une source égale à `/`, `$HOME`, `/Users`, `/System`, `/Library`,
   `/Applications`, `/Volumes`, ou à l'un de leurs ancêtres.
3. Vérifier que la source est sous `~/workspace/my-hermes/<slug>`, porte le
   slug attendu et contient les fichiers de projet attendus.
4. Vérifier que la destination est sous le répertoire de déploiement autorisé
   et porte exactement le même slug. Une destination active n'est jamais
   écrasée directement.
5. Produire et relire un aperçu (`rsync --dry-run --stats` ou équivalent) ;
   arrêter si son volume dépasse le budget déclaré pour l'agent.
6. Ne jamais utiliser `--copy-links` / `-L` et ne jamais suivre de lien
   symbolique vers l'hôte pendant la copie.
7. Déployer d'abord dans un répertoire de staging, valider le démarrage, puis
   basculer vers la version validée. Les services existants restent arrêtés
   jusqu'à cette validation.
8. Toute synchronisation avec `--delete` et toute suppression d'un ancien
   déploiement exigent une validation humaine explicite après affichage des
   chemins concernés et de leur taille.

Les scripts de déploiement utilisent `set -euo pipefail` et échouent si leurs
variables de source ou destination sont absentes, vides ou hors périmètre.
Un déploiement anormalement volumineux est un incident : arrêter immédiatement
la copie, ne pas tenter de la corriger en place, puis mesurer et supprimer le
répertoire fautif après arrêt du service concerné.

## Identité et nommage

Le nom fonctionnel peut être un personnage (`Père Blaise`, `Léodagan`,
`Yvain`), mais toutes les identités techniques utilisent un unique `slug`
kebab-case ASCII, par exemple `pere-blaise`.

| Élément | Convention | Exemple |
| --- | --- | --- |
| Dossier source | `<slug>/` | `pere-blaise/` |
| Service Compose | `<slug>` | `leodagan` |
| Projet Compose | `hermes-<slug>` | `hermes-yvain` |
| Conteneur | `hermes-<slug>` | `hermes-leodagan` |
| Volume nommé | `hermes-<slug>-data` | `hermes-yvain-data` |
| Profil / runtime Hermes | `hermes-<slug>` ou runtime dédié documenté | `hermes-yvain` |
| Canal Slack | `#agent-<slug>` | `#agent-yvain` |
| Application Slack | `Hermes — <Nom>` | `Hermes — Yvain` |
| Répertoire de livrables | `<slug>/outbox/` ou un nom métier justifié | `yvain/reports/` |

Un slug est réservé une fois choisi. Ne pas créer de variantes (`yvain2`,
`hermes_yvain`, `hermes-yvain-runtime`) pour le même agent. Un remplacement
crée un nouveau slug, conserve l'ancien runtime en lecture seule le temps de la
rétention, et documente la migration.

## Modèle, abonnement et secrets

Chaque agent configure explicitement le fournisseur et le modèle de travail :

```yaml
model:
  provider: openai-codex
  default: <modele-approuve>
```

L'authentification Codex/ChatGPT est réalisée dans le runtime privé de
l'agent. Le jeton OAuth est un secret : pas de commit, pas d'image Docker, pas
de journal, pas de variable affichée, pas de volume partagé avec un autre
agent. La fiche d'exploitation indique qui peut réauthentifier l'agent et
comment vérifier le renouvellement.

Avant la mise en service, confirmer que l'abonnement et le modèle choisis
autorisent le volume et l'automatisation visés. Les limites, indisponibilités
ou changements d'offre ne doivent pas basculer silencieusement vers une API ou
un autre fournisseur ; l'agent se met en attente et signale le blocage.

## Communication Slack

Slack est le canal humain standard ; un fil Slack représente une conversation
partagée. L'agent doit être invité dans `#agent-<slug>` et répondre seulement
aux personnes/canaux autorisés. Les messages directs ne sont activés que si
cela est un besoin explicite.

Pour chaque agent exposé à Slack, documenter :

- le workspace, le canal et les groupes/utilisateurs autorisés ;
- l'application Slack dédiée, ses scopes minimaux, son token et l'emplacement
  privé de ce token ;
- la connectivité entrante nécessaire aux événements Slack (URL publique,
  tunnel ou relais), sa protection et son test de bout en bout ;
- les règles de mention, de thread, de notifications et de transfert à un
  humain ;
- la conduite en cas d'échec d'authentification ou de livraison.

Un agent ne publie pas dans un autre canal, n'envoie pas de DM et n'appelle pas
un service externe au nom d'une personne sans que son contrat le permette.

## Mémoire et apprentissage

La mémoire est l'apprentissage de faits ; les skills sont l'apprentissage de
procédures. Les deux sont nécessaires mais ne se substituent pas.

Par défaut, activer la mémoire Hermes persistante pour l'agent. Sa politique
doit dire ce qu'il mémorise : préférences stables, contexte métier durable,
décisions confirmées, conventions et erreurs récurrentes. Elle doit aussi dire
ce qu'il ne mémorise pas : secrets, jetons, données personnelles inutiles,
contenu sensible non approuvé, informations temporaires ou non vérifiées.

Au démarrage d'une relation ou d'un nouveau projet, l'agent propose
explicitement l'apprentissage : « Je peux retenir les préférences et décisions
durables de cet agent/projet ; confirmez ce que je dois conserver. » Il indique
comment consulter, corriger et supprimer ces apprentissages. Pour une donnée
sensible ou ambiguë, il attend toujours cette confirmation ; il ne la déduit
pas d'une conversation.

Une mémoire est **par agent**. Une mémoire de projet (par exemple NexTarget)
est exceptionnelle : elle passe par un fournisseur de mémoire externe ou une
base de connaissances conçue pour ce projet, avec propriétaire, contrôle
d'accès, rétention, procédure d'indexation et test de séparation. Ne jamais la
simuler par un même `HERMES_HOME`, une même base SQLite ou un même volume Docker
monté dans plusieurs agents.

Toute procédure répétable appartient à un skill versionné dans
`<slug>/skills/<slug>/`. Une amélioration observée plusieurs fois est proposée
au propriétaire comme évolution de skill, revue puis testée ; elle n'est pas
seulement enfouie dans la mémoire. Les skills et les changements de configuration
qui modifient le prompt ou les outils sont appliqués à une nouvelle session ou
après redémarrage contrôlé, afin de préserver la cohérence des conversations en
cours.

## Permissions et isolation

La matrice d'accès fait partie du contrat avant toute implémentation. Pour
chaque ressource, préciser : lecture, écriture, exécution, réseau, identité
utilisée, justification et test de refus.

Règles par défaut :

- conteneur non privilégié, sans socket Docker, sans montage de répertoire
  personnel ou de dépôt entier ;
- réseau réduit au besoin ; aucune écoute publique sans authentification ;
- volumes par agent et entrées montées en lecture seule ;
- `HERMES_WRITE_SAFE_ROOT` réduit aux seules sorties prévues ;
- allowlist Hermes/gateway et allowlist Slack activées ; jamais `allow_all`
  par commodité ;
- secrets injectés depuis un emplacement privé, à permissions restrictives,
  et jamais depuis un fichier versionné ;
- actions irréversibles, publications, dépenses, changements d'accès et
  écritures dans un système tiers soumis à validation humaine, sauf exception
  écrite et testée.

Si un agent doit être plus contraint, créer une politique dédiée et réduire les
montages, toolsets, permissions réseau et actions autorisées ; ne pas compter
sur une instruction en langage naturel comme contrôle de sécurité.

## Toolsets, skills, tâches planifiées et observation

Les toolsets sont un budget de capacité et de contexte : n'activer que ceux
qui servent la mission. La configuration liste explicitement les toolsets par
surface (Slack, API, desktop, cron) et justifie terminal, navigateur, MCP,
GitHub ou tout outil d'écriture. Tester qu'un outil non autorisé est absent ou
refusé.

Chaque tâche planifiée possède une identité, un propriétaire, une fréquence,
un fuseau horaire, une limite de durée/coût, une règle d'idempotence, une sortie
et une alerte d'échec. Elle est créée désactivée, exécutée une fois à la main,
puis activée après validation.

Avant mise en production, définir : emplacement des journaux, indicateur de
santé, sauvegarde et restauration du runtime, rétention des livrables et
journaux, mise à jour de l'image Hermes, procédure de rotation/révocation des
secrets et procédure d'arrêt. Un agent sans ces éléments n'est pas validable.

## Revue de création et exceptions

La checklist est une porte de passage : aucun agent n'est mis en service tant
que les rubriques identité, mission, modèle, Slack, mémoire, permissions,
skills, opérations et tests ne sont pas cochées avec une preuve.

Une exception doit être courte, datée, approuvée par le propriétaire, indiquer
le risque accepté, les compensations et une date de révision. Elle vit dans le
README de l'agent ; elle ne devient pas une nouvelle convention implicite.
