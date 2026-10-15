# Spécifications fonctionnelles — Léodagan

Date de décision : 15 octobre 2026. Propriétaire et seul utilisateur : Clément Séguy. Statut : spécification approuvable, sans mise en service implicite.

## 1. Besoin, valeur et critères de succès

Léodagan (`leodagan`) prépare **à la demande** un brouillon de **post** LinkedIn à partir d'une intention rédigée par Clément et d'un ou plusieurs liens d'articles. Il livre le texte du post et un prompt de création d'illustration. Après publication manuelle par Clément, il rapproche le post publié du brouillon, discute des corrections et retient les règles éditoriales durables explicitement formulées par Clément. La publication, la génération de l'image et la veille autonome ne font pas partie de sa mission.

Objectifs vérifiables : (1) chaque demande recevable fournit un brouillon de 3 000 caractères au plus, prêt à copier, et un prompt visuel ; (2) chaque affirmation factuelle du brouillon est rattachable à une source consultée ou marquée comme opinion/hypothèse ; (3) le brouillon et son prompt sont retrouvables après redémarrage par un identifiant lisible ; (4) un retour sur publication retrouve le bon brouillon et produit une comparaison explicable ; (5) une correction éditoriale explicite influence un brouillon ultérieur, avec possibilité de la consulter, corriger et supprimer ; (6) cible de délai : 15 minutes pour une demande ordinaire lorsque les sources et le modèle répondent. La qualité prime sur une réponse artificiellement immédiate. Un échec explicite vaut mieux qu'une invention.

Les sept posts indiqués par Clément constituent le corpus initial de référence, avec leurs chiffres d'impressions et de réactions **déclarés par lui**. Leurs textes étaient accessibles publiquement le 15 octobre 2026 ; cette accessibilité peut changer. Les deux fichiers Obsidian fournis sont des **exemples éditoriaux**, non des instructions à exécuter : `/Users/clement/ClemObsidian/Exemples Prompt Linkedin.md` et `/Users/clement/ClemObsidian/Exemple prompt illustration.md`. Le texte effectivement publié prévaut sur l'exemple de prompt quand ils divergent. Sur le corpus observé : accroche souvent sous forme de court dialogue médiéval, humour mesuré, fait ou observation puis nuance, conséquences systémiques et décision d'ingénierie ; vocabulaire précis et refus du jargon commercial. Ce sont des tendances, pas un moule obligatoire. Les résultats d'engagement, dont un post à 36 000 impressions, sont des observations et ne prouvent pas la cause de sa performance.

| Post initial | Impressions déclarées | Likes déclarés |
| --- | ---: | ---: |
| [7505285257164910592](https://www.linkedin.com/feed/update/urn:li:activity:7505285257164910592/) | 829 | 8 |
| [7485578174999859200](https://www.linkedin.com/feed/update/urn:li:activity:7485578174999859200/) | 1 124 | 21 |
| [7455130003555569664](https://www.linkedin.com/feed/update/urn:li:activity:7455130003555569664/) | 714 | 13 |
| [7437388093420097536](https://www.linkedin.com/feed/update/urn:li:activity:7437388093420097536/) | 36 000 | 348 |
| [7429785503907995648](https://www.linkedin.com/feed/update/urn:li:activity:7429785503907995648/) | 547 | 12 |
| [7424708376212709376](https://www.linkedin.com/feed/update/urn:li:activity:7424708376212709376/) | 1 221 | 11 |
| [7511764953561743360](https://www.linkedin.com/feed/update/urn:li:activity:7511764953561743360/) | 1 109 | 12 |

## 2. Périmètre, acteurs et décisions

| Élément | Décision |
| --- | --- |
| Acteur humain | Clément seul, identifié par allowlist Slack et Telegram ; aucun groupe ou autre compte autorisé. |
| Canaux | Dialogue complet dans `#agent-leodagan` sur Slack via l'application déjà dédiée à Léodagan ; dialogue privé avec un bot Telegram dédié à créer. Une demande peut commencer sur l'un et être reprise sur l'autre grâce à l'identifiant du brouillon. |
| Déclenchement | Message de Clément uniquement ; pas de veille ni de suivi planifié. |
| Modèle cible | `openai-codex` / `gpt-5.6-terra`, effort `medium`, via abonnement ChatGPT/Codex ; validation réelle de disponibilité et limites avant activation. |
| Sources | Les liens donnés et l'intention de Clément sont acceptés quel que soit le sujet. Pas d'obligation de deux sources ; toute incertitude ou affirmation non corroborée est signalée. |
| Sortie visuelle | Un prompt d'image, pas l'image. Direction artistique médiévale, bande dessinée semi-réaliste, palette froide, lisible en fil LinkedIn ; adaptation au sujet. |
| Apprentissage | Les **corrections explicites** et préférences clairement formulées peuvent devenir des règles durables automatiquement. Les inférences ambiguës ou les données sensibles exigent confirmation. |
| LinkedIn | Lecture seule si l'API officielle et ses permissions sont disponibles ; sinon lecture publique du lien si possible, puis demande à Clément du texte et des statistiques manquants. Aucun accès d'écriture. |
| Conservation | Brouillons, prompts, posts finaux, retours et instantanés de statistiques conservés jusqu'à suppression explicite. Sauvegarde et suppression sélective nécessaires. |
| Ancien Léodagan | Inventaire et validation humaine avant toute remise à zéro. Aucune suppression ou écrasement direct de l'ancien runtime. |

### Hors périmètre

Publication ou programmation LinkedIn ; réaction, commentaire ou message au nom de Clément ; génération/téléchargement d'image ; surveillance périodique des statistiques ; veille éditoriale planifiée ; modification automatique des guidelines ou de la politique éditoriale versionnée ; accès aux secrets ou au runtime d'un autre agent. Le terme « article LinkedIn » dans le besoin désigne ici un **post LinkedIn** limité à 3 000 caractères, pas un article long de la plateforme.

## 3. Parcours utilisateur

### P1 — Demander un brouillon

Clément écrit sur Slack ou Telegram son idée, son raisonnement/objectif/position et au moins un lien d'article. Léodagan confirme la prise en charge et attribue un identifiant sous forme de deux mots français ASCII reliés par un tiret, par exemple `cafe-geant` ; l'unicité est vérifiée. Si l'intention ou les liens sont insuffisants, il pose une question ciblée. Il consulte les articles, distingue faits, interprétations et opinion de Clément, construit un angle argumenté, vérifie le risque de contresens, rédige puis contrôle le nombre de caractères. Il prépare un prompt visuel cohérent avec l'angle. Le brouillon, le prompt, les sources, limites et date de consultation sont enregistrés **avant** l'annonce de réussite. La réponse fournit l'identifiant, le post intégral, son décompte, le prompt visuel et une brève note de vérification ou d'incertitude. Si une limite du canal coupe le message, des messages liés dans le même fil conservent l'intégralité et l'identifiant.

### P2 — Réviser et discuter

Clément demande une modification avec l'identifiant ou dans le fil du brouillon. Léodagan garde les versions antérieures, explique le changement demandé et fournit la nouvelle version contrôlée. Il peut discuter de ce qui fonctionne ou non. Une correction ponctuelle ne devient pas automatiquement une règle universelle ; une préférence formulée explicitement comme durable le peut et est annoncée avec une commande de consultation/correction/suppression.

### P3 — Apprendre du post publié

Clément transmet le lien du post final et ses explications, avec l'identifiant du brouillon si nécessaire. Léodagan résout la correspondance ; si plusieurs brouillons sont plausibles, il demande lequel comparer. Il récupère le texte final via API officielle en lecture seule si autorisée, sinon via la page publique ; en cas d'échec, il demande le texte. Il récupère impressions et réactions via API approuvée si disponible, sinon demande les chiffres. Il affiche la provenance et la date de chaque mesure, compare la version finale avec le brouillon retenu, identifie les changements de fond, structure, ton, nuances et visuel, puis soumet son analyse à la discussion. Les règles durables explicitement données sont mémorisées. Les métriques ne dictent pas seules une règle éditoriale.

### P4 — Retrouver, corriger, effacer

Clément peut demander le brouillon, sa version, le post final, les statistiques enregistrées, les décisions éditoriales apprises, puis corriger ou effacer un élément précis. La suppression indique les fichiers et enregistrements concernés ; les sauvegardes suivent une procédure de purge documentée. Les commandes de purge globale et de désinstallation sont distinctes du dialogue ordinaire.

## 4. Exigences fonctionnelles

Priorités : **P0** indispensable à la première mise en service ; **P1** nécessaire au cycle complet de retour ; **P2** amélioration contrôlée. Chaque preuve est détaillée dans la section recette et dans la matrice technique.

| ID | Prio. | Exigence et justification | Critère d'acceptation observable |
| --- | --- | --- | --- |
| F-001 | P0 | N'accepter que Clément dans le canal Slack dédié et son DM Telegram ; confidentialité. | Des messages de Clément déclenchent une réponse dans le bon fil ; autres utilisateurs, canaux et groupes sont refusés sans exécution. |
| F-002 | P0 | Déclencher uniquement sur demande ; respecter le nouveau périmètre. | Aucun job éditorial ou de statistiques ne s'exécute spontanément après démarrage ou redémarrage. |
| F-003 | P0 | Recevoir texte d'intention et au moins un lien ; éviter le faux cadrage. | Une demande complète est reconnue ; une demande incomplète entraîne une question ciblée sans brouillon inventé. |
| F-004 | P0 | Lire chaque article accessible, garder URL et date de consultation, identifier ce qui n'est pas vérifié ; traçabilité. | Le dossier du brouillon expose pour chaque lien état d'accès, éléments retenus, source et limites ; un lien inaccessible est signalé. |
| F-005 | P0 | Séparer le propos de Clément, les faits sourcés et l'analyse de Léodagan ; exactitude. | Une revue du brouillon peut relier les affirmations importantes à une source ou à une opinion explicite ; aucune citation ou chiffre non vu n'est présenté comme vérifié. |
| F-006 | P0 | Produire une voix proche du corpus, avec raisonnement critique, vocabulaire précis et nuance ; valeur éditoriale. | Sur une série de cinq sujets représentatifs, Clément juge au moins quatre brouillons « utilisables après révision » ; l'évaluation conserve ses motifs. |
| F-007 | P0 | Livrer un post copiable de 3 000 caractères maximum, hashtags et liens inclus ; contrainte LinkedIn. | Comptage déterministe conservateur sur le texte exact envoyé, espaces, retours ligne et emoji inclus ; au plus 3 000 unités UTF-16 et validation sur cas limites, sans prétendre disposer d'une API de prépublication LinkedIn. |
| F-008 | P0 | Livrer un seul prompt d'image adapté au sujet et au style visuel ; sortie demandée. | Le prompt décrit composition, sujet, palette, format horizontal 16:9, lisibilité, contraintes de texte et évite visage d'acteur ou imitation précise d'artiste ; aucune image n'est produite. |
| F-009 | P0 | Enregistrer durablement chaque version, prompt, liens et identifiant avant livraison ; reprise fiable. | Le même identifiant restitue le contenu après redémarrage ; une écriture échouée ne produit pas de faux accusé de succès. |
| F-010 | P0 | Permettre révision conversationnelle et historique ; collaboration. | Une demande de révision crée une nouvelle version sans écraser l'ancienne et répond dans le même fil ou avec l'identifiant. |
| F-011 | P1 | Récupérer le post final par lecture seule si possible, avec repli manuel ; boucle d'apprentissage. | API approuvée, page publique ou texte fourni par Clément sont distingués ; en cas d'échec d'accès, une demande de texte est envoyée et aucun faux contenu n'est enregistré. |
| F-012 | P1 | Rapprocher le post final du bon brouillon ; éviter l'apprentissage erroné. | Correspondance certaine via identifiant ; en cas d'ambiguïté, demande de choix avant comparaison. |
| F-013 | P1 | Comparer fond, plan, accroche, ton, omissions/ajouts, nuances et prompt visuel avec les explications de Clément ; apprentissage explicable. | Rapport de différences et décisions attribuées à la comparaison ou aux explications, sans prétendre deviner l'intention. |
| F-014 | P1 | Enregistrer impressions et réactions à la demande ou lors du retour, avec date et provenance ; suivi demandé. | Une mesure est horodatée, liée au post, distingue `REACTION` du nombre de « likes » fourni et ne déclenche aucun sondage planifié. |
| F-015 | P1 | Mémoriser automatiquement les corrections durables explicites ; améliorer les futurs brouillons. | Une règle confirmée par les mots de Clément est retrouvée dans une nouvelle session et appliquée ; une simple corrélation métrique ne crée pas de règle. |
| F-016 | P1 | Consulter, corriger, retirer apprentissages et données ; contrôle humain. | Clément peut voir la règle et son origine, la modifier ou la supprimer ; un nouveau brouillon ne la reprend plus après suppression. |
| F-017 | P0 | Gérer erreurs d'accès, quota, authentification et livraison ; fiabilité. | Erreur nommée, état enregistré, reprise manuelle ou nouvel essai borné selon cause ; pas de bascule fournisseur silencieuse ni de brouillon déclaré livré si la livraison échoue. |
| F-018 | P0 | Interdire publication et actions LinkedIn en écriture ; maîtrise du risque. | Aucun token avec scope d'écriture, aucun outil de publication, test de refus vérifié. |
| F-019 | P0 | Conserver les données jusqu'à suppression explicite et permettre sauvegarde/restauration ; continuité. | Après restauration sur un runtime privé, un brouillon et une règle mémoire sont retrouvés ; désinstallation préserve données/secrets. |
| F-020 | P0 | Inventorier l'ancien runtime et ses livrables puis demander validation avant remise à zéro ; éviter la perte. | Rapport avec chemins et tailles présenté ; aucune suppression ou migration destructive sans accord explicite sur cet inventaire. |
| F-021 | P0 | Présenter état et journal d'activité sans exposer secrets ni texte privé hors canaux autorisés ; exploitation. | Un opérateur peut voir identifiant, étape, erreurs et horodatage ; les journaux ne contiennent pas de token ou d'articles complets par défaut. |
| F-022 | P1 | Associer conversation et brouillon entre Slack et Telegram via l'identifiant ; continuité multicanal. | Un brouillon créé dans un canal est retrouvé dans l'autre par Clément, sans fusion automatique hasardeuse de deux fils. |

## 5. Données, confidentialité et durée

| Donnée | Provenance / accès | Conservation et suppression |
| --- | --- | --- |
| Intention et commentaires de Clément | Messages Slack/Telegram autorisés | Historique Hermes et dossier métier privés ; jusqu'à suppression explicite ; export et purge sélective. |
| Articles sources | URLs données ; pages publiques consultées en lecture | URL, extrait utile, date, résultat d'accès et provenance liés au brouillon ; pas d'aspiration générale du site. |
| Corpus de sept posts | Liens de Clément ; texte public observé ; chiffres fournis par Clément | Références initiales et fiches de style privées ; texte réimportable si accès public disparaît ; jusqu'à suppression. |
| Brouillons, prompts et versions | Léodagan | Identifiant, état, version, horodatage et contenu dans stockage propre à Léodagan ; jusqu'à suppression. |
| Post final, retours et statistiques | Lecture officielle/publique ou saisie de Clément | Instantanés datés avec provenance ; correction/suppression à la demande ; jusqu'à suppression. |
| Préférences durables | Corrections explicites de Clément | Mémoire par agent, consultable et révisable ; pas de secrets, données personnelles inutiles ou hypothèses non validées. |
| Tokens OAuth, Slack, Telegram, éventuel LinkedIn | Provisionnement privé par Clément | Secrets du runtime seulement, sauvegarde chiffrée, rotation/révocation documentées ; jamais dans Git ou messages. |

Le premier échange de Léodagan propose l'apprentissage et explique comment consulter/corriger/supprimer. La décision de Clément dans ce cadrage autorise déjà la mémorisation automatique de ses **corrections explicites** ; toute donnée sensible ou ambiguë requiert sa confirmation spécifique.

## 6. Cas limites, erreurs et intervention humaine

- Lien d'article inaccessible, payant ou supprimé : tenter uniquement une lecture publique autorisée ; demander le texte/extrait à Clément ; ne pas contourner la restriction. Si le matériau suffit malgré un lien manquant, livrer avec limites visibles, sinon suspendre la rédaction.
- Sources contradictoires ou thèse non étayée : expliciter la contradiction ; demander si nécessaire la position de Clément ; aucune règle automatique des « deux sources ».
- Texte d'entrée potentiellement confidentiel : ne pas le republier vers un connecteur tiers ; demander confirmation avant une extraction externe non prévue. Le modèle et les canaux configurés restent les traitements prévus.
- Message fragmenté sur Slack/Telegram : garder le même identifiant et une version canonique consultable. Une livraison partielle est marquée comme telle et reprise sans créer un deuxième brouillon.
- Post final non lisible ou API refusée : demander texte et chiffres à Clément. La lecture publique est opportuniste et ne remplace pas le consentement OAuth.
- Échec d'écriture, disque plein, 429 ou OAuth expiré : état explicite, aucun succès fictif ; nouvelle tentative bornée sur incident transitoire, sinon alerte dans le canal de la demande et action humaine décrite. Ne jamais utiliser une clé API en repli implicite.
- Réponses concurrentes ou répétées : idempotence par message et identifiant ; deux demandes distinctes reçoivent deux identifiants ; pas d'écrasement.
- Suppression : action de Clément seulement, ciblée et vérifiable. Une restauration de sauvegarde peut réintroduire une donnée supprimée ; le runbook impose une purge cohérente des sauvegardes concernées ou une restriction de restauration.

## 7. Exigences non fonctionnelles utilisateur

- **Disponibilité** : service local utilisable lorsque Docker Desktop, la connexion réseau, les canaux et Codex sont disponibles ; panne signalée, pas de promesse de disponibilité cloud.
- **Délai** : cible de 15 minutes pour un dossier ordinaire ; réponse de progression si la consultation des sources retarde la livraison ; attente explicite en cas de blocage.
- **Confidentialité** : un seul utilisateur, runtime propre, canaux autorisés, secrets non affichés, aucun accès LinkedIn en écriture ni partage avec Père Blaise.
- **Lisibilité/accessibilité** : texte français en clair, paragraphes courts, post intégral copiable, alternatives descriptives textuelles au prompt d'image ; statut compréhensible sans ouvrir un journal technique.
- **Coût/usage** : abonnement ChatGPT/Codex seulement ; pas d'API payante ni de service mémoire externe sans décision documentée ; limite de concurrence à une rédaction lourde à la fois par défaut, revue après mesures.
- **Exploitation** : sauvegarde et restauration vérifiées, état de santé visible, procédure de réauthentification et d'arrêt, mises à jour réversibles.

## 8. Recette de bout en bout

| Scénario | Étapes et résultat attendu | Exigences |
| --- | --- | --- |
| R1 Brouillon Slack | Message de Clément avec idée + deux liens ; lecture, post ≤ 3 000 caractères, prompt et sources ; restitution dans le fil et stockage. | F-001 à F-009, F-021 |
| R2 Telegram et révision | Même parcours avec un lien ; demander une révision ; retrouver les deux versions depuis Slack par identifiant. | F-001, F-003 à F-010, F-022 |
| R3 Retour publié | Fournir lien final, corrections explicites et chiffres ; retrouver le brouillon, comparer, mémoriser la règle, créer un nouveau brouillon qui l'applique. | F-011 à F-016 |
| R4 Échec connecteur | Simuler refus API LinkedIn et échec de lecture publique ; Léodagan demande texte/chiffres, conserve l'état et n'invente rien. | F-011, F-014, F-017 |
| R5 Refus d'accès | Utilisateur Slack/Telegram non autorisé, autre canal, tentative de publication LinkedIn ; aucune action métier, refus observé. | F-001, F-018 |
| R6 Redémarrage | Créer un brouillon, redémarrer le conteneur, retrouver versions et mémoire, aucun cron éditorial déclenché. | F-002, F-009, F-015, F-019 |
| R7 Restauration | Sauvegarde chiffrée, arrêt, restauration isolée, contrôle d'intégrité et relecture brouillon/règle ; aucun secret montré. | F-019, F-021 |
| R8 Panne de livraison | Couper un canal après enregistrement ; état « enregistré, livraison échouée », reprise sur demande avec le même identifiant. | F-009, F-017 |

## 9. Décisions tranchées et hypothèses résiduelles

Les choix du tableau en section 2 proviennent des réponses de Clément. Le lien court `https://lnkd.in/p/e5sCxTwc` et les sept liens initiaux étaient consultables dans un navigateur public le 15 octobre 2026 ; cette observation n'accorde aucun accès futur garanti. La lecture API LinkedIn personnelle est conditionnelle à l'approbation effective des permissions de l'application ; le repli manuel est accepté. L'application Slack existante est dédiée à Léodagan ; ses scopes et sa configuration doivent être audités lors du développement. Le bot Telegram reste à créer. La cible de 15 minutes est un objectif de recette, non une garantie en cas de source ou fournisseur indisponible. Les identifiants réels Slack/Telegram, les quotas de l'abonnement et la possibilité effective de l'API LinkedIn sont des paramètres de mise en service à vérifier sans réinterpréter la mission.
