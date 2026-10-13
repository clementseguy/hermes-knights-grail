### Cadrage — Agentisation du développement Nextarget

Version 1.0 — 10 octobre 2026

Objectif : mettre en place une équipe d'agents de développement orchestrée par Hermes Agent, exécutée sur macOS, capable de prendre en charge un sprint Nextarget depuis sa planification jusqu'à sa livraison technique, avec recette humaine en fin de sprint.

Ce document constitue la base de reprise de la discussion sur le poste de travail, avec accès à l'infrastructure Hermes existante.

### 1\. Environnement et contraintes

| Dimension           | Choix                                                            |
| ------------------- | ---------------------------------------------------------------- |
| Infrastructure      | Hermes Agent sur macOS                                           |
| Modèles disponibles | API Claude, OpenAI, Gemini                                       |
| Backend Nextarget   | Python                                                           |
| Application mobile  | Flutter                                                          |
| Gestion de code     | GitHub, potentiellement plusieurs repos                          |
| Gestion produit     | GitHub Issues / Projects                                         |
| CI/CD               | GitHub Actions                                                   |
| Prompts existants   | Développement, review, affinement des user stories               |
| Autonomie           | Exécution autonome avec validations humaines aux étapes définies |

Principe : réutiliser au maximum les fonctionnalités natives de Hermes et les prompts existants. Ne développer des composants supplémentaires que lorsqu'une lacune est démontrée.

### 2\. Organisation du processus

Le développement est organisé en sprints.

1\. Sprint Planning

PM Agent + Humain

Affinement, sélection, dépendances, priorisation

2\. Validation du sprint

Humain

Approbation du périmètre et de l'ordre de traitement

3\. Exécution séquentielle des stories

Story N

Routage → Architecture si nécessaire → Développement → QA → Review → CI → Intégration

Story suivante éligible jusqu'à la fin du sprint

4\. Recette globale

Humain

Validation ou refus du résultat du sprint

5\. Clôture et préparation du sprint suivant

Bilan, anomalies, stories non terminées, backlog mis à jour

Il n'y a pas de développements parallèles. Une seule story est activement développée à la fois.

### Gestion des blocages

Lorsqu'une story est bloquée, l'orchestrateur documente le blocage et passe à la prochaine story éligible, en respectant les dépendances.

Les stories bloquées ne sont pas considérées comme livrées. Leur reprise ou leur report doit être tracé.

### Recette

La recette est effectuée globalement à la fin du sprint, et non individuellement après chaque story.

Les anomalies découvertes sont transformées en GitHub Issues de type Bug et ajoutées au backlog du sprint suivant. Il n'y a pas de boucle automatique de correction après la recette humaine.

### 3\. Organisation de l'équipe d'agents

| Agent                   | Responsabilité                                               |
| ----------------------- | ------------------------------------------------------------ |
| Orchestrateur de sprint | États, ordonnancement, transitions, blocages, reprise        |
| Product Manager         | Backlog, affinement, sprint planning, critères d'acceptation |
| Architecte              | Analyse technique, arbitrages, risques, contrats d'interface |
| Routeur                 | Choix automatique du développeur                             |
| Développeur simple      | Implémentation courante avec Luna Medium                     |
| Développeur complexe    | Implémentation complexe ou risquée avec Terra Medium         |
| QA / Testeur            | Vérifications fonctionnelles et techniques                   |
| Code Reviewer           | Revue indépendante du code et de la conformité               |
| Intégration             | Git, PR, GitHub Actions, consolidation du sprint             |

Ces rôles sont logiques : ils ne nécessitent pas forcément neuf processus Hermes permanents. Certains peuvent être implémentés comme profils spécialisés invoqués à la demande.

### 4\. Stratégie des deux développeurs

Cible 80 %

### Luna Medium

Développeur simple

Bugs localisés, évolutions simples à moyennes, modifications limitées et refactorings locaux nécessaires à la story.

Cible 20 %

### Terra Medium

Développeur complexe

Évolutions complexes, migrations, changements de contrats d'interface, modifications à risque élevé et dépendances techniques importantes.

Le ratio 80/20 est une cible économique indicative, jamais un quota imposé.

### Routage

Le routeur classe chaque story selon sa complexité, ses risques, les composants concernés, les dépendances et les changements d'interfaces.

L'architecte intervient en cas d'incertitude ou de décision sensible.

Une modification multi-repo n'implique pas automatiquement Terra. Inversement, une modification dans un seul repo peut nécessiter Terra si elle est risquée.

### Escalade

* Luna escalade immédiatement vers Terra lorsqu'il découvre une complexité hors de son périmètre.

* En cas d'échec de tests ou de review, Luna dispose d'un nombre limité de tentatives de correction.

* La valeur initiale proposée est de deux cycles, à confirmer expérimentalement.

* Le transfert vers Terra doit préserver le contexte, le code produit, les décisions, les erreurs et les résultats des tests.

* Terra ne redélègue pas la même tentative à Luna.

Objectif d'optimisation : réduire le coût par story livrée, sans dégrader la qualité ni allonger excessivement les sprints.

### 5\. Politique de refactoring

| Type                                                                                 | Règle                                            |
| ------------------------------------------------------------------------------------ | ------------------------------------------------ |
| Refactoring cyclique : dette technique, simplification générale, qualité ou sécurité | Exclu du processus automatisé, géré manuellement |
| Refactoring ciblé nécessaire à une user story                                        | Inclus dans le développement de la story         |
| Refactoring local maîtrisé                                                           | Peut être effectué par Luna                      |
| Refactoring structurel risqué induit par une story                                   | Orienté vers Terra                               |

Les agents ne doivent pas entreprendre spontanément de refactoring sans lien direct avec la story.

### 6\. Gestion du backlog

GitHub Issues / Projects reste la source de vérité produit.

Trois niveaux sont distingués :

* Product Backlog : ensemble des besoins, bugs, évolutions et stories à affiner.

* Sprint Backlog : sélection validée des stories à traiter pendant le sprint, avec ordre et dépendances.

* Execution Queue : liste dynamique des stories actuellement éligibles à l'exécution.

Une story doit disposer d'un état explicite, de critères d'acceptation et de dépendances identifiées.

Les statuts envisagés incluent `Draft`, `Refined`, `Ready`, `In Sprint`, `In Dev`, `In Review`, `Integrated`, `Awaiting UAT`, `Accepted`, ainsi que `Blocked` et `Rejected`.

Ces statuts constituent un modèle cible, pas encore un schéma définitivement implémenté.

### 7\. Contrats entre agents

Chaque étape devra être définie par un contrat explicite :

| Élément            | Exigence                                                       |
| ------------------ | -------------------------------------------------------------- |
| Entrées            | Story, contexte, dépendances, artefacts précédents             |
| Sorties            | Livrables structurés et vérifiables                            |
| Critères de succès | Conditions de passage à l'étape suivante                       |
| Critères d'échec   | Erreurs, blocages, non-conformités                             |
| Retours arrière    | Responsable de la correction et limite de tentatives           |
| Traçabilité        | Historique des décisions, modèles utilisés, tests et résultats |

Les prompts existants seront conservés autant que possible et adaptés à ces contrats.

Les formats exacts (Markdown, JSON, fichiers de travail, commentaires GitHub) restent à définir.

### 8\. Architecture technique envisagée

Trois projets ont été identifiés comme candidats à examiner :

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

Socle principal envisagé : runtime, délégation, Kanban et workers.

[lingjiuu/hermes-dynamic-workflows](https://github.com/lingjiuu/hermes-dynamic-workflows)

Candidat pour l'orchestration explicite des étapes.

[tonbistudio/hermes-multi-agent-workflow](https://github.com/tonbistudio/hermes-multi-agent-workflow)

Référence potentielle de conception d'un pipeline multi-agents.

Aucun framework n'est encore définitivement sélectionné. Il faudra auditer les versions installées, les dépôts, le code et les capacités réellement disponibles sur le poste.

L'architecture préférée à ce stade est Hermes natif, complété uniquement par les composants d'orchestration nécessaires.

### 9\. Points techniques à vérifier sur le poste de travail

* Installation, version et configuration actuelle de Hermes Agent.

* Capacités réelles du Kanban : persistance, dépendances, workers, blocages et reprise.

* Support des profils d'agents et configuration exacte de Luna Medium / Terra Medium.

* Possibilité d'orchestrer les étapes avec validation et retours arrière.

* Intégration GitHub Issues / Projects et GitHub Actions.

* Isolation Git par story et stratégie d'intégration par sprint.

* Reprise après crash, redémarrage de Hermes ou mise en veille du Mac.

* Observabilité, suivi des coûts et prévention des boucles de correction infinies.

### 10\. Critères de succès du projet

Le premier POC devra démontrer qu'un sprint contenant plusieurs stories peut être exécuté avec :

* Un sprint backlog validé par l'humain.

* Une sélection séquentielle des stories éligibles.

* Un routage automatique Luna / Terra.

* Une escalade avec transfert de contexte.

* Des contrôles QA, review et CI.

* Un traitement fiable des stories bloquées.

* Une reprise après interruption.

* Une livraison consolidée pour recette humaine.

* Un bilan exploitable et une mise à jour du backlog.

Les indicateurs à suivre seront notamment le coût par story intégrée, la durée de traitement, le taux d'escalade, les cycles de correction, les échecs de CI et les anomalies détectées en recette.

### 11\. Consigne pour reprendre la discussion sur le poste de travail

Tu peux copier le texte suivant dans une nouvelle conversation avec accès à ton infrastructure Hermes :

Je travaille sur Nextarget, une application avec un backend Python, une application Flutter, GitHub Issues / Projects et GitHub Actions.

Je souhaite mettre en place une équipe d'agents de développement orchestrée par Hermes Agent sur mon Mac.

**Le cadrage fonctionnel est établi :**

- Sprint planning avec un agent PM, puis validation humaine du sprint.
- Exécution autonome et séquentielle des user stories, en respectant priorités et dépendances.
- Deux développeurs spécialisés, jamais exécutés en parallèle : Luna Medium pour les tâches simples à moyennes (cible 80 %) et Terra Medium pour les tâches complexes ou risquées (cible 20 %).
- Routage automatique avec arbitrage de l'architecte en cas d'incertitude.
- Escalade immédiate Luna vers Terra lorsque la complexité dépasse le périmètre de Luna, avec transmission structurée du contexte.
- Corrections limitées après échec de tests ou de review, puis escalade.
- QA, review indépendante et GitHub Actions avant intégration.
- En cas de blocage, passage à la prochaine story éligible.
- Recette humaine globale à la fin du sprint.
- Bugs détectés en recette ajoutés au backlog du sprint suivant.
- Refactoring cyclique exclu ; refactoring ciblé nécessaire à une story autorisé dans cette story.
- GitHub Projects est la source de vérité produit.
- Les prompts existants de développement, review et affinement doivent être réutilisés.

**Ta mission :**

1. Examiner l'infrastructure Hermes réellement installée sur mon Mac.
2. Auditer les capacités natives de Hermes et les frameworks GitHub pertinents, notamment NousResearch/hermes-agent, hermes-dynamic-workflows et hermes-multi-agent-workflow.
3. Distinguer les fonctionnalités disponibles de celles qui nécessiteraient du développement.
4. Recommander une architecture minimale, fiable et maintenable.
5. Définir les contrats entre agents, les états du workflow et les mécanismes de reprise.
6. Proposer un POC sur un sprint Nextarget réduit.

Ne commence pas par développer un orchestrateur maison. Privilégie les fonctionnalités existantes et vérifie-les dans le code et la documentation avant de conclure.

Commence par l'audit technique de l'environnement Hermes et présente-moi les résultats et les choix d'architecture avant toute modification de l'installation.

Le cadrage métier est terminé. Les prochaines étapes sont l'audit technique, la sélection de l'architecture et la formalisation des contrats d'interface. L'enjeu est maintenant de construire le système le plus simple qui respecte ce processus, et non de multiplier les agents ou les frameworks.

