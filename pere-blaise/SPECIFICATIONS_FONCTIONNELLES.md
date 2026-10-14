# Spécifications fonctionnelles — Père-Blaise

Version de cadrage : 14 octobre 2026. Statut : décisions structurantes prises avec le propriétaire ; aucune mise en service autorisée par ce document.

## 1. Objet, valeur et mesure

Père-Blaise aide des personnes explicitement autorisées à classer les fichiers réguliers de `Downloads` dans les répertoires **existants** de `Documents`, sans jamais réorganiser les documents déjà classés. Il cherche aussi un fichier par son nom sous `Documents/**` et l'envoie, sur demande, en pièce jointe Telegram ou Slack. Il apprend des classements manuels des fichiers qu'il avait placés dans `Documents/a_trier`.

La réussite d'une recette exige : zéro déplacement après `analyse` ou `détaille` ; 100 % des fichiers d'un `range` réussi présents à leur destination, absents de `Downloads` et sauvegardés hors `Documents` ; 100 % des échecs injectés sans perte de fichier, avec retour automatique à l'état source ou blocage explicite et procédure de reprise ; aucun document préexistant modifié ou supprimé ; aucune commande acceptée hors allowlist. Les tests doivent couvrir deux canaux, le dimanche à 17 h Europe/Paris et un redémarrage.

## 2. Périmètre, exclusions et acteurs

- **Propriétaire/exploitant** : Clément ; il configure les chemins, les personnes habilitées, les secrets, les sauvegardes techniques et les mises à jour.
- **Personnes autorisées** : plusieurs personnes inscrites individuellement dans les allowlists Telegram et Slack. Elles ont toutes accès aux cinq commandes. Un plan reste personnel à son auteur ; une autre personne ne peut ni le détailler ni l'exécuter.
- **Agent de classement** : propose des cibles à partir des seuls noms et métadonnées autorisés ; il n'accède pas aux octets des fichiers.
- **Composant local isolé** : seul détenteur des montages de fichiers ; il peut lire des octets pour empreinte, copie de backup et envoi explicitement demandé. Il n'envoie jamais ces octets au modèle.

Les racines métier sont `Downloads` et `Documents`. Une troisième racine, privée et configurable, est réservée aux **backups** du composant local. Le runtime, les journaux et les secrets privés sont des ressources techniques isolées, sans accès à d'autres documents personnels. Aucun autre dossier personnel, dépôt, volume voisin ou fichier de l'hôte n'est monté ou parcouru.

Hors périmètre : lecture sémantique du contenu, OCR, recherche plein texte, création de sous-répertoires dans `Documents` sauf la création initiale de `a_trier`, réorganisation de `Documents`, suppression ou mise en corbeille d'un fichier préexistant, déplacement spontané, DM Slack, groupes Telegram, apprentissage d'un fichier non suivi, purge automatique des backups.

## 3. Canaux et règles communes

Telegram utilise des conversations privées avec les comptes autorisés. Slack utilise uniquement le canal privé `#agent-pere-blaise`, avec réponse dans le fil de la commande ; aucune pièce jointe n'est publiée dans un autre canal. L'app Slack et le bot Telegram déjà créés sont **réutilisés** après audit de leurs droits, de leurs tokens, de leur appartenance aux canaux et de l'absence d'un second processus actif sur le même bot. Il n'y a aucune raison de les supprimer par défaut. Les identifiants exacts restent dans la configuration privée fournie lors de l'installation, pas dans Git.

L'identité d'auteur est `(plateforme, identifiant immuable)` ; une correspondance entre deux comptes d'une même personne n'est admise que si l'exploitant la vérifie et l'enregistre. Un ID de plan n'est jamais un droit d'accès à lui seul. Les réponses ne révèlent des noms de fichiers qu'au demandeur autorisé, dans son chat Telegram privé ou dans le canal Slack privé. Toutes les personnes admises dans ce canal peuvent lire son historique : son appartenance fait donc partie de l'autorisation de consulter ces métadonnées et pièces jointes.

## 4. Parcours

### 4.1 `analyse`

Une analyse manuelle ou hebdomadaire inventorie les fichiers réguliers éligibles sous `Downloads`, la hiérarchie des dossiers de `Documents` et les apprentissages confirmés. Aucun octet de document n'est transmis au modèle : seuls les noms de fichiers de `Downloads`, leurs métadonnées nécessaires et les noms des dossiers de `Documents` le sont. Les noms de fichiers déjà dans `Documents` restent locaux. Le composant local construit un plan complet, vérifie ses cibles, calcule son niveau général, lui attribue deux mots français aléatoires séparés par un trait d'union, avec accents possibles, puis répond seulement : « Je propose le plan <ID> pour <N> fichiers ; confiance <High|Medium|Low>. Validité du plan jusqu'à hh:mm. » Il indique comment demander `détaille <ID>`. et `range <ID>` Aucun déplacement n'a lieu.

Un nouveau plan invalide **tous** les plans encore proposés, quel que soit leur auteur. Le plan est valable 30 minutes à compter de sa création, tant qu'aucun autre plan n'est créé et que l'inventaire déclencheur n'a pas changé. Toute addition, suppression ou modification de nom sous `Downloads`, ainsi que toute addition, suppression ou modification de nom d'un **répertoire** sous `Documents`, invalide le plan. Un changement de taille, contenu ou identité d'un fichier source provoque aussi un refus de `range` au contrôle de sécurité. Les modifications sans changement de nom dans un document déjà classé ne changent pas le classement, mais un conflit de cible est toujours recontrôlé avant exécution.

S'il n'y a aucun fichier éligible, réponse `PB-DL-EMPTY`, sans plan. Un inventaire inaccessible, incomplet, trop volumineux ou ambigu produit une erreur, pas un plan partiel présenté comme complet. Les fichiers cachés, liens symboliques et objets non réguliers sont exclus avec un compteur explicite ; cette convention de sécurité est une hypothèse mineure à valider en recette.

### 4.2 `détaille <ID>`

Seul l'auteur voit les déplacements `Downloads/<source> → Documents/<cible>` de chaque fichier, la justification **par fichier** de la cible et de sa confiance, le nombre et le pourcentage vers `a_trier`, les obstacles et les éventuelles suggestions de nouveaux dossiers. Une suggestion de dossier reste informative : aucune création n'est incluse dans le plan, sauf `a_trier` si absent. La réponse donne l'échéance et rappelle qu'`range <ID>` est l'accord final. Détailer un plan expiré, invalidé, appliqué ou appartenant à autrui est refusé sans déplacement.

### 4.3 `range <ID>`

Cette commande, donnée par l'auteur authentifié, est la validation finale du plan détaillable ; aucune seconde confirmation n'est demandée. Un script versionné et auditable revalide le plan et l'environnement, crée et vérifie **tous** les backups hors `Documents` avant le premier déplacement, puis exécute les déplacements approuvés. Il ne crée aucun dossier cible sauf `Documents/a_trier` à son premier usage. Il préserve les noms de fichiers et refuse tout écrasement. Le succès confirme le nombre de fichiers et l'ID. Le backup reste conservé sans purge automatique, même après un incident ou un retour arrière.

En cas d'échec, l'exécuteur arrête le plan et remet uniquement les fichiers que ce plan vient de déplacer dans leur source ; il retire uniquement ses propres copies temporaires et nouvelles cibles créées pendant ce plan. Il ne touche jamais à un document préexistant. Un journal durable permet une reprise après coupure. Si le retour automatique est impossible sans risquer d'écraser une modification humaine, le plan est bloqué, aucun nouveau `range` n'est accepté et un message fournit un code d'incident et la marche à suivre ; il serait trompeur d'annoncer un retour réussi. Un plan s'exécute au plus une fois.

### 4.4 `envoie <requête>`

La requête non vide correspond à tout ou partie du **nom de fichier**, sans recherche dans le contenu ni dans le seul chemin de dossier ; comparaison insensible à la casse et aux accents. Zéro résultat : réponse explicite. Un seul résultat : le composant d'envoi ouvre ce fichier régulier après recontrôle de son chemin, transmet ses octets uniquement à l'API native du canal demandeur et confirme la livraison. Plusieurs résultats : il **liste tous** les chemins relatifs correspondants, sans en envoyer aucun, puis demande lequel envoyer ; la sélection ultérieure est liée au demandeur et à une liste qui est revalidée avant émission. Aucun premier résultat arbitraire, aucune troncature silencieuse. Le canal peut refuser un fichier trop grand : code et limite indiqués, sans conversion ni service tiers implicite.

### 4.5 `apprentissages`

L'agent liste les observations confirmées de rangement manuel : nom d'origine, dossier final, date, exemples en attente et cas ambigus/non retrouvés, avec une commande ou procédure de correction et d'effacement. Il affiche toujours le **chemin configuré des backups**, sans en afficher le contenu. Pour chaque fichier placé par lui dans `a_trier`, le composant local conserve empreinte SHA-256, métadonnées et identité locale. À l'analyse suivante, il recherche sous `Documents` un correspondant déplacé et éventuellement renommé par une personne. Il calcule localement les empreintes des **seuls candidats nécessaires** ; il n'apprend que si un seul candidat certain est trouvé hors `a_trier`. Deux fichiers identiques ou un fichier modifié donnent un état ambigu, sans apprentissage automatique. Les observations peuvent guider les plans suivants mais n'autorisent jamais un déplacement sans `range`.

### 4.6 Dimanche à 17 h

Une tâche unique, fuseau `Europe/Paris`, se déclenche tous les dimanches à 17 h, heure locale avec changement d'heure géré par le fuseau. Elle notifie **au lancement** Telegram et Slack, puis exécute `analyse` une fois, envoie son résultat ou son erreur sur les deux canaux et attend une commande humaine. Elle ne lance jamais `range`. Si une notification échoue, l'autre est tentée et l'échec est journalisé. Elle est créée désactivée, testée une fois manuellement, puis activée après validation de l'exploitant.

## 5. Confiance

Soit `N` le nombre de fichiers du plan et `A` le nombre orienté vers `a_trier`. La classification est calculée par le composant local sur **toutes** les actions : `High` si `A=0`, tous les noms sont clairs et chaque dossier existant est justifié ; `Medium` si `0<A/N<20 %` et aucun nom n'est opaque ; `Low` si `A/N≥20 %` **ou** au moins un nom est opaque. Un nom opaque inclut une suite sans indice métier exploitable, par exemple `1245487654657564jhkjh.pdf`. Un nom opaque va normalement dans `a_trier`. Le plan peut être `Low` et néanmoins exécutable après `range` explicite. Aucun pourcentage arrondi n'est utilisé pour décider du seuil.

## 6. Catalogue des exigences

Priorités : P0 = indispensable avant mise en service ; P1 = exploitation nécessaire ; P2 = amélioration sans extension de privilège. Chaque critère est observable en recette.

| ID | Prio | Exigence et raison | Critère d'acceptation |
| --- | --- | --- | --- |
| F-001 | P0 | Allowlist par plateforme et canal ; protéger fichiers et plans. | Une personne admise agit ; une autre ou un autre canal reçoit un refus sans nom de fichier. |
| F-002 | P0 | `analyse` non destructive et complète ; validation humaine. | Un plan, compte et confiance sont émis ; arborescences et empreintes de fichiers restent identiques. |
| F-003 | P0 | Détail personnel, exhaustif et motivé ; décision éclairée. | Chaque action et justification est visible seulement par l'auteur. |
| F-004 | P0 | Plan 30 min, invalidations et usage unique ; éviter un plan périmé. | Temps limite, nouveau plan et changements prescrits refusent `range`. |
| F-005 | P0 | Deux mots français aléatoires et maniables ; saisie mobile. | ID unique actif, accent conservé, formes non conformes refusées. |
| F-006 | P0 | `range` après accord, script versionné ; audit. | Aucun déplacement sans commande de l'auteur ; journal et manifeste liés à l'ID. |
| F-007 | P0 | Backup intégral préalable hors `Documents` ; reprise. | Chaque fichier déplacé possède un backup vérifié ; manque d'espace refuse avant mouvement. |
| F-008 | P0 | Retour arrière limité au plan ; éviter pertes et toucher les tiers. | Erreur au milieu : sources restaurées ou incident bloquant clairement signalé ; documents préexistants inchangés. |
| F-009 | P0 | Pas de suppression ni reclassement d'un document préexistant ; respecter le périmètre. | Toute cible existante et toute action `Documents→Documents` sont refusées. |
| F-010 | P0 | Aucune création de dossier sauf `a_trier` initial ; garder la hiérarchie humaine. | Dossier suggéré jamais créé ; seul `a_trier` peut l'être une fois. |
| F-011 | P0 | Envoi par nom avec désambiguïsation exhaustive ; éviter le mauvais destinataire/fichier. | 0/1/N résultats corrects, aucune pièce jointe avant choix si N>1. |
| F-012 | P0 | Accès aux octets borné à empreinte, backup et envoi explicite ; confidentialité. | Aucun contenu ni hash envoyé au LLM/logs ; accès hors montages et symlink refusés. |
| F-013 | P1 | Apprendre seulement un classement manuel certain après `a_trier`. | Déplacement avec renommage identifié par hash ; ambiguïté sans apprentissage. |
| F-014 | P1 | `apprentissages`, correction, effacement et chemin backup ; contrôle humain. | Liste et chemin affichés ; suppression d'une observation de la base vérifiée, backup intact. |
| F-015 | P1 | Analyse hebdomadaire à 17 h et double notification ; suivi. | Départ puis résultat sur les deux canaux ; aucun fichier déplacé. |
| F-016 | P0 | Codes d'erreur corrélés aux logs ; diagnostic sans fuite. | Chaque échec possède code stable et ID d'incident ; logs retrouvent la cause. |
| F-017 | P1 | Survie au redémarrage et restauration de l'état privé ; continuité. | Plans périmés refusés après reprise ; apprentissages restaurés ; transaction inachevée réconciliée. |
| F-018 | P1 | Réutiliser bot et app existants après vérification ; éviter doublons. | Un seul consommateur Telegram, app Slack à scopes minimaux et tests réels. |

## 7. Données, conservation et suppression

Les noms de `Downloads`, tailles, dates, types et dossiers `Documents` proviennent de l'hôte ; les noms de documents classés restent locaux pour la recherche et la vérification des collisions. Les octets ne sont ouverts que par le composant local pour l'empreinte, la copie vérifiée et l'envoi demandé. Le modèle reçoit uniquement le contexte réduit indiqué au §4.1. Telegram et Slack reçoivent les réponses et, sur `envoie`, la pièce jointe demandée ; leur rétention propre dépend des plateformes et de l'administration de ces comptes.

Par défaut de spécification, plans et détails locaux : 30 jours après clôture ; apprentissages confirmés et événements : 90 jours ; suivi non résolu de `a_trier` : jusqu'à résolution ou effacement explicite ; journaux techniques minimisés : 30 jours ; backups : sans purge automatique. Ces durées sont configurables sans changer le contrat des 30 minutes. L'effacement d'un apprentissage retire ses métadonnées locales, jamais un document ou backup. Les secrets n'entrent ni dans les plans ni dans la mémoire. La sauvegarde/restauration du runtime est privée et chiffrée selon le runbook.

## 8. Erreurs et interventions

Format utilisateur : `PB-<CODE> — phrase utile — incident <ID>`, sans token, contenu de fichier ni trace brute. Catalogue minimal : `PB-DL-EMPTY` (rien à classer), `PB-FS-DENIED` (droits), `PB-PLAN-EXPIRED`, `PB-PLAN-INVALID`, `PB-PLAN-OWNER`, `PB-PLAN-COLLISION`, `PB-BACKUP-SPACE`, `PB-BACKUP-VERIFY`, `PB-APPLY-FAILED`, `PB-ROLLBACK-BLOCKED`, `PB-MODEL-UNAVAILABLE`, `PB-SEND-NOTFOUND`, `PB-SEND-AMBIGUOUS`, `PB-SEND-LIMIT`, `PB-SEND-FAILED`, `PB-CHANNEL-FAILED`. Les logs techniques portent l'ID, le code, l'étape et les chemins relatifs nécessaires, sans octets ni secret. Une panne de modèle bloque l'analyse ; elle ne déclenche aucun fournisseur alternatif. Une panne d'un canal ne masque pas l'autre.

## 9. Qualités attendues et recette

Le service fonctionne tant que le Mac, Docker Desktop et les réseaux nécessaires fonctionnent ; aucune disponibilité 24/7 n'est promise pendant veille/arrêt. La réponse de commande indique immédiatement qu'une analyse ou un transfert long est en cours, puis donne le résultat ; les limites de durée, taille, concurrence et coût sont configurables et affichées au runbook. Une seule analyse et un seul `range` peuvent accéder au registre à la fois. Le fuseau et les accents sont pris en charge ; chaque réponse fournit la syntaxe textuelle, sans dépendre d'un bouton. L'abonnement Codex et ses limites sont vérifiés avant activation ; aucun basculement payant implicite.

Recette de bout en bout : (R1) 0/1/N résultats `envoie`, choix et contrôle du destinataire ; (R2) `analyse→détaille→range` avec backups contrôlés ; (R3) plan expiré, nouveau plan, renommage dans `Downloads`, nouveau dossier dans `Documents` ; (R4) collision cible et espace insuffisant avant mouvement ; (R5) échec injecté après un déplacement, rollback et récupération après arrêt brutal ; (R6) fichier passé par `a_trier`, renommé puis classé manuellement, apprentissage au run suivant ; (R7) échec Slack ou Telegram, autre canal livré et code corrélé ; (R8) redémarrage des services puis restauration de la base et des secrets de test, sans rejouer un plan consommé ; (R9) dimanche 17 h simulé en `Europe/Paris`, notifications de lancement et résultat sans `range` ; (R10) accès refusé à un tiers, à un symlink et à un chemin hors périmètre.

## 10. Décisions et hypothèses résiduelles

Décidé avec l'utilisateur pendant ce cadrage : plusieurs personnes autorisées avec mêmes commandes ; canal Slack privé ; plan réservé à son auteur ; `range <ID>` est l'accord final ; backup vérifié avant mouvement ; retour arrière limité aux artefacts du plan ; empreinte locale et envoi d'octets sur demande explicite permis ; troisième chemin de backup réservé au composant isolé ; création initiale unique de `a_trier` ; seuil `Low` dès 20 % ou nom opaque ; transmission au modèle des seules métadonnées minimales.

Hypothèses mineures à valider en recette/configuration : noms des fichiers cachés et objets spéciaux exclus avec compteur ; conservation par défaut ci-dessus ; chemin physique des trois racines et identifiants de personnes fournis à l'installation ; limite de taille adaptée aux plateformes et au disque disponible. Aucun secret ou identifiant réel n'est nécessaire dans ces spécifications. Si la politique locale impose de classer des fichiers cachés ou si `Downloads` et `Documents` ne sont pas accessibles à Docker Desktop, l'exploitant doit revoir le périmètre et refaire la recette avant activation.
